"""Actor catalog API — serves the hard-coded 27,753 actor catalog."""
from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.actor_catalog.registry import actor_catalog
from packages.core.actor_runtime import ActorRunState, ActorRuntimeResult, ActorSpec, BaseActorRunner
from packages.core.storage.models import ResultModel, RunModel, TaskModel
from packages.core.storage.repositories import ResultRepository, RunRepository, TaskRepository
from services.control_plane.dependencies import get_session, get_tenant_id

logger = logging.getLogger(__name__)

actors_router = APIRouter(prefix="/actors", tags=["Actors"])

RUNNABLE_NATIVE_STRATEGIES = {"native_pipeline"}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ActorRunRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class NativePipelineActorRunner(BaseActorRunner):
    def __init__(
        self,
        spec: ActorSpec,
        *,
        task_id: str,
        tenant_id: str,
    ) -> None:
        super().__init__(spec)
        self.task_id = task_id
        self.tenant_id = tenant_id

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = str(payload.get("target") or payload.get("url") or "").strip()
        if not target:
            raise ValueError("Actor input requires a target URL or url field")

        from services.worker_http.worker import HttpWorker

        worker = HttpWorker()
        try:
            worker_result = await worker.process_task(
                {
                    "task_id": self.task_id,
                    "tenant_id": self.tenant_id,
                    "url": target,
                    "timeout_ms": int(payload.get("timeout_ms") or 30000),
                    "paginate": bool(payload.get("paginate") or (int(payload.get("max_pages") or 1) > 1)),
                    "max_pages": int(payload.get("max_pages") or 1),
                    "css_selectors": payload.get("css_selectors"),
                }
            )
        finally:
            await worker.close()

        if worker_result.get("status") != "success":
            raise RuntimeError(worker_result.get("error") or "Native pipeline execution failed")

        return {
            "extracted_data": worker_result.get("extracted_data", []),
            "item_count": worker_result.get("item_count", 0),
            "confidence": worker_result.get("confidence", 0.0),
            "status_code": worker_result.get("status_code"),
            "extraction_method": worker_result.get("extraction_method", "deterministic"),
            "bytes_downloaded": worker_result.get("bytes_downloaded", 0),
            "duration_ms": worker_result.get("duration_ms", 0),
            "artifacts": worker_result.get("artifacts", []),
        }


def _build_actor_spec(entry) -> ActorSpec:
    return ActorSpec(
        actor_id=entry.actor_id,
        slug=entry.name,
        title=entry.title,
        base_family=entry.route_strategy,
        compliance_notes=(
            "Apify catalog URL is source metadata only; execution must use native Scraper-app stack.",
        ),
    )


def _create_actor_runner(
    spec: ActorSpec,
    entry,
    *,
    task_id: str,
    tenant_id: str,
) -> BaseActorRunner:
    if entry.route_strategy == "native_pipeline":
        return NativePipelineActorRunner(spec, task_id=task_id, tenant_id=tenant_id)
    return BaseActorRunner(spec)


def _terminal_status_for_state(state: ActorRunState) -> tuple[str, str]:
    if state == ActorRunState.SUCCEEDED:
        return "completed", "completed"
    if state == ActorRunState.SKIPPED_MISSING_KEY:
        return "skipped", ActorRunState.SKIPPED_MISSING_KEY.value
    if state == ActorRunState.BLOCKED_POLICY:
        return "blocked", ActorRunState.BLOCKED_POLICY.value
    return "failed", "failed"


def _result_items(output: dict[str, Any]) -> list[dict[str, Any]]:
    data = output.get("extracted_data", output.get("items", []))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _actor_run_base_query(actor_id: str, tenant_id: str):
    actor_id_filter = TaskModel.metadata_json["actor_id"].as_string() == actor_id
    return (
        select(TaskModel, RunModel)
        .join(RunModel, RunModel.task_id == TaskModel.id)
        .where(
            TaskModel.tenant_id == tenant_id,
            RunModel.tenant_id == tenant_id,
            TaskModel.task_type == "actor",
            actor_id_filter,
        )
    )


async def _get_result_for_run(session: AsyncSession, run_id: str, tenant_id: str) -> ResultModel | None:
    stmt = select(ResultModel).where(ResultModel.run_id == run_id, ResultModel.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _serialize_result(result: ResultModel | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "id": result.id,
        "item_count": result.item_count,
        "confidence": result.confidence,
        "extraction_method": result.extraction_method,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


def _serialize_actor_run(task: TaskModel, run: RunModel, result: ResultModel | None = None) -> dict[str, Any]:
    metadata = task.metadata_json or {}
    return {
        "actor_id": metadata.get("actor_id", ""),
        "state": metadata.get("actor_state", run.status),
        "missing_env_names": metadata.get("missing_env_names", []),
        "provider": metadata.get("provider"),
        "output": metadata.get("actor_output", {}),
        "error": run.error,
        "task": {
            "id": task.id,
            "status": task.status,
            "name": task.name or "",
            "url": task.url,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        },
        "run": {
            "id": run.id,
            "task_id": run.task_id,
            "status": run.status,
            "lane": run.lane,
            "connector": run.connector,
            "status_code": run.status_code,
            "duration_ms": run.duration_ms,
            "bytes_downloaded": run.bytes_downloaded,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        },
        "result": _serialize_result(result),
    }


async def _persist_actor_run_result(
    *,
    session: AsyncSession,
    tenant_id: str,
    task_id: str,
    run_id: str,
    target_url: str,
    runtime_result: ActorRuntimeResult,
) -> ResultModel | None:
    if runtime_result.state != ActorRunState.SUCCEEDED:
        return None

    items = _result_items(runtime_result.output)
    result_repo = ResultRepository(session)
    return await result_repo.create(
        tenant_id=tenant_id,
        task_id=task_id,
        run_id=run_id,
        url=target_url,
        extracted_data=items,
        item_count=len(items),
        confidence=float(runtime_result.output.get("confidence", 0.0) or 0.0),
        extraction_method=str(runtime_result.output.get("extraction_method") or "actor_runtime"),
        artifacts_json=runtime_result.output.get("artifacts", []),
        normalization_applied=bool(runtime_result.output.get("normalization_applied", False)),
        dedup_applied=bool(runtime_result.output.get("dedup_applied", False)),
    )


@actors_router.get("")
async def list_actors(
    q: str = Query("", description="Search query"),
    category: str = Query("", description="Filter by category"),
    developer: str = Query("", description="Filter by developer"),
    pricing_model: str = Query("", description="Filter by pricing model"),
    strategy: str = Query("", description="Filter by route strategy"),
    runnable: str = Query("", description="Filter by runnable status"),
    sort: str = Query("relevant", description="Sort: relevant, name, popular, runs, rating"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(24, ge=1, le=100, description="Page size"),
) -> dict[str, Any]:
    """List actors with search, filtering, and pagination."""
    actors, total = actor_catalog.search(
        query=q,
        category=category,
        developer=developer,
        pricing_model=pricing_model,
        strategy=strategy,
        runnable=runnable,
        sort=sort,
        offset=offset,
        limit=limit,
    )
    return {
        "success": True,
        "data": [asdict(a) for a in actors],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@actors_router.post("/{actor_id}/runs")
async def create_actor_run(
    actor_id: str,
    body: ActorRunRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Create and execute a native actor run without delegating to Apify."""
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")

    task_repo = TaskRepository(session)
    run_repo = RunRepository(session)
    task_id = str(uuid4())
    run_id = str(uuid4())
    target_url = str(body.input.get("target") or body.input.get("url") or f"actor://{actor_id}")
    now = _utcnow()

    task = await task_repo.create(
        tenant_id=tenant_id,
        id=task_id,
        name=entry.title,
        url=target_url,
        task_type="actor",
        extraction_type=entry.route_strategy,
        status="running",
        metadata_json={
            "source": "actor_runtime",
            "actor_id": actor_id,
            "actor_name": entry.name,
            "actor_title": entry.title,
            "route_strategy": entry.route_strategy,
            "runnable_status": entry.runnable_status,
            "input": body.input,
            "options": body.options,
        },
    )
    run = await run_repo.create(
        tenant_id=tenant_id,
        id=run_id,
        task_id=task_id,
        lane="actor",
        connector="actor_runtime",
        status="running",
        started_at=now,
    )
    await session.flush()

    if entry.route_strategy not in RUNNABLE_NATIVE_STRATEGIES:
        runtime_result = ActorRuntimeResult(
            actor_id=actor_id,
            state=ActorRunState.BLOCKED_POLICY,
            error=f"Native actor family is not implemented for route strategy: {entry.route_strategy}",
            metadata={"base_family": entry.route_strategy},
        )
    else:
        spec = _build_actor_spec(entry)
        runner = _create_actor_runner(spec, entry, task_id=task_id, tenant_id=tenant_id)
        runtime_result = await runner.run(body.input)

    task_status, run_status = _terminal_status_for_state(runtime_result.state)
    output = runtime_result.output if runtime_result.state == ActorRunState.SUCCEEDED else {}
    task_metadata = task.metadata_json or {}
    task_metadata.update(
        {
            "actor_state": runtime_result.state.value,
            "missing_env_names": list(runtime_result.missing_env_names),
            "provider": runtime_result.provider,
            "actor_output": output,
            "actor_error": runtime_result.error,
        }
    )

    duration_ms = int((_utcnow() - now).total_seconds() * 1000)
    task = await task_repo.update(task_id, tenant_id, status=task_status, metadata_json=task_metadata)
    run = await run_repo.update(
        run_id,
        tenant_id,
        status=run_status,
        error=runtime_result.error,
        completed_at=_utcnow(),
        duration_ms=int(output.get("duration_ms", duration_ms) if output else duration_ms),
        bytes_downloaded=int(output.get("bytes_downloaded", 0) if output else 0),
        status_code=output.get("status_code") if output else None,
    )
    result = await _persist_actor_run_result(
        session=session,
        tenant_id=tenant_id,
        task_id=task_id,
        run_id=run_id,
        target_url=target_url,
        runtime_result=runtime_result,
    )
    await session.flush()

    return {
        "success": True,
        "data": _serialize_actor_run(task, run, result),
    }


@actors_router.get("/{actor_id}/runs")
async def list_actor_runs(
    actor_id: str,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """List persisted runs for one actor, scoped to the current tenant."""
    if actor_catalog.get(actor_id) is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")

    count_stmt = (
        select(func.count())
        .select_from(RunModel)
        .join(TaskModel, RunModel.task_id == TaskModel.id)
        .where(
            TaskModel.tenant_id == tenant_id,
            RunModel.tenant_id == tenant_id,
            TaskModel.task_type == "actor",
            TaskModel.metadata_json["actor_id"].as_string() == actor_id,
        )
    )
    total_result = await session.execute(count_stmt)
    total = int(total_result.scalar() or 0)

    stmt = (
        _actor_run_base_query(actor_id, tenant_id)
        .order_by(RunModel.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    items = []
    for task, run in rows:
        result = await _get_result_for_run(session, run.id, tenant_id)
        items.append(_serialize_actor_run(task, run, result))

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@actors_router.get("/{actor_id}/runs/{run_id}")
async def get_actor_run(
    actor_id: str,
    run_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Get one persisted actor run, scoped by tenant and actor."""
    if actor_catalog.get(actor_id) is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")

    stmt = _actor_run_base_query(actor_id, tenant_id).where(RunModel.id == run_id)
    row = (await session.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Actor run not found")
    task, run = row
    result = await _get_result_for_run(session, run.id, tenant_id)
    return {
        "success": True,
        "data": _serialize_actor_run(task, run, result),
    }


@actors_router.get("/stats")
async def actor_stats() -> dict[str, Any]:
    """Aggregate actor catalog statistics."""
    return {
        "success": True,
        "data": actor_catalog.stats(),
    }


@actors_router.get("/categories")
async def actor_categories() -> dict[str, Any]:
    """List all unique actor categories."""
    return {
        "success": True,
        "data": actor_catalog.categories(),
    }


@actors_router.get("/developers")
async def actor_developers() -> dict[str, Any]:
    """List all unique actor developers."""
    return {
        "success": True,
        "data": actor_catalog.developers(),
    }


@actors_router.get("/pricing-models")
async def actor_pricing_models() -> dict[str, Any]:
    """List all unique actor pricing models."""
    return {
        "success": True,
        "data": actor_catalog.pricing_models(),
    }


@actors_router.get("/{actor_id}")
async def get_actor(actor_id: str) -> dict[str, Any]:
    """Get actor detail by ID."""
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    return {
        "success": True,
        "data": asdict(entry),
    }
