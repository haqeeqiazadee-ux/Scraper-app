"""
Hard-Target Lane Worker — main consumption loop.

Connects to the task queue (Redis or in-memory), polls for tasks on
the ``hard_target`` queue, and dispatches them to :class:`HardTargetLaneWorker`.

Usage::

    python -m services.worker_hard_target.main

Environment variables:

    QUEUE_BACKEND   — ``redis`` or ``memory`` (default: ``memory``)
    REDIS_URL       — Redis connection string
    WORKER_CONCURRENCY — max concurrent tasks (default: 1)
    HARD_TARGET_QUEUE — queue name (default: ``hard_target``)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from typing import Any

from packages.core.queue_factory import create_queue, QueueType

logger = logging.getLogger(__name__)

QUEUE_NAME = os.environ.get("HARD_TARGET_QUEUE", "hard_target")
CONCURRENCY = int(os.environ.get("WORKER_CONCURRENCY", "1"))
POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT_SECONDS", "10"))


class HardTargetWorkerRunner:
    """Manages the hard-target worker consumption loop with graceful shutdown."""

    def __init__(
        self,
        queue: QueueType | None = None,
        concurrency: int = CONCURRENCY,
        queue_name: str = QUEUE_NAME,
        poll_timeout: int = POLL_TIMEOUT,
    ) -> None:
        self._queue = queue or create_queue()
        self._concurrency = concurrency
        self._queue_name = queue_name
        self._poll_timeout = poll_timeout
        self._running = False
        self._semaphore = asyncio.Semaphore(concurrency)
        self._worker = None

    async def _ensure_worker(self) -> Any:
        """Lazily create the worker to avoid import-time Playwright init."""
        if self._worker is None:
            from services.worker_hard_target.worker import HardTargetLaneWorker
            from packages.connectors.captcha_adapter import CaptchaAdapter
            from packages.connectors.proxy_adapter import ProxyAdapter, IPRoyalProxyProvider

            # Build CAPTCHA adapter from env
            captcha = CaptchaAdapter.from_config(
                capsolver_key=os.environ.get("CAPSOLVER_API_KEY"),
                two_captcha_key=os.environ.get("TWO_CAPTCHA_API_KEY"),
                anti_captcha_key=os.environ.get("ANTI_CAPTCHA_API_KEY"),
                capmonster_key=os.environ.get("CAPMONSTER_API_KEY"),
                nopecha_key=os.environ.get("NOPECHA_API_KEY"),
            )

            # Build proxy adapter from env (IPRoyal if key present)
            proxy = ProxyAdapter()
            iproyal_key = os.environ.get("IPROYAL_API_KEY")
            if iproyal_key:
                provider = IPRoyalProxyProvider(
                    api_key=iproyal_key,
                    country=os.environ.get("IPROYAL_COUNTRY", ""),
                    num_sessions=int(os.environ.get("IPROYAL_SESSIONS", "10")),
                )
                proxy.set_provider(provider)
                await proxy.refresh()

            self._worker = HardTargetLaneWorker(
                proxy_adapter=proxy,
                captcha_adapter=captcha,
            )
        return self._worker

    async def start(self) -> None:
        """Start the consumption loop."""
        self._running = True
        self._install_signal_handlers()
        logger.info(
            "Hard-target worker starting",
            extra={"queue": self._queue_name, "concurrency": self._concurrency},
        )
        try:
            while self._running:
                await self._semaphore.acquire()
                if not self._running:
                    self._semaphore.release()
                    break
                try:
                    msg = await self._queue.dequeue(
                        self._queue_name, timeout=self._poll_timeout
                    )
                except Exception:
                    self._semaphore.release()
                    if not self._running:
                        break
                    logger.exception("Queue dequeue error")
                    await asyncio.sleep(1)
                    continue

                if msg is None:
                    self._semaphore.release()
                    continue

                asyncio.create_task(self._process(msg))
        finally:
            await self._cleanup()

    async def stop(self) -> None:
        """Signal the loop to stop after current tasks finish."""
        logger.info("Hard-target worker stopping")
        self._running = False

    async def _process(self, msg: dict) -> None:
        """Process a single task from the queue."""
        msg_id: str | None = msg.get("_msg_id")
        try:
            task_data: dict[str, Any]
            if isinstance(msg.get("data"), str):
                task_data = json.loads(msg["data"])
            elif isinstance(msg.get("data"), dict):
                task_data = msg["data"]
            else:
                task_data = msg

            worker = await self._ensure_worker()
            result = await worker.process_task(task_data)

            if msg_id:
                await self._queue.ack(self._queue_name, msg_id)

            status = result.get("status", "unknown")
            logger.info(
                "Hard-target task processed",
                extra={
                    "task_id": task_data.get("task_id"),
                    "status": status,
                    "duration_ms": result.get("duration_ms"),
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
        if self._worker is not None:
            await self._worker.close()
        if hasattr(self._queue, "close"):
            await self._queue.close()
        logger.info("Hard-target worker shut down cleanly")

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
    runner = HardTargetWorkerRunner()
    await runner.start()


if __name__ == "__main__":
    asyncio.run(main())
