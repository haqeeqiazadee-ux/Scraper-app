"""Schedule management API endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts.task import Task, TaskCreate, TaskStatus
from packages.core.scheduler import TaskScheduler, ScheduleEntry
from services.control_plane.dependencies import get_session, get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level scheduler instance — initialized during app startup.
# The enqueue function is set when the scheduler is wired into the app.
_scheduler: TaskScheduler | None = None


def get_scheduler() -> TaskScheduler:
    """Get the global scheduler instance."""
    if _scheduler is None:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not initialized",
        )
    return _scheduler


def set_scheduler(scheduler: TaskScheduler) -> None:
    """Set the global scheduler instance (called during app startup)."""
    global _scheduler
    _scheduler = scheduler


class ScheduleCreateRequest(BaseModel):
    """Request body for creating a schedule."""

    url: HttpUrl
    schedule: str
    task_type: str = "scrape"
    priority: int = 5
    callback_url: HttpUrl | None = None
    webhook_secret: str | None = None
    metadata: dict = {}


class ScheduleResponse(BaseModel):
    """Response for a schedule entry."""

    schedule_id: str
    task_id: str
    schedule: str
    schedule_type: str
    active: bool
    url: str
    created_at: str | None = None
    last_fired: str | None = None


def _entry_to_response(entry: ScheduleEntry) -> ScheduleResponse:
    """Convert a ScheduleEntry to an API response."""
    return ScheduleResponse(
        schedule_id=str(entry.id),
        task_id=str(entry.task.id),
        schedule=entry.task.schedule or "",
        schedule_type=entry.schedule_type,
        active=entry.active,
        url=str(entry.task.url),
        created_at=entry.created_at.isoformat() if entry.created_at else None,
        last_fired=entry.last_fired.isoformat() if entry.last_fired else None,
    )


@router.get("/schedules")
async def list_schedules(
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """List all scheduled tasks for the tenant."""
    scheduler = get_scheduler()
    entries = [
        _entry_to_response(entry)
        for entry in scheduler.schedules.values()
        if entry.task.tenant_id == tenant_id
    ]
    return {
        "items": [e.model_dump() for e in entries],
        "total": len(entries),
    }


@router.post("/schedules", status_code=201)
async def create_schedule(
    request: ScheduleCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Create a new scheduled task."""
    scheduler = get_scheduler()

    task = Task(
        tenant_id=tenant_id,
        url=request.url,
        task_type=request.task_type,
        priority=request.priority,
        schedule=request.schedule,
        callback_url=request.callback_url,
        webhook_secret=request.webhook_secret,
        metadata=request.metadata,
        status=TaskStatus.PENDING,
    )

    try:
        entry = await scheduler.add_schedule(task)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info(
        "Schedule created via API",
        extra={
            "schedule_id": str(entry.id),
            "tenant_id": tenant_id,
        },
    )
    return _entry_to_response(entry).model_dump()


@router.get("/schedules/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Get schedule details by ID."""
    scheduler = get_scheduler()
    try:
        sid = UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule ID format")

    entry = scheduler.schedules.get(sid)
    if entry is None or entry.task.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return _entry_to_response(entry).model_dump()


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Remove a schedule."""
    scheduler = get_scheduler()
    try:
        sid = UUID(schedule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid schedule ID format")

    # Check ownership
    entry = scheduler.schedules.get(sid)
    if entry is None or entry.task.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    removed = await scheduler.remove_schedule(sid)
    if not removed:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {"schedule_id": schedule_id, "status": "removed"}
