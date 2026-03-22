"""Policy contract — defines extraction policy schema."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LanePreference(StrEnum):
    API = "api"
    HTTP = "http"
    BROWSER = "browser"
    HARD_TARGET = "hard_target"
    AUTO = "auto"


class RateLimit(BaseModel):
    """Rate limiting configuration."""

    max_requests_per_minute: int = Field(default=60, ge=1)
    max_requests_per_hour: int = Field(default=1000, ge=1)
    max_concurrent: int = Field(default=5, ge=1)


class ProxyPolicy(BaseModel):
    """Proxy usage configuration."""

    enabled: bool = True
    geo: Optional[str] = None
    proxy_type: Optional[str] = None  # "datacenter", "residential", "mobile"
    rotation_strategy: str = "weighted"  # "round_robin", "random", "weighted", "sticky", "geo"
    sticky_session: bool = False


class SessionPolicy(BaseModel):
    """Session reuse configuration."""

    reuse_sessions: bool = True
    max_session_age_minutes: int = Field(default=60, ge=1)
    max_requests_per_session: int = Field(default=100, ge=1)
    rotate_on_failure: bool = True


class RetryPolicy(BaseModel):
    """Retry configuration."""

    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_base_seconds: float = Field(default=2.0, ge=0.1)
    backoff_max_seconds: float = Field(default=60.0, ge=1.0)
    retry_on_status_codes: list[int] = Field(default_factory=lambda: [429, 500, 502, 503, 504])


class PolicyCreate(BaseModel):
    """Schema for creating a new policy via API."""

    name: str = Field(min_length=1, max_length=255)
    target_domains: list[str] = Field(default_factory=list)
    preferred_lane: LanePreference = LanePreference.AUTO
    extraction_rules: dict = Field(default_factory=dict)
    rate_limit: RateLimit = Field(default_factory=RateLimit)
    proxy_policy: ProxyPolicy = Field(default_factory=ProxyPolicy)
    session_policy: SessionPolicy = Field(default_factory=SessionPolicy)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    robots_compliance: bool = True


class PolicyUpdate(BaseModel):
    """Schema for updating a policy."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    target_domains: Optional[list[str]] = None
    preferred_lane: Optional[LanePreference] = None
    extraction_rules: Optional[dict] = None
    rate_limit: Optional[RateLimit] = None
    proxy_policy: Optional[ProxyPolicy] = None
    session_policy: Optional[SessionPolicy] = None
    retry_policy: Optional[RetryPolicy] = None
    timeout_ms: Optional[int] = Field(default=None, ge=1000, le=300000)
    robots_compliance: Optional[bool] = None


class Policy(BaseModel):
    """Full policy record as stored in the database."""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    name: str
    target_domains: list[str] = Field(default_factory=list)
    preferred_lane: LanePreference = LanePreference.AUTO
    extraction_rules: dict = Field(default_factory=dict)
    rate_limit: RateLimit = Field(default_factory=RateLimit)
    proxy_policy: ProxyPolicy = Field(default_factory=ProxyPolicy)
    session_policy: SessionPolicy = Field(default_factory=SessionPolicy)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    robots_compliance: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
