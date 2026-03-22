"""Tests for session persistence and persistent session manager."""

import json

import pytest

from packages.contracts.session import SessionStatus, SessionType
from packages.core.session_persistence import SessionPersistence
from packages.core.session_store import PersistentSessionManager


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def storage_path(tmp_path):
    return str(tmp_path / "session_data")


@pytest.fixture
def persistence(storage_path):
    return SessionPersistence(storage_path=storage_path)


@pytest.fixture
def persistent_manager(persistence):
    return PersistentSessionManager(persistence=persistence)


# ======================================================================
# SessionPersistence — cookies
# ======================================================================


class TestCookiePersistence:

    @pytest.mark.asyncio
    async def test_save_and_load_cookies(self, persistence):
        cookies = {"session_token": "abc123", "csrf": "xyz789"}
        await persistence.save_cookies("s1", cookies)

        loaded = await persistence.load_cookies("s1")
        assert loaded == cookies

    @pytest.mark.asyncio
    async def test_load_cookies_missing(self, persistence):
        result = await persistence.load_cookies("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_overwrite_cookies(self, persistence):
        await persistence.save_cookies("s1", {"old": "value"})
        await persistence.save_cookies("s1", {"new": "value"})

        loaded = await persistence.load_cookies("s1")
        assert loaded == {"new": "value"}


# ======================================================================
# SessionPersistence — browser profile
# ======================================================================


class TestBrowserProfilePersistence:

    @pytest.mark.asyncio
    async def test_save_and_load_browser_profile(self, persistence):
        profile = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
            "timezone": "America/New_York",
            "browser_profile_id": "profile-001",
        }
        await persistence.save_browser_profile("s1", profile)

        loaded = await persistence.load_browser_profile("s1")
        assert loaded == profile

    @pytest.mark.asyncio
    async def test_load_browser_profile_missing(self, persistence):
        result = await persistence.load_browser_profile("nonexistent")
        assert result is None


# ======================================================================
# SessionPersistence — headers
# ======================================================================


class TestHeadersPersistence:

    @pytest.mark.asyncio
    async def test_save_and_load_headers(self, persistence):
        headers = {
            "Authorization": "Bearer token123",
            "Accept-Language": "en-US,en;q=0.9",
        }
        await persistence.save_headers("s1", headers)

        loaded = await persistence.load_headers("s1")
        assert loaded == headers

    @pytest.mark.asyncio
    async def test_load_headers_missing(self, persistence):
        result = await persistence.load_headers("nonexistent")
        assert result is None


# ======================================================================
# SessionPersistence — delete
# ======================================================================


class TestDeleteSessionData:

    @pytest.mark.asyncio
    async def test_delete_session_data(self, persistence, storage_path):
        await persistence.save_cookies("s1", {"a": "1"})
        await persistence.save_headers("s1", {"b": "2"})
        await persistence.save_browser_profile("s1", {"c": "3"})

        await persistence.delete_session_data("s1")

        assert await persistence.load_cookies("s1") is None
        assert await persistence.load_headers("s1") is None
        assert await persistence.load_browser_profile("s1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, persistence):
        # Should not raise
        await persistence.delete_session_data("nonexistent")


# ======================================================================
# SessionPersistence — list sessions
# ======================================================================


class TestListSessions:

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, persistence):
        sessions = await persistence.list_sessions()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_sessions(self, persistence):
        await persistence.save_cookies("session-a", {"x": "1"})
        await persistence.save_cookies("session-b", {"y": "2"})
        await persistence.save_cookies("session-c", {"z": "3"})

        sessions = await persistence.list_sessions()
        assert sessions == ["session-a", "session-b", "session-c"]

    @pytest.mark.asyncio
    async def test_list_sessions_after_delete(self, persistence):
        await persistence.save_cookies("s1", {})
        await persistence.save_cookies("s2", {})
        await persistence.delete_session_data("s1")

        sessions = await persistence.list_sessions()
        assert sessions == ["s2"]


# ======================================================================
# SessionPersistence — JSON file format
# ======================================================================


class TestStorageFormat:

    @pytest.mark.asyncio
    async def test_cookies_stored_as_json(self, persistence, storage_path):
        from pathlib import Path

        cookies = {"token": "abc"}
        await persistence.save_cookies("s1", cookies)

        path = Path(storage_path) / "s1" / "cookies.json"
        assert path.exists()

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == cookies

    @pytest.mark.asyncio
    async def test_profile_stored_as_json(self, persistence, storage_path):
        from pathlib import Path

        profile = {"user_agent": "test-agent"}
        await persistence.save_browser_profile("s1", profile)

        path = Path(storage_path) / "s1" / "profile.json"
        assert path.exists()

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == profile

    @pytest.mark.asyncio
    async def test_headers_stored_as_json(self, persistence, storage_path):
        from pathlib import Path

        headers = {"X-Custom": "value"}
        await persistence.save_headers("s1", headers)

        path = Path(storage_path) / "s1" / "headers.json"
        assert path.exists()

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == headers


# ======================================================================
# PersistentSessionManager — create with persistence
# ======================================================================


class TestPersistentSessionManagerCreate:

    @pytest.mark.asyncio
    async def test_create_session_no_cookies(self, persistent_manager):
        session = await persistent_manager.create_session("t1", "example.com")
        assert session.domain == "example.com"
        assert session.tenant_id == "t1"
        assert session.status == SessionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_session_with_cookies(self, persistent_manager, persistence):
        cookies = {"sid": "abc"}
        session = await persistent_manager.create_session(
            "t1", "example.com", cookies=cookies
        )

        assert session.cookies == cookies
        # Verify persistence
        loaded = await persistence.load_cookies(str(session.id))
        assert loaded == cookies

    @pytest.mark.asyncio
    async def test_create_session_with_headers(self, persistent_manager, persistence):
        headers = {"Authorization": "Bearer tok"}
        session = await persistent_manager.create_session(
            "t1", "example.com", headers=headers
        )

        assert session.headers == headers
        loaded = await persistence.load_headers(str(session.id))
        assert loaded == headers

    @pytest.mark.asyncio
    async def test_create_session_with_cookies_and_headers(
        self, persistent_manager, persistence
    ):
        cookies = {"c": "1"}
        headers = {"h": "2"}
        session = await persistent_manager.create_session(
            "t1", "example.com", cookies=cookies, headers=headers
        )

        assert session.cookies == cookies
        assert session.headers == headers
        assert await persistence.load_cookies(str(session.id)) == cookies
        assert await persistence.load_headers(str(session.id)) == headers

    @pytest.mark.asyncio
    async def test_create_session_type(self, persistent_manager):
        session = await persistent_manager.create_session(
            "t1", "example.com", session_type=SessionType.BROWSER
        )
        assert session.session_type == SessionType.BROWSER


# ======================================================================
# PersistentSessionManager — get_or_create
# ======================================================================


class TestGetOrCreateSession:

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(self, persistent_manager):
        s1 = await persistent_manager.create_session("t1", "example.com")
        s2 = await persistent_manager.get_or_create_session("t1", "example.com")
        assert s1.id == s2.id

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(self, persistent_manager):
        session = await persistent_manager.get_or_create_session("t1", "new.com")
        assert session.domain == "new.com"
        assert session.status == SessionStatus.ACTIVE


# ======================================================================
# PersistentSessionManager — update operations
# ======================================================================


class TestUpdateOperations:

    @pytest.mark.asyncio
    async def test_update_cookies(self, persistent_manager, persistence):
        session = await persistent_manager.create_session("t1", "example.com")
        sid = str(session.id)

        new_cookies = {"updated": "cookie"}
        await persistent_manager.update_cookies(sid, new_cookies)

        assert session.cookies == new_cookies
        assert await persistence.load_cookies(sid) == new_cookies

    @pytest.mark.asyncio
    async def test_update_cookies_nonexistent_session(self, persistent_manager):
        # Should not raise
        await persistent_manager.update_cookies("nonexistent", {"a": "b"})

    @pytest.mark.asyncio
    async def test_update_headers(self, persistent_manager, persistence):
        session = await persistent_manager.create_session("t1", "example.com")
        sid = str(session.id)

        new_headers = {"X-New": "header"}
        await persistent_manager.update_headers(sid, new_headers)

        assert session.headers == new_headers
        assert await persistence.load_headers(sid) == new_headers

    @pytest.mark.asyncio
    async def test_update_browser_profile(self, persistent_manager, persistence):
        session = await persistent_manager.create_session("t1", "example.com")
        sid = str(session.id)

        profile = {"user_agent": "new-agent", "viewport": {"width": 800, "height": 600}}
        await persistent_manager.update_browser_profile(sid, profile)

        assert await persistence.load_browser_profile(sid) == profile


# ======================================================================
# PersistentSessionManager — cleanup
# ======================================================================


class TestCleanup:

    @pytest.mark.asyncio
    async def test_cleanup_removes_persisted_data(self, persistent_manager, persistence):
        s1 = await persistent_manager.create_session(
            "t1", "a.com", cookies={"c": "1"}
        )
        s2 = await persistent_manager.create_session(
            "t1", "b.com", cookies={"c": "2"}
        )
        s3 = await persistent_manager.create_session(
            "t1", "c.com", cookies={"c": "3"}
        )

        # Expire s1, invalidate s2, keep s3 active
        persistent_manager.invalidate(str(s1.id), reason="blocked")
        persistent_manager._manager.expire(str(s2.id))

        removed = await persistent_manager.cleanup()
        assert removed == 2

        # Persisted data for s1 and s2 should be gone
        assert await persistence.load_cookies(str(s1.id)) is None
        assert await persistence.load_cookies(str(s2.id)) is None

        # s3 should still be there
        assert await persistence.load_cookies(str(s3.id)) == {"c": "3"}

    @pytest.mark.asyncio
    async def test_cleanup_empty(self, persistent_manager):
        removed = await persistent_manager.cleanup()
        assert removed == 0

    @pytest.mark.asyncio
    async def test_cleanup_counts(self, persistent_manager):
        s1 = await persistent_manager.create_session("t1", "a.com")
        persistent_manager.invalidate(str(s1.id))

        removed = await persistent_manager.cleanup()
        assert removed == 1
        assert persistent_manager.total_count == 0


# ======================================================================
# PersistentSessionManager — delegated operations
# ======================================================================


class TestDelegatedOperations:

    @pytest.mark.asyncio
    async def test_get_session(self, persistent_manager):
        session = await persistent_manager.create_session("t1", "example.com")
        found = persistent_manager.get_session(str(session.id))
        assert found is not None
        assert found.id == session.id

    @pytest.mark.asyncio
    async def test_record_success(self, persistent_manager):
        session = await persistent_manager.create_session("t1", "example.com")
        persistent_manager.record_success(str(session.id))
        assert session.request_count == 1
        assert session.success_count == 1

    @pytest.mark.asyncio
    async def test_record_failure(self, persistent_manager):
        session = await persistent_manager.create_session("t1", "example.com")
        persistent_manager.record_failure(str(session.id))
        assert session.request_count == 1
        assert session.failure_count == 1

    @pytest.mark.asyncio
    async def test_get_stats(self, persistent_manager):
        await persistent_manager.create_session("t1", "a.com")
        stats = persistent_manager.get_stats()
        assert stats["total"] == 1

    @pytest.mark.asyncio
    async def test_active_and_total_count(self, persistent_manager):
        await persistent_manager.create_session("t1", "a.com")
        await persistent_manager.create_session("t1", "b.com")
        assert persistent_manager.active_count == 2
        assert persistent_manager.total_count == 2
