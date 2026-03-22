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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.control_plane.routers import health, tasks, policies  # noqa: E402 — uses symlink

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    logger.info("Control plane starting up")
    # TODO: Initialize database connections
    # TODO: Initialize Redis connection
    # TODO: Initialize queue consumers
    yield
    logger.info("Control plane shutting down")
    # TODO: Close connections gracefully


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Scraping Platform — Control Plane",
        description="Central API for the AI-powered web scraping platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(tasks.router, prefix="/api/v1", tags=["Tasks"])
    app.include_router(policies.router, prefix="/api/v1", tags=["Policies"])

    return app


# Application instance
app = create_app()
