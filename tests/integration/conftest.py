"""
Shared fixtures for integration tests.

Provides: test database, test client, sample data factories.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from services.control_plane.dependencies import init_database, get_database


# ---------------------------------------------------------------------------
# Database fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def test_db():
    """Create an in-memory SQLite database for integration tests."""
    db = init_database("sqlite+aiosqlite:///:memory:")
    await db.create_tables()
    yield db
    await db.drop_tables()
    await db.close()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest.fixture
async def client(test_db):
    """Create a FastAPI test client backed by the in-memory database."""
    from services.control_plane.app import create_app
    from services.control_plane.middleware.rate_limit import set_rate_limiter
    from packages.core.rate_limiter import InMemoryRateLimiter, RateLimitConfig

    # Use very generous rate limits for tests
    test_limiter = InMemoryRateLimiter(
        default_config=RateLimitConfig(
            requests_per_minute=10000,
            requests_per_hour=100000,
            burst_size=10000,
        )
    )
    set_rate_limiter(test_limiter)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_rate_limiter(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tenant headers
# ---------------------------------------------------------------------------

TENANT_HEADER = {"X-Tenant-ID": "test-tenant"}
TENANT_ID = "test-tenant"


@pytest.fixture
def tenant_header():
    """Default tenant header dict."""
    return dict(TENANT_HEADER)


@pytest.fixture
def tenant_id():
    """Default tenant ID string."""
    return TENANT_ID


# ---------------------------------------------------------------------------
# Data factories
# ---------------------------------------------------------------------------

class TaskFactory:
    """Factory for creating task payloads."""

    @staticmethod
    def create(
        url: str = "https://example.com/products",
        task_type: str = "scrape",
        priority: int = 5,
        **kwargs,
    ) -> dict:
        payload = {
            "url": url,
            "task_type": task_type,
            "priority": priority,
        }
        payload.update(kwargs)
        return payload

    @staticmethod
    async def create_via_api(
        client: AsyncClient,
        url: str = "https://example.com/products",
        headers: dict | None = None,
        **kwargs,
    ) -> dict:
        """Create a task through the API and return the response data."""
        payload = TaskFactory.create(url=url, **kwargs)
        resp = await client.post(
            "/api/v1/tasks",
            json=payload,
            headers=headers or TENANT_HEADER,
        )
        assert resp.status_code == 201
        return resp.json()


class PolicyFactory:
    """Factory for creating policy payloads."""

    @staticmethod
    def create(
        name: str = "Test Policy",
        target_domains: list[str] | None = None,
        preferred_lane: str = "auto",
        timeout_ms: int = 30000,
        **kwargs,
    ) -> dict:
        payload = {
            "name": name,
            "target_domains": target_domains or [],
            "preferred_lane": preferred_lane,
            "timeout_ms": timeout_ms,
        }
        payload.update(kwargs)
        return payload

    @staticmethod
    async def create_via_api(
        client: AsyncClient,
        name: str = "Test Policy",
        headers: dict | None = None,
        **kwargs,
    ) -> dict:
        """Create a policy through the API and return the response data."""
        payload = PolicyFactory.create(name=name, **kwargs)
        resp = await client.post(
            "/api/v1/policies",
            json=payload,
            headers=headers or TENANT_HEADER,
        )
        assert resp.status_code == 201
        return resp.json()


class ResultFactory:
    """Factory for creating result data dicts (for direct DB insertion)."""

    @staticmethod
    def create(
        task_id: str | None = None,
        run_id: str | None = None,
        url: str = "https://example.com/products",
        extracted_data: list[dict] | None = None,
        item_count: int = 3,
        confidence: float = 0.95,
        extraction_method: str = "deterministic",
    ) -> dict:
        return {
            "id": str(uuid4()),
            "task_id": task_id or str(uuid4()),
            "run_id": run_id or str(uuid4()),
            "url": url,
            "extracted_data": extracted_data or [
                {"name": "Product A", "price": "29.99"},
                {"name": "Product B", "price": "49.99"},
                {"name": "Product C", "price": "19.99"},
            ],
            "item_count": item_count,
            "confidence": confidence,
            "extraction_method": extraction_method,
        }


@pytest.fixture
def task_factory():
    return TaskFactory()


@pytest.fixture
def policy_factory():
    return PolicyFactory()


@pytest.fixture
def result_factory():
    return ResultFactory()
