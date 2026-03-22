"""Integration tests for Task API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from services.control_plane.dependencies import init_database, get_database


@pytest.fixture
async def client():
    """Create a test client with in-memory database."""
    db = init_database("sqlite+aiosqlite:///:memory:")
    await db.create_tables()

    from services.control_plane.app import create_app
    app = create_app()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    await db.drop_tables()
    await db.close()


TENANT_HEADER = {"X-Tenant-ID": "test-tenant"}


class TestTasksAPI:

    @pytest.mark.asyncio
    async def test_create_task(self, client):
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com/products"},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["url"] == "https://example.com/products"
        assert data["status"] == "pending"
        assert data["tenant_id"] == "test-tenant"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_task(self, client):
        # Create
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com"},
            headers=TENANT_HEADER,
        )
        task_id = resp.json()["id"]

        # Get
        resp = await client.get(f"/api/v1/tasks/{task_id}", headers=TENANT_HEADER)
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, client):
        resp = await client.get("/api/v1/tasks/nonexistent", headers=TENANT_HEADER)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_task_tenant_isolation(self, client):
        # Create as tenant-1
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com"},
            headers={"X-Tenant-ID": "tenant-1"},
        )
        task_id = resp.json()["id"]

        # Try to get as tenant-2
        resp = await client.get(f"/api/v1/tasks/{task_id}", headers={"X-Tenant-ID": "tenant-2"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_tasks(self, client):
        # Create 3 tasks
        for i in range(3):
            await client.post(
                "/api/v1/tasks",
                json={"url": f"https://example.com/{i}"},
                headers=TENANT_HEADER,
            )

        resp = await client.get("/api/v1/tasks", headers=TENANT_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_tasks_filter_status(self, client):
        # Create a task
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com"},
            headers=TENANT_HEADER,
        )
        task_id = resp.json()["id"]

        # Update to running
        await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "running"},
            headers=TENANT_HEADER,
        )

        # Filter by running
        resp = await client.get("/api/v1/tasks?status=running", headers=TENANT_HEADER)
        assert resp.json()["total"] == 1

        # Filter by completed (should be empty)
        resp = await client.get("/api/v1/tasks?status=completed", headers=TENANT_HEADER)
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_update_task(self, client):
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com"},
            headers=TENANT_HEADER,
        )
        task_id = resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "running", "priority": 10},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"
        assert resp.json()["priority"] == 10

    @pytest.mark.asyncio
    async def test_cancel_task(self, client):
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com"},
            headers=TENANT_HEADER,
        )
        task_id = resp.json()["id"]

        resp = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=TENANT_HEADER)
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_task_fails(self, client):
        resp = await client.post(
            "/api/v1/tasks",
            json={"url": "https://example.com"},
            headers=TENANT_HEADER,
        )
        task_id = resp.json()["id"]

        # Set to completed
        await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "completed"},
            headers=TENANT_HEADER,
        )

        # Try to cancel
        resp = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=TENANT_HEADER)
        assert resp.status_code == 400


class TestPoliciesAPI:

    @pytest.mark.asyncio
    async def test_create_policy(self, client):
        resp = await client.post(
            "/api/v1/policies",
            json={"name": "E-Commerce Policy", "target_domains": ["shop.com"]},
            headers=TENANT_HEADER,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "E-Commerce Policy"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_policy(self, client):
        resp = await client.post(
            "/api/v1/policies",
            json={"name": "Test"},
            headers=TENANT_HEADER,
        )
        policy_id = resp.json()["id"]

        resp = await client.get(f"/api/v1/policies/{policy_id}", headers=TENANT_HEADER)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test"

    @pytest.mark.asyncio
    async def test_list_policies(self, client):
        for name in ["P1", "P2"]:
            await client.post(
                "/api/v1/policies",
                json={"name": name},
                headers=TENANT_HEADER,
            )

        resp = await client.get("/api/v1/policies", headers=TENANT_HEADER)
        assert resp.json()["total"] == 2

    @pytest.mark.asyncio
    async def test_delete_policy(self, client):
        resp = await client.post(
            "/api/v1/policies",
            json={"name": "ToDelete"},
            headers=TENANT_HEADER,
        )
        policy_id = resp.json()["id"]

        resp = await client.delete(f"/api/v1/policies/{policy_id}", headers=TENANT_HEADER)
        assert resp.status_code == 204

        resp = await client.get(f"/api/v1/policies/{policy_id}", headers=TENANT_HEADER)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_policy_tenant_isolation(self, client):
        resp = await client.post(
            "/api/v1/policies",
            json={"name": "Private"},
            headers={"X-Tenant-ID": "tenant-a"},
        )
        policy_id = resp.json()["id"]

        resp = await client.get(f"/api/v1/policies/{policy_id}", headers={"X-Tenant-ID": "tenant-b"})
        assert resp.status_code == 404
