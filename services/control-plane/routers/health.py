"""Health check endpoints."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check() -> dict:
    """Basic health check — returns 200 if the service is running."""
    return {
        "status": "healthy",
        "service": "control-plane",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check — verifies all dependencies are available."""
    from services.control_plane.config import settings
    from services.control_plane.dependencies import get_database
    from sqlalchemy import text

    checks: dict[str, str] = {
        "database": "not_configured",
        "redis": "not_configured",
        "storage": "not_configured",
    }

    # --- Database connectivity ---
    db_url = settings.database_url
    db_type = "postgresql" if "asyncpg" in db_url else "sqlite" if "sqlite" in db_url else "unknown"
    try:
        db = get_database()
        async with db.session() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()  # ensure result is consumed
        checks["database"] = "healthy"
    except RuntimeError:
        checks["database"] = "error"
    except Exception:
        checks["database"] = "error"

    # --- Redis connectivity ---
    redis_url = settings.redis_url or os.environ.get("REDIS_URL", "")
    queue_backend = os.environ.get("QUEUE_BACKEND", "memory")
    if queue_backend == "redis" and redis_url and not redis_url.startswith("${{"):
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(redis_url, decode_responses=True)
            pong = await client.ping()
            await client.aclose()
            checks["redis"] = "healthy" if pong else "error: no PONG"
        except Exception:
            checks["redis"] = "error"
    else:
        checks["redis"] = "skipped (in-memory mode)"

    # --- Storage check ---
    storage_type = settings.storage_type
    storage_path = settings.storage_path
    if storage_type == "filesystem":
        from pathlib import Path

        p = Path(storage_path)
        if p.is_dir():
            checks["storage"] = "healthy"
        else:
            # Try to create it
            try:
                p.mkdir(parents=True, exist_ok=True)
                checks["storage"] = "healthy (created)"
            except Exception as e:
                checks["storage"] = f"error: {type(e).__name__}: {e}"
    else:
        checks["storage"] = "skipped (non-filesystem)"

    all_ok = all(v.startswith("healthy") or v.startswith("skipped") for v in checks.values())
    return {
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
        "database_type": db_type,
        "queue_backend": queue_backend,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/check-connection")
async def check_connection() -> dict:
    """Deep connection check — removed from public access for security.

    This endpoint previously leaked database host, version, table names,
    and Redis metadata. It now returns only a simple connectivity status.
    """
    from services.control_plane.dependencies import get_database
    from sqlalchemy import text

    db_ok = False
    redis_ok = False

    try:
        db = get_database()
        async with db.session() as session:
            row = await session.execute(text("SELECT 1"))
            db_ok = bool(row.scalar())
    except Exception:
        logger.warning("Database check failed")

    redis_url = os.environ.get("REDIS_URL", "")
    queue_backend = os.environ.get("QUEUE_BACKEND", "memory")
    if queue_backend == "redis" and redis_url and not redis_url.startswith("${{"):
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(redis_url, decode_responses=True)
            pong = await client.ping()
            await client.aclose()
            redis_ok = bool(pong)
        except Exception:
            logger.warning("Redis check failed")
    else:
        redis_ok = True  # in-memory mode

    overall = db_ok and redis_ok
    return {
        "status": "connected" if overall else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _mask_url(url: str) -> str:
    """Mask password in a database/redis URL for safe logging."""
    try:
        # Pattern: scheme://user:password@host...
        if "://" in url and "@" in url:
            scheme_rest = url.split("://", 1)
            user_pass_host = scheme_rest[1].split("@", 1)
            if ":" in user_pass_host[0]:
                user = user_pass_host[0].split(":", 1)[0]
                return f"{scheme_rest[0]}://{user}:***@{user_pass_host[1]}"
        return url
    except Exception:
        return "***masked***"
