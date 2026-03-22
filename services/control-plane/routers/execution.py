"""Execution routing API endpoints — wire ExecutionRouter into the control plane."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts.policy import LanePreference, Policy
from packages.contracts.task import Task, TaskStatus
from packages.core.router import ExecutionRouter, RouteDecision, Lane
from packages.core.storage.repositories import TaskRepository, PolicyRepository
from services.control_plane.dependencies import get_session, get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level router instance (singleton within the process)
_execution_router = ExecutionRouter()


def _task_model_to_contract(task_model) -> Task:
    """Convert a TaskModel ORM instance to a Task Pydantic contract."""
    return Task(
        id=task_model.id,
        tenant_id=task_model.tenant_id,
        url=task_model.url,
        task_type=task_model.task_type,
        policy_id=task_model.policy_id,
        priority=task_model.priority,
        schedule=task_model.schedule,
        callback_url=task_model.callback_url,
        metadata=task_model.metadata_json or {},
        status=task_model.status,
        created_at=task_model.created_at,
        updated_at=task_model.updated_at,
    )


def _policy_model_to_contract(policy_model) -> Policy:
    """Convert a PolicyModel ORM instance to a Policy Pydantic contract."""
    return Policy(
        id=policy_model.id,
        tenant_id=policy_model.tenant_id,
        name=policy_model.name,
        target_domains=policy_model.target_domains or [],
        preferred_lane=policy_model.preferred_lane,
        extraction_rules=policy_model.extraction_rules or {},
        rate_limit=policy_model.rate_limit or {},
        proxy_policy=policy_model.proxy_policy or {},
        session_policy=policy_model.session_policy or {},
        retry_policy=policy_model.retry_policy or {},
        timeout_ms=policy_model.timeout_ms,
        robots_compliance=policy_model.robots_compliance,
        created_at=policy_model.created_at,
        updated_at=policy_model.updated_at,
    )


def _route_decision_to_dict(decision: RouteDecision) -> dict:
    """Serialize a RouteDecision to a JSON-friendly dict."""
    return {
        "lane": decision.lane.value,
        "reason": decision.reason,
        "fallback_lanes": [l.value for l in decision.fallback_lanes],
        "confidence": decision.confidence,
    }


class DryRunRequest(BaseModel):
    """Request body for dry-run routing."""

    url: HttpUrl
    policy_id: Optional[UUID] = None


@router.post("/tasks/{task_id}/execute")
async def execute_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Trigger execution of a pending task.

    Fetches the task from the database, optionally loads its policy,
    routes through the ExecutionRouter, and returns the route decision.
    """
    task_repo = TaskRepository(session)
    task_model = await task_repo.get(task_id, tenant_id)
    if not task_model:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_model.status != TaskStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Task is not pending (current status: {task_model.status})",
        )

    # Convert ORM model to Pydantic contract for the router
    task = _task_model_to_contract(task_model)

    # Optionally fetch policy
    policy: Optional[Policy] = None
    if task_model.policy_id:
        policy_repo = PolicyRepository(session)
        policy_model = await policy_repo.get(task_model.policy_id, tenant_id)
        if policy_model:
            policy = _policy_model_to_contract(policy_model)

    # Route via ExecutionRouter
    decision = _execution_router.route(task, policy)

    # Update task status to queued
    await task_repo.update(task_id, tenant_id, status=TaskStatus.QUEUED.value)

    logger.info(
        "Task routed for execution",
        extra={
            "task_id": task_id,
            "lane": decision.lane.value,
            "reason": decision.reason,
        },
    )

    return {
        "task_id": task_id,
        "status": "queued",
        "route": _route_decision_to_dict(decision),
    }


@router.post("/route")
async def dry_run_route(
    request: DryRunRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Dry-run routing: determine which lane would be selected for a URL.

    Accepts a URL and optional policy_id, returns the route decision
    without creating or modifying any task.
    """
    # Build a minimal Task contract for the router
    task = Task(
        tenant_id=tenant_id,
        url=request.url,
    )

    # Optionally fetch the policy
    policy: Optional[Policy] = None
    if request.policy_id:
        policy_repo = PolicyRepository(session)
        policy_model = await policy_repo.get(str(request.policy_id), tenant_id)
        if not policy_model:
            raise HTTPException(status_code=404, detail="Policy not found")
        policy = _policy_model_to_contract(policy_model)

    decision = _execution_router.route(task, policy)

    return {
        "url": str(request.url),
        "route": _route_decision_to_dict(decision),
    }
