"""
HTTP Lane Worker — processes HTTP extraction tasks from the queue.

Pipeline: dequeue task → HTTP fetch → extract data → normalize → store result
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional
from uuid import uuid4

from packages.connectors.http_collector import HttpCollector
from packages.core.ai_providers.deterministic import DeterministicProvider
from packages.core.interfaces import FetchRequest, AIProvider

logger = logging.getLogger(__name__)


class HttpWorker:
    """Worker that processes HTTP lane tasks."""

    def __init__(
        self,
        ai_provider: Optional[AIProvider] = None,
        proxy: Optional[str] = None,
    ) -> None:
        self._collector = HttpCollector(proxy=proxy)
        self._ai = ai_provider or DeterministicProvider()

    async def process_task(self, task: dict) -> dict:
        """
        Process a single HTTP extraction task.

        Args:
            task: Dict with at least 'url' and 'tenant_id' keys.

        Returns:
            Dict with extraction results, run metadata, and status.
        """
        url = task["url"]
        tenant_id = task.get("tenant_id", "default")
        task_id = task.get("task_id", str(uuid4()))
        run_id = str(uuid4())

        logger.info("Processing HTTP task", extra={"task_id": task_id, "url": url})
        start_time = time.time()

        # Step 1: Fetch the page
        request = FetchRequest(
            url=url,
            timeout_ms=task.get("timeout_ms", 30000),
        )

        response = await self._collector.fetch(request)

        if not response.ok:
            elapsed = int((time.time() - start_time) * 1000)
            logger.warning("HTTP fetch failed", extra={
                "task_id": task_id, "url": url,
                "status_code": response.status_code, "error": response.error,
            })
            return {
                "task_id": task_id,
                "run_id": run_id,
                "tenant_id": tenant_id,
                "lane": "http",
                "connector": "http_collector",
                "status": "failed",
                "status_code": response.status_code,
                "error": response.error or f"HTTP {response.status_code}",
                "duration_ms": elapsed,
                "extracted_data": [],
                "item_count": 0,
                "should_escalate": True,
            }

        # Step 2: Extract data from HTML
        html = response.html or response.text
        extracted_data = await self._ai.extract(html, url)

        # Step 3: Calculate confidence
        confidence = 0.0
        if extracted_data:
            # Score based on how many fields were extracted
            total_fields = 0
            filled_fields = 0
            for item in extracted_data:
                for key, value in item.items():
                    total_fields += 1
                    if value and str(value).strip():
                        filled_fields += 1
            confidence = filled_fields / total_fields if total_fields > 0 else 0.0

        elapsed = int((time.time() - start_time) * 1000)
        extraction_method = "deterministic" if isinstance(self._ai, DeterministicProvider) else "ai"

        logger.info("HTTP task completed", extra={
            "task_id": task_id, "url": url,
            "items": len(extracted_data), "confidence": f"{confidence:.2f}",
            "duration_ms": elapsed,
        })

        return {
            "task_id": task_id,
            "run_id": run_id,
            "tenant_id": tenant_id,
            "url": url,
            "lane": "http",
            "connector": "http_collector",
            "status": "success",
            "status_code": response.status_code,
            "duration_ms": elapsed,
            "bytes_downloaded": len(response.body),
            "extracted_data": extracted_data,
            "item_count": len(extracted_data),
            "confidence": round(confidence, 4),
            "extraction_method": extraction_method,
            "should_escalate": len(extracted_data) == 0,
        }

    async def close(self) -> None:
        """Clean up resources."""
        await self._collector.close()
