"""Batch Processing — Accept lists of items, return bulk results.

POST /batch — Process a list of URLs/ASINs/queries concurrently
GET /batch/{batch_id} — Poll async batch status

Optimizations:
- Amazon ASINs -> single Keepa batch call (up to 100)
- Concurrent processing with configurable parallelism
- <10 items: synchronous response
- >=10 items: async job with webhook callback
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any, Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from services.control_plane.dependencies import get_session, get_database, get_tenant_id

logger = structlog.get_logger(__name__)
batch_router = APIRouter(tags=["Batch"])

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
_batch_jobs: dict[str, dict[str, Any]] = {}  # In-memory store for async batch jobs


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class BatchRequest(BaseModel):
    items: list[str] = Field(min_length=1, max_length=500)
    intent: str = "products"
    schema_fields: dict[str, Any] | None = Field(default=None, alias="schema")
    cookies: list[dict[str, Any]] | None = None
    concurrency: int = Field(default=5, ge=1, le=10)
    webhook_url: str | None = None

    model_config = {"populate_by_name": True}


class BatchItemResult(BaseModel):
    input: str
    status: str = "pending"  # success, failed, skipped
    item_count: int = 0
    data: list[dict[str, Any]] = []
    error: str | None = None
    duration_ms: int = 0


class BatchResponse(BaseModel):
    batch_id: str
    status: str  # completed, processing, failed
    total: int
    completed: int = 0
    failed: int = 0
    results: list[BatchItemResult] = []
    duration_ms: int = 0
    webhook_url: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_url(item: str) -> bool:
    """Return True if the item looks like a URL rather than a search query."""
    stripped = item.strip()
    if stripped.startswith(("http://", "https://")):
        return True
    # Contains a dot before any space (e.g., "example.com/page")
    space_idx = stripped.find(" ")
    dot_idx = stripped.find(".")
    if dot_idx != -1 and (space_idx == -1 or dot_idx < space_idx):
        if "/" in stripped or " " not in stripped[:dot_idx]:
            return True
    return False


# ---------------------------------------------------------------------------
# Single-item processing via smart_scrape delegation
# ---------------------------------------------------------------------------


async def _process_single_item(
    item: str,
    intent: str,
    schema: dict[str, Any] | None,
    cookies: list[dict[str, Any]] | None,
    tenant_id: str,
    session: AsyncSession,
) -> BatchItemResult:
    """Process a single batch item via smart scrape logic."""
    start = time.time()
    try:
        if _is_url(item):
            url = item if item.startswith("http") else f"https://{item}"
            # Use smart scrape's _handle_url_scrape directly
            from services.control_plane.routers.smart_scrape import (
                _handle_url_scrape,
                SmartScrapeRequest,
            )

            steps: list[dict[str, Any]] = []
            req = SmartScrapeRequest(
                target=url, intent=intent, schema=schema,
            )
            result = await _handle_url_scrape(
                url=url,
                tenant_id=tenant_id,
                cookies=cookies,
                schema_fields=schema,
                max_pages=1,
                max_depth=0,
                output_format="json",
                steps=steps,
                op_start=start,
                session=session,
                request=req,
            )
            elapsed = int((time.time() - start) * 1000)
            extracted = result.get("extracted_data", [])
            return BatchItemResult(
                input=item,
                status="success",
                item_count=len(extracted),
                data=extracted[:50],
                duration_ms=elapsed,
            )
        else:
            # Search query — use smart scrape's _handle_search
            from services.control_plane.routers.smart_scrape import _handle_search

            steps: list[dict[str, Any]] = []
            result = await _handle_search(
                query=item,
                max_results=5,
                steps=steps,
                op_start=start,
            )
            elapsed = int((time.time() - start) * 1000)
            extracted = result.get("extracted_data", [])
            return BatchItemResult(
                input=item,
                status=result.get("status", "success"),
                item_count=len(extracted),
                data=extracted[:50],
                duration_ms=elapsed,
            )
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        logger.warning("batch.item.failed", item=item, error=str(e))
        return BatchItemResult(
            input=item,
            status="failed",
            error=str(e)[:200],
            duration_ms=elapsed,
        )


# ---------------------------------------------------------------------------
# Optimized Keepa batch for Amazon ASINs
# ---------------------------------------------------------------------------


async def _process_keepa_batch(
    asins: list[str], domain: str = "US"
) -> list[BatchItemResult]:
    """Process all ASINs in a single Keepa API call."""
    start = time.time()
    try:
        from services.control_plane.routers.keepa import _get_keepa

        keepa = _get_keepa()
        products = await keepa.query_products(
            asins=asins[:100],
            domain=domain,
            include_rating=True,
            stats_days=90,
            history_days=30,
        )

        # Map each ASIN to its product data
        products_by_asin: dict[str, dict[str, Any]] = {}
        for p in products if isinstance(products, list) else []:
            p_asin = p.get("asin", "")
            if p_asin:
                products_by_asin[p_asin] = p

        batch_results: list[BatchItemResult] = []
        for asin in asins:
            elapsed = int((time.time() - start) * 1000)
            if asin in products_by_asin:
                p = products_by_asin[asin]
                batch_results.append(
                    BatchItemResult(
                        input=asin,
                        status="success",
                        item_count=1,
                        data=[
                            {
                                "name": p.get("name", ""),
                                "price": p.get("price", ""),
                                "asin": asin,
                                "brand": p.get("brand", ""),
                                "rating": p.get("rating", ""),
                                "reviews_count": p.get("reviews_count", ""),
                                "image_url": p.get("image_url", ""),
                                "product_url": p.get("product_url", ""),
                                "sales_rank": p.get("sales_rank", 0),
                                "category": p.get("category", ""),
                                "source": "keepa",
                            }
                        ],
                        duration_ms=elapsed,
                    )
                )
            else:
                batch_results.append(
                    BatchItemResult(
                        input=asin,
                        status="failed",
                        error="Not found in Keepa",
                        duration_ms=elapsed,
                    )
                )
        return batch_results
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        logger.error("batch.keepa.failed", error=str(e))
        return [
            BatchItemResult(
                input=asin,
                status="failed",
                error=f"Keepa batch error: {str(e)[:150]}",
                duration_ms=elapsed,
            )
            for asin in asins
        ]


# ---------------------------------------------------------------------------
# Async background batch runner
# ---------------------------------------------------------------------------


async def _run_async_batch(
    batch_id: str,
    items: list[str],
    request: BatchRequest,
    tenant_id: str,
) -> None:
    """Process items concurrently in background, updating _batch_jobs as we go."""
    start = time.time()
    job = _batch_jobs.get(batch_id)
    if job is None:
        return

    sem = asyncio.Semaphore(request.concurrency)

    async def _run_one(item: str) -> BatchItemResult:
        async with sem:
            # Each background item needs its own session
            db = get_database()
            async with db.session() as bg_session:
                try:
                    result = await _process_single_item(
                        item,
                        request.intent,
                        request.schema_fields,
                        request.cookies,
                        tenant_id,
                        bg_session,
                    )
                    await bg_session.commit()
                    return result
                except Exception:
                    await bg_session.rollback()
                    raise

    try:
        tasks = [_run_one(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results: list[BatchItemResult] = []
        completed_count = 0
        failed_count = 0
        for item, res in zip(items, results):
            if isinstance(res, BaseException):
                failed_count += 1
                final_results.append(
                    BatchItemResult(
                        input=item,
                        status="failed",
                        error=str(res)[:200],
                    )
                )
            else:
                if res.status == "success":
                    completed_count += 1
                else:
                    failed_count += 1
                final_results.append(res)

        elapsed = int((time.time() - start) * 1000)
        job.update(
            {
                "status": "completed",
                "completed": completed_count,
                "failed": failed_count,
                "results": final_results,
                "duration_ms": elapsed,
            }
        )

        # Send webhook if configured
        if request.webhook_url:
            await _send_webhook(
                request.webhook_url,
                BatchResponse(
                    batch_id=batch_id,
                    status="completed",
                    total=len(items),
                    completed=completed_count,
                    failed=failed_count,
                    results=final_results,
                    duration_ms=elapsed,
                    webhook_url=request.webhook_url,
                ),
            )
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        logger.error("batch.async.failed", batch_id=batch_id, error=str(e))
        job.update(
            {
                "status": "failed",
                "duration_ms": elapsed,
            }
        )


async def _send_webhook(url: str, response: BatchResponse) -> None:
    """POST batch results to the configured webhook URL."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(
                url,
                json=response.model_dump(mode="json"),
                headers={"Content-Type": "application/json"},
            )
        logger.info("batch.webhook.sent", url=url, batch_id=response.batch_id)
    except Exception as e:
        logger.warning("batch.webhook.failed", url=url, error=str(e))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@batch_router.post("/batch", response_model=BatchResponse)
async def process_batch(
    request: BatchRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> BatchResponse:
    """Process a list of URLs/ASINs/queries concurrently.

    - All ASINs (<=100): optimized single Keepa batch call
    - <10 items: synchronous response
    - >=10 items: async job (poll via GET /batch/{batch_id})
    """
    batch_id = f"batch_{uuid4().hex[:16]}"
    items = [i.strip() for i in request.items if i.strip()]
    start = time.time()

    if not items:
        raise HTTPException(status_code=400, detail="No valid items provided")

    logger.info(
        "batch.start",
        batch_id=batch_id,
        item_count=len(items),
        intent=request.intent,
    )

    # Optimization: detect if ALL items are Amazon ASINs
    all_asins = all(ASIN_RE.match(item) for item in items)

    if all_asins and len(items) <= 100:
        # Single Keepa batch call — most efficient path
        results = await _process_keepa_batch(items)
        elapsed = int((time.time() - start) * 1000)
        completed = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "failed")
        logger.info(
            "batch.keepa.complete",
            batch_id=batch_id,
            completed=completed,
            failed=failed,
            duration_ms=elapsed,
        )
        resp = BatchResponse(
            batch_id=batch_id,
            status="completed",
            total=len(items),
            completed=completed,
            failed=failed,
            results=results,
            duration_ms=elapsed,
        )
        _batch_jobs[batch_id] = {
            "status": "completed", "total": len(items),
            "completed": completed, "failed": failed,
            "results": [r.model_dump() for r in results],
            "duration_ms": elapsed,
        }
        return resp

    # Store sync batch results for polling
    _batch_jobs[batch_id] = {
        "status": "processing",
        "total": len(items),
        "completed": 0,
        "failed": 0,
        "results": [],
        "webhook_url": request.webhook_url,
    }

    # If <10 items: process synchronously (each gets own DB session)
    if len(items) < 10:
        sem = asyncio.Semaphore(request.concurrency)
        db = get_database()

        async def _run(item: str) -> BatchItemResult:
            async with sem:
                async with db.session() as item_session:
                    return await _process_single_item(
                        item,
                        request.intent,
                        request.schema_fields,
                        request.cookies,
                        tenant_id,
                        item_session,
                    )

        tasks = [_run(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results: list[BatchItemResult] = []
        for item, res in zip(items, results):
            if isinstance(res, BaseException):
                final_results.append(
                    BatchItemResult(
                        input=item,
                        status="failed",
                        error=str(res)[:200],
                    )
                )
            else:
                final_results.append(res)

        elapsed = int((time.time() - start) * 1000)
        completed = sum(1 for r in final_results if r.status == "success")
        failed = sum(1 for r in final_results if r.status == "failed")
        logger.info(
            "batch.sync.complete",
            batch_id=batch_id,
            completed=completed,
            failed=failed,
            duration_ms=elapsed,
        )
        resp = BatchResponse(
            batch_id=batch_id,
            status="completed",
            total=len(items),
            completed=completed,
            failed=failed,
            results=final_results,
            duration_ms=elapsed,
        )
        # Store for polling
        _batch_jobs[batch_id] = {
            "status": "completed",
            "total": len(items),
            "completed": completed,
            "failed": failed,
            "results": [r.model_dump() for r in final_results],
            "duration_ms": elapsed,
            "webhook_url": request.webhook_url,
        }
        return resp

    # >=10 items: async job — return immediately, process in background
    _batch_jobs[batch_id] = {
        "status": "processing",
        "total": len(items),
        "completed": 0,
        "failed": 0,
        "results": [],
        "duration_ms": 0,
        "webhook_url": request.webhook_url,
    }
    asyncio.create_task(
        _run_async_batch(batch_id, items, request, tenant_id)
    )

    logger.info(
        "batch.async.started",
        batch_id=batch_id,
        item_count=len(items),
    )
    return BatchResponse(
        batch_id=batch_id,
        status="processing",
        total=len(items),
        webhook_url=request.webhook_url,
    )


@batch_router.get("/batch/{batch_id}", response_model=BatchResponse)
async def get_batch_status(batch_id: str) -> BatchResponse:
    """Poll the status of an async batch job."""
    job = _batch_jobs.get(batch_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch not found")

    results = job.get("results", [])
    return BatchResponse(
        batch_id=batch_id,
        status=job["status"],
        total=job["total"],
        completed=job.get("completed", 0),
        failed=job.get("failed", 0),
        results=results if isinstance(results, list) else [],
        duration_ms=job.get("duration_ms", 0),
        webhook_url=job.get("webhook_url"),
    )
