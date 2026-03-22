"""Authentication endpoints — token issuance and user introspection."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.control_plane.middleware.auth import (
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth")


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class TokenRequest(BaseModel):
    """Body for the token-issue endpoint."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Returned on successful authentication."""
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/token", response_model=TokenResponse)
async def issue_token(body: TokenRequest) -> TokenResponse:
    """Issue a JWT access token.

    **Scaffolding implementation** — accepts any username/password combination.
    A real implementation would validate credentials against a user store.
    """
    # Build claims — use username as subject, assign a default tenant and role.
    claims: dict[str, Any] = {
        "sub": body.username,
        "tenant_id": "default",
        "roles": ["user"],
    }
    token = create_access_token(claims)
    return TokenResponse(access_token=token)


@router.get("/me")
async def me(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Return the current authenticated user's claims."""
    return user
