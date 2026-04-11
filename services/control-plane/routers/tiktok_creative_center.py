"""P0.2 — TikTok Creative Center scraper route.

Scrapes the public TikTok Creative Center for:
    - Top performing ads (ads.tiktok.com/business/creativecenter)
    - Trending hashtags and creators
    - Keyword insights by region
    - Top products (TikTok Shop)

Feeds YOUSELL E01 tiktok-discovery and E05 creator-matching so the
platform can surface pre-viral products 2-8 weeks before they hit
Amazon (per COMPOSITE_AI_RESEARCH.md Section 23.6 upstream_supply_signal).

Phase 0A scope: route skeleton + job queueing.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

tiktok_cc_router = APIRouter(prefix="/tiktok-creative-center", tags=["TikTok Creative Center"])


class TikTokCreativeRequest(BaseModel):
    mode: str = Field(
        ...,
        description="top_ads | trending_hashtags | trending_creators | keyword_insights | top_products",
    )
    country: str = Field(default="US", description="ISO 3166-1 alpha-2 country code")
    industry: str | None = Field(default=None, description="Industry filter (e.g. 'beauty', 'electronics')")
    keyword: str | None = Field(default=None, description="Required for keyword_insights mode")
    time_window: str = Field(default="7d", description="1d | 7d | 30d | 120d")
    limit: int = Field(default=100, ge=1, le=1000)


class TikTokCreativeJob(BaseModel):
    job_id: str
    status: str
    mode: str
    created_at: str
    results_found: int = 0


_jobs: dict[str, dict[str, Any]] = {}


@tiktok_cc_router.post("/scrape", status_code=status.HTTP_202_ACCEPTED)
async def start_scrape(req: TikTokCreativeRequest) -> TikTokCreativeJob:
    valid_modes = {
        "top_ads",
        "trending_hashtags",
        "trending_creators",
        "keyword_insights",
        "top_products",
    }
    if req.mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"mode must be one of {valid_modes}")
    if req.mode == "keyword_insights" and not req.keyword:
        raise HTTPException(status_code=400, detail="keyword_insights mode requires 'keyword'")

    job_id = f"tcc_{uuid.uuid4().hex[:12]}"
    record = {
        "job_id": job_id,
        "status": "queued",
        "mode": req.mode,
        "created_at": datetime.utcnow().isoformat(),
        "params": req.model_dump(),
        "results_found": 0,
    }
    _jobs[job_id] = record
    logger.info("tiktok_cc.queued", job_id=job_id, mode=req.mode, country=req.country)
    return TikTokCreativeJob(**record)


@tiktok_cc_router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> TikTokCreativeJob:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return TikTokCreativeJob(**job)
