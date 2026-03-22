"""
SQLAlchemy ORM models for the metadata store.

Maps Pydantic contract schemas to database tables.
Supports both PostgreSQL and SQLite backends.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text, JSON,
    ForeignKey, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def gen_uuid() -> str:
    return str(uuid4())


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(255), nullable=False, index=True)
    url = Column(Text, nullable=False)
    task_type = Column(String(50), nullable=False, default="scrape")
    policy_id = Column(String(36), nullable=True)
    priority = Column(Integer, nullable=False, default=5)
    schedule = Column(String(255), nullable=True)
    callback_url = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    runs = relationship("RunModel", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_tasks_tenant_status", "tenant_id", "status"),
        Index("ix_tasks_tenant_created", "tenant_id", "created_at"),
    )


class PolicyModel(Base):
    __tablename__ = "policies"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    target_domains = Column(JSON, nullable=False, default=list)
    preferred_lane = Column(String(50), nullable=False, default="auto")
    extraction_rules = Column(JSON, nullable=False, default=dict)
    rate_limit = Column(JSON, nullable=False, default=dict)
    proxy_policy = Column(JSON, nullable=False, default=dict)
    session_policy = Column(JSON, nullable=False, default=dict)
    retry_policy = Column(JSON, nullable=False, default=dict)
    timeout_ms = Column(Integer, nullable=False, default=30000)
    robots_compliance = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    session_type = Column(String(50), nullable=False, default="http")
    cookies = Column(JSON, nullable=False, default=dict)
    headers = Column(JSON, nullable=False, default=dict)
    proxy_id = Column(String(36), nullable=True)
    browser_profile_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="active")
    request_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class RunModel(Base):
    __tablename__ = "runs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    lane = Column(String(50), nullable=False)
    connector = Column(String(100), nullable=False)
    session_id = Column(String(36), nullable=True)
    proxy_used = Column(String(255), nullable=True)
    attempt = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, default="running")
    status_code = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    bytes_downloaded = Column(Integer, nullable=False, default=0)
    ai_tokens_used = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    task = relationship("TaskModel", back_populates="runs")


class ResultModel(Base):
    __tablename__ = "results"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False)
    tenant_id = Column(String(255), nullable=False, index=True)
    url = Column(Text, nullable=False)
    extracted_data = Column(JSON, nullable=False, default=list)
    item_count = Column(Integer, nullable=False, default=0)
    schema_version = Column(String(20), nullable=False, default="1.0")
    confidence = Column(Float, nullable=False, default=0.0)
    extraction_method = Column(String(50), nullable=False, default="deterministic")
    normalization_applied = Column(Boolean, nullable=False, default=False)
    dedup_applied = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    artifacts_json = Column(JSON, nullable=False, default=list)


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    result_id = Column(String(36), ForeignKey("results.id"), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    artifact_type = Column(String(50), nullable=False)
    storage_path = Column(Text, nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False, default=0)
    checksum = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
