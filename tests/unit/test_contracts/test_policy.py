"""Tests for Policy contract schema validation."""

import pytest
from uuid import uuid4

from packages.contracts.policy import (
    Policy, PolicyCreate, PolicyUpdate,
    RateLimit, ProxyPolicy, SessionPolicy, RetryPolicy,
    LanePreference,
)


class TestRateLimit:
    """Tests for RateLimit sub-model."""

    def test_defaults(self):
        rl = RateLimit()
        assert rl.max_requests_per_minute == 60
        assert rl.max_requests_per_hour == 1000
        assert rl.max_concurrent == 5

    def test_custom_values(self):
        rl = RateLimit(max_requests_per_minute=10, max_requests_per_hour=100, max_concurrent=2)
        assert rl.max_requests_per_minute == 10

    def test_minimum_bounds(self):
        with pytest.raises(Exception):
            RateLimit(max_requests_per_minute=0)


class TestProxyPolicy:
    """Tests for ProxyPolicy sub-model."""

    def test_defaults(self):
        pp = ProxyPolicy()
        assert pp.enabled is True
        assert pp.geo is None
        assert pp.rotation_strategy == "weighted"
        assert pp.sticky_session is False

    def test_custom(self):
        pp = ProxyPolicy(enabled=False, geo="US", proxy_type="residential", sticky_session=True)
        assert pp.geo == "US"
        assert pp.proxy_type == "residential"


class TestSessionPolicy:
    """Tests for SessionPolicy sub-model."""

    def test_defaults(self):
        sp = SessionPolicy()
        assert sp.reuse_sessions is True
        assert sp.max_session_age_minutes == 60
        assert sp.rotate_on_failure is True

    def test_bounds(self):
        with pytest.raises(Exception):
            SessionPolicy(max_session_age_minutes=0)


class TestRetryPolicy:
    """Tests for RetryPolicy sub-model."""

    def test_defaults(self):
        rp = RetryPolicy()
        assert rp.max_retries == 3
        assert rp.backoff_base_seconds == 2.0
        assert 429 in rp.retry_on_status_codes
        assert 503 in rp.retry_on_status_codes

    def test_bounds(self):
        with pytest.raises(Exception):
            RetryPolicy(max_retries=-1)
        with pytest.raises(Exception):
            RetryPolicy(max_retries=11)


class TestPolicyCreate:
    """Tests for PolicyCreate validation."""

    def test_minimal(self):
        policy = PolicyCreate(name="My Policy")
        assert policy.name == "My Policy"
        assert policy.preferred_lane == LanePreference.AUTO
        assert policy.timeout_ms == 30000
        assert policy.robots_compliance is True

    def test_full(self):
        policy = PolicyCreate(
            name="E-Commerce Policy",
            target_domains=["shop.com", "store.com"],
            preferred_lane=LanePreference.BROWSER,
            extraction_rules={"selectors": {"title": "h1"}},
            rate_limit=RateLimit(max_requests_per_minute=10),
            timeout_ms=60000,
            robots_compliance=False,
        )
        assert policy.preferred_lane == LanePreference.BROWSER
        assert len(policy.target_domains) == 2
        assert policy.timeout_ms == 60000

    def test_name_required(self):
        with pytest.raises(Exception):
            PolicyCreate(name="")

    def test_timeout_bounds(self):
        with pytest.raises(Exception):
            PolicyCreate(name="Test", timeout_ms=500)  # Below 1000
        with pytest.raises(Exception):
            PolicyCreate(name="Test", timeout_ms=500000)  # Above 300000


class TestPolicy:
    """Tests for full Policy model."""

    def test_defaults(self):
        policy = Policy(tenant_id="t1", name="Default")
        assert policy.id is not None
        assert policy.preferred_lane == LanePreference.AUTO
        assert isinstance(policy.rate_limit, RateLimit)
        assert isinstance(policy.proxy_policy, ProxyPolicy)
        assert isinstance(policy.session_policy, SessionPolicy)
        assert isinstance(policy.retry_policy, RetryPolicy)

    def test_serialization_roundtrip(self):
        policy = Policy(
            tenant_id="t1",
            name="Test Policy",
            target_domains=["example.com"],
            preferred_lane=LanePreference.HTTP,
            rate_limit=RateLimit(max_requests_per_minute=30),
        )
        data = policy.model_dump()
        restored = Policy(**data)
        assert restored.name == policy.name
        assert restored.preferred_lane == policy.preferred_lane
        assert restored.rate_limit.max_requests_per_minute == 30

    def test_json_roundtrip(self):
        policy = Policy(tenant_id="t1", name="JSON Test")
        json_str = policy.model_dump_json()
        restored = Policy.model_validate_json(json_str)
        assert restored.id == policy.id

    def test_lane_preference_values(self):
        for lane in LanePreference:
            policy = Policy(tenant_id="t1", name="Test", preferred_lane=lane)
            assert policy.preferred_lane == lane


class TestPolicyUpdate:
    """Tests for PolicyUpdate partial updates."""

    def test_empty_update(self):
        update = PolicyUpdate()
        assert update.model_dump(exclude_unset=True) == {}

    def test_partial_update(self):
        update = PolicyUpdate(name="Updated", timeout_ms=45000)
        data = update.model_dump(exclude_unset=True)
        assert data["name"] == "Updated"
        assert data["timeout_ms"] == 45000
        assert "preferred_lane" not in data
