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


def test_actor_profile_api_persists_learning_proposals_and_promotions() -> None:
    actor_id = _first_native_actor()

    async def scenario(client: AsyncClient) -> None:
        active_default = await client.get(f"/api/v1/actors/{actor_id}/profiles/active", headers=TENANT_HEADER)
        assert active_default.status_code == 200
        assert active_default.json()["data"]["persisted"] is False

        saved = await client.post(
            f"/api/v1/actors/{actor_id}/profiles",
            json={
                "version": "1.2.0",
                "provider_order": ["http_worker"],
                "replay_fixture_ids": ["fixture-1"],
                "metrics": {"success_rate": 0.9},
            },
            headers=TENANT_HEADER,
        )
        assert saved.status_code == 200
        assert saved.json()["data"]["version"] == "1.2.0"
        assert saved.json()["data"]["persisted"] is True

        event = await client.post(
            f"/api/v1/actors/{actor_id}/profiles/learning-events",
            json={
                "event_type": "missing_fields",
                "trigger_reason": "missing_price",
                "profile_version": "1.2.0",
                "payload_fingerprint": "fp-safe-1",
                "redacted_payload_keys": ["token"],
                "metrics": {"missing_required_fields": ["price"]},
                "evidence": ["unit-test"],
            },
            headers=TENANT_HEADER,
        )
        assert event.status_code == 200
        assert event.json()["data"]["redacted_payload_keys"] == ["token"]

        event_list = await client.get(
            f"/api/v1/actors/{actor_id}/profiles/learning-events",
            headers=TENANT_HEADER,
        )
        assert event_list.status_code == 200
        assert event_list.json()["data"]["total"] == 1

        proposal = await client.post(
            f"/api/v1/actors/{actor_id}/profiles/proposals",
            json={
                "current_profile_version": "1.2.0",
                "proposed_profile_version": "1.2.1",
                "patch": {"schema_aliases": {"price": ["amount"]}},
                "rationale": "map price alias",
                "required_replay_fixture_ids": ["fixture-1"],
            },
            headers=TENANT_HEADER,
        )
        assert proposal.status_code == 200
        proposal_id = proposal.json()["data"]["proposal_id"]

        blocked = await client.post(
            f"/api/v1/actors/{actor_id}/profiles/proposals/{proposal_id}/promote",
            json={"promoted_by": "codex-test"},
            headers=TENANT_HEADER,
        )
        assert blocked.status_code == 409

        validation = await client.post(
            f"/api/v1/actors/{actor_id}/profiles/proposals/{proposal_id}/replay-validations",
            json={
                "passed": True,
                "fixtures_run": ["fixture-1"],
                "score_before": 0.8,
                "score_after": 0.95,
            },
            headers=TENANT_HEADER,
        )
        assert validation.status_code == 200
        assert validation.json()["data"]["passed"] is True

        promoted = await client.post(
            f"/api/v1/actors/{actor_id}/profiles/proposals/{proposal_id}/promote",
            json={"promoted_by": "codex-test"},
            headers=TENANT_HEADER,
        )
        assert promoted.status_code == 200
        assert promoted.json()["data"]["version"] == "1.2.1"
        assert promoted.json()["data"]["schema_aliases"]["price"] == ["amount"]

        history = await client.get(f"/api/v1/actors/{actor_id}/profiles/history", headers=TENANT_HEADER)
        assert history.status_code == 200
        assert history.json()["data"]["total"] == 2

        other_tenant = await client.get(
            f"/api/v1/actors/{actor_id}/profiles/history",
            headers={"X-Tenant-ID": "other-tenant"},
        )
        assert other_tenant.status_code == 200
        assert other_tenant.json()["data"]["total"] == 0

    asyncio.run(_with_client(scenario))


def test_actor_run_uses_persisted_active_strategy_profile(monkeypatch) -> None:  # noqa: ANN001
    actor_id = _first_native_actor()

    from packages.core.actor_runtime import ActorRuntimeResult, ActorRunState, BaseActorRunner
    from services.control_plane.routers import actors as actors_router_module

    class ProfileAwareRunner(BaseActorRunner):
        async def run(self, payload: dict) -> Any:
            return ActorRuntimeResult(
                actor_id=self.spec.actor_id,
                state=ActorRunState.SUCCEEDED,
                provider="profile-aware-provider",
                output={
                    "extracted_data": [{"profile_version": self.strategy_profile.version}],
                    "item_count": 1,
                    "confidence": 0.9,
                    "extraction_method": "profile_aware",
                },
                metadata={"strategy_profile": self._strategy_profile_metadata()},
            )

    def fake_create_runner(spec: ActorSpec, entry: Any, *, task_id: str, tenant_id: str) -> ProfileAwareRunner:
        return ProfileAwareRunner(spec)

    monkeypatch.setattr(actors_router_module, "create_actor_runner", fake_create_runner)

    async def scenario(client: AsyncClient) -> None:
        saved = await client.post(
            f"/api/v1/actors/{actor_id}/profiles",
            json={"version": "2.0.0", "provider_order": ["profile-aware-provider"]},
            headers=TENANT_HEADER,
        )
        assert saved.status_code == 200

        run = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            json={"input": {"target": "https://example.com"}},
            headers=TENANT_HEADER,
        )
        assert run.status_code == 200
        data = run.json()["data"]
        assert data["runtime_metadata"]["strategy_profile"]["version"] == "2.0.0"
        assert data["output"]["extracted_data"][0]["profile_version"] == "2.0.0"

    asyncio.run(_with_client(scenario))
