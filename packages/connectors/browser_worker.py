"""
Browser Worker — Playwright-based browser automation connector.

Implements the BrowserWorker protocol for the browser execution lane.
Handles JavaScript rendering, infinite scroll, load-more, AJAX pagination.
"""

from __future__ import annotations

import logging
from typing import Optional

from packages.core.interfaces import BrowserWorker, ConnectorMetrics, FetchRequest, FetchResponse

logger = logging.getLogger(__name__)


class PlaywrightBrowserWorker:
    """Browser connector using Playwright for JS-rendered pages."""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None) -> None:
        self._headless = headless
        self._proxy = proxy
        self._metrics = ConnectorMetrics()
        self._browser = None
        self._page = None

    async def _ensure_browser(self) -> None:
        """Lazy-initialize Playwright browser."""
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            launch_args: dict = {"headless": self._headless}
            if self._proxy:
                launch_args["proxy"] = {"server": self._proxy}
            self._browser = await self._playwright.chromium.launch(**launch_args)

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch a URL using a browser, executing JavaScript."""
        await self._ensure_browser()
        assert self._browser is not None
        self._metrics.total_requests += 1

        context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
        )

        try:
            page = await context.new_page()
            self._page = page

            if request.cookies:
                cookie_list = [
                    {"name": k, "value": v, "url": request.url}
                    for k, v in request.cookies.items()
                ]
                await context.add_cookies(cookie_list)

            response = await page.goto(
                request.url,
                timeout=request.timeout_ms,
                wait_until="networkidle",
            )

            html = await page.content()
            status_code = response.status if response else 0

            self._metrics.successful_requests += 1
            return FetchResponse(
                url=page.url,
                status_code=status_code,
                html=html,
                text=html,
                body=html.encode("utf-8"),
            )
        except Exception as e:
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            logger.warning("Browser fetch failed", extra={"url": request.url, "error": str(e)})
            return FetchResponse(url=request.url, status_code=0, error=str(e))
        finally:
            await context.close()
            self._page = None

    async def scroll_to_bottom(self, max_scrolls: int = 50) -> int:
        """Scroll page to load dynamic content."""
        if not self._page:
            return 0
        items_found = 0
        for _ in range(max_scrolls):
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self._page.wait_for_timeout(1000)
            new_height = await self._page.evaluate("document.body.scrollHeight")
            items_found = new_height  # Approximate
        return items_found

    async def click_element(self, selector: str) -> bool:
        """Click an element on the page."""
        if not self._page:
            return False
        try:
            await self._page.click(selector, timeout=5000)
            return True
        except Exception:
            return False

    async def wait_for_selector(self, selector: str, timeout_ms: int = 5000) -> bool:
        """Wait for an element to appear."""
        if not self._page:
            return False
        try:
            await self._page.wait_for_selector(selector, timeout=timeout_ms)
            return True
        except Exception:
            return False

    async def get_page_html(self) -> str:
        """Get current page HTML after JS execution."""
        if not self._page:
            return ""
        return await self._page.content()

    async def screenshot(self) -> bytes:
        """Take a screenshot of the current page."""
        if not self._page:
            return b""
        return await self._page.screenshot(full_page=True)

    async def health_check(self) -> bool:
        """Check if the browser is responsive."""
        try:
            await self._ensure_browser()
            return self._browser is not None
        except Exception:
            return False

    def get_metrics(self) -> ConnectorMetrics:
        return self._metrics

    async def close(self) -> None:
        """Close the browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if hasattr(self, "_playwright") and self._playwright:
            await self._playwright.stop()
            self._playwright = None
