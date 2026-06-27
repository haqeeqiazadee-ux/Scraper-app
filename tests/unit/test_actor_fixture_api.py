from __future__ import annotations

import asyncio

from httpx import AsyncClient

from packages.core.actor_catalog.registry import actor_catalog
from tests.unit.test_actor_runs_api import TENANT_HEADER, _with_client


def _first_native_actor() -> str:
    actors, total = actor_catalog.search(strategy="native_pipeline", limit=1)
    assert total > 0
    return actors[0].actor_id


def test_fixture_candidate_review_and_materialization_api_is_tenant_scoped() -> None:
    actor_id = _first_native_actor()

    async def scenario(client: AsyncClient) -> None:
        created = await client.post(
            f"/api/v1/actors/{actor_id}/fixtures/candidates",
            json={
                "trigger_reasons": ["missing_required_fields"],
                "source_trace_id": "trace-api-fixture",
                "state": "succeeded",
                "provider": "http_worker",
                "sanitized_input": {"target": "https://example.com", "token": "[redacted]"},
                "redacted_payload_keys": ["token"],
                "expected_assertions": ["required_fields_should_be_present"],
                "tags": ["actor-regression"],
            },
            headers=TENANT_HEADER,
        )
        assert created.status_code == 200
        data = created.json()["data"]
        fixture_id = data["fixture_id"]
        assert data["status"] == "pending_review"
        assert data["sanitized_input"]["token"] == "[redacted]"

        other_tenant = await client.get(
            f"/api/v1/actors/{actor_id}/fixtures/candidates",
            headers={"X-Tenant-ID": "other-tenant"},
        )
        assert other_tenant.status_code == 200
        assert other_tenant.json()["data"]["total"] == 0

        blocked_materialize = await client.post(
            f"/api/v1/actors/{actor_id}/fixtures/candidates/{fixture_id}/materialize",
            json={"reviewed_by": "codex-test"},
            headers=TENANT_HEADER,
        )
        assert blocked_materialize.status_code == 409

        approved = await client.post(
            f"/api/v1/actors/{actor_id}/fixtures/candidates/{fixture_id}/approve",
            json={"reviewed_by": "codex-test", "notes": "safe to replay"},
            headers=TENANT_HEADER,
        )
        assert approved.status_code == 200
        assert approved.json()["data"]["status"] == "approved"

        materialized = await client.post(
            f"/api/v1/actors/{actor_id}/fixtures/candidates/{fixture_id}/materialize",
            json={"reviewed_by": "codex-test"},
            headers=TENANT_HEADER,
        )
        assert materialized.status_code == 200
        fixture = materialized.json()["data"]
        assert fixture["fixture_id"] == fixture_id
        assert fixture["input"]["token"] == "[redacted]"
        assert fixture["provenance"]["reviewed_by"] == "codex-test"

        listed = await client.get(
            f"/api/v1/actors/{actor_id}/fixtures/candidates?status=materialized",
            headers=TENANT_HEADER,
        )
        assert listed.status_code == 200
        assert listed.json()["data"]["total"] == 1
        assert listed.json()["data"]["items"][0]["materialized_fixture"]["fixture_id"] == fixture_id


        rejected = await client.post(
            f"/api/v1/actors/{actor_id}/fixtures/candidates",
            json={
                "fixture_id": "fixture-rejected",
                "trigger_reasons": ["low_confidence"],
                "state": "succeeded",
                "sanitized_input": {"target": "https://example.com/low"},
            },
            headers=TENANT_HEADER,
        )
        assert rejected.status_code == 200
        reject_response = await client.post(
            f"/api/v1/actors/{actor_id}/fixtures/candidates/fixture-rejected/reject",
            json={"reviewed_by": "codex-test", "notes": "not representative"},
            headers=TENANT_HEADER,
        )
        assert reject_response.status_code == 200
        assert reject_response.json()["data"]["status"] == "rejected"

    asyncio.run(_with_client(scenario))
