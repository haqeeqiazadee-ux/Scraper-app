"""
Integration tests for the full task lifecycle:
  create task -> execute -> get results -> verify status transitions.

Uses the FastAPI test client backed by an in-memory SQLite database.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.integration.conftest import TENANT_HEADER, TaskFactory, PolicyFactory


@pytest.mark.asyncio
class TestTaskLifecycle:
    """Full task lifecycle integration tests."""

    async def test_create_task_returns_201(self, client: AsyncClient):
        """Creating a task via POST /api/v1/tasks returns 201 with expected fields."""
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com/products", "priority": 8},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["priority"] == 8
        assert data["url"] == "https://example.com/products"
        assert "id" in data
        assert "created_at" in data

    async def test_execute_task_triggers_router(self, client: AsyncClient):
        """Executing a pending task routes it and updates status to queued."""
        # Create task
        task = await TaskFactory.create_via_api(client, url="https://example.com/page")
        task_id = task["id"]

        # Execute
        resp = await client.post(
            f"/api/v1/tasks/{task_id}/execute",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert "route" in data
        assert data["route"]["lane"] in ("http", "browser", "api", "hard_target")
        assert "reason" in data["route"]

    async def test_execute_updates_task_status(self, client: AsyncClient):
        """After execution, GET /tasks/{id} shows 'queued' status."""
        task = await TaskFactory.create_via_api(client)
        task_id = task["id"]

        await client.post(f"/api/v1/tasks/{task_id}/execute", headers=TENANT_HEADER)

        resp = await client.get(f"/api/v1/tasks/{task_id}", headers=TENANT_HEADER)
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"

    async def test_execute_non_pending_task_fails(self, client: AsyncClient):
        """Executing a task that is not pending returns 400."""
        task = await TaskFactory.create_via_api(client)
        task_id = task["id"]

        # Execute once (pending -> queued)
        await client.post(f"/api/v1/tasks/{task_id}/execute", headers=TENANT_HEADER)

        # Execute again (queued != pending -> 400)
        resp = await client.post(f"/api/v1/tasks/{task_id}/execute", headers=TENANT_HEADER)
        assert resp.status_code == 400
        assert "not pending" in resp.json()["detail"].lower()

    async def test_execute_nonexistent_task_returns_404(self, client: AsyncClient):
        """Executing a nonexistent task returns 404."""
        resp = await client.post(
            "/api/v1/tasks/nonexistent-id/execute",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 404

    async def test_task_status_transitions(self, client: AsyncClient):
        """Task status can be updated through lifecycle transitions."""
        task = await TaskFactory.create_via_api(client)
        task_id = task["id"]
        assert task["status"] == "pending"

        # pending -> running
        resp = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "running"},
            headers=TENANT_HEADER,
        )
        assert resp.json()["status"] == "running"

        # running -> completed
        resp = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "completed"},
            headers=TENANT_HEADER,
        )
        assert resp.json()["status"] == "completed"

    async def test_execute_with_policy_routes_correctly(self, client: AsyncClient):
        """Executing a task with a browser-preferred policy routes to browser lane."""
        # Create policy with browser preference
        policy = await PolicyFactory.create_via_api(
            client,
            name="Browser Policy",
            preferred_lane="browser",
        )
        policy_id = policy["id"]

        # Create task referencing the policy
        resp = await client.post(
            "/api/v1/tasks",
            json={
                "url": "https://example.com/dynamic-page",
                "policy_id": policy_id,
            },
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 201
        task_id = resp.json()["id"]

        # Execute
        resp = await client.post(
            f"/api/v1/tasks/{task_id}/execute",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        assert resp.json()["route"]["lane"] == "browser"

    async def test_dry_run_route_without_creating_task(self, client: AsyncClient):
        """POST /api/v1/route performs dry-run routing without creating a task."""
        resp = await client.post(
            "/api/v1/route",
            json={"url": "https://www.amazon.com/dp/B09V3KXJPB"},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["route"]["lane"] == "browser"
        assert "reason" in data["route"]
