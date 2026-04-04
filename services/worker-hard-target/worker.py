"""
Hard-Target Lane Worker — stealth browser scraping with intelligent extraction.

Pipeline: stealth fetch → wait for JS content → smart scroll → detect CAPTCHA →
          extract data → normalize → deduplicate

Uses HardTargetWorker connector with fingerprint randomization, stealth flags,
and optional proxy/CAPTCHA solving for sites with aggressive anti-bot protection.
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
from packages.core.dedup import DedupEngine
from packages.core.normalizer import Normalizer
from packages.core.interfaces import AIProvider, FetchRequest
from packages.core.markdown_converter import MarkdownConverter

logger = logging.getLogger(__name__)

# Content selectors — same as browser worker for consistency
_CONTENT_SELECTORS = [
    "[data-component-type='s-search-result']",
    ".s-result-item",
    ".a-carousel-card",
    "[class*='DealCard']",
    "[class*='GridCard']",
    ".a-price",
    "[data-a-target*='deal']",
    "[class*='ProductCard']",
    ".product-card", ".product-item",
    "[data-testid='product']",
    "[data-testid='tweet']",
    "article[role='article']",
    "[data-component-type]",
    "main [class*='grid'] > div:nth-child(3)",
    ".feed-item", ".listing",
]

_CAPTCHA_SELECTORS = [
    "#captchacharacters",
    ".g-recaptcha",
    "#challenge-running",
    "[class*='captcha']",
    "#px-captcha",
    "iframe[src*='captcha']",
]


class HardTargetLaneWorker:
    """Stealth browser worker with intelligent content detection.

    Extends HardTargetWorker with:
    - Smart waiting for JS-rendered content
    - Auto-scrolling for lazy-loaded elements
    - CAPTCHA detection
    - Normalization and deduplication
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
        self._normalizer = Normalizer()
        self._dedup = DedupEngine()
        self._converter = MarkdownConverter()

    async def process_task(self, task: dict) -> dict:
        """Process a hard-target extraction task with intelligent content detection."""
        url = task["url"]
        tenant_id = task.get("tenant_id", "default")
        task_id = task.get("task_id", str(uuid4()))
        run_id = str(uuid4())
        css_selectors = task.get("css_selectors")

        logger.info("Hard-target task starting", extra={"task_id": task_id, "url": url})
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
            failure_reason = self._classify_failure(response)
            logger.warning("Hard-target fetch failed", extra={
                "task_id": task_id, "url": url,
                "status_code": response.status_code,
                "error": response.error,
                "failure_reason": failure_reason,
            })
            return {
                "task_id": task_id, "run_id": run_id, "tenant_id": tenant_id,
                "url": url, "lane": "hard_target", "connector": "hard_target_worker",
                "status": "failed", "status_code": response.status_code,
                "error": response.error or f"Hard-target fetch failed (status {response.status_code})",
                "failure_reason": failure_reason,
                "duration_ms": elapsed, "extracted_data": [], "item_count": 0,
                "should_escalate": False,
            }

        # Step 2: Use rendered HTML from response
        # CAPTCHA detection, JS wait, scroll, and content rendering are now
        # handled inside HardTargetWorker.fetch() with full behavioral simulation
        # (warm-up navigation, Bezier mouse curves, idle jitter, human scroll).
        html = response.html or response.text

        # Step 3: Extract data
        extract_kwargs: dict = {}
        if css_selectors and isinstance(self._ai, DeterministicProvider):
            extract_kwargs["css_selectors"] = css_selectors

        extracted_data = await self._ai.extract(html, url, **extract_kwargs)

        # Step 4: Normalize
        normalization_applied = False
        if extracted_data:
            extracted_data = self._normalizer.normalize_batch(extracted_data)
            normalization_applied = True

        # Step 5: Deduplicate
        dedup_applied = False
        original_count = len(extracted_data)
        if extracted_data:
            extracted_data = self._dedup.deduplicate(extracted_data)
            dedup_applied = len(extracted_data) < original_count

        # Step 6: Confidence (data quality, not just field coverage)
        confidence = 0.0
        if extracted_data:
            item_scores = []
            for item in extracted_data:
                score = 0.0
                if item.get("name") and len(str(item["name"]).strip()) > 2:
                    score += 0.3
                if item.get("price"):
                    score += 0.3
                if item.get("image_url"):
                    score += 0.15
                if item.get("product_url") and item["product_url"] != url:
                    score += 0.1
                if item.get("currency"):
                    score += 0.05
                if item.get("rating"):
                    score += 0.05
                if item.get("brand"):
                    score += 0.025
                if item.get("sku"):
                    score += 0.025
                item_scores.append(min(score, 1.0))
            confidence = sum(item_scores) / len(item_scores) if item_scores else 0.0

        # Output format conversion (markdown, etc.)
        output_format = task.get("output_format", "json")
        converted_content = None
        estimated_tokens = None
        if output_format != "json" and html:
            conversion = self._converter.convert(html, url, output_format=output_format)
            converted_content = conversion.content
            estimated_tokens = conversion.estimated_tokens

        elapsed = int((time.time() - start_time) * 1000)
        method = "deterministic" if isinstance(self._ai, DeterministicProvider) else "ai"

        logger.info("Hard-target task completed", extra={
            "task_id": task_id, "url": url,
            "items": len(extracted_data), "confidence": f"{confidence:.2f}",
            "duration_ms": elapsed,
        })

        result = {
            "task_id": task_id, "run_id": run_id, "tenant_id": tenant_id,
            "url": url, "lane": "hard_target", "connector": "hard_target_worker",
            "status": "success", "status_code": response.status_code,
            "duration_ms": elapsed,
            "bytes_downloaded": len(response.body) if response.body else len(html),
            "extracted_data": extracted_data,
            "item_count": len(extracted_data),
            "confidence": round(confidence, 4),
            "extraction_method": method,
            "normalization_applied": normalization_applied,
            "dedup_applied": dedup_applied,
            "should_escalate": False,
            "output_format": output_format,
        }
        if converted_content is not None:
            result["converted_content"] = converted_content
            result["estimated_tokens"] = estimated_tokens
        return result

    def _classify_failure(self, response: object) -> str:
        """Classify the failure reason from the response."""
        error = getattr(response, "error", "") or ""
        status = getattr(response, "status_code", 0)
        error_lower = error.lower()

        if "captcha" in error_lower:
            return "captcha_detected"
        elif "timeout" in error_lower:
            return "timeout"
        elif status == 403:
            return "access_denied"
        elif status == 429:
            return "rate_limited"
        elif status >= 500:
            return "server_error"
        elif "connection" in error_lower or "network" in error_lower:
            return "network_error"
        else:
            return "unknown"

    async def close(self) -> None:
        """Clean up resources."""
        await self._hard_target.close()
