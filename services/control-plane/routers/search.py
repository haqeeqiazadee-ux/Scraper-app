"""Search API endpoint — search the web and scrape results."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.control_plane.routers.crawl import OutputFormat

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Pydantic v2 request / response models
# ---------------------------------------------------------------------------

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_SCRAPE_SEMAPHORE_LIMIT = 3


class SearchRequest(BaseModel):
    """Parameters for a search-and-scrape request."""

    model_config = {"from_attributes": True}

    query: str = Field(..., min_length=1, max_length=400, description="Natural language search query")
    max_results: int = Field(default=5, ge=1, le=20, description="Number of search results to scrape")
    output_format: OutputFormat = Field(default=OutputFormat.json, description="Output format for scraped data")


class SearchResultItem(BaseModel):
    """A single scraped search result."""

    model_config = {"from_attributes": True}

    url: str
    title: str = ""
    status: str = "success"
    extracted_data: list[dict[str, Any]] = Field(default_factory=list)
    item_count: int = 0
    error: str | None = None


class SearchResponse(BaseModel):
    """Aggregated response for the search endpoint."""

    model_config = {"from_attributes": True}

    query: str
    results: list[SearchResultItem]
    total_results: int
    search_provider: str = "brave"


# ---------------------------------------------------------------------------
# Lazy worker helper
# ---------------------------------------------------------------------------

_http_worker: Any = None


def _get_http_worker():
    """Return (or create) a reusable HttpWorker instance."""
    global _http_worker
    if _http_worker is None:
        from services.worker_http.worker import HttpWorker

        _http_worker = HttpWorker()
    return _http_worker


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _brave_search(query: str, count: int, api_key: str) -> list[dict[str, str]]:
    """Call Brave Search API and return a list of {url, title} dicts."""
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": min(count, 20)}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(BRAVE_SEARCH_URL, headers=headers, params=params)

    if resp.status_code != 200:
        logger.error(
            "brave_search.failed",
            status_code=resp.status_code,
            body=resp.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail=f"Brave Search API returned {resp.status_code}",
        )

    data = resp.json()
    web_results = data.get("web", {}).get("results", [])
    return [
        {"url": r["url"], "title": r.get("title", "")}
        for r in web_results
        if r.get("url")
    ]


async def _scrape_url(url: str, semaphore: asyncio.Semaphore) -> dict[str, Any]:
    """Scrape a single URL through the HttpWorker pipeline."""
    async with semaphore:
        worker = _get_http_worker()
        task = {
            "url": url,
            "tenant_id": "search",
            "paginate": False,
        }
        try:
            result = await worker.process_task(task)
            return result
        except Exception as exc:
            logger.error("search.scrape_error", url=url, error=str(exc))
            return {
                "status": "failed",
                "error": str(exc),
                "extracted_data": [],
                "item_count": 0,
            }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

search_router = APIRouter(prefix="/search", tags=["Search"])


@search_router.post("", status_code=200)
async def search_and_scrape(request: SearchRequest) -> SearchResponse:
    """Search the web via Brave and scrape the top results."""
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "Brave Search API key is not configured. "
                "Set the BRAVE_SEARCH_API_KEY environment variable. "
                "Get a free key at https://brave.com/search/api/ (2 000 queries/month)."
            ),
        )

    logger.info("search.start", query=request.query, max_results=request.max_results)

    # Step 1 — search
    search_hits = await _brave_search(request.query, request.max_results, api_key)
    if not search_hits:
        return SearchResponse(
            query=request.query,
            results=[],
            total_results=0,
        )

    # Step 2 — scrape each URL concurrently (bounded by semaphore)
    semaphore = asyncio.Semaphore(_SCRAPE_SEMAPHORE_LIMIT)
    scrape_coros = [_scrape_url(hit["url"], semaphore) for hit in search_hits]
    raw_results = await asyncio.gather(*scrape_coros, return_exceptions=True)

    # Step 3 — aggregate
    items: list[SearchResultItem] = []
    for hit, raw in zip(search_hits, raw_results):
        if isinstance(raw, BaseException):
            items.append(
                SearchResultItem(
                    url=hit["url"],
                    title=hit.get("title", ""),
                    status="failed",
                    error=str(raw),
                )
            )
            continue

        extracted = raw.get("extracted_data", [])
        items.append(
            SearchResultItem(
                url=hit["url"],
                title=hit.get("title", ""),
                status=raw.get("status", "success"),
                extracted_data=extracted,
                item_count=len(extracted) if isinstance(extracted, list) else 0,
                error=raw.get("error"),
            )
        )

    logger.info(
        "search.complete",
        query=request.query,
        results=len(items),
        successful=sum(1 for i in items if i.status == "success"),
    )

    return SearchResponse(
        query=request.query,
        results=items,
        total_results=len(items),
    )
