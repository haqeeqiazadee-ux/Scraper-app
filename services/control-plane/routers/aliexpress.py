"""P0.5 — AliExpress scraper route.

Scrapes AliExpress public product listings. Feeds YOUSELL E08
supplier-discovery with Chinese supplier data + sale velocity signals.

Fields: product_id, title, price, discount, rating, review_count,
orders_count, store_name, store_rating, shipping_options, images.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

aliexpress_router = APIRouter(prefix="/aliexpress", tags=["AliExpress"])


class AliexpressSearchRequest(BaseModel):
    query: str = Field(..., description="Product keyword")
    category_id: str | None = Field(default=None, description="AliExpress category id")
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    min_rating: float | None = Field(default=None, ge=0, le=5)
    free_shipping: bool = Field(default=False)
    ship_to: str = Field(default="US", description="Destination country for shipping filter")
    sort: str = Field(default="orders", description="relevance | price_asc | price_desc | orders | newest")
    limit: int = Field(default=100, ge=1, le=500)


class AliexpressJob(BaseModel):
    job_id: str
    status: str
    created_at: str
    query: str
    products_found: int = 0


_jobs: dict[str, dict[str, Any]] = {}


@aliexpress_router.post("/search", status_code=status.HTTP_202_ACCEPTED)
async def search(req: AliexpressSearchRequest) -> AliexpressJob:
    job_id = f"ali_{uuid.uuid4().hex[:12]}"
    record = {
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "query": req.query,
        "params": req.model_dump(),
        "products_found": 0,
    }
    _jobs[job_id] = record
    logger.info("aliexpress.queued", job_id=job_id, query=req.query)
    return AliexpressJob(**record)


@aliexpress_router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> AliexpressJob:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return AliexpressJob(**job)
