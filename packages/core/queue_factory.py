"""
Queue & Cache Factory — returns the appropriate backend based on configuration.

Uses the ``QUEUE_BACKEND`` environment variable to select between:
  - ``memory`` (default) — in-process asyncio.Queue / dict
  - ``redis``            — distributed Redis-backed implementation
"""

from __future__ import annotations

import logging
import os
from typing import Union

from packages.core.storage.memory_cache import InMemoryCache
from packages.core.storage.memory_queue import InMemoryQueue
from packages.core.storage.redis_cache import RedisCache
from packages.core.storage.redis_queue import RedisQueue

logger = logging.getLogger(__name__)

QueueType = Union[InMemoryQueue, RedisQueue]
CacheType = Union[InMemoryCache, RedisCache]


def create_queue(
    backend: str | None = None,
    redis_url: str | None = None,
    max_retries: int = 3,
) -> QueueType:
    """Create a queue backend based on configuration.

    Parameters
    ----------
    backend:
        ``"redis"`` or ``"memory"``.  Defaults to the ``QUEUE_BACKEND``
        env var, then ``"memory"``.
    redis_url:
        Redis connection URL (only used when *backend* is ``"redis"``).
    max_retries:
        Max nack retries before DLQ (Redis only).
    """
    backend = backend or os.environ.get("QUEUE_BACKEND", "memory")

    if backend == "redis":
        logger.info("Using Redis queue backend")
        return RedisQueue(redis_url=redis_url, max_retries=max_retries)

    logger.info("Using in-memory queue backend")
    return InMemoryQueue()


def create_cache(
    backend: str | None = None,
    redis_url: str | None = None,
    key_prefix: str = "cache:",
) -> CacheType:
    """Create a cache backend based on configuration.

    Parameters
    ----------
    backend:
        ``"redis"`` or ``"memory"``.  Defaults to the ``QUEUE_BACKEND``
        env var, then ``"memory"``.
    redis_url:
        Redis connection URL (only used when *backend* is ``"redis"``).
    key_prefix:
        Key prefix for namespacing (Redis only).
    """
    backend = backend or os.environ.get("QUEUE_BACKEND", "memory")

    if backend == "redis":
        logger.info("Using Redis cache backend")
        return RedisCache(redis_url=redis_url, key_prefix=key_prefix)

    logger.info("Using in-memory cache backend")
    return InMemoryCache()
