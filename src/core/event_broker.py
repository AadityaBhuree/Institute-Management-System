"""In-Process Real-Time Pub/Sub Event Broker.
Manages asynchronous event queues, channel routing, role/user audience targeting,
and Server-Sent Events (SSE) serialization across asynchronous and thread-pool boundaries.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ims")


@dataclass
class Subscriber:
    """Represents an active client streaming connection queue."""

    id: str
    channel: str
    user_id: Optional[int] = None
    role: Optional[str] = None
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=100))
    created_at: float = field(default_factory=time.time)


class EventBroker:
    """Thread-safe in-memory publish/subscribe broker for real-time institutional streams."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, Subscriber] = {}
        self._lock: threading.RLock = threading.RLock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._published_total: int = 0

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Explicitly bind the active asyncio event loop."""
        with self._lock:
            self._loop = loop

    def _get_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Obtain active running asyncio loop or return registered loop."""
        with self._lock:
            if self._loop is not None and not self._loop.is_closed():
                return self._loop
        try:
            loop = asyncio.get_running_loop()
            with self._lock:
                self._loop = loop
            return loop
        except RuntimeError:
            return None

    def subscribe(
        self,
        channel: str,
        role: Optional[str] = None,
        user_id: Optional[int] = None,
        maxsize: int = 100,
    ) -> Subscriber:
        """Register a new streaming subscriber to a channel."""
        sub_id = str(uuid.uuid4())
        self._get_loop()
        sub = Subscriber(
            id=sub_id,
            channel=channel,
            user_id=user_id,
            role=role.upper() if role else None,
            queue=asyncio.Queue(maxsize=maxsize),
        )
        with self._lock:
            self._subscribers[sub_id] = sub
        logger.debug(
            "Registered SSE subscriber %s on channel '%s' (user_id=%s, role=%s)",
            sub_id,
            channel,
            user_id,
            role,
        )
        return sub

    def unsubscribe(self, subscriber_id: str) -> None:
        """Remove a disconnected subscriber and free its queue."""
        with self._lock:
            removed = self._subscribers.pop(subscriber_id, None)
        if removed:
            logger.debug(
                "Unsubscribed SSE subscriber %s from channel '%s'",
                subscriber_id,
                removed.channel,
            )

    @staticmethod
    def format_sse_message(
        event: str,
        data: Any,
        event_id: Optional[str] = None,
        retry_ms: Optional[int] = None,
    ) -> str:
        """Serialize payload into standard W3C Server-Sent Events (SSE) text protocol format."""
        msg_id = event_id or uuid.uuid4().hex[:12]
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, separators=(",", ":"), default=str)
        else:
            data_str = str(data)

        lines = [f"id: {msg_id}", f"event: {event}"]
        if retry_ms:
            lines.append(f"retry: {retry_ms}")
        lines.append(f"data: {data_str}\n\n")
        return "\n".join(lines)

    def publish(
        self,
        channel: str,
        event_type: str,
        data: Any,
        target_role: Optional[str] = None,
        target_user_id: Optional[int] = None,
    ) -> int:
        """Publish an event to all matching subscribers on a channel.

        Supports cross-thread invocation from background tasks or synchronous endpoints.
        Returns count of subscribers the event was queued to.
        """
        formatted_msg = self.format_sse_message(event=event_type, data=data)
        norm_target_role = target_role.upper() if target_role else None

        with self._lock:
            self._published_total += 1
            # Filter matching subscribers
            matched: List[Subscriber] = []
            for sub in self._subscribers.values():
                if sub.channel != channel:
                    continue

                # Role-based gating:
                # - Target 'ALL' or None delivers to everyone
                # - Admin role always receives administrative streams
                # - Exact role match
                if norm_target_role and norm_target_role != "ALL":
                    if sub.role and sub.role != "ADMIN" and sub.role != norm_target_role:
                        continue

                # User-based gating:
                # - If target_user_id is set, only that user or administrative monitors match
                if target_user_id is not None:
                    if sub.user_id is not None and sub.user_id != target_user_id:
                        if sub.role != "ADMIN":
                            continue

                matched.append(sub)

        if not matched:
            return 0

        loop = self._get_loop()
        queued_count = 0

        for sub in matched:
            try:
                # If no coroutine is actively awaiting queue.get() on an event loop,
                # put directly into the queue so synchronous callers/tests observe it immediately.
                has_active_getters = bool(getattr(sub.queue, "_getters", None))

                try:
                    current_loop = asyncio.get_running_loop()
                except RuntimeError:
                    current_loop = None

                if not has_active_getters or (current_loop is not None and current_loop == loop):
                    # Same thread or no active async waiters
                    if sub.queue.full():
                        try:
                            sub.queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    sub.queue.put_nowait(formatted_msg)
                    queued_count += 1
                elif loop is not None and not loop.is_closed():
                    # Cross-thread dispatch to active listener on loop
                    def _enqueue_safely(q=sub.queue, msg=formatted_msg) -> None:
                        if q.full():
                            try:
                                q.get_nowait()
                            except asyncio.QueueEmpty:
                                pass
                        q.put_nowait(msg)

                    loop.call_soon_threadsafe(_enqueue_safely)
                    queued_count += 1
                else:
                    if sub.queue.full():
                        try:
                            sub.queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    sub.queue.put_nowait(formatted_msg)
                    queued_count += 1
            except Exception as e:
                logger.warning("Failed to queue SSE event to subscriber %s: %s", sub.id, e)

        return queued_count

    def get_telemetry(self) -> Dict[str, Any]:
        """Aggregate active channel metrics and subscriber telemetry."""
        with self._lock:
            channels: Dict[str, int] = {}
            for sub in self._subscribers.values():
                channels[sub.channel] = channels.get(sub.channel, 0) + 1

            return {
                "active_subscribers": len(self._subscribers),
                "channels": channels,
                "published_total": self._published_total,
            }

    def clear(self) -> None:
        """Teardown all subscribers and reset event metrics (for testing)."""
        with self._lock:
            self._subscribers.clear()
            self._published_total = 0
            self._loop = None


# Singleton institutional event broker instance
event_broker = EventBroker()
