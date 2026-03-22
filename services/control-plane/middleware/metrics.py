"""
Request metrics middleware for the control plane.

Automatically records:
- ``scraper_http_requests_total`` — counter of HTTP requests by method, path, status
- ``scraper_http_request_duration_ms`` — histogram of request latencies in milliseconds
- ``scraper_tasks_active`` — gauge of currently in-flight requests
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from packages.core.metrics import metrics


class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that tracks request count and duration."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        path = request.url.path

        # Track active requests
        metrics.gauge_inc("scraper_tasks_active")

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            metrics.counter_inc(
                "scraper_http_requests_total",
                labels={"method": method, "path": path, "status": "500"},
            )
            metrics.counter_inc(
                "scraper_errors_total",
                labels={"type": "unhandled_exception"},
            )
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            metrics.gauge_dec("scraper_tasks_active")
            metrics.histogram_observe(
                "scraper_request_duration_ms",
                elapsed_ms,
                labels={"method": method, "path": path},
            )

        status_code = str(response.status_code)
        metrics.counter_inc(
            "scraper_http_requests_total",
            labels={"method": method, "path": path, "status": status_code},
        )

        return response
