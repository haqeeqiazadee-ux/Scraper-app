from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from typing import Any, Callable

from httpx import ASGITransport, AsyncClient

from packages.core.actor_catalog.registry import actor_catalog
from packages.core.actor_runtime import (
    ActorProofFailureClass,
    ActorProofLevel,
    ActorRuntimeResult,
    ActorRunState,
    choose_proof_level,
    classify_actor_proof_failure,
    generate_actor_test_input,
)
from packages.core.rate_limiter import InMemoryRateLimiter, RateLimitConfig
from services.control_plane.dependencies import init_database
from services.control_plane.middleware.rate_limit import set_rate_limiter


TENANT_HEADER = {"X-Tenant-ID": "actor-proof-test-tenant"}


async def _with_client(fn: Callable[[AsyncClient], Any]) -> Any:
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    os.environ.setdefault("SECRET_KEY", "test-secret")
    os.environ.setdefault("ENVIRONMENT", "test")

    db = init_database("sqlite+aiosqlite:///:memory:")
    await db.create_tables()
    set_rate_limiter(
        InMemoryRateLimiter(
            default_config=RateLimitConfig(
                requests_per_minute=10_000,
                requests_per_hour=100_000,
                burst_size=10_000,
            )
        )
    )

    from services.control_plane.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await fn(client)
    finally:
        await db.drop_tables()
        await db.close()


def _first_native_actor() -> str:
    actors, total = actor_catalog.search(strategy="native_pipeline", limit=1)
    assert total > 0
    return actors[0].actor_id


def test_actor_proof_helpers_are_strict_about_live_e2e() -> None:
    entry = SimpleNamespace(
        actor_id="actor-1",
        name="example-products",
        url="https://apify.com/example/products",
        categories=("ECOMMERCE",),
        route_strategy="native_pipeline",
    )

    generated = generate_actor_test_input(entry)
    assert "apify.com" not in generated["target"]
    assert generated["target"] == "https://example.com/products"

    job_generated = generate_actor_test_input(
        SimpleNamespace(
            actor_id="actor-jobs",
            name="jobs",
            categories=("JOBS",),
            route_strategy="job_board_schema",
        )
    )
    assert job_generated["target"].startswith("https://")

    generic_generated = generate_actor_test_input(
        SimpleNamespace(
            actor_id="actor-generic",
            name="generic",
            categories=(),
            route_strategy="native_pipeline",
        )
    )
    assert generic_generated["target"] == "https://example.com"
    assert generic_generated["workflow_hint"] == "generic"

    assert classify_actor_proof_failure(
        run_status="failed",
        error="missing API key",
        missing_env_names=(),
        item_count=0,
    ) == ActorProofFailureClass.MISSING_CREDENTIALS

    assert choose_proof_level(
        run_status="completed",
        has_result=True,
        item_count=1,
        export_json_passed=True,
        export_csv_passed=True,
        ui_route_passed=True,
        fixture_replay_passed=False,
    ) == ActorProofLevel.LIVE_E2E_PASSED

    assert choose_proof_level(
        run_status="completed",
        has_result=True,
        item_count=1,
        export_json_passed=True,
        export_csv_passed=True,
        ui_route_passed=False,
        fixture_replay_passed=True,
    ) == ActorProofLevel.FIXTURE_REPLAY_PASSED

    assert choose_proof_level(
        run_status="failed",
        has_result=False,
        item_count=0,
        export_json_passed=False,
        export_csv_passed=False,
        ui_route_passed=True,
        fixture_replay_passed=False,
    ) == ActorProofLevel.API_MAPPED

    assert choose_proof_level(
        run_status="completed",
        has_result=True,
        item_count=0,
        export_json_passed=True,
        export_csv_passed=True,
        ui_route_passed=False,
        fixture_replay_passed=False,
    ) == ActorProofLevel.API_MAPPED


def test_actor_proof_api_records_manual_ui_route_proof() -> None:
    actor_id = _first_native_actor()

    async def scenario(client: AsyncClient) -> None:
        summary = await client.get("/api/v1/actors/proof/summary", headers=TENANT_HEADER)
        assert summary.status_code == 200
        assert summary.json()["data"]["catalog_actor_count"] == actor_catalog.total
        assert summary.json()["data"]["proof_ledger_count"] == 0

        fallback = await client.get(f"/api/v1/actors/{actor_id}/proof", headers=TENANT_HEADER)
        assert fallback.status_code == 200
        fallback_data = fallback.json()["data"]
        assert fallback_data["proof_level"] == "api_mapped"
        assert fallback_data["persisted"] is False
        assert "apify.com" not in fallback_data["test_input"]["target"]

        recorded = await client.post(
            f"/api/v1/actors/{actor_id}/proof",
            headers=TENANT_HEADER,
            json={
                "proof_level": "ui_route_passed",
                "ui_route_passed": True,
                "provenance": ["unit-test-ui-route"],
            },
        )
        assert recorded.status_code == 200
        assert recorded.json()["data"]["proof_level"] == "ui_route_passed"
        assert recorded.json()["data"]["claim_boundary"] == "not_live_e2e_proven"

        summary_after = await client.get("/api/v1/actors/proof/summary", headers=TENANT_HEADER)
        data = summary_after.json()["data"]
        assert data["proof_ledger_count"] == 1
        assert data["ui_route_passed_count"] == 1
        assert data["full_catalog_live_e2e_proven"] is False

    asyncio.run(_with_client(scenario))


def test_actor_run_can_be_promoted_to_live_e2e_proof(monkeypatch) -> None:  # noqa: ANN001
    actor_id = _first_native_actor()

    from services.control_plane.routers import actors as actors_router_module

    class FakeRunner:
        async def run(self, payload: dict[str, Any]) -> ActorRuntimeResult:  # noqa: ARG002
            return ActorRuntimeResult(
                actor_id=actor_id,
                state=ActorRunState.SUCCEEDED,
                output={
                    "items": [{"name": "proof item", "url": "https://example.com/item"}],
                    "confidence": 0.93,
                    "duration_ms": 12,
                    "bytes_downloaded": 128,
                    "extraction_method": "unit_fake",
                },
                provider="unit_fake",
                metadata={"knowledge": {"decision": "run_fresh", "freshness_state": "fresh"}},
            )

    def fake_create_actor_runner(*args, **kwargs):  # noqa: ANN002, ANN003, ARG001
        return FakeRunner()

    monkeypatch.setattr(actors_router_module, "create_actor_runner", fake_create_actor_runner)

    async def scenario(client: AsyncClient) -> None:
        run_response = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            headers=TENANT_HEADER,
            json={"input": {"target": "https://example.com/products"}},
        )
        assert run_response.status_code == 200
        run_id = run_response.json()["data"]["run"]["id"]

        proof_response = await client.post(
            f"/api/v1/actors/{actor_id}/runs/{run_id}/proof",
            headers=TENANT_HEADER,
            json={"ui_route_passed": True, "provenance": ["unit-test-run-proof"]},
        )
        assert proof_response.status_code == 200
        proof = proof_response.json()["data"]
        assert proof["proof_level"] == "live_e2e_passed"
        assert proof["live_e2e_passed"] is True
        assert proof["export_json_passed"] is True
        assert proof["export_csv_passed"] is True
        assert proof["items_count"] == 1

    asyncio.run(_with_client(scenario))


def test_failed_actor_run_cannot_be_promoted_to_ui_route_proof(monkeypatch) -> None:  # noqa: ANN001
    actor_id = _first_native_actor()

    from services.control_plane.routers import actors as actors_router_module

    class FailingRunner:
        async def run(self, payload: dict[str, Any]) -> ActorRuntimeResult:  # noqa: ARG002
            return ActorRuntimeResult(
                actor_id=actor_id,
                state=ActorRunState.FAILED,
                error="synthetic proof failure",
                provider="unit_fake",
            )

    def fake_create_actor_runner(*args, **kwargs):  # noqa: ANN002, ANN003, ARG001
        return FailingRunner()

    monkeypatch.setattr(actors_router_module, "create_actor_runner", fake_create_actor_runner)

    async def scenario(client: AsyncClient) -> None:
        run_response = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            headers=TENANT_HEADER,
            json={"input": {"target": "https://example.com/products"}},
        )
        assert run_response.status_code == 200
        run_id = run_response.json()["data"]["run"]["id"]

        proof_response = await client.post(
            f"/api/v1/actors/{actor_id}/runs/{run_id}/proof",
            headers=TENANT_HEADER,
            json={"ui_route_passed": True, "provenance": ["unit-test-failed-run-proof"]},
        )
        assert proof_response.status_code == 200
        proof = proof_response.json()["data"]
        assert proof["proof_level"] == "api_mapped"
        assert proof["live_e2e_passed"] is False
        assert proof["ui_route_passed"] is False
        assert proof["failure_class"] == "implementation_bug"
        assert proof["claim_boundary"] == "not_live_e2e_proven"

        summary = await client.get("/api/v1/actors/proof/summary", headers=TENANT_HEADER)
        data = summary.json()["data"]
        assert data["ui_route_passed_count"] == 0
        assert data["live_e2e_passed_count"] == 0

    asyncio.run(_with_client(scenario))
