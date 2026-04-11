"""P0.6 — 1688.com scraper route.

Scrapes 1688.com — Alibaba's domestic-China wholesale marketplace.
This is the PRIMARY upstream signal for YOUSELL's Composite AI
upstream_supply_signal confounder (COMPOSITE_AI_RESEARCH.md
Section 23.6). Products appearing here precede Amazon trends by
2-8 weeks via the 1688 -> Temu -> Amazon pipeline.

Note: 1688 is Chinese-language only. The scraper captures the raw
Chinese title and relies on downstream translation (the existing
Azure Translator integration).

Requires a Chinese IP via rotating proxy pool — the control plane
has a proxy_providers module in packages/connectors.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

alibaba_1688_router = APIRouter(prefix="/alibaba-1688", tags=["Alibaba 1688"])


class Alibaba1688SearchRequest(BaseModel):
    query: str = Field(..., description="Search keyword (Chinese or pinyin)")
    min_price_cny: float | None = Field(default=None, ge=0, description="Price in RMB")
    max_price_cny: float | None = Field(default=None, ge=0)
    min_moq: int | None = Field(default=None, ge=0, description="Minimum order quantity filter")
    sort: str = Field(default="sales_desc", description="relevance | price_asc | price_desc | sales_desc | newest")
    translate: bool = Field(default=True, description="Run Azure Translator on titles post-scrape")
    limit: int = Field(default=100, ge=1, le=500)


class Alibaba1688Job(BaseModel):
    job_id: str
    status: str
    created_at: str
    query: str
    products_found: int = 0


_jobs: dict[str, dict[str, Any]] = {}


@alibaba_1688_router.post("/search", status_code=status.HTTP_202_ACCEPTED)
async def search(req: Alibaba1688SearchRequest) -> Alibaba1688Job:
    job_id = f"1688_{uuid.uuid4().hex[:12]}"
    record = {
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "query": req.query,
        "params": req.model_dump(),
        "products_found": 0,
    }
    _jobs[job_id] = record
    logger.info("alibaba_1688.queued", job_id=job_id, query=req.query)
    return Alibaba1688Job(**record)


@alibaba_1688_router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Alibaba1688Job:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return Alibaba1688Job(**job)
