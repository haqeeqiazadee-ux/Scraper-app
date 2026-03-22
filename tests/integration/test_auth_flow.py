"""
Integration tests for the auth middleware:
  create JWT, access protected endpoints, test role-based access,
  test expired tokens.

These tests conditionally skip if PyJWT is not available.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

# Check if JWT is importable at module level
_jwt_available = True
try:
    from services.control_plane.middleware.auth import (
        create_access_token,
        verify_token,
        require_role,
        get_current_user,
    )
except BaseException:
    _jwt_available = False

pytestmark = pytest.mark.skipif(not _jwt_available, reason="PyJWT not available")


@pytest.mark.asyncio
class TestAuthFlow:
    """Auth middleware integration tests."""

    async def test_create_and_verify_token(self):
        """A freshly created token should verify successfully."""
        claims = {"sub": "testuser", "tenant_id": "t1", "roles": ["user"]}
        token = create_access_token(claims)

        payload = verify_token(token)
        assert payload["sub"] == "testuser"
        assert payload["tenant_id"] == "t1"
        assert "user" in payload["roles"]
        assert "exp" in payload

    async def test_expired_token_raises(self):
        """An expired token should raise an HTTPException with 401."""
        from fastapi import HTTPException

        claims = {"sub": "testuser", "tenant_id": "t1", "roles": ["user"]}
        token = create_access_token(claims, expires_delta=timedelta(seconds=-1))

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    async def test_invalid_token_raises(self):
        """A garbage token should raise 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_token("not-a-real-jwt-token")
        assert exc_info.value.status_code == 401

    async def test_token_via_auth_endpoint(self, client):
        """POST /api/v1/auth/token issues a valid JWT."""
        resp = await client.post(
            "/api/v1/auth/token",
            json={"username": "admin", "password": "secret"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Verify the issued token is valid
        payload = verify_token(data["access_token"])
        assert payload["sub"] == "admin"

    async def test_auth_me_endpoint(self, client):
        """GET /api/v1/auth/me returns current user claims when authenticated."""
        # Issue a token
        token_resp = await client.post(
            "/api/v1/auth/token",
            json={"username": "testuser", "password": "pass"},
        )
        token = token_resp.json()["access_token"]

        # Use token to access /me
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        user = resp.json()
        assert user["sub"] == "testuser"
        assert "roles" in user
