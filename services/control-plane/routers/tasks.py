"""Task management API endpoints — database-backed."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts.task import Task, TaskCreate, TaskUpdate, TaskStatus
from packages.core.storage.repositories import TaskRepository, RunRepository
from services.control_plane.dependencies import get_session, get_tenant_id

router = APIRouter()


@router.post("/tasks", status_code=201)
async def create_task(
    task_input: TaskCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Submit a new scraping task."""
    repo = TaskRepository(session)
    task_id = str(uuid4())
    task = await repo.create(
        tenant_id=tenant_id,
        id=task_id,
        name=task_input.name,
        url=str(task_input.url),
        task_type=task_input.task_type.value,
        extraction_type=task_input.extraction_type.value if task_input.extraction_type else "auto",
        selectors=task_input.selectors or [],
        policy_id=str(task_input.policy_id) if task_input.policy_id else None,
        priority=task_input.priority,
        schedule=task_input.schedule,
        callback_url=str(task_input.callback_url) if task_input.callback_url else None,
        metadata_json=task_input.metadata,
        status=TaskStatus.PENDING.value,
    )
    return _task_dict(task)


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Get a task by ID."""
    repo = TaskRepository(session)
    task = await repo.get(task_id, tenant_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_dict(task)


@router.get("/tasks")
async def list_tasks(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """List tasks with optional filtering."""
    repo = TaskRepository(session)
    tasks, total = await repo.list(tenant_id, status=status, limit=limit, offset=offset)
    return {
        "items": [_task_list_dict(t) for t in tasks],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Update a task."""
    repo = TaskRepository(session)
    update_data = task_update.model_dump(exclude_unset=True)
    # Convert enums to strings for DB
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value
    if "extraction_type" in update_data and update_data["extraction_type"]:
        update_data["extraction_type"] = update_data["extraction_type"].value
    if "url" in update_data and update_data["url"]:
        update_data["url"] = str(update_data["url"])

    task = await repo.update(task_id, tenant_id, **update_data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_dict(task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> None:
    """Delete a task."""
    repo = TaskRepository(session)
    deleted = await repo.delete(task_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Cancel a pending or running task."""
    repo = TaskRepository(session)
    task = await repo.get(task_id, tenant_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in {task.status} status")

    task = await repo.update(task_id, tenant_id, status="cancelled")
    return {"id": task.id, "status": task.status}


@router.get("/tasks/{task_id}/runs")
async def list_task_runs(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """List execution runs for a task."""
    run_repo = RunRepository(session)
    runs = await run_repo.list_by_task(task_id, tenant_id)
    return {
        "items": [
            {
                "id": r.id,
                "task_id": r.task_id,
                "lane": r.lane,
                "connector": r.connector,
                "status": r.status,
                "status_code": r.status_code,
                "error": r.error,
                "duration_ms": r.duration_ms,
                "bytes_downloaded": r.bytes_downloaded,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ],
        "total": len(runs),
    }


def _task_dict(task) -> dict:
    """Full task representation."""
    return {
        "id": task.id,
        "tenant_id": task.tenant_id,
        "name": task.name or "",
        "url": task.url,
        "task_type": task.task_type,
        "extraction_type": task.extraction_type or "auto",
        "selectors": task.selectors or [],
        "policy_id": task.policy_id,
        "priority": task.priority,
        "schedule": task.schedule,
        "callback_url": task.callback_url,
        "metadata": task.metadata_json,
        "status": task.status,
        "last_run": None,
        "next_run": None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def _task_list_dict(task) -> dict:
    """Summary task for list view."""
    metadata = task.metadata_json or {}
    return {
        "id": task.id,
        "name": task.name or "",
        "url": task.url,
        "task_type": task.task_type,
        "extraction_type": task.extraction_type or "auto",
        "priority": task.priority,
        "status": task.status,
        "last_error": metadata.get("last_error") if task.status == "failed" else None,
        "last_run": None,
        "next_run": None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }

