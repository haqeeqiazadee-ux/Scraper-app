"""Tests for enhanced CAPTCHA adapter with concrete solver implementations."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from packages.connectors.captcha_adapter import (
    CaptchaAdapter,
    CaptchaEscalationStrategy,
    CaptchaSolution,
    CaptchaType,
    TwoCaptchaSolver,
    AntiCaptchaSolver,
    CapMonsterSolver,
)


# ---------------------------------------------------------------------------
# TwoCaptchaSolver
# ---------------------------------------------------------------------------

class TestTwoCaptchaSolver:
    def test_get_name(self):
        solver = TwoCaptchaSolver(api_key="test-key")
        assert solver.get_name() == "2captcha"

    @pytest.mark.asyncio
    async def test_solve_success(self):
        solver = TwoCaptchaSolver(api_key="test-key")

        submit_response = MagicMock()
        submit_response.json.return_value = {"status": 1, "request": "captcha-123"}

        result_response = MagicMock()
        result_response.json.return_value = {"status": 1, "request": "solved-token-abc"}

        mock_client = AsyncMock()
        mock_client.post.return_value = submit_response
        mock_client.get.return_value = result_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            solution = await solver.solve(CaptchaType.RECAPTCHA_V2, "site-key", "https://example.com")

        assert solution.success is True
        assert solution.solution == "solved-token-abc"
        assert solution.solver_name == "2captcha"
        assert solution.cost_usd > 0

    @pytest.mark.asyncio
    async def test_solve_submit_failure(self):
        solver = TwoCaptchaSolver(api_key="test-key")

        submit_response = MagicMock()
        submit_response.json.return_value = {"status": 0, "request": "ERROR_WRONG_USER_KEY"}

        mock_client = AsyncMock()
        mock_client.post.return_value = submit_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            solution = await solver.solve(CaptchaType.RECAPTCHA_V2, "site-key", "https://example.com")

        assert solution.success is False
        assert "ERROR_WRONG_USER_KEY" in solution.error

    @pytest.mark.asyncio
    async def test_unsupported_type(self):
        solver = TwoCaptchaSolver(api_key="test-key")
        solution = await solver.solve(CaptchaType.IMAGE, "site-key", "https://example.com")
        assert solution.success is False
        assert "Unsupported" in solution.error


# ---------------------------------------------------------------------------
# AntiCaptchaSolver
# ---------------------------------------------------------------------------

class TestAntiCaptchaSolver:
    def test_get_name(self):
        solver = AntiCaptchaSolver(api_key="test-key")
        assert solver.get_name() == "anti-captcha"

    @pytest.mark.asyncio
    async def test_solve_success(self):
        solver = AntiCaptchaSolver(api_key="test-key")

        submit_response = MagicMock()
        submit_response.json.return_value = {"errorId": 0, "taskId": 12345}

        result_response = MagicMock()
        result_response.json.return_value = {
            "status": "ready",
            "solution": {"gRecaptchaResponse": "solved-token"},
            "cost": 0.002,
        }

        mock_client = AsyncMock()
        mock_client.post.side_effect = [submit_response, result_response]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            solution = await solver.solve(CaptchaType.RECAPTCHA_V2, "site-key", "https://example.com")

        assert solution.success is True
        assert solution.solution == "solved-token"
        assert solution.solver_name == "anti-captcha"

    @pytest.mark.asyncio
    async def test_solve_submit_error(self):
        solver = AntiCaptchaSolver(api_key="bad-key")

        submit_response = MagicMock()
        submit_response.json.return_value = {"errorId": 1, "errorDescription": "ERROR_KEY_DOES_NOT_EXIST"}

        mock_client = AsyncMock()
        mock_client.post.return_value = submit_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            solution = await solver.solve(CaptchaType.RECAPTCHA_V2, "site-key", "https://example.com")

        assert solution.success is False


# ---------------------------------------------------------------------------
# CapMonsterSolver
# ---------------------------------------------------------------------------

class TestCapMonsterSolver:
    def test_get_name(self):
        solver = CapMonsterSolver(api_key="test-key")
        assert solver.get_name() == "capmonster"

    def test_uses_capmonster_api_base(self):
        solver = CapMonsterSolver(api_key="test-key")
        assert "capmonster" in solver._delegate.API_BASE


# ---------------------------------------------------------------------------
# CaptchaAdapter
# ---------------------------------------------------------------------------

class TestCaptchaAdapter:
    def test_from_config_all_keys(self):
        adapter = CaptchaAdapter.from_config(
            two_captcha_key="key1",
            anti_captcha_key="key2",
            capmonster_key="key3",
        )
        assert adapter.solver_count == 3

    def test_from_config_no_keys(self):
        adapter = CaptchaAdapter.from_config()
        assert adapter.solver_count == 0

    def test_from_config_partial_keys(self):
        adapter = CaptchaAdapter.from_config(two_captcha_key="key1")
        assert adapter.solver_count == 1

    @pytest.mark.asyncio
    async def test_solve_no_solvers(self):
        adapter = CaptchaAdapter()
        result = await adapter.solve(CaptchaType.RECAPTCHA_V2, "key", "https://example.com")
        assert result.success is False
        assert "No CAPTCHA solvers" in result.error

    @pytest.mark.asyncio
    async def test_solve_fallback_chain(self):
        """First solver fails, second succeeds."""
        adapter = CaptchaAdapter()

        solver1 = AsyncMock()
        solver1.get_name.return_value = "solver1"
        solver1.solve.return_value = CaptchaSolution(success=False, solver_name="solver1", error="fail")

        solver2 = AsyncMock()
        solver2.get_name.return_value = "solver2"
        solver2.solve.return_value = CaptchaSolution(success=True, solution="token", solver_name="solver2", cost_usd=0.003)

        adapter.add_solver(solver1)
        adapter.add_solver(solver2)

        result = await adapter.solve(CaptchaType.RECAPTCHA_V2, "key", "https://example.com", max_attempts=1)
        assert result.success is True
        assert result.solver_name == "solver2"
        assert adapter.stats["total_solves"] == 1

    @pytest.mark.asyncio
    async def test_solve_all_fail(self):
        adapter = CaptchaAdapter()

        solver = AsyncMock()
        solver.get_name.return_value = "failing"
        solver.solve.return_value = CaptchaSolution(success=False, error="fail")

        adapter.add_solver(solver)
        result = await adapter.solve(CaptchaType.RECAPTCHA_V2, "key", "https://example.com", max_attempts=2)
        assert result.success is False
        assert adapter.stats["total_failures"] == 1

    @pytest.mark.asyncio
    async def test_cost_tracking(self):
        adapter = CaptchaAdapter()

        solver = AsyncMock()
        solver.get_name.return_value = "cheap"
        solver.solve.return_value = CaptchaSolution(success=True, solution="t", solver_name="cheap", cost_usd=0.002)

        adapter.add_solver(solver)
        await adapter.solve(CaptchaType.HCAPTCHA, "key", "https://example.com")
        await adapter.solve(CaptchaType.HCAPTCHA, "key", "https://example.com")

        assert adapter.total_cost_usd == pytest.approx(0.004)
        assert adapter.stats["total_solves"] == 2


# ---------------------------------------------------------------------------
# CaptchaEscalationStrategy
# ---------------------------------------------------------------------------

class TestCaptchaEscalationStrategy:
    def test_should_not_solve_early_attempts(self):
        strategy = CaptchaEscalationStrategy(max_retries_before_captcha=2)
        adapter = CaptchaAdapter.from_config(two_captcha_key="key")
        assert strategy.should_solve(0, adapter) is False
        assert strategy.should_solve(1, adapter) is False

    def test_should_solve_after_retries(self):
        strategy = CaptchaEscalationStrategy(max_retries_before_captcha=2)
        adapter = CaptchaAdapter.from_config(two_captcha_key="key")
        assert strategy.should_solve(2, adapter) is True

    def test_should_not_solve_over_budget(self):
        strategy = CaptchaEscalationStrategy(captcha_budget_usd=0.01)
        strategy.record_cost(0.01)
        adapter = CaptchaAdapter.from_config(two_captcha_key="key")
        assert strategy.should_solve(5, adapter) is False

    def test_should_not_solve_no_solvers(self):
        strategy = CaptchaEscalationStrategy()
        adapter = CaptchaAdapter()
        assert strategy.should_solve(5, adapter) is False

    def test_budget_remaining(self):
        strategy = CaptchaEscalationStrategy(captcha_budget_usd=1.0)
        strategy.record_cost(0.3)
        assert strategy.budget_remaining == pytest.approx(0.7)
