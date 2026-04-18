"""In-memory cache with TTL support — implements CachePort.

Drop-in replacement for Redis in development / single-instance deployments.
For production horizontal scaling, swap with a Redis-backed implementation.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional, Tuple

from app.core.logging import get_logger
from app.domain.interfaces.cache import CachePort

logger = get_logger(__name__)


class MemoryCache(CachePort):
    """Thread-safe in-memory cache with per-key TTL.

    Args:
        default_ttl: Default time-to-live in seconds.
        max_size: Maximum number of entries before eviction.
    """

    def __init__(self, default_ttl: int = 300, max_size: int = 1000) -> None:
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expires_at = time.monotonic() + ttl
        async with self._lock:
            if len(self._store) >= self._max_size:
                self._evict_expired()
            self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            return self._store.pop(key, None) is not None

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    def _evict_expired(self) -> None:
        """Remove all expired entries (called under lock)."""
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
