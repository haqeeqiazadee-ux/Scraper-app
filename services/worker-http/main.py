"""
HTTP Lane Worker — main consumption loop.

Connects to the task queue (Redis or in-memory), polls for tasks on
the ``http_lane`` queue, and dispatches them to :class:`HttpWorker`.

Usage::

    python -m services.worker-http.main

Environment variables:

    QUEUE_BACKEND   — ``redis`` or ``memory`` (default: ``memory``)
    REDIS_URL       — Redis connection string
    WORKER_CONCURRENCY — max concurrent tasks (default: 5)
    HTTP_LANE_QUEUE — queue name (default: ``http_lane``)
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Any

from packages.core.queue_factory import create_queue, QueueType
from services.worker_http.worker import HttpWorker

logger = logging.getLogger(__name__)

QUEUE_NAME = os.environ.get("HTTP_LANE_QUEUE", "http_lane")
CONCURRENCY = int(os.environ.get("WORKER_CONCURRENCY", "5"))
POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT_SECONDS", "5"))


class HttpWorkerRunner:
    """Manages the HTTP worker consumption loop with graceful shutdown."""

    def __init__(
        self,
        queue: QueueType | None = None,
        worker: HttpWorker | None = None,
        concurrency: int = CONCURRENCY,
        queue_name: str = QUEUE_NAME,
        poll_timeout: int = POLL_TIMEOUT,
    ) -> None:
        self._queue = queue or create_queue()
        self._worker = worker or HttpWorker()
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
            "HTTP worker starting",
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

        # Wait for in-flight tasks to finish
        if self._tasks:
            logger.info("Waiting for %d in-flight tasks to complete", len(self._tasks))
            await asyncio.gather(*self._tasks, return_exceptions=True)

        await self._cleanup()

    async def stop(self) -> None:
        """Signal the loop to stop."""
        logger.info("HTTP worker stopping")
        self._running = False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _handle_message(self, message: dict) -> None:
        """Process a single message and ack/nack."""
        msg_id = message.pop("_msg_id", None)
        try:
            result = await self._worker.process_task(message)

            if result.get("status") == "success":
                if msg_id:
                    await self._queue.ack(self._queue_name, msg_id)
                logger.info(
                    "Task succeeded",
                    extra={
                        "task_id": result.get("task_id"),
                        "items": result.get("item_count", 0),
                    },
                )
            else:
                if msg_id:
                    await self._queue.nack(self._queue_name, msg_id)
                logger.warning(
                    "Task failed, nacked",
                    extra={
                        "task_id": result.get("task_id"),
                        "error": result.get("error"),
                    },
                )
        except Exception:
            logger.exception("Unhandled error processing task")
            if msg_id:
                await self._queue.nack(self._queue_name, msg_id)
        finally:
            self._semaphore.release()

    async def _cleanup(self) -> None:
        """Clean up worker and queue resources."""
        await self._worker.close()
        if hasattr(self._queue, "close"):
            await self._queue.close()
        logger.info("HTTP worker shut down cleanly")

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
                # Windows doesn't support add_signal_handler
                pass


async def main() -> None:
    """Entry point."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    runner = HttpWorkerRunner()
    await runner.start()


if __name__ == "__main__":
    asyncio.run(main())
