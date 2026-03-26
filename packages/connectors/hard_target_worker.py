"""
Hard-Target Worker — stealth browser connector for anti-bot protected sites.

Uses Camoufox (C++-level Firefox stealth) when available, falls back to
Playwright Chromium with JS stealth patches. Integrates coherent device
profiles, warm-up navigation, human behavioral simulation, CAPTCHA solving,
and residential proxy rotation.

This connector is the last resort in the escalation chain:
HTTP -> Browser -> Hard-Target
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Optional

from packages.connectors.captcha_adapter import CaptchaAdapter, CaptchaType
from packages.connectors.proxy_adapter import ProxyAdapter
from packages.core.device_profiles import DeviceProfile, get_headers_for_profile
from packages.core.human_behavior import (
    human_click,
    human_delay,
    human_scroll,
    idle_jitter,
    warm_up_navigation,
)
from packages.core.interfaces import ConnectorMetrics, FetchRequest, FetchResponse

logger = logging.getLogger(__name__)


# Check for Camoufox availability
_HAS_CAMOUFOX = False
try:
    import camoufox  # noqa: F401
    _HAS_CAMOUFOX = True
except ImportError:
    logger.info("camoufox not installed — falling back to Playwright Chromium with JS stealth patches")


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
    "aws-waf-token",
    "awswaf",
]

# CSS selectors that indicate a CAPTCHA is present on the page
CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    ".g-recaptcha",
    ".h-captcha",
    "#captcha",
    "[data-sitekey]",
    "iframe[src*='challenges.cloudflare.com']",
]


@dataclass
class Fingerprint:
    """Browser fingerprint derived from a coherent device profile."""

    profile: DeviceProfile
    user_agent: str
    viewport: dict[str, int]
    timezone: str
    locale: str

    @classmethod
    def from_profile(cls, profile: DeviceProfile) -> Fingerprint:
        return cls(
            profile=profile,
            user_agent=profile.user_agent,
            viewport=profile.viewport,
            timezone=profile.timezone,
            locale=profile.locale,
        )

    @classmethod
    def random(cls, geo: Optional[str] = None) -> Fingerprint:
        profile = DeviceProfile.random(geo=geo)
        return cls.from_profile(profile)


# ---- Stealth JavaScript snippets (fallback for Playwright Chromium) --------
# These are ONLY used when Camoufox is not available. Camoufox handles stealth
# at the C++ level, making these unnecessary and actually counterproductive.

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
    # Canvas fingerprint noise (add subtle random noise to canvas reads)
    """const _toDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        if (type === 'image/png') {
            const ctx = this.getContext('2d');
            if (ctx) {
                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] = imageData.data[i] ^ (Math.random() > 0.99 ? 1 : 0);
                }
                ctx.putImageData(imageData, 0, 0);
            }
        }
        return _toDataURL.apply(this, arguments);
    };""",
    # WebGL vendor/renderer masking
    """const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.apply(this, arguments);
    };""",
]


class HardTargetWorker:
    """Stealth browser connector for sites with aggressive anti-bot measures.

    Combines:
    - Camoufox (C++-level stealth) or Playwright + JS patches (fallback)
    - Coherent device profiles (all fingerprint signals consistent)
    - Warm-up navigation (homepage visit before target)
    - Human behavioral simulation (Bezier mouse, scroll, idle jitter)
    - Residential proxy rotation via ProxyAdapter
    - Cookie/session persistence across requests
    - CAPTCHA detection and escalation to CaptchaAdapter
    - Retry with exponential backoff (log-normal delays)
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
        executable_path: Optional[str] = None,
        enable_warm_up: bool = True,
        use_camoufox: bool = True,
    ) -> None:
        self._proxy_adapter = proxy_adapter
        self._captcha_adapter = captcha_adapter
        self._headless = headless
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max
        self._human_delay_range = human_delay_range
        self._executable_path = executable_path
        self._enable_warm_up = enable_warm_up
        self._use_camoufox = use_camoufox and _HAS_CAMOUFOX
        self._metrics = ConnectorMetrics()

        # Lazy-initialised browser resources
        self._playwright: Any = None
        self._browser: Any = None
        self._browser_type: str = ""  # "camoufox" or "playwright"

        # Session persistence: domain -> cookies
        self._cookie_jar: dict[str, list[dict[str, Any]]] = {}

    # ---- lifecycle -------------------------------------------------------

    async def _ensure_browser(self, profile: DeviceProfile) -> None:
        """Lazy-initialise the browser instance."""
        if self._browser is not None:
            return

        if self._use_camoufox:
            await self._launch_camoufox(profile)
        else:
            await self._launch_playwright(profile)

    async def _launch_camoufox(self, profile: DeviceProfile) -> None:
        """Launch Camoufox with C++-level stealth — no JS patches needed."""
        from camoufox.async_api import AsyncCamoufox

        self._camoufox_cm = AsyncCamoufox(
            headless=self._headless,
            geoip=True,  # Auto-match locale/timezone to IP
        )
        self._browser = await self._camoufox_cm.__aenter__()
        self._browser_type = "camoufox"
        logger.info("Launched Camoufox (C++-level stealth, headless=%s)", self._headless)

    async def _launch_playwright(self, profile: DeviceProfile) -> None:
        """Fallback: launch Playwright Chromium with JS stealth patches."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        launch_args: dict[str, Any] = {
            "headless": self._headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--window-size=1920,1080",
            ],
        }
        if self._executable_path:
            launch_args["executable_path"] = self._executable_path
        self._browser = await self._playwright.chromium.launch(**launch_args)
        self._browser_type = "playwright"
        logger.info("Launched Playwright Chromium fallback (JS stealth patches)")

    async def close(self) -> None:
        """Release browser resources."""
        if self._browser_type == "camoufox" and hasattr(self, "_camoufox_cm"):
            try:
                await self._camoufox_cm.__aexit__(None, None, None)
            except Exception:
                pass
            self._browser = None
        elif self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    # ---- context creation ------------------------------------------------

    async def _create_context(self, fingerprint: Fingerprint, proxy_url: Optional[str] = None) -> Any:
        """Create a browser context with the given fingerprint."""
        context_opts: dict[str, Any] = {
            "user_agent": fingerprint.user_agent,
            "viewport": fingerprint.viewport,
            "locale": fingerprint.locale,
            "timezone_id": fingerprint.timezone,
            "ignore_https_errors": True,
            "screen": fingerprint.profile.screen,
            "color_scheme": "light",
        }
        if proxy_url:
            context_opts["proxy"] = {"server": proxy_url}

        if self._browser_type == "camoufox":
            # Camoufox: fingerprint is handled at C++ level, but we still
            # set context-level options for viewport/locale/timezone
            context = await self._browser.new_context(**context_opts)
        else:
            # Playwright: need context options
            context = await self._browser.new_context(**context_opts)

        return context

    # ---- stealth ---------------------------------------------------------

    async def _apply_stealth(self, page: Any) -> None:
        """Inject stealth JS patches — ONLY for Playwright fallback."""
        if self._browser_type == "camoufox":
            return  # Camoufox handles stealth at C++ level

        for script in STEALTH_SCRIPTS:
            await page.add_init_script(script)

    # ---- proxy -----------------------------------------------------------

    def _get_proxy_url(self, domain: Optional[str] = None) -> Optional[str]:
        """Select a proxy from the pool, preferring sticky sessions per domain."""
        if self._proxy_adapter is None:
            return None
        proxy = self._proxy_adapter.get_proxy(domain=domain, sticky=True)
        return proxy.url if proxy else None

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
        """Attempt to solve a detected CAPTCHA via CaptchaAdapter."""
        if self._captcha_adapter is None or self._captcha_adapter.solver_count == 0:
            logger.warning("CAPTCHA detected but no solver configured")
            return False

        site_key = await self._extract_site_key(page)
        if not site_key:
            logger.warning("CAPTCHA detected but site key not found")
            return False

        captcha_type = await self._determine_captcha_type(page)

        solution = await self._captcha_adapter.solve(
            captcha_type=captcha_type,
            site_key=site_key,
            page_url=url,
        )

        if solution.success:
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
            if "challenges.cloudflare.com" in html:
                return CaptchaType.HCAPTCHA  # Turnstile uses hCaptcha-like flow
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
        """Fetch a URL with full stealth stack and exponential-backoff retries."""
        # Determine geo from proxy adapter or URL domain
        domain = self._domain_from_url(request.url)
        geo = request.metadata.get("geo")

        fingerprint = Fingerprint.random(geo=geo)
        await self._ensure_browser(fingerprint.profile)
        assert self._browser is not None
        self._metrics.total_requests += 1

        last_error: Optional[str] = None
        last_screenshot: bytes = b""

        for attempt in range(1, self._max_retries + 1):
            # Fresh fingerprint each attempt (but coherent within itself)
            fingerprint = Fingerprint.random(geo=geo)
            proxy_url = self._get_proxy_url(domain=domain)

            context = await self._create_context(fingerprint, proxy_url)
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

                # Warm-up navigation on first attempt (visit homepage first)
                if attempt == 1 and self._enable_warm_up:
                    await warm_up_navigation(page, request.url)

                # Human-like pre-navigation delay (log-normal, not uniform)
                if attempt > 1:
                    await human_delay(median=2.0, sigma=0.5)

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

                # Human behavioral simulation post-navigation
                await idle_jitter(page, duration=random.uniform(0.3, 1.0))
                await human_scroll(page, distance=random.randint(200, 600))
                await human_delay(median=1.0, sigma=0.3)

                # CAPTCHA detection
                if await self._detect_captcha(page):
                    solved = await self._handle_captcha(page, request.url)
                    if solved:
                        await human_delay(median=1.5, sigma=0.3)
                        response = await page.goto(
                            request.url,
                            timeout=request.timeout_ms,
                            wait_until=wait_until,
                        )
                    else:
                        last_error = "CAPTCHA detected and solving failed"
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
                    proxy_obj = self._proxy_adapter.get_proxy(domain=domain, sticky=True)
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
                    proxy_obj = self._proxy_adapter.get_proxy(domain=domain, sticky=True)
                    if proxy_obj:
                        self._proxy_adapter.mark_failure(proxy_obj)

                logger.warning(
                    "Hard-target fetch attempt failed",
                    extra={"url": request.url, "attempt": attempt, "error": last_error, "engine": self._browser_type},
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
            profile = DeviceProfile.random()
            await self._ensure_browser(profile)
            return self._browser is not None
        except Exception:
            return False

    def get_metrics(self) -> ConnectorMetrics:
        """Return current connector metrics."""
        return self._metrics

    @property
    def browser_type(self) -> str:
        """Return which browser engine is active."""
        return self._browser_type
