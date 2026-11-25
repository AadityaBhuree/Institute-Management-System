"""Institute Management System - Enterprise Security Hardening Module.
Implements brute-force login throttling, security response headers, and request body size bounds.
"""

import threading
import time
from typing import Dict, List, Optional

from fastapi.responses import JSONResponse
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.core.config import (
    LOGIN_LOCKOUT_SECONDS,
    LOGIN_MAX_ATTEMPTS,
    MAX_REQUEST_SIZE_BYTES,
)


class LoginRateLimiter:
    """Thread-safe sliding-window rate limiter for brute-force login protection."""

    def __init__(
        self, max_attempts: int = LOGIN_MAX_ATTEMPTS, lockout_seconds: int = LOGIN_LOCKOUT_SECONDS
    ):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._failures: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def _clean_expired(self, key: str, now: float) -> List[float]:
        threshold = now - self.lockout_seconds
        valid = [t for t in self._failures.get(key, []) if t > threshold]
        if valid:
            self._failures[key] = valid
        elif key in self._failures:
            del self._failures[key]
        return valid

    def is_locked(self, username: Optional[str] = None, ip_address: Optional[str] = None) -> bool:
        """Check if username or IP address has exceeded the allowed failed login attempts."""
        now = time.time()
        with self._lock:
            keys = []
            if username:
                keys.append(f"user:{username.lower().strip()}")
            if ip_address:
                keys.append(f"ip:{ip_address.strip()}")

            for key in keys:
                attempts = self._clean_expired(key, now)
                if len(attempts) >= self.max_attempts:
                    return True
        return False

    def record_failure(
        self, username: Optional[str] = None, ip_address: Optional[str] = None
    ) -> None:
        """Register a failed login attempt for the provided username and client IP."""
        now = time.time()
        with self._lock:
            keys = []
            if username:
                keys.append(f"user:{username.lower().strip()}")
            if ip_address:
                keys.append(f"ip:{ip_address.strip()}")

            for key in keys:
                attempts = self._clean_expired(key, now)
                attempts.append(now)
                self._failures[key] = attempts

    def record_success(
        self, username: Optional[str] = None, ip_address: Optional[str] = None
    ) -> None:
        """Clear failed login attempts following a successful authentication."""
        with self._lock:
            if username:
                self._failures.pop(f"user:{username.lower().strip()}", None)
            if ip_address:
                self._failures.pop(f"ip:{ip_address.strip()}", None)

    def reset(self) -> None:
        """Clear all active brute-force failure tracking."""
        with self._lock:
            self._failures.clear()


# Global login rate limiter singleton
login_limiter = LoginRateLimiter()


class SecurityHeadersMiddleware:
    """Enforces essential OWASP security headers across all incoming web & API responses via pure ASGI."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["X-XSS-Protection"] = "1; mode=block"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
                headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' https://fonts.gstatic.com data:; "
                    "img-src 'self' data:; "
                    "connect-src 'self'; "
                    "frame-ancestors 'none';"
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestBodySizeLimitMiddleware:
    """Guards against memory exhaustion and payload flood by rejecting oversized HTTP request bodies via pure ASGI."""

    def __init__(self, app: ASGIApp, max_body_bytes: int = MAX_REQUEST_SIZE_BYTES):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        content_length = headers.get("content-length")
        if content_length:
            try:
                length_int = int(content_length)
                if length_int > self.max_body_bytes:
                    limit_mb = self.max_body_bytes // (1024 * 1024)
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request body exceeds maximum allowed size of {limit_mb}MB."
                        },
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass

        await self.app(scope, receive, send)
