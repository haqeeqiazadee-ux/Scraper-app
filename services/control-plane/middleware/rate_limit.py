"""
Rate-limiting middleware for the control plane.

Applies per-tenant rate limiting using the InMemoryRateLimiter and returns
standard HTTP 429 responses with Retry-After and X-RateLimit-* headers.
"""

from __future__ import annotations

import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from packages.core.rate_limiter import InMemoryRateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)

# Module-level singleton — shared across requests within a process.
_rate_limiter: InMemoryRateLimiter | None = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """Return (and lazily create) the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        config = RateLimitConfig(
            requests_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60")),
            requests_per_hour=int(os.environ.get("RATE_LIMIT_PER_HOUR", "1000")),
            burst_size=int(os.environ.get("RATE_LIMIT_BURST", "100")),
        )
        _rate_limiter = InMemoryRateLimiter(default_config=config)
    return _rate_limiter


def set_rate_limiter(limiter: InMemoryRateLimiter) -> None:
    """Replace the global rate limiter (useful for testing)."""
    global _rate_limiter
    _rate_limiter = limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that enforces per-tenant rate limits.

    Reads the tenant ID from the ``X-Tenant-ID`` header (defaulting to
    ``"default"``).  Non-API paths (health, docs) are skipped.
    """

    # Paths that bypass rate limiting
    SKIP_PREFIXES: tuple[str, ...] = (
        "/health",
        "/readiness",
        "/docs",
        "/openapi.json",
        "/metrics",
    )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip non-API paths
        if any(path.startswith(prefix) for prefix in self.SKIP_PREFIXES):
            return await call_next(request)

        tenant_id = request.headers.get("X-Tenant-ID", "default")
        limiter = get_rate_limiter()

        allowed = await limiter.acquire(tenant_id)

        if not allowed:
            retry_after = await limiter.get_retry_after(tenant_id)
            remaining = await limiter.get_remaining(tenant_id)
            limit = await limiter.get_limit(tenant_id)

            logger.warning(
                "Rate limit exceeded",
                extra={"tenant_id": tenant_id, "path": path},
            )

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please retry later.",
                    "retry_after": round(retry_after, 1),
                },
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": str(remaining),
                },
            )

        # Request allowed — attach rate-limit headers to response
        response = await call_next(request)

        remaining = await limiter.get_remaining(tenant_id)
        limit = await limiter.get_limit(tenant_id)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
