"""
JWT authentication and tenant middleware for the control plane.

Provides:
- Token creation and verification helpers
- FastAPI dependency for extracting the current user from a Bearer token
- Role-based access control dependency factory
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.control_plane.config import settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Parameters
    ----------
    data:
        Arbitrary claims to embed.  Must include at least ``sub``.
    expires_delta:
        Custom lifetime.  Falls back to ``settings.jwt_access_token_expire_minutes``.

    Returns
    -------
    str
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT token.

    Returns
    -------
    dict
        The token payload on success.

    Raises
    ------
    HTTPException (401)
        If the token is expired, tampered with, or otherwise invalid.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency — extract and validate the current user from the
    Authorization header.

    Returns a dict with at least ``sub``, ``tenant_id``, and ``roles``.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials)

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "sub": sub,
        "tenant_id": payload.get("tenant_id", "default"),
        "roles": payload.get("roles", []),
    }


def require_role(*roles: str):
    """Dependency factory that enforces one-or-more roles on the current user.

    Usage::

        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
        async def admin_only(): ...
    """

    async def _check(
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        user_roles = set(user.get("roles", []))
        if not user_roles.intersection(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}",
            )
        return user

    return _check
