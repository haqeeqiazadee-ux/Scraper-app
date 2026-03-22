"""Tests for lane escalation logic."""

import pytest

from packages.core.router import ExecutionRouter, Lane, RouteDecision
from packages.core.escalation import EscalationManager


@pytest.fixture
def router():
    return ExecutionRouter()


@pytest.fixture
def manager(router):
    return EscalationManager(router, confidence_threshold=0.3)


class TestEscalationManager:

    def test_should_escalate_on_failure(self, manager):
        assert manager.should_escalate({"status": "failed"}) is True

    def test_should_escalate_on_zero_items(self, manager):
        assert manager.should_escalate({"status": "success", "item_count": 0}) is True

    def test_should_escalate_on_low_confidence(self, manager):
        assert manager.should_escalate({"status": "success", "item_count": 5, "confidence": 0.1}) is True

    def test_should_not_escalate_on_good_result(self, manager):
        assert manager.should_escalate({"status": "success", "item_count": 10, "confidence": 0.8}) is False

    def test_should_escalate_on_explicit_flag(self, manager):
        assert manager.should_escalate({"should_escalate": True}) is True

    def test_get_escalation_http_to_browser(self, manager):
        decision = RouteDecision(lane=Lane.HTTP, reason="test", fallback_lanes=[Lane.BROWSER, Lane.HARD_TARGET])
        result = {"status": "failed", "lane": "http", "url": "https://test.com"}

        next_lane = manager.get_escalation("task-1", result, decision)
        assert next_lane == Lane.BROWSER

    def test_get_escalation_browser_to_hard_target(self, manager):
        decision = RouteDecision(lane=Lane.BROWSER, reason="test", fallback_lanes=[Lane.HARD_TARGET])
        result = {"status": "failed", "lane": "browser", "url": "https://test.com"}

        next_lane = manager.get_escalation("task-2", result, decision)
        assert next_lane == Lane.HARD_TARGET

    def test_escalation_exhausted(self, manager):
        decision = RouteDecision(lane=Lane.HTTP, reason="test", fallback_lanes=[Lane.BROWSER, Lane.HARD_TARGET])
        result = {"status": "failed", "lane": "http", "url": "https://test.com"}

        # Escalate 3 times (max depth)
        manager.get_escalation("task-3", result, decision)
        manager.get_escalation("task-3", result, decision)
        manager.get_escalation("task-3", result, decision)

        # 4th should return None (exhausted)
        next_lane = manager.get_escalation("task-3", result, decision)
        assert next_lane is None

    def test_escalation_no_fallbacks(self, manager):
        decision = RouteDecision(lane=Lane.HARD_TARGET, reason="test", fallback_lanes=[])
        result = {"status": "failed", "lane": "hard_target"}

        next_lane = manager.get_escalation("task-4", result, decision)
        assert next_lane is None

    def test_complete_clears_context(self, manager):
        decision = RouteDecision(lane=Lane.HTTP, reason="test", fallback_lanes=[Lane.BROWSER])
        result = {"status": "failed", "lane": "http", "url": "https://test.com"}
        manager.get_escalation("task-5", result, decision)

        assert manager.get_context("task-5") is not None
        manager.complete("task-5", {"status": "success", "item_count": 5, "url": "https://test.com"})
        assert manager.get_context("task-5") is None

    def test_escalation_tracks_depth(self, manager):
        decision = RouteDecision(lane=Lane.HTTP, reason="test", fallback_lanes=[Lane.BROWSER, Lane.HARD_TARGET])
        result = {"status": "failed", "lane": "http"}

        manager.get_escalation("task-6", result, decision)
        ctx = manager.get_context("task-6")
        assert ctx is not None
        assert ctx.depth == 1
        assert len(ctx.attempts) == 1
