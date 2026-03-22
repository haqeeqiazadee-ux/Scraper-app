"""
Hard-Target Lane Worker — processes hard-target extraction tasks from the queue.

Pipeline: dequeue task -> stealth browser fetch -> optional scroll/wait ->
           extract data -> normalize -> store result

Uses HardTargetWorker connector for sites with aggressive anti-bot protection
(Cloudflare, Akamai, PerimeterX, DataDome, etc.).
"""

from __future__ import annotations

import logging
import time
from typing import Optional
from uuid import uuid4

from packages.connectors.captcha_adapter import CaptchaAdapter
from packages.connectors.hard_target_worker import HardTargetWorker
from packages.connectors.proxy_adapter import ProxyAdapter
from packages.core.ai_providers.deterministic import DeterministicProvider
from packages.core.interfaces import AIProvider, FetchRequest

logger = logging.getLogger(__name__)


class HardTargetLaneWorker:
    """Worker that processes hard-target lane tasks.

    Wraps the HardTargetWorker connector and provides a task-processing
    pipeline that creates Run records, stores Results, and handles errors
    with detailed failure reasons.
    """

    def __init__(
        self,
        ai_provider: Optional[AIProvider] = None,
        proxy_adapter: Optional[ProxyAdapter] = None,
        captcha_adapter: Optional[CaptchaAdapter] = None,
        headless: bool = True,
        max_retries: int = 3,
    ) -> None:
        self._hard_target = HardTargetWorker(
            proxy_adapter=proxy_adapter,
            captcha_adapter=captcha_adapter,
            headless=headless,
            max_retries=max_retries,
        )
        self._ai = ai_provider or DeterministicProvider()

    async def process_task(self, task: dict) -> dict:
        """
        Process a single hard-target extraction task.

        Args:
            task: Dict with at least 'url' and 'tenant_id' keys.
                  Optional keys:
                    - wait_selector (str): CSS selector to wait for before extraction
                    - wait_selector_timeout_ms (int): timeout for wait_selector
                    - wait_until (str): Playwright wait strategy (default "networkidle")
                    - timeout_ms (int): page load timeout (default 60000)

        Returns:
            Dict with extraction results, run metadata, and status.
        """
        url = task["url"]
        tenant_id = task.get("tenant_id", "default")
        task_id = task.get("task_id", str(uuid4()))
        run_id = str(uuid4())

        logger.info("Processing hard-target task", extra={"task_id": task_id, "url": url})
        start_time = time.time()

        # Build metadata for the HardTargetWorker
        metadata: dict = {}
        if task.get("wait_selector"):
            metadata["wait_selector"] = task["wait_selector"]
        if task.get("wait_selector_timeout_ms"):
            metadata["wait_selector_timeout_ms"] = task["wait_selector_timeout_ms"]
        if task.get("wait_until"):
            metadata["wait_until"] = task["wait_until"]

        # Step 1: Stealth fetch
        request = FetchRequest(
            url=url,
            timeout_ms=task.get("timeout_ms", 60000),
            metadata=metadata,
        )

        response = await self._hard_target.fetch(request)

        if not response.ok:
            elapsed = int((time.time() - start_time) * 1000)

            # Determine detailed failure reason
            failure_reason = self._classify_failure(response)

            logger.warning("Hard-target fetch failed", extra={
                "task_id": task_id, "url": url,
                "status_code": response.status_code,
                "error": response.error,
                "failure_reason": failure_reason,
            })
            return {
                "task_id": task_id,
                "run_id": run_id,
                "tenant_id": tenant_id,
                "lane": "hard_target",
                "connector": "hard_target_worker",
                "status": "failed",
                "status_code": response.status_code,
                "error": response.error or f"Hard-target fetch failed (status {response.status_code})",
                "failure_reason": failure_reason,
                "duration_ms": elapsed,
                "extracted_data": [],
                "item_count": 0,
                "should_escalate": False,  # Hard-target is the last lane
            }

        # Step 2: Extract data from HTML
        html = response.html or response.text
        extracted_data = await self._ai.extract(html, url)

        # Step 3: Calculate confidence
        confidence = 0.0
        if extracted_data:
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

        logger.info("Hard-target task completed", extra={
            "task_id": task_id, "url": url,
            "items": len(extracted_data), "confidence": f"{confidence:.2f}",
            "duration_ms": elapsed,
        })

        return {
            "task_id": task_id,
            "run_id": run_id,
            "tenant_id": tenant_id,
            "url": url,
            "lane": "hard_target",
            "connector": "hard_target_worker",
            "status": "success",
            "status_code": response.status_code,
            "duration_ms": elapsed,
            "bytes_downloaded": len(response.body),
            "extracted_data": extracted_data,
            "item_count": len(extracted_data),
            "confidence": round(confidence, 4),
            "extraction_method": extraction_method,
            "should_escalate": False,  # Hard-target is the last lane
        }

    def _classify_failure(self, response: object) -> str:
        """Classify the failure reason from the response for diagnostics."""
        error = getattr(response, "error", "") or ""
        status = getattr(response, "status_code", 0)
        error_lower = error.lower()

        if "captcha" in error_lower:
            return "captcha_unsolved"
        if status == 403:
            return "access_denied"
        if status == 429:
            return "rate_limited"
        if status == 503:
            return "service_unavailable"
        if "timeout" in error_lower:
            return "timeout"
        if "connection" in error_lower or "network" in error_lower:
            return "network_error"
        if "retries exhausted" in error_lower:
            return "retries_exhausted"
        return "unknown"

    async def close(self) -> None:
        """Clean up all resources."""
        await self._hard_target.close()
