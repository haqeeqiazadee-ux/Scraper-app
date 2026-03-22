"""
Browser Lane Worker — processes browser extraction tasks from the queue.

Pipeline: dequeue task -> browser fetch -> optional scroll/wait -> extract data -> normalize -> store result

Uses PlaywrightBrowserWorker for JS-rendered pages that require a full browser
environment (SPAs, infinite scroll, dynamic AJAX content).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional
from uuid import uuid4

from packages.connectors.browser_worker import PlaywrightBrowserWorker
from packages.core.ai_providers.deterministic import DeterministicProvider
from packages.core.interfaces import AIProvider, FetchRequest

logger = logging.getLogger(__name__)


class BrowserLaneWorker:
    """Worker that processes browser lane tasks using Playwright."""

    def __init__(
        self,
        ai_provider: Optional[AIProvider] = None,
        proxy: Optional[str] = None,
        headless: bool = True,
    ) -> None:
        self._browser_worker = PlaywrightBrowserWorker(
            headless=headless,
            proxy=proxy,
        )
        self._ai = ai_provider or DeterministicProvider()

    async def process_task(self, task: dict) -> dict:
        """
        Process a single browser extraction task.

        Args:
            task: Dict with at least 'url' and 'tenant_id' keys.
                  Optional keys:
                    - scroll (bool): scroll to bottom for infinite-scroll pages
                    - max_scrolls (int): maximum scroll iterations (default 50)
                    - wait_selector (str): CSS selector to wait for before extraction
                    - wait_timeout_ms (int): timeout for wait_selector (default 5000)
                    - timeout_ms (int): page load timeout (default 30000)

        Returns:
            Dict with extraction results, run metadata, and status.
        """
        url = task["url"]
        tenant_id = task.get("tenant_id", "default")
        task_id = task.get("task_id", str(uuid4()))
        run_id = str(uuid4())

        logger.info("Processing browser task", extra={"task_id": task_id, "url": url})
        start_time = time.time()

        # Step 1: Fetch the page via browser
        request = FetchRequest(
            url=url,
            timeout_ms=task.get("timeout_ms", 30000),
        )

        response = await self._browser_worker.fetch(request)

        if not response.ok:
            elapsed = int((time.time() - start_time) * 1000)
            logger.warning("Browser fetch failed", extra={
                "task_id": task_id, "url": url,
                "status_code": response.status_code, "error": response.error,
            })
            return {
                "task_id": task_id,
                "run_id": run_id,
                "tenant_id": tenant_id,
                "lane": "browser",
                "connector": "playwright_browser",
                "status": "failed",
                "status_code": response.status_code,
                "error": response.error or f"Browser fetch failed (status {response.status_code})",
                "duration_ms": elapsed,
                "extracted_data": [],
                "item_count": 0,
                "should_escalate": True,
            }

        # Step 2: Optional — scroll to bottom for infinite-scroll pages
        scrolled = False
        if task.get("scroll", False):
            max_scrolls = task.get("max_scrolls", 50)
            await self._browser_worker.scroll_to_bottom(max_scrolls=max_scrolls)
            scrolled = True

        # Step 3: Optional — wait for a specific CSS selector (JS-rendered content)
        waited_for_selector = False
        if task.get("wait_selector"):
            wait_timeout = task.get("wait_timeout_ms", 5000)
            selector_found = await self._browser_worker.wait_for_selector(
                task["wait_selector"], timeout_ms=wait_timeout,
            )
            waited_for_selector = selector_found

        # Step 4: Get final page HTML (after scroll/wait mutations)
        if scrolled or waited_for_selector:
            html = await self._browser_worker.get_page_html()
            # Fall back to initial response HTML if page ref was lost
            if not html:
                html = response.html or response.text
        else:
            html = response.html or response.text

        # Step 5: Extract data from HTML
        extracted_data = await self._ai.extract(html, url)

        # Step 6: Calculate confidence
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

        logger.info("Browser task completed", extra={
            "task_id": task_id, "url": url,
            "items": len(extracted_data), "confidence": f"{confidence:.2f}",
            "duration_ms": elapsed, "scrolled": scrolled,
            "waited_for_selector": waited_for_selector,
        })

        return {
            "task_id": task_id,
            "run_id": run_id,
            "tenant_id": tenant_id,
            "url": url,
            "lane": "browser",
            "connector": "playwright_browser",
            "status": "success",
            "status_code": response.status_code,
            "duration_ms": elapsed,
            "bytes_downloaded": len(response.body),
            "extracted_data": extracted_data,
            "item_count": len(extracted_data),
            "confidence": round(confidence, 4),
            "extraction_method": extraction_method,
            "scrolled": scrolled,
            "waited_for_selector": waited_for_selector,
            "should_escalate": len(extracted_data) == 0,
        }

    async def close(self) -> None:
        """Clean up browser resources."""
        await self._browser_worker.close()
