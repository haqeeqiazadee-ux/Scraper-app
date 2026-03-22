"""
Session Manager — manages session lifecycle, health scoring, and invalidation.

Sessions track cookies, headers, proxy affinity, and health metrics
for reuse across multiple requests to the same domain.
"""

from __future__ import annotations

import logging
import time
from typing import Optional
from uuid import uuid4

from packages.contracts.session import Session, SessionCreate, SessionStatus, SessionType

logger = logging.getLogger(__name__)

# Health thresholds
DEGRADED_THRESHOLD = 0.7
INVALIDATION_THRESHOLD = 0.3
MAX_CONSECUTIVE_FAILURES = 5
MAX_SESSION_AGE_HOURS = 24


class SessionManager:
    """Manages session lifecycle with health scoring and invalidation."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}  # session_id -> Session

    def create_session(
        self,
        tenant_id: str,
        domain: str,
        session_type: SessionType = SessionType.HTTP,
        proxy_id: Optional[str] = None,
    ) -> Session:
        """Create a new session for a domain."""
        session = Session(
            id=uuid4(),
            tenant_id=tenant_id,
            domain=domain,
            session_type=session_type,
            proxy_id=proxy_id if proxy_id else None,
            status=SessionStatus.ACTIVE,
        )
        self._sessions[str(session.id)] = session
        logger.info("Session created", extra={
            "session_id": str(session.id), "domain": domain, "type": session_type,
        })
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_session_for_domain(self, tenant_id: str, domain: str) -> Optional[Session]:
        """Get the best active session for a domain."""
        candidates = [
            s for s in self._sessions.values()
            if s.tenant_id == tenant_id
            and s.domain == domain
            and s.status in (SessionStatus.ACTIVE, SessionStatus.DEGRADED)
        ]
        if not candidates:
            return None
        # Return highest health score session
        return max(candidates, key=lambda s: s.health_score)

    def record_success(self, session_id: str) -> None:
        """Record a successful request on this session."""
        session = self._sessions.get(session_id)
        if not session:
            return
        session.request_count += 1
        session.success_count += 1
        self._update_status(session)

    def record_failure(self, session_id: str) -> None:
        """Record a failed request and potentially degrade/invalidate."""
        session = self._sessions.get(session_id)
        if not session:
            return
        session.request_count += 1
        session.failure_count += 1
        self._update_status(session)

    def invalidate(self, session_id: str, reason: str = "") -> None:
        """Manually invalidate a session."""
        session = self._sessions.get(session_id)
        if session:
            session.status = SessionStatus.INVALIDATED
            logger.info("Session invalidated", extra={
                "session_id": session_id, "reason": reason,
            })

    def expire(self, session_id: str) -> None:
        """Mark a session as expired."""
        session = self._sessions.get(session_id)
        if session:
            session.status = SessionStatus.EXPIRED

    def cleanup_expired(self) -> int:
        """Remove expired and invalidated sessions. Returns count removed."""
        to_remove = [
            sid for sid, s in self._sessions.items()
            if s.status in (SessionStatus.EXPIRED, SessionStatus.INVALIDATED)
        ]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)

    def get_stats(self) -> dict:
        """Get session pool statistics."""
        statuses = {}
        for session in self._sessions.values():
            statuses[session.status] = statuses.get(session.status, 0) + 1
        return {
            "total": len(self._sessions),
            "by_status": statuses,
        }

    def _update_status(self, session: Session) -> None:
        """Update session status based on health score."""
        score = session.health_score

        if score >= DEGRADED_THRESHOLD:
            if session.status == SessionStatus.DEGRADED:
                session.status = SessionStatus.ACTIVE  # Recovered
        elif score >= INVALIDATION_THRESHOLD:
            session.status = SessionStatus.DEGRADED
        else:
            # Check consecutive failures
            consecutive = session.failure_count - session.success_count
            if consecutive >= MAX_CONSECUTIVE_FAILURES:
                session.status = SessionStatus.INVALIDATED
                logger.warning("Session auto-invalidated", extra={
                    "session_id": str(session.id),
                    "health_score": f"{score:.2f}",
                    "consecutive_failures": consecutive,
                })

    @property
    def active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == SessionStatus.ACTIVE)

    @property
    def total_count(self) -> int:
        return len(self._sessions)
