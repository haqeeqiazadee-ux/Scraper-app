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
from packages.core.markdown_converter import MarkdownConverter

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
        self._converter = MarkdownConverter()

    async def _smart_wait(self, page, task_id: str, timeout_ms: int = 15000) -> bool:
        """Wait intelligently for dynamic content to finish loading.

        Instead of fixed timeout, checks for:
        1. Network idle (no pending XHR/fetch for 2 seconds)
        2. DOM stability (no new nodes for 1.5 seconds)
        3. Specific element appearance (from task config or auto-detected)

        Returns True if content appears stable, False if timed out.
        """
        # Try network idle first
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout_ms)
            return True
        except Exception:
            pass

        # Fallback: DOM mutation observer
        # Inject JS that resolves when no DOM mutations for 1.5 seconds
        try:
            await page.evaluate("""
                () => new Promise((resolve) => {
                    let timer;
                    const observer = new MutationObserver(() => {
                        clearTimeout(timer);
                        timer = setTimeout(() => {
                            observer.disconnect();
                            resolve(true);
                        }, 1500);
                    });
                    observer.observe(document.body, { childList: true, subtree: true });
                    timer = setTimeout(() => {
                        observer.disconnect();
                        resolve(false);
                    }, %d);
                })
            """ % timeout_ms)
            return True
        except Exception:
            return False

    async def _extract_shadow_dom(self, page) -> str:
        """Extract HTML content from shadow DOM roots.

        Web Components use shadow DOM, which is invisible to regular DOM queries.
        This method opens shadow roots and extracts their content.
        """
        shadow_html = await page.evaluate("""
            () => {
                function extractShadowDom(root) {
                    let html = '';
                    const shadowHosts = root.querySelectorAll('*');
                    for (const el of shadowHosts) {
                        if (el.shadowRoot) {
                            html += el.shadowRoot.innerHTML;
                            html += extractShadowDom(el.shadowRoot);
                        }
                    }
                    return html;
                }
                return extractShadowDom(document);
            }
        """)
        return shadow_html or ""

    async def _trigger_lazy_load(self, page) -> int:
        """Scroll through page to trigger lazy-loaded images and content.

        Returns number of new images that loaded.
        """
        return await page.evaluate("""
            () => {
                // Trigger IntersectionObserver-based lazy loading
                const images = document.querySelectorAll('img[data-src], img[loading="lazy"], img[data-lazy]');
                let count = 0;
                images.forEach(img => {
                    if (img.dataset.src && !img.src.includes(img.dataset.src)) {
                        img.src = img.dataset.src;
                        count++;
                    }
                });
                return count;
            }
        """)

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
                task=task,
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

        # Smart wait: intelligently wait for dynamic content instead of fixed timeout
        await self._smart_wait(page, task_id)

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

        # ── Step 4b: Trigger lazy loading and extract shadow DOM ──
        # Trigger lazy loading
        lazy_count = await self._trigger_lazy_load(page)
        if lazy_count > 0:
            logger.info("Triggered %d lazy-loaded images", lazy_count, extra={"task_id": task_id})

        # Extract shadow DOM content
        shadow_html = await self._extract_shadow_dom(page)

        # ── Step 5: Get final rendered HTML ──
        try:
            html = await page.content()
        except Exception:
            html = response.html or response.text

        if shadow_html:
            html = html + "\n<!-- Shadow DOM Content -->\n" + shadow_html

        # ── Step 6: Extract, normalize, deduplicate ──
        return await self._extract_and_return(
            task_id, run_id, tenant_id, url, html, start_time,
            response, css_selectors, scrolled, waited,
            task=task,
        )

    async def _extract_and_return(
        self, task_id: str, run_id: str, tenant_id: str, url: str,
        html: str, start_time: float, response, css_selectors,
        scrolled: bool, waited: bool, task: Optional[dict] = None,
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

        # Confidence (data quality, not just field coverage)
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
        output_format = task.get("output_format", "json") if task else "json"
        converted_content = None
        estimated_tokens = None
        if output_format != "json" and html:
            conversion = self._converter.convert(html, url, output_format=output_format)
            converted_content = conversion.content
            estimated_tokens = conversion.estimated_tokens

        elapsed = int((time.time() - start_time) * 1000)
        method = "deterministic" if isinstance(self._ai, DeterministicProvider) else "ai"

        logger.info("Browser task completed", extra={
            "task_id": task_id, "url": url,
            "items": len(extracted_data), "confidence": f"{confidence:.2f}",
            "duration_ms": elapsed, "scrolled": scrolled, "waited": waited,
            "html_size": len(html),
        })

        result = {
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
            "output_format": output_format,
        }
        if converted_content is not None:
            result["converted_content"] = converted_content
            result["estimated_tokens"] = estimated_tokens
        return result

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
