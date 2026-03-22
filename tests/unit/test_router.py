"""Tests for ExecutionRouter lane selection logic."""

import pytest

from packages.contracts.task import Task, TaskType
from packages.contracts.policy import Policy, LanePreference
from packages.core.router import ExecutionRouter, Lane, RouteDecision


@pytest.fixture
def router():
    return ExecutionRouter()


class TestExecutionRouter:

    def test_default_route_is_http(self, router):
        """Unknown URLs should default to HTTP lane."""
        task = Task(tenant_id="t1", url="https://unknown-site.com/products")
        decision = router.route(task)
        assert decision.lane == Lane.HTTP
        assert Lane.BROWSER in decision.fallback_lanes

    def test_policy_preferred_lane(self, router):
        """Policy preferred_lane should override default routing."""
        task = Task(tenant_id="t1", url="https://example.com")
        policy = Policy(tenant_id="t1", name="Browser Policy", preferred_lane=LanePreference.BROWSER)
        decision = router.route(task, policy=policy)
        assert decision.lane == Lane.BROWSER
        assert "Policy" in decision.reason

    def test_policy_auto_uses_default_logic(self, router):
        """Policy with AUTO lane should use default routing logic."""
        task = Task(tenant_id="t1", url="https://unknown.com")
        policy = Policy(tenant_id="t1", name="Auto Policy", preferred_lane=LanePreference.AUTO)
        decision = router.route(task, policy=policy)
        assert decision.lane == Lane.HTTP  # Default

    def test_known_browser_domain(self, router):
        """Known browser-required domains should route to browser lane."""
        task = Task(tenant_id="t1", url="https://www.amazon.com/products")
        decision = router.route(task)
        assert decision.lane == Lane.BROWSER

    def test_known_api_domain(self, router):
        """Known API-available domains should route to API lane."""
        task = Task(tenant_id="t1", url="https://mystore.myshopify.com/products.json")
        decision = router.route(task)
        assert decision.lane == Lane.API

    def test_fallback_lanes_http(self, router):
        """HTTP lane should have browser and hard_target as fallbacks."""
        task = Task(tenant_id="t1", url="https://example.com")
        decision = router.route(task)
        assert Lane.BROWSER in decision.fallback_lanes
        assert Lane.HARD_TARGET in decision.fallback_lanes

    def test_fallback_lanes_browser(self, router):
        """Browser lane should have hard_target as fallback."""
        task = Task(tenant_id="t1", url="https://amazon.com")
        decision = router.route(task)
        assert decision.lane == Lane.BROWSER
        assert Lane.HARD_TARGET in decision.fallback_lanes

    def test_get_next_lane(self, router):
        """get_next_lane should return first fallback."""
        decision = RouteDecision(
            lane=Lane.HTTP,
            reason="test",
            fallback_lanes=[Lane.BROWSER, Lane.HARD_TARGET],
        )
        next_lane = router.get_next_lane(decision)
        assert next_lane == Lane.BROWSER

    def test_get_next_lane_empty(self, router):
        """get_next_lane should return None when no fallbacks."""
        decision = RouteDecision(lane=Lane.HARD_TARGET, reason="test", fallback_lanes=[])
        assert router.get_next_lane(decision) is None

    def test_record_outcome_updates_site_profile(self, router):
        """Successful outcomes should update site profiles."""
        router.record_outcome("test-site.com", Lane.BROWSER, success=True)
        task = Task(tenant_id="t1", url="https://test-site.com/page")
        decision = router.route(task)
        assert decision.lane == Lane.BROWSER
        assert "Site profile" in decision.reason

    def test_domain_extraction(self, router):
        """Router should extract domain correctly."""
        assert router._extract_domain("https://www.example.com/path") == "example.com"
        assert router._extract_domain("https://shop.com:8080/products") == "shop.com"
        assert router._extract_domain("http://api.example.com/v1") == "api.example.com"
