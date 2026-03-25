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
from packages.core.escalation import EscalationManager
from packages.core.webhook import WebhookExecutor
from packages.core.storage.repositories import TaskRepository, PolicyRepository, ResultRepository, RunRepository
from services.control_plane.dependencies import get_session, get_database, get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level router instance (singleton within the process)
_execution_router = ExecutionRouter()
_escalation_manager = EscalationManager(_execution_router)

# Lane → connector name mapping
_LANE_CONNECTORS = {
    Lane.HTTP: "http_collector",
    Lane.BROWSER: "playwright_browser",
    Lane.HARD_TARGET: "hard_target_worker",
}


async def _execute_lane(lane: Lane, task_payload: dict) -> dict:
    """Execute a task using the worker for the given lane.

    Returns the worker result dict. If browser/hard_target fails
    (including Playwright not installed), returns a failure result with
    should_escalate=True so the escalation loop tries the next lane.
    Does NOT silently fall back to HTTP -- that masks real errors.
    """
    try:
        if lane == Lane.HTTP:
            from services.worker_http.worker import HttpWorker
            worker = HttpWorker()
            try:
                return await worker.process_task(task_payload)
            finally:
                await worker.close()

        elif lane in (Lane.BROWSER, Lane.HARD_TARGET):
            if lane == Lane.BROWSER:
                from services.worker_browser.worker import BrowserLaneWorker
                worker = BrowserLaneWorker()
            else:
                from services.worker_hard_target.worker import HardTargetLaneWorker
                worker = HardTargetLaneWorker()
            try:
                return await worker.process_task(task_payload)
            finally:
                await worker.close()

        else:
            from services.worker_http.worker import HttpWorker
            worker = HttpWorker()
            try:
                return await worker.process_task(task_payload)
            finally:
                await worker.close()

    except Exception as exc:
        logger.warning("Lane %s worker failed: %s", lane.value, exc)
        return {
            "task_id": task_payload.get("task_id", "unknown"),
            "tenant_id": task_payload.get("tenant_id", "default"),
            "url": task_payload.get("url", ""),
            "lane": lane.value,
            "status": "failed",
            "status_code": 0,
            "error": f"{lane.value} worker error: {str(exc)[:500]}",
            "duration_ms": 0,
            "extracted_data": [],
            "item_count": 0,
            "should_escalate": True,
        }



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


async def _run_task_inline(task_id: str, tenant_id: str, url: str, lane: str, extraction_config: dict, route_decision: RouteDecision | None = None) -> None:
    """Execute a scraping task inline via asyncio.create_task.

    Runs the appropriate worker directly in the control plane process,
    stores the result, and updates the task status.  Supports automatic
    escalation through the fallback chain (HTTP → Browser → Hard-Target)
    when a lane fails with ``should_escalate=True``.
    """
    import traceback

    logger.info("Background task started for task_id=%s url=%s lane=%s", task_id, url, lane)

    db = get_database()
    current_lane = Lane(lane)
    escalation_chain: list[dict] = []  # track all attempts

    try:
        while True:
            run_id = str(uuid4())

            # Mark task as running and create a run record for this attempt
            async with db.session() as session:
                task_repo = TaskRepository(session)
                run_repo = RunRepository(session)
                await task_repo.update(task_id, tenant_id, status=TaskStatus.RUNNING.value)
                await run_repo.create(
                    tenant_id=tenant_id,
                    id=run_id,
                    task_id=task_id,
                    lane=current_lane.value,
                    connector=_LANE_CONNECTORS.get(current_lane, "http_collector"),
                    status="running",
                )
                await session.commit()

            logger.info("Task %s executing via %s lane", task_id, current_lane.value)

            # Execute the actual scrape via the lane-specific worker
            task_payload = {
                "task_id": task_id,
                "tenant_id": tenant_id,
                "url": url,
                "css_selectors": extraction_config.get("css_selectors"),
                "paginate": extraction_config.get("paginate", False),
                "max_pages": extraction_config.get("max_pages", 1),
            }

            worker_result = await _execute_lane(current_lane, task_payload)

            logger.info("Worker finished for task %s: lane=%s status=%s items=%s",
                         task_id, current_lane.value, worker_result.get("status"),
                         worker_result.get("item_count"))

            succeeded = worker_result.get("status") == "success"

            # Record run result
            async with db.session() as session:
                run_repo = RunRepository(session)
                await run_repo.update(
                    run_id, tenant_id,
                    status="completed" if succeeded else "failed",
                    status_code=worker_result.get("status_code"),
                    error=worker_result.get("error"),
                    duration_ms=worker_result.get("duration_ms", 0),
                    bytes_downloaded=worker_result.get("bytes_downloaded", 0),
                )
                await session.commit()

            escalation_chain.append({
                "lane": current_lane.value,
                "status": worker_result.get("status"),
                "status_code": worker_result.get("status_code"),
                "item_count": worker_result.get("item_count", 0),
            })

            # Check if escalation is needed — ALWAYS consult escalation manager,
            # even on "success". A success with 1 garbage item on a listing page
            # should still escalate to a better lane.
            needs_escalation = _escalation_manager.should_escalate(worker_result)
            if not needs_escalation:
                # Final result — store and finish
                async with db.session() as session:
                    task_repo = TaskRepository(session)
                    result_repo = ResultRepository(session)
                    final_status = TaskStatus.COMPLETED.value if succeeded else TaskStatus.FAILED.value
                    metadata = {"escalation_chain": escalation_chain}
                    if not succeeded:
                        metadata["last_error"] = worker_result.get("error") or f"HTTP {worker_result.get('status_code', 'unknown')}"
                    await task_repo.update(task_id, tenant_id, status=final_status, metadata_json=metadata)

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
                            normalization_applied=worker_result.get("normalization_applied", False),
                            dedup_applied=worker_result.get("dedup_applied", False),
                        )

                    await session.commit()

                logger.info("Task %s finished with status=%s (escalation_chain=%s)",
                            task_id, final_status, [e["lane"] for e in escalation_chain])
                break

            # Attempt escalation to next lane
            if route_decision is None:
                route_decision = RouteDecision(
                    lane=current_lane,
                    reason="escalation",
                    fallback_lanes=_execution_router._get_fallback_lanes(current_lane),
                )

            next_lane = _escalation_manager.get_escalation(task_id, worker_result, route_decision)
            if next_lane is None:
                # Escalation exhausted — mark as failed
                async with db.session() as session:
                    task_repo = TaskRepository(session)
                    error_msg = worker_result.get("error") or f"HTTP {worker_result.get('status_code', 'unknown')}"
                    await task_repo.update(
                        task_id, tenant_id,
                        status=TaskStatus.FAILED.value,
                        metadata_json={"last_error": error_msg, "escalation_chain": escalation_chain},
                    )
                    await session.commit()
                logger.info("Task %s failed — escalation exhausted (chain=%s)",
                            task_id, [e["lane"] for e in escalation_chain])
                break

            logger.info("Task %s escalating: %s → %s", task_id, current_lane.value, next_lane.value)
            current_lane = next_lane
            # Update route_decision for the next iteration
            route_decision = RouteDecision(
                lane=current_lane,
                reason="escalation",
                fallback_lanes=_execution_router._get_fallback_lanes(current_lane),
            )

        # Clean up escalation context
        _escalation_manager.complete(task_id, worker_result)

    except Exception:
        error_tb = traceback.format_exc()
        logger.error("Inline task execution FAILED for %s: %s", task_id, error_tb)
        try:
            async with db.session() as session:
                task_repo = TaskRepository(session)
                short_error = error_tb.strip().split("\n")[-1][:500]
                await task_repo.update(
                    task_id, tenant_id,
                    status=TaskStatus.FAILED.value,
                    metadata_json={"last_error": short_error, "escalation_chain": escalation_chain},
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
    """Trigger execution of a task — runs the scraper inline and returns results.

    Fetches the task, routes it, executes the HTTP worker synchronously,
    stores results, and returns the outcome. Typically completes in < 2s.
    """
    import traceback
    import time

    task_repo = TaskRepository(session)
    run_repo = RunRepository(session)
    result_repo = ResultRepository(session)

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

    # Extraction config from policy
    extraction_config = {
        "css_selectors": (policy.extraction_rules or {}).get("css_selectors") if policy else None,
        "paginate": (policy.extraction_rules or {}).get("paginate", False) if policy else False,
        "max_pages": (policy.extraction_rules or {}).get("max_pages", 1) if policy else 1,
    }

    # Mark task as running and create a run record
    run_id = str(uuid4())
    await task_repo.update(task_id, tenant_id, status=TaskStatus.RUNNING.value)
    await run_repo.create(
        tenant_id=tenant_id,
        id=run_id,
        task_id=task_id,
        lane=decision.lane.value,
        connector=_LANE_CONNECTORS.get(decision.lane, "http_collector"),
        status="running",
    )
    await session.flush()

    logger.info("Task %s executing inline (lane=%s)", task_id, decision.lane.value)

    # Execute the scraper inline with auto-escalation
    url = str(task.url)
    start_time = time.time()
    current_lane = decision.lane
    current_decision = decision
    escalation_chain: list[dict] = []

    try:
        task_payload = {
            "task_id": task_id,
            "tenant_id": tenant_id,
            "url": url,
            "css_selectors": extraction_config.get("css_selectors"),
            "paginate": extraction_config.get("paginate", False),
            "max_pages": extraction_config.get("max_pages", 1),
            # Browser worker config — enable smart scrolling and waiting
            "scroll": True,
            "max_scrolls": extraction_config.get("max_scrolls", 5),
            "wait_selector": extraction_config.get("wait_selector"),
            "wait_timeout_ms": extraction_config.get("wait_timeout_ms", 10000),
            "timeout_ms": extraction_config.get("timeout_ms", 45000),
        }

        while True:
            # Create a run record for this attempt
            attempt_run_id = str(uuid4()) if escalation_chain else run_id
            if escalation_chain:
                await run_repo.create(
                    tenant_id=tenant_id,
                    id=attempt_run_id,
                    task_id=task_id,
                    lane=current_lane.value,
                    connector=_LANE_CONNECTORS.get(current_lane, "http_collector"),
                    status="running",
                )
                await session.flush()

            worker_result = await _execute_lane(current_lane, task_payload)

            succeeded = worker_result.get("status") == "success"

            # Update this run's status
            await run_repo.update(
                attempt_run_id, tenant_id,
                status="completed" if succeeded else "failed",
                status_code=worker_result.get("status_code"),
                error=worker_result.get("error"),
                duration_ms=worker_result.get("duration_ms", 0),
                bytes_downloaded=worker_result.get("bytes_downloaded", 0),
            )

            escalation_chain.append({
                "lane": current_lane.value,
                "status": worker_result.get("status"),
                "status_code": worker_result.get("status_code"),
                "item_count": worker_result.get("item_count", 0),
            })

            # Check if we should escalate — always consult manager, even on "success"
            if not _escalation_manager.should_escalate(worker_result):
                break

            # Get next lane
            next_lane = _escalation_manager.get_escalation(task_id, worker_result, current_decision)
            if next_lane is None:
                logger.info("Task %s escalation exhausted (chain=%s)",
                            task_id, [e["lane"] for e in escalation_chain])
                break

            logger.info("Task %s auto-escalating: %s → %s",
                        task_id, current_lane.value, next_lane.value)
            current_lane = next_lane
            current_decision = RouteDecision(
                lane=current_lane,
                reason="auto-escalation",
                fallback_lanes=_execution_router._get_fallback_lanes(current_lane),
            )

        # Clean up escalation context
        _escalation_manager.complete(task_id, worker_result)

        # Final status
        final_status = TaskStatus.COMPLETED.value if succeeded else TaskStatus.FAILED.value
        metadata: dict = {"escalation_chain": escalation_chain}
        if not succeeded:
            error_msg = worker_result.get("error") or f"HTTP {worker_result.get('status_code', 'unknown')}"
            metadata["last_error"] = error_msg

        await task_repo.update(task_id, tenant_id, status=final_status, metadata_json=metadata)

        # Store result if successful
        if succeeded:
            await result_repo.create(
                tenant_id=tenant_id,
                task_id=task_id,
                run_id=attempt_run_id,
                url=url,
                extracted_data=worker_result.get("extracted_data", []),
                item_count=worker_result.get("item_count", 0),
                confidence=worker_result.get("confidence", 0.0),
                extraction_method=worker_result.get("extraction_method", "deterministic"),
                artifacts_json=worker_result.get("artifacts", []),
                normalization_applied=worker_result.get("normalization_applied", False),
                dedup_applied=worker_result.get("dedup_applied", False),
            )

        elapsed = int((time.time() - start_time) * 1000)
        logger.info("Task %s completed: status=%s items=%d in %dms (chain=%s)",
                     task_id, final_status, worker_result.get("item_count", 0), elapsed,
                     [e["lane"] for e in escalation_chain])

        return {
            "task_id": task_id,
            "status": final_status,
            "route": _route_decision_to_dict(decision),
            "lane_used": current_lane.value,
            "escalation_chain": escalation_chain,
            "item_count": worker_result.get("item_count", 0),
            "confidence": worker_result.get("confidence", 0),
            "duration_ms": elapsed,
            "error": worker_result.get("error"),
        }

    except Exception:
        error_tb = traceback.format_exc()
        logger.error("Task %s execution failed: %s", task_id, error_tb)
        short_error = error_tb.strip().split("\n")[-1][:500]
        try:
            await session.rollback()
            await task_repo.update(
                task_id, tenant_id,
                status=TaskStatus.FAILED.value,
                metadata_json={"last_error": short_error, "escalation_chain": escalation_chain},
            )
            await run_repo.update(
                run_id, tenant_id,
                status="failed",
                error=short_error,
                )
        except Exception:
            logger.error("Failed to mark task %s as failed: %s", task_id, traceback.format_exc())

        return {
            "task_id": task_id,
            "status": "failed",
            "route": _route_decision_to_dict(decision),
            "lane_used": current_lane.value,
            "escalation_chain": escalation_chain,
            "item_count": 0,
            "confidence": 0,
            "duration_ms": int((time.time() - start_time) * 1000),
            "error": short_error,
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

    # Route to determine initial lane
    test_task = Task(tenant_id=tenant_id, url=request.url)
    decision = _execution_router.route(test_task)
    current_lane = decision.lane
    current_decision = decision
    escalation_chain: list[dict] = []

    try:
        task_payload = {
            "task_id": "test",
            "tenant_id": tenant_id,
            "url": url,
            "timeout_ms": request.timeout_ms,
            "paginate": False,
            "max_pages": 1,
        }

        while True:
            result = await _execute_lane(current_lane, task_payload)

            succeeded = result.get("status") == "success"
            escalation_chain.append({
                "lane": current_lane.value,
                "status": result.get("status"),
                "status_code": result.get("status_code"),
                "item_count": result.get("item_count", 0),
            })

            if not _escalation_manager.should_escalate(result):
                break

            next_lane = _escalation_manager.get_escalation("test", result, current_decision)
            if next_lane is None:
                break

            logger.info("Test scrape auto-escalating: %s → %s", current_lane.value, next_lane.value)
            current_lane = next_lane
            current_decision = RouteDecision(
                lane=current_lane,
                reason="auto-escalation",
                fallback_lanes=_execution_router._get_fallback_lanes(current_lane),
            )

        _escalation_manager.complete("test", result)

        elapsed = int((time.time() - start) * 1000)
        return {
            "url": url,
            "status": result.get("status"),
            "status_code": result.get("status_code"),
            "lane_used": current_lane.value,
            "escalation_chain": escalation_chain,
            "item_count": result.get("item_count", 0),
            "confidence": result.get("confidence", 0),
            "extraction_method": result.get("extraction_method"),
            "duration_ms": elapsed,
            "error": result.get("error"),
            "extracted_data": result.get("extracted_data", [])[:10],
            "should_escalate": False,  # escalation already handled
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
            "lane_used": current_lane.value,
            "escalation_chain": escalation_chain,
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


@router.get("/debug/playwright")
async def debug_playwright() -> dict:
    """Diagnostic: check if Playwright + Chromium is available on this instance."""
    import shutil
    import os

    info: dict = {
        "playwright_installed": False,
        "chromium_path": None,
        "chromium_exists": False,
        "error": None,
    }

    try:
        from playwright.async_api import async_playwright
        info["playwright_installed"] = True

        # Check if chromium binary exists
        pw = await async_playwright().start()
        try:
            browser = await pw.chromium.launch(headless=True)
            info["chromium_exists"] = True
            info["chromium_version"] = browser.version
            await browser.close()
        except Exception as e:
            info["error"] = str(e)[:500]
        finally:
            await pw.stop()

    except ImportError as e:
        info["error"] = f"playwright not importable: {e}"
    except Exception as e:
        info["error"] = str(e)[:500]

    # Check common Playwright cache locations
    for cache_dir in [
        os.path.expanduser("~/.cache/ms-playwright"),
        "/root/.cache/ms-playwright",
        "/home/appuser/.cache/ms-playwright",
    ]:
        if os.path.isdir(cache_dir):
            info["chromium_path"] = cache_dir
            # List contents
            try:
                info["cache_contents"] = os.listdir(cache_dir)
            except Exception:
                pass
            break

    return info
