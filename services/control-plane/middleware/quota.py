"""
Quota enforcement middleware for the control plane.

Checks tenant quotas before task-creation and task-execution endpoints.
Returns HTTP 402 Payment Required when quotas are exceeded, with usage
details in response headers.
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from packages.core.quota_manager import QuotaManager, QuotaStatus

logger = logging.getLogger(__name__)

# Module-level singleton
_quota_manager: QuotaManager | None = None


def get_quota_manager() -> QuotaManager:
    """Return (and lazily create) the global quota manager instance."""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = QuotaManager()
    return _quota_manager


def set_quota_manager(manager: QuotaManager) -> None:
    """Replace the global quota manager (useful for testing)."""
    global _quota_manager
    _quota_manager = manager


class QuotaMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that enforces tenant quotas on task endpoints.

    Only checks quotas for POST requests to task-related paths.
    """

    # Paths that trigger quota checks (POST only)
    QUOTA_PATHS: tuple[str, ...] = (
        "/api/v1/tasks",
    )

    # Paths for task execution
    EXECUTION_SUFFIX: str = "/execute"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        method = request.method

        # Only enforce on POST to task endpoints
        should_check = False
        if method == "POST":
            # Check exact task creation path
            if path.rstrip("/") in self.QUOTA_PATHS:
                should_check = True
            # Check task execution paths like /api/v1/tasks/{id}/execute
            elif path.endswith(self.EXECUTION_SUFFIX) and "/tasks/" in path:
                should_check = True

        if not should_check:
            return await call_next(request)

        tenant_id = request.headers.get("X-Tenant-ID", "default")
        manager = get_quota_manager()

        result = await manager.check_quota(tenant_id)

        if result.status == QuotaStatus.EXCEEDED:
            logger.warning(
                "Quota exceeded",
                extra={
                    "tenant_id": tenant_id,
                    "exceeded": result.exceeded_resources,
                    "path": path,
                },
            )
            return JSONResponse(
                status_code=402,
                content={
                    "detail": "Quota exceeded. Please upgrade your plan or wait for the next billing cycle.",
                    "exceeded_resources": result.exceeded_resources,
                    "usage": result.usage.model_dump(),
                },
                headers={
                    "X-Quota-Status": "exceeded",
                    "X-Quota-Exceeded": ",".join(result.exceeded_resources),
                    "X-Quota-Tasks-Used": str(result.usage.tasks_today),
                    "X-Quota-AI-Tokens-Used": str(result.usage.ai_tokens_today),
                },
            )

        # Request allowed — attach quota headers
        response = await call_next(request)

        response.headers["X-Quota-Status"] = result.status.value
        response.headers["X-Quota-Tasks-Used"] = str(result.usage.tasks_today)
        response.headers["X-Quota-AI-Tokens-Used"] = str(result.usage.ai_tokens_today)

        if result.status == QuotaStatus.WARNING:
            response.headers["X-Quota-Warning"] = ",".join(result.warning_resources)

        return response
