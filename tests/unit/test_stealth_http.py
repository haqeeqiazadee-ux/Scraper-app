"""Tests for the stealth HTTP collector (curl_cffi integration).

Covers:
- curl_cffi vs httpx backend selection
- Device profile integration
- Header generation
- Metrics tracking
- Graceful fallback
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.connectors.http_collector import HttpCollector
from packages.core.device_profiles import DeviceProfile
from packages.core.interfaces import FetchRequest, FetchResponse


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------


class TestBackendSelection:

    @pytest.mark.asyncio
    async def test_collector_creates_without_error(self) -> None:
        """HttpCollector can be instantiated without errors."""
        collector = HttpCollector()
        assert collector._client is None
        assert collector.client_type == ""

    @pytest.mark.asyncio
    async def test_collector_with_profile(self) -> None:
        """HttpCollector accepts a device profile."""
        profile = DeviceProfile.for_browser("chrome")
        collector = HttpCollector(profile=profile)
        assert collector._profile is profile

    @pytest.mark.asyncio
    async def test_collector_with_proxy(self) -> None:
        """HttpCollector accepts a proxy URL."""
        collector = HttpCollector(proxy="http://user:pass@proxy:8080")
        assert collector._proxy == "http://user:pass@proxy:8080"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetrics:

    def test_initial_metrics_are_zero(self) -> None:
        """Fresh collector has zero metrics."""
        collector = HttpCollector()
        metrics = collector.get_metrics()
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.avg_latency_ms == 0.0

    @pytest.mark.asyncio
    async def test_close_resets_client(self) -> None:
        """Closing the collector resets the client."""
        collector = HttpCollector()
        collector._client = MagicMock()
        collector._client.aclose = AsyncMock()
        collector._client_type = "httpx"
        await collector.close()
        assert collector._client is None


# ---------------------------------------------------------------------------
# Fetch with mock (no real HTTP)
# ---------------------------------------------------------------------------


class TestFetchMock:

    @pytest.mark.asyncio
    async def test_fetch_increments_total_requests(self) -> None:
        """Each fetch increments total_requests in metrics."""
        collector = HttpCollector()

        # Mock the client as curl_cffi style (no httpx needed)
        mock_response = MagicMock()
        mock_response.url = "https://example.com"
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = MagicMock()
        mock_response.cookies.items = MagicMock(return_value=[])
        mock_response.content = b"<html>test</html>"
        mock_response.text = "<html>test</html>"

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        collector._client = mock_client
        collector._client_type = "curl_cffi"

        request = FetchRequest(url="https://example.com")
        result = await collector.fetch(request)

        assert collector._metrics.total_requests == 1
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_failure_increments_failed(self) -> None:
        """Failed fetch increments failed_requests."""
        collector = HttpCollector()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Connection refused"))
        collector._client = mock_client
        collector._client_type = "curl_cffi"

        request = FetchRequest(url="https://example.com")
        result = await collector.fetch(request)

        assert collector._metrics.failed_requests == 1
        assert result.error is not None
        assert result.status_code == 0


# ---------------------------------------------------------------------------
# Integration: device profile headers
# ---------------------------------------------------------------------------


class TestProfileHeaderIntegration:

    def test_chrome_profile_produces_correct_headers(self) -> None:
        """Chrome profile generates sec-ch-ua and Accept headers."""
        from packages.core.device_profiles import get_headers_for_profile
        profile = DeviceProfile.for_browser("chrome")
        headers = get_headers_for_profile(profile)
        assert "sec-ch-ua" in headers
        assert "Accept" in headers
        assert "User-Agent" in headers

    def test_all_profiles_produce_headers(self) -> None:
        """Every profile in the database can generate headers."""
        from packages.core.device_profiles import DEVICE_PROFILES, get_headers_for_profile
        for profile in DEVICE_PROFILES:
            headers = get_headers_for_profile(profile)
            assert "User-Agent" in headers
            assert "Accept" in headers
