"""P0.3 — Google Trends scraper route.

Wraps Google Trends fetches via the public endpoint (what pytrends
uses). The TS side has its own Google Trends client in
src/lib/engines/seo/google-trends.ts (SEO-08) which is the
preferred path, but this server-side route exists so:

    1. We can bulk-queue trend fetches in BullMQ without paying the
       alpha API rate limit per client
    2. We can cache results in Supabase for the whole client fleet
    3. SEO-12 composite-ai confounders can be computed server-side
       without every decide() call hitting Google directly
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

google_trends_router = APIRouter(prefix="/google-trends", tags=["Google Trends"])


class GoogleTrendsRequest(BaseModel):
    keywords: list[str] = Field(..., min_length=1, max_length=5, description="1-5 keywords to compare")
    timeframe: str = Field(
        default="today 3-m",
        description="now 1-H | now 4-H | now 1-d | today 1-m | today 3-m | today 12-m | today 5-y",
    )
    geo: str = Field(default="", description="Country code, empty = worldwide")
    category: int = Field(default=0, description="Google Trends category id, 0 = all")


class GoogleTrendsJob(BaseModel):
    job_id: str
    status: str
    created_at: str
    keywords: list[str]


_jobs: dict[str, dict[str, Any]] = {}


@google_trends_router.post("/fetch", status_code=status.HTTP_202_ACCEPTED)
async def fetch_trends(req: GoogleTrendsRequest) -> GoogleTrendsJob:
    job_id = f"gtrend_{uuid.uuid4().hex[:12]}"
    record = {
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "keywords": req.keywords,
        "params": req.model_dump(),
    }
    _jobs[job_id] = record
    logger.info("google_trends.queued", job_id=job_id, keywords=req.keywords, geo=req.geo)
    return GoogleTrendsJob(**record)


@google_trends_router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> GoogleTrendsJob:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return GoogleTrendsJob(**job)
