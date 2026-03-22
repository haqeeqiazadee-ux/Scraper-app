"""Health check endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Basic health check — returns 200 if the service is running."""
    return {
        "status": "healthy",
        "service": "control-plane",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check — verifies all dependencies are available."""
    checks = {
        "database": "not_configured",
        "redis": "not_configured",
        "storage": "not_configured",
    }
    # TODO: Actually check database, Redis, and storage connectivity

    all_healthy = all(v == "healthy" for v in checks.values())
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }
