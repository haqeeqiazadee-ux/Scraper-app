from __future__ import annotations


def test_actor_cost_estimate_charges_fresh_marketplace_runs() -> None:
    from packages.core.actor_runtime import (
        ActorSpec,
        KnowledgeDecision,
        KnowledgeFreshnessState,
        KnowledgeRuntimeDecisionResult,
        estimate_actor_cost,
    )

    spec = ActorSpec(
        actor_id="marketplace-1",
        slug="marketplace",
        title="Marketplace",
        base_family="marketplace_product_catalog",
    )
    decision = KnowledgeRuntimeDecisionResult(
        decision=KnowledgeDecision.RUN_FRESH,
        freshness_state=KnowledgeFreshnessState.MISSING,
        reason="knowledge_snapshot_missing",
    )

    cost = estimate_actor_cost(spec, decision, {"item_count": 3})

    assert cost.estimated_usd == 0.03
    assert cost.estimated_credits > 0
    assert cost.saved_by_knowledge_usd == 0.0


def test_actor_cost_estimate_counts_cached_reuse_as_savings() -> None:
    from packages.core.actor_runtime import (
        ActorSpec,
        KnowledgeDecision,
        KnowledgeFreshnessState,
        KnowledgeRuntimeDecisionResult,
        estimate_actor_cost,
    )

    spec = ActorSpec(
        actor_id="maps-1",
        slug="maps",
        title="Maps",
        base_family="local_maps_serp",
    )
    decision = KnowledgeRuntimeDecisionResult(
        decision=KnowledgeDecision.SERVE_CACHED,
        freshness_state=KnowledgeFreshnessState.FRESH,
        reason="knowledge_snapshot_fresh",
    )

    cost = estimate_actor_cost(spec, decision, {"item_count": 5})

    assert cost.estimated_usd == 0.0
    assert cost.estimated_credits == 0
    assert cost.saved_by_knowledge_usd == 0.01
    assert cost.pricing_basis == "knowledge_reuse_avoided:serper_places"
