"""
Repository classes for database CRUD operations.

Each repository handles one entity type and enforces tenant isolation.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.storage.models import TaskModel, PolicyModel, RunModel, ResultModel, ArtifactModel

logger = logging.getLogger(__name__)


class TaskRepository:
    """CRUD operations for tasks with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> TaskModel:
        task = TaskModel(tenant_id=tenant_id, **kwargs)
        self._session.add(task)
        await self._session.flush()
        return task

    async def get(self, task_id: str, tenant_id: str) -> Optional[TaskModel]:
        stmt = select(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, tenant_id: str, status: Optional[str] = None,
        limit: int = 50, offset: int = 0,
    ) -> tuple[list[TaskModel], int]:
        stmt = select(TaskModel).where(TaskModel.tenant_id == tenant_id)
        count_stmt = select(func.count()).select_from(TaskModel).where(TaskModel.tenant_id == tenant_id)

        if status:
            stmt = stmt.where(TaskModel.status == status)
            count_stmt = count_stmt.where(TaskModel.status == status)

        stmt = stmt.order_by(TaskModel.created_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar_one()

    async def update(self, task_id: str, tenant_id: str, **kwargs) -> Optional[TaskModel]:
        task = await self.get(task_id, tenant_id)
        if not task:
            return None
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        await self._session.flush()
        return task

    async def delete(self, task_id: str, tenant_id: str) -> bool:
        stmt = delete(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0


class PolicyRepository:
    """CRUD operations for policies with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> PolicyModel:
        policy = PolicyModel(tenant_id=tenant_id, **kwargs)
        self._session.add(policy)
        await self._session.flush()
        return policy

    async def get(self, policy_id: str, tenant_id: str) -> Optional[PolicyModel]:
        stmt = select(PolicyModel).where(
            PolicyModel.id == policy_id,
            PolicyModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, tenant_id: str, limit: int = 50, offset: int = 0) -> tuple[list[PolicyModel], int]:
        stmt = (
            select(PolicyModel)
            .where(PolicyModel.tenant_id == tenant_id)
            .order_by(PolicyModel.created_at.desc())
            .limit(limit).offset(offset)
        )
        count_stmt = select(func.count()).select_from(PolicyModel).where(PolicyModel.tenant_id == tenant_id)

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar_one()

    async def update(self, policy_id: str, tenant_id: str, **kwargs) -> Optional[PolicyModel]:
        policy = await self.get(policy_id, tenant_id)
        if not policy:
            return None
        for key, value in kwargs.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        await self._session.flush()
        return policy

    async def delete(self, policy_id: str, tenant_id: str) -> bool:
        stmt = delete(PolicyModel).where(
            PolicyModel.id == policy_id,
            PolicyModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0


class RunRepository:
    """CRUD operations for runs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> RunModel:
        run = RunModel(tenant_id=tenant_id, **kwargs)
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, run_id: str, tenant_id: str) -> Optional[RunModel]:
        stmt = select(RunModel).where(RunModel.id == run_id, RunModel.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, run_id: str, tenant_id: str, **kwargs) -> Optional[RunModel]:
        run = await self.get(run_id, tenant_id)
        if not run:
            return None
        for key, value in kwargs.items():
            if hasattr(run, key):
                setattr(run, key, value)
        await self._session.flush()
        return run

    async def list_by_task(self, task_id: str, tenant_id: str) -> list[RunModel]:
        stmt = (
            select(RunModel)
            .where(RunModel.task_id == task_id, RunModel.tenant_id == tenant_id)
            .order_by(RunModel.started_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class ResultRepository:
    """CRUD operations for results."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> ResultModel:
        result_obj = ResultModel(tenant_id=tenant_id, **kwargs)
        self._session.add(result_obj)
        await self._session.flush()
        return result_obj

    async def get(self, result_id: str, tenant_id: str) -> Optional[ResultModel]:
        stmt = select(ResultModel).where(ResultModel.id == result_id, ResultModel.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, tenant_id: str, limit: int = 50, offset: int = 0,
        min_confidence: float | None = None, sort_by: str = "created_at", sort_order: str = "desc",
    ) -> tuple[list[ResultModel], int]:
        stmt = select(ResultModel).where(ResultModel.tenant_id == tenant_id)
        count_stmt = select(func.count()).select_from(ResultModel).where(ResultModel.tenant_id == tenant_id)

        if min_confidence is not None:
            stmt = stmt.where(ResultModel.confidence >= min_confidence)
            count_stmt = count_stmt.where(ResultModel.confidence >= min_confidence)

        col = getattr(ResultModel, sort_by, ResultModel.created_at)
        stmt = stmt.order_by(col.desc() if sort_order == "desc" else col.asc())
        stmt = stmt.offset(offset).limit(limit)

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)
        return list(result.scalars().all()), count_result.scalar() or 0

    async def list_by_task(self, task_id: str, tenant_id: str) -> list[ResultModel]:
        stmt = (
            select(ResultModel)
            .where(ResultModel.task_id == task_id, ResultModel.tenant_id == tenant_id)
            .order_by(ResultModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class ArtifactRepository:
    """CRUD operations for artifacts with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> ArtifactModel:
        artifact = ArtifactModel(tenant_id=tenant_id, **kwargs)
        self._session.add(artifact)
        await self._session.flush()
        return artifact

    async def get(self, artifact_id: str, tenant_id: str) -> Optional[ArtifactModel]:
        stmt = select(ArtifactModel).where(
            ArtifactModel.id == artifact_id,
            ArtifactModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_result(self, result_id: str, tenant_id: str) -> list[ArtifactModel]:
        stmt = (
            select(ArtifactModel)
            .where(ArtifactModel.result_id == result_id, ArtifactModel.tenant_id == tenant_id)
            .order_by(ArtifactModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_tenant(
        self, tenant_id: str, limit: int = 50, offset: int = 0,
    ) -> tuple[list[ArtifactModel], int]:
        stmt = (
            select(ArtifactModel)
            .where(ArtifactModel.tenant_id == tenant_id)
            .order_by(ArtifactModel.created_at.desc())
            .limit(limit).offset(offset)
        )
        count_stmt = select(func.count()).select_from(ArtifactModel).where(
            ArtifactModel.tenant_id == tenant_id,
        )

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar_one()

    async def delete(self, artifact_id: str, tenant_id: str) -> bool:
        stmt = delete(ArtifactModel).where(
            ArtifactModel.id == artifact_id,
            ArtifactModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0
