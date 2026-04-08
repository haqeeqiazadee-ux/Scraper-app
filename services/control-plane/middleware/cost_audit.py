"""Cost Audit Middleware -- auto-log every API request with costs and timing."""

from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from packages.core.cost_tracker import CostTracker


class CostAuditMiddleware(BaseHTTPMiddleware):
    """Attach CostTracker to every request, log audit on response."""

    TRACKED_PREFIXES = ("/api/v1/", "/v1/")

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        path = request.url.path

        # Only track API requests
        if not any(path.startswith(p) for p in self.TRACKED_PREFIXES):
            return await call_next(request)

        # Generate request ID and attach cost tracker
        request_id = f"req_{uuid4().hex[:20]}"
        request.state.request_id = request_id
        request.state.cost_tracker = CostTracker()
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = int((time.monotonic() - start) * 1000)
        tracker: CostTracker = getattr(request.state, "cost_tracker", CostTracker())

        # Add cost headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Cost-USD"] = str(round(tracker.total_usd(), 6))
        response.headers["X-Duration-MS"] = str(duration_ms)

        # Async log to DB (fire-and-forget)
        try:
            asyncio.create_task(
                _log_to_db(
                    request_id=request_id,
                    method=request.method,
                    path=path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    cost_usd=tracker.total_usd(),
                    tenant_id=request.headers.get("X-Tenant-ID", "default"),
                )
            )
        except Exception:
            pass  # Non-critical

        return response


async def _log_to_db(**kwargs: object) -> None:
    """Log request to audit table (best-effort)."""
    try:
        from services.control_plane.dependencies import get_database

        db = get_database()
        async with db.session() as session:
            from packages.core.storage.repositories_public_api import (
                AuditLogRepository,
            )

            repo = AuditLogRepository(session)
            await repo.create(
                request_id=str(kwargs["request_id"]),
                tenant_id=str(kwargs["tenant_id"]),
                method=str(kwargs["method"]),
                endpoint=str(kwargs["path"]),
                status_code=int(kwargs["status_code"]),  # type: ignore[arg-type]
                duration_ms=int(kwargs["duration_ms"]),  # type: ignore[arg-type]
                credits_used=int(float(kwargs["cost_usd"]) * 1000),  # type: ignore[arg-type]  # millicents as credits
            )
            await session.commit()
    except Exception:
        pass  # Audit is non-critical, never fail the request
