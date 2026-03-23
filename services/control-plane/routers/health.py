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
    except RuntimeError as e:
        checks["database"] = f"error: {e}"
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}: {e}"

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
        except Exception as e:
            checks["redis"] = f"error: {type(e).__name__}: {e}"
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
    """Deep connection check — tests database with table introspection.

    Returns detailed diagnostic info useful for debugging deployment issues.
    """
    from services.control_plane.config import settings
    from services.control_plane.dependencies import get_database
    from sqlalchemy import text

    result: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {},
        "redis": {},
    }

    # --- Database deep check ---
    db_url = settings.database_url
    # Mask password in URL for safe display
    masked_url = _mask_url(db_url)
    result["database"]["url"] = masked_url

    try:
        db = get_database()
        async with db.session() as session:
            # Basic connectivity
            row = await session.execute(text("SELECT 1 AS connected"))
            result["database"]["connected"] = bool(row.scalar())

            # Check if tables exist
            if "asyncpg" in db_url:
                # PostgreSQL — query information_schema
                tables_result = await session.execute(text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' ORDER BY table_name"
                ))
                tables = [r[0] for r in tables_result.fetchall()]

                # Get database version
                ver = await session.execute(text("SELECT version()"))
                result["database"]["server_version"] = ver.scalar()
            else:
                # SQLite
                tables_result = await session.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ))
                tables = [r[0] for r in tables_result.fetchall()]
                result["database"]["server_version"] = "SQLite"

            result["database"]["tables"] = tables
            result["database"]["table_count"] = len(tables)
            result["database"]["status"] = "healthy"

    except Exception as e:
        logger.error("Database connection check failed", extra={"error": str(e)})
        result["database"]["status"] = "error"
        result["database"]["error"] = f"{type(e).__name__}: {e}"

    # --- Redis deep check ---
    redis_url = settings.redis_url or os.environ.get("REDIS_URL", "")
    queue_backend = os.environ.get("QUEUE_BACKEND", "memory")
    result["redis"]["backend"] = queue_backend

    if queue_backend == "redis" and redis_url and not redis_url.startswith("${{"):
        result["redis"]["url"] = _mask_url(redis_url)
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(redis_url, decode_responses=True)
            info = await client.info("server")
            await client.aclose()
            result["redis"]["status"] = "healthy"
            result["redis"]["server_version"] = info.get("redis_version", "unknown")
        except Exception as e:
            result["redis"]["status"] = "error"
            result["redis"]["error"] = f"{type(e).__name__}: {e}"
    else:
        result["redis"]["status"] = "skipped"
        result["redis"]["reason"] = "in-memory mode or REDIS_URL not set"

    overall = (
        result["database"].get("status") == "healthy"
        and result["redis"].get("status") in ("healthy", "skipped")
    )
    result["overall"] = "connected" if overall else "degraded"

    return result


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
