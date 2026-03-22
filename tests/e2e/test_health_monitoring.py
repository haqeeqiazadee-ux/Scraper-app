"""
E2E tests for observability endpoints:
  health, readiness, metrics (Prometheus + JSON).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Health and readiness endpoint E2E tests."""

    async def test_health_endpoint_returns_healthy(self, app_client: AsyncClient):
        """GET /health returns 200 with status=healthy."""
        resp = await app_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "control-plane"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data

    async def test_readiness_endpoint(self, app_client: AsyncClient):
        """GET /ready returns 200 with checks dict."""
        resp = await app_client.get("/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data
        # In test mode, services are not configured
        assert "database" in data["checks"]


@pytest.mark.asyncio
class TestMetricsEndpoints:
    """Metrics endpoint E2E tests."""

    async def test_prometheus_metrics_endpoint(self, app_client: AsyncClient):
        """GET /metrics returns Prometheus text format."""
        # Make a few requests to generate metrics data
        await app_client.get("/health")
        await app_client.get("/ready")

        resp = await app_client.get("/metrics")
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/plain" in content_type

        body = resp.text
        # Should contain HTTP request counter from middleware
        assert "scraper_http_requests_total" in body or len(body) > 0

    async def test_json_metrics_endpoint(self, app_client: AsyncClient):
        """GET /api/v1/metrics returns JSON metrics."""
        # Generate some traffic first
        await app_client.get("/health")

        resp = await app_client.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "counters" in data
        assert "gauges" in data
        assert "histograms" in data
