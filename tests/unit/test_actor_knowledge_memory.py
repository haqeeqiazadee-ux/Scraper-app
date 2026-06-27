from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any


def _spec() -> Any:
    from packages.core.actor_runtime import ActorSpec

    return ActorSpec(
        actor_id="actor-knowledge-1",
        slug="knowledge-demo",
        title="Knowledge Demo",
        base_family="generic_web_page_extraction",
    )


class DemoKnowledgeStore:
    def __init__(self, snapshot: Any | None = None) -> None:
        self.snapshot = snapshot
        self.recorded: list[dict[str, Any]] = []

    def lookup(self, *, spec: Any, payload: dict[str, Any], context: Any) -> Any | None:
        return self.snapshot

    def record(self, *, spec: Any, payload: dict[str, Any], context: Any, result: Any) -> None:
        self.recorded.append(
            {
                "actor_id": spec.actor_id,
                "tenant_id": context.tenant_id,
                "query_fingerprint": context.query_fingerprint,
                "result_state": result.state,
            }
        )


def test_knowledge_evaluator_serves_fresh_cached_snapshot() -> None:
    from packages.core.actor_runtime import (
        FreshnessPolicy,
        KnowledgeDecision,
        KnowledgeFreshnessEvaluator,
        KnowledgeRuntimeContext,
        KnowledgeSnapshot,
        KnowledgeSource,
    )

    now = datetime(2026, 6, 27, 12, tzinfo=UTC)
    snapshot = KnowledgeSnapshot(
        actor_id="actor-knowledge-1",
        tenant_id="tenant-1",
        query_fingerprint="fp-1",
        output={"items": [{"name": "cached"}]},
        source=KnowledgeSource.GRAPH,
        observed_at=now - timedelta(minutes=5),
        provenance=("graph-node:result-1",),
        field_coverage={"name": True},
    )
    decision = KnowledgeFreshnessEvaluator(FreshnessPolicy(fresh_ttl_seconds=3600)).evaluate(
        spec=_spec(),
        context=KnowledgeRuntimeContext(
            actor_id="actor-knowledge-1",
            tenant_id="tenant-1",
            query_fingerprint="fp-1",
            requested_fields=("name",),
            now=now,
        ),
        snapshot=snapshot,
    )

    assert decision.decision == KnowledgeDecision.SERVE_CACHED
    assert decision.reusable_output == {"items": [{"name": "cached"}]}
    assert decision.source == KnowledgeSource.GRAPH


def test_knowledge_evaluator_blocks_tenant_mismatch_and_missing_provenance() -> None:
    from packages.core.actor_runtime import (
        KnowledgeDecision,
        KnowledgeFreshnessEvaluator,
        KnowledgeFreshnessState,
        KnowledgeRuntimeContext,
        KnowledgeSnapshot,
    )

    now = datetime(2026, 6, 27, 12, tzinfo=UTC)
    evaluator = KnowledgeFreshnessEvaluator()
    tenant_mismatch = evaluator.evaluate(
        spec=_spec(),
        context=KnowledgeRuntimeContext(
            actor_id="actor-knowledge-1",
            tenant_id="tenant-2",
            query_fingerprint="fp-1",
            now=now,
        ),
        snapshot=KnowledgeSnapshot(
            actor_id="actor-knowledge-1",
            tenant_id="tenant-1",
            query_fingerprint="fp-1",
            observed_at=now,
            provenance=("db:row-1",),
        ),
    )
    missing_provenance = evaluator.evaluate(
        spec=_spec(),
        context=KnowledgeRuntimeContext(
            actor_id="actor-knowledge-1",
            tenant_id="tenant-1",
            query_fingerprint="fp-1",
            now=now,
        ),
        snapshot=KnowledgeSnapshot(
            actor_id="actor-knowledge-1",
            tenant_id="tenant-1",
            query_fingerprint="fp-1",
            observed_at=now,
        ),
    )

    assert tenant_mismatch.decision == KnowledgeDecision.RUN_FRESH
    assert tenant_mismatch.freshness_state == KnowledgeFreshnessState.BLOCKED
    assert tenant_mismatch.reason == "tenant_isolation_mismatch"
    assert missing_provenance.decision == KnowledgeDecision.RUN_FRESH
    assert missing_provenance.reason == "missing_provenance"


def test_knowledge_evaluator_marks_stale_snapshot_for_revalidation() -> None:
    from packages.core.actor_runtime import (
        FreshnessPolicy,
        KnowledgeDecision,
        KnowledgeFreshnessEvaluator,
        KnowledgeRuntimeContext,
        KnowledgeSnapshot,
    )

    now = datetime(2026, 6, 27, 12, tzinfo=UTC)
    decision = KnowledgeFreshnessEvaluator(
        FreshnessPolicy(fresh_ttl_seconds=60, stale_ttl_seconds=3600)
    ).evaluate(
        spec=_spec(),
        context=KnowledgeRuntimeContext(
            actor_id="actor-knowledge-1",
            tenant_id="tenant-1",
            query_fingerprint="fp-1",
            now=now,
        ),
        snapshot=KnowledgeSnapshot(
            actor_id="actor-knowledge-1",
            tenant_id="tenant-1",
            query_fingerprint="fp-1",
            output={"items": [{"name": "stale"}]},
            observed_at=now - timedelta(minutes=10),
            provenance=("cache:fp-1",),
        ),
    )

    assert decision.decision == KnowledgeDecision.SERVE_CACHED_AND_REFRESH
    assert decision.age_seconds == 600


def test_knowledge_evaluator_requests_partial_refresh_for_missing_fields() -> None:
    from packages.core.actor_runtime import (
        KnowledgeDecision,
        KnowledgeFreshnessEvaluator,
        KnowledgeRuntimeContext,
        KnowledgeSnapshot,
    )

    now = datetime(2026, 6, 27, 12, tzinfo=UTC)
    decision = KnowledgeFreshnessEvaluator().evaluate(
        spec=_spec(),
        context=KnowledgeRuntimeContext(
            actor_id="actor-knowledge-1",
            tenant_id="tenant-1",
            query_fingerprint="fp-1",
            requested_fields=("name", "price"),
            now=now,
        ),
        snapshot=KnowledgeSnapshot(
            actor_id="actor-knowledge-1",
            tenant_id="tenant-1",
            query_fingerprint="fp-1",
            output={"items": [{"name": "cached"}]},
            observed_at=now,
            provenance=("graph:fp-1",),
            field_coverage={"name": True},
        ),
    )

    assert decision.decision == KnowledgeDecision.PARTIAL_REFRESH
    assert decision.refresh_fields == ("price",)


def test_base_actor_runner_serves_cached_snapshot_without_execute() -> None:
    from packages.core.actor_runtime import ActorRunState, BaseActorRunner, KnowledgeSnapshot

    class DemoRunner(BaseActorRunner):
        executed = False

        async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
            self.executed = True
            return {"items": [{"name": "fresh"}]}

    payload = {"target": "https://example.com", "tenant_id": "tenant-1", "query_fingerprint": "fp-1"}
    store = DemoKnowledgeStore(
        KnowledgeSnapshot(
            actor_id="actor-knowledge-1",
            tenant_id="tenant-1",
            query_fingerprint="fp-1",
            output={"items": [{"name": "cached"}]},
            observed_at=datetime.now(UTC),
            provenance=("graph:fp-1",),
        )
    )
    runner = DemoRunner(_spec(), knowledge_store=store)

    result = asyncio.run(runner.run(payload))

    assert result.state == ActorRunState.SUCCEEDED
    assert result.output == {"items": [{"name": "cached"}]}
    assert runner.executed is False
    assert result.metadata["knowledge"]["decision"] == "serve_cached"


def test_base_actor_runner_records_successful_fresh_result() -> None:
    from packages.core.actor_runtime import ActorRunState, BaseActorRunner

    class DemoRunner(BaseActorRunner):
        async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
            return {"items": [{"name": "fresh"}]}

    store = DemoKnowledgeStore()
    runner = DemoRunner(_spec(), knowledge_store=store)
    result = asyncio.run(
        runner.run({"target": "https://example.com", "tenant_id": "tenant-1", "query_fingerprint": "fp-1"})
    )

    assert result.state == ActorRunState.SUCCEEDED
    assert result.output == {"items": [{"name": "fresh"}]}
    assert store.recorded == [
        {
            "actor_id": "actor-knowledge-1",
            "tenant_id": "tenant-1",
            "query_fingerprint": "fp-1",
            "result_state": ActorRunState.SUCCEEDED,
        }
    ]
