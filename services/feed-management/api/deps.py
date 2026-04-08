"""Database session and optional API key."""

from __future__ import annotations

import os
from collections.abc import Generator
from functools import lru_cache

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_engine


@lru_cache
def _cached_engine():
    return get_engine()


def get_db() -> Generator[Session, None, None]:
    with Session(_cached_engine()) as session:
        yield session


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Require ``X-API-Key`` when ``B2B_API_KEY`` is set in the environment."""
    expected = (os.environ.get("B2B_API_KEY") or "").strip()
    if not expected:
        return
    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
