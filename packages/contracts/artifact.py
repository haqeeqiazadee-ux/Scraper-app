"""Artifact contract — defines stored artifact schema."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ArtifactType(StrEnum):
    HTML_SNAPSHOT = "html_snapshot"
    SCREENSHOT = "screenshot"
    EXPORT_XLSX = "export_xlsx"
    EXPORT_JSON = "export_json"
    EXPORT_CSV = "export_csv"


class ArtifactCreate(BaseModel):
    """Schema for creating a new artifact."""

    result_id: UUID
    artifact_type: ArtifactType
    storage_path: str
    content_type: str
    size_bytes: int = Field(ge=0)
    checksum: str


class Artifact(BaseModel):
    """Full artifact record."""

    id: UUID = Field(default_factory=uuid4)
    result_id: UUID
    tenant_id: str
    artifact_type: ArtifactType
    storage_path: str
    content_type: str
    size_bytes: int = Field(ge=0)
    checksum: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
