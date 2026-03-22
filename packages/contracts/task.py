"""Task contract — defines scraping task schema."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class TaskStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(StrEnum):
    SCRAPE = "scrape"
    MONITOR = "monitor"
    EXTRACT = "extract"


class TaskCreate(BaseModel):
    """Schema for creating a new task via API."""

    url: HttpUrl
    task_type: TaskType = TaskType.SCRAPE
    policy_id: Optional[UUID] = None
    priority: int = Field(default=5, ge=0, le=10)
    schedule: Optional[str] = None
    callback_url: Optional[HttpUrl] = None
    webhook_secret: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    status: Optional[TaskStatus] = None
    priority: Optional[int] = Field(default=None, ge=0, le=10)
    schedule: Optional[str] = None
    callback_url: Optional[HttpUrl] = None
    webhook_secret: Optional[str] = None
    metadata: Optional[dict] = None


class Task(BaseModel):
    """Full task record as stored in the database."""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    url: HttpUrl
    task_type: TaskType = TaskType.SCRAPE
    policy_id: Optional[UUID] = None
    priority: int = Field(default=5, ge=0, le=10)
    schedule: Optional[str] = None
    callback_url: Optional[HttpUrl] = None
    webhook_secret: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING

    model_config = {"from_attributes": True}
