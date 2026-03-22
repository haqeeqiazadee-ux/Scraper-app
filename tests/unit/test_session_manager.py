"""Tests for session manager."""

import pytest
from packages.contracts.session import SessionStatus, SessionType
from packages.core.session_manager import SessionManager


@pytest.fixture
def manager():
    return SessionManager()


class TestSessionManager:

    def test_create_session(self, manager):
        session = manager.create_session("t1", "example.com")
        assert session.domain == "example.com"
        assert session.status == SessionStatus.ACTIVE
        assert session.tenant_id == "t1"
        assert session.health_score == 1.0

    def test_get_session(self, manager):
        session = manager.create_session("t1", "example.com")
        found = manager.get_session(str(session.id))
        assert found is not None
        assert found.id == session.id

    def test_get_session_not_found(self, manager):
        assert manager.get_session("nonexistent") is None

    def test_get_session_for_domain(self, manager):
        manager.create_session("t1", "example.com")
        manager.create_session("t1", "other.com")

        found = manager.get_session_for_domain("t1", "example.com")
        assert found is not None
        assert found.domain == "example.com"

    def test_get_session_for_domain_best_health(self, manager):
        s1 = manager.create_session("t1", "example.com")
        s2 = manager.create_session("t1", "example.com")

        # Degrade s1
        for _ in range(5):
            manager.record_failure(str(s1.id))

        best = manager.get_session_for_domain("t1", "example.com")
        assert best.id == s2.id  # s2 is healthier

    def test_get_session_for_domain_tenant_isolation(self, manager):
        manager.create_session("t1", "example.com")
        found = manager.get_session_for_domain("t2", "example.com")
        assert found is None

    def test_record_success(self, manager):
        session = manager.create_session("t1", "example.com")
        manager.record_success(str(session.id))
        assert session.request_count == 1
        assert session.success_count == 1
        assert session.status == SessionStatus.ACTIVE

    def test_record_failure_degrades(self, manager):
        session = manager.create_session("t1", "example.com")
        # Many failures should degrade
        for _ in range(10):
            manager.record_failure(str(session.id))
        assert session.status in (SessionStatus.DEGRADED, SessionStatus.INVALIDATED)

    def test_invalidate(self, manager):
        session = manager.create_session("t1", "example.com")
        manager.invalidate(str(session.id), reason="blocked by site")
        assert session.status == SessionStatus.INVALIDATED

    def test_expire(self, manager):
        session = manager.create_session("t1", "example.com")
        manager.expire(str(session.id))
        assert session.status == SessionStatus.EXPIRED

    def test_cleanup_expired(self, manager):
        s1 = manager.create_session("t1", "example.com")
        s2 = manager.create_session("t1", "other.com")
        manager.expire(str(s1.id))
        manager.invalidate(str(s2.id))

        removed = manager.cleanup_expired()
        assert removed == 2
        assert manager.total_count == 0

    def test_stats(self, manager):
        manager.create_session("t1", "a.com")
        manager.create_session("t1", "b.com")
        s3 = manager.create_session("t1", "c.com")
        manager.expire(str(s3.id))

        stats = manager.get_stats()
        assert stats["total"] == 3
        assert stats["by_status"][SessionStatus.ACTIVE] == 2
        assert stats["by_status"][SessionStatus.EXPIRED] == 1

    def test_active_count(self, manager):
        manager.create_session("t1", "a.com")
        manager.create_session("t1", "b.com")
        s3 = manager.create_session("t1", "c.com")
        manager.expire(str(s3.id))
        assert manager.active_count == 2

    def test_session_type(self, manager):
        session = manager.create_session("t1", "auth-site.com", session_type=SessionType.AUTHENTICATED)
        assert session.session_type == SessionType.AUTHENTICATED
