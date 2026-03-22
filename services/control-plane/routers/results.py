"""Result and export API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.storage.repositories import ResultRepository
from services.control_plane.dependencies import get_session, get_tenant_id

router = APIRouter()


@router.get("/results/{result_id}")
async def get_result(
    result_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Get a result by ID."""
    repo = ResultRepository(session)
    result = await repo.get(result_id, tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return {
        "id": result.id,
        "task_id": result.task_id,
        "run_id": result.run_id,
        "tenant_id": result.tenant_id,
        "url": result.url,
        "extracted_data": result.extracted_data,
        "item_count": result.item_count,
        "confidence": result.confidence,
        "extraction_method": result.extraction_method,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


@router.get("/tasks/{task_id}/results")
async def get_task_results(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Get all results for a task."""
    repo = ResultRepository(session)
    results = await repo.list_by_task(task_id, tenant_id)
    return {
        "items": [
            {
                "id": r.id,
                "run_id": r.run_id,
                "url": r.url,
                "item_count": r.item_count,
                "confidence": r.confidence,
                "extraction_method": r.extraction_method,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ],
        "total": len(results),
    }
