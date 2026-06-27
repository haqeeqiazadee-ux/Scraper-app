from __future__ import annotations

import asyncio
import json
from typing import Any


def _content_json(contents: list[Any]) -> dict[str, Any]:
    assert contents
    return json.loads(contents[0].text)


def _first_actor_with_strategy(strategy: str) -> str:
    from packages.core.actor_catalog.registry import actor_catalog

    actors, total = actor_catalog.search(strategy=strategy, limit=1)
    assert total > 0
    return actors[0].actor_id


def test_mcp_tool_list_exposes_actor_catalog_route_and_run_tools() -> None:
    from packages.core import mcp_server

    tools = asyncio.run(mcp_server.list_tools())
    names = {tool.name for tool in tools}

    assert {"scrape", "crawl", "search", "extract", "route"} <= names
    assert {"actor_search", "actor_get", "actor_route", "actor_run"} <= names


def test_mcp_actor_search_uses_local_catalog_without_apify_execution(monkeypatch) -> None:
    from packages.core import mcp_server

    monkeypatch.delenv("SCRAPER_API_KEY_REQUIRED", raising=False)

    data = _content_json(
        asyncio.run(
            mcp_server.call_tool(
                "actor_search",
                {
                    "q": "google maps",
                    "limit": 3,
                },
            )
        )
    )

    assert data["success"] is True
    assert data["execution_source"] == "local_actor_catalog"
    assert data["total"] > 0
    assert 1 <= len(data["data"]) <= 3
    assert all(item["execution_source"] == "local_actor_catalog" for item in data["data"])


def test_mcp_actor_route_returns_api_surface_and_provider_ladder(monkeypatch) -> None:
    from packages.core import mcp_server

    monkeypatch.delenv("SCRAPER_API_KEY_REQUIRED", raising=False)
    actor_id = _first_actor_with_strategy("native_pipeline")

    data = _content_json(asyncio.run(mcp_server.call_tool("actor_route", {"actor_id": actor_id})))

    assert data["success"] is True
    assert data["actor_id"] == actor_id
    assert data["base_family"]
    assert data["provider_ladder"]
    assert data["provider_ladder"][0]["tier"] != "unsupported"
    assert data["api_surface"]["run_endpoint"] == f"/api/v1/actors/{actor_id}/runs"


def test_mcp_actor_run_executes_yt_dlp_routes_without_apify_fallback(monkeypatch) -> None:
    from packages.core import mcp_server
    from packages.core.actor_runtime import ActorRuntimeResult, ActorRunState

    monkeypatch.delenv("SCRAPER_API_KEY_REQUIRED", raising=False)
    actor_id = _first_actor_with_strategy("yt_dlp")

    class FakeRunner:
        async def run(self, payload: dict[str, Any]) -> ActorRuntimeResult:
            return ActorRuntimeResult(
                actor_id=actor_id,
                state=ActorRunState.SUCCEEDED,
                provider="yt_dlp_metadata",
                output={
                    "extracted_data": [{"video_id": "video-1", "title": "Fixture Video"}],
                    "item_count": 1,
                    "extraction_method": "yt_dlp_metadata",
                },
            )

    monkeypatch.setattr(mcp_server, "_create_actor_runtime_runner", lambda *args, **kwargs: FakeRunner())

    data = _content_json(
        asyncio.run(
            mcp_server.call_tool(
                "actor_run",
                {
                    "actor_id": actor_id,
                    "input": {"target": "https://www.youtube.com/watch?v=video-1"},
                },
            )
        )
    )

    assert data["success"] is True
    assert data["state"] == "succeeded"
    assert data["provider"] == "yt_dlp_metadata"
    assert data["execution_source"] == "native_actor_runtime"
    assert data["provider_ladder"][0]["tier"] == "provider_sdk"
    assert "apify" not in json.dumps(data["provider_ladder"]).lower()


def test_mcp_actor_run_passes_payload_to_native_runtime(monkeypatch) -> None:
    from packages.core import mcp_server
    from packages.core.actor_runtime import ActorRuntimeResult, ActorRunState

    monkeypatch.delenv("SCRAPER_API_KEY_REQUIRED", raising=False)
    actor_id = _first_actor_with_strategy("native_pipeline")
    observed: dict[str, Any] = {}

    class FakeRunner:
        async def run(self, payload: dict[str, Any]) -> ActorRuntimeResult:
            observed["payload"] = payload
            return ActorRuntimeResult(
                actor_id=actor_id,
                state=ActorRunState.SUCCEEDED,
                provider="unit-test-native-runtime",
                output={"extracted_data": [{"name": "MCP Item"}], "item_count": 1},
                metadata={"knowledge": {"decision": "fresh_run"}},
            )

    def fake_create_runner(spec: Any, entry: Any, *, task_id: str, tenant_id: str) -> FakeRunner:
        observed["task_id"] = task_id
        observed["tenant_id"] = tenant_id
        observed["base_family"] = spec.base_family
        return FakeRunner()

    monkeypatch.setattr(mcp_server, "_create_actor_runtime_runner", fake_create_runner)

    data = _content_json(
        asyncio.run(
            mcp_server.call_tool(
                "actor_run",
                {
                    "actor_id": actor_id,
                    "input": {"target": "https://example.com/products"},
                    "options": {
                        "tenant_id": "mcp-unit-tenant",
                        "task_id": "mcp-task-1",
                        "knowledge_context": {"decision": "fresh_run"},
                    },
                },
            )
        )
    )

    assert data["success"] is True
    assert data["state"] == "succeeded"
    assert data["provider"] == "unit-test-native-runtime"
    assert data["task_id"] == "mcp-task-1"
    assert data["tenant_id"] == "mcp-unit-tenant"
    assert data["output"]["item_count"] == 1
    assert observed["payload"]["knowledge_context"] == {"decision": "fresh_run"}
    assert observed["base_family"]
