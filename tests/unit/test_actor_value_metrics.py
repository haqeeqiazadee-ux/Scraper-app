from __future__ import annotations

import asyncio
from typing import Any

from httpx import AsyncClient

from packages.core.actor_catalog.registry import actor_catalog
from packages.core.actor_runtime import ActorSpec
from tests.unit.test_actor_runs_api import TENANT_HEADER, _with_client


def _first_native_actor() -> str:
    actors, total = actor_catalog.search(strategy="native_pipeline", limit=1)
    assert total > 0
    return actors[0].actor_id


def test_actor_value_metrics_aggregate_runs_profiles_and_fixtures(monkeypatch) -> None:  # noqa: ANN001
    actor_id = _first_native_actor()

    from packages.core.actor_runtime import ActorRuntimeResult, ActorRunState, BaseActorRunner
    from services.control_plane.routers import actors as actors_router_module

    class CachedRunner(BaseActorRunner):
        async def run(self, payload: dict) -> Any:
            return ActorRuntimeResult(
                actor_id=self.spec.actor_id,
                state=ActorRunState.SUCCEEDED,
                provider="cache-aware-provider",
                output={
                    "extracted_data": [{"name": "Cached Item"}],
                    "item_count": 1,
                    "confidence": 0.88,
                    "duration_ms": 4,
                    "bytes_downloaded": 0,
                    "extraction_method": "knowledge_cached",
                },
                metadata={
                    "knowledge": {
                        "decision": "serve_cached",
                        "freshness_state": "fresh",
                    }
                },
            )

    def fake_create_runner(spec: ActorSpec, entry: Any, *, task_id: str, tenant_id: str) -> CachedRunner:
        return CachedRunner(spec)

    monkeypatch.setattr(actors_router_module, "create_actor_runner", fake_create_runner)

    async def scenario(client: AsyncClient) -> None:
        profile = await client.post(
            f"/api/v1/actors/{actor_id}/profiles",
            json={"version": "3.0.0", "provider_order": ["cache-aware-provider"]},
            headers=TENANT_HEADER,
        )
        assert profile.status_code == 200

        event = await client.post(
            f"/api/v1/actors/{actor_id}/profiles/learning-events",
            json={
                "event_type": "low_confidence",
                "trigger_reason": "quality_score_below_threshold",
                "profile_version": "3.0.0",
                "payload_fingerprint": "fp-value-1",
            },
            headers=TENANT_HEADER,
        )
        assert event.status_code == 200

        run = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            json={"input": {"target": "https://example.com/value"}},
            headers=TENANT_HEADER,
        )
        assert run.status_code == 200

        candidate = await client.post(
            f"/api/v1/actors/{actor_id}/fixtures/candidates",
            json={
                "fixture_id": "fixture-value-1",
                "trigger_reasons": ["low_confidence"],
                "state": "succeeded",
                "sanitized_input": {"target": "https://example.com/value"},
            },
            headers=TENANT_HEADER,
        )
        assert candidate.status_code == 200
        approved = await client.post(
            f"/api/v1/actors/{actor_id}/fixtures/candidates/fixture-value-1/approve",
            json={"reviewed_by": "codex-test"},
            headers=TENANT_HEADER,
        )
        assert approved.status_code == 200
        materialized = await client.post(
            f"/api/v1/actors/{actor_id}/fixtures/candidates/fixture-value-1/materialize",
            json={"reviewed_by": "codex-test"},
            headers=TENANT_HEADER,
        )
        assert materialized.status_code == 200

        metrics = await client.get(f"/api/v1/actors/{actor_id}/value-metrics", headers=TENANT_HEADER)
        assert metrics.status_code == 200
        data = metrics.json()["data"]
        assert data["total_runs"] == 1
        assert data["successful_runs"] == 1
        assert data["cache_hits"] == 1
        assert data["cache_hit_rate"] == 1.0
        assert data["average_quality_score"] == 0.88
        assert data["learning_event_count"] == 1
        assert data["active_profile_version"] == "3.0.0"
        assert data["fixture_status_counts"]["materialized"] == 1
        assert data["value_signals"]["accepted_fixtures"] == 1

    asyncio.run(_with_client(scenario))
