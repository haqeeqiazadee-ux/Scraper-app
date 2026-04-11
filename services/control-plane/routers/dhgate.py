"""P0.8 — DHgate scraper route.

Scrapes DHgate (dhgate.com) — B2B wholesale marketplace that
overlaps with 1688 + Temu for upstream supply signal. Feeds YOUSELL
E08 supplier-discovery and contributes to the composite-ai
upstream_supply_signal confounder.

Fields: product_id, title, price, moq, seller_name, seller_rating,
review_count, orders_count, lead_time_days, ships_from.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

dhgate_router = APIRouter(prefix="/dhgate", tags=["DHgate"])


class DhgateSearchRequest(BaseModel):
    query: str = Field(..., description="Product search query")
    category: str | None = Field(default=None)
    min_price: float | None = Field(default=None, ge=0, description="Price in USD")
    max_price: float | None = Field(default=None, ge=0)
    min_orders: int | None = Field(default=None, ge=0, description="Minimum recent orders filter")
    sort: str = Field(default="orders", description="relevance | price_asc | price_desc | orders | newest")
    limit: int = Field(default=100, ge=1, le=500)


class DhgateJob(BaseModel):
    job_id: str
    status: str
    created_at: str
    query: str
    products_found: int = 0


_jobs: dict[str, dict[str, Any]] = {}


@dhgate_router.post("/search", status_code=status.HTTP_202_ACCEPTED)
async def search(req: DhgateSearchRequest) -> DhgateJob:
    job_id = f"dh_{uuid.uuid4().hex[:12]}"
    record = {
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "query": req.query,
        "params": req.model_dump(),
        "products_found": 0,
    }
    _jobs[job_id] = record
    logger.info("dhgate.queued", job_id=job_id, query=req.query)
    return DhgateJob(**record)


@dhgate_router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> DhgateJob:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return DhgateJob(**job)
