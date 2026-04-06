"""
Repository classes for the Zero Checksum Public API.

Each repository handles one entity type and enforces tenant isolation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.storage.models_public_api import (
    ApiKeyModel,
    AsyncJobModel,
    IdempotencyKeyModel,
    RequestAuditLogModel,
    WebhookDeliveryLogModel,
)

logger = logging.getLogger(__name__)


class ApiKeyRepository:
    """CRUD operations for API keys with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> ApiKeyModel:
        api_key = ApiKeyModel(tenant_id=tenant_id, **kwargs)
        self._session.add(api_key)
        await self._session.flush()
        return api_key

    async def get_by_hash(self, key_hash: str) -> Optional[ApiKeyModel]:
        stmt = select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self, tenant_id: str, limit: int = 50, offset: int = 0,
    ) -> tuple[list[ApiKeyModel], int]:
        stmt = (
            select(ApiKeyModel)
            .where(ApiKeyModel.tenant_id == tenant_id)
            .order_by(ApiKeyModel.created_at.desc())
            .limit(limit).offset(offset)
        )
        count_stmt = select(func.count()).select_from(ApiKeyModel).where(
            ApiKeyModel.tenant_id == tenant_id,
        )

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar_one()

    async def revoke(self, api_key_id: str, tenant_id: str) -> Optional[ApiKeyModel]:
        stmt = select(ApiKeyModel).where(
            ApiKeyModel.id == api_key_id,
            ApiKeyModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        api_key = result.scalar_one_or_none()
        if not api_key:
            return None
        api_key.is_active = False
        api_key.revoked_at = datetime.now(timezone.utc)
        await self._session.flush()
        return api_key

    async def update_last_used(self, api_key_id: str) -> None:
        stmt = (
            update(ApiKeyModel)
            .where(ApiKeyModel.id == api_key_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)


class IdempotencyRepository:
    """CRUD operations for idempotency keys."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, tenant_id: str, idempotency_key: str) -> Optional[IdempotencyKeyModel]:
        stmt = select(IdempotencyKeyModel).where(
            IdempotencyKeyModel.tenant_id == tenant_id,
            IdempotencyKeyModel.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def store(self, tenant_id: str, **kwargs) -> IdempotencyKeyModel:
        record = IdempotencyKeyModel(tenant_id=tenant_id, **kwargs)
        self._session.add(record)
        await self._session.flush()
        return record

    async def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc)
        stmt = delete(IdempotencyKeyModel).where(
            IdempotencyKeyModel.expires_at < now,
        )
        result = await self._session.execute(stmt)
        return result.rowcount


class AuditLogRepository:
    """CRUD operations for request audit logs with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> RequestAuditLogModel:
        log = RequestAuditLogModel(tenant_id=tenant_id, **kwargs)
        self._session.add(log)
        await self._session.flush()
        return log

    async def update_response(
        self, request_id: str, tenant_id: str, **kwargs,
    ) -> Optional[RequestAuditLogModel]:
        stmt = select(RequestAuditLogModel).where(
            RequestAuditLogModel.request_id == request_id,
            RequestAuditLogModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        log = result.scalar_one_or_none()
        if not log:
            return None
        for key, value in kwargs.items():
            if hasattr(log, key):
                setattr(log, key, value)
        await self._session.flush()
        return log

    async def query_usage(
        self,
        tenant_id: str,
        start: datetime,
        end: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[RequestAuditLogModel], int]:
        stmt = (
            select(RequestAuditLogModel)
            .where(
                RequestAuditLogModel.tenant_id == tenant_id,
                RequestAuditLogModel.created_at >= start,
                RequestAuditLogModel.created_at <= end,
            )
            .order_by(RequestAuditLogModel.created_at.desc())
            .limit(limit).offset(offset)
        )
        count_stmt = (
            select(func.count())
            .select_from(RequestAuditLogModel)
            .where(
                RequestAuditLogModel.tenant_id == tenant_id,
                RequestAuditLogModel.created_at >= start,
                RequestAuditLogModel.created_at <= end,
            )
        )

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar_one()

    async def get_by_request_id(self, request_id: str, tenant_id: str) -> Optional[RequestAuditLogModel]:
        stmt = select(RequestAuditLogModel).where(
            RequestAuditLogModel.request_id == request_id,
            RequestAuditLogModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class AsyncJobRepository:
    """CRUD operations for async jobs with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> AsyncJobModel:
        job = AsyncJobModel(tenant_id=tenant_id, **kwargs)
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: str, tenant_id: str) -> Optional[AsyncJobModel]:
        stmt = select(AsyncJobModel).where(
            AsyncJobModel.id == job_id,
            AsyncJobModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self, job_id: str, tenant_id: str, **kwargs,
    ) -> Optional[AsyncJobModel]:
        job = await self.get(job_id, tenant_id)
        if not job:
            return None
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        await self._session.flush()
        return job

    async def update_progress(
        self, job_id: str, tenant_id: str, progress: dict,
    ) -> Optional[AsyncJobModel]:
        job = await self.get(job_id, tenant_id)
        if not job:
            return None
        job.progress = progress
        await self._session.flush()
        return job

    async def list_by_tenant(
        self, tenant_id: str, status: Optional[str] = None,
        limit: int = 50, offset: int = 0,
    ) -> tuple[list[AsyncJobModel], int]:
        stmt = select(AsyncJobModel).where(AsyncJobModel.tenant_id == tenant_id)
        count_stmt = select(func.count()).select_from(AsyncJobModel).where(
            AsyncJobModel.tenant_id == tenant_id,
        )

        if status:
            stmt = stmt.where(AsyncJobModel.status == status)
            count_stmt = count_stmt.where(AsyncJobModel.status == status)

        stmt = stmt.order_by(AsyncJobModel.created_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar_one()


class WebhookDeliveryLogRepository:
    """CRUD operations for webhook delivery logs with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> WebhookDeliveryLogModel:
        log = WebhookDeliveryLogModel(tenant_id=tenant_id, **kwargs)
        self._session.add(log)
        await self._session.flush()
        return log

    async def list_by_request(
        self, request_id: str, tenant_id: str,
    ) -> list[WebhookDeliveryLogModel]:
        stmt = (
            select(WebhookDeliveryLogModel)
            .where(
                WebhookDeliveryLogModel.request_id == request_id,
                WebhookDeliveryLogModel.tenant_id == tenant_id,
            )
            .order_by(WebhookDeliveryLogModel.delivered_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def acknowledge(
        self, delivery_id: str, tenant_id: str,
    ) -> Optional[WebhookDeliveryLogModel]:
        stmt = select(WebhookDeliveryLogModel).where(
            WebhookDeliveryLogModel.id == delivery_id,
            WebhookDeliveryLogModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        log = result.scalar_one_or_none()
        if not log:
            return None
        log.acknowledged_at = datetime.now(timezone.utc)
        await self._session.flush()
        return log
