"""
E2E test fixtures: full app client, auth tokens.
"""

from __future__ import annotations

import pytest

try:
    from httpx import ASGITransport, AsyncClient
    from services.control_plane.dependencies import init_database
    _HAS_BACKEND_DEPS = True
except ImportError:
    _HAS_BACKEND_DEPS = False


# ---------------------------------------------------------------------------
# Full application client
# ---------------------------------------------------------------------------

@pytest.fixture
async def app_client():
    """Create a full application client for E2E testing.

    Initializes a fresh in-memory database and creates the complete
    FastAPI application with all middleware and routers.
    """
    if not _HAS_BACKEND_DEPS:
        pytest.skip("httpx or backend dependencies not installed")
    db = init_database("sqlite+aiosqlite:///:memory:")
    await db.create_tables()

    from services.control_plane.app import create_app
    from services.control_plane.middleware.rate_limit import set_rate_limiter
    from packages.core.rate_limiter import InMemoryRateLimiter, RateLimitConfig

    # Use very generous rate limits for E2E tests
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
    await db.drop_tables()
    await db.close()


TENANT_HEADER = {"X-Tenant-ID": "e2e-tenant"}
E2E_TENANT = "e2e-tenant"


@pytest.fixture
def e2e_headers():
    """Default E2E tenant headers."""
    return dict(TENANT_HEADER)


# ---------------------------------------------------------------------------
# Auth token fixture (conditional — JWT may not be available)
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_token():
    """Create a JWT auth token if PyJWT is available, else skip."""
    try:
        from services.control_plane.middleware.auth import create_access_token
        token = create_access_token({"sub": "e2e-user", "tenant_id": E2E_TENANT, "roles": ["user"]})
        return token
    except Exception:
        pytest.skip("JWT support not available (PyJWT/cryptography issue)")


@pytest.fixture
def auth_headers(auth_token, e2e_headers):
    """Headers with both tenant ID and Authorization bearer token."""
    headers = dict(e2e_headers)
    headers["Authorization"] = f"Bearer {auth_token}"
    return headers
