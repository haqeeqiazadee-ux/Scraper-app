"""
Persistent Session Store — combines in-memory SessionManager with
filesystem persistence for cookies, browser profiles, and headers.
"""

from __future__ import annotations

import logging
from typing import Optional

from packages.contracts.session import Session, SessionStatus, SessionType
from packages.core.session_manager import SessionManager
from packages.core.session_persistence import SessionPersistence

logger = logging.getLogger(__name__)


class PersistentSessionManager:
    """SessionManager with automatic persistence."""

    def __init__(self, persistence: SessionPersistence) -> None:
        self._manager = SessionManager()
        self._persistence = persistence

    # ------------------------------------------------------------------
    # Session creation
    # ------------------------------------------------------------------

    async def create_session(
        self,
        tenant_id: str,
        domain: str,
        session_type: SessionType = SessionType.HTTP,
        proxy_id: Optional[str] = None,
        cookies: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Session:
        """Create session and optionally persist initial cookies/headers."""
        session = self._manager.create_session(
            tenant_id=tenant_id,
            domain=domain,
            session_type=session_type,
            proxy_id=proxy_id,
        )
        sid = str(session.id)

        if cookies:
            session.cookies = cookies
            await self._persistence.save_cookies(sid, cookies)

        if headers:
            session.headers = headers
            await self._persistence.save_headers(sid, headers)

        logger.info(
            "Persistent session created",
            extra={"session_id": sid, "domain": domain},
        )
        return session

    # ------------------------------------------------------------------
    # Get or create with persisted data restore
    # ------------------------------------------------------------------

    async def get_or_create_session(
        self,
        tenant_id: str,
        domain: str,
        session_type: SessionType = SessionType.HTTP,
    ) -> Session:
        """Get existing session or create new one, loading persisted data."""
        existing = self._manager.get_session_for_domain(tenant_id, domain)
        if existing is not None:
            return existing

        session = self._manager.create_session(
            tenant_id=tenant_id,
            domain=domain,
            session_type=session_type,
        )
        sid = str(session.id)

        # Attempt to load previously persisted data
        cookies = await self._persistence.load_cookies(sid)
        if cookies:
            session.cookies = cookies

        headers = await self._persistence.load_headers(sid)
        if headers:
            session.headers = headers

        profile = await self._persistence.load_browser_profile(sid)
        if profile and profile.get("browser_profile_id"):
            session.browser_profile_id = profile["browser_profile_id"]

        return session

    # ------------------------------------------------------------------
    # Cookie updates
    # ------------------------------------------------------------------

    async def update_cookies(self, session_id: str, cookies: dict) -> None:
        """Update and persist cookies."""
        session = self._manager.get_session(session_id)
        if session is None:
            logger.warning(
                "Cannot update cookies — session not found",
                extra={"session_id": session_id},
            )
            return
        session.cookies = cookies
        await self._persistence.save_cookies(session_id, cookies)

    # ------------------------------------------------------------------
    # Header updates
    # ------------------------------------------------------------------

    async def update_headers(self, session_id: str, headers: dict) -> None:
        """Update and persist headers."""
        session = self._manager.get_session(session_id)
        if session is None:
            logger.warning(
                "Cannot update headers — session not found",
                extra={"session_id": session_id},
            )
            return
        session.headers = headers
        await self._persistence.save_headers(session_id, headers)

    # ------------------------------------------------------------------
    # Browser profile updates
    # ------------------------------------------------------------------

    async def update_browser_profile(
        self, session_id: str, profile_data: dict
    ) -> None:
        """Update and persist browser profile."""
        session = self._manager.get_session(session_id)
        if session is None:
            logger.warning(
                "Cannot update browser profile — session not found",
                extra={"session_id": session_id},
            )
            return
        await self._persistence.save_browser_profile(session_id, profile_data)

    # ------------------------------------------------------------------
    # Delegated read operations
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._manager.get_session(session_id)

    def record_success(self, session_id: str) -> None:
        self._manager.record_success(session_id)

    def record_failure(self, session_id: str) -> None:
        self._manager.record_failure(session_id)

    def invalidate(self, session_id: str, reason: str = "") -> None:
        self._manager.invalidate(session_id, reason)

    def get_stats(self) -> dict:
        return self._manager.get_stats()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup(self) -> int:
        """Clean up expired sessions and their persisted data."""
        # Collect IDs that will be removed
        to_remove = [
            sid
            for sid, s in self._manager._sessions.items()
            if s.status in (SessionStatus.EXPIRED, SessionStatus.INVALIDATED)
        ]

        # Delete persisted data for each
        for sid in to_remove:
            await self._persistence.delete_session_data(sid)

        # Remove from in-memory manager
        removed = self._manager.cleanup_expired()
        logger.info("Persistent cleanup complete", extra={"removed": removed})
        return removed

    @property
    def active_count(self) -> int:
        return self._manager.active_count

    @property
    def total_count(self) -> int:
        return self._manager.total_count
