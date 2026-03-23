"""Result and export API endpoints."""

from __future__ import annotations

import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.storage.repositories import ResultRepository
from services.control_plane.dependencies import get_session, get_tenant_id

router = APIRouter()


class ResultCreateRequest(BaseModel):
    """Request body for creating a result."""
    task_id: str
    run_id: str
    url: str
    extracted_data: list[dict] | dict = []
    item_count: int = 0
    confidence: float = 0.0
    extraction_method: str = "deterministic"


@router.post("/results", status_code=201)
async def create_result(
    body: ResultCreateRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Store an extraction result."""
    repo = ResultRepository(session)
    result = await repo.create(
        tenant_id=tenant_id,
        task_id=body.task_id,
        run_id=body.run_id,
        url=body.url,
        extracted_data=body.extracted_data if isinstance(body.extracted_data, list) else [body.extracted_data],
        item_count=body.item_count,
        confidence=body.confidence,
        extraction_method=body.extraction_method,
    )
    await session.commit()
    return {
        "id": result.id,
        "task_id": result.task_id,
        "run_id": result.run_id,
        "tenant_id": result.tenant_id,
        "item_count": result.item_count,
        "confidence": result.confidence,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


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


def _gather_items(results: list) -> list[dict]:
    """Flatten extracted_data from all results into a single list."""
    items = []
    for r in results:
        data = r.extracted_data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                data = []
        if isinstance(data, list):
            items.extend(data)
        elif isinstance(data, dict):
            items.append(data)
    return items


@router.get("/tasks/{task_id}/export/json")
async def export_json(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    """Export task results as a JSON file download."""
    repo = ResultRepository(session)
    results = await repo.list_by_task(task_id, tenant_id)
    if not results:
        raise HTTPException(status_code=404, detail="No results found for this task")

    items = _gather_items(results)
    content = json.dumps(items, indent=2, default=str)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="export_{task_id}.json"'},
    )


@router.get("/tasks/{task_id}/export/csv")
async def export_csv(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    """Export task results as a CSV file download."""
    repo = ResultRepository(session)
    results = await repo.list_by_task(task_id, tenant_id)
    if not results:
        raise HTTPException(status_code=404, detail="No results found for this task")

    items = _gather_items(results)
    if not items:
        raise HTTPException(status_code=404, detail="No extracted data to export")

    # Collect all unique keys across items for CSV headers
    headers = list(dict.fromkeys(k for item in items for k in item.keys()))

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for item in items:
        writer.writerow(item)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="export_{task_id}.csv"'},
    )


@router.get("/tasks/{task_id}/export/xlsx")
async def export_xlsx(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    """Export task results as an XLSX (Excel) file download."""
    try:
        from openpyxl import Workbook
    except ImportError:
        raise HTTPException(status_code=501, detail="openpyxl not installed for XLSX export")

    repo = ResultRepository(session)
    results = await repo.list_by_task(task_id, tenant_id)
    if not results:
        raise HTTPException(status_code=404, detail="No results found for this task")

    items = _gather_items(results)
    if not items:
        raise HTTPException(status_code=404, detail="No extracted data to export")

    headers = list(dict.fromkeys(k for item in items for k in item.keys()))

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(headers)
    for item in items:
        ws.append([str(item.get(h, "")) for h in headers])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="export_{task_id}.xlsx"'},
    )
