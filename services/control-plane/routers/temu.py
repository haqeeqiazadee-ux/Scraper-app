"""P0.7 — Temu scraper route.

Scrapes Temu (temu.com) product listings, best-sellers, and category
trends. Critical pre-Amazon trend signal — Temu is the mid-stage in
the 1688 -> Temu -> Amazon pipeline (COMPOSITE_AI_RESEARCH.md
Section 23.6).

Heavy JS-rendered pages — uses the Playwright session pool in the
execution router.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

temu_router = APIRouter(prefix="/temu", tags=["Temu"])


class TemuRequest(BaseModel):
    mode: str = Field(..., description="search | bestsellers | category | product_detail")
    query: str | None = Field(default=None, description="Required for search mode")
    category_id: str | None = Field(default=None, description="Required for category mode")
    product_id: str | None = Field(default=None, description="Required for product_detail mode")
    country: str = Field(default="US", description="Storefront country code")
    limit: int = Field(default=100, ge=1, le=500)


class TemuJob(BaseModel):
    job_id: str
    status: str
    mode: str
    created_at: str
    items_found: int = 0


_jobs: dict[str, dict[str, Any]] = {}


@temu_router.post("/scrape", status_code=status.HTTP_202_ACCEPTED)
async def scrape(req: TemuRequest) -> TemuJob:
    valid_modes = {"search", "bestsellers", "category", "product_detail"}
    if req.mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"mode must be one of {valid_modes}")
    if req.mode == "search" and not req.query:
        raise HTTPException(status_code=400, detail="search mode requires 'query'")
    if req.mode == "category" and not req.category_id:
        raise HTTPException(status_code=400, detail="category mode requires 'category_id'")
    if req.mode == "product_detail" and not req.product_id:
        raise HTTPException(status_code=400, detail="product_detail mode requires 'product_id'")

    job_id = f"temu_{uuid.uuid4().hex[:12]}"
    record = {
        "job_id": job_id,
        "status": "queued",
        "mode": req.mode,
        "created_at": datetime.utcnow().isoformat(),
        "params": req.model_dump(),
        "items_found": 0,
    }
    _jobs[job_id] = record
    logger.info("temu.queued", job_id=job_id, mode=req.mode)
    return TemuJob(**record)


@temu_router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> TemuJob:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return TemuJob(**job)
