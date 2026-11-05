"""In-Process Asynchronous Background Task Queue & Worker Pool.
Executes non-blocking background operations (email dispatch, notifications,
maintenance checkpoints) using an unprivileged ThreadPoolExecutor.
"""

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

from src.core.config import TASK_WORKERS

logger = logging.getLogger("ims")


class BackgroundTaskWorker:
    """Thread-safe background task scheduler and worker manager."""

    _executor: Optional[ThreadPoolExecutor] = None
    _lock: threading.Lock = threading.Lock()
    _queued_count: int = 0
    _completed_count: int = 0
    _failed_count: int = 0

    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        with cls._lock:
            if cls._executor is None:
                cls._executor = ThreadPoolExecutor(
                    max_workers=TASK_WORKERS,
                    thread_name_prefix="ims-worker",
                )
                logger.info(
                    "Initialized BackgroundTaskWorker with %d worker threads.", TASK_WORKERS
                )
            return cls._executor

    @classmethod
    def enqueue(cls, task_fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
        """Schedule a callable to run asynchronously in a worker thread."""
        executor = cls._get_executor()
        with cls._lock:
            cls._queued_count += 1

        def _runner() -> Any:
            try:
                result = task_fn(*args, **kwargs)
                with cls._lock:
                    cls._completed_count += 1
                return result
            except Exception as e:
                with cls._lock:
                    cls._failed_count += 1
                logger.error(
                    "Background task '%s' failed with error: %s",
                    getattr(task_fn, "__name__", str(task_fn)),
                    e,
                    exc_info=True,
                )
                raise

        return executor.submit(_runner)

    @classmethod
    def get_telemetry(cls) -> Dict[str, Any]:
        """Report task queue execution metrics."""
        with cls._lock:
            return {
                "max_workers": TASK_WORKERS,
                "queued_total": cls._queued_count,
                "completed_total": cls._completed_count,
                "failed_total": cls._failed_count,
                "active_pending": max(
                    0, cls._queued_count - (cls._completed_count + cls._failed_count)
                ),
            }

    @classmethod
    def shutdown(cls, wait: bool = True) -> None:
        """Gracefully terminate background thread pool."""
        with cls._lock:
            if cls._executor is not None:
                logger.info("Shutting down BackgroundTaskWorker pool (wait=%s)...", wait)
                cls._executor.shutdown(wait=wait)
                cls._executor = None


def enqueue_background_task(task_fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
    """Public helper to submit a task to the background worker pool."""
    return BackgroundTaskWorker.enqueue(task_fn, *args, **kwargs)


def get_task_telemetry() -> Dict[str, Any]:
    """Retrieve execution metrics from the background worker pool."""
    return BackgroundTaskWorker.get_telemetry()


def shutdown_task_worker_pool(wait: bool = True) -> None:
    """Shutdown background task worker threads."""
    BackgroundTaskWorker.shutdown(wait=wait)
