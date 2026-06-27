from __future__ import annotations

import asyncio
from typing import Any


def test_actor_trace_metadata_is_stable_and_payload_safe() -> None:
    from packages.core.actor_runtime import (
        ActorSpec,
        KnowledgeDecision,
        KnowledgeFreshnessState,
        KnowledgeRuntimeDecisionResult,
        build_actor_governance_metadata,
    )

    spec = ActorSpec(
        actor_id="actor-trace-1",
        slug="trace-demo",
        title="Trace Demo",
        base_family="generic_web_page_extraction",
    )
    decision = KnowledgeRuntimeDecisionResult(
        decision=KnowledgeDecision.RUN_FRESH,
        freshness_state=KnowledgeFreshnessState.MISSING,
        reason="knowledge_snapshot_missing",
    )
    metadata = build_actor_governance_metadata(
        spec=spec,
        payload={"target": "https://example.com", "api_key": "secret-value-must-not-leak"},
        output={"extracted_data": [{"name": "Item"}], "item_count": 1, "confidence": 0.8},
        decision=decision,
        provider="unit-test",
        requested_fields=("name",),
    )

    assert metadata["trace"]["actor_id"] == "actor-trace-1"
    assert metadata["trace"]["decision"] == "run_fresh"
    assert metadata["security"]["redacted_payload_keys"] == ["api_key"]
    assert "secret-value-must-not-leak" not in str(metadata)


def test_base_actor_runner_attaches_trace_cost_security_and_eval_metadata() -> None:
    from packages.core.actor_runtime import ActorRunState, ActorSpec, BaseActorRunner

    class DemoRunner(BaseActorRunner):
        async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
            return {
                "extracted_data": [{"name": "Item A"}],
                "item_count": 1,
                "confidence": 0.8,
                "extraction_method": "unit_test",
            }

    runner = DemoRunner(
        ActorSpec(
            actor_id="actor-trace-2",
            slug="trace-demo-2",
            title="Trace Demo 2",
            base_family="generic_web_page_extraction",
        )
    )
    result = asyncio.run(
        runner.run(
            {
                "target": "https://example.com",
                "requested_fields": ["name"],
            }
        )
    )

    assert result.state == ActorRunState.SUCCEEDED
    assert result.metadata["trace"]["decision"] == "run_fresh"
    assert result.metadata["cost"]["pricing_basis"] == "curl_cffi_page"
    assert result.metadata["security"]["allowed"] is True
    assert result.metadata["eval"]["passed"] is True
