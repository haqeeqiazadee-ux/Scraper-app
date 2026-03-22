"""
Unit tests for OBS-002: Prometheus metrics collector, middleware, and endpoints.
"""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.core.metrics import MetricsCollector, _label_key, _label_suffix


# ---------------------------------------------------------------------------
# MetricsCollector — counters
# ---------------------------------------------------------------------------


class TestCounterInc:
    """Tests for counter_inc."""

    def test_simple_increment(self) -> None:
        mc = MetricsCollector()
        mc.counter_inc("requests_total")
        assert mc._counters[_label_key("requests_total", None)] == 1

    def test_increment_by_value(self) -> None:
        mc = MetricsCollector()
        mc.counter_inc("bytes_total", value=512)
        assert mc._counters[_label_key("bytes_total", None)] == 512

    def test_multiple_increments_accumulate(self) -> None:
        mc = MetricsCollector()
        mc.counter_inc("req", value=1)
        mc.counter_inc("req", value=2)
        mc.counter_inc("req", value=3)
        assert mc._counters[_label_key("req", None)] == 6

    def test_counter_with_labels(self) -> None:
        mc = MetricsCollector()
        mc.counter_inc("scraper_tasks_total", labels={"status": "completed"})
        mc.counter_inc("scraper_tasks_total", labels={"status": "failed"})
        mc.counter_inc("scraper_tasks_total", labels={"status": "completed"})
        key_ok = _label_key("scraper_tasks_total", {"status": "completed"})
        key_fail = _label_key("scraper_tasks_total", {"status": "failed"})
        assert mc._counters[key_ok] == 2
        assert mc._counters[key_fail] == 1

    def test_counter_with_multiple_labels(self) -> None:
        mc = MetricsCollector()
        mc.counter_inc("scraper_errors_total", labels={"type": "timeout", "lane": "http"})
        key = _label_key("scraper_errors_total", {"type": "timeout", "lane": "http"})
        assert mc._counters[key] == 1


# ---------------------------------------------------------------------------
# MetricsCollector — gauges
# ---------------------------------------------------------------------------


class TestGaugeSet:
    """Tests for gauge_set."""

    def test_set_value(self) -> None:
        mc = MetricsCollector()
        mc.gauge_set("scraper_proxy_pool_size", 42)
        assert mc._gauges[_label_key("scraper_proxy_pool_size", None)] == 42

    def test_overwrite_value(self) -> None:
        mc = MetricsCollector()
        mc.gauge_set("pool", 10)
        mc.gauge_set("pool", 20)
        assert mc._gauges[_label_key("pool", None)] == 20

    def test_gauge_with_labels(self) -> None:
        mc = MetricsCollector()
        mc.gauge_set("scraper_session_count", 5, labels={"status": "active"})
        mc.gauge_set("scraper_session_count", 3, labels={"status": "idle"})
        key_active = _label_key("scraper_session_count", {"status": "active"})
        key_idle = _label_key("scraper_session_count", {"status": "idle"})
        assert mc._gauges[key_active] == 5
        assert mc._gauges[key_idle] == 3

    def test_gauge_inc_dec(self) -> None:
        mc = MetricsCollector()
        mc.gauge_set("active", 0)
        mc.gauge_inc("active")
        mc.gauge_inc("active")
        mc.gauge_dec("active")
        assert mc._gauges[_label_key("active", None)] == 1


# ---------------------------------------------------------------------------
# MetricsCollector — histograms
# ---------------------------------------------------------------------------


class TestHistogramObserve:
    """Tests for histogram_observe."""

    def test_single_observation(self) -> None:
        mc = MetricsCollector()
        mc.histogram_observe("scraper_request_duration_ms", 150)
        key = _label_key("scraper_request_duration_ms", None)
        assert mc._hist_count[key] == 1
        assert mc._hist_sum[key] == 150

    def test_multiple_observations(self) -> None:
        mc = MetricsCollector()
        mc.histogram_observe("latency", 10)
        mc.histogram_observe("latency", 20)
        mc.histogram_observe("latency", 30)
        key = _label_key("latency", None)
        assert mc._hist_count[key] == 3
        assert mc._hist_sum[key] == 60

    def test_histogram_with_labels(self) -> None:
        mc = MetricsCollector()
        mc.histogram_observe("scraper_request_duration_ms", 100, labels={"lane": "http"})
        mc.histogram_observe("scraper_request_duration_ms", 500, labels={"lane": "browser"})
        key_http = _label_key("scraper_request_duration_ms", {"lane": "http"})
        key_browser = _label_key("scraper_request_duration_ms", {"lane": "browser"})
        assert mc._hist_count[key_http] == 1
        assert mc._hist_count[key_browser] == 1

    def test_histogram_bucket_placement(self) -> None:
        mc = MetricsCollector(buckets=(10, 50, 100, float("inf")))
        mc.histogram_observe("dur", 5)   # <= 10, 50, 100, +Inf
        mc.histogram_observe("dur", 30)  # <= 50, 100, +Inf
        mc.histogram_observe("dur", 75)  # <= 100, +Inf
        key = _label_key("dur", None)
        buckets = mc._hist_buckets[key]
        assert buckets[10] == 1
        assert buckets[50] == 2    # 5 and 30
        assert buckets[100] == 3   # all three (cumulative is computed at export)
        # Wait — internally each bucket counts how many obs fall <= that bound
        # Actually looking at the code: for each observation, every bucket where value <= bound gets +1
        # So bucket[10] gets +1 for obs=5 only → 1
        # bucket[50] gets +1 for obs=5, obs=30 → 2
        # bucket[100] gets +1 for obs=5, obs=30, obs=75 → 3
        assert buckets[10] == 1
        assert buckets[50] == 2
        assert buckets[100] == 3
        assert buckets[float("inf")] == 3

    def test_extraction_confidence_histogram(self) -> None:
        mc = MetricsCollector(buckets=(0.1, 0.25, 0.5, 0.75, 0.9, 1.0, float("inf")))
        mc.histogram_observe("scraper_extraction_confidence", 0.85)
        mc.histogram_observe("scraper_extraction_confidence", 0.95)
        mc.histogram_observe("scraper_extraction_confidence", 0.60)
        key = _label_key("scraper_extraction_confidence", None)
        assert mc._hist_count[key] == 3
        assert mc._hist_sum[key] == pytest.approx(2.4)


# ---------------------------------------------------------------------------
# Prometheus export format
# ---------------------------------------------------------------------------


class TestExportPrometheus:
    """Tests for export_prometheus."""

    def test_counter_format(self) -> None:
        mc = MetricsCollector()
        mc.counter_inc("scraper_tasks_total", labels={"status": "completed"})
        mc.counter_inc("scraper_tasks_total", labels={"status": "completed"})
        output = mc.export_prometheus()
        assert '# TYPE scraper_tasks_total counter' in output
        assert 'scraper_tasks_total{status="completed"} 2' in output

    def test_gauge_format(self) -> None:
        mc = MetricsCollector()
        mc.gauge_set("scraper_proxy_pool_size", 15)
        output = mc.export_prometheus()
        assert '# TYPE scraper_proxy_pool_size gauge' in output
        assert 'scraper_proxy_pool_size 15' in output

    def test_histogram_format(self) -> None:
        mc = MetricsCollector(buckets=(10, 50, 100, float("inf")))
        mc.histogram_observe("dur", 25)
        output = mc.export_prometheus()
        assert '# TYPE dur histogram' in output
        assert 'dur_bucket{le="10"} 0' in output
        assert 'dur_bucket{le="50"} 1' in output
        assert 'dur_bucket{le="100"} 1' in output
        assert 'dur_bucket{le="+Inf"} 1' in output
        assert 'dur_sum 25' in output
        assert 'dur_count 1' in output

    def test_multiple_metric_types(self) -> None:
        mc = MetricsCollector(buckets=(100, float("inf")))
        mc.counter_inc("c1")
        mc.gauge_set("g1", 42)
        mc.histogram_observe("h1", 50)
        output = mc.export_prometheus()
        assert "# TYPE c1 counter" in output
        assert "# TYPE g1 gauge" in output
        assert "# TYPE h1 histogram" in output

    def test_empty_export(self) -> None:
        mc = MetricsCollector()
        output = mc.export_prometheus()
        # Should be empty or just whitespace
        assert output.strip() == ""

    def test_counter_with_multiple_labels(self) -> None:
        mc = MetricsCollector()
        mc.counter_inc("scraper_errors_total", labels={"type": "timeout", "lane": "http"})
        output = mc.export_prometheus()
        assert 'scraper_errors_total{lane="http",type="timeout"} 1' in output


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------


class TestExportJson:
    """Tests for export_json."""

    def test_counter_json(self) -> None:
        mc = MetricsCollector()
        mc.counter_inc("req", 3)
        data = mc.export_json()
        assert "req" in data["counters"]
        assert data["counters"]["req"]["value"] == 3

    def test_gauge_json(self) -> None:
        mc = MetricsCollector()
        mc.gauge_set("pool", 10)
        data = mc.export_json()
        assert "pool" in data["gauges"]
        assert data["gauges"]["pool"]["value"] == 10

    def test_histogram_json(self) -> None:
        mc = MetricsCollector()
        mc.histogram_observe("lat", 100)
        mc.histogram_observe("lat", 200)
        data = mc.export_json()
        assert "lat" in data["histograms"]
        hist = data["histograms"]["lat"]
        assert hist["count"] == 2
        assert hist["sum"] == 300
        assert hist["min"] == 100
        assert hist["max"] == 200
        assert hist["avg"] == 150

    def test_empty_json(self) -> None:
        mc = MetricsCollector()
        data = mc.export_json()
        assert data == {"counters": {}, "gauges": {}, "histograms": {}}


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


class TestReset:
    """Tests for reset."""

    def test_reset_clears_all(self) -> None:
        mc = MetricsCollector()
        mc.counter_inc("c")
        mc.gauge_set("g", 1)
        mc.histogram_observe("h", 10)
        mc.reset()
        assert mc._counters == {}
        assert mc._gauges == {}
        assert mc._hist_observations == {}
        data = mc.export_json()
        assert data == {"counters": {}, "gauges": {}, "histograms": {}}


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class TestMetricsMiddleware:
    """Tests for the MetricsMiddleware."""

    @pytest.mark.asyncio
    async def test_middleware_records_request(self) -> None:
        from packages.core.metrics import metrics as global_metrics
        from services.control_plane.middleware.metrics import MetricsMiddleware

        global_metrics.reset()

        middleware = MetricsMiddleware(app=MagicMock())

        # Build a mock request
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/health"

        # Build a mock response
        mock_response = MagicMock()
        mock_response.status_code = 200

        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

        # Check that counter was incremented
        prom = global_metrics.export_prometheus()
        assert "scraper_http_requests_total" in prom
        assert 'status="200"' in prom

        # Check duration histogram was recorded
        assert "scraper_request_duration_ms" in prom

        # Active gauge should be back to 0
        json_data = global_metrics.export_json()
        active_key = "scraper_tasks_active"
        assert json_data["gauges"][active_key]["value"] == 0

    @pytest.mark.asyncio
    async def test_middleware_records_errors(self) -> None:
        from packages.core.metrics import metrics as global_metrics
        from services.control_plane.middleware.metrics import MetricsMiddleware

        global_metrics.reset()

        middleware = MetricsMiddleware(app=MagicMock())

        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/v1/tasks"

        call_next = AsyncMock(side_effect=RuntimeError("boom"))

        with pytest.raises(RuntimeError, match="boom"):
            await middleware.dispatch(request, call_next)

        prom = global_metrics.export_prometheus()
        assert 'scraper_http_requests_total{method="POST",path="/api/v1/tasks",status="500"} 1' in prom
        assert 'scraper_errors_total{type="unhandled_exception"} 1' in prom


# ---------------------------------------------------------------------------
# Endpoints (unit-level — test router directly)
# ---------------------------------------------------------------------------


class TestMetricsEndpoints:
    """Tests for the /metrics and /api/v1/metrics endpoints."""

    @pytest.mark.asyncio
    async def test_prometheus_endpoint(self) -> None:
        from packages.core.metrics import metrics as global_metrics
        from services.control_plane.routers.metrics import prometheus_metrics

        global_metrics.reset()
        global_metrics.counter_inc("scraper_tasks_total", labels={"status": "completed"})
        global_metrics.gauge_set("scraper_proxy_pool_size", 7)

        response = await prometheus_metrics()
        body = response.body.decode()
        assert 'scraper_tasks_total{status="completed"} 1' in body
        assert "scraper_proxy_pool_size 7" in body
        assert response.media_type == "text/plain; version=0.0.4; charset=utf-8"

    @pytest.mark.asyncio
    async def test_json_endpoint(self) -> None:
        from packages.core.metrics import metrics as global_metrics
        from services.control_plane.routers.metrics import json_metrics

        global_metrics.reset()
        global_metrics.counter_inc("scraper_tasks_total", labels={"status": "failed"})

        data = await json_metrics()
        assert "counters" in data
        assert "gauges" in data
        assert "histograms" in data
        # The counter should be present
        found = False
        for key, val in data["counters"].items():
            if "scraper_tasks_total" in key and val["labels"] == {"status": "failed"}:
                assert val["value"] == 1
                found = True
        assert found, "Expected scraper_tasks_total{status=failed} in JSON output"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    """Tests for label key and suffix helpers."""

    def test_label_key_no_labels(self) -> None:
        assert _label_key("foo", None) == "foo"

    def test_label_key_with_labels(self) -> None:
        key = _label_key("foo", {"b": "2", "a": "1"})
        assert key == 'foo{a="1",b="2"}'

    def test_label_suffix_no_labels(self) -> None:
        assert _label_suffix(None) == ""

    def test_label_suffix_with_labels(self) -> None:
        assert _label_suffix({"method": "GET"}) == '{method="GET"}'
