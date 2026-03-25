"""
Browser Lane Worker — intelligent browser-based scraping engine.

Pipeline: fetch page → wait for JS render → smart scroll → detect content →
          extract structured data → normalize → deduplicate

Designed to handle the hardest scraping targets:
- Amazon deal pages, product listings, search results
- JS-rendered SPAs (React, Next.js, Angular)
- Infinite scroll / lazy-loaded content
- Dynamic AJAX carousels and tab content
- Bot-detection pages (CAPTCHA detection + escalation signal)
"""

from __future__ import annotations

import logging
import time
from typing import Optional
from uuid import uuid4

from packages.connectors.browser_worker import PlaywrightBrowserWorker
from packages.core.ai_providers.deterministic import DeterministicProvider
from packages.core.dedup import DedupEngine
from packages.core.normalizer import Normalizer
from packages.core.interfaces import AIProvider, FetchRequest

logger = logging.getLogger(__name__)

# Common selectors that indicate page content has loaded.
# Ordered from most specific to most generic — first match wins.
_CONTENT_SELECTORS = [
    # Amazon-specific (deals, search, product pages)
    "[data-component-type='s-search-result']",     # Amazon search results
    ".s-result-item",                               # Amazon search items
    ".a-carousel-card",                             # Amazon carousels
    "[class*='DealCard']",                          # Amazon deal cards
    "[class*='GridCard']",                          # Amazon grid cards
    ".a-price",                                     # Amazon price elements (multiple = products)
    "[data-a-target*='deal']",                      # Amazon deal targets
    # Shopify / Generic e-commerce
    "[class*='ProductCard']",
    ".product-card", ".product-item", ".product-grid-item",
    "[data-testid='product']",
    ".collection-product", ".grid-product",
    # Social media
    "[data-testid='tweet']", "[data-testid='post']",
    "article[role='article']",
    # General dynamic content
    "[data-component-type]",
    "main [class*='grid'] > div:nth-child(3)",     # Wait for 3rd grid item (confirms content loaded)
    ".feed-item", ".listing",
]

# Selectors that indicate bot detection / CAPTCHA
_CAPTCHA_SELECTORS = [
    "#captchacharacters",           # Amazon CAPTCHA
    ".g-recaptcha",                 # reCAPTCHA
    "#challenge-running",           # Cloudflare challenge
    "[class*='captcha']",           # Generic
    "#px-captcha",                  # PerimeterX
    "iframe[src*='captcha']",       # Iframe CAPTCHA
]


class BrowserLaneWorker:
    """Intelligent browser worker that auto-detects content and scrolls smartly.

    Unlike a basic browser fetch, this worker:
    1. Waits for dynamic JS content to render (not just network idle)
    2. Auto-scrolls to trigger lazy loading (images, infinite scroll, carousels)
    3. Detects CAPTCHA/bot-detection and signals escalation
    4. Extracts multiple items from complex page layouts
    5. Normalizes and deduplicates results
    """

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
        self._normalizer = Normalizer()
        self._dedup = DedupEngine()

    async def process_task(self, task: dict) -> dict:
        """Process a browser extraction task with intelligent content detection.

        Always waits for JS content, scrolls to load lazy elements, and detects
        bot-protection. No manual flags needed — the worker figures it out.
        """
        url = task["url"]
        tenant_id = task.get("tenant_id", "default")
        task_id = task.get("task_id", str(uuid4()))
        run_id = str(uuid4())
        css_selectors = task.get("css_selectors")

        logger.info("Browser task starting", extra={"task_id": task_id, "url": url})
        start_time = time.time()

        # ── Step 1: Fetch page via Playwright ──
        request = FetchRequest(
            url=url,
            timeout_ms=task.get("timeout_ms", 45000),
        )

        response = await self._browser_worker.fetch(request)

        if not response.ok:
            elapsed = int((time.time() - start_time) * 1000)
            logger.warning("Browser fetch failed", extra={
                "task_id": task_id, "url": url,
                "status_code": response.status_code, "error": response.error,
            })
            return self._fail_result(task_id, run_id, tenant_id, url, elapsed,
                                     response.status_code, response.error)

        page = self._browser_worker._page
        if not page:
            html = response.html or response.text
            return await self._extract_and_return(
                task_id, run_id, tenant_id, url, html, start_time,
                response, css_selectors, scrolled=False, waited=False,
            )

        # ── Step 2: Check for CAPTCHA / bot detection ──
        captcha_detected = False
        for selector in _CAPTCHA_SELECTORS:
            try:
                el = await page.query_selector(selector)
                if el:
                    captcha_detected = True
                    logger.warning("CAPTCHA/bot-detection detected",
                                   extra={"task_id": task_id, "selector": selector})
                    break
            except Exception:
                pass

        if captcha_detected:
            elapsed = int((time.time() - start_time) * 1000)
            return {
                "task_id": task_id, "run_id": run_id, "tenant_id": tenant_id,
                "url": url, "lane": "browser", "connector": "playwright_browser",
                "status": "failed", "status_code": response.status_code,
                "error": "CAPTCHA/bot-detection detected — escalate to hard-target lane",
                "duration_ms": elapsed, "extracted_data": [], "item_count": 0,
                "should_escalate": True,
            }

        # ── Step 3: Wait for dynamic JS content to render ──
        waited = False
        # Try explicit wait_selector from task config first
        if task.get("wait_selector"):
            try:
                await page.wait_for_selector(
                    task["wait_selector"],
                    timeout=task.get("wait_timeout_ms", 8000),
                )
                waited = True
            except Exception:
                logger.debug("Explicit wait_selector not found: %s", task["wait_selector"])

        # Auto-detect content by trying common selectors
        if not waited:
            for selector in _CONTENT_SELECTORS:
                try:
                    await page.wait_for_selector(selector, timeout=8000)
                    waited = True
                    logger.info("Content detected via: %s", selector,
                                extra={"task_id": task_id})
                    break
                except Exception:
                    continue

        # Always give JS an extra moment to finish rendering after first element appears
        # Amazon, React SPAs, etc. often load the container first, then fill data
        try:
            await page.wait_for_timeout(3000)
        except Exception:
            pass

        # ── Step 4: Smart scroll to load lazy content ──
        scrolled = False
        scroll_explicitly_disabled = task.get("scroll") is False
        max_scrolls = task.get("max_scrolls", 5)  # Default 5 scrolls, not 50

        if not scroll_explicitly_disabled:
            try:
                prev_height = await page.evaluate("document.body.scrollHeight")
                scroll_count = 0

                for _ in range(max_scrolls):
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await page.wait_for_timeout(1500)
                    new_height = await page.evaluate("document.body.scrollHeight")
                    scroll_count += 1

                    if new_height == prev_height:
                        # No new content loaded — stop scrolling
                        break
                    prev_height = new_height

                if scroll_count > 0:
                    scrolled = True
                    logger.info("Scrolled %d times (page height grew)",
                                scroll_count, extra={"task_id": task_id})

                # Scroll back to top so full page is in DOM
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(500)

            except Exception as scroll_err:
                logger.debug("Scroll failed: %s", scroll_err)

        # ── Step 5: Get final rendered HTML ──
        try:
            html = await page.content()
        except Exception:
            html = response.html or response.text

        # ── Step 6: Extract, normalize, deduplicate ──
        return await self._extract_and_return(
            task_id, run_id, tenant_id, url, html, start_time,
            response, css_selectors, scrolled, waited,
        )

    async def _extract_and_return(
        self, task_id: str, run_id: str, tenant_id: str, url: str,
        html: str, start_time: float, response, css_selectors,
        scrolled: bool, waited: bool,
    ) -> dict:
        """Extract data from HTML, normalize, deduplicate, and return result dict."""

        # Extract
        extract_kwargs: dict = {}
        if css_selectors and isinstance(self._ai, DeterministicProvider):
            extract_kwargs["css_selectors"] = css_selectors

        extracted_data = await self._ai.extract(html, url, **extract_kwargs)

        # Normalize
        normalization_applied = False
        if extracted_data:
            extracted_data = self._normalizer.normalize_batch(extracted_data)
            normalization_applied = True

        # Deduplicate
        dedup_applied = False
        original_count = len(extracted_data)
        if extracted_data:
            extracted_data = self._dedup.deduplicate(extracted_data)
            dedup_applied = len(extracted_data) < original_count

        # Confidence
        confidence = 0.0
        if extracted_data:
            total_fields = sum(len(item) for item in extracted_data)
            filled_fields = sum(
                1 for item in extracted_data
                for v in item.values()
                if v and str(v).strip()
            )
            confidence = filled_fields / total_fields if total_fields > 0 else 0.0

        elapsed = int((time.time() - start_time) * 1000)
        method = "deterministic" if isinstance(self._ai, DeterministicProvider) else "ai"

        logger.info("Browser task completed", extra={
            "task_id": task_id, "url": url,
            "items": len(extracted_data), "confidence": f"{confidence:.2f}",
            "duration_ms": elapsed, "scrolled": scrolled, "waited": waited,
            "html_size": len(html),
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
            "bytes_downloaded": len(response.body) if response.body else len(html),
            "extracted_data": extracted_data,
            "item_count": len(extracted_data),
            "confidence": round(confidence, 4),
            "extraction_method": method,
            "normalization_applied": normalization_applied,
            "dedup_applied": dedup_applied,
            "scrolled": scrolled,
            "waited_for_selector": waited,
            # Escalate if no data, or suspiciously few items for what looks like a listing page
            "should_escalate": len(extracted_data) == 0 or (len(extracted_data) <= 2 and confidence < 0.5),
        }

    @staticmethod
    def _fail_result(task_id, run_id, tenant_id, url, elapsed, status_code, error):
        return {
            "task_id": task_id, "run_id": run_id, "tenant_id": tenant_id,
            "url": url, "lane": "browser", "connector": "playwright_browser",
            "status": "failed", "status_code": status_code,
            "error": error or f"Browser fetch failed (status {status_code})",
            "duration_ms": elapsed, "extracted_data": [], "item_count": 0,
            "should_escalate": True,
        }

    async def close(self) -> None:
        """Clean up browser resources."""
        await self._browser_worker.close()
