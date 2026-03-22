"""
In-Memory Cache — cache/session store for desktop/local mode.

Implements the CacheBackend protocol using a dict with TTL support.
Used when Redis is not available (desktop EXE, development).
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class InMemoryCache:
    """In-memory cache with TTL support."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, Optional[float]]] = {}  # key -> (value, expires_at)

    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired."""
        if key not in self._store:
            return True
        _, expires_at = self._store[key]
        if expires_at is not None and time.time() > expires_at:
            del self._store[key]
            return True
        return False

    def _cleanup(self) -> None:
        """Remove expired keys (called periodically)."""
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if exp is not None and now > exp]
        for k in expired:
            del self._store[k]

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key. Returns None if not found or expired."""
        if self._is_expired(key):
            return None
        value, _ = self._store[key]
        return value

    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
        """Set a key-value pair with optional TTL."""
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        """Delete a key."""
        self._store.pop(key, None)

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric key. Creates with value=amount if not exists."""
        current = await self.get(key)
        if current is None:
            new_val = amount
        else:
            new_val = int(current) + amount
        # Preserve existing TTL if any
        if key in self._store:
            _, expires_at = self._store[key]
            self._store[key] = (str(new_val), expires_at)
        else:
            self._store[key] = (str(new_val), None)
        return new_val

    async def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        return not self._is_expired(key)

    @property
    def size(self) -> int:
        """Return number of keys (including possibly expired)."""
        self._cleanup()
        return len(self._store)
