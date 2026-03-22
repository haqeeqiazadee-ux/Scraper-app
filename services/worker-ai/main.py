"""
AI Normalization Worker — main consumption loop.

Connects to the task queue (Redis or in-memory), polls for results on
the ``ai_normalization`` queue, and dispatches them to
:class:`AINormalizationWorker`.

Usage::

    python -m services.worker-ai.main

Environment variables:

    QUEUE_BACKEND      — ``redis`` or ``memory`` (default: ``memory``)
    REDIS_URL          — Redis connection string
    WORKER_CONCURRENCY — max concurrent tasks (default: 10)
    AI_LANE_QUEUE      — queue name (default: ``ai_normalization``)
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Any

from packages.core.queue_factory import create_queue, QueueType
from services.worker_ai.worker import AINormalizationWorker

logger = logging.getLogger(__name__)

QUEUE_NAME = os.environ.get("AI_LANE_QUEUE", "ai_normalization")
CONCURRENCY = int(os.environ.get("WORKER_CONCURRENCY", "10"))
POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT_SECONDS", "5"))


class AIWorkerRunner:
    """Manages the AI normalization worker consumption loop."""

    def __init__(
        self,
        queue: QueueType | None = None,
        worker: AINormalizationWorker | None = None,
        concurrency: int = CONCURRENCY,
        queue_name: str = QUEUE_NAME,
        poll_timeout: int = POLL_TIMEOUT,
    ) -> None:
        self._queue = queue or create_queue()
        self._worker = worker or AINormalizationWorker()
        self._concurrency = concurrency
        self._queue_name = queue_name
        self._poll_timeout = poll_timeout
        self._semaphore = asyncio.Semaphore(concurrency)
        self._running = True
        self._tasks: set[asyncio.Task[Any]] = set()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the consumption loop."""
        logger.info(
            "AI normalization worker starting",
            extra={
                "queue": self._queue_name,
                "concurrency": self._concurrency,
            },
        )
        self._install_signal_handlers()

        while self._running:
            try:
                await self._semaphore.acquire()
                if not self._running:
                    self._semaphore.release()
                    break

                message = await self._queue.dequeue(
                    self._queue_name, timeout_seconds=self._poll_timeout
                )

                if message is None:
                    self._semaphore.release()
                    continue

                task = asyncio.create_task(self._handle_message(message))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

            except asyncio.CancelledError:
                break
            except Exception:
                self._semaphore.release()
                logger.exception("Error in consumption loop")
                await asyncio.sleep(1)

        if self._tasks:
            logger.info("Waiting for %d in-flight tasks to complete", len(self._tasks))
            await asyncio.gather(*self._tasks, return_exceptions=True)

        await self._cleanup()

    async def stop(self) -> None:
        """Signal the loop to stop."""
        logger.info("AI normalization worker stopping")
        self._running = False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _handle_message(self, message: dict) -> None:
        """Process a single normalization message and ack/nack."""
        msg_id = message.pop("_msg_id", None)
        try:
            result = await self._worker.normalize(message)

            # AI normalization always produces a result; ack it.
            if msg_id:
                await self._queue.ack(self._queue_name, msg_id)

            logger.info(
                "Normalization complete",
                extra={
                    "task_id": result.get("task_id"),
                    "items": len(result.get("extracted_data", [])),
                    "confidence": result.get("confidence"),
                },
            )
        except Exception:
            logger.exception("Unhandled error during normalization")
            if msg_id:
                await self._queue.nack(self._queue_name, msg_id)
        finally:
            self._semaphore.release()

    async def _cleanup(self) -> None:
        """Clean up worker and queue resources."""
        await self._worker.close()
        if hasattr(self._queue, "close"):
            await self._queue.close()
        logger.info("AI normalization worker shut down cleanly")

    def _install_signal_handlers(self) -> None:
        """Install SIGTERM / SIGINT handlers for graceful shutdown."""
        loop = asyncio.get_running_loop()

        def _signal_handler() -> None:
            logger.info("Received shutdown signal")
            asyncio.ensure_future(self.stop())

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                pass


async def main() -> None:
    """Entry point."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    runner = AIWorkerRunner()
    await runner.start()


if __name__ == "__main__":
    asyncio.run(main())
