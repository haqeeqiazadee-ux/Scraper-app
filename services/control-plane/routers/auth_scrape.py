"""Authenticated scraping API endpoints.

Allows users to upload browser cookies, create authenticated sessions,
and scrape pages that require login (LinkedIn, Instagram, etc.).
Uses the database SessionModel for persistent session storage.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.control_plane.dependencies import get_database, get_tenant_id

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class SessionCreateRequest(BaseModel):
    """Request to create an authenticated session from cookies."""

    cookies: list[dict] = Field(..., description="List of cookie objects (name, value, domain, ...)")
    target_domain: Optional[str] = Field(default=None, description="Override domain detection")


class ScrapeRequest(BaseModel):
    """Request to scrape a page using an authenticated session."""

    session_id: str = Field(..., description="Active session ID")
    target_url: str = Field(..., description="URL to scrape after authentication")
    extraction_mode: str = Field(default="everything", description="everything|table|fields|links")
    schema_: Optional[dict] = Field(default=None, alias="schema", description="Extraction schema for 'fields' mode")
    max_pages: int = Field(default=1, ge=1, le=100, description="Max pages to scrape")


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------

PRESETS = [
    {
        "id": "linkedin",
        "name": "LinkedIn",
        "icon": "briefcase",
        "login_url": "https://www.linkedin.com/login",
        "description": "Professional profiles, connections, job listings",
        "default_schema": {"name": "string", "title": "string", "company": "string", "connections": "string"},
    },
    {
        "id": "instagram",
        "name": "Instagram",
        "icon": "camera",
        "login_url": "https://www.instagram.com/accounts/login",
        "description": "User profiles, posts, followers, engagement metrics",
        "default_schema": {"username": "string", "posts": "number", "followers": "number", "following": "number"},
    },
    {
        "id": "twitter",
        "name": "Twitter / X",
        "icon": "bird",
        "login_url": "https://twitter.com/login",
        "description": "Tweets, followers, following, engagement data",
        "default_schema": {"tweets": "number", "followers": "number", "following": "number"},
    },
    {
        "id": "reddit",
        "name": "Reddit",
        "icon": "alien",
        "login_url": "https://www.reddit.com/login",
        "description": "Posts, karma, saved content, subreddit data",
        "default_schema": {"posts": "number", "karma": "number", "saved": "number"},
    },
    {
        "id": "shopify",
        "name": "Shopify Admin",
        "icon": "store",
        "login_url": "https://myshopify.com/admin",
        "description": "Orders, products, revenue from your Shopify store",
        "default_schema": {"orders": "number", "products": "number", "revenue": "number"},
    },
    {
        "id": "google-analytics",
        "name": "Google Analytics",
        "icon": "chart",
        "login_url": "https://analytics.google.com",
        "description": "Sessions, users, pageviews, traffic analytics",
        "default_schema": {"sessions": "number", "users": "number", "pageviews": "number"},
    },
]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

auth_scrape_router = APIRouter(prefix="", tags=["Auth Scrape"])


def _extract_domain(cookies: list[dict], fallback: str | None = None) -> str:
    """Extract the primary domain from a list of cookie objects."""
    for cookie in cookies:
        domain = cookie.get("domain", "")
        if domain:
            # Strip leading dot from cookie domains (e.g. ".linkedin.com" -> "linkedin.com")
            return domain.lstrip(".")
    if fallback:
        # Try to extract domain from URL
        from urllib.parse import urlparse
        parsed = urlparse(fallback if "://" in fallback else f"https://{fallback}")
        return parsed.netloc or fallback
    return "unknown"


@auth_scrape_router.post("/auth-scrape/session")
async def create_session(
    body: SessionCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Create an authenticated session from uploaded cookies.

    Stores cookies in the database SessionModel for persistent access.
    """
    if not body.cookies:
        raise HTTPException(status_code=400, detail="No cookies provided")

    domain = _extract_domain(body.cookies, body.target_domain)
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    db = get_database()
    async with db.session() as session:
        from packages.core.storage.models import SessionModel

        new_session = SessionModel(
            id=session_id,
            tenant_id=tenant_id,
            domain=domain,
            session_type="authenticated",
            cookies=body.cookies,
            headers={},
            status="active",
            request_count=0,
            success_count=0,
            failure_count=0,
            created_at=now,
            last_used_at=now,
        )
        session.add(new_session)
        await session.commit()

    logger.info(
        "auth_scrape.session_created",
        session_id=session_id,
        domain=domain,
        cookie_count=len(body.cookies),
        tenant_id=tenant_id,
    )

    return {
        "session_id": session_id,
        "domain": domain,
        "cookie_count": len(body.cookies),
        "status": "active",
        "created_at": now.isoformat(),
    }


@auth_scrape_router.post("/auth-scrape/scrape")
async def scrape_with_session(
    body: ScrapeRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Scrape a page using an authenticated session's cookies."""
    import traceback

    start = time.time()

    # Load session from DB
    db = get_database()
    async with db.session() as session:
        from packages.core.storage.models import SessionModel
        from sqlalchemy import select

        stmt = select(SessionModel).where(
            SessionModel.id == body.session_id,
            SessionModel.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        session_model = result.scalar_one_or_none()

        if session_model is None:
            raise HTTPException(status_code=404, detail=f"Session {body.session_id} not found")

        if session_model.status != "active":
            raise HTTPException(status_code=400, detail=f"Session is {session_model.status}, not active")

        cookies_list = session_model.cookies or []

    # Build cookie dict for HTTP requests: {name: value}
    cookie_dict = {}
    for c in cookies_list:
        name = c.get("name", "")
        value = c.get("value", "")
        if name and value:
            cookie_dict[name] = value

    url = body.target_url
    extraction_mode = body.extraction_mode

    try:
        # Use HttpWorker to fetch the page with cookies
        from services.worker_http.worker import HttpWorker

        task_payload: dict[str, Any] = {
            "task_id": f"auth-scrape-{uuid.uuid4().hex[:8]}",
            "tenant_id": tenant_id,
            "url": url,
            "timeout_ms": 20000,
            "paginate": False,
            "max_pages": body.max_pages,
            "cookies": cookie_dict,
        }

        if extraction_mode in ("everything", "content"):
            task_payload["output_format"] = "markdown"

        worker = HttpWorker()
        try:
            worker_result = await worker.process_task(task_payload)
        finally:
            await worker.close()

        succeeded = worker_result.get("status") == "success"
        extracted_data = worker_result.get("extracted_data", [])
        extraction_method = worker_result.get("extraction_method", "deterministic")

        # Post-process based on extraction mode
        if extraction_mode == "everything" and succeeded:
            html_snapshot = worker_result.get("html_snapshot", "")
            if html_snapshot:
                try:
                    from packages.core.ai_providers.deterministic import DeterministicProvider
                    from services.control_plane.routers.execution import _extract_everything

                    ai_provider = DeterministicProvider()
                    extracted_data = await _extract_everything(html_snapshot, url, ai_provider)
                    extraction_method = "deterministic+trafilatura+dom"
                except Exception as extract_err:
                    logger.warning("auth_scrape.extract_everything_fallback", error=str(extract_err))

        elif extraction_mode == "table" and succeeded:
            html_snapshot = worker_result.get("html_snapshot", "")
            if html_snapshot:
                extracted_data = _extract_tables(html_snapshot)
                extraction_method = "table_extraction"

        elif extraction_mode == "fields" and body.schema_ and succeeded:
            html_snapshot = worker_result.get("html_snapshot", "")
            if html_snapshot and extracted_data:
                try:
                    from services.control_plane.routers.extract import _match_to_schema
                    extracted_data = _match_to_schema(extracted_data, body.schema_)
                    extraction_method = "schema_match"
                except Exception:
                    pass  # Keep original extracted data

        elif extraction_mode == "links" and succeeded:
            html_snapshot = worker_result.get("html_snapshot", "")
            if html_snapshot:
                extracted_data = _extract_links(html_snapshot, url)
                extraction_method = "link_extraction"

        elapsed = int((time.time() - start) * 1000)
        item_count = len(extracted_data)
        confidence = worker_result.get("confidence", 0.0)

        # Update session health
        async with db.session() as session:
            from packages.core.storage.models import SessionModel
            from sqlalchemy import select

            stmt = select(SessionModel).where(SessionModel.id == body.session_id)
            result = await session.execute(stmt)
            sm = result.scalar_one_or_none()
            if sm:
                sm.request_count = (sm.request_count or 0) + 1
                sm.last_used_at = datetime.now(timezone.utc)
                if succeeded:
                    sm.success_count = (sm.success_count or 0) + 1
                else:
                    sm.failure_count = (sm.failure_count or 0) + 1
                await session.commit()

        # Save result to DB
        saved = False
        try:
            async with db.session() as save_session:
                from packages.core.storage.repositories import TaskRepository, ResultRepository, RunRepository

                task_id = str(uuid.uuid4())
                run_id = str(uuid.uuid4())

                task_repo = TaskRepository(save_session)
                run_repo = RunRepository(save_session)
                result_repo = ResultRepository(save_session)

                await task_repo.create(
                    tenant_id=tenant_id,
                    id=task_id,
                    url=url,
                    task_type="auth-scrape",
                    status="completed" if succeeded else "failed",
                )
                await run_repo.create(
                    tenant_id=tenant_id,
                    id=run_id,
                    task_id=task_id,
                    lane="http",
                    connector="http_collector",
                    status="completed" if succeeded else "failed",
                )
                if succeeded and extracted_data:
                    await result_repo.create(
                        tenant_id=tenant_id,
                        task_id=task_id,
                        run_id=run_id,
                        url=url,
                        extracted_data=extracted_data,
                        item_count=item_count,
                        confidence=confidence,
                        extraction_method=extraction_method,
                    )
                await save_session.commit()
                saved = True
        except Exception as save_err:
            logger.warning("auth_scrape.save_failed", error=str(save_err))

        return {
            "status": worker_result.get("status", "failed"),
            "item_count": item_count,
            "confidence": confidence,
            "extraction_method": extraction_method,
            "extraction_mode": extraction_mode,
            "duration_ms": elapsed,
            "error": worker_result.get("error"),
            "extracted_data": extracted_data[:50],
            "saved": saved,
        }

    except HTTPException:
        raise
    except Exception:
        elapsed = int((time.time() - start) * 1000)
        error = traceback.format_exc()
        logger.error("auth_scrape.scrape_failed", url=url, error=error)
        short_error = error.strip().split("\n")[-1][:500]
        return {
            "status": "failed",
            "item_count": 0,
            "confidence": 0,
            "extraction_method": None,
            "extraction_mode": extraction_mode,
            "duration_ms": elapsed,
            "error": short_error,
            "extracted_data": [],
            "saved": False,
        }


@auth_scrape_router.get("/auth-scrape/sessions")
async def list_sessions(
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """List all authenticated sessions for the current tenant."""
    db = get_database()
    async with db.session() as session:
        from packages.core.storage.models import SessionModel
        from sqlalchemy import select

        stmt = (
            select(SessionModel)
            .where(
                SessionModel.tenant_id == tenant_id,
                SessionModel.session_type == "authenticated",
            )
            .order_by(SessionModel.created_at.desc())
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

    sessions_out = []
    for s in rows:
        total = (s.success_count or 0) + (s.failure_count or 0)
        health_score = round((s.success_count or 0) / total * 100, 1) if total > 0 else 100.0
        cookie_count = len(s.cookies) if isinstance(s.cookies, list) else 0
        sessions_out.append({
            "id": s.id,
            "domain": s.domain,
            "status": s.status,
            "cookie_count": cookie_count,
            "health_score": health_score,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
        })

    return {"sessions": sessions_out}


@auth_scrape_router.delete("/auth-scrape/sessions/{session_id}")
async def delete_session(
    session_id: str,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Delete an authenticated session."""
    db = get_database()
    async with db.session() as session:
        from packages.core.storage.models import SessionModel
        from sqlalchemy import select, delete as sql_delete

        # Verify ownership
        stmt = select(SessionModel).where(
            SessionModel.id == session_id,
            SessionModel.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        await session.delete(existing)
        await session.commit()

    logger.info("auth_scrape.session_deleted", session_id=session_id, tenant_id=tenant_id)
    return {"status": "deleted", "session_id": session_id}


@auth_scrape_router.get("/auth-scrape/presets")
async def get_presets() -> dict:
    """Return static list of popular site presets."""
    return {"presets": PRESETS}


# ---------------------------------------------------------------------------
# Helper extraction functions
# ---------------------------------------------------------------------------


def _extract_tables(html: str) -> list[dict]:
    """Extract HTML tables from a page as structured data."""
    import re

    tables: list[dict] = []
    table_pattern = re.compile(r"<table[^>]*>(.*?)</table>", re.DOTALL | re.IGNORECASE)
    row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
    cell_pattern = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.DOTALL | re.IGNORECASE)
    tag_strip = re.compile(r"<[^>]+>")

    for table_match in table_pattern.finditer(html):
        table_html = table_match.group(1)
        rows = row_pattern.findall(table_html)
        if not rows:
            continue

        # First row as headers
        header_cells = cell_pattern.findall(rows[0])
        headers = [tag_strip.sub("", c).strip() or f"col_{i}" for i, c in enumerate(header_cells)]

        for row_html in rows[1:]:
            cells = cell_pattern.findall(row_html)
            if not cells:
                continue
            row_data: dict[str, str] = {}
            for i, cell in enumerate(cells):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row_data[key] = tag_strip.sub("", cell).strip()
            if any(v for v in row_data.values()):
                tables.append(row_data)

    return tables


def _extract_links(html: str, base_url: str) -> list[dict]:
    """Extract all links from a page."""
    import re
    from urllib.parse import urljoin

    link_pattern = re.compile(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    tag_strip = re.compile(r"<[^>]+>")

    links: list[dict] = []
    seen: set[str] = set()

    for match in link_pattern.finditer(html):
        href = match.group(1).strip()
        text = tag_strip.sub("", match.group(2)).strip()

        if href.startswith(("#", "javascript:", "mailto:")):
            continue

        full_url = urljoin(base_url, href)
        if full_url in seen:
            continue
        seen.add(full_url)

        links.append({
            "url": full_url,
            "text": text[:200] if text else "",
            "is_external": not full_url.startswith(base_url.split("/")[0] + "//" + base_url.split("//")[1].split("/")[0]) if "//" in base_url else True,
        })

    return links
