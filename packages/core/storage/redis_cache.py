"""
Redis Cache — distributed async cache backend for cloud/production mode.

Implements the CacheBackend protocol using Redis with TTL support.
Values are stored as JSON-serialised strings via SETEX / SET.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-backed cache with TTL support.

    Parameters
    ----------
    redis_url:
        Redis connection URL.  Falls back to the ``REDIS_URL``
        environment variable, then ``redis://localhost:6379/0``.
    key_prefix:
        Optional prefix prepended to every key for namespacing.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        key_prefix: str = "cache:",
    ) -> None:
        self._redis_url = redis_url or os.environ.get(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        self._key_prefix = key_prefix
        self._client: Any = None  # lazy-initialised redis.asyncio client

    def _prefixed(self, key: str) -> str:
        """Return the prefixed key."""
        return f"{self._key_prefix}{key}"

    async def _get_client(self) -> Any:
        """Lazy-initialise and return the async Redis client."""
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
            )
            logger.info("Redis cache client connected", extra={"url": self._redis_url})
        return self._client

    # ------------------------------------------------------------------
    # CacheBackend protocol methods
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Optional[str]:
        """Get a value by key. Returns None if not found or expired."""
        client = await self._get_client()
        value = await client.get(self._prefixed(key))
        if value is None:
            return None
        # Values are stored as JSON; unwrap the string.
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(
        self, key: str, value: str, ttl_seconds: Optional[int] = None
    ) -> None:
        """Set a key-value pair with optional TTL (in seconds)."""
        client = await self._get_client()
        serialised = json.dumps(value)
        prefixed = self._prefixed(key)
        if ttl_seconds is not None and ttl_seconds > 0:
            await client.setex(prefixed, ttl_seconds, serialised)
        else:
            await client.set(prefixed, serialised)

    async def delete(self, key: str) -> None:
        """Delete a key."""
        client = await self._get_client()
        await client.delete(self._prefixed(key))

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric key. Creates with value=amount if not exists."""
        client = await self._get_client()
        prefixed = self._prefixed(key)

        # Check if key exists; if so, read current value.
        raw = await client.get(prefixed)
        if raw is not None:
            try:
                current = int(json.loads(raw))
            except (json.JSONDecodeError, TypeError, ValueError):
                current = 0
        else:
            current = 0

        new_val = current + amount
        await client.set(prefixed, json.dumps(str(new_val)))
        return new_val

    async def exists(self, key: str) -> bool:
        """Check if a key exists (and has not expired)."""
        client = await self._get_client()
        return bool(await client.exists(self._prefixed(key)))

    # ------------------------------------------------------------------
    # Extended operations
    # ------------------------------------------------------------------

    async def clear(self, pattern: str = "*") -> int:
        """Delete all keys matching *pattern* under the prefix.

        Returns the number of keys deleted.
        """
        client = await self._get_client()
        full_pattern = f"{self._key_prefix}{pattern}"
        cursor = "0"
        deleted = 0
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=full_pattern, count=100)
            if keys:
                await client.delete(*keys)
                deleted += len(keys)
            if cursor == 0 or cursor == "0":
                break
        return deleted

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Redis cache client closed")
