"""In-memory thread-safe TTL cache utility for high-performance read caching.
Provides sub-millisecond retrieval with automatic time-to-live expiration and metric tracking.
"""

import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar

T = TypeVar("T")


class TTLCache:
    """Thread-safe in-memory cache with configurable TTL per key and telemetry counters."""

    def __init__(self, default_ttl_seconds: float = 300.0):
        self._default_ttl = default_ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expire_timestamp)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value if present and not expired; otherwise return None."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            val, expiry = entry
            if time.time() > expiry:
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return val

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Store a value in cache with specified or default TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expiry = time.time() + ttl
        with self._lock:
            self._cache[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        """Remove a single key from cache. Returns True if key was present."""
        with self._lock:
            return bool(self._cache.pop(key, None))

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys starting with prefix. Returns count of invalidated entries."""
        with self._lock:
            keys_to_del = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_del:
                del self._cache[k]
            return len(keys_to_del)

    def clear(self) -> None:
        """Clear all entries from cache and reset hit/miss counters."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        ttl_seconds: Optional[float] = None,
    ) -> T:
        """Retrieve cached value or compute and store it via factory callback."""
        cached = self.get(key)
        if cached is not None:
            return cached
        val = factory()
        self.set(key, val, ttl_seconds=ttl_seconds)
        return val

    def stats(self) -> Dict[str, Any]:
        """Return cache health telemetry and hit/miss ratios."""
        with self._lock:
            now = time.time()
            active_count = sum(1 for _, expiry in self._cache.values() if expiry > now)
            total_lookups = self._hits + self._misses
            hit_ratio = round((self._hits / total_lookups * 100), 1) if total_lookups > 0 else 0.0
            return {
                "active_entries": active_count,
                "total_stored": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio_percent": hit_ratio,
                "default_ttl_seconds": self._default_ttl,
            }


# Global singleton cache instance for application lifecycle
cache = TTLCache(default_ttl_seconds=300.0)
