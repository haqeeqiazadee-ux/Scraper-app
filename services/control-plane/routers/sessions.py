"""Session management API — stub endpoints for frontend compatibility."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from services.control_plane.dependencies import get_tenant_id

router = APIRouter()


@router.get("/sessions")
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """List browser sessions (stub — returns empty list)."""
    return {"items": [], "total": 0}
