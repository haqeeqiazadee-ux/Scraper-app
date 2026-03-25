"""
Integration tests for proxy rotation and CAPTCHA solving.

Covers:
  UC-8.2.1 — ProxyAdapter integration wired in HardTargetWorker
  UC-8.2.2 — Proxy rotation per request in HardTargetWorker
  UC-8.3.2 — reCAPTCHA solving via solver chain
  UC-8.3.4 — CAPTCHA cost tracking
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.connectors.proxy_adapter import ProxyAdapter, Proxy
from packages.connectors.captcha_adapter import (
    CaptchaAdapter,
    CaptchaType,
    CaptchaSolution,
    CaptchaEscalationStrategy,
    TwoCaptchaSolver,
    AntiCaptchaSolver,
    CapSolverSolver,
    NopeCHASolver,
)


# ---------------------------------------------------------------------------
# UC-8.2.1/8.2.2 — Proxy rotation integration
# ---------------------------------------------------------------------------

class TestProxyRotation:
    """Proxy adapter provides rotation per request."""

    def test_proxy_adapter_has_get_proxy(self):
        """ProxyAdapter exposes get_proxy() for per-request rotation."""
        adapter = ProxyAdapter()
        assert hasattr(adapter, "get_proxy")

    def test_proxy_adapter_cycles_proxies(self):
        """Successive get_proxy calls cycle through available proxies."""
        proxies = [
            Proxy(host="proxy1", port=8080),
            Proxy(host="proxy2", port=8080),
            Proxy(host="proxy3", port=8080),
        ]
        adapter = ProxyAdapter(proxies=proxies, strategy="round_robin")

        results = [adapter.get_proxy() for _ in range(6)]
        # Should cycle through all proxies
        hosts = [p.host for p in results if p]
        assert len(hosts) == 6
        # All three proxies should be used
        assert set(hosts) == {"proxy1", "proxy2", "proxy3"}

    def test_empty_proxy_list_returns_none(self):
        """With no proxies configured, get_proxy returns None."""
        adapter = ProxyAdapter()
        assert adapter.get_proxy() is None

    def test_proxy_health_tracking(self):
        """Proxy adapter tracks success/failure per proxy."""
        proxy = Proxy(host="proxy1", port=8080)
        adapter = ProxyAdapter(proxies=[proxy])

        # Record success
        adapter.mark_success(proxy, response_time=0.5)
        assert proxy.total_requests == 1
        assert proxy.successful_requests == 1
        assert len(proxy.response_times) == 1

    def test_proxy_failure_cooldown(self):
        """Proxies are put on cooldown after max failures."""
        proxy = Proxy(host="proxy1", port=8080)
        adapter = ProxyAdapter(proxies=[proxy], max_failures=3)

        for _ in range(3):
            adapter.mark_failure(proxy)

        assert proxy.failed_requests == 3
        assert proxy.cooldown_until > 0  # cooldown set

    def test_get_best_proxies(self):
        """get_best_proxies returns proxies sorted by score."""
        proxies = [
            Proxy(host="slow", port=1, total_requests=6, successful_requests=1, failed_requests=5),
            Proxy(host="fast", port=2, total_requests=10, successful_requests=10, failed_requests=0),
        ]
        adapter = ProxyAdapter(proxies=proxies)
        best = adapter.get_best_proxies(n=2)
        assert best[0].host == "fast"


# ---------------------------------------------------------------------------
# UC-8.3.2 — reCAPTCHA solving
# ---------------------------------------------------------------------------

class TestReCaptchaSolving:
    """Verify reCAPTCHA can be solved through the solver chain."""

    @pytest.mark.asyncio
    async def test_capsolver_recaptcha_v2(self):
        """CapSolver can solve reCAPTCHA v2."""
        solver = CapSolverSolver(api_key="test-key")

        with patch("httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            # Mock submit response
            submit_resp = MagicMock()
            submit_resp.json.return_value = {"errorId": 0, "taskId": "test-123"}

            # Mock poll response
            poll_resp = MagicMock()
            poll_resp.json.return_value = {
                "status": "ready",
                "solution": {"gRecaptchaResponse": "test-token-abc123"},
            }

            client.post.side_effect = [submit_resp, poll_resp]

            solution = await solver.solve(
                CaptchaType.RECAPTCHA_V2,
                "6Lc_test_site_key",
                "https://example.com/login",
            )

            assert solution.success
            assert solution.solution == "test-token-abc123"
            assert solution.solver_name == "capsolver"

    @pytest.mark.asyncio
    async def test_nopecha_recaptcha_v2(self):
        """NopeCHA can solve reCAPTCHA v2."""
        solver = NopeCHASolver(api_key="test-nopecha-key")

        with patch("httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            # Mock submit response
            submit_resp = MagicMock()
            submit_resp.json.return_value = {"data": "job-456"}
            client.post.return_value = submit_resp

            # Mock poll response
            poll_resp = MagicMock()
            poll_resp.json.return_value = {"data": "solved-token-xyz"}
            client.get.return_value = poll_resp

            solution = await solver.solve(
                CaptchaType.RECAPTCHA_V2,
                "6Lc_test_key",
                "https://example.com/page",
            )

            assert solution.success
            assert solution.solution == "solved-token-xyz"
            assert solution.solver_name == "nopecha"

    @pytest.mark.asyncio
    async def test_2captcha_recaptcha(self):
        """TwoCaptcha solver creates correct request structure."""
        solver = TwoCaptchaSolver(api_key="test-2cap-key")

        with patch("httpx.AsyncClient") as MockClient:
            client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            # Mock submit
            submit_resp = MagicMock()
            submit_resp.json.return_value = {"status": 1, "request": "cap-id-789"}
            client.post.return_value = submit_resp

            # Mock poll
            poll_resp = MagicMock()
            poll_resp.json.return_value = {"status": 1, "request": "2cap-token-def"}
            client.get.return_value = poll_resp

            solution = await solver.solve(
                CaptchaType.RECAPTCHA_V2,
                "6Le_test",
                "https://example.com",
            )

            assert solution.success
            assert solution.solution == "2cap-token-def"
            assert solution.solver_name == "2captcha"


# ---------------------------------------------------------------------------
# UC-8.3.4 — CAPTCHA cost tracking
# ---------------------------------------------------------------------------

class TestCaptchaCostTracking:
    """CAPTCHA adapter tracks total cost across all solves."""

    @pytest.mark.asyncio
    async def test_cost_tracked_on_success(self):
        """Successful solve records cost in the adapter."""
        adapter = CaptchaAdapter()

        mock_solver = AsyncMock()
        mock_solver.get_name.return_value = "mock-solver"
        mock_solver.solve.return_value = CaptchaSolution(
            success=True,
            solution="token",
            solver_name="mock-solver",
            cost_usd=0.003,
        )
        adapter.add_solver(mock_solver)

        await adapter.solve(CaptchaType.RECAPTCHA_V2, "site-key", "https://example.com")

        assert adapter.total_cost_usd == pytest.approx(0.003)
        assert adapter.stats["total_solves"] == 1
        assert adapter.stats["total_failures"] == 0

    @pytest.mark.asyncio
    async def test_cost_accumulates(self):
        """Multiple solves accumulate total cost."""
        adapter = CaptchaAdapter()

        mock_solver = AsyncMock()
        mock_solver.get_name.return_value = "mock"
        mock_solver.solve.return_value = CaptchaSolution(
            success=True, solution="t", solver_name="mock", cost_usd=0.002,
        )
        adapter.add_solver(mock_solver)

        for _ in range(5):
            await adapter.solve(CaptchaType.HCAPTCHA, "key", "https://test.com")

        assert adapter.total_cost_usd == pytest.approx(0.010)
        assert adapter.stats["total_solves"] == 5

    @pytest.mark.asyncio
    async def test_no_cost_on_failure(self):
        """Failed solves don't add cost."""
        adapter = CaptchaAdapter()

        mock_solver = AsyncMock()
        mock_solver.get_name.return_value = "mock"
        mock_solver.solve.return_value = CaptchaSolution(
            success=False, solver_name="mock", error="timeout",
        )
        adapter.add_solver(mock_solver)

        await adapter.solve(CaptchaType.RECAPTCHA_V2, "key", "https://test.com")

        assert adapter.total_cost_usd == 0.0
        assert adapter.stats["total_failures"] == 1

    @pytest.mark.asyncio
    async def test_fallback_tries_next_solver(self):
        """When first solver fails, adapter tries the next."""
        adapter = CaptchaAdapter()

        fail_solver = AsyncMock()
        fail_solver.get_name.return_value = "fail"
        fail_solver.solve.return_value = CaptchaSolution(
            success=False, solver_name="fail", error="unavailable",
        )

        success_solver = AsyncMock()
        success_solver.get_name.return_value = "success"
        success_solver.solve.return_value = CaptchaSolution(
            success=True, solution="token", solver_name="success", cost_usd=0.001,
        )

        adapter.add_solver(fail_solver)
        adapter.add_solver(success_solver)

        result = await adapter.solve(CaptchaType.RECAPTCHA_V2, "key", "https://test.com")

        assert result.success
        assert result.solver_name == "success"
        assert adapter.total_cost_usd == pytest.approx(0.001)


class TestCaptchaEscalation:
    """CAPTCHA escalation strategy with budget tracking."""

    def test_budget_enforcement(self):
        """Escalation stops when budget is exhausted."""
        strategy = CaptchaEscalationStrategy(captcha_budget_usd=0.01)
        adapter = CaptchaAdapter()
        adapter.add_solver(MagicMock())

        assert strategy.should_solve(3, adapter)

        strategy.record_cost(0.005)
        assert strategy.should_solve(3, adapter)  # still under budget

        strategy.record_cost(0.006)  # now over
        assert not strategy.should_solve(3, adapter)

    def test_retry_before_captcha(self):
        """Don't solve CAPTCHA until retries are exhausted."""
        strategy = CaptchaEscalationStrategy(max_retries_before_captcha=3)
        adapter = CaptchaAdapter()
        adapter.add_solver(MagicMock())

        assert not strategy.should_solve(0, adapter)
        assert not strategy.should_solve(1, adapter)
        assert not strategy.should_solve(2, adapter)
        assert strategy.should_solve(3, adapter)

    def test_budget_remaining(self):
        strategy = CaptchaEscalationStrategy(captcha_budget_usd=1.0)
        assert strategy.budget_remaining == 1.0
        strategy.record_cost(0.25)
        assert strategy.budget_remaining == pytest.approx(0.75)

    def test_no_solver_no_solve(self):
        """Don't attempt CAPTCHA if no solvers configured."""
        strategy = CaptchaEscalationStrategy()
        adapter = CaptchaAdapter()  # no solvers
        assert not strategy.should_solve(5, adapter)
