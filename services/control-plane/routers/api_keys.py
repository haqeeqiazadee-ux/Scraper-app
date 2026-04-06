"""API key management router — dashboard-facing CRUD for API keys.

Uses JWT-based tenant authentication (``get_tenant_id``), NOT API-key auth.
This router is mounted under ``/api/v1/api-keys`` and lets tenants create,
list, and revoke their ``sk_live_*`` keys via the dashboard.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts.public_api import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyResponse,
)
from packages.core.storage.repositories_public_api import ApiKeyRepository
from services.control_plane.dependencies import get_session, get_tenant_id

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_raw_key() -> str:
    """Generate a new ``sk_live_`` prefixed API key."""
    return "sk_live_" + secrets.token_hex(16)


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash a raw API key for storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _key_prefix(raw_key: str) -> str:
    """Return a safe display prefix (first 12 chars)."""
    return raw_key[:12]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

api_keys_router = APIRouter(prefix="/api/v1/api-keys", tags=["API Keys"])


@api_keys_router.post("", status_code=201)
async def create_api_key(
    body: ApiKeyCreate,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a new API key.

    The full key is returned **only once** in this response.  Store it
    securely -- it cannot be retrieved again.
    """
    raw_key = _generate_raw_key()
    key_hash = _hash_key(raw_key)
    prefix = _key_prefix(raw_key)

    expires_at: Optional[datetime] = None
    if body.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    repo = ApiKeyRepository(session)
    api_key = await repo.create(
        tenant_id=tenant_id,
        key_hash=key_hash,
        key_prefix=prefix,
        name=body.name,
        scopes=body.scopes,
        expires_at=expires_at,
    )

    logger.info(
        "api_keys.created",
        api_key_id=api_key.id,
        tenant_id=tenant_id,
        name=body.name,
        scopes=body.scopes,
    )

    return ApiKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key_prefix=prefix,
        scopes=api_key.scopes or ["*"],
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        key=raw_key,
    )


@api_keys_router.get("", status_code=200)
async def list_api_keys(
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """List all API keys for the tenant (prefix only, never the full key)."""
    repo = ApiKeyRepository(session)
    keys, total = await repo.list_by_tenant(tenant_id)

    result = [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes or ["*"],
            is_active=k.is_active,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ]

    logger.info("api_keys.listed", tenant_id=tenant_id, count=len(result))
    return {"items": [r.model_dump(mode="json") for r in result], "total": total}


@api_keys_router.delete("/{key_id}", status_code=200)
async def revoke_api_key(
    key_id: str,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Revoke an API key (sets ``is_active=False`` and ``revoked_at``)."""
    repo = ApiKeyRepository(session)
    api_key = await repo.revoke(key_id, tenant_id)

    if api_key is None:
        raise HTTPException(
            status_code=404,
            detail=f"API key {key_id} not found or does not belong to this tenant.",
        )

    logger.info(
        "api_keys.revoked",
        api_key_id=key_id,
        tenant_id=tenant_id,
    )
    return {
        "id": key_id,
        "status": "revoked",
        "revoked_at": api_key.revoked_at.isoformat() if api_key.revoked_at else None,
    }
