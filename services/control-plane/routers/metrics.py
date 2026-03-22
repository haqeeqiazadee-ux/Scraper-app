"""
Metrics endpoints for the control plane.

- GET /metrics           — Prometheus text exposition format (for scraping)
- GET /api/v1/metrics    — JSON format (for the web dashboard)
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from packages.core.metrics import metrics

router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> PlainTextResponse:
    """Export metrics in Prometheus text exposition format."""
    body = metrics.export_prometheus()
    return PlainTextResponse(
        content=body,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/api/v1/metrics")
async def json_metrics() -> dict:
    """Export metrics as JSON for the dashboard."""
    return metrics.export_json()
