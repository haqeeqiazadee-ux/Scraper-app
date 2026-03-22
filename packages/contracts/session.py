"""Session contract — defines session lifecycle schema."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field


class SessionStatus(StrEnum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class SessionType(StrEnum):
    HTTP = "http"
    BROWSER = "browser"
    AUTHENTICATED = "authenticated"


class SessionCreate(BaseModel):
    """Schema for creating a new session."""

    domain: str
    session_type: SessionType = SessionType.HTTP
    cookies: dict = Field(default_factory=dict)
    headers: dict = Field(default_factory=dict)
    proxy_id: Optional[UUID] = None
    browser_profile_id: Optional[str] = None


class Session(BaseModel):
    """Full session record."""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    domain: str
    session_type: SessionType = SessionType.HTTP
    cookies: dict = Field(default_factory=dict)
    headers: dict = Field(default_factory=dict)
    proxy_id: Optional[UUID] = None
    browser_profile_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    status: SessionStatus = SessionStatus.ACTIVE

    @computed_field
    @property
    def health_score(self) -> float:
        """Calculate session health score (0.0 to 1.0)."""
        if self.request_count == 0:
            return 1.0

        success_rate = self.success_count / self.request_count
        # Weighted: 60% success rate, 20% recency, 20% age
        return min(1.0, max(0.0, success_rate * 0.6 + 0.4))

    model_config = {"from_attributes": True}
