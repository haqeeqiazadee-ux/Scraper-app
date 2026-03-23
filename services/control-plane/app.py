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

from services.control_plane.routers import health, tasks, policies, results, execution, metrics, schedules, billing  # noqa: E402 — uses symlink
from services.control_plane.middleware.metrics import MetricsMiddleware
from services.control_plane.middleware.rate_limit import RateLimitMiddleware
from services.control_plane.middleware.quota import QuotaMiddleware

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
    db = init_database(settings.database_url)

    # Use Alembic migrations for production (PostgreSQL).
    # Fall back to create_tables() for SQLite / development.
    if "sqlite" in settings.database_url:
        await db.create_tables()
        logger.info("Database tables created (SQLite dev mode)")
    else:
        logger.info("Skipping auto-create — use 'alembic upgrade head' for production migrations")
    logger.info("Database initialized", extra={"url": settings.database_url})

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

    # Register routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(metrics.router, tags=["Metrics"])
    app.include_router(tasks.router, prefix="/api/v1", tags=["Tasks"])
    app.include_router(policies.router, prefix="/api/v1", tags=["Policies"])
    app.include_router(results.router, prefix="/api/v1", tags=["Results"])
    app.include_router(execution.router, prefix="/api/v1", tags=["Execution"])
    app.include_router(schedules.router, prefix="/api/v1", tags=["Schedules"])
    app.include_router(billing.router, prefix="/api/v1", tags=["Billing"])
    if _auth_available:
        app.include_router(auth_router.router, prefix="/api/v1", tags=["Auth"])

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
