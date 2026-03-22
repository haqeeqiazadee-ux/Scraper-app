"""
Unit tests for proxy provider integrations.

All HTTP calls are mocked — no real network access.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.connectors.proxy_providers.base import (
    ProxyInfo,
    ProxyProviderProtocol,
    ProxyUsage,
)
from packages.connectors.proxy_providers.brightdata import BrightDataProvider
from packages.connectors.proxy_providers.free_proxy import FreeProxyProvider
from packages.connectors.proxy_providers.oxylabs import OxylabsProvider
from packages.connectors.proxy_providers.smartproxy import SmartproxyProvider


# =============================================================================
# ProxyInfo dataclass tests
# =============================================================================


class TestProxyInfo:
    def test_url_with_auth(self):
        proxy = ProxyInfo(host="1.2.3.4", port=8080, username="user", password="pass")
        assert proxy.url == "http://user:pass@1.2.3.4:8080"

    def test_url_without_auth(self):
        proxy = ProxyInfo(host="1.2.3.4", port=8080)
        assert proxy.url == "http://1.2.3.4:8080"

    def test_display_with_country(self):
        proxy = ProxyInfo(host="1.2.3.4", port=8080, country="US")
        assert proxy.display == "http://1.2.3.4:8080 [US]"

    def test_display_without_country(self):
        proxy = ProxyInfo(host="1.2.3.4", port=8080)
        assert proxy.display == "http://1.2.3.4:8080"


class TestProxyUsage:
    def test_bytes_remaining(self):
        usage = ProxyUsage(bytes_used=500, bytes_limit=1000)
        assert usage.bytes_remaining == 500

    def test_bytes_remaining_unlimited(self):
        usage = ProxyUsage(bytes_used=500, bytes_limit=0)
        assert usage.bytes_remaining == -1

    def test_usage_percent(self):
        usage = ProxyUsage(bytes_used=750, bytes_limit=1000)
        assert usage.usage_percent == 75.0

    def test_usage_percent_unlimited(self):
        usage = ProxyUsage(bytes_used=750, bytes_limit=0)
        assert usage.usage_percent == 0.0


# =============================================================================
# BrightDataProvider tests
# =============================================================================


class TestBrightDataProvider:
    def test_name(self):
        provider = BrightDataProvider(customer_id="cust1", zone="res", password="pw")
        assert provider.name == "brightdata"

    @pytest.mark.asyncio
    async def test_get_proxy_rotating(self):
        provider = BrightDataProvider(customer_id="cust1", zone="res", password="pw")
        proxy = await provider.get_proxy(country="US")

        assert proxy.host == "brd.superproxy.io"
        assert proxy.port == 22225
        assert "country-us" in proxy.username
        assert "zone-res" in proxy.username
        assert proxy.password == "pw"
        assert proxy.country == "US"
        assert proxy.session_id is None
        assert proxy.provider_name == "brightdata"

    @pytest.mark.asyncio
    async def test_get_proxy_sticky(self):
        provider = BrightDataProvider(customer_id="cust1", zone="res", password="pw")
        proxy = await provider.get_proxy(session_type="sticky")

        assert "session-sess_1" in proxy.username
        assert proxy.session_id == "sess_1"

    @pytest.mark.asyncio
    async def test_sticky_sessions_increment(self):
        provider = BrightDataProvider(customer_id="cust1", zone="res", password="pw")
        p1 = await provider.get_proxy(session_type="sticky")
        p2 = await provider.get_proxy(session_type="sticky")

        assert p1.session_id == "sess_1"
        assert p2.session_id == "sess_2"

    @pytest.mark.asyncio
    async def test_rotate_returns_new_proxy(self):
        provider = BrightDataProvider(customer_id="cust1", zone="res", password="pw")
        proxy = await provider.rotate()

        assert proxy.session_id is None  # rotating = no sticky session
        assert proxy.host == "brd.superproxy.io"

    @pytest.mark.asyncio
    async def test_validate_credentials_success(self):
        provider = BrightDataProvider(customer_id="cust1", zone="res", password="pw")
        mock_resp = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        result = await provider.validate_credentials()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_failure(self):
        provider = BrightDataProvider(customer_id="cust1", zone="res", password="pw")
        mock_resp = MagicMock(status_code=401)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        result = await provider.validate_credentials()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_delegates_to_validate(self):
        provider = BrightDataProvider(customer_id="cust1", zone="res", password="pw")
        mock_resp = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        result = await provider.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_usage_success(self):
        provider = BrightDataProvider(customer_id="cust1", zone="res", password="pw")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"bw": 1000000, "bw_limit": 5000000}
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        usage = await provider.get_usage()
        assert usage.bytes_used == 1000000
        assert usage.bytes_limit == 5000000
        assert usage.provider_name == "brightdata"

    @pytest.mark.asyncio
    async def test_get_usage_api_error(self):
        provider = BrightDataProvider(customer_id="cust1", zone="res", password="pw")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        provider._client = mock_client

        usage = await provider.get_usage()
        assert usage.bytes_used == 0
        assert usage.provider_name == "brightdata"

    @pytest.mark.asyncio
    async def test_username_format_no_country(self):
        provider = BrightDataProvider(customer_id="cust1", zone="res", password="pw")
        proxy = await provider.get_proxy()

        assert proxy.username == "brd-customer-cust1-zone-res"

    @pytest.mark.asyncio
    async def test_username_format_with_country_and_session(self):
        provider = BrightDataProvider(customer_id="cust1", zone="dc", password="pw")
        proxy = await provider.get_proxy(country="GB", session_type="sticky")

        assert "country-gb" in proxy.username
        assert "session-sess_1" in proxy.username
        assert "zone-dc" in proxy.username

    @pytest.mark.asyncio
    async def test_env_var_fallback(self):
        with patch.dict("os.environ", {
            "BRIGHTDATA_CUSTOMER_ID": "env_cust",
            "BRIGHTDATA_ZONE": "env_zone",
            "BRIGHTDATA_PASSWORD": "env_pw",
        }):
            provider = BrightDataProvider()
            proxy = await provider.get_proxy()
            assert "env_cust" in proxy.username
            assert "env_zone" in proxy.username
            assert proxy.password == "env_pw"

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        provider = BrightDataProvider(customer_id="c", zone="z", password="p")
        await provider.close()  # no client, should be no-op
        await provider.close()  # still no-op


# =============================================================================
# SmartproxyProvider tests
# =============================================================================


class TestSmartproxyProvider:
    def test_name(self):
        provider = SmartproxyProvider(username="user", password="pass")
        assert provider.name == "smartproxy"

    @pytest.mark.asyncio
    async def test_get_proxy_residential(self):
        provider = SmartproxyProvider(username="user", password="pass")
        proxy = await provider.get_proxy(country="DE")

        assert proxy.host == "gate.smartproxy.com"
        assert proxy.port == 7000
        assert "country-de" in proxy.username
        assert proxy.password == "pass"
        assert proxy.country == "DE"

    @pytest.mark.asyncio
    async def test_get_proxy_datacenter(self):
        provider = SmartproxyProvider(username="user", password="pass", pool_type="datacenter")
        proxy = await provider.get_proxy()

        assert proxy.port == 10000
        assert proxy.pool_type == "datacenter"

    @pytest.mark.asyncio
    async def test_city_targeting(self):
        provider = SmartproxyProvider(username="user", password="pass")
        proxy = await provider.get_proxy(country="US", city="New York")

        assert "country-us" in proxy.username
        assert "city-new york" in proxy.username
        assert proxy.city == "New York"

    @pytest.mark.asyncio
    async def test_sticky_session(self):
        provider = SmartproxyProvider(username="user", password="pass")
        proxy = await provider.get_proxy(session_type="sticky")

        assert "session-sp_1" in proxy.username
        assert proxy.session_id == "sp_1"

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        provider = SmartproxyProvider(username="user", password="pass")
        mock_resp = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        provider = SmartproxyProvider(username="user", password="pass")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Timeout"))
        provider._client = mock_client

        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_bandwidth_usage(self):
        provider = SmartproxyProvider(username="user", password="pass")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = [{"traffic_used": 2000000, "traffic_limit": 10000000}]
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        usage = await provider.get_bandwidth_usage()
        assert usage.bytes_used == 2000000
        assert usage.bytes_limit == 10000000

    @pytest.mark.asyncio
    async def test_get_usage_is_alias(self):
        provider = SmartproxyProvider(username="user", password="pass")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = [{"traffic_used": 100, "traffic_limit": 1000}]
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        usage = await provider.get_usage()
        assert usage.bytes_used == 100


# =============================================================================
# OxylabsProvider tests
# =============================================================================


class TestOxylabsProvider:
    def test_name(self):
        provider = OxylabsProvider(username="user", password="pass")
        assert provider.name == "oxylabs"

    @pytest.mark.asyncio
    async def test_get_proxy_residential(self):
        provider = OxylabsProvider(username="user", password="pass")
        proxy = await provider.get_proxy(country="JP")

        assert proxy.host == "pr.oxylabs.io"
        assert proxy.port == 7777
        assert "cc-JP" in proxy.username
        assert proxy.country == "JP"

    @pytest.mark.asyncio
    async def test_get_proxy_datacenter(self):
        provider = OxylabsProvider(username="user", password="pass", pool_type="datacenter")
        proxy = await provider.get_proxy()

        assert proxy.host == "dc.pr.oxylabs.io"
        assert proxy.pool_type == "datacenter"

    @pytest.mark.asyncio
    async def test_get_proxy_isp(self):
        provider = OxylabsProvider(username="user", password="pass", pool_type="isp")
        proxy = await provider.get_proxy()

        assert proxy.host == "isp.oxylabs.io"
        assert proxy.pool_type == "isp"

    @pytest.mark.asyncio
    async def test_sticky_session(self):
        provider = OxylabsProvider(username="user", password="pass")
        proxy = await provider.get_proxy(session_type="sticky")

        assert "sessid-oxy_1" in proxy.username
        assert proxy.session_id == "oxy_1"

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        provider = OxylabsProvider(username="user", password="pass")
        mock_resp = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_get_realtime_stats(self):
        provider = OxylabsProvider(username="user", password="pass")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"active_connections": 5, "requests_per_second": 10}
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        stats = await provider.get_realtime_stats()
        assert stats["active_connections"] == 5

    @pytest.mark.asyncio
    async def test_get_usage(self):
        provider = OxylabsProvider(username="user", password="pass")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "traffic_used": 5000,
            "traffic_limit": 50000,
            "requests_used": 100,
            "requests_limit": 10000,
        }
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        usage = await provider.get_usage()
        assert usage.bytes_used == 5000
        assert usage.requests_used == 100
        assert usage.requests_limit == 10000

    @pytest.mark.asyncio
    async def test_get_realtime_stats_error(self):
        provider = OxylabsProvider(username="user", password="pass")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("err"))
        provider._client = mock_client

        stats = await provider.get_realtime_stats()
        assert stats == {}


# =============================================================================
# FreeProxyProvider tests
# =============================================================================


class TestFreeProxyProvider:
    def test_name(self):
        provider = FreeProxyProvider()
        assert provider.name == "free_proxy"

    @pytest.mark.asyncio
    async def test_get_proxy_with_cached_proxies(self):
        provider = FreeProxyProvider()
        # Pre-populate cache
        import time
        provider._cached_proxies = [
            ProxyInfo(host="1.1.1.1", port=8080, provider_name="free_proxy", pool_type="free"),
            ProxyInfo(host="2.2.2.2", port=9090, provider_name="free_proxy", pool_type="free"),
        ]
        provider._cache_time = time.time()

        proxy = await provider.get_proxy()
        assert proxy.host in ("1.1.1.1", "2.2.2.2")

    @pytest.mark.asyncio
    async def test_rotation_round_robin(self):
        provider = FreeProxyProvider()
        import time
        provider._cached_proxies = [
            ProxyInfo(host="1.1.1.1", port=8080, provider_name="free_proxy", pool_type="free"),
            ProxyInfo(host="2.2.2.2", port=9090, provider_name="free_proxy", pool_type="free"),
        ]
        provider._cache_time = time.time()

        p1 = await provider.get_proxy()
        p2 = await provider.get_proxy()
        assert p1.host == "1.1.1.1"
        assert p2.host == "2.2.2.2"

    @pytest.mark.asyncio
    async def test_get_proxy_no_cache_raises(self):
        provider = FreeProxyProvider(sources=[])
        # Empty sources = no proxies can be fetched
        provider._cached_proxies = []
        provider._cache_time = 0

        # Mock the refresh to return empty
        async def mock_refresh():
            return []
        provider.refresh_list = mock_refresh

        with pytest.raises(RuntimeError, match="No working free proxies"):
            await provider.get_proxy()

    @pytest.mark.asyncio
    async def test_health_check_with_cached(self):
        provider = FreeProxyProvider()
        import time
        provider._cached_proxies = [
            ProxyInfo(host="1.1.1.1", port=8080, provider_name="free_proxy", pool_type="free"),
        ]
        provider._cache_time = time.time()

        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_get_usage_returns_cache_size(self):
        provider = FreeProxyProvider()
        import time
        provider._cached_proxies = [
            ProxyInfo(host="1.1.1.1", port=8080, provider_name="free_proxy", pool_type="free"),
            ProxyInfo(host="2.2.2.2", port=9090, provider_name="free_proxy", pool_type="free"),
        ]
        provider._cache_time = time.time()

        usage = await provider.get_usage()
        assert usage.active_sessions == 2
        assert usage.provider_name == "free_proxy"

    @pytest.mark.asyncio
    async def test_cache_validity(self):
        provider = FreeProxyProvider(cache_ttl=1.0)
        import time
        provider._cached_proxies = [
            ProxyInfo(host="1.1.1.1", port=8080, provider_name="free_proxy", pool_type="free"),
        ]
        # Set cache time in the past
        provider._cache_time = time.time() - 2.0

        assert provider._is_cache_valid() is False

    @pytest.mark.asyncio
    async def test_fetch_proxy_list_parsing(self):
        provider = FreeProxyProvider(sources=["http://fake.test/proxies"])
        mock_resp = MagicMock(status_code=200, text="1.1.1.1:8080\n2.2.2.2:9090\ninvalid\n")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        raw = await provider._fetch_proxy_list()
        assert len(raw) == 2
        assert ("1.1.1.1", 8080) in raw
        assert ("2.2.2.2", 9090) in raw

    @pytest.mark.asyncio
    async def test_fetch_proxy_list_deduplication(self):
        provider = FreeProxyProvider(sources=["http://fake.test/proxies"])
        mock_resp = MagicMock(status_code=200, text="1.1.1.1:8080\n1.1.1.1:8080\n2.2.2.2:9090\n")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        raw = await provider._fetch_proxy_list()
        assert len(raw) == 2  # deduped


# =============================================================================
# Protocol compliance tests
# =============================================================================


class TestProtocolCompliance:
    """Verify all providers satisfy ProxyProviderProtocol structurally."""

    def test_brightdata_satisfies_protocol(self):
        provider = BrightDataProvider(customer_id="c", zone="z", password="p")
        assert isinstance(provider, ProxyProviderProtocol)

    def test_smartproxy_satisfies_protocol(self):
        provider = SmartproxyProvider(username="u", password="p")
        assert isinstance(provider, ProxyProviderProtocol)

    def test_oxylabs_satisfies_protocol(self):
        provider = OxylabsProvider(username="u", password="p")
        assert isinstance(provider, ProxyProviderProtocol)

    def test_free_proxy_satisfies_protocol(self):
        provider = FreeProxyProvider()
        assert isinstance(provider, ProxyProviderProtocol)


# =============================================================================
# Error handling tests
# =============================================================================


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_brightdata_network_error_on_validate(self):
        provider = BrightDataProvider(customer_id="c", zone="z", password="p")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=ConnectionError("refused"))
        provider._client = mock_client

        assert await provider.validate_credentials() is False

    @pytest.mark.asyncio
    async def test_oxylabs_network_error_on_usage(self):
        provider = OxylabsProvider(username="u", password="p")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=TimeoutError("timed out"))
        provider._client = mock_client

        usage = await provider.get_usage()
        assert usage.bytes_used == 0

    @pytest.mark.asyncio
    async def test_smartproxy_empty_subscription(self):
        provider = SmartproxyProvider(username="u", password="p")
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = []
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        provider._client = mock_client

        usage = await provider.get_bandwidth_usage()
        assert usage.bytes_used == 0
