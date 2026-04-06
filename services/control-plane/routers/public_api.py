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
    AmazonDealsRequest,
    AmazonProductRequest,
    AmazonSearchRequest,
    AuthScrapeRequest,
    AuthSessionRequest,
    CrawlRequest,
    ExtractRequest,
    FacebookScrapeRequest,
    FacebookSessionRequest,
    JobResults,
    JobStatus,
    MapsSearchRequest,
    ScrapeRequest,
    ScrapeResult,
    ScheduleCreateRequest as PublicScheduleCreateRequest,
    SearchRequest,
    TemplateRunRequest,
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


# ==========================================================================
# 10-25: Additional workflow endpoints
# ==========================================================================


# ====================  10. POST /v1/auth-session  =========================


@public_api_router.post("/auth-session", status_code=200)
async def public_auth_session(
    body: AuthSessionRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Upload cookies and create an authenticated session. [0 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/auth-session",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.auth_scrape import (
            SessionCreateRequest as _SCR,
            create_session as _create_session,
        )

        # Build the internal request model
        internal_body = _SCR(cookies=body.cookies, target_domain=body.target_domain)
        # Call the internal function directly, passing tenant_id
        result = await _create_session(body=internal_body, tenant_id=tenant_id)

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=0, duration_ms=duration_ms,
        )
        logger.info("public_api.auth_session.created", request_id=request_id)
        return success_response(data=result, request=request, credits_used=0)
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="AUTH_SESSION_ERROR",
        )
        logger.error("public_api.auth_session.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "AUTH_SESSION_ERROR", "message": str(exc)}], request, 502,
        )


# =====================  11. POST /v1/auth-scrape  =========================


@public_api_router.post("/auth-scrape", status_code=200)
async def public_auth_scrape(
    body: AuthScrapeRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Scrape a page using an authenticated session. [2 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    credits = 2
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/auth-scrape",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.auth_scrape import (
            ScrapeRequest as _ASR,
            scrape_with_session as _scrape_with_session,
        )

        internal_body = _ASR(
            session_id=body.session_id,
            target_url=str(body.target_url),
            extraction_mode=body.extraction_mode,
            schema=body.schema,
            max_pages=body.max_pages,
        )
        result = await _scrape_with_session(body=internal_body, tenant_id=tenant_id)

        duration_ms = int((time.time() - start) * 1000)
        actual_credits = credits if result.get("status") != "failed" else 0
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=actual_credits, duration_ms=duration_ms,
        )
        logger.info(
            "public_api.auth_scrape.complete",
            request_id=request_id,
            item_count=result.get("item_count", 0),
        )
        return success_response(data=result, request=request, credits_used=actual_credits)
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="AUTH_SCRAPE_ERROR",
        )
        logger.error("public_api.auth_scrape.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "AUTH_SCRAPE_ERROR", "message": str(exc)}], request, 502,
        )


# ====================  12. GET /v1/auth-sessions  =========================


@public_api_router.get("/auth-sessions", status_code=200)
async def public_auth_sessions(
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """List active authenticated sessions. [0 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/auth-sessions",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.auth_scrape import list_sessions as _list_sessions

        result = await _list_sessions(tenant_id=tenant_id)

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=0, duration_ms=duration_ms,
        )
        return success_response(data=result, request=request, credits_used=0)
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="AUTH_SESSIONS_ERROR",
        )
        logger.error("public_api.auth_sessions.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "AUTH_SESSIONS_ERROR", "message": str(exc)}], request, 502,
        )


# ===================  13. POST /v1/amazon/product  ========================


@public_api_router.post("/amazon/product", status_code=200)
async def public_amazon_product(
    body: AmazonProductRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Look up an Amazon product by ASIN, URL, or keyword. [3 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    credits = 3
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/amazon/product",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.keepa import (
            KeepaQueryRequest,
            keepa_query,
        )

        internal_req = KeepaQueryRequest(
            query=body.query,
            domain=body.domain,
            max_results=body.max_results,
        )
        result = await keepa_query(internal_req)

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=credits, duration_ms=duration_ms,
        )
        logger.info(
            "public_api.amazon.product.complete",
            request_id=request_id,
            count=result.get("count", 0),
        )
        return success_response(data=result, request=request, credits_used=credits)
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="AMAZON_ERROR",
        )
        logger.error("public_api.amazon.product.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "AMAZON_ERROR", "message": str(exc)}], request, 502,
        )


# ====================  14. POST /v1/amazon/search  ========================


@public_api_router.post("/amazon/search", status_code=200)
async def public_amazon_search(
    body: AmazonSearchRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Search Amazon products with filters. [3 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    credits = 3
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/amazon/search",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.keepa import (
            KeepaSearchRequest,
            keepa_search,
        )

        # Convert price from dollars (float) to cents (int) for Keepa
        min_price_cents = int(body.min_price * 100) if body.min_price is not None else None
        max_price_cents = int(body.max_price * 100) if body.max_price is not None else None
        # Keepa rating is 0-50 scale; public API uses 0-5 float
        min_rating_keepa = int(body.min_rating * 10) if body.min_rating is not None else None

        internal_req = KeepaSearchRequest(
            title=body.title,
            brand=body.brand,
            min_price=min_price_cents,
            max_price=max_price_cents,
            min_rating=min_rating_keepa,
            domain=body.domain,
            max_results=body.max_results,
        )
        result = await keepa_search(internal_req)

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=credits, duration_ms=duration_ms,
        )
        logger.info(
            "public_api.amazon.search.complete",
            request_id=request_id,
            count=result.get("count", 0),
        )
        return success_response(data=result, request=request, credits_used=credits)
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="AMAZON_SEARCH_ERROR",
        )
        logger.error("public_api.amazon.search.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "AMAZON_SEARCH_ERROR", "message": str(exc)}], request, 502,
        )


# ====================  15. POST /v1/amazon/deals  =========================


@public_api_router.post("/amazon/deals", status_code=200)
async def public_amazon_deals(
    body: AmazonDealsRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Find current Amazon deals. [3 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    credits = 3
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/amazon/deals",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.keepa import (
            KeepaDealsRequest,
            keepa_deals,
        )

        internal_req = KeepaDealsRequest(
            min_discount_percent=body.min_discount_percent,
            domain=body.domain,
        )
        result = await keepa_deals(internal_req)

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=credits, duration_ms=duration_ms,
        )
        logger.info(
            "public_api.amazon.deals.complete",
            request_id=request_id,
            count=result.get("count", 0),
        )
        return success_response(data=result, request=request, credits_used=credits)
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="AMAZON_DEALS_ERROR",
        )
        logger.error("public_api.amazon.deals.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "AMAZON_DEALS_ERROR", "message": str(exc)}], request, 502,
        )


# =======================  16. POST /v1/maps  ==============================


@public_api_router.post("/maps", status_code=200)
async def public_maps_search(
    body: MapsSearchRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Search Google Maps for businesses by query + location. [2 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    credits = 2
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/maps",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.maps import (
            MapsSearchRequest as _MSR,
            maps_search as _maps_search,
        )

        internal_req = _MSR(
            query=body.query,
            max_results=body.max_results,
            location=body.location,
        )
        result = await _maps_search(internal_req)

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=credits, duration_ms=duration_ms,
        )
        logger.info(
            "public_api.maps.complete",
            request_id=request_id,
            count=result.get("count", 0),
        )
        return success_response(data=result, request=request, credits_used=credits)
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="MAPS_ERROR",
        )
        logger.error("public_api.maps.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "MAPS_ERROR", "message": str(exc)}], request, 502,
        )


# ==================  17. POST /v1/facebook/session  =======================


@public_api_router.post("/facebook/session", status_code=200)
async def public_facebook_session(
    body: FacebookSessionRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Upload Facebook cookies for authenticated access. [0 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/facebook/session",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.facebook import upload_cookies as _upload_cookies

        result = await _upload_cookies(cookies=body.cookies)

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=0, duration_ms=duration_ms,
        )
        logger.info("public_api.facebook.session.created", request_id=request_id)
        return success_response(data=result, request=request, credits_used=0)
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="FACEBOOK_SESSION_ERROR",
        )
        logger.error("public_api.facebook.session.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "FACEBOOK_SESSION_ERROR", "message": str(exc)}], request, 502,
        )


# ==================  18. POST /v1/facebook/scrape  ========================


@public_api_router.post("/facebook/scrape", status_code=200)
async def public_facebook_scrape(
    body: FacebookScrapeRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Scrape Facebook group posts. [5 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    credits = 5
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/facebook/scrape",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.facebook import (
            GroupScrapeRequest as _GSR,
            scrape_group as _scrape_group,
        )

        internal_req = _GSR(url=str(body.url), max_posts=body.max_posts)
        result = await _scrape_group(internal_req)

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=credits, duration_ms=duration_ms,
        )
        logger.info("public_api.facebook.scrape.started", request_id=request_id)
        return success_response(data=result, request=request, credits_used=credits)
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="FACEBOOK_SCRAPE_ERROR",
        )
        logger.error("public_api.facebook.scrape.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "FACEBOOK_SCRAPE_ERROR", "message": str(exc)}], request, 502,
        )


# =====================  19. GET /v1/templates  ============================


@public_api_router.get("/templates", status_code=200)
async def public_list_templates(
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    category: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    """List all scraper templates. [0 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/templates",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.templates import list_all_templates as _list_templates

        result = await _list_templates(
            category=category, platform=platform, tag=tag, q=q,
        )

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=0, duration_ms=duration_ms,
        )
        return success_response(data=result, request=request, credits_used=0)
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="TEMPLATES_ERROR",
        )
        logger.error("public_api.templates.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "TEMPLATES_ERROR", "message": str(exc)}], request, 502,
        )


# ================  20. POST /v1/templates/{template_id}/run  ==============


@public_api_router.post("/templates/{template_id}/run", status_code=200)
async def public_run_template(
    template_id: str,
    body: TemplateRunRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Apply a template, create a task, and execute it. [credits vary by template]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    credits = 2  # Base cost; may vary by template
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, f"/v1/templates/{template_id}/run",
    )
    request.state.request_id = request_id

    try:
        # Step 1: Apply the template to create a policy
        from services.control_plane.routers.templates import apply_template as _apply_template

        policy_result = await _apply_template(
            template_id=template_id,
            overrides=body.overrides,
            session=session,
            tenant_id=tenant_id,
        )
        policy_id = policy_result.get("policy_id")

        # Step 2: Create a task for the URL
        from packages.core.storage.repositories import TaskRepository

        task_repo = TaskRepository(session)
        task_id = str(uuid4())
        await task_repo.create(
            tenant_id=tenant_id,
            id=task_id,
            url=str(body.url),
            task_type="template",
            status="pending",
            policy_id=policy_id,
        )
        await session.flush()

        # Step 3: Execute the task inline
        from services.control_plane.routers.execution import execute_task as _execute_task

        exec_result = await _execute_task(
            task_id=task_id,
            session=session,
            tenant_id=tenant_id,
        )

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=credits, duration_ms=duration_ms,
        )
        logger.info(
            "public_api.templates.run.complete",
            request_id=request_id,
            template_id=template_id,
            task_id=task_id,
        )
        return success_response(
            data={
                "template_id": template_id,
                "policy_id": policy_id,
                "task_id": task_id,
                "execution": exec_result,
            },
            request=request,
            credits_used=credits,
        )
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="TEMPLATE_RUN_ERROR",
        )
        logger.error(
            "public_api.templates.run.failed",
            request_id=request_id,
            template_id=template_id,
            error=str(exc),
        )
        return error_response(
            [{"code": "TEMPLATE_RUN_ERROR", "message": str(exc)}], request, 502,
        )


# ====================  21. POST /v1/schedules  ============================


@public_api_router.post("/schedules", status_code=201)
async def public_create_schedule(
    body: PublicScheduleCreateRequest,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Create a scheduled scrape. [0 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/schedules",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.schedules import (
            ScheduleCreateRequest as _IntSCR,
            create_schedule as _create_schedule,
        )

        internal_req = _IntSCR(
            url=body.url,
            schedule=body.schedule,
            task_type=body.task_type,
        )
        result = await _create_schedule(request=internal_req, tenant_id=tenant_id)

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=201, credits_used=0, duration_ms=duration_ms,
        )
        logger.info("public_api.schedules.created", request_id=request_id)
        return success_response(data=result, request=request, credits_used=0)
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="SCHEDULE_CREATE_ERROR",
        )
        logger.error("public_api.schedules.create.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "SCHEDULE_CREATE_ERROR", "message": str(exc)}], request, 502,
        )


# =====================  22. GET /v1/schedules  ============================


@public_api_router.get("/schedules", status_code=200)
async def public_list_schedules(
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """List all schedules for the tenant. [0 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/schedules",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.schedules import list_schedules as _list_schedules

        result = await _list_schedules(tenant_id=tenant_id)

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=0, duration_ms=duration_ms,
        )
        return success_response(data=result, request=request, credits_used=0)
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="SCHEDULE_LIST_ERROR",
        )
        logger.error("public_api.schedules.list.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "SCHEDULE_LIST_ERROR", "message": str(exc)}], request, 502,
        )


# ================  23. DELETE /v1/schedules/{schedule_id}  ================


@public_api_router.delete("/schedules/{schedule_id}", status_code=200)
async def public_delete_schedule(
    schedule_id: str,
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Delete a schedule. [0 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, f"/v1/schedules/{schedule_id}",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.schedules import delete_schedule as _delete_schedule

        result = await _delete_schedule(schedule_id=schedule_id, tenant_id=tenant_id)

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=0, duration_ms=duration_ms,
        )
        logger.info("public_api.schedules.deleted", request_id=request_id, schedule_id=schedule_id)
        return success_response(data=result, request=request, credits_used=0)
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="SCHEDULE_DELETE_ERROR",
        )
        logger.error("public_api.schedules.delete.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "SCHEDULE_DELETE_ERROR", "message": str(exc)}], request, 502,
        )


# =====================  24. GET /v1/presets  ==============================


@public_api_router.get("/presets", status_code=200)
async def public_get_presets(
    request: Request,
    api_ctx: ApiKeyContext = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Get auth-scrape presets and template presets. [0 credits]"""
    start = time.time()
    request.state.start_time = start
    tenant_id = api_ctx.tenant_id
    audit_repo = AuditLogRepository(session)
    request_id = await _log_request(
        audit_repo, tenant_id, api_ctx.api_key_id,
        request, "/v1/presets",
    )
    request.state.request_id = request_id

    try:
        from services.control_plane.routers.auth_scrape import PRESETS as AUTH_PRESETS

        # Also gather template summaries as presets
        template_presets: list[dict[str, Any]] = []
        try:
            from packages.core.template_registry import list_templates

            for t in list_templates():
                template_presets.append({
                    "id": t.id,
                    "name": t.name,
                    "category": t.category.value,
                    "description": t.description,
                    "platform": t.platform,
                })
        except Exception:
            pass  # Template registry may not be available

        result = {
            "auth_scrape_presets": AUTH_PRESETS,
            "template_presets": template_presets,
        }

        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=200, credits_used=0, duration_ms=duration_ms,
        )
        return success_response(data=result, request=request, credits_used=0)
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        await _finalise_audit(
            audit_repo, request_id, tenant_id,
            status_code=502, credits_used=0, duration_ms=duration_ms,
            error_code="PRESETS_ERROR",
        )
        logger.error("public_api.presets.failed", request_id=request_id, error=str(exc))
        return error_response(
            [{"code": "PRESETS_ERROR", "message": str(exc)}], request, 502,
        )
