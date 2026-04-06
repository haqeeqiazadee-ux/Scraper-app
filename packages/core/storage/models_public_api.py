"""
SQLAlchemy ORM models for the Zero Checksum Public API.

Extends the metadata store with tables for API keys, idempotency,
audit logging, async jobs, and webhook delivery tracking.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text, JSON,
    ForeignKey, Index,
)

from packages.core.storage.models import Base


def gen_uuid() -> str:
    return str(uuid4())


class ApiKeyModel(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(255), nullable=False, index=True)
    key_hash = Column(String(64), nullable=False, unique=True)
    key_prefix = Column(String(12), nullable=False)
    name = Column(String(255), nullable=False)
    scopes = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_api_keys_key_hash", "key_hash"),
        Index("ix_api_keys_tenant_active", "tenant_id", "is_active"),
        Index("ix_api_keys_tenant_created", "tenant_id", "created_at"),
    )


class IdempotencyKeyModel(Base):
    __tablename__ = "idempotency_keys"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(255), nullable=False, index=True)
    idempotency_key = Column(String(255), nullable=False)
    request_id = Column(String(36), nullable=False)
    endpoint = Column(String(255), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_idempotency_tenant_key", "tenant_id", "idempotency_key", unique=True),
        Index("ix_idempotency_expires", "expires_at"),
    )


class RequestAuditLogModel(Base):
    __tablename__ = "request_audit_log"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    request_id = Column(String(36), nullable=False, unique=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    api_key_id = Column(String(36), ForeignKey("api_keys.id"), nullable=True)
    method = Column(String(10), nullable=False)
    endpoint = Column(String(255), nullable=False)
    request_body_hash = Column(String(64), nullable=True)
    idempotency_key = Column(String(255), nullable=True)
    status_code = Column(Integer, nullable=True)
    credits_used = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=False, default=0)
    error_code = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_audit_request_id", "request_id"),
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_tenant_endpoint", "tenant_id", "endpoint"),
    )


class AsyncJobModel(Base):
    __tablename__ = "async_jobs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    request_id = Column(String(36), nullable=False)
    tenant_id = Column(String(255), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    input_params = Column(JSON, nullable=False, default=dict)
    result_data = Column(JSON, nullable=True)
    credits_used = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    webhook_url = Column(Text, nullable=True)
    progress = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_jobs_tenant_created", "tenant_id", "created_at"),
        Index("ix_jobs_request_id", "request_id"),
    )


class WebhookDeliveryLogModel(Base):
    __tablename__ = "webhook_delivery_log"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    request_id = Column(String(36), nullable=False)
    tenant_id = Column(String(255), nullable=False, index=True)
    webhook_url = Column(Text, nullable=False)
    event_type = Column(String(100), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    attempt = Column(Integer, nullable=False, default=1)
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    error = Column(Text, nullable=True)
    delivered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_webhook_tenant_request", "tenant_id", "request_id"),
        Index("ix_webhook_tenant_event", "tenant_id", "event_type"),
        Index("ix_webhook_delivered", "delivered_at"),
    )
