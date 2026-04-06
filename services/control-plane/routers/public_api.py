"""Zero Checksum Public API router — /v1 endpoints.

Provides scrape, crawl, search, extract, jobs, webhooks, usage, and account
endpoints. All routes require API-key authentication via ``require_api_key``.
"""

from __future__ import annotations

import asyncio
import hashlib
import secrets
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts.public_api import (
    AccountInfo,
    CrawlRequest,
    ExtractRequest,
    JobResults,
    JobStatus,
    ScrapeRequest,
    ScrapeResult,
    SearchRequest,
    UsageRecord,
    UsageResponse,
    WebhookRegistration,
)
from packages.core.storage.repositories_public_api import (
    AsyncJobRepository,
    AuditLogRepository,
    IdempotencyRepository,
    ApiKeyRepository,
)
from services.control_plane.dependencies import get_session
from services.control_plane.middleware.api_key_auth import ApiKeyContext, require_api_key
from services.control_plane.utils.response import (
    accepted_response,
    error_response,
    generate_request_id,
    success_response,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Lazy worker / manager singletons — avoids circular imports
# ---------------------------------------------------------------------------

_http_worker: Any = None
_crawl_manager: Any = None


def _get_http_worker():
    """Return (or create) a reusable HttpWorker instance."""
    global _http_worker
    if _http_worker is None:
        from services.worker_http.worker import HttpWorker

        _http_worker = HttpWorker()
    return _http_worker


def _get_crawl_manager():
    """Return (or create) the singleton CrawlManager instance."""
    global _crawl_manager
    if _crawl_manager is None:
        from packages.core.crawl_manager import CrawlManager

        _crawl_manager = CrawlManager()
    return _crawl_manager


# ---------------------------------------------------------------------------
# In-memory webhook registry (per-process; replace with DB table later)
# ---------------------------------------------------------------------------

_webhook_registry: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _gen_job_id() -> str:
    return str(uuid4())


async def _log_request(
    audit_repo: AuditLogRepository,
    tenant_id: str,
    api_key_id: str,
    request: Request,
    endpoint: str,
    idempotency_key: Optional[str] = None,
) -> str:
    """Create an audit log entry at the start of a request.  Returns request_id."""
    request_id = getattr(request.state, "request_id", generate_request_id())
    await audit_repo.create(
        tenant_id=tenant_id,
        request_id=request_id,
        api_key_id=api_key_id,
        method=request.method,
        endpoint=endpoint,
        idempotency_key=idempotency_key,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    return request_id


async def _finalise_audit(
    audit_repo: AuditLogRepository,
    request_id: str,
    tenant_id: str,
    status_code: int,
    credits_used: int,
    duration_ms: int,
    error_code: Optional[str] = None,
) -> None:
    """Update the audit log entry when the request finishes."""
    await audit_repo.update_response(
        request_id=request_id,
        tenant_id=tenant_id,
        status_code=status_code,
        credits_used=credits_used,
        duration_ms=duration_ms,
        error_code=error_code,
        completed_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

public_api_router = APIRouter(prefix="/v1", tags=["Public API"])


# ===========================  1. POST /v1/scrape  ===========================


@public_api_router.post("/scrape", status_code=200)
async def scrape(
    body: ScrapeRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Scrape a single URL synchronously, or submit an async job."""
    start = time.time()
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    job_repo = AsyncJobRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/scrape", idempotency_key,
    )
    request.state.request_id = request_id
    request.state.idempotency_key = idempotency_key
    request.state.start_time = start

    url_str = str(body.url)
    # Determine lane based on wait_for (browser needed for JS rendering)
    use_browser = body.wait_for is not None
    credits = 5 if use_browser else 1

    logger.info(
        "public_api.scrape.start",
        request_id=request_id,
        url=url_str,
        async_mode=body.async_mode,
        use_browser=use_browser,
    )

    # ----- Async mode -----
    if body.async_mode:
        job_id = _gen_job_id()
        await job_repo.create(
            tenant_id=tenant_id,
            id=job_id,
            request_id=request_id,
            job_type="scrape",
            status="pending",
            input_params={
                "url": url_str,
                "formats": body.formats,
                "wait_for": body.wait_for,
                "timeout_ms": body.timeout_ms,
                "headers": body.headers,
            },
            webhook_url=str(body.webhook_url) if body.webhook_url else None,
        )
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=202, credits_used=0, duration_ms=duration_ms,
        )
        logger.info("public_api.scrape.accepted", request_id=request_id, job_id=job_id)
        return accepted_response(job_id=job_id, request=request, credits_used=0)

    # ----- Sync mode -----
    worker = _get_http_worker()
    task_payload: dict[str, Any] = {
        "url": url_str,
        "tenant_id": tenant_id,
        "paginate": False,
    }
    if body.headers:
        task_payload["headers"] = body.headers

    try:
        result = await worker.process_task(task_payload)
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="SCRAPE_FAILED",
        )
        logger.error("public_api.scrape.failed", request_id=request_id, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Scrape failed: {exc}") from exc

    if result.get("status") == "failed":
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="SCRAPE_FAILED",
        )
        raise HTTPException(
            status_code=502,
            detail=f"Scrape failed: {result.get('error', 'unknown error')}",
        )

    extracted = result.get("extracted_data", [])
    scrape_result = ScrapeResult(
        url=url_str,
        extracted_data=extracted,
        markdown=result.get("markdown"),
        html=result.get("html_snapshot"),
        item_count=len(extracted) if isinstance(extracted, list) else 0,
        confidence=result.get("confidence", 1.0),
        extraction_method=result.get("extraction_method", "http_worker"),
    )

    duration_ms = int((time.time() - start) * 1000)
    await _finalise_audit(
        audit_repo, request_id, tenant_id,
        status_code=200, credits_used=credits, duration_ms=duration_ms,
    )
    logger.info(
        "public_api.scrape.complete",
        request_id=request_id,
        item_count=scrape_result.item_count,
        credits=credits,
    )
    return success_response(
        data=scrape_result.model_dump(),
        request=request,
        credits_used=credits,
    )


# ===========================  2. POST /v1/crawl  ============================


@public_api_router.post("/crawl", status_code=202)
async def crawl(
    body: CrawlRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Start an asynchronous crawl job (always returns 202)."""
    start = time.time()
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    job_repo = AsyncJobRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/crawl", idempotency_key,
    )
    request.state.request_id = request_id
    request.state.idempotency_key = idempotency_key
    request.state.start_time = start

    url_str = str(body.url)
    job_id = _gen_job_id()

    logger.info(
        "public_api.crawl.start",
        request_id=request_id,
        url=url_str,
        max_depth=body.max_depth,
        max_pages=body.max_pages,
    )

    await job_repo.create(
        tenant_id=tenant_id,
        id=job_id,
        request_id=request_id,
        job_type="crawl",
        status="pending",
        input_params={
            "url": url_str,
            "max_depth": body.max_depth,
            "max_pages": body.max_pages,
            "include_patterns": body.include_patterns,
            "exclude_patterns": body.exclude_patterns,
            "formats": body.formats,
        },
        webhook_url=str(body.webhook_url) if body.webhook_url else None,
    )

    # Fire-and-forget crawl via CrawlManager
    try:
        from packages.core.crawl_manager import CrawlConfig

        manager = _get_crawl_manager()
        config = CrawlConfig(
            seed_urls=[url_str],
            max_depth=body.max_depth,
            max_pages=body.max_pages,
            url_patterns=body.include_patterns,
            deny_patterns=body.exclude_patterns,
        )
        crawl_id = await manager.start_crawl(config)
        # Store the crawl_id in the job progress for correlation
        await job_repo.update_progress(
            job_id, tenant_id, {"crawl_id": crawl_id},
        )
        await job_repo.update_status(
            job_id, tenant_id, status="running", started_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error("public_api.crawl.manager_error", request_id=request_id, error=str(exc))
        await job_repo.update_status(
            job_id, tenant_id, status="failed", error=str(exc),
            completed_at=datetime.now(timezone.utc),
        )

    duration_ms = int((time.time() - start) * 1000)
    await _finalise_audit(
        audit_repo, request_id, tenant_id,
        status_code=202, credits_used=0, duration_ms=duration_ms,
    )
    logger.info("public_api.crawl.accepted", request_id=request_id, job_id=job_id)
    return accepted_response(job_id=job_id, request=request, credits_used=0)


# ===========================  3. POST /v1/search  ===========================


@public_api_router.post("/search", status_code=200)
async def search(
    body: SearchRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Search the web and optionally scrape top results (synchronous)."""
    start = time.time()
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/search", idempotency_key,
    )
    request.state.request_id = request_id
    request.state.idempotency_key = idempotency_key
    request.state.start_time = start

    logger.info(
        "public_api.search.start",
        request_id=request_id,
        query=body.query,
        max_results=body.max_results,
    )

    # Delegate to existing Serper search logic
    import os
    api_key = os.environ.get("SERPER_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Search is not available: SERPER_API_KEY is not configured.",
        )

    from services.control_plane.routers.search import _serper_search, _scrape_url

    search_hits = await _serper_search(body.query, body.max_results, api_key)
    if not search_hits:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=0, duration_ms=duration_ms,
        )
        return success_response(
            data={"query": body.query, "results": [], "total_results": 0},
            request=request,
            credits_used=0,
        )

    # Optionally scrape each result
    results_data: list[dict[str, Any]] = []
    credits = 0

    if body.scrape_results:
        semaphore = asyncio.Semaphore(3)
        scrape_coros = [_scrape_url(hit["url"], semaphore) for hit in search_hits]
        raw_results = await asyncio.gather(*scrape_coros, return_exceptions=True)

        for hit, raw in zip(search_hits, raw_results):
            if isinstance(raw, BaseException):
                results_data.append({
                    "url": hit["url"],
                    "title": hit.get("title", ""),
                    "status": "failed",
                    "error": str(raw),
                    "extracted_data": [],
                    "item_count": 0,
                })
            else:
                extracted = raw.get("extracted_data", [])
                results_data.append({
                    "url": hit["url"],
                    "title": hit.get("title", ""),
                    "status": raw.get("status", "success"),
                    "extracted_data": extracted,
                    "item_count": len(extracted) if isinstance(extracted, list) else 0,
                    "error": raw.get("error"),
                })
                if raw.get("status") != "failed":
                    credits += 1
    else:
        results_data = [
            {"url": hit["url"], "title": hit.get("title", ""), "status": "success"}
            for hit in search_hits
        ]
        credits = 1  # Search-only cost

    duration_ms = int((time.time() - start) * 1000)
    await _finalise_audit(
        audit_repo, request_id, tenant_id,
        status_code=200, credits_used=credits, duration_ms=duration_ms,
    )
    logger.info(
        "public_api.search.complete",
        request_id=request_id,
        total_results=len(results_data),
        credits=credits,
    )
    return success_response(
        data={
            "query": body.query,
            "results": results_data,
            "total_results": len(results_data),
            "search_provider": "serper",
        },
        request=request,
        credits_used=credits,
    )


# ==========================  4. POST /v1/extract  ===========================


@public_api_router.post("/extract", status_code=200)
async def extract(
    body: ExtractRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Extract structured data from a URL using a JSON schema (synchronous)."""
    start = time.time()
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/extract", idempotency_key,
    )
    request.state.request_id = request_id
    request.state.idempotency_key = idempotency_key
    request.state.start_time = start

    url_str = str(body.url)
    credits = 2

    logger.info(
        "public_api.extract.start",
        request_id=request_id,
        url=url_str,
        schema_fields=list(body.schema.get("properties", body.schema).keys()),
    )

    worker = _get_http_worker()
    task_payload: dict[str, Any] = {
        "url": url_str,
        "tenant_id": tenant_id,
        "paginate": False,
    }

    try:
        result = await worker.process_task(task_payload)
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="EXTRACT_FAILED",
        )
        logger.error("public_api.extract.failed", request_id=request_id, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {exc}") from exc

    if result.get("status") == "failed":
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="EXTRACT_FAILED",
        )
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch URL: {result.get('error', 'unknown error')}",
        )

    # Delegate to existing schema-matching logic
    from services.control_plane.routers.extract import _match_to_schema

    raw_items = result.get("extracted_data", [])
    html_snapshot = result.get("html_snapshot", "")
    extraction_method = "http_worker+deterministic"

    if not raw_items and not html_snapshot:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=credits, duration_ms=duration_ms,
        )
        return success_response(
            data={
                "url": url_str,
                "extracted_data": {},
                "confidence": 0.0,
                "extraction_method": extraction_method,
            },
            request=request,
            credits_used=credits,
        )

    matched_data, confidence = _match_to_schema(
        raw_items, body.schema, html=html_snapshot, url=url_str,
    )
    if html_snapshot:
        extraction_method = "http_worker+deterministic+html_parser"

    duration_ms = int((time.time() - start) * 1000)
    await _finalise_audit(
        audit_repo, request_id, tenant_id,
        status_code=200, credits_used=credits, duration_ms=duration_ms,
    )
    logger.info(
        "public_api.extract.complete",
        request_id=request_id,
        confidence=confidence,
        matched_fields=len(matched_data),
    )
    return success_response(
        data={
            "url": url_str,
            "extracted_data": matched_data,
            "confidence": confidence,
            "extraction_method": extraction_method,
        },
        request=request,
        credits_used=credits,
    )


# =======================  5. GET /v1/jobs/{job_id}  =========================


@public_api_router.get("/jobs/{job_id}", status_code=200)
async def get_job_status(
    job_id: str,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Poll the status of an async job."""
    request.state.start_time = time.time()
    tenant_id = api_ctx.tenant_id
    job_repo = AsyncJobRepository(session)

    job = await job_repo.get(job_id, tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job_status = JobStatus(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )

    logger.info(
        "public_api.job.status",
        job_id=job_id,
        status=job.status,
        tenant_id=tenant_id,
    )
    return success_response(
        data=job_status.model_dump(mode="json"),
        request=request,
        credits_used=0,
    )


# ====================  6. GET /v1/jobs/{job_id}/results  ====================


@public_api_router.get("/jobs/{job_id}/results", status_code=200)
async def get_job_results(
    job_id: str,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Retrieve paginated results for a completed async job."""
    request.state.start_time = time.time()
    tenant_id = api_ctx.tenant_id
    job_repo = AsyncJobRepository(session)

    job = await job_repo.get(job_id, tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status not in ("completed", "running"):
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is in '{job.status}' state; results not available yet.",
        )

    result_data = job.result_data or []
    if isinstance(result_data, dict):
        result_data = result_data.get("items", [])

    total = len(result_data)
    page_items = result_data[offset: offset + limit]

    job_results = JobResults(
        job_id=job.id,
        items=page_items,
        total_items=total,
        has_more=(offset + limit) < total,
    )

    logger.info(
        "public_api.job.results",
        job_id=job_id,
        total=total,
        returned=len(page_items),
    )
    return success_response(
        data=job_results.model_dump(mode="json"),
        request=request,
        credits_used=0,
    )


# ========================  7. POST /v1/webhooks  ============================


@public_api_router.post("/webhooks", status_code=201)
async def register_webhook(
    body: WebhookRegistration,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Register a webhook endpoint for async job notifications."""
    request.state.start_time = time.time()
    tenant_id = api_ctx.tenant_id

    webhook_secret = body.secret or ("whsec_" + secrets.token_hex(16))
    webhook_id = str(uuid4())

    _webhook_registry[webhook_id] = {
        "id": webhook_id,
        "tenant_id": tenant_id,
        "url": str(body.url),
        "events": body.events,
        "secret": webhook_secret,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "public_api.webhook.registered",
        webhook_id=webhook_id,
        url=str(body.url),
        events=body.events,
        tenant_id=tenant_id,
    )
    return success_response(
        data={
            "webhook_id": webhook_id,
            "url": str(body.url),
            "events": body.events,
            "secret": webhook_secret,
        },
        request=request,
        credits_used=0,
    )


# ===========================  8. GET /v1/usage  =============================


@public_api_router.get("/usage", status_code=200)
async def get_usage(
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    start_date: date = Query(default=None, description="Start of period (YYYY-MM-DD)"),
    end_date: date = Query(default=None, description="End of period (YYYY-MM-DD)"),
    request_id: Optional[str] = Query(default=None, description="Filter by request ID"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Return usage records for the authenticated tenant."""
    request.state.start_time = time.time()
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)

    # Default: last 30 days
    now = datetime.now(timezone.utc)
    period_end = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc) if end_date else now
    period_start = (
        datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        if start_date
        else (now - timedelta(days=30))
    )

    # Single request lookup
    if request_id:
        record = await audit_repo.get_by_request_id(request_id, tenant_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
        usage_record = UsageRecord(
            request_id=record.request_id,
            endpoint=record.endpoint,
            credits_used=record.credits_used,
            timestamp=record.created_at,
        )
        return success_response(
            data=UsageResponse(
                total_credits_used=record.credits_used,
                period_start=record.created_at.date(),
                period_end=record.created_at.date(),
                records=[usage_record],
            ).model_dump(mode="json"),
            request=request,
            credits_used=0,
        )

    records, total_count = await audit_repo.query_usage(
        tenant_id=tenant_id,
        start=period_start,
        end=period_end,
        limit=limit,
        offset=offset,
    )

    usage_records = [
        UsageRecord(
            request_id=r.request_id,
            endpoint=r.endpoint,
            credits_used=r.credits_used,
            timestamp=r.created_at,
        )
        for r in records
    ]
    total_credits = sum(r.credits_used for r in records)

    logger.info(
        "public_api.usage.query",
        tenant_id=tenant_id,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        record_count=len(usage_records),
    )
    return success_response(
        data=UsageResponse(
            total_credits_used=total_credits,
            period_start=period_start.date(),
            period_end=period_end.date(),
            records=usage_records,
        ).model_dump(mode="json"),
        request=request,
        credits_used=0,
    )


# ==========================  9. GET /v1/account  ============================


@public_api_router.get("/account", status_code=200)
async def get_account(
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Return account info for the authenticated tenant."""
    request.state.start_time = time.time()
    tenant_id = api_ctx.tenant_id
    key_repo = ApiKeyRepository(session)

    keys, _total = await key_repo.list_by_tenant(tenant_id)
    api_keys_summary = [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        }
        for k in keys
    ]

    # Plan / quota info — would normally come from a billing table; stub for now
    plan_tier = api_ctx.plan_tier or "free"
    credits_limit = {"free": 1000, "starter": 10000, "growth": 100000, "enterprise": 1000000}.get(
        plan_tier, 1000,
    )

    account = AccountInfo(
        tenant_id=tenant_id,
        plan=plan_tier,
        credits_remaining=credits_limit,  # placeholder until billing is wired
        credits_limit=credits_limit,
        api_keys=api_keys_summary,
    )

    logger.info("public_api.account.info", tenant_id=tenant_id, plan=plan_tier)
    return success_response(
        data=account.model_dump(mode="json"),
        request=request,
        credits_used=0,
    )
