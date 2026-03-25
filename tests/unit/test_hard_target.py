"""Tests for the hard-target execution lane.

Covers:
- HardTargetWorker stealth settings, proxy rotation, CAPTCHA detection,
  retry logic, fingerprint randomisation, cookie persistence
- HardTargetLaneWorker task processing pipeline
- ExecutionRouter hard-target routing
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from packages.connectors.captcha_adapter import CaptchaAdapter, CaptchaSolution, CaptchaType
from packages.connectors.hard_target_worker import (
    CAPTCHA_MARKERS,
    CAPTCHA_SELECTORS,
    STEALTH_SCRIPTS,
    Fingerprint,
    HardTargetWorker,
)
from packages.connectors.proxy_adapter import Proxy, ProxyAdapter
from packages.core.interfaces import FetchRequest, FetchResponse
from packages.core.router import ExecutionRouter, Lane, HARD_TARGET_DOMAINS
from services.worker_hard_target.worker import HardTargetLaneWorker


SAMPLE_HTML = """
<html>
<head><title>Test Product Page</title></head>
<body>
<script type="application/ld+json">
{
    "@type": "Product",
    "name": "Hard Target Product",
    "sku": "HT-001",
    "offers": {"price": "149.99", "priceCurrency": "USD"}
}
</script>
</body>
</html>
"""

CAPTCHA_HTML = """
<html><body>
<div class="g-recaptcha" data-sitekey="6Le-FAKE-KEY"></div>
<iframe src="https://www.google.com/recaptcha/api2/anchor"></iframe>
</body></html>
"""

EMPTY_HTML = "<html><body>Nothing here</body></html>"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_response(url: str = "https://example.com/product", html: str = SAMPLE_HTML) -> FetchResponse:
    return FetchResponse(
        url=url,
        status_code=200,
        html=html,
        text=html,
        body=html.encode("utf-8"),
    )


def _failed_response(
    url: str = "https://blocked.com",
    status_code: int = 0,
    error: str = "Timeout",
) -> FetchResponse:
    return FetchResponse(url=url, status_code=status_code, error=error)


def _make_mock_page(html: str = SAMPLE_HTML, url: str = "https://example.com") -> AsyncMock:
    """Create a mock Playwright page object."""
    page = AsyncMock()
    page.content = AsyncMock(return_value=html)
    page.url = url
    page.screenshot = AsyncMock(return_value=b"fake-screenshot")
    page.goto = AsyncMock(return_value=MagicMock(status=200))
    page.add_init_script = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.query_selector = AsyncMock(return_value=None)
    page.evaluate = AsyncMock(return_value=None)
    return page


def _make_mock_context(page: AsyncMock) -> AsyncMock:
    """Create a mock Playwright browser context."""
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=page)
    context.add_cookies = AsyncMock()
    context.cookies = AsyncMock(return_value=[])
    context.close = AsyncMock()
    return context


# ---------------------------------------------------------------------------
# Test: Fingerprint randomisation
# ---------------------------------------------------------------------------


class TestFingerprint:

    def test_random_generates_valid_fingerprint(self) -> None:
        """Fingerprint.random() produces all required fields."""
        fp = Fingerprint.random()
        assert fp.user_agent
        assert "width" in fp.viewport
        assert "height" in fp.viewport
        assert fp.timezone
        assert fp.locale
        assert fp.profile is not None

    def test_random_varies_across_calls(self) -> None:
        """Multiple random fingerprints should not all be identical."""
        fingerprints = [Fingerprint.random() for _ in range(20)]
        user_agents = {fp.user_agent for fp in fingerprints}
        # With 14 profiles and 20 samples, we should see more than 1
        assert len(user_agents) > 1

    def test_from_profile_preserves_values(self) -> None:
        """Fingerprint.from_profile() uses the profile's values."""
        from packages.core.device_profiles import DeviceProfile
        profile = DeviceProfile.for_geo("US")
        fp = Fingerprint.from_profile(profile)
        assert fp.user_agent == profile.user_agent
        assert fp.viewport == profile.viewport
        assert fp.timezone == profile.timezone
        assert fp.locale == profile.locale

    def test_random_with_geo_filter(self) -> None:
        """Fingerprint.random(geo='GB') returns UK fingerprint."""
        for _ in range(10):
            fp = Fingerprint.random(geo="GB")
            assert fp.profile.geo_hint == "GB"


# ---------------------------------------------------------------------------
# Test: HardTargetWorker (connector)
# ---------------------------------------------------------------------------


class TestHardTargetWorkerStealth:

    def test_stealth_scripts_not_empty(self) -> None:
        """At least one stealth JS snippet is configured."""
        assert len(STEALTH_SCRIPTS) >= 3

    def test_stealth_scripts_include_canvas_noise(self) -> None:
        """Stealth scripts include Canvas fingerprint noise injection."""
        scripts_text = " ".join(STEALTH_SCRIPTS)
        assert "toDataURL" in scripts_text, "Should include Canvas noise injection"

    def test_stealth_scripts_include_webgl_masking(self) -> None:
        """Stealth scripts include WebGL vendor/renderer masking."""
        scripts_text = " ".join(STEALTH_SCRIPTS)
        assert "WebGLRenderingContext" in scripts_text, "Should include WebGL masking"

    @pytest.mark.asyncio
    async def test_stealth_scripts_injected_playwright_mode(self) -> None:
        """All stealth scripts are injected when using Playwright fallback."""
        page = _make_mock_page()
        worker = HardTargetWorker(max_retries=1, use_camoufox=False)
        worker._browser_type = "playwright"  # Force Playwright mode
        await worker._apply_stealth(page)
        assert page.add_init_script.call_count == len(STEALTH_SCRIPTS)

    @pytest.mark.asyncio
    async def test_stealth_scripts_skipped_camoufox_mode(self) -> None:
        """Stealth scripts are NOT injected when using Camoufox (handled at C++ level)."""
        page = _make_mock_page()
        worker = HardTargetWorker(max_retries=1, use_camoufox=False)
        worker._browser_type = "camoufox"  # Simulate Camoufox mode
        await worker._apply_stealth(page)
        assert page.add_init_script.call_count == 0

    @pytest.mark.asyncio
    async def test_browser_launch_args_disable_automation(self) -> None:
        """Browser launch args include --disable-blink-features=AutomationControlled."""
        import sys
        from packages.core.device_profiles import DeviceProfile

        worker = HardTargetWorker(use_camoufox=False)

        mock_browser = AsyncMock()
        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_async_playwright = MagicMock()
        mock_async_playwright.return_value.start = AsyncMock(return_value=mock_pw_instance)

        mock_module = MagicMock()
        mock_module.async_playwright = mock_async_playwright

        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.async_api": mock_module}):
            profile = DeviceProfile.random()
            await worker._launch_playwright(profile)

        launch_call = mock_pw_instance.chromium.launch.call_args
        assert "--disable-blink-features=AutomationControlled" in launch_call.kwargs.get("args", [])


class TestHardTargetWorkerProxy:

    def test_get_proxy_url_with_adapter(self) -> None:
        """get_proxy_url returns a URL when proxy adapter has proxies."""
        proxy = Proxy(host="1.2.3.4", port=8080, protocol="http")
        adapter = ProxyAdapter(proxies=[proxy])
        worker = HardTargetWorker(proxy_adapter=adapter)
        url = worker._get_proxy_url(domain="example.com")
        assert url == "http://1.2.3.4:8080"

    def test_get_proxy_url_without_adapter(self) -> None:
        """get_proxy_url returns None when no adapter is configured."""
        worker = HardTargetWorker()
        assert worker._get_proxy_url() is None

    def test_proxy_rotation_uses_different_proxies(self) -> None:
        """With multiple proxies, different calls can yield different proxies."""
        proxies = [
            Proxy(host="1.1.1.1", port=8080),
            Proxy(host="2.2.2.2", port=8080),
            Proxy(host="3.3.3.3", port=8080),
        ]
        adapter = ProxyAdapter(proxies=proxies, strategy="random")
        worker = HardTargetWorker(proxy_adapter=adapter)
        # Use different domains so sticky sessions don't pin the same proxy
        urls = set()
        for i in range(30):
            url = worker._get_proxy_url(domain=f"domain-{i}.com")
            urls.add(url)
        # With random strategy and 30 different domains, expect >1 distinct proxy
        assert len(urls) > 1


class TestHardTargetWorkerCaptcha:

    @pytest.mark.asyncio
    async def test_detect_captcha_with_marker(self) -> None:
        """Detects CAPTCHA when marker string is present in HTML."""
        page = _make_mock_page(html=CAPTCHA_HTML)
        worker = HardTargetWorker()
        assert await worker._detect_captcha(page) is True

    @pytest.mark.asyncio
    async def test_detect_captcha_no_marker(self) -> None:
        """Returns False when no CAPTCHA markers are present."""
        page = _make_mock_page(html=EMPTY_HTML)
        worker = HardTargetWorker()
        assert await worker._detect_captcha(page) is False

    @pytest.mark.asyncio
    async def test_detect_captcha_with_selector(self) -> None:
        """Detects CAPTCHA when a matching CSS selector element exists."""
        page = _make_mock_page(html=EMPTY_HTML)
        # Simulate a query_selector hit for .g-recaptcha
        async def mock_query(sel: str):
            if sel == ".g-recaptcha":
                return MagicMock()  # truthy element
            return None
        page.query_selector = AsyncMock(side_effect=mock_query)
        worker = HardTargetWorker()
        assert await worker._detect_captcha(page) is True

    @pytest.mark.asyncio
    async def test_handle_captcha_no_solver(self) -> None:
        """handle_captcha returns False when no solver is configured."""
        page = _make_mock_page(html=CAPTCHA_HTML)
        worker = HardTargetWorker(captcha_adapter=CaptchaAdapter())
        result = await worker._handle_captcha(page, "https://example.com")
        assert result is False


class TestHardTargetWorkerRetry:

    @pytest.mark.asyncio
    async def test_retry_on_blocked_status(self) -> None:
        """Worker retries when receiving a 403 blocking status."""
        worker = HardTargetWorker(max_retries=2, backoff_base=0.01, backoff_max=0.02, enable_warm_up=False, use_camoufox=False)

        call_count = 0

        async def mock_goto(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            if call_count < 2:
                mock_resp.status = 403
            else:
                mock_resp.status = 200
            return mock_resp

        page = _make_mock_page()
        page.goto = mock_goto
        page.content = AsyncMock(return_value=SAMPLE_HTML)

        context = _make_mock_context(page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=context)

        worker._browser = mock_browser
        worker._browser_type = "playwright"

        request = FetchRequest(url="https://blocked.com", timeout_ms=5000)
        response = await worker.fetch(request)

        assert call_count == 2
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self) -> None:
        """When all retries fail, returns error response."""
        worker = HardTargetWorker(max_retries=2, backoff_base=0.01, backoff_max=0.02, enable_warm_up=False, use_camoufox=False)

        page = _make_mock_page()
        page.goto = AsyncMock(return_value=MagicMock(status=403))
        page.content = AsyncMock(return_value="<html>Blocked</html>")

        context = _make_mock_context(page)
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=context)
        worker._browser = mock_browser
        worker._browser_type = "playwright"

        request = FetchRequest(url="https://blocked.com", timeout_ms=5000)
        response = await worker.fetch(request)

        assert response.status_code == 0
        assert response.error is not None
        assert "retries" in response.error.lower() or "blocked" in response.error.lower()


class TestHardTargetWorkerCookiePersistence:

    @pytest.mark.asyncio
    async def test_cookies_saved_and_loaded(self) -> None:
        """Cookies from first fetch are restored on subsequent fetch to same domain."""
        worker = HardTargetWorker(max_retries=1, backoff_base=0.01, enable_warm_up=False, use_camoufox=False)

        saved_cookies = [{"name": "session", "value": "abc123", "domain": "example.com"}]

        page = _make_mock_page()
        page.goto = AsyncMock(return_value=MagicMock(status=200))

        context = _make_mock_context(page)
        context.cookies = AsyncMock(return_value=saved_cookies)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=context)
        worker._browser = mock_browser
        worker._browser_type = "playwright"

        # First fetch — saves cookies
        request = FetchRequest(url="https://example.com/page1", timeout_ms=5000)
        await worker.fetch(request)

        assert "example.com" in worker._cookie_jar
        assert worker._cookie_jar["example.com"] == saved_cookies

        # Second fetch — should load cookies
        context2 = _make_mock_context(page)
        context2.cookies = AsyncMock(return_value=saved_cookies)
        mock_browser.new_context = AsyncMock(return_value=context2)

        request2 = FetchRequest(url="https://example.com/page2", timeout_ms=5000)
        await worker.fetch(request2)

        # add_cookies should have been called with our saved cookies
        context2.add_cookies.assert_any_call(saved_cookies)


# ---------------------------------------------------------------------------
# Test: HardTargetLaneWorker (service)
# ---------------------------------------------------------------------------


class TestHardTargetLaneWorker:

    @pytest.fixture
    def lane_worker(self) -> HardTargetLaneWorker:
        return HardTargetLaneWorker(headless=True, max_retries=1)

    @pytest.mark.asyncio
    async def test_process_task_success(self, lane_worker: HardTargetLaneWorker) -> None:
        """Successful hard-target extraction returns correct result dict."""
        mock_response = _ok_response()
        with patch.object(lane_worker._hard_target, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await lane_worker.process_task({
                "url": "https://example.com/product",
                "tenant_id": "t1",
                "task_id": "ht-task-1",
            })

        assert result["status"] == "success"
        assert result["lane"] == "hard_target"
        assert result["connector"] == "hard_target_worker"
        assert result["task_id"] == "ht-task-1"
        assert result["should_escalate"] is False
        assert result["item_count"] >= 1

    @pytest.mark.asyncio
    async def test_process_task_failure(self, lane_worker: HardTargetLaneWorker) -> None:
        """Failed fetch returns failure result with classified reason."""
        mock_response = _failed_response(status_code=403, error="Forbidden")
        with patch.object(lane_worker._hard_target, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await lane_worker.process_task({
                "url": "https://blocked.com",
                "tenant_id": "t1",
            })

        assert result["status"] == "failed"
        assert result["failure_reason"] == "access_denied"
        assert result["should_escalate"] is False  # Last lane

    @pytest.mark.asyncio
    async def test_classify_failure_captcha(self, lane_worker: HardTargetLaneWorker) -> None:
        """Failure with CAPTCHA error is classified as captcha_unsolved."""
        mock_response = _failed_response(error="CAPTCHA detected and solving failed")
        with patch.object(lane_worker._hard_target, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await lane_worker.process_task({
                "url": "https://captcha.com",
                "tenant_id": "t1",
            })

        assert result["failure_reason"] == "captcha_detected"

    @pytest.mark.asyncio
    async def test_close_delegates(self, lane_worker: HardTargetLaneWorker) -> None:
        """close() delegates to the underlying HardTargetWorker."""
        with patch.object(lane_worker._hard_target, "close", new_callable=AsyncMock) as mock_close:
            await lane_worker.close()
            mock_close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test: Router hard-target routing
# ---------------------------------------------------------------------------


class TestRouterHardTarget:

    def test_hard_target_domain_routes_directly(self) -> None:
        """Known hard-target domains route directly to hard_target lane."""
        from packages.contracts.task import Task
        router = ExecutionRouter()
        task = Task(
            tenant_id="t1",
            url="https://www.linkedin.com/in/someone",
        )
        decision = router.route(task)
        assert decision.lane == Lane.HARD_TARGET
        assert decision.fallback_lanes == []
        assert "hard-target" in decision.reason

    def test_hard_target_in_escalation_chain(self) -> None:
        """Hard-target appears as fallback for browser lane."""
        router = ExecutionRouter()
        fallbacks = router._get_fallback_lanes(Lane.BROWSER)
        assert Lane.HARD_TARGET in fallbacks

    def test_hard_target_no_further_escalation(self) -> None:
        """Hard-target lane has no further fallback lanes."""
        router = ExecutionRouter()
        fallbacks = router._get_fallback_lanes(Lane.HARD_TARGET)
        assert fallbacks == []

    def test_policy_hard_target_override(self) -> None:
        """Policy with preferred_lane=hard_target routes directly."""
        from packages.contracts.policy import Policy, LanePreference
        from packages.contracts.task import Task
        router = ExecutionRouter()
        task = Task(tenant_id="t1", url="https://example.com")
        policy = Policy(
            tenant_id="t1",
            name="stealth",
            preferred_lane=LanePreference.HARD_TARGET,
        )
        decision = router.route(task, policy=policy)
        assert decision.lane == Lane.HARD_TARGET
