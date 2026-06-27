from __future__ import annotations

import asyncio


def _spec():
    from packages.core.actor_runtime import ActorSpec, ProviderStep

    return ActorSpec(
        actor_id="actor-learning-1",
        slug="learning-demo",
        title="Learning Demo",
        base_family="generic_web_page_extraction",
        provider_chain=[ProviderStep(name="http_worker", priority=1)],
    )


def test_learning_event_redacts_sensitive_payload_and_detects_missing_fields() -> None:
    from packages.core.actor_runtime import (
        ActorRuntimeResult,
        ActorRunState,
        StrategyProfileEngine,
        build_default_strategy_profile,
    )

    spec = _spec()
    profile = build_default_strategy_profile(spec)
    result = ActorRuntimeResult(
        actor_id=spec.actor_id,
        state=ActorRunState.SUCCEEDED,
        provider="http_worker",
        metadata={
            "eval": {
                "score": 0.5,
                "missing_required_fields": ("price",),
            }
        },
    )

    event = StrategyProfileEngine().build_learning_event(
        spec=spec,
        payload={"target": "https://example.com", "api_key": "secret-value"},
        result=result,
        profile=profile,
        tenant_id="tenant-a",
    )

    assert event.event_type == "missing_fields"
    assert event.redacted_payload_keys == ("api_key",)
    assert event.payload_fingerprint
    assert event.metrics["missing_required_fields"] == ("price",)


def test_strategy_profile_promotion_requires_deterministic_replay() -> None:
    from packages.core.actor_runtime import StrategyProfileEngine, StrategyProfile

    engine = StrategyProfileEngine()
    profile = StrategyProfile(
        actor_id="actor-learning-1",
        base_family="generic_web_page_extraction",
        replay_fixture_ids=("fixture-happy-path",),
    )
    proposal = engine.propose_patch(
        event=engine.build_learning_event(
            spec=_spec(),
            payload={"target": "https://example.com"},
            result=__import__("packages.core.actor_runtime", fromlist=["ActorRuntimeResult"]).ActorRuntimeResult(
                actor_id="actor-learning-1",
                state=__import__("packages.core.actor_runtime", fromlist=["ActorRunState"]).ActorRunState.SUCCEEDED,
                metadata={"eval": {"missing_required_fields": ("price",), "score": 0.4}},
            ),
            profile=profile,
        ),
        profile=profile,
    )

    failed_validation = engine.validate_replay(proposal, ())
    try:
        engine.promote_profile(profile, proposal, failed_validation)
    except ValueError as exc:
        assert "replay validation" in str(exc)
    else:
        raise AssertionError("Expected promotion to require replay validation")


def test_strategy_profile_promotes_after_replay_and_applies_patch() -> None:
    from packages.core.actor_runtime import StrategyPatchProposal, StrategyProfile, StrategyProfileEngine

    profile = StrategyProfile(
        actor_id="actor-learning-1",
        base_family="generic_web_page_extraction",
        replay_fixture_ids=("fixture-happy-path",),
    )
    proposal = StrategyPatchProposal(
        proposal_id="proposal-1",
        actor_id=profile.actor_id,
        base_family=profile.base_family,
        current_profile_version=profile.version,
        proposed_profile_version="1.0.1",
        patch={
            "schema_aliases": {"price": ("amount", "cost")},
            "provider_order": ("shopify_products_json", "http_worker"),
        },
        rationale="Replay proved alias improvement.",
        required_replay_fixture_ids=("fixture-happy-path",),
    )
    engine = StrategyProfileEngine()
    validation = engine.validate_replay(
        proposal,
        (
            {
                "fixture_id": "fixture-happy-path",
                "passed": True,
                "score_before": 0.65,
                "score_after": 0.91,
            },
        ),
    )
    promoted = engine.promote_profile(profile, proposal, validation)

    assert promoted.version == "1.0.1"
    assert promoted.schema_aliases["price"] == ("amount", "cost")
    assert promoted.provider_order == ("shopify_products_json", "http_worker")
    assert promoted.metrics["last_replay_score_after"] == 0.91


def test_base_actor_runner_exposes_strategy_profile_metadata() -> None:
    from packages.core.actor_runtime import ActorRunState, BaseActorRunner, StrategyProfile

    class DemoRunner(BaseActorRunner):
        async def execute(self, payload: dict) -> dict:
            return {"items": [{"target": payload["target"]}], "item_count": 1}

    profile = StrategyProfile(
        actor_id="actor-learning-1",
        base_family="generic_web_page_extraction",
        version="1.2.3",
        provider_order=("http_worker",),
        replay_fixture_ids=("fixture-a",),
    )
    runner = DemoRunner(_spec(), strategy_profile=profile)

    result = asyncio.run(runner.run({"target": "https://example.com"}))

    assert result.state == ActorRunState.SUCCEEDED
    assert result.metadata["strategy_profile"]["version"] == "1.2.3"
    assert result.metadata["strategy_profile"]["provider_order"] == ["http_worker"]
    assert result.metadata["strategy_profile"]["replay_fixture_ids"] == ["fixture-a"]


def test_base_actor_runner_records_sanitized_learning_events() -> None:
    from packages.core.actor_runtime import ActorRunState, BaseActorRunner, StrategyProfile

    class MemoryProfileStore:
        def __init__(self) -> None:
            self.events = []

        def get_profile(self, actor_id: str, tenant_id: str | None = None):  # noqa: ANN001
            return None

        def record_learning_event(self, event):  # noqa: ANN001
            self.events.append(event)

        def promote_profile(self, profile):  # noqa: ANN001
            return None

    class DemoRunner(BaseActorRunner):
        tenant_id = "tenant-learning"

        async def execute(self, payload: dict) -> dict:
            return {"items": [{"target": payload["target"]}], "item_count": 1}

    store = MemoryProfileStore()
    profile = StrategyProfile(
        actor_id="actor-learning-1",
        base_family="generic_web_page_extraction",
        version="1.2.3",
    )
    runner = DemoRunner(_spec(), strategy_profile=profile, strategy_profile_store=store)

    result = asyncio.run(runner.run({"target": "https://example.com", "token": "secret-value"}))

    assert result.state == ActorRunState.SUCCEEDED
    assert len(store.events) == 1
    assert store.events[0].tenant_id == "tenant-learning"
    assert store.events[0].redacted_payload_keys == ("token",)
    assert result.metadata["strategy_profile"]["learning_event"]["event_type"] == "security_risk"
    assert "secret-value" not in str(result.metadata)
