"""Execution routing API endpoints — wire ExecutionRouter into the control plane."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts.policy import LanePreference, Policy
from packages.contracts.task import Task, TaskStatus
from packages.contracts.result import Result
from packages.core.router import ExecutionRouter, RouteDecision, Lane
from packages.core.webhook import WebhookExecutor
from packages.core.storage.repositories import TaskRepository, PolicyRepository, ResultRepository, RunRepository
from services.control_plane.dependencies import get_session, get_database, get_tenant_id

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


async def _run_task_inline(task_id: str, tenant_id: str, url: str, lane: str, extraction_config: dict) -> None:
    """Execute a scraping task inline via asyncio.create_task.

    Runs the HTTP worker directly in the control plane process,
    stores the result, and updates the task status.
    """
    import traceback

    logger.info("Background task started for task_id=%s url=%s", task_id, url)

    db = get_database()
    run_id = str(uuid4())

    try:
        # Mark task as running and create a run record
        async with db.session() as session:
            task_repo = TaskRepository(session)
            run_repo = RunRepository(session)
            await task_repo.update(task_id, tenant_id, status=TaskStatus.RUNNING.value)
            await run_repo.create(
                tenant_id=tenant_id,
                id=run_id,
                task_id=task_id,
                lane=lane,
                connector="http_collector",
                status="running",
            )
            await session.commit()
        logger.info("Task %s marked as running", task_id)

        # Execute the actual scrape
        from services.worker_http.worker import HttpWorker
        worker = HttpWorker()
        try:
            worker_result = await worker.process_task({
                "task_id": task_id,
                "tenant_id": tenant_id,
                "url": url,
                "css_selectors": extraction_config.get("css_selectors"),
                "paginate": extraction_config.get("paginate", False),
                "max_pages": extraction_config.get("max_pages", 1),
            })
        finally:
            await worker.close()

        logger.info("Worker finished for task %s: status=%s items=%s",
                     task_id, worker_result.get("status"), worker_result.get("item_count"))

        # Store result and update task + run status
        async with db.session() as session:
            task_repo = TaskRepository(session)
            run_repo = RunRepository(session)
            result_repo = ResultRepository(session)

            succeeded = worker_result.get("status") == "success"
            final_status = TaskStatus.COMPLETED.value if succeeded else TaskStatus.FAILED.value

            await task_repo.update(task_id, tenant_id, status=final_status)

            # Store error info in task metadata for UI visibility
            if not succeeded:
                error_msg = worker_result.get("error") or f"HTTP {worker_result.get('status_code', 'unknown')}"
                await task_repo.update(task_id, tenant_id, metadata_json={"last_error": error_msg})

            await run_repo.update(
                run_id, tenant_id,
                status="completed" if succeeded else "failed",
                status_code=worker_result.get("status_code"),
                error=worker_result.get("error"),
                duration_ms=worker_result.get("duration_ms", 0),
                bytes_downloaded=worker_result.get("bytes_downloaded", 0),
                completed_at=datetime.now(timezone.utc),
            )

            if succeeded:
                await result_repo.create(
                    tenant_id=tenant_id,
                    task_id=task_id,
                    run_id=run_id,
                    url=url,
                    extracted_data=worker_result.get("extracted_data", []),
                    item_count=worker_result.get("item_count", 0),
                    confidence=worker_result.get("confidence", 0.0),
                    extraction_method=worker_result.get("extraction_method", "deterministic"),
                    artifacts_json=worker_result.get("artifacts", []),
                )

            await session.commit()

        logger.info("Task %s finished with status=%s", task_id, final_status)

    except Exception:
        error_tb = traceback.format_exc()
        logger.error("Inline task execution FAILED for %s: %s", task_id, error_tb)
        # Mark task AND run as failed
        try:
            async with db.session() as session:
                task_repo = TaskRepository(session)
                run_repo = RunRepository(session)
                short_error = error_tb.strip().split("\n")[-1][:500]
                await task_repo.update(
                    task_id, tenant_id,
                    status=TaskStatus.FAILED.value,
                    metadata_json={"last_error": short_error},
                )
                await run_repo.update(
                    run_id, tenant_id,
                    status="failed",
                    error=short_error,
                    completed_at=datetime.now(timezone.utc),
                )
                await session.commit()
            logger.info("Task %s marked as failed after error", task_id)
        except Exception:
            logger.error("Failed to update task %s to failed: %s", task_id, traceback.format_exc())


@router.post("/tasks/{task_id}/execute")
async def execute_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Trigger execution of a pending task.

    Fetches the task from the database, optionally loads its policy,
    routes through the ExecutionRouter, and kicks off inline execution
    via asyncio.create_task.
    """
    task_repo = TaskRepository(session)
    task_model = await task_repo.get(task_id, tenant_id)
    if not task_model:
        raise HTTPException(status_code=404, detail="Task not found")

    # Allow re-running from pending, queued (stuck), running (stuck), or failed
    non_runnable = {TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value}
    if task_model.status in non_runnable:
        raise HTTPException(
            status_code=400,
            detail=f"Task cannot be re-run (current status: {task_model.status})",
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

    # Include extraction config from policy extraction_rules (UC-6.3.1)
    extraction_config = {
        "css_selectors": (policy.extraction_rules or {}).get("css_selectors") if policy else None,
        "paginate": (policy.extraction_rules or {}).get("paginate", False) if policy else False,
        "max_pages": (policy.extraction_rules or {}).get("max_pages", 1) if policy else 1,
    }

    # Kick off inline execution via asyncio.create_task (fire-and-forget)
    asyncio.create_task(
        _run_task_inline(
            task_id=task_id,
            tenant_id=tenant_id,
            url=str(task.url),
            lane=decision.lane.value,
            extraction_config=extraction_config,
        )
    )

    return {
        "task_id": task_id,
        "status": "queued",
        "route": _route_decision_to_dict(decision),
        "extraction_config": extraction_config,
    }


class TestScrapeRequest(BaseModel):
    """Request body for real-time scrape test."""
    url: HttpUrl
    timeout_ms: int = 15000


@router.post("/test-scrape")
async def test_scrape(
    request: TestScrapeRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Real-time scrape test — runs inline and returns results immediately.

    Useful for debugging and testing URLs without creating a task.
    """
    import traceback
    import time

    url = str(request.url)
    start = time.time()

    try:
        from services.worker_http.worker import HttpWorker

        worker = HttpWorker()
        try:
            result = await worker.process_task({
                "task_id": "test",
                "tenant_id": tenant_id,
                "url": url,
                "timeout_ms": request.timeout_ms,
                "paginate": False,
                "max_pages": 1,
            })
        finally:
            await worker.close()

        elapsed = int((time.time() - start) * 1000)
        return {
            "url": url,
            "status": result.get("status"),
            "status_code": result.get("status_code"),
            "item_count": result.get("item_count", 0),
            "confidence": result.get("confidence", 0),
            "extraction_method": result.get("extraction_method"),
            "duration_ms": elapsed,
            "error": result.get("error"),
            "extracted_data": result.get("extracted_data", [])[:10],  # Limit to 10 items
            "should_escalate": result.get("should_escalate", False),
        }

    except Exception:
        elapsed = int((time.time() - start) * 1000)
        error = traceback.format_exc()
        logger.error("Test scrape failed for %s: %s", url, error)
        short_error = error.strip().split("\n")[-1][:500]
        return {
            "url": url,
            "status": "error",
            "status_code": None,
            "item_count": 0,
            "confidence": 0,
            "extraction_method": None,
            "duration_ms": elapsed,
            "error": short_error,
            "extracted_data": [],
            "should_escalate": False,
        }


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Mark a task as completed and fire its webhook if configured.

    This endpoint is called by workers when execution finishes. It updates
    the task status and sends a webhook notification if callback_url is set.
    """
    task_repo = TaskRepository(session)
    task_model = await task_repo.get(task_id, tenant_id)
    if not task_model:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update task status to completed
    await task_repo.update(task_id, tenant_id, status=TaskStatus.COMPLETED.value)

    task = _task_model_to_contract(task_model)
    task.status = TaskStatus.COMPLETED

    # Fetch the latest result for this task (if any)
    result: Optional[Result] = None
    result_repo = ResultRepository(session)
    results = await result_repo.list_by_task(task_id, tenant_id)
    if results:
        # Use the most recent result
        result = Result(
            id=results[-1].id,
            task_id=results[-1].task_id,
            run_id=results[-1].run_id,
            tenant_id=results[-1].tenant_id,
            url=results[-1].url,
            item_count=results[-1].item_count,
            confidence=results[-1].confidence,
            extraction_method=results[-1].extraction_method,
            schema_version=getattr(results[-1], "schema_version", "1.0"),
        )

    # Fire webhook if callback_url is configured
    webhook_status = None
    if task.callback_url:
        from services.control_plane.app import get_webhook_executor
        executor = get_webhook_executor()
        delivery = await executor.send(task, result)
        webhook_status = {
            "delivered": delivery.success,
            "attempts": delivery.attempts,
            "status_code": delivery.status_code,
            "error": delivery.error,
        }

    logger.info(
        "Task completed",
        extra={
            "task_id": task_id,
            "webhook_fired": webhook_status is not None,
        },
    )

    return {
        "task_id": task_id,
        "status": "completed",
        "webhook": webhook_status,
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
