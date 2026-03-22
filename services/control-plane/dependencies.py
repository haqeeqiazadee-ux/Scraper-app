"""
FastAPI dependency injection for the control plane.

Provides database sessions, repositories, and tenant context.
"""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, Header, HTTPException

from packages.core.storage.database import Database
from packages.core.storage.repositories import (
    TaskRepository, PolicyRepository, RunRepository, ResultRepository,
)

# Global database instance — initialized during app startup
_db: Database | None = None


def get_database() -> Database:
    """Get the global database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


def init_database(url: str = "sqlite+aiosqlite:///./scraper.db") -> Database:
    """Initialize the global database."""
    global _db
    _db = Database(url=url)
    return _db


async def get_session():
    """Yield a database session for request scope."""
    db = get_database()
    async with db.session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_tenant_id(
    x_tenant_id: str = Header(default="default", alias="X-Tenant-ID"),
) -> str:
    """Extract tenant ID from request header. Default: 'default'."""
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")
    return x_tenant_id
