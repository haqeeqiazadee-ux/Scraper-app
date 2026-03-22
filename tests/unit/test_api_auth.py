"""Tests for JWT authentication middleware and auth endpoints."""

from __future__ import annotations

import sys
from datetime import timedelta

import pytest

# PyJWT's cryptography dependency may crash with PanicException (not an Exception)
try:
    import jwt as pyjwt  # noqa: F401
    _jwt_ok = True
except BaseException:
    _jwt_ok = False

if not _jwt_ok:
    # If jwt is completely unusable, skip the entire module at collect time
    pytest.skip("PyJWT not usable in this environment", allow_module_level=True)

from httpx import ASGITransport, AsyncClient  # noqa: E402

from services.control_plane.app import create_app  # noqa: E402
from services.control_plane.config import settings  # noqa: E402
from services.control_plane.dependencies import init_database  # noqa: E402
from services.control_plane.middleware.auth import (  # noqa: E402
    create_access_token,
    verify_token,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    db = init_database("sqlite+aiosqlite:///:memory:")
    await db.create_tables()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await db.close()


def _make_token(claims: dict | None = None, **kw) -> str:
    """Convenience helper to mint a token with default claims."""
    data = {"sub": "testuser", "tenant_id": "t1", "roles": ["user"]}
    if claims:
        data.update(claims)
    return create_access_token(data, **kw)


# ---------------------------------------------------------------------------
# Unit tests — token helpers
# ---------------------------------------------------------------------------

class TestTokenCreation:

    def test_create_access_token_returns_string(self):
        token = create_access_token({"sub": "alice"})
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_create_access_token_embeds_claims(self):
        token = create_access_token({"sub": "bob", "tenant_id": "acme"})
        payload = pyjwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        assert payload["sub"] == "bob"
        assert payload["tenant_id"] == "acme"
        assert "exp" in payload

    def test_create_access_token_custom_expiry(self):
        token = create_access_token(
            {"sub": "carol"},
            expires_delta=timedelta(hours=2),
        )
        payload = pyjwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        assert payload["sub"] == "carol"


class TestTokenVerification:

    def test_verify_valid_token(self):
        token = create_access_token({"sub": "dave", "extra": 42})
        payload = verify_token(token)
        assert payload["sub"] == "dave"
        assert payload["extra"] == 42

    def test_verify_expired_token(self):
        token = create_access_token(
            {"sub": "eve"},
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(Exception) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_verify_invalid_token(self):
        with pytest.raises(Exception) as exc_info:
            verify_token("not.a.jwt")
        assert exc_info.value.status_code == 401

    def test_verify_tampered_token(self):
        token = create_access_token({"sub": "mallory"})
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with pytest.raises(Exception) as exc_info:
            verify_token(tampered)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Integration tests — /auth/token endpoint
# ---------------------------------------------------------------------------

class TestAuthTokenEndpoint:

    @pytest.mark.asyncio
    async def test_issue_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            json={"username": "alice", "password": "secret"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        payload = verify_token(body["access_token"])
        assert payload["sub"] == "alice"

    @pytest.mark.asyncio
    async def test_issue_token_missing_fields(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/token", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Integration tests — /auth/me endpoint
# ---------------------------------------------------------------------------

class TestAuthMeEndpoint:

    @pytest.mark.asyncio
    async def test_me_returns_user(self, client: AsyncClient):
        token = _make_token()
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["sub"] == "testuser"
        assert body["tenant_id"] == "t1"
        assert "user" in body["roles"]

    @pytest.mark.asyncio
    async def test_me_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer garbage.token.here"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_expired_token(self, client: AsyncClient):
        token = create_access_token(
            {"sub": "stale", "tenant_id": "t1", "roles": []},
            expires_delta=timedelta(seconds=-1),
        )
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Role-based access (unit level)
# ---------------------------------------------------------------------------

class TestRequireRole:

    @pytest.mark.asyncio
    async def test_require_role_allowed(self):
        from services.control_plane.middleware.auth import require_role

        checker = require_role("admin", "user")
        user = {"sub": "u1", "tenant_id": "t1", "roles": ["user"]}
        result = await checker(user=user)
        assert result["sub"] == "u1"

    @pytest.mark.asyncio
    async def test_require_role_denied(self):
        from services.control_plane.middleware.auth import require_role

        checker = require_role("admin")
        user = {"sub": "u1", "tenant_id": "t1", "roles": ["user"]}
        with pytest.raises(Exception) as exc_info:
            await checker(user=user)
        assert exc_info.value.status_code == 403
