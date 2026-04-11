"""P0.1 — Meta Ad Library scraper route.

Scrapes public ad creatives from Meta's Ad Library transparency portal.
Unlike the existing facebook.py (which handles authenticated group
scraping), this route hits the public endpoint that requires no login.

Used by YOUSELL E07 ad-intelligence + the competitive moat engine
(multi-platform-defense) to see what active ads competitors are running
on Facebook/Instagram.

Fields captured:
    page_id, page_name, ad_creative_id, ad_text, media_urls,
    platform (facebook/instagram/messenger/audience_network),
    impressions_range, spend_range, countries, first_seen, last_seen

Phase 0A scope: route skeleton + job queueing. The actual scraping
worker is wired by the existing execution router and shares the
Playwright session pool.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

meta_ad_library_router = APIRouter(prefix="/meta-ad-library", tags=["Meta Ad Library"])


class MetaAdLibraryRequest(BaseModel):
    """Search parameters for a Meta Ad Library scrape job."""

    search_terms: str = Field(..., description="Search query (brand name, product, keyword)")
    country: str = Field(default="US", description="ISO 3166-1 alpha-2 country code")
    ad_type: str = Field(
        default="all",
        description="all | political_and_issue_ads | housing_ads | employment_ads | credit_ads",
    )
    active_status: str = Field(
        default="all",
        description="all | active | inactive",
    )
    publisher_platforms: list[str] = Field(
        default_factory=lambda: ["facebook", "instagram"],
        description="Subset of facebook/instagram/messenger/audience_network",
    )
    max_ads: int = Field(default=100, ge=1, le=5000)


class MetaAdLibraryJob(BaseModel):
    job_id: str
    status: str
    created_at: str
    params: MetaAdLibraryRequest
    ads_found: int = 0


_jobs: dict[str, dict[str, Any]] = {}


@meta_ad_library_router.post("/scrape", status_code=status.HTTP_202_ACCEPTED)
async def start_scrape(req: MetaAdLibraryRequest) -> MetaAdLibraryJob:
    """Queue a Meta Ad Library scrape job. Returns a job_id to poll."""
    job_id = f"mal_{uuid.uuid4().hex[:12]}"
    record = {
        "job_id": job_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "params": req.model_dump(),
        "ads_found": 0,
    }
    _jobs[job_id] = record
    logger.info("meta_ad_library.queued", job_id=job_id, search_terms=req.search_terms)
    return MetaAdLibraryJob(**record)


@meta_ad_library_router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> MetaAdLibraryJob:
    """Poll a job's status."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")
    return MetaAdLibraryJob(**job)


@meta_ad_library_router.get("/jobs")
async def list_jobs(limit: int = 50) -> list[MetaAdLibraryJob]:
    """List recent jobs, newest first."""
    rows = sorted(_jobs.values(), key=lambda r: r["created_at"], reverse=True)[:limit]
    return [MetaAdLibraryJob(**r) for r in rows]
