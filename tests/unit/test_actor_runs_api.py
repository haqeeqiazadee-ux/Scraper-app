from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from typing import Any, Callable

import pytest
from httpx import ASGITransport, AsyncClient

from packages.core.actor_catalog.registry import actor_catalog
from packages.core.actor_runtime import ActorSpec
from services.control_plane.dependencies import init_database
from services.control_plane.middleware.rate_limit import set_rate_limiter
from packages.core.rate_limiter import InMemoryRateLimiter, RateLimitConfig


TENANT_HEADER = {"X-Tenant-ID": "actor-test-tenant"}


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


def _first_actor_with_strategy(strategy: str) -> str:
    actors, total = actor_catalog.search(strategy=strategy, limit=1)
    assert total > 0
    return actors[0].actor_id


def _first_native_local_maps_actor() -> str:
    from packages.core.actor_runtime.families import ActorBaseFamily, build_actor_spec

    actors, total = actor_catalog.search(query="google maps", strategy="native_pipeline", limit=100)
    assert total > 0
    for actor in actors:
        if build_actor_spec(actor).base_family == ActorBaseFamily.LOCAL_MAPS_SERP:
            return actor.actor_id
    raise AssertionError("No native local maps actor found in catalog sample")


def _first_actor_matching_strategy(strategy: str) -> str:
    actors, total = actor_catalog.search(strategy=strategy, limit=1)
    assert total > 0
    return actors[0].actor_id


def test_actor_run_blocks_non_native_strategy_without_redirecting() -> None:
    actor_id = _first_actor_with_strategy("yt_dlp")

    async def scenario(client: AsyncClient) -> None:
        response = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            json={"input": {"target": "https://example.com/products"}},
            headers=TENANT_HEADER,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["actor_id"] == actor_id
        assert data["state"] == "blocked_policy"
        assert data["task"]["status"] == "blocked"
        assert data["run"]["status"] == "blocked_policy"
        assert data["run"]["connector"] == "actor_runtime"
        assert "apify.com" not in data["run"]["connector"]

        detail = await client.get(
            f"/api/v1/actors/{actor_id}/runs/{data['run']['id']}",
            headers=TENANT_HEADER,
        )
        assert detail.status_code == 200
        assert detail.json()["data"]["state"] == "blocked_policy"

    asyncio.run(_with_client(scenario))


def test_actor_run_skips_missing_required_key_and_lists_persisted_run(monkeypatch: pytest.MonkeyPatch) -> None:
    actor_id = _first_actor_with_strategy("native_pipeline")

    from services.control_plane.routers import actors as actors_router_module

    def fake_build_actor_spec(entry: Any) -> ActorSpec:
        return ActorSpec(
            actor_id=entry.actor_id,
            slug=entry.name,
            title=entry.title,
            base_family=entry.route_strategy,
            required_env_names=["ACTOR_RUN_TEST_MISSING_KEY"],
        )

    monkeypatch.setattr(actors_router_module, "build_actor_spec", fake_build_actor_spec)

    async def scenario(client: AsyncClient) -> None:
        response = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            json={"input": {"target": "https://example.com/products"}},
            headers=TENANT_HEADER,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["actor_id"] == actor_id
        assert data["state"] == "skipped_missing_key"
        assert data["missing_env_names"] == ["ACTOR_RUN_TEST_MISSING_KEY"]
        assert data["task"]["status"] == "skipped"
        assert data["run"]["status"] == "skipped_missing_key"

        listing = await client.get(
            f"/api/v1/actors/{actor_id}/runs",
            headers=TENANT_HEADER,
        )
        assert listing.status_code == 200
        listed = listing.json()["data"]
        assert listed["total"] == 1
        assert listed["items"][0]["run"]["id"] == data["run"]["id"]

    asyncio.run(_with_client(scenario))


def test_actor_run_unknown_actor_returns_404() -> None:
    async def scenario(client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/actors/not-a-real-actor/runs",
            json={"input": {"target": "https://example.com/products"}},
            headers=TENANT_HEADER,
        )
        assert response.status_code == 404

    asyncio.run(_with_client(scenario))


def test_actor_run_detail_and_list_are_tenant_isolated() -> None:
    actor_id = _first_actor_with_strategy("yt_dlp")

    async def scenario(client: AsyncClient) -> None:
        created = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            json={"input": {"target": "https://example.com/products"}},
            headers={"X-Tenant-ID": "tenant-a"},
        )
        assert created.status_code == 200
        run_id = created.json()["data"]["run"]["id"]

        detail = await client.get(
            f"/api/v1/actors/{actor_id}/runs/{run_id}",
            headers={"X-Tenant-ID": "tenant-b"},
        )
        assert detail.status_code == 404

        listing = await client.get(
            f"/api/v1/actors/{actor_id}/runs",
            headers={"X-Tenant-ID": "tenant-b"},
        )
        assert listing.status_code == 200
        assert listing.json()["data"]["total"] == 0

    asyncio.run(_with_client(scenario))


def test_actor_run_success_persists_result(monkeypatch: pytest.MonkeyPatch) -> None:
    actor_id = _first_actor_with_strategy("native_pipeline")

    from packages.core.actor_runtime import ActorRuntimeResult, ActorRunState, BaseActorRunner
    from services.control_plane.routers import actors as actors_router_module

    class SuccessfulRunner(BaseActorRunner):
        async def run(self, payload: dict) -> Any:
            return ActorRuntimeResult(
                actor_id=self.spec.actor_id,
                state=ActorRunState.SUCCEEDED,
                provider="test-provider",
                output={
                    "extracted_data": [{"name": "Item A", "price": "$10"}],
                    "item_count": 1,
                    "confidence": 0.91,
                    "status_code": 200,
                    "extraction_method": "unit_test_native_runner",
                    "duration_ms": 12,
                    "bytes_downloaded": 1234,
                },
            )

    def fake_create_runner(spec: ActorSpec, entry: Any, *, task_id: str, tenant_id: str) -> SuccessfulRunner:
        return SuccessfulRunner(spec)

    monkeypatch.setattr(actors_router_module, "create_actor_runner", fake_create_runner)

    async def scenario(client: AsyncClient) -> None:
        response = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            json={"input": {"target": "https://example.com/products"}},
            headers=TENANT_HEADER,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["state"] == "succeeded"
        assert data["provider"] == "test-provider"
        assert data["task"]["status"] == "completed"
        assert data["run"]["status"] == "completed"
        assert data["run"]["status_code"] == 200
        assert data["result"]["item_count"] == 1
        assert data["result"]["extraction_method"] == "unit_test_native_runner"

        detail = await client.get(
            f"/api/v1/actors/{actor_id}/runs/{data['run']['id']}",
            headers=TENANT_HEADER,
        )
        assert detail.status_code == 200
        assert detail.json()["data"]["result"]["confidence"] == 0.91

    asyncio.run(_with_client(scenario))


def test_actor_run_list_is_newest_first_and_paginated() -> None:
    actor_id = _first_actor_with_strategy("yt_dlp")

    async def scenario(client: AsyncClient) -> None:
        run_ids: list[str] = []
        for i in range(3):
            created = await client.post(
                f"/api/v1/actors/{actor_id}/runs",
                json={"input": {"target": f"https://example.com/products/{i}"}},
                headers=TENANT_HEADER,
            )
            assert created.status_code == 200
            run_ids.append(created.json()["data"]["run"]["id"])

        first_page = await client.get(
            f"/api/v1/actors/{actor_id}/runs?limit=2&offset=0",
            headers=TENANT_HEADER,
        )
        assert first_page.status_code == 200
        first_data = first_page.json()["data"]
        assert first_data["total"] == 3
        assert [item["run"]["id"] for item in first_data["items"]] == [run_ids[2], run_ids[1]]

        second_page = await client.get(
            f"/api/v1/actors/{actor_id}/runs?limit=2&offset=2",
            headers=TENANT_HEADER,
        )
        assert second_page.status_code == 200
        assert [item["run"]["id"] for item in second_page.json()["data"]["items"]] == [run_ids[0]]

    asyncio.run(_with_client(scenario))


def test_actor_run_local_maps_persists_browser_fallback_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    actor_id = _first_native_local_maps_actor()

    from packages.core.actor_runtime.families import LocalMapsSerpRunner
    from services.control_plane.routers import actors as actors_router_module

    class FakeMapsConnector:
        async def search_businesses(
            self,
            query: str,
            max_results: int = 20,
            location: str | None = None,
            language: str = "en",
        ) -> list[dict]:
            assert query == "coffee shops in Austin"
            return [{"name": "Coffee A", "source": "maps_browser_fallback"}]

        async def close(self) -> None:
            pass

    def fake_create_runner(spec: ActorSpec, entry: Any, *, task_id: str, tenant_id: str) -> LocalMapsSerpRunner:
        return LocalMapsSerpRunner(
            spec,
            task_id=task_id,
            tenant_id=tenant_id,
            maps_factory=FakeMapsConnector,
        )

    monkeypatch.setattr(actors_router_module, "create_actor_runner", fake_create_runner)

    async def scenario(client: AsyncClient) -> None:
        response = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            json={"input": {"query": "coffee shops in Austin", "max_results": 1}},
            headers=TENANT_HEADER,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["state"] == "succeeded"
        assert data["provider"] == "maps_browser_fallback"
        assert data["result"]["item_count"] == 1
        assert data["output"]["extracted_data"][0]["source"] == "maps_browser_fallback"

    asyncio.run(_with_client(scenario))


def test_actor_run_job_board_schema_strategy_is_native_runnable(monkeypatch: pytest.MonkeyPatch) -> None:
    actor_id = _first_actor_matching_strategy("job_board_schema")

    from packages.core.actor_runtime import ActorRuntimeResult, ActorRunState, BaseActorRunner
    from services.control_plane.routers import actors as actors_router_module

    class SuccessfulRunner(BaseActorRunner):
        async def run(self, payload: dict) -> Any:
            return ActorRuntimeResult(
                actor_id=self.spec.actor_id,
                state=ActorRunState.SUCCEEDED,
                provider="http_worker_schema_match",
                output={
                    "extracted_data": [
                        {
                            "url": "https://jobs.example.com/1",
                            "title": "Data Engineer",
                            "company_name": "Acme Inc",
                            "description": "Build data pipelines.",
                            "source": "Example Jobs",
                        }
                    ],
                    "item_count": 1,
                    "confidence": 0.9,
                    "status_code": 200,
                    "extraction_method": "job_board_schema",
                    "duration_ms": 5,
                    "bytes_downloaded": 100,
                },
            )

    def fake_create_runner(spec: ActorSpec, entry: Any, *, task_id: str, tenant_id: str) -> SuccessfulRunner:
        return SuccessfulRunner(spec)

    monkeypatch.setattr(actors_router_module, "create_actor_runner", fake_create_runner)

    async def scenario(client: AsyncClient) -> None:
        response = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            json={"input": {"target": "https://jobs.example.com"}},
            headers=TENANT_HEADER,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["state"] == "succeeded"
        assert data["provider"] == "http_worker_schema_match"
        assert data["task"]["status"] == "completed"
        assert data["run"]["status"] == "completed"
        assert data["result"]["item_count"] == 1

    asyncio.run(_with_client(scenario))


def test_actor_run_real_estate_schema_strategy_is_native_runnable(monkeypatch: pytest.MonkeyPatch) -> None:
    actor_id = _first_actor_matching_strategy("real_estate_schema")

    from packages.core.actor_runtime import ActorRuntimeResult, ActorRunState, BaseActorRunner
    from services.control_plane.routers import actors as actors_router_module

    class SuccessfulRunner(BaseActorRunner):
        async def run(self, payload: dict) -> Any:
            return ActorRuntimeResult(
                actor_id=self.spec.actor_id,
                state=ActorRunState.SUCCEEDED,
                provider="http_worker_schema_match",
                output={
                    "extracted_data": [
                        {
                            "url": "https://homes.example.com/1",
                            "title": "Beautiful Family Home",
                            "description": "A wonderful home.",
                            "source": "Example Homes",
                            "price": 450000,
                        }
                    ],
                    "item_count": 1,
                    "confidence": 0.9,
                    "status_code": 200,
                    "extraction_method": "real_estate_schema",
                    "duration_ms": 5,
                    "bytes_downloaded": 100,
                },
            )

    def fake_create_runner(spec: ActorSpec, entry: Any, *, task_id: str, tenant_id: str) -> SuccessfulRunner:
        return SuccessfulRunner(spec)

    monkeypatch.setattr(actors_router_module, "create_actor_runner", fake_create_runner)

    async def scenario(client: AsyncClient) -> None:
        response = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            json={"input": {"target": "https://homes.example.com/1"}},
            headers=TENANT_HEADER,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["state"] == "succeeded"
        assert data["provider"] == "http_worker_schema_match"
        assert data["task"]["status"] == "completed"
        assert data["run"]["status"] == "completed"
        assert data["result"]["item_count"] == 1

    asyncio.run(_with_client(scenario))


def test_actor_run_direct_phase5_family_strategy_is_native_runnable(monkeypatch: pytest.MonkeyPatch) -> None:
    actor_id = "direct-lead-family-actor"

    from packages.core.actor_runtime import ActorRuntimeResult, ActorRunState, BaseActorRunner
    from services.control_plane.routers import actors as actors_router_module

    entry = SimpleNamespace(
        actor_id=actor_id,
        name="direct-lead-family-actor",
        title="Direct Lead Family Actor",
        description="Extract business contact emails and phones.",
        categories=("LEAD_GENERATION",),
        route_strategy="lead_generation_generic",
        runnable_status="runnable",
    )

    class SuccessfulRunner(BaseActorRunner):
        async def run(self, payload: dict) -> Any:
            return ActorRuntimeResult(
                actor_id=self.spec.actor_id,
                state=ActorRunState.SUCCEEDED,
                provider="http_worker_contacts",
                output={
                    "extracted_data": [{"name": "Acme", "email": "sales@example.com"}],
                    "item_count": 1,
                    "confidence": 0.9,
                    "status_code": 200,
                    "extraction_method": "lead_generation_generic",
                    "duration_ms": 5,
                    "bytes_downloaded": 100,
                },
            )

    def fake_get(requested_actor_id: str) -> Any:
        return entry if requested_actor_id == actor_id else None

    def fake_create_runner(spec: ActorSpec, catalog_entry: Any, *, task_id: str, tenant_id: str) -> SuccessfulRunner:
        return SuccessfulRunner(spec)

    monkeypatch.setattr(actors_router_module.actor_catalog, "get", fake_get)
    monkeypatch.setattr(actors_router_module, "create_actor_runner", fake_create_runner)

    async def scenario(client: AsyncClient) -> None:
        response = await client.post(
            f"/api/v1/actors/{actor_id}/runs",
            json={"input": {"target": "https://example.com/contact"}},
            headers=TENANT_HEADER,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["state"] == "succeeded"
        assert data["provider"] == "http_worker_contacts"
        assert data["task"]["status"] == "completed"

    asyncio.run(_with_client(scenario))
