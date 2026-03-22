"""
In-Memory Queue — async queue backend for desktop/local mode.

Implements the QueueBackend protocol using asyncio.Queue.
Used when Redis is not available (desktop EXE, development).
"""

from __future__ import annotations

import asyncio
import logging
import json
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class InMemoryQueue:
    """In-memory task queue using asyncio.Queue."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self._pending: dict[str, dict[str, dict]] = {}  # queue -> {msg_id -> message}

    def _get_queue(self, queue_name: str) -> asyncio.Queue:
        if queue_name not in self._queues:
            self._queues[queue_name] = asyncio.Queue()
            self._pending[queue_name] = {}
        return self._queues[queue_name]

    async def enqueue(self, queue_name: str, message: dict) -> str:
        """Add a message to the queue. Returns message ID."""
        q = self._get_queue(queue_name)
        msg_id = str(uuid4())
        wrapped = {"_id": msg_id, "_payload": message}
        await q.put(wrapped)
        logger.debug("Message enqueued", extra={"queue": queue_name, "msg_id": msg_id})
        return msg_id

    async def dequeue(self, queue_name: str, timeout_seconds: int = 0) -> Optional[dict]:
        """Remove and return a message from the queue."""
        q = self._get_queue(queue_name)
        try:
            if timeout_seconds > 0:
                wrapped = await asyncio.wait_for(q.get(), timeout=timeout_seconds)
            else:
                wrapped = q.get_nowait()
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            return None

        msg_id = wrapped["_id"]
        payload = wrapped["_payload"]
        # Track as pending until ack/nack
        self._pending[queue_name][msg_id] = payload
        payload["_msg_id"] = msg_id
        return payload

    async def ack(self, queue_name: str, message_id: str) -> None:
        """Acknowledge a message (mark as processed)."""
        if queue_name in self._pending:
            self._pending[queue_name].pop(message_id, None)
            logger.debug("Message acked", extra={"queue": queue_name, "msg_id": message_id})

    async def nack(self, queue_name: str, message_id: str) -> None:
        """Negative-acknowledge a message (re-queue for retry)."""
        if queue_name in self._pending and message_id in self._pending[queue_name]:
            payload = self._pending[queue_name].pop(message_id)
            await self.enqueue(queue_name, payload)
            logger.debug("Message nacked and re-queued", extra={"queue": queue_name, "msg_id": message_id})

    async def queue_size(self, queue_name: str) -> int:
        """Return the number of messages in the queue."""
        q = self._get_queue(queue_name)
        return q.qsize()
