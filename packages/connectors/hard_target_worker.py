"""
Hard-Target Worker — stealth browser connector for anti-bot protected sites.

Combines Playwright stealth settings, residential proxy rotation, fingerprint
randomisation, CAPTCHA detection/escalation, and exponential-backoff retries.

This connector is the last resort in the escalation chain:
HTTP -> Browser -> Hard-Target
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from packages.connectors.captcha_adapter import CaptchaAdapter, CaptchaType
from packages.connectors.proxy_adapter import ProxyAdapter
from packages.core.interfaces import ConnectorMetrics, FetchRequest, FetchResponse

logger = logging.getLogger(__name__)


# ---- Fingerprint configuration pools ------------------------------------

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]

TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "Europe/London",
    "Europe/Berlin",
]

LOCALES = ["en-US", "en-GB", "en-CA", "de-DE", "fr-FR"]

# CAPTCHA marker strings commonly found in challenge pages
CAPTCHA_MARKERS = [
    "captcha",
    "recaptcha",
    "hcaptcha",
    "challenge-form",
    "g-recaptcha",
    "h-captcha",
    "cf-challenge",
    "challenge-platform",
    "arkose",
]

# CSS selectors that indicate a CAPTCHA is present on the page
CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    ".g-recaptcha",
    ".h-captcha",
    "#captcha",
    "[data-sitekey]",
]


@dataclass
class Fingerprint:
    """Randomised browser fingerprint for a single session."""

    user_agent: str
    viewport: dict[str, int]
    timezone: str
    locale: str

    @classmethod
    def random(cls) -> Fingerprint:
        return cls(
            user_agent=random.choice(USER_AGENTS),
            viewport=random.choice(VIEWPORTS),
            timezone=random.choice(TIMEZONES),
            locale=random.choice(LOCALES),
        )


# ---- Stealth JavaScript snippets ----------------------------------------

STEALTH_SCRIPTS: list[str] = [
    # Remove webdriver flag
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
    # Override navigator.plugins to look like a real browser
    """Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });""",
    # Override navigator.languages
    "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});",
    # Chrome runtime stub
    "window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};",
    # Override permissions query
    """const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({state: Notification.permission})
            : originalQuery(parameters);""",
]


class HardTargetWorker:
    """Stealth browser connector for sites with aggressive anti-bot measures.

    Combines:
    - Playwright with stealth JS patches (webdriver flag, navigator overrides)
    - Residential proxy rotation via ProxyAdapter
    - Random human-like delays between actions
    - Cookie/session persistence across requests
    - Multiple JS rendering wait strategies (networkidle, selector-based)
    - Screenshot capture on failure for debugging
    - CAPTCHA detection and escalation to CaptchaAdapter
    - Retry with exponential backoff
    - Fingerprint randomisation (viewport, user-agent, timezone, locale)
    """

    def __init__(
        self,
        proxy_adapter: Optional[ProxyAdapter] = None,
        captcha_adapter: Optional[CaptchaAdapter] = None,
        headless: bool = True,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        backoff_max: float = 60.0,
        human_delay_range: tuple[float, float] = (0.5, 2.5),
    ) -> None:
        self._proxy_adapter = proxy_adapter
        self._captcha_adapter = captcha_adapter
        self._headless = headless
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max
        self._human_delay_range = human_delay_range
        self._metrics = ConnectorMetrics()

        # Lazy-initialised Playwright resources
        self._playwright: Any = None
        self._browser: Any = None

        # Session persistence: domain -> cookies
        self._cookie_jar: dict[str, list[dict[str, Any]]] = {}

    # ---- lifecycle -------------------------------------------------------

    async def _ensure_browser(self) -> None:
        """Lazy-initialise the Playwright browser instance."""
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )

    async def close(self) -> None:
        """Release browser and Playwright resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    # ---- fingerprint & stealth -------------------------------------------

    def _generate_fingerprint(self) -> Fingerprint:
        """Create a randomised browser fingerprint."""
        return Fingerprint.random()

    async def _apply_stealth(self, page: Any) -> None:
        """Inject stealth JS patches into a page before navigation."""
        for script in STEALTH_SCRIPTS:
            await page.add_init_script(script)

    # ---- proxy -----------------------------------------------------------

    def _get_proxy_url(self, domain: Optional[str] = None) -> Optional[str]:
        """Select a proxy from the pool, preferring sticky sessions per domain."""
        if self._proxy_adapter is None:
            return None
        proxy = self._proxy_adapter.get_proxy(domain=domain, sticky=True)
        return proxy.url if proxy else None

    # ---- human-like delays -----------------------------------------------

    async def _human_delay(self) -> None:
        """Sleep for a random duration to mimic human behaviour."""
        delay = random.uniform(*self._human_delay_range)
        await asyncio.sleep(delay)

    # ---- CAPTCHA detection -----------------------------------------------

    async def _detect_captcha(self, page: Any) -> bool:
        """Check whether the current page contains a CAPTCHA challenge."""
        try:
            html_lower = (await page.content()).lower()
            for marker in CAPTCHA_MARKERS:
                if marker in html_lower:
                    logger.info("CAPTCHA marker detected", extra={"marker": marker})
                    return True

            for selector in CAPTCHA_SELECTORS:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        logger.info("CAPTCHA element detected", extra={"selector": selector})
                        return True
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("CAPTCHA detection error", extra={"error": str(exc)})
        return False

    async def _handle_captcha(self, page: Any, url: str) -> bool:
        """Attempt to solve a detected CAPTCHA via CaptchaAdapter.

        Returns True if the CAPTCHA was solved and the page should be re-evaluated.
        """
        if self._captcha_adapter is None or self._captcha_adapter.solver_count == 0:
            logger.warning("CAPTCHA detected but no solver configured")
            return False

        # Try to find a site key on the page
        site_key = await self._extract_site_key(page)
        if not site_key:
            logger.warning("CAPTCHA detected but site key not found")
            return False

        # Determine CAPTCHA type
        captcha_type = await self._determine_captcha_type(page)

        solution = await self._captcha_adapter.solve(
            captcha_type=captcha_type,
            site_key=site_key,
            page_url=url,
        )

        if solution.success:
            # Inject solution into the page
            await page.evaluate(
                f"document.getElementById('g-recaptcha-response').innerHTML = '{solution.solution}';"
            )
            logger.info("CAPTCHA solution injected", extra={"solver": solution.solver_name})
            return True

        logger.warning("CAPTCHA solving failed", extra={"error": solution.error})
        return False

    async def _extract_site_key(self, page: Any) -> Optional[str]:
        """Extract a CAPTCHA site key from the page."""
        try:
            site_key = await page.evaluate(
                """() => {
                    const el = document.querySelector('[data-sitekey]');
                    return el ? el.getAttribute('data-sitekey') : null;
                }"""
            )
            return site_key
        except Exception:
            return None

    async def _determine_captcha_type(self, page: Any) -> CaptchaType:
        """Determine the CAPTCHA type present on the page."""
        try:
            html = (await page.content()).lower()
            if "hcaptcha" in html or "h-captcha" in html:
                return CaptchaType.HCAPTCHA
            if "recaptcha/api" in html or "g-recaptcha" in html:
                return CaptchaType.RECAPTCHA_V2
        except Exception:
            pass
        return CaptchaType.RECAPTCHA_V2

    # ---- cookie persistence ----------------------------------------------

    def _domain_from_url(self, url: str) -> str:
        """Extract domain for cookie storage keying."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if ":" in domain:
            domain = domain.split(":")[0]
        return domain

    async def _load_cookies(self, context: Any, url: str) -> None:
        """Restore cookies from a previous session for the same domain."""
        domain = self._domain_from_url(url)
        cookies = self._cookie_jar.get(domain, [])
        if cookies:
            await context.add_cookies(cookies)
            logger.debug("Loaded %d cookies for %s", len(cookies), domain)

    async def _save_cookies(self, context: Any, url: str) -> None:
        """Persist cookies from the current context for future requests."""
        domain = self._domain_from_url(url)
        cookies = await context.cookies()
        if cookies:
            self._cookie_jar[domain] = cookies
            logger.debug("Saved %d cookies for %s", len(cookies), domain)

    # ---- screenshot on failure -------------------------------------------

    async def _capture_failure_screenshot(self, page: Any) -> bytes:
        """Take a full-page screenshot for post-mortem debugging."""
        try:
            return await page.screenshot(full_page=True)
        except Exception:
            return b""

    # ---- core fetch with retry -------------------------------------------

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch a URL with stealth settings and exponential-backoff retries."""
        await self._ensure_browser()
        assert self._browser is not None
        self._metrics.total_requests += 1

        last_error: Optional[str] = None
        last_screenshot: bytes = b""

        for attempt in range(1, self._max_retries + 1):
            fingerprint = self._generate_fingerprint()
            proxy_url = self._get_proxy_url(domain=self._domain_from_url(request.url))

            context_opts: dict[str, Any] = {
                "user_agent": fingerprint.user_agent,
                "viewport": fingerprint.viewport,
                "locale": fingerprint.locale,
                "timezone_id": fingerprint.timezone,
                "ignore_https_errors": True,
            }
            if proxy_url:
                context_opts["proxy"] = {"server": proxy_url}

            context = await self._browser.new_context(**context_opts)
            page = None
            try:
                page = await context.new_page()
                await self._apply_stealth(page)

                # Load persisted cookies
                await self._load_cookies(context, request.url)

                # Add request-level cookies
                if request.cookies:
                    cookie_list = [
                        {"name": k, "value": v, "url": request.url}
                        for k, v in request.cookies.items()
                    ]
                    await context.add_cookies(cookie_list)

                # Human-like pre-navigation delay (skip first attempt for speed)
                if attempt > 1:
                    await self._human_delay()

                # Navigate with wait strategy
                wait_until = request.metadata.get("wait_until", "networkidle")
                response = await page.goto(
                    request.url,
                    timeout=request.timeout_ms,
                    wait_until=wait_until,
                )

                # Wait for a specific selector if requested
                wait_selector = request.metadata.get("wait_selector")
                if wait_selector:
                    wait_timeout = request.metadata.get("wait_selector_timeout_ms", 5000)
                    try:
                        await page.wait_for_selector(wait_selector, timeout=wait_timeout)
                    except Exception:
                        logger.debug("Wait selector %s timed out", wait_selector)

                # Post-navigation human delay
                await self._human_delay()

                # CAPTCHA detection
                if await self._detect_captcha(page):
                    solved = await self._handle_captcha(page, request.url)
                    if solved:
                        # Re-navigate after CAPTCHA solution
                        await self._human_delay()
                        response = await page.goto(
                            request.url,
                            timeout=request.timeout_ms,
                            wait_until=wait_until,
                        )
                    else:
                        last_error = "CAPTCHA detected and solving failed"
                        last_screenshot = await self._capture_failure_screenshot(page)
                        # Save cookies even on failure (for session continuity)
                        await self._save_cookies(context, request.url)
                        await context.close()
                        # Apply backoff before retry
                        if attempt < self._max_retries:
                            backoff = min(
                                self._backoff_base ** attempt + random.uniform(0, 1),
                                self._backoff_max,
                            )
                            await asyncio.sleep(backoff)
                        continue

                status_code = response.status if response else 0

                # Check for blocking status codes
                if status_code in (403, 429, 503):
                    last_error = f"Blocked with status {status_code}"
                    last_screenshot = await self._capture_failure_screenshot(page)
                    await self._save_cookies(context, request.url)
                    await context.close()
                    if attempt < self._max_retries:
                        backoff = min(
                            self._backoff_base ** attempt + random.uniform(0, 1),
                            self._backoff_max,
                        )
                        await asyncio.sleep(backoff)
                    continue

                html = await page.content()

                # Persist cookies for session reuse
                await self._save_cookies(context, request.url)

                # Mark proxy success
                if self._proxy_adapter and proxy_url:
                    proxy_obj = self._proxy_adapter.get_proxy(domain=self._domain_from_url(request.url), sticky=True)
                    if proxy_obj:
                        self._proxy_adapter.mark_success(proxy_obj)

                self._metrics.successful_requests += 1
                return FetchResponse(
                    url=page.url,
                    status_code=status_code,
                    html=html,
                    text=html,
                    body=html.encode("utf-8"),
                )

            except Exception as exc:
                last_error = str(exc)
                if page:
                    last_screenshot = await self._capture_failure_screenshot(page)

                # Mark proxy failure
                if self._proxy_adapter and proxy_url:
                    proxy_obj = self._proxy_adapter.get_proxy(domain=self._domain_from_url(request.url), sticky=True)
                    if proxy_obj:
                        self._proxy_adapter.mark_failure(proxy_obj)

                logger.warning(
                    "Hard-target fetch attempt failed",
                    extra={"url": request.url, "attempt": attempt, "error": last_error},
                )

                if attempt < self._max_retries:
                    backoff = min(
                        self._backoff_base ** attempt + random.uniform(0, 1),
                        self._backoff_max,
                    )
                    await asyncio.sleep(backoff)
            finally:
                try:
                    await context.close()
                except Exception:
                    pass

        # All retries exhausted
        self._metrics.failed_requests += 1
        self._metrics.last_error = last_error
        return FetchResponse(
            url=request.url,
            status_code=0,
            error=last_error or "All retries exhausted",
        )

    # ---- additional browser actions --------------------------------------

    async def screenshot(self, page: Any) -> bytes:
        """Take a screenshot of the current page."""
        try:
            return await page.screenshot(full_page=True)
        except Exception:
            return b""

    # ---- protocol methods ------------------------------------------------

    async def health_check(self) -> bool:
        """Check if the browser can be launched."""
        try:
            await self._ensure_browser()
            return self._browser is not None
        except Exception:
            return False

    def get_metrics(self) -> ConnectorMetrics:
        """Return current connector metrics."""
        return self._metrics
