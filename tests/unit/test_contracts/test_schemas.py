"""Tests for Session, Run, Result, Artifact, and Billing contract schemas."""

import pytest
from uuid import uuid4
from datetime import datetime, date

from packages.contracts.session import Session, SessionCreate, SessionStatus, SessionType
from packages.contracts.run import Run, RunCreate, RunStatus
from packages.contracts.result import Result, ResultCreate
from packages.contracts.artifact import Artifact, ArtifactCreate, ArtifactType
from packages.contracts.billing import TenantQuota, UsageCounters, PlanTier, PLAN_DEFAULTS


# =============================================================================
# Session Tests
# =============================================================================

class TestSession:

    def test_session_create(self):
        sc = SessionCreate(domain="example.com")
        assert sc.domain == "example.com"
        assert sc.session_type == SessionType.HTTP
        assert sc.cookies == {}

    def test_session_defaults(self):
        s = Session(tenant_id="t1", domain="example.com")
        assert s.status == SessionStatus.ACTIVE
        assert s.request_count == 0
        assert s.health_score == 1.0  # No requests = healthy

    def test_session_health_score(self):
        s = Session(
            tenant_id="t1", domain="example.com",
            request_count=10, success_count=8, failure_count=2,
        )
        assert 0.0 <= s.health_score <= 1.0
        # 8/10 = 0.8 success rate * 0.6 + 0.4 = 0.88
        assert s.health_score == pytest.approx(0.88, abs=0.01)

    def test_session_health_score_zero_requests(self):
        s = Session(tenant_id="t1", domain="example.com", request_count=0)
        assert s.health_score == 1.0

    def test_session_health_score_all_failures(self):
        s = Session(
            tenant_id="t1", domain="example.com",
            request_count=10, success_count=0, failure_count=10,
        )
        assert s.health_score == pytest.approx(0.4, abs=0.01)

    def test_session_serialization(self):
        s = Session(tenant_id="t1", domain="shop.com", session_type=SessionType.BROWSER)
        data = s.model_dump()
        restored = Session(**data)
        assert restored.domain == "shop.com"
        assert restored.session_type == SessionType.BROWSER

    def test_session_json_roundtrip(self):
        s = Session(tenant_id="t1", domain="test.com")
        json_str = s.model_dump_json()
        restored = Session.model_validate_json(json_str)
        assert restored.id == s.id

    def test_session_status_values(self):
        for status in SessionStatus:
            s = Session(tenant_id="t1", domain="x.com", status=status)
            assert s.status == status

    def test_session_type_values(self):
        for st in SessionType:
            s = Session(tenant_id="t1", domain="x.com", session_type=st)
            assert s.session_type == st


# =============================================================================
# Run Tests
# =============================================================================

class TestRun:

    def test_run_create(self):
        task_id = uuid4()
        rc = RunCreate(task_id=task_id, lane="http", connector="http_collector")
        assert rc.task_id == task_id
        assert rc.lane == "http"
        assert rc.attempt == 1

    def test_run_defaults(self):
        r = Run(tenant_id="t1", task_id=uuid4(), lane="browser", connector="playwright")
        assert r.status == RunStatus.RUNNING
        assert r.duration_ms == 0
        assert r.bytes_downloaded == 0
        assert r.ai_tokens_used == 0
        assert r.attempt == 1

    def test_run_attempt_minimum(self):
        with pytest.raises(Exception):
            RunCreate(task_id=uuid4(), lane="http", connector="c", attempt=0)

    def test_run_serialization(self):
        r = Run(
            tenant_id="t1", task_id=uuid4(), lane="http", connector="httpx",
            status=RunStatus.SUCCESS, status_code=200, duration_ms=1500, bytes_downloaded=50000,
        )
        data = r.model_dump()
        restored = Run(**data)
        assert restored.status == RunStatus.SUCCESS
        assert restored.status_code == 200
        assert restored.duration_ms == 1500

    def test_run_status_values(self):
        for status in RunStatus:
            r = Run(tenant_id="t1", task_id=uuid4(), lane="x", connector="y", status=status)
            assert r.status == status


# =============================================================================
# Result Tests
# =============================================================================

class TestResult:

    def test_result_create(self):
        rc = ResultCreate(
            task_id=uuid4(), run_id=uuid4(), url="https://example.com",
            extracted_data=[{"name": "Product A", "price": 29.99}],
            item_count=1, confidence=0.95,
        )
        assert rc.item_count == 1
        assert rc.confidence == 0.95
        assert rc.extraction_method == "deterministic"

    def test_result_defaults(self):
        r = Result(
            tenant_id="t1", task_id=uuid4(), run_id=uuid4(),
            url="https://example.com",
        )
        assert r.extracted_data == []
        assert r.item_count == 0
        assert r.confidence == 0.0
        assert r.normalization_applied is False
        assert r.dedup_applied is False
        assert r.artifacts == []

    def test_result_confidence_bounds(self):
        with pytest.raises(Exception):
            ResultCreate(
                task_id=uuid4(), run_id=uuid4(), url="https://x.com",
                confidence=1.5,
            )
        with pytest.raises(Exception):
            ResultCreate(
                task_id=uuid4(), run_id=uuid4(), url="https://x.com",
                confidence=-0.1,
            )

    def test_result_serialization(self):
        r = Result(
            tenant_id="t1", task_id=uuid4(), run_id=uuid4(),
            url="https://shop.com/products",
            extracted_data=[{"name": "A"}, {"name": "B"}],
            item_count=2, confidence=0.85,
            extraction_method="hybrid",
        )
        data = r.model_dump()
        restored = Result(**data)
        assert len(restored.extracted_data) == 2
        assert restored.extraction_method == "hybrid"


# =============================================================================
# Artifact Tests
# =============================================================================

class TestArtifact:

    def test_artifact_create(self):
        ac = ArtifactCreate(
            result_id=uuid4(),
            artifact_type=ArtifactType.HTML_SNAPSHOT,
            storage_path="tenant1/snapshots/abc123.html",
            content_type="text/html",
            size_bytes=50000,
            checksum="sha256:abc123def456",
        )
        assert ac.artifact_type == ArtifactType.HTML_SNAPSHOT
        assert ac.size_bytes == 50000

    def test_artifact_defaults(self):
        a = Artifact(
            tenant_id="t1", result_id=uuid4(),
            artifact_type=ArtifactType.EXPORT_XLSX,
            storage_path="t1/exports/data.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            size_bytes=120000,
            checksum="sha256:xyz789",
        )
        assert a.id is not None
        assert a.expires_at is None
        assert isinstance(a.created_at, datetime)

    def test_artifact_size_nonnegative(self):
        with pytest.raises(Exception):
            ArtifactCreate(
                result_id=uuid4(), artifact_type=ArtifactType.SCREENSHOT,
                storage_path="x", content_type="image/png",
                size_bytes=-1, checksum="x",
            )

    def test_artifact_type_values(self):
        for at in ArtifactType:
            a = Artifact(
                tenant_id="t1", result_id=uuid4(),
                artifact_type=at, storage_path="x",
                content_type="x", size_bytes=0, checksum="x",
            )
            assert a.artifact_type == at

    def test_artifact_serialization(self):
        a = Artifact(
            tenant_id="t1", result_id=uuid4(),
            artifact_type=ArtifactType.EXPORT_JSON,
            storage_path="t1/exports/data.json",
            content_type="application/json",
            size_bytes=5000, checksum="sha256:test",
        )
        json_str = a.model_dump_json()
        restored = Artifact.model_validate_json(json_str)
        assert restored.id == a.id
        assert restored.artifact_type == ArtifactType.EXPORT_JSON


# =============================================================================
# Billing Tests
# =============================================================================

class TestBilling:

    def test_usage_counters_defaults(self):
        uc = UsageCounters()
        assert uc.tasks_today == 0
        assert uc.browser_minutes_today == 0.0
        assert uc.ai_tokens_today == 0
        assert uc.storage_bytes_used == 0
        assert uc.proxy_requests_today == 0

    def test_plan_defaults_exist(self):
        for tier in PlanTier:
            assert tier in PLAN_DEFAULTS
            defaults = PLAN_DEFAULTS[tier]
            assert "max_tasks_per_day" in defaults
            assert "max_concurrent_tasks" in defaults

    def test_plan_tier_ordering(self):
        """Higher tiers should have higher limits."""
        free = PLAN_DEFAULTS[PlanTier.FREE]
        starter = PLAN_DEFAULTS[PlanTier.STARTER]
        pro = PLAN_DEFAULTS[PlanTier.PRO]
        enterprise = PLAN_DEFAULTS[PlanTier.ENTERPRISE]

        assert free["max_tasks_per_day"] < starter["max_tasks_per_day"]
        assert starter["max_tasks_per_day"] < pro["max_tasks_per_day"]
        assert pro["max_tasks_per_day"] < enterprise["max_tasks_per_day"]

    def test_tenant_quota_defaults(self):
        tq = TenantQuota(tenant_id="t1")
        assert tq.plan == PlanTier.FREE
        assert tq.max_tasks_per_day == 50
        assert tq.max_concurrent_tasks == 2

    def test_is_within_quota_true(self):
        tq = TenantQuota(
            tenant_id="t1",
            max_tasks_per_day=100,
            current_usage=UsageCounters(tasks_today=50),
        )
        assert tq.is_within_quota("tasks") is True

    def test_is_within_quota_false(self):
        tq = TenantQuota(
            tenant_id="t1",
            max_tasks_per_day=100,
            current_usage=UsageCounters(tasks_today=100),
        )
        assert tq.is_within_quota("tasks") is False

    def test_is_within_quota_unknown_resource(self):
        tq = TenantQuota(tenant_id="t1")
        assert tq.is_within_quota("nonexistent") is True

    def test_quota_all_resources(self):
        tq = TenantQuota(tenant_id="t1")
        for resource in ["tasks", "browser_minutes", "ai_tokens", "storage", "proxy_requests"]:
            assert tq.is_within_quota(resource) is True

    def test_quota_serialization(self):
        tq = TenantQuota(
            tenant_id="t1", plan=PlanTier.PRO,
            max_tasks_per_day=5000,
            current_usage=UsageCounters(tasks_today=100, ai_tokens_today=5000),
        )
        data = tq.model_dump()
        restored = TenantQuota(**data)
        assert restored.plan == PlanTier.PRO
        assert restored.current_usage.tasks_today == 100
        assert restored.current_usage.ai_tokens_today == 5000
