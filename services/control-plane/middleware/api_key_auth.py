"""
API-key authentication middleware for the Zero Checksum Public API.

Validates ``sk_live_*`` bearer tokens against hashed keys stored in the
``api_keys`` table and injects an ``ApiKeyContext`` into ``request.state``.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.storage.models_public_api import ApiKeyModel

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class ApiKeyContext:
    """Resolved identity for an authenticated API-key request."""

    tenant_id: str
    api_key_id: str
    scopes: list[str]
    plan_tier: str


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash a raw API key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _error_envelope(code: str, message: str) -> dict:
    """Build a minimal error body matching the standard API envelope."""
    return {
        "request_id": None,
        "idempotency_key": None,
        "status": "error",
        "data": None,
        "meta": None,
        "errors": [{"code": code, "message": message}],
    }


async def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> ApiKeyContext:
    """FastAPI dependency — authenticate via API key.

    Accepts keys in either the ``Authorization: Bearer sk_live_xxx`` header
    or the ``X-API-Key`` header.

    Sets ``request.state.api_key_context`` on success.

    Raises
    ------
    HTTPException (401)
        If the key is missing, invalid, expired, or revoked.
    """
    # Extract raw key from Authorization header or X-API-Key header
    raw_key: str | None = None
    if credentials is not None:
        raw_key = credentials.credentials
    else:
        raw_key = request.headers.get("X-API-Key")

    if raw_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_envelope("INVALID_API_KEY", "Missing API key"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    key_hash = _hash_key(raw_key)

    # Look up key in database
    session: AsyncSession = request.state.db  # assumes DB session on request
    stmt = select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
    result = await session.execute(stmt)
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_envelope("INVALID_API_KEY", "Invalid API key"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate active state
    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_envelope("INVALID_API_KEY", "API key is inactive"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate not revoked
    if api_key.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_envelope("API_KEY_REVOKED", "API key has been revoked"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate expiration
    now = datetime.now(timezone.utc)
    if api_key.expires_at is not None and api_key.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_error_envelope("API_KEY_EXPIRED", "API key has expired"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_used_at
    await session.execute(
        update(ApiKeyModel)
        .where(ApiKeyModel.id == api_key.id)
        .values(last_used_at=now)
    )

    ctx = ApiKeyContext(
        tenant_id=api_key.tenant_id,
        api_key_id=api_key.id,
        scopes=api_key.scopes or ["*"],
        plan_tier=getattr(request.state, "plan_tier", "free"),
    )

    request.state.api_key_context = ctx
    return ctx
