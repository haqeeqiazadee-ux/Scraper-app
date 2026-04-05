"""Facebook scraping API endpoints."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class GroupScrapeRequest(BaseModel):
    """Parameters for starting a Facebook group scrape."""

    url: str = Field(..., description="Facebook group URL to scrape")
    max_posts: int = Field(default=0, ge=0, description="Max posts to collect (0 = unlimited)")


class GroupScrapeStatus(BaseModel):
    """Status of a group scrape job."""

    job_id: str
    status: str
    posts_found: int = 0
    scroll_count: int = 0


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_facebook_cookies: list[dict] = []
_scrape_jobs: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

facebook_router = APIRouter(prefix="/facebook", tags=["Facebook"])


@facebook_router.post("/cookies", status_code=200)
async def upload_cookies(cookies: list[dict]) -> dict:
    """Upload Facebook cookies for authenticated access.

    Body: JSON array of cookie objects, e.g.:
    [{"name": "c_user", "value": "123", "domain": ".facebook.com"}, ...]
    """
    global _facebook_cookies
    _facebook_cookies = cookies
    logger.info("facebook.cookies_uploaded", cookie_count=len(cookies))
    return {"status": "ok", "cookie_count": len(cookies)}


@facebook_router.post("/group/scrape", status_code=201)
async def scrape_group(request: GroupScrapeRequest) -> dict:
    """Start scraping a Facebook group.

    Body: { url: str, max_posts: int = 0 }
    """
    job_id = str(uuid.uuid4())
    job: dict[str, Any] = {
        "job_id": job_id,
        "status": "running",
        "url": request.url,
        "max_posts": request.max_posts,
        "posts_found": 0,
        "scroll_count": 0,
        "posts": [],
        "error": None,
    }
    _scrape_jobs[job_id] = job

    logger.info(
        "facebook.group_scrape.started",
        job_id=job_id,
        url=request.url,
        max_posts=request.max_posts,
    )

    # Launch scraper in background
    asyncio.create_task(_run_group_scrape(job_id))

    return {"job_id": job_id, "status": "running"}


@facebook_router.get("/group/{job_id}")
async def get_group_scrape_status(job_id: str) -> GroupScrapeStatus:
    """Get scrape progress."""
    job = _scrape_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return GroupScrapeStatus(
        job_id=job["job_id"],
        status=job["status"],
        posts_found=job["posts_found"],
        scroll_count=job["scroll_count"],
    )


@facebook_router.get("/group/{job_id}/results")
async def get_group_results(job_id: str) -> dict:
    """Get extracted posts."""
    job = _scrape_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "job_id": job["job_id"],
        "posts": job["posts"],
        "total": len(job["posts"]),
    }


@facebook_router.get("/group/{job_id}/export")
async def export_group_results(job_id: str):
    """Export results as Excel file."""
    job = _scrape_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if not job["posts"]:
        raise HTTPException(status_code=400, detail="No posts to export")

    try:
        from packages.core.ai_providers.social.facebook_group_scraper import (
            FacebookGroupScraper,
        )

        scraper = FacebookGroupScraper()
        file_path = scraper.export_to_excel(job["posts"], job_id=job_id)
        return FileResponse(
            path=file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"facebook_group_{job_id}.xlsx",
        )
    except ImportError:
        # Fallback: generate a simple Excel file with openpyxl
        import tempfile

        try:
            import openpyxl
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="Excel export requires openpyxl. Install it with: pip install openpyxl",
            )

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Group Posts"

        # Headers
        headers = [
            "post_id", "author_name", "text", "timestamp",
            "like_count", "comment_count", "share_count",
            "image_urls", "post_url", "price", "location",
        ]
        ws.append(headers)

        for post in job["posts"]:
            row = []
            for h in headers:
                val = post.get(h, "")
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                row.append(val)
            ws.append(row)

        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        wb.save(tmp.name)
        tmp.close()

        return FileResponse(
            path=tmp.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"facebook_group_{job_id}.xlsx",
        )


# ---------------------------------------------------------------------------
# Background scrape task
# ---------------------------------------------------------------------------


async def _run_group_scrape(job_id: str) -> None:
    """Run the Facebook group scrape in the background."""
    job = _scrape_jobs.get(job_id)
    if job is None:
        return

    try:
        from packages.core.ai_providers.social.facebook_group_scraper import (
            FacebookGroupScraper,
        )

        scraper = FacebookGroupScraper(cookies=_facebook_cookies)
        async for update in scraper.scrape(
            url=job["url"],
            max_posts=job["max_posts"],
        ):
            job["posts_found"] = update.get("posts_found", job["posts_found"])
            job["scroll_count"] = update.get("scroll_count", job["scroll_count"])
            job["posts"] = update.get("posts", job["posts"])

        job["status"] = "completed"
        logger.info(
            "facebook.group_scrape.completed",
            job_id=job_id,
            posts_found=job["posts_found"],
        )
    except ImportError:
        # FacebookGroupScraper not yet available — use extractor directly on
        # a single page fetch as a minimal fallback.
        try:
            from packages.core.ai_providers.social.facebook import FacebookExtractor

            extractor = FacebookExtractor()
            # Minimal: the actual scraping infrastructure is not available,
            # mark as failed with helpful message
            job["status"] = "failed"
            job["error"] = (
                "FacebookGroupScraper module not found. "
                "The extractor is available but the full scraping pipeline "
                "(browser automation + scrolling) is not yet implemented."
            )
            logger.warning("facebook.group_scrape.no_scraper", job_id=job_id)
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = str(exc)
            logger.error("facebook.group_scrape.failed", job_id=job_id, error=str(exc))
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
        logger.error("facebook.group_scrape.failed", job_id=job_id, error=str(exc))
