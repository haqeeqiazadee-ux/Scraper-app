"""Task management API endpoints."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from packages.contracts.task import Task, TaskCreate, TaskUpdate, TaskStatus

router = APIRouter()

# In-memory store for scaffolding (will be replaced by database)
_tasks: dict[UUID, Task] = {}


@router.post("/tasks", status_code=201)
async def create_task(task_input: TaskCreate) -> Task:
    """Submit a new scraping task."""
    task = Task(
        id=uuid4(),
        tenant_id="default",  # TODO: Extract from auth middleware
        url=task_input.url,
        task_type=task_input.task_type,
        policy_id=task_input.policy_id,
        priority=task_input.priority,
        schedule=task_input.schedule,
        callback_url=task_input.callback_url,
        metadata=task_input.metadata,
        status=TaskStatus.PENDING,
    )
    _tasks[task.id] = task
    # TODO: Enqueue task to Redis queue
    # TODO: Route task to execution lane
    return task


@router.get("/tasks/{task_id}")
async def get_task(task_id: UUID) -> Task:
    """Get a task by ID."""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks")
async def list_tasks(
    status: TaskStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List tasks with optional filtering."""
    tasks = list(_tasks.values())
    if status:
        tasks = [t for t in tasks if t.status == status]

    total = len(tasks)
    tasks = tasks[offset : offset + limit]

    return {
        "items": tasks,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/tasks/{task_id}")
async def update_task(task_id: UUID, task_update: TaskUpdate) -> Task:
    """Update a task."""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    return task


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: UUID) -> Task:
    """Cancel a pending or running task."""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in {task.status} status")

    task.status = TaskStatus.CANCELLED
    # TODO: Send cancellation signal to worker
    return task
