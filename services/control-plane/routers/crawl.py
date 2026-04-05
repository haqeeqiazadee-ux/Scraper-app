"""Crawl management API endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Pydantic v2 request / response models
# ---------------------------------------------------------------------------


class OutputFormat(str, Enum):
    json = "json"
    csv = "csv"
    markdown = "markdown"
    html = "html"


class CrawlRequest(BaseModel):
    """Parameters for starting a new crawl."""

    model_config = {"from_attributes": True}

    seed_urls: list[str] = Field(..., min_length=1, description="Starting URLs for the crawl")
    max_depth: int = Field(default=3, ge=0, le=100, description="Maximum link-follow depth")
    max_pages: int = Field(default=100, ge=1, le=100_000, description="Maximum pages to crawl")
    url_patterns: list[str] = Field(default_factory=list, description="URL regex patterns to include")
    deny_patterns: list[str] = Field(default_factory=list, description="URL regex patterns to exclude")
    follow_external: bool = Field(default=False, description="Follow links to external domains")
    respect_robots: bool = Field(default=True, description="Honour robots.txt directives")
    output_format: OutputFormat = Field(default=OutputFormat.json, description="Output format for results")
    crawl_delay: float = Field(default=1.0, ge=0, le=60, description="Delay in seconds between requests")
    concurrent_limit: int = Field(default=5, ge=1, le=50, description="Maximum concurrent requests")


class CrawlState(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    stopped = "stopped"
    failed = "failed"


class CrawlStats(BaseModel):
    """Live statistics for an active or finished crawl."""

    model_config = {"from_attributes": True}

    pages_crawled: int = 0
    pages_failed: int = 0
    pages_queued: int = 0
    bytes_downloaded: int = 0
    elapsed_seconds: float = 0.0


class CrawlStatusResponse(BaseModel):
    """Full status snapshot for a crawl."""

    model_config = {"from_attributes": True}

    crawl_id: str
    state: CrawlState
    stats: CrawlStats
    config: dict[str, Any]
    created_at: str
    updated_at: str


class CrawlResultsResponse(BaseModel):
    """Paginated crawl results."""

    model_config = {"from_attributes": True}

    crawl_id: str
    total_items: int
    items: list[dict[str, Any]]
    has_more: bool


# ---------------------------------------------------------------------------
# Module-level CrawlManager — lazy-initialised so the import never fails
# even while packages/core/crawl_manager.py is still being built.
# ---------------------------------------------------------------------------

_crawl_manager: Any = None


def _get_crawl_manager():
    """Return (or create) the singleton CrawlManager instance."""
    global _crawl_manager
    if _crawl_manager is None:
        from packages.core.crawl_manager import CrawlManager

        _crawl_manager = CrawlManager()
    return _crawl_manager


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

crawl_router = APIRouter(prefix="/crawl", tags=["Crawl"])


@crawl_router.post("", status_code=201)
async def start_crawl(request: CrawlRequest) -> dict:
    """Start a new crawl job."""
    manager = _get_crawl_manager()
    logger.info(
        "crawl.start_requested",
        seed_urls=request.seed_urls,
        max_depth=request.max_depth,
        max_pages=request.max_pages,
    )
    from packages.core.crawl_manager import CrawlConfig

    config = CrawlConfig(
        seed_urls=request.seed_urls,
        max_depth=request.max_depth,
        max_pages=request.max_pages,
        url_patterns=request.url_patterns,
        deny_patterns=request.deny_patterns,
        follow_external=request.follow_external,
        respect_robots=request.respect_robots,
        output_format=request.output_format.value,
        crawl_delay=request.crawl_delay,
        concurrent_limit=request.concurrent_limit,
    )
    crawl_id = await manager.start_crawl(config)
    logger.info("crawl.started", crawl_id=crawl_id)
    return {"crawl_id": crawl_id, "status": "running"}


@crawl_router.get("/{crawl_id}")
async def get_crawl_status(crawl_id: str) -> CrawlStatusResponse:
    """Return the current status of a crawl."""
    manager = _get_crawl_manager()
    crawl = await manager.get_crawl(crawl_id)
    if crawl is None:
        raise HTTPException(status_code=404, detail=f"Crawl {crawl_id} not found")

    # CrawlJob is a dataclass — access via attributes
    stats = crawl.stats
    config_dict = {}
    if crawl.config:
        config_dict = {
            "seed_urls": getattr(crawl.config, 'seed_urls', []),
            "max_depth": getattr(crawl.config, 'max_depth', 0),
            "max_pages": getattr(crawl.config, 'max_pages', 0),
        }

    return CrawlStatusResponse(
        crawl_id=crawl.crawl_id,
        state=CrawlState(crawl.state.value if hasattr(crawl.state, 'value') else crawl.state),
        stats=CrawlStats(
            pages_crawled=getattr(stats, 'pages_crawled', 0),
            pages_queued=getattr(stats, 'pages_queued', 0),
            bytes_downloaded=getattr(stats, 'bytes_downloaded', 0),
            elapsed_seconds=getattr(stats, 'elapsed_seconds', 0.0),
        ),
        config=config_dict,
        created_at=crawl.created_at.isoformat() if hasattr(crawl.created_at, 'isoformat') else str(crawl.created_at),
        updated_at=crawl.updated_at.isoformat() if hasattr(crawl.updated_at, 'isoformat') else str(crawl.updated_at),
    )


@crawl_router.get("/{crawl_id}/results")
async def get_crawl_results(
    crawl_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> CrawlResultsResponse:
    """Return paginated results for a completed (or in-progress) crawl."""
    manager = _get_crawl_manager()
    crawl = await manager.get_crawl(crawl_id)
    if crawl is None:
        raise HTTPException(status_code=404, detail=f"Crawl {crawl_id} not found")

    raw_results = await manager.get_results(crawl_id)
    # get_results returns a list of dicts
    all_items = raw_results if isinstance(raw_results, list) else raw_results.get("items", []) if isinstance(raw_results, dict) else []
    total = len(all_items)
    page_items = all_items[offset:offset + limit]
    return CrawlResultsResponse(
        crawl_id=crawl_id,
        total_items=total,
        items=page_items,
        has_more=(offset + limit) < total,
    )


@crawl_router.post("/{crawl_id}/stop")
async def stop_crawl(crawl_id: str) -> dict:
    """Stop a running crawl."""
    manager = _get_crawl_manager()
    crawl = await manager.get_crawl(crawl_id)
    if crawl is None:
        raise HTTPException(status_code=404, detail=f"Crawl {crawl_id} not found")

    state_val = crawl.state.value if hasattr(crawl.state, 'value') else str(crawl.state)
    if state_val in ("stopped", "completed", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Crawl {crawl_id} is already in '{state_val}' state and cannot be stopped",
        )

    result = await manager.stop_crawl(crawl_id)
    logger.info("crawl.stopped", crawl_id=crawl_id)
    return {
        "crawl_id": crawl_id,
        "status": result["status"],
        "message": f"Crawl {crawl_id} has been stopped",
    }
