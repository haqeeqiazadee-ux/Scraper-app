"""Actor catalog API — serves the hard-coded 27,753 actor catalog."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.actor_catalog.registry import actor_catalog
from packages.core.actor_runtime import (
    ActorLearningEvent,
    ActorProofFailureClass,
    ActorProofLevel,
    ActorProofRecord,
    ActorRuntimeResult,
    ActorRunState,
    FixtureReviewStatus,
    LearningEventType,
    RegressionFixtureCandidate,
    ReplayValidationResult,
    StrategyPatchProposal,
    StrategyPatchStatus,
    StrategyProfile,
    StrategyProfileEngine,
    actor_catalog_version,
    actor_public_route,
    build_actor_spec,
    build_default_strategy_profile,
    choose_proof_level,
    classify_actor_proof_failure,
    create_actor_runner,
    generate_actor_test_input,
)
from packages.core.storage.models import ResultModel, RunModel, TaskModel
from packages.core.storage.repositories import (
    ActorFixtureRepository,
    ActorProofRepository,
    ActorStrategyProfileRepository,
    ResultRepository,
    RunRepository,
    TaskRepository,
)
from services.control_plane.dependencies import get_session, get_tenant_id

logger = logging.getLogger(__name__)

actors_router = APIRouter(prefix="/actors", tags=["Actors"])

RUNNABLE_NATIVE_STRATEGIES = {
    "native_pipeline",
    "job_board_schema",
    "real_estate_schema",
    "lead_generation_generic",
    "review_monitoring_generic",
    "news_content_monitoring",
}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ActorRunRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class StrategyProfileUpsertRequest(BaseModel):
    version: str = "1.0.0"
    policy_version: str = "strategy-profile-v1"
    promoted_by: str = "codex"
    provider_order: list[str] = Field(default_factory=list)
    schema_aliases: dict[str, list[str]] = Field(default_factory=dict)
    freshness_overrides: dict[str, Any] = Field(default_factory=dict)
    replay_fixture_ids: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class LearningEventCreateRequest(BaseModel):
    event_type: LearningEventType = LearningEventType.RUN_SUCCEEDED
    trigger_reason: str = "manual_observation"
    profile_version: str = "1.0.0"
    payload_fingerprint: str
    redacted_payload_keys: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)


class StrategyPatchProposalCreateRequest(BaseModel):
    current_profile_version: str = "1.0.0"
    proposed_profile_version: str = "1.0.1"
    patch: dict[str, Any] = Field(default_factory=dict)
    rationale: str = "manual_patch_proposal"
    required_replay_fixture_ids: list[str] = Field(default_factory=list)


class ReplayValidationCreateRequest(BaseModel):
    passed: bool = False
    fixtures_run: list[str] = Field(default_factory=list)
    score_before: float = 0.0
    score_after: float = 0.0
    security_blockers: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PromoteProfileRequest(BaseModel):
    promoted_by: str = "codex"


class FixtureCandidateCreateRequest(BaseModel):
    fixture_id: str | None = None
    trigger_reasons: list[str] = Field(default_factory=list)
    source_trace_id: str | None = None
    state: str = "failed"
    provider: str | None = None
    sanitized_input: dict[str, Any] = Field(default_factory=dict)
    redacted_payload_keys: list[str] = Field(default_factory=list)
    expected_assertions: list[str] = Field(default_factory=lambda: ["fixture_replay_is_deterministic"])
    tags: list[str] = Field(default_factory=lambda: ["actor-regression", "manual-review"])


class FixtureReviewRequest(BaseModel):
    reviewed_by: str = "codex"
    notes: str = ""


class ActorProofRecordRequest(BaseModel):
    proof_level: ActorProofLevel = ActorProofLevel.API_MAPPED
    test_input: dict[str, Any] = Field(default_factory=dict)
    run_id: str | None = None
    result_id: str | None = None
    items_count: int = 0
    schema_passed: bool = False
    export_json_passed: bool = False
    export_csv_passed: bool = False
    ui_route_passed: bool = False
    live_e2e_passed: bool = False
    fixture_replay_passed: bool = False
    blocked_reason: str | None = None
    failure_reason: str | None = None
    failure_class: ActorProofFailureClass = ActorProofFailureClass.NONE
    source_timestamp: datetime | None = None
    policy_version: str = "actor-proof-v1"
    provenance: list[str] = Field(default_factory=list)
    proof_metadata: dict[str, Any] = Field(default_factory=dict)


class ActorProofFromRunRequest(BaseModel):
    ui_route_passed: bool = False
    fixture_replay_passed: bool = False
    source_timestamp: datetime | None = None
    policy_version: str = "actor-proof-v1"
    provenance: list[str] = Field(default_factory=list)
    proof_metadata: dict[str, Any] = Field(default_factory=dict)


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


def _status_event(state: str, message: str, **extra: Any) -> dict[str, Any]:
    event = {
        "state": state,
        "message": message,
        "at": _utcnow().isoformat(),
    }
    event.update({key: value for key, value in extra.items() if value is not None})
    return event


def _append_status_history(metadata: dict[str, Any], state: str, message: str, **extra: Any) -> None:
    history = metadata.get("status_history")
    if not isinstance(history, list):
        history = []
    history.append(_status_event(state, message, **extra))
    metadata["status_history"] = history
    logs = metadata.get("logs")
    if not isinstance(logs, list):
        logs = []
    logs.append(
        {
            "level": "info" if state not in {"failed", "blocked", "cancelled"} else "warning",
            "message": message,
            "at": history[-1]["at"],
        }
    )
    metadata["logs"] = logs


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
    item_count = result.item_count if result is not None else int(metadata.get("actor_output", {}).get("item_count", 0) or 0)
    return {
        "actor_id": metadata.get("actor_id", ""),
        "state": metadata.get("actor_state", run.status),
        "missing_env_names": metadata.get("missing_env_names", []),
        "provider": metadata.get("provider"),
        "knowledge": metadata.get("knowledge", {}),
        "runtime_metadata": metadata.get("runtime_metadata", {}),
        "output": metadata.get("actor_output", {}),
        "status_history": metadata.get("status_history", []),
        "logs": metadata.get("logs", []),
        "usage": {
            "duration_ms": run.duration_ms,
            "bytes_downloaded": run.bytes_downloaded,
            "ai_tokens_used": run.ai_tokens_used,
            "item_count": item_count,
            "estimated_credits": max(1, item_count) if run.status == "completed" else 0,
        },
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


def _serialize_profile(profile: StrategyProfile, *, persisted: bool = True) -> dict[str, Any]:
    data = profile.model_dump(mode="json")
    data["persisted"] = persisted
    return data


def _serialize_learning_event(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "actor_id": row.actor_id,
        "tenant_id": row.tenant_id,
        "base_family": row.base_family,
        "event_type": row.event_type,
        "trigger_reason": row.trigger_reason,
        "observed_at": row.observed_at.isoformat() if row.observed_at else None,
        "profile_version": row.profile_version,
        "payload_fingerprint": row.payload_fingerprint,
        "redacted_payload_keys": row.redacted_payload_keys_json or [],
        "metrics": row.metrics_json or {},
        "evidence": row.evidence_json or [],
    }


def _catalog_proof_for_actor(actor_id: str, tenant_id: str) -> ActorProofRecord:
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    catalog_total = actor_catalog.total
    return ActorProofRecord(
        actor_id=actor_id,
        tenant_id=tenant_id,
        catalog_version=actor_catalog_version(catalog_total),
        catalog_total=catalog_total,
        proof_level=ActorProofLevel.API_MAPPED,
        test_input=generate_actor_test_input(entry),
        tenant_scope="tenant",
        provenance=(
            "actor_catalog:registry",
            "api:/api/v1/actors/{actor_id}",
            f"ui:{actor_public_route(actor_id)}",
        ),
        proof_metadata={
            "persisted": False,
            "route_strategy": entry.route_strategy,
            "runnable_status": entry.runnable_status,
            "claim_boundary": "api_mapped_not_live_e2e",
        },
    )


def _serialize_proof(proof: ActorProofRecord, *, persisted: bool = True) -> dict[str, Any]:
    data = proof.model_dump(mode="json")
    data["persisted"] = persisted
    data["claim_boundary"] = (
        "live_e2e_proven"
        if proof.proof_level == ActorProofLevel.LIVE_E2E_PASSED and proof.live_e2e_passed
        else "not_live_e2e_proven"
    )
    return data


async def _load_actor_run_row(
    *,
    session: AsyncSession,
    actor_id: str,
    run_id: str,
    tenant_id: str,
) -> tuple[TaskModel, RunModel, ResultModel | None]:
    if actor_catalog.get(actor_id) is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    stmt = _actor_run_base_query(actor_id, tenant_id).where(RunModel.id == run_id)
    row = (await session.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Actor run not found")
    task, run = row
    result = await _get_result_for_run(session, run.id, tenant_id)
    return task, run, result


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
            "status_history": [_status_event("running", "Actor run accepted", connector="actor_runtime")],
            "logs": [
                {
                    "level": "info",
                    "message": "Actor run accepted",
                    "at": now.isoformat(),
                }
            ],
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
        spec = build_actor_spec(entry)
        profile_repo = ActorStrategyProfileRepository(session)
        active_profile = await profile_repo.get_active_profile(actor_id, tenant_id)
        if active_profile is None:
            active_profile = build_default_strategy_profile(spec)
        runner = create_actor_runner(spec, entry, task_id=task_id, tenant_id=tenant_id)
        runner.strategy_profile = active_profile
        runtime_payload = dict(body.input)
        knowledge_context = body.options.get("knowledge_context")
        if isinstance(knowledge_context, dict):
            runtime_payload["knowledge_context"] = knowledge_context
        runtime_result = await runner.run(runtime_payload)

    task_status, run_status = _terminal_status_for_state(runtime_result.state)
    output = runtime_result.output if runtime_result.state == ActorRunState.SUCCEEDED else {}
    task_metadata = dict(task.metadata_json or {})
    _append_status_history(
        task_metadata,
        task_status,
        runtime_result.error or f"Actor run {runtime_result.state.value}",
        provider=runtime_result.provider,
    )
    task_metadata.update(
        {
            "actor_state": runtime_result.state.value,
            "missing_env_names": list(runtime_result.missing_env_names),
            "provider": runtime_result.provider,
            "knowledge": runtime_result.metadata.get("knowledge", {}),
            "runtime_metadata": runtime_result.metadata,
            "actor_output": output,
            "actor_error": runtime_result.error,
        }
    )

    duration_ms = int((_utcnow() - now).total_seconds() * 1000)
    updated_task = await task_repo.update(task_id, tenant_id, status=task_status, metadata_json=task_metadata)
    if updated_task is not None:
        task = updated_task
    else:
        task.status = task_status
        task.metadata_json = task_metadata

    updated_run = await run_repo.update(
        run_id,
        tenant_id,
        status=run_status,
        error=runtime_result.error,
        completed_at=_utcnow(),
        duration_ms=int(output.get("duration_ms", duration_ms) if output else duration_ms),
        bytes_downloaded=int(output.get("bytes_downloaded", 0) if output else 0),
        status_code=output.get("status_code") if output else None,
    )
    if updated_run is not None:
        run = updated_run
    else:
        run.status = run_status
        run.error = runtime_result.error
        run.completed_at = _utcnow()
        run.duration_ms = int(output.get("duration_ms", duration_ms) if output else duration_ms)
        run.bytes_downloaded = int(output.get("bytes_downloaded", 0) if output else 0)
        run.status_code = output.get("status_code") if output else None

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
    task, run, result = await _load_actor_run_row(
        session=session,
        actor_id=actor_id,
        run_id=run_id,
        tenant_id=tenant_id,
    )
    return {
        "success": True,
        "data": _serialize_actor_run(task, run, result),
    }


@actors_router.get("/{actor_id}/profiles/active")
async def get_active_actor_strategy_profile(
    actor_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Return the active tenant-scoped strategy profile or the computed default profile."""
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    repo = ActorStrategyProfileRepository(session)
    profile = await repo.get_active_profile(actor_id, tenant_id)
    if profile is None:
        profile = build_default_strategy_profile(build_actor_spec(entry))
        return {"success": True, "data": _serialize_profile(profile, persisted=False)}
    return {"success": True, "data": _serialize_profile(profile, persisted=True)}


@actors_router.post("/{actor_id}/profiles")
async def upsert_actor_strategy_profile(
    actor_id: str,
    body: StrategyProfileUpsertRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Persist a tenant-scoped active strategy profile for an actor."""
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    spec = build_actor_spec(entry)
    profile = StrategyProfile(
        actor_id=actor_id,
        base_family=spec.base_family,
        version=body.version,
        policy_version=body.policy_version,
        promoted_by=body.promoted_by,
        provider_order=tuple(body.provider_order),
        schema_aliases={key: tuple(value) for key, value in body.schema_aliases.items()},
        freshness_overrides=body.freshness_overrides,
        replay_fixture_ids=tuple(body.replay_fixture_ids),
        metrics=body.metrics,
    )
    repo = ActorStrategyProfileRepository(session)
    saved = await repo.save_profile(profile, tenant_id, active=True)
    await session.flush()
    return {"success": True, "data": _serialize_profile(saved, persisted=True)}


@actors_router.get("/{actor_id}/profiles/history")
async def list_actor_strategy_profiles(
    actor_id: str,
    limit: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """List tenant-scoped profile promotion history for an actor."""
    if actor_catalog.get(actor_id) is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    repo = ActorStrategyProfileRepository(session)
    profiles = await repo.list_profiles(actor_id, tenant_id, limit=limit)
    return {
        "success": True,
        "data": {
            "items": [_serialize_profile(profile, persisted=True) for profile in profiles],
            "total": len(profiles),
        },
    }


@actors_router.post("/{actor_id}/profiles/learning-events")
async def record_actor_learning_event(
    actor_id: str,
    body: LearningEventCreateRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Persist a sanitized learning event for an actor profile."""
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    spec = build_actor_spec(entry)
    event = ActorLearningEvent(
        actor_id=actor_id,
        tenant_id=tenant_id,
        base_family=spec.base_family,
        event_type=body.event_type,
        trigger_reason=body.trigger_reason,
        profile_version=body.profile_version,
        payload_fingerprint=body.payload_fingerprint,
        redacted_payload_keys=tuple(body.redacted_payload_keys),
        metrics=body.metrics,
        evidence=tuple(body.evidence),
    )
    repo = ActorStrategyProfileRepository(session)
    event_id = await repo.record_learning_event(event)
    await session.flush()
    return {"success": True, "data": {"id": event_id, **event.model_dump(mode="json")}}


@actors_router.get("/{actor_id}/profiles/learning-events")
async def list_actor_learning_events(
    actor_id: str,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """List sanitized tenant-scoped learning events for an actor."""
    if actor_catalog.get(actor_id) is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    repo = ActorStrategyProfileRepository(session)
    rows = await repo.list_learning_events(actor_id, tenant_id, limit=limit)
    return {"success": True, "data": {"items": [_serialize_learning_event(row) for row in rows], "total": len(rows)}}


@actors_router.post("/{actor_id}/profiles/proposals")
async def create_actor_strategy_proposal(
    actor_id: str,
    body: StrategyPatchProposalCreateRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Persist a replay-gated strategy patch proposal."""
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    spec = build_actor_spec(entry)
    basis = f"{tenant_id}:{actor_id}:{body.current_profile_version}:{body.proposed_profile_version}:{json.dumps(body.patch, sort_keys=True, default=str)}"
    proposal = StrategyPatchProposal(
        proposal_id=str(uuid4()) if not body.patch else hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24],
        actor_id=actor_id,
        base_family=spec.base_family,
        current_profile_version=body.current_profile_version,
        proposed_profile_version=body.proposed_profile_version,
        patch=body.patch,
        rationale=body.rationale,
        required_replay_fixture_ids=tuple(body.required_replay_fixture_ids),
    )
    repo = ActorStrategyProfileRepository(session)
    saved = await repo.create_proposal(proposal, tenant_id)
    await session.flush()
    return {"success": True, "data": saved.model_dump(mode="json")}


@actors_router.get("/{actor_id}/profiles/proposals")
async def list_actor_strategy_proposals(
    actor_id: str,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """List tenant-scoped strategy proposals."""
    if actor_catalog.get(actor_id) is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    repo = ActorStrategyProfileRepository(session)
    proposals = await repo.list_proposals(actor_id, tenant_id, limit=limit)
    return {"success": True, "data": {"items": [p.model_dump(mode="json") for p in proposals], "total": len(proposals)}}


@actors_router.post("/{actor_id}/profiles/proposals/{proposal_id}/replay-validations")
async def record_actor_replay_validation(
    actor_id: str,
    proposal_id: str,
    body: ReplayValidationCreateRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Persist replay validation for a strategy proposal."""
    repo = ActorStrategyProfileRepository(session)
    proposal = await repo.get_proposal(proposal_id, actor_id, tenant_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Strategy proposal not found")
    validation = ReplayValidationResult(
        proposal_id=proposal_id,
        passed=body.passed,
        fixtures_run=tuple(body.fixtures_run),
        score_before=body.score_before,
        score_after=body.score_after,
        security_blockers=tuple(body.security_blockers),
        errors=tuple(body.errors),
    )
    saved = await repo.record_replay_validation(actor_id, tenant_id, validation)
    await repo.set_proposal_status(
        proposal_id,
        actor_id,
        tenant_id,
        StrategyPatchStatus.REPLAY_PASSED if saved.passed else StrategyPatchStatus.REPLAY_FAILED,
    )
    await session.flush()
    return {"success": True, "data": saved.model_dump(mode="json")}


@actors_router.post("/{actor_id}/profiles/proposals/{proposal_id}/promote")
async def promote_actor_strategy_profile(
    actor_id: str,
    proposal_id: str,
    body: PromoteProfileRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Promote a strategy proposal after replay validation has passed."""
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    repo = ActorStrategyProfileRepository(session)
    proposal = await repo.get_proposal(proposal_id, actor_id, tenant_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Strategy proposal not found")
    validation = await repo.latest_replay_validation(proposal_id, actor_id, tenant_id)
    if validation is None or not validation.passed:
        raise HTTPException(status_code=409, detail="Replay validation must pass before profile promotion")
    active_profile = await repo.get_active_profile(actor_id, tenant_id)
    if active_profile is None:
        active_profile = build_default_strategy_profile(build_actor_spec(entry))
    try:
        promoted = StrategyProfileEngine().promote_profile(
            active_profile,
            proposal,
            validation,
            promoted_by=body.promoted_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    saved = await repo.save_profile(promoted, tenant_id, active=True)
    await repo.set_proposal_status(proposal_id, actor_id, tenant_id, StrategyPatchStatus.PROMOTED)
    await session.flush()
    return {"success": True, "data": _serialize_profile(saved, persisted=True)}


@actors_router.post("/{actor_id}/fixtures/candidates")
async def create_actor_fixture_candidate(
    actor_id: str,
    body: FixtureCandidateCreateRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Persist a sanitized fixture candidate for review."""
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    spec = build_actor_spec(entry)
    fixture_id = body.fixture_id
    if not fixture_id:
        basis = {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "trace": body.source_trace_id,
            "state": body.state,
            "input": body.sanitized_input,
            "reasons": body.trigger_reasons,
        }
        fixture_id = "fixture-" + hashlib.sha256(json.dumps(basis, sort_keys=True, default=str).encode()).hexdigest()[:24]
    candidate = RegressionFixtureCandidate(
        fixture_id=fixture_id,
        actor_id=actor_id,
        base_family=spec.base_family,
        tenant_id=tenant_id,
        trigger_reasons=tuple(body.trigger_reasons),
        source_trace_id=body.source_trace_id,
        state=body.state,
        provider=body.provider,
        sanitized_input=body.sanitized_input,
        redacted_payload_keys=tuple(body.redacted_payload_keys),
        expected_assertions=tuple(body.expected_assertions),
        tags=tuple(body.tags),
    )
    repo = ActorFixtureRepository(session)
    saved = await repo.create_candidate(candidate)
    await session.flush()
    row = await repo.get_candidate(saved.fixture_id, actor_id, tenant_id)
    return {"success": True, "data": repo.serialize_row(row)}


@actors_router.get("/{actor_id}/fixtures/candidates")
async def list_actor_fixture_candidates(
    actor_id: str,
    status: str = Query("", description="Optional candidate status filter"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """List tenant-scoped fixture review candidates for an actor."""
    if actor_catalog.get(actor_id) is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    repo = ActorFixtureRepository(session)
    rows = await repo.list_candidates(actor_id, tenant_id, status=status or None, limit=limit)
    return {"success": True, "data": {"items": [repo.serialize_row(row) for row in rows], "total": len(rows)}}


@actors_router.post("/{actor_id}/fixtures/candidates/{fixture_id}/approve")
async def approve_actor_fixture_candidate(
    actor_id: str,
    fixture_id: str,
    body: FixtureReviewRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Approve a sanitized fixture candidate for materialization."""
    repo = ActorFixtureRepository(session)
    row = await repo.review_candidate(
        fixture_id,
        actor_id,
        tenant_id,
        status=FixtureReviewStatus.APPROVED,
        reviewed_by=body.reviewed_by,
        notes=body.notes,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Fixture candidate not found")
    await session.flush()
    return {"success": True, "data": repo.serialize_row(row)}


@actors_router.post("/{actor_id}/fixtures/candidates/{fixture_id}/reject")
async def reject_actor_fixture_candidate(
    actor_id: str,
    fixture_id: str,
    body: FixtureReviewRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Reject a fixture candidate without materializing it."""
    repo = ActorFixtureRepository(session)
    row = await repo.review_candidate(
        fixture_id,
        actor_id,
        tenant_id,
        status=FixtureReviewStatus.REJECTED,
        reviewed_by=body.reviewed_by,
        notes=body.notes,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Fixture candidate not found")
    await session.flush()
    return {"success": True, "data": repo.serialize_row(row)}


@actors_router.post("/{actor_id}/fixtures/candidates/{fixture_id}/materialize")
async def materialize_actor_fixture_candidate(
    actor_id: str,
    fixture_id: str,
    body: FixtureReviewRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Materialize an approved sanitized candidate into a replay fixture payload."""
    repo = ActorFixtureRepository(session)
    try:
        fixture = await repo.materialize_candidate(
            fixture_id,
            actor_id,
            tenant_id,
            reviewed_by=body.reviewed_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if fixture is None:
        raise HTTPException(status_code=404, detail="Fixture candidate not found")
    await session.flush()
    return {"success": True, "data": fixture.model_dump(mode="json")}


@actors_router.get("/proof/summary")
async def get_actor_proof_summary(
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Return honest proof counts for the current actor catalog."""
    repo = ActorProofRepository(session)
    summary = await repo.summary(tenant_id, catalog_actor_count=actor_catalog.total)
    data = summary.model_dump(mode="json")
    data["proof_levels"] = [level.value for level in ActorProofLevel]
    data["full_catalog_live_e2e_proven"] = (
        summary.proof_ledger_count == summary.catalog_actor_count
        and summary.live_e2e_passed_count == summary.catalog_actor_count
        and summary.catalog_actor_count > 0
    )
    return {"success": True, "data": data}


@actors_router.get("/proof/records")
async def list_actor_proof_records(
    proof_level: str = Query("", description="Optional proof-level filter"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """List latest tenant-scoped proof rows without implying full live E2E coverage."""
    repo = ActorProofRepository(session)
    items, total = await repo.latest_records(
        tenant_id,
        proof_level=proof_level or None,
        limit=limit,
        offset=offset,
    )
    return {
        "success": True,
        "data": {
            "items": [_serialize_proof(item) for item in items],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@actors_router.get("/{actor_id}/proof")
async def get_actor_proof(
    actor_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Return latest proof for one actor, or a non-persisted API-mapped fallback."""
    if actor_catalog.get(actor_id) is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    repo = ActorProofRepository(session)
    proof = await repo.latest_for_actor(actor_id, tenant_id)
    if proof is None:
        return {"success": True, "data": _serialize_proof(_catalog_proof_for_actor(actor_id, tenant_id), persisted=False)}
    return {"success": True, "data": _serialize_proof(proof)}


@actors_router.post("/{actor_id}/proof")
async def record_actor_proof(
    actor_id: str,
    body: ActorProofRecordRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Persist a proof row created by a proof runner, UI route verifier, or fixture replay."""
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    catalog_total = actor_catalog.total
    proof = ActorProofRecord(
        actor_id=actor_id,
        tenant_id=tenant_id,
        catalog_version=actor_catalog_version(catalog_total),
        catalog_total=catalog_total,
        proof_level=body.proof_level,
        test_input=body.test_input or generate_actor_test_input(entry),
        run_id=body.run_id,
        result_id=body.result_id,
        items_count=body.items_count,
        schema_passed=body.schema_passed,
        export_json_passed=body.export_json_passed,
        export_csv_passed=body.export_csv_passed,
        ui_route_passed=body.ui_route_passed,
        live_e2e_passed=body.live_e2e_passed,
        fixture_replay_passed=body.fixture_replay_passed,
        blocked_reason=body.blocked_reason,
        failure_reason=body.failure_reason,
        failure_class=body.failure_class,
        source_timestamp=body.source_timestamp,
        policy_version=body.policy_version,
        tenant_scope="tenant",
        provenance=tuple(body.provenance or ["manual-proof-api"]),
        proof_metadata={
            **body.proof_metadata,
            "route_strategy": entry.route_strategy,
            "runnable_status": entry.runnable_status,
        },
    )
    saved = await ActorProofRepository(session).record_proof(proof)
    await session.flush()
    return {"success": True, "data": _serialize_proof(saved)}


@actors_router.post("/{actor_id}/runs/{run_id}/proof")
async def record_actor_proof_from_run(
    actor_id: str,
    run_id: str,
    body: ActorProofFromRunRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Verify a persisted actor run into an explicit proof row."""
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    task, run, result = await _load_actor_run_row(
        session=session,
        actor_id=actor_id,
        run_id=run_id,
        tenant_id=tenant_id,
    )
    metadata = task.metadata_json or {}
    item_count = int(result.item_count or 0) if result is not None else 0
    has_result = result is not None
    export_json_passed = has_result
    export_csv_passed = has_result
    failure_class = classify_actor_proof_failure(
        run_status=run.status,
        error=run.error or metadata.get("actor_error"),
        missing_env_names=tuple(metadata.get("missing_env_names") or ()),
        item_count=item_count,
    )
    proof_level = choose_proof_level(
        run_status=run.status,
        has_result=has_result,
        item_count=item_count,
        export_json_passed=export_json_passed,
        export_csv_passed=export_csv_passed,
        ui_route_passed=body.ui_route_passed,
        fixture_replay_passed=body.fixture_replay_passed,
    )
    proof = ActorProofRecord(
        actor_id=actor_id,
        tenant_id=tenant_id,
        catalog_version=actor_catalog_version(actor_catalog.total),
        catalog_total=actor_catalog.total,
        proof_level=proof_level,
        test_input=dict(metadata.get("input") or generate_actor_test_input(entry)),
        run_id=run.id,
        result_id=result.id if result is not None else None,
        items_count=item_count,
        schema_passed=has_result,
        export_json_passed=export_json_passed,
        export_csv_passed=export_csv_passed,
        ui_route_passed=body.ui_route_passed,
        live_e2e_passed=proof_level == ActorProofLevel.LIVE_E2E_PASSED,
        fixture_replay_passed=body.fixture_replay_passed,
        blocked_reason=run.error if failure_class != ActorProofFailureClass.NONE else None,
        failure_reason=run.error if failure_class != ActorProofFailureClass.NONE else None,
        failure_class=failure_class,
        source_timestamp=body.source_timestamp,
        policy_version=body.policy_version,
        tenant_scope="tenant",
        provenance=tuple(body.provenance or ["actor-run-proof-api", f"run:{run.id}"]),
        proof_metadata={
            **body.proof_metadata,
            "route_strategy": entry.route_strategy,
            "runnable_status": entry.runnable_status,
            "export_json_verified": export_json_passed,
            "export_csv_verified": export_csv_passed,
        },
    )
    saved = await ActorProofRepository(session).record_proof(proof)
    await session.flush()
    return {"success": True, "data": _serialize_proof(saved)}


@actors_router.get("/{actor_id}/value-metrics")
async def get_actor_value_metrics(
    actor_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Return tenant-scoped customer value metrics for one actor."""
    if actor_catalog.get(actor_id) is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")

    rows = (await session.execute(_actor_run_base_query(actor_id, tenant_id))).all()
    total_runs = len(rows)
    status_counts: dict[str, int] = {}
    cache_hits = 0
    fresh_runs = 0
    stale_runs = 0
    blocked_runs = 0
    total_duration_ms = 0
    total_bytes = 0
    total_items = 0
    quality_scores: list[float] = []

    for task, run in rows:
        status_counts[run.status] = status_counts.get(run.status, 0) + 1
        if run.status in {"blocked_policy", "failed", "skipped_missing_key"}:
            blocked_runs += 1
        total_duration_ms += int(run.duration_ms or 0)
        total_bytes += int(run.bytes_downloaded or 0)
        metadata = task.metadata_json or {}
        knowledge = metadata.get("knowledge", {}) if isinstance(metadata.get("knowledge"), dict) else {}
        if knowledge.get("decision") in {"serve_cached", "serve_cached_and_refresh"}:
            cache_hits += 1
        if knowledge.get("freshness_state") == "fresh":
            fresh_runs += 1
        if knowledge.get("freshness_state") in {"stale", "expired"}:
            stale_runs += 1
        result = await _get_result_for_run(session, run.id, tenant_id)
        if result is not None:
            total_items += int(result.item_count or 0)
            quality_scores.append(float(result.confidence or 0.0))

    fixture_repo = ActorFixtureRepository(session)
    fixture_rows = await fixture_repo.list_candidates(actor_id, tenant_id, limit=200)
    fixture_status_counts: dict[str, int] = {}
    for row in fixture_rows:
        fixture_status_counts[row.status] = fixture_status_counts.get(row.status, 0) + 1

    profile_repo = ActorStrategyProfileRepository(session)
    learning_events = await profile_repo.list_learning_events(actor_id, tenant_id, limit=200)
    proposals = await profile_repo.list_proposals(actor_id, tenant_id, limit=200)
    active_profile = await profile_repo.get_active_profile(actor_id, tenant_id)

    successful_runs = status_counts.get("completed", 0)
    success_rate = (successful_runs / total_runs) if total_runs else 0.0
    cache_hit_rate = (cache_hits / total_runs) if total_runs else 0.0
    average_quality = (sum(quality_scores) / len(quality_scores)) if quality_scores else 0.0
    estimated_fresh_run_seconds = 30
    saved_seconds = cache_hits * estimated_fresh_run_seconds
    saved_usd = round(cache_hits * 0.02, 4)

    return {
        "success": True,
        "data": {
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_or_blocked_runs": blocked_runs,
            "status_counts": status_counts,
            "success_rate": round(success_rate, 4),
            "cache_hits": cache_hits,
            "cache_hit_rate": round(cache_hit_rate, 4),
            "fresh_runs": fresh_runs,
            "stale_runs": stale_runs,
            "estimated_time_saved_seconds": saved_seconds,
            "estimated_cost_saved_usd": saved_usd,
            "total_duration_ms": total_duration_ms,
            "total_bytes_downloaded": total_bytes,
            "total_items": total_items,
            "average_quality_score": round(average_quality, 4),
            "learning_event_count": len(learning_events),
            "patch_proposal_count": len(proposals),
            "active_profile_version": active_profile.version if active_profile else None,
            "fixture_status_counts": fixture_status_counts,
            "value_signals": {
                "avoided_reruns": cache_hits,
                "quality_improvement_candidates": len(learning_events),
                "accepted_fixtures": fixture_status_counts.get("materialized", 0),
            },
        },
    }


@actors_router.get("/{actor_id}/runs/{run_id}/logs")
async def get_actor_run_logs(
    actor_id: str,
    run_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Return status history and operator logs for a tenant-scoped actor run."""
    task, run, result = await _load_actor_run_row(
        session=session,
        actor_id=actor_id,
        run_id=run_id,
        tenant_id=tenant_id,
    )
    serialized = _serialize_actor_run(task, run, result)
    return {
        "success": True,
        "data": {
            "run_id": run.id,
            "status_history": serialized["status_history"],
            "logs": serialized["logs"],
        },
    }


@actors_router.get("/{actor_id}/runs/{run_id}/usage")
async def get_actor_run_usage(
    actor_id: str,
    run_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Return tenant-scoped usage and quota-facing counters for one actor run."""
    task, run, result = await _load_actor_run_row(
        session=session,
        actor_id=actor_id,
        run_id=run_id,
        tenant_id=tenant_id,
    )
    return {
        "success": True,
        "data": {
            "run_id": run.id,
            "task_id": task.id,
            "usage": _serialize_actor_run(task, run, result)["usage"],
        },
    }


@actors_router.post("/{actor_id}/runs/{run_id}/cancel")
async def cancel_actor_run(
    actor_id: str,
    run_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Cancel a non-terminal actor run without touching other tenants."""
    task, run, result = await _load_actor_run_row(
        session=session,
        actor_id=actor_id,
        run_id=run_id,
        tenant_id=tenant_id,
    )
    if run.status in {"completed", "failed", "blocked_policy", "skipped_missing_key", "cancelled"}:
        return {
            "success": True,
            "data": {
                **_serialize_actor_run(task, run, result),
                "cancelled": False,
                "reason": "run_already_terminal",
            },
        }

    metadata = dict(task.metadata_json or {})
    _append_status_history(metadata, "cancelled", "Actor run cancelled by tenant request")
    task_repo = TaskRepository(session)
    run_repo = RunRepository(session)
    task = await task_repo.update(task.id, tenant_id, status="cancelled", metadata_json=metadata) or task
    run = await run_repo.update(
        run.id,
        tenant_id,
        status="cancelled",
        error="cancelled_by_tenant",
        completed_at=_utcnow(),
    ) or run
    await session.flush()
    return {
        "success": True,
        "data": {
            **_serialize_actor_run(task, run, result),
            "cancelled": True,
        },
    }


@actors_router.post("/{actor_id}/runs/{run_id}/rerun")
async def rerun_actor_run(
    actor_id: str,
    run_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Create a new actor run from the original input/options."""
    task, _, _ = await _load_actor_run_row(
        session=session,
        actor_id=actor_id,
        run_id=run_id,
        tenant_id=tenant_id,
    )
    metadata = task.metadata_json or {}
    request = ActorRunRequest(
        input=dict(metadata.get("input") or {}),
        options={**dict(metadata.get("options") or {}), "rerun_of_run_id": run_id},
    )
    response = await create_actor_run(actor_id, request, session, tenant_id)
    response["data"]["rerun_of_run_id"] = run_id
    return response


@actors_router.post("/{actor_id}/runs/{run_id}/retry")
async def retry_actor_run(
    actor_id: str,
    run_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Retry a failed or blocked actor run by creating a fresh native run."""
    task, run, _ = await _load_actor_run_row(
        session=session,
        actor_id=actor_id,
        run_id=run_id,
        tenant_id=tenant_id,
    )
    metadata = task.metadata_json or {}
    request = ActorRunRequest(
        input=dict(metadata.get("input") or {}),
        options={
            **dict(metadata.get("options") or {}),
            "retry_of_run_id": run_id,
            "retry_of_status": run.status,
        },
    )
    response = await create_actor_run(actor_id, request, session, tenant_id)
    response["data"]["retry_of_run_id"] = run_id
    return response


@actors_router.get("/{actor_id}/runs/{run_id}/export")
async def export_actor_run(
    actor_id: str,
    run_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    """Export one actor run's dataset as JSON or CSV."""
    _, run, result = await _load_actor_run_row(
        session=session,
        actor_id=actor_id,
        run_id=run_id,
        tenant_id=tenant_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="No result dataset for this actor run")
    items = result.extracted_data if isinstance(result.extracted_data, list) else []
    if format == "csv":
        headers = list(dict.fromkeys(key for item in items if isinstance(item, dict) for key in item.keys()))
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            if isinstance(item, dict):
                writer.writerow({key: str(value)[:500] if value is not None else "" for key, value in item.items()})
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="actor_run_{run.id}.csv"'},
        )
    return Response(
        content=json.dumps(items, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="actor_run_{run.id}.json"'},
    )


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
