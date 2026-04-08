"""
Control Plane — FastAPI application for the AI Scraping Platform.

Central coordination layer that:
- Accepts task submissions
- Enforces policies and quotas
- Routes tasks to execution lanes
- Serves results and artifacts
- Manages tenants and auth
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from services.control_plane.routers import health, tasks, policies, results, execution, metrics, schedules, billing, artifacts, sessions, webhooks, templates  # noqa: E402 — uses symlink
from services.control_plane.routers.crawl import crawl_router
from services.control_plane.routers.search import search_router
from services.control_plane.routers.extract import extract_router
from services.control_plane.routers.facebook import facebook_router
from services.control_plane.routers.smart_scrape import smart_scrape_router
from services.control_plane.middleware.metrics import MetricsMiddleware
from services.control_plane.middleware.rate_limit import RateLimitMiddleware
from services.control_plane.middleware.quota import QuotaMiddleware
from services.control_plane.middleware.cost_audit import CostAuditMiddleware

# Auth router requires PyJWT — import conditionally (PyJWT may raise PanicException)
try:
    from services.control_plane.routers import auth as auth_router
    _auth_available = True
except BaseException:
    _auth_available = False
from services.control_plane.dependencies import init_database, get_database
from services.control_plane.config import settings
from packages.core.scheduler import TaskScheduler
from packages.core.webhook import WebhookExecutor

logger = logging.getLogger(__name__)

# Module-level instances for scheduler and webhook executor
_webhook_executor: WebhookExecutor | None = None
_task_scheduler: TaskScheduler | None = None


def get_webhook_executor() -> WebhookExecutor:
    """Get the global webhook executor instance."""
    global _webhook_executor
    if _webhook_executor is None:
        _webhook_executor = WebhookExecutor()
    return _webhook_executor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    global _task_scheduler, _webhook_executor
    logger.info("Control plane starting up")

    # Validate DATABASE_URL before connecting — catch common misconfiguration
    db_url = settings.database_url
    if "asyncpg" in db_url and "#" in db_url:
        raise RuntimeError(
            "DATABASE_URL contains an unescaped '#' character. "
            "URL-encode it as '%23' and quote the value in .env. "
            "Example: DATABASE_URL=\"postgresql+asyncpg://user:pass%23word@host:5432/db\""
        )

    db = init_database(db_url)

    # Brief network diagnostic for PostgreSQL connections
    if "asyncpg" in db_url:
        import socket
        try:
            host_part = db_url.split("@")[1].split("/")[0]
            db_host = host_part.rsplit(":", 1)[0]
            db_port = int(host_part.rsplit(":", 1)[1]) if ":" in host_part else 5432
            addrs = socket.getaddrinfo(db_host, db_port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            ipv4 = [a for a in addrs if a[0] == socket.AF_INET]
            ipv6 = [a for a in addrs if a[0] == socket.AF_INET6]
            logger.info(
                "DB host %s:%d → %d IPv4, %d IPv6 addresses",
                db_host, db_port, len(ipv4), len(ipv6),
            )
        except Exception as dns_err:
            logger.warning("DNS lookup failed for DB host: %s", dns_err)

    # Auto-create tables with retry for transient network issues in containers.
    # Railway / cloud containers may take a moment to establish network routes.
    import asyncio
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            await db.create_tables()
            if "sqlite" in db_url:
                logger.info("Database tables created (SQLite dev mode)")
            else:
                logger.info("Database tables ensured (PostgreSQL)")
            break
        except Exception as e:
            # Walk the exception chain to find the root cause
            root = e
            while root.__cause__:
                root = root.__cause__
            error_msg = f"{type(root).__name__}: {root}"
            full_msg = f"{type(e).__name__}: {e} (root: {error_msg})"

            is_network_error = any(s in full_msg.lower() for s in [
                "network is unreachable", "connection refused",
                "could not connect", "timeout", "name resolution",
                "no route to host", "connection reset", "errno 101",
                "errno 111", "errno 110",
            ])
            if is_network_error and attempt < max_retries:
                wait = 2 ** attempt  # 2, 4, 8, 16, 32 seconds
                logger.warning(
                    "Database connection attempt %d/%d failed, retrying in %ds: %s",
                    attempt, max_retries, wait, full_msg,
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "Failed to connect to database after %d attempts: %s",
                    attempt, full_msg,
                )
                raise
    logger.info("Database initialized")

    # Initialize webhook executor
    _webhook_executor = WebhookExecutor()

    # Initialize and start task scheduler
    async def _enqueue_task(task):
        logger.info("Scheduled task enqueued", extra={"task_id": str(task.id)})

    _task_scheduler = TaskScheduler(enqueue_fn=_enqueue_task)
    schedules.set_scheduler(_task_scheduler)
    await _task_scheduler.start()
    logger.info("Task scheduler started")

    yield

    logger.info("Control plane shutting down")
    if _task_scheduler is not None:
        await _task_scheduler.stop()
    if _webhook_executor is not None:
        await _webhook_executor.close()
    db = get_database()
    await db.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Scraping Platform — Control Plane",
        description="Central API for the AI-powered web scraping platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware — restrict origins via CORS_ORIGINS env var
    import os
    cors_origins_str = os.environ.get("CORS_ORIGINS", "*")
    cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Metrics middleware — must be added before routers
    app.add_middleware(MetricsMiddleware)

    # Rate limiting middleware
    app.add_middleware(RateLimitMiddleware)

    # Quota enforcement middleware
    app.add_middleware(QuotaMiddleware)

    # Cost audit middleware — tracks API costs and logs to audit table
    app.add_middleware(CostAuditMiddleware)

    # Global exception handler for debugging
    from fastapi.responses import JSONResponse
    from starlette.requests import Request

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception", extra={"error": str(exc), "type": type(exc).__name__, "path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={"detail": f"{type(exc).__name__}: {exc}", "path": str(request.url.path)},
        )

    # Register routers — health/metrics at both root and /api/v1 for frontend compat
    app.include_router(health.router, tags=["Health"])
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(metrics.router, tags=["Metrics"])
    app.include_router(metrics.router, prefix="/api/v1", tags=["Metrics"])
    app.include_router(tasks.router, prefix="/api/v1", tags=["Tasks"])
    app.include_router(policies.router, prefix="/api/v1", tags=["Policies"])
    app.include_router(results.router, prefix="/api/v1", tags=["Results"])
    app.include_router(execution.router, prefix="/api/v1", tags=["Execution"])
    app.include_router(schedules.router, prefix="/api/v1", tags=["Schedules"])
    app.include_router(billing.router, prefix="/api/v1", tags=["Billing"])
    app.include_router(artifacts.router, prefix="/api/v1", tags=["Artifacts"])
    app.include_router(sessions.router, prefix="/api/v1", tags=["Sessions"])
    app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])
    app.include_router(templates.router, prefix="/api/v1", tags=["Templates"])
    app.include_router(crawl_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(extract_router, prefix="/api/v1")
    app.include_router(facebook_router, prefix="/api/v1")
    app.include_router(smart_scrape_router, prefix="/api/v1")
    from services.control_plane.routers.batch import batch_router
    app.include_router(batch_router, prefix="/api/v1")
    from services.control_plane.routers import keepa
    app.include_router(keepa.router, prefix="/api/v1", tags=["Keepa"])
    from services.control_plane.routers import maps
    app.include_router(maps.router, prefix="/api/v1", tags=["Google Maps"])
    if _auth_available:
        app.include_router(auth_router.router, prefix="/api/v1", tags=["Auth"])

    # --- Auth Scrape ---
    try:
        from services.control_plane.routers.auth_scrape import auth_scrape_router
        app.include_router(auth_scrape_router, prefix="/api/v1", tags=["Auth Scrape"])
        logger.info("Auth Scrape router mounted")
    except Exception as e:
        logger.warning("Auth Scrape router not loaded: %s", e)

    # Google scraping uses cookie-based sessions via auth_scrape — no OAuth needed

    # --- Zero Checksum Public API ---
    try:
        from services.control_plane.routers.public_api import public_api_router
        from services.control_plane.routers.api_keys import api_keys_router
        app.include_router(public_api_router)  # mounted at /v1
        app.include_router(api_keys_router)    # mounted at /api/v1/api-keys
        logger.info("Public API v1 mounted at /v1 (9 endpoints)")
    except Exception as e:
        logger.warning("Public API not loaded: %s", e)

    # --- Serve the web dashboard (pre-built Vite dist) ---
    # Resolve dist path relative to repo root
    _repo_root = Path(__file__).resolve().parent.parent.parent
    _dist_dir = _repo_root / "apps" / "web" / "dist"
    _assets_dir = _dist_dir / "assets"

    if _dist_dir.is_dir() and _assets_dir.is_dir():
        # Serve JS/CSS assets
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="dashboard-assets")

        # Catch-all: serve index.html for any non-API route (SPA routing)
        _index_html = _dist_dir / "index.html"

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(request: Request, full_path: str):
            # If a static file exists in dist, serve it
            file_path = _dist_dir / full_path
            if full_path and file_path.is_file():
                return FileResponse(str(file_path))
            # Otherwise serve index.html for SPA client-side routing
            return FileResponse(str(_index_html))

    return app


# Application instance
app = create_app()
