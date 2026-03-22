"""
End-to-end API tests using the full FastAPI application.

Tests full CRUD cycles for tasks, policies, execution + results flow,
and export endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.e2e.conftest import TENANT_HEADER, E2E_TENANT


@pytest.mark.asyncio
class TestTaskCRUDE2E:
    """Full CRUD cycle for tasks — end-to-end."""

    async def test_full_task_crud_cycle(self, app_client: AsyncClient):
        """Create -> Read -> Update -> Cancel a task in one flow."""
        headers = TENANT_HEADER

        # CREATE
        resp = await app_client.post(
            "/api/v1/tasks",
            json={"url": "https://shop.example.com/products", "priority": 7},
            headers=headers,
        )
        assert resp.status_code == 201
        task_id = resp.json()["id"]

        # READ
        resp = await app_client.get(f"/api/v1/tasks/{task_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["priority"] == 7
        assert data["status"] == "pending"

        # UPDATE
        resp = await app_client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"priority": 10},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["priority"] == 10

        # CANCEL
        resp = await app_client.post(f"/api/v1/tasks/{task_id}/cancel", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    async def test_list_tasks_with_pagination(self, app_client: AsyncClient):
        """Create multiple tasks and verify pagination works."""
        headers = TENANT_HEADER

        # Create 5 tasks
        for i in range(5):
            await app_client.post(
                "/api/v1/tasks",
                json={"url": f"https://example.com/page/{i}"},
                headers=headers,
            )

        # List with limit
        resp = await app_client.get("/api/v1/tasks?limit=3&offset=0", headers=headers)
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["limit"] == 3
        assert data["offset"] == 0

        # Page 2
        resp = await app_client.get("/api/v1/tasks?limit=3&offset=3", headers=headers)
        data = resp.json()
        assert len(data["items"]) == 2

    async def test_task_not_found_returns_404(self, app_client: AsyncClient):
        """Getting a nonexistent task returns 404."""
        resp = await app_client.get(
            "/api/v1/tasks/does-not-exist",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestPolicyCRUDE2E:
    """Full CRUD cycle for policies — end-to-end."""

    async def test_full_policy_crud_cycle(self, app_client: AsyncClient):
        """Create -> Read -> Update -> Delete a policy."""
        headers = TENANT_HEADER

        # CREATE
        resp = await app_client.post(
            "/api/v1/policies",
            json={
                "name": "E-Commerce Scraping",
                "target_domains": ["shop.com", "store.com"],
                "preferred_lane": "http",
                "timeout_ms": 15000,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        policy_id = resp.json()["id"]

        # READ
        resp = await app_client.get(f"/api/v1/policies/{policy_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "E-Commerce Scraping"
        assert "shop.com" in data["target_domains"]
        assert data["timeout_ms"] == 15000

        # UPDATE
        resp = await app_client.patch(
            f"/api/v1/policies/{policy_id}",
            json={"name": "Updated Policy", "timeout_ms": 60000},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Policy"
        assert resp.json()["timeout_ms"] == 60000

        # DELETE
        resp = await app_client.delete(f"/api/v1/policies/{policy_id}", headers=headers)
        assert resp.status_code == 204

        # Confirm deleted
        resp = await app_client.get(f"/api/v1/policies/{policy_id}", headers=headers)
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestExecutionE2E:
    """End-to-end execution and routing tests."""

    async def test_execute_and_check_status(self, app_client: AsyncClient):
        """Create task -> execute -> verify status changed to queued."""
        headers = TENANT_HEADER

        # Create
        resp = await app_client.post(
            "/api/v1/tasks",
            json={"url": "https://news.example.com/articles"},
            headers=headers,
        )
        task_id = resp.json()["id"]

        # Execute
        resp = await app_client.post(f"/api/v1/tasks/{task_id}/execute", headers=headers)
        assert resp.status_code == 200
        exec_data = resp.json()
        assert exec_data["status"] == "queued"
        assert exec_data["route"]["lane"] == "http"  # Default for unknown domain

        # Verify task status persisted
        resp = await app_client.get(f"/api/v1/tasks/{task_id}", headers=headers)
        assert resp.json()["status"] == "queued"

    async def test_dry_run_routing(self, app_client: AsyncClient):
        """Dry-run route returns lane without modifying any task."""
        resp = await app_client.post(
            "/api/v1/route",
            json={"url": "https://mystore.myshopify.com/products"},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["route"]["lane"] == "api"  # Shopify has known API

    async def test_execute_with_policy_overrides_lane(self, app_client: AsyncClient):
        """Execute with a policy that specifies hard_target lane."""
        headers = TENANT_HEADER

        # Create policy
        resp = await app_client.post(
            "/api/v1/policies",
            json={"name": "Hard Target", "preferred_lane": "hard_target"},
            headers=headers,
        )
        policy_id = resp.json()["id"]

        # Create task with policy
        resp = await app_client.post(
            "/api/v1/tasks",
            json={"url": "https://protected.example.com", "policy_id": policy_id},
            headers=headers,
        )
        task_id = resp.json()["id"]

        # Execute
        resp = await app_client.post(f"/api/v1/tasks/{task_id}/execute", headers=headers)
        assert resp.json()["route"]["lane"] == "hard_target"


@pytest.mark.asyncio
class TestTenantIsolationE2E:
    """Verify tenant isolation across all resource types."""

    async def test_tasks_isolated_between_tenants(self, app_client: AsyncClient):
        """Tasks created by tenant-A are invisible to tenant-B."""
        # Create as tenant-A
        resp = await app_client.post(
            "/api/v1/tasks",
            json={"url": "https://secret.example.com"},
            headers={"X-Tenant-ID": "tenant-A"},
        )
        task_id = resp.json()["id"]

        # Try to read as tenant-B
        resp = await app_client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"X-Tenant-ID": "tenant-B"},
        )
        assert resp.status_code == 404

    async def test_policies_isolated_between_tenants(self, app_client: AsyncClient):
        """Policies created by one tenant are invisible to another."""
        resp = await app_client.post(
            "/api/v1/policies",
            json={"name": "Private Policy"},
            headers={"X-Tenant-ID": "tenant-X"},
        )
        policy_id = resp.json()["id"]

        resp = await app_client.get(
            f"/api/v1/policies/{policy_id}",
            headers={"X-Tenant-ID": "tenant-Y"},
        )
        assert resp.status_code == 404
