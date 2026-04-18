"""Cache port interface — contract for caching backends.

Provides a simple get/set/delete abstraction. Implementations can be
in-memory, Redis, or any other caching technology.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class CachePort(ABC):
    """Abstract cache interface."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key. Returns None if not found or expired."""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store a value with an optional TTL."""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if it existed."""

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached entries."""
