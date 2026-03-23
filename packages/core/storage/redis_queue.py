"""
Redis Queue — distributed async queue backend for cloud/production mode.

Implements the QueueBackend protocol using Redis lists (LPUSH/BRPOP).
Uses a pending hash to track in-flight messages for ack/nack.
Supports dead-letter queues for messages that exceed max retries.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Default maximum number of retries before sending to dead-letter queue.
DEFAULT_MAX_RETRIES = 3
# Redis key prefix for pending message hashes.
PENDING_PREFIX = "queue:pending:"
# Redis key prefix for retry counts.
RETRY_PREFIX = "queue:retries:"
# Dead-letter queue suffix.
DLQ_SUFFIX = ":dlq"


class RedisQueue:
    """Redis-backed distributed task queue.

    Uses Redis lists for FIFO queue semantics (LPUSH to enqueue,
    BRPOP to dequeue) and Redis hashes to track pending messages
    until they are acknowledged or negatively acknowledged.

    Parameters
    ----------
    redis_url:
        Redis connection URL.  Falls back to the ``REDIS_URL``
        environment variable, then ``redis://localhost:6379/0``.
    max_retries:
        Maximum nack retries before a message is moved to the
        dead-letter queue.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._redis_url = redis_url or os.environ.get(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        self._max_retries = max_retries
        self._client: Any = None  # lazy-initialised redis.asyncio client

    async def _get_client(self) -> Any:
        """Lazy-initialise and return the async Redis client."""
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
            )
            logger.info("Redis queue client connected", extra={"url": self._redis_url})
        return self._client

    # ------------------------------------------------------------------
    # QueueBackend protocol methods
    # ------------------------------------------------------------------

    async def enqueue(self, queue_name: str, message: dict) -> str:
        """Add a message to the queue. Returns message ID."""
        client = await self._get_client()
        msg_id = str(uuid4())
        wrapped = json.dumps({"_id": msg_id, "_payload": message})
        await client.lpush(queue_name, wrapped)
        logger.debug("Message enqueued", extra={"queue": queue_name, "msg_id": msg_id})
        return msg_id

    async def dequeue(
        self, queue_name: str, timeout_seconds: int = 0
    ) -> Optional[dict]:
        """Remove and return a message from the queue.

        Uses BRPOP for blocking dequeue when *timeout_seconds* > 0,
        RPOP for non-blocking dequeue otherwise.
        """
        client = await self._get_client()

        if timeout_seconds > 0:
            result = await client.brpop(queue_name, timeout=timeout_seconds)
            if result is None:
                return None
            # brpop returns (key, value)
            raw = result[1]
        else:
            raw = await client.rpop(queue_name)
            if raw is None:
                return None

        wrapped = json.loads(raw)
        msg_id = wrapped["_id"]
        payload = wrapped["_payload"]

        # Track as pending until ack/nack
        pending_key = f"{PENDING_PREFIX}{queue_name}"
        await client.hset(pending_key, msg_id, json.dumps(payload))

        payload["_msg_id"] = msg_id
        return payload

    async def ack(self, queue_name: str, message_id: str) -> None:
        """Acknowledge a message (mark as successfully processed)."""
        client = await self._get_client()
        pending_key = f"{PENDING_PREFIX}{queue_name}"
        retry_key = f"{RETRY_PREFIX}{queue_name}:{message_id}"

        await client.hdel(pending_key, message_id)
        await client.delete(retry_key)
        logger.debug("Message acked", extra={"queue": queue_name, "msg_id": message_id})

    async def nack(self, queue_name: str, message_id: str) -> None:
        """Negative-acknowledge a message.

        Re-queues for retry up to ``max_retries`` times; after that the
        message is moved to the dead-letter queue.
        """
        client = await self._get_client()
        pending_key = f"{PENDING_PREFIX}{queue_name}"
        retry_key = f"{RETRY_PREFIX}{queue_name}:{message_id}"

        raw = await client.hget(pending_key, message_id)
        if raw is None:
            logger.warning(
                "nack called for unknown message",
                extra={"queue": queue_name, "msg_id": message_id},
            )
            return

        payload = json.loads(raw)
        await client.hdel(pending_key, message_id)

        # Increment retry count
        retries = await client.incr(retry_key)

        if retries >= self._max_retries:
            # Move to dead-letter queue
            dlq_name = f"{queue_name}{DLQ_SUFFIX}"
            dlq_msg = json.dumps({
                "_id": message_id,
                "_payload": payload,
                "_retries": retries,
            })
            await client.lpush(dlq_name, dlq_msg)
            await client.delete(retry_key)
            logger.warning(
                "Message moved to DLQ after max retries",
                extra={
                    "queue": queue_name,
                    "dlq": dlq_name,
                    "msg_id": message_id,
                    "retries": retries,
                },
            )
        else:
            # Re-queue for retry
            await self.enqueue(queue_name, payload)
            logger.debug(
                "Message nacked and re-queued",
                extra={
                    "queue": queue_name,
                    "msg_id": message_id,
                    "retry": retries,
                },
            )

    async def queue_size(self, queue_name: str) -> int:
        """Return the number of messages in the queue."""
        client = await self._get_client()
        return await client.llen(queue_name)

    # ------------------------------------------------------------------
    # Extended operations
    # ------------------------------------------------------------------

    async def peek(self, queue_name: str, count: int = 1) -> list[dict]:
        """Peek at messages without removing them (right end = next to dequeue)."""
        client = await self._get_client()
        raw_items = await client.lrange(queue_name, -count, -1)
        results: list[dict] = []
        for raw in reversed(raw_items):
            wrapped = json.loads(raw)
            results.append(wrapped["_payload"])
        return results

    async def dlq_size(self, queue_name: str) -> int:
        """Return the size of the dead-letter queue for *queue_name*."""
        client = await self._get_client()
        return await client.llen(f"{queue_name}{DLQ_SUFFIX}")

    async def pending_count(self, queue_name: str) -> int:
        """Return the number of messages currently pending (in-flight)."""
        client = await self._get_client()
        pending_key = f"{PENDING_PREFIX}{queue_name}"
        return await client.hlen(pending_key)

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Redis queue client closed")
