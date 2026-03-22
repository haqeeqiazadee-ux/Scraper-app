"""Result contract — defines extraction result schema."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ResultCreate(BaseModel):
    """Schema for creating a new result."""

    task_id: UUID
    run_id: UUID
    url: str
    extracted_data: list[dict] = Field(default_factory=list)
    item_count: int = 0
    schema_version: str = "1.0"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_method: str = "deterministic"  # "deterministic", "ai", "hybrid", "fallback"
    normalization_applied: bool = False
    dedup_applied: bool = False


class Result(BaseModel):
    """Full result record."""

    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    run_id: UUID
    tenant_id: str
    url: str
    extracted_data: list[dict] = Field(default_factory=list)
    item_count: int = 0
    schema_version: str = "1.0"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_method: str = "deterministic"
    normalization_applied: bool = False
    dedup_applied: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    artifacts: list[UUID] = Field(default_factory=list)

    model_config = {"from_attributes": True}
