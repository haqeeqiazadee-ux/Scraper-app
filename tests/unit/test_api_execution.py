"""Unit tests for Execution routing API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from services.control_plane.dependencies import init_database


@pytest.fixture
async def client():
    """Create a test client with in-memory database."""
    db = init_database("sqlite+aiosqlite:///:memory:")
    await db.create_tables()

    from services.control_plane.app import create_app
    app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await db.drop_tables()
    await db.close()


TENANT_HEADER = {"X-Tenant-ID": "test-tenant"}


class TestExecuteTask:
    """Tests for POST /api/v1/tasks/{task_id}/execute."""

    @pytest.mark.asyncio
    async def test_execute_pending_task(self, client):
        """Executing a pending task returns a route decision and sets status to queued."""
        # Create a task
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com/products"},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 201
        task_id = resp.json()["id"]

        # Execute it
        resp = await client.post(
            f"/api/v1/tasks/{task_id}/execute",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert data["status"] == "queued"
        assert "route" in data
        route = data["route"]
        assert "lane" in route
        assert "reason" in route
        assert "fallback_lanes" in route
        assert "confidence" in route
        assert isinstance(route["fallback_lanes"], list)
        assert isinstance(route["confidence"], float)

    @pytest.mark.asyncio
    async def test_execute_task_default_lane_is_http(self, client):
        """A generic URL with no policy should default to HTTP lane."""
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com/page"},
            headers=TENANT_HEADER,
        )
        task_id = resp.json()["id"]

        resp = await client.post(
            f"/api/v1/tasks/{task_id}/execute",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        assert resp.json()["route"]["lane"] == "http"

    @pytest.mark.asyncio
    async def test_execute_task_browser_domain(self, client):
        """A known browser-required domain should route to browser lane."""
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://www.amazon.com/dp/B09V3KXJPB"},
            headers=TENANT_HEADER,
        )
        task_id = resp.json()["id"]

        resp = await client.post(
            f"/api/v1/tasks/{task_id}/execute",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        assert resp.json()["route"]["lane"] == "browser"

    @pytest.mark.asyncio
    async def test_execute_task_with_policy(self, client):
        """A task with a policy specifying a preferred lane should use that lane."""
        # Create a policy with browser preference
        resp = await client.post(
            "/api/v1/policies",
            json={"name": "Force Browser", "preferred_lane": "browser"},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 201
        policy_id = resp.json()["id"]

        # Create a task linked to the policy
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com/simple", "policy_id": policy_id},
            headers=TENANT_HEADER,
        )
        task_id = resp.json()["id"]

        # Execute it
        resp = await client.post(
            f"/api/v1/tasks/{task_id}/execute",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        assert resp.json()["route"]["lane"] == "browser"

    @pytest.mark.asyncio
    async def test_execute_task_updates_status_to_queued(self, client):
        """After execution routing, the task status should be updated to queued."""
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com"},
            headers=TENANT_HEADER,
        )
        task_id = resp.json()["id"]

        # Execute
        await client.post(
            f"/api/v1/tasks/{task_id}/execute",
            headers=TENANT_HEADER,
        )

        # Verify status changed
        resp = await client.get(f"/api/v1/tasks/{task_id}", headers=TENANT_HEADER)
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"

    @pytest.mark.asyncio
    async def test_execute_task_not_found(self, client):
        """Executing a nonexistent task returns 404."""
        resp = await client.post(
            "/api/v1/tasks/nonexistent-id/execute",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_execute_non_pending_task_fails(self, client):
        """Executing a task that is not in pending status returns 400."""
        # Create and then cancel a task
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com"},
            headers=TENANT_HEADER,
        )
        task_id = resp.json()["id"]

        await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=TENANT_HEADER)

        # Try to execute the cancelled task
        resp = await client.post(
            f"/api/v1/tasks/{task_id}/execute",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 400
        assert "not pending" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_execute_already_queued_task_fails(self, client):
        """Executing a task that has already been queued returns 400."""
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com"},
            headers=TENANT_HEADER,
        )
        task_id = resp.json()["id"]

        # Execute once (sets status to queued)
        resp = await client.post(
            f"/api/v1/tasks/{task_id}/execute",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200

        # Execute again should fail
        resp = await client.post(
            f"/api/v1/tasks/{task_id}/execute",
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_execute_task_tenant_isolation(self, client):
        """A tenant cannot execute another tenant's task."""
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com"},
            headers={"X-Tenant-ID": "tenant-a"},
        )
        task_id = resp.json()["id"]

        resp = await client.post(
            f"/api/v1/tasks/{task_id}/execute",
            headers={"X-Tenant-ID": "tenant-b"},
        )
        assert resp.status_code == 404


class TestDryRunRoute:
    """Tests for POST /api/v1/route (dry-run routing)."""

    @pytest.mark.asyncio
    async def test_dry_run_basic_url(self, client):
        """Dry-run routing for a basic URL returns HTTP lane."""
        resp = await client.post(
            "/api/v1/route",
            json={"url": "https://example.com/page"},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://example.com/page"
        assert "route" in data
        assert data["route"]["lane"] == "http"

    @pytest.mark.asyncio
    async def test_dry_run_browser_domain(self, client):
        """Dry-run routing for a known browser domain returns browser lane."""
        resp = await client.post(
            "/api/v1/route",
            json={"url": "https://www.instagram.com/profile"},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        assert resp.json()["route"]["lane"] == "browser"

    @pytest.mark.asyncio
    async def test_dry_run_api_domain(self, client):
        """Dry-run routing for a known API domain returns API lane."""
        resp = await client.post(
            "/api/v1/route",
            json={"url": "https://store.myshopify.com/products.json"},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        assert resp.json()["route"]["lane"] == "api"

    @pytest.mark.asyncio
    async def test_dry_run_with_policy(self, client):
        """Dry-run routing respects policy preferred lane."""
        # Create a policy
        resp = await client.post(
            "/api/v1/policies",
            json={"name": "Hard Target", "preferred_lane": "hard_target"},
            headers=TENANT_HEADER,
        )
        policy_id = resp.json()["id"]

        resp = await client.post(
            "/api/v1/route",
            json={"url": "https://example.com", "policy_id": policy_id},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        assert resp.json()["route"]["lane"] == "hard_target"

    @pytest.mark.asyncio
    async def test_dry_run_with_nonexistent_policy(self, client):
        """Dry-run routing with a nonexistent policy_id returns 404."""
        resp = await client.post(
            "/api/v1/route",
            json={
                "url": "https://example.com",
                "policy_id": "00000000-0000-0000-0000-000000000000",
            },
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 404
        assert "policy" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_dry_run_does_not_create_task(self, client):
        """Dry-run routing does not create any task in the database."""
        await client.post(
            "/api/v1/route",
            json={"url": "https://example.com"},
            headers=TENANT_HEADER,
        )

        # Verify no tasks exist
        resp = await client.get("/api/v1/tasks", headers=TENANT_HEADER)
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_dry_run_response_structure(self, client):
        """Verify the full response structure of dry-run routing."""
        resp = await client.post(
            "/api/v1/route",
            json={"url": "https://example.com/data"},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert "route" in data
        route = data["route"]
        assert set(route.keys()) == {"lane", "reason", "fallback_lanes", "confidence"}

    @pytest.mark.asyncio
    async def test_dry_run_auto_policy_uses_default_routing(self, client):
        """A policy with AUTO lane preference falls through to default routing."""
        resp = await client.post(
            "/api/v1/policies",
            json={"name": "Auto Policy", "preferred_lane": "auto"},
            headers=TENANT_HEADER,
        )
        policy_id = resp.json()["id"]

        resp = await client.post(
            "/api/v1/route",
            json={"url": "https://example.com", "policy_id": policy_id},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        # AUTO should fall through to default HTTP for a generic domain
        assert resp.json()["route"]["lane"] == "http"
