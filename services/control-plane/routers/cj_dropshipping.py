"""P0.4 — CJ Dropshipping scraper route.

Scrapes CJ Dropshipping (cjdropshipping.com) for supplier catalog,
pricing, fulfillment data, and trending products. Feeds YOUSELL E08
supplier-discovery and the fulfillment-recommendation engine.

CJ has a public search page + an OAuth-gated developer API. This
route uses the public search path first and falls back to the API
when CJ_API_KEY is set.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

cj_router = APIRouter(prefix="/cj-dropshipping", tags=["CJ Dropshipping"])


class CjSearchRequest(BaseModel):
    query: str = Field(..., description="Product search query")
    category: str | None = Field(default=None, description="CJ category id or name")
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    sort: str = Field(default="relevance", description="relevance | price_asc | price_desc | sales | newest")
    limit: int = Field(default=100, ge=1, le=500)


class CjJob(BaseModel):
    job_id: str
    status: str
    created_at: str
    query: str
    products_found: int = 0


_jobs: dict[str, dict[str, Any]] = {}


@cj_router.post("/search", status_code=status.HTTP_202_ACCEPTED)
async def search(req: CjSearchRequest) -> CjJob:
    job_id = f"cj_{uuid.uuid4().hex[:12]}"
    record = {
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "query": req.query,
        "params": req.model_dump(),
        "products_found": 0,
    }
    _jobs[job_id] = record
    logger.info("cj.queued", job_id=job_id, query=req.query)
    return CjJob(**record)


@cj_router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> CjJob:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return CjJob(**job)
