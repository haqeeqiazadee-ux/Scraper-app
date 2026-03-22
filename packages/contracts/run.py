"""Run contract — defines individual execution attempt schema."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"


class RunCreate(BaseModel):
    """Schema for creating a new run record."""

    task_id: UUID
    lane: str
    connector: str
    session_id: Optional[UUID] = None
    proxy_used: Optional[str] = None
    attempt: int = Field(default=1, ge=1)


class Run(BaseModel):
    """Full run record."""

    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    tenant_id: str
    lane: str
    connector: str
    session_id: Optional[UUID] = None
    proxy_used: Optional[str] = None
    attempt: int = Field(default=1, ge=1)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    status: RunStatus = RunStatus.RUNNING
    status_code: Optional[int] = None
    error: Optional[str] = None
    bytes_downloaded: int = 0
    ai_tokens_used: int = 0

    model_config = {"from_attributes": True}
