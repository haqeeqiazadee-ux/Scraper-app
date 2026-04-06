"""
Idempotency middleware for the Zero Checksum Public API.

Ensures POST requests bearing an ``Idempotency-Key`` header return
the same response on replay within the key's TTL window.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.storage.models_public_api import IdempotencyKeyModel

logger = logging.getLogger(__name__)

# Default TTL for idempotency keys (24 hours)
IDEMPOTENCY_TTL = timedelta(hours=24)


class IdempotencyManager:
    """Manages creation and lookup of idempotency keys.

    Each key is scoped to a tenant + endpoint combination.
    """

    async def check(
        self,
        session: AsyncSession,
        tenant_id: str,
        key: str,
        request_hash: str,
        endpoint: str,
    ) -> Optional[dict]:
        """Check for an existing idempotency record.

        Returns
        -------
        dict | None
            The cached response dict if the key was already used, otherwise ``None``.

        Raises
        ------
        HTTPException (409)
            If the same key was used with a different request body hash.
        """
        stmt = select(IdempotencyKeyModel).where(
            IdempotencyKeyModel.tenant_id == tenant_id,
            IdempotencyKeyModel.idempotency_key == key,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            return None

        # Key exists but the request body differs — conflict
        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "request_id": None,
                    "status": "error",
                    "data": None,
                    "meta": None,
                    "errors": [{
                        "code": "IDEMPOTENCY_KEY_CONFLICT",
                        "message": (
                            "Idempotency key has already been used with a "
                            "different request payload"
                        ),
                    }],
                },
            )

        # Check if the key has expired
        now = datetime.now(timezone.utc)
        if existing.expires_at < now:
            # Expired — caller should treat as new
            await session.delete(existing)
            await session.flush()
            return None

        return {
            "request_id": existing.request_id,
            "status_code": existing.response_status,
            "body": existing.response_body,
        }

    async def store(
        self,
        session: AsyncSession,
        tenant_id: str,
        key: str,
        request_id: str,
        endpoint: str,
        request_hash: str,
        response_status: int,
        response_body: dict,
    ) -> None:
        """Persist an idempotency record after a successful response."""
        now = datetime.now(timezone.utc)
        record = IdempotencyKeyModel(
            tenant_id=tenant_id,
            idempotency_key=key,
            request_id=request_id,
            endpoint=endpoint,
            request_hash=request_hash,
            response_status=response_status,
            response_body=response_body,
            created_at=now,
            expires_at=now + IDEMPOTENCY_TTL,
        )
        session.add(record)
        await session.flush()

    async def cleanup_expired(self, session: AsyncSession) -> int:
        """Delete expired idempotency keys.

        Returns the number of rows removed.
        """
        now = datetime.now(timezone.utc)
        stmt = delete(IdempotencyKeyModel).where(
            IdempotencyKeyModel.expires_at < now,
        )
        result = await session.execute(stmt)
        return result.rowcount


# Module-level singleton
_idempotency_manager = IdempotencyManager()


def _hash_body(body: bytes) -> str:
    """SHA-256 hex-digest of the raw request body."""
    return hashlib.sha256(body).hexdigest()


async def check_idempotency(request: Request) -> Optional[dict]:
    """FastAPI dependency for POST endpoints.

    Reads the ``Idempotency-Key`` header.  If present, checks for an
    existing cached response and stores the result on
    ``request.state.idempotency_key``.

    Returns
    -------
    dict | None
        Cached response if the key has already been used, else ``None``.
    """
    idem_key = request.headers.get("Idempotency-Key")
    if idem_key is None:
        return None

    request.state.idempotency_key = idem_key

    session: AsyncSession = request.state.db
    tenant_id = getattr(request.state, "api_key_context", None)
    if tenant_id is not None:
        tenant_id = tenant_id.tenant_id
    else:
        tenant_id = request.headers.get("X-Tenant-ID", "default")

    body = await request.body()
    request_hash = _hash_body(body)
    endpoint = request.url.path

    cached = await _idempotency_manager.check(
        session, tenant_id, idem_key, request_hash, endpoint,
    )
    return cached
