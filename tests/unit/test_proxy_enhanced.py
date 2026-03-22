"""Tests for enhanced proxy adapter features."""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from packages.connectors.proxy_adapter import (
    FileProxyProvider,
    ListProxyProvider,
    Proxy,
    ProxyAdapter,
    ProxyProvider,
    RotatingProxyProvider,
)


# ---------------------------------------------------------------------------
# Proxy.from_url
# ---------------------------------------------------------------------------


class TestProxyFromUrl:
    def test_full_url_with_auth(self):
        p = Proxy.from_url("http://user:pass@proxy.example.com:8080")
        assert p.host == "proxy.example.com"
        assert p.port == 8080
        assert p.protocol == "http"
        assert p.username == "user"
        assert p.password == "pass"

    def test_url_without_auth(self):
        p = Proxy.from_url("http://proxy.example.com:3128")
        assert p.host == "proxy.example.com"
        assert p.port == 3128
        assert p.username is None
        assert p.password is None

    def test_socks5_protocol(self):
        p = Proxy.from_url("socks5://proxy.example.com:1080")
        assert p.protocol == "socks5"

    def test_https_protocol(self):
        p = Proxy.from_url("https://admin:secret@secure.proxy:443")
        assert p.protocol == "https"
        assert p.username == "admin"
        assert p.password == "secret"
        assert p.port == 443

    def test_host_port_only_defaults_to_http(self):
        p = Proxy.from_url("10.0.0.1:9999")
        assert p.protocol == "http"
        assert p.host == "10.0.0.1"
        assert p.port == 9999

    def test_extra_kwargs_forwarded(self):
        p = Proxy.from_url("http://host:80", geo="US", region="NY")
        assert p.geo == "US"
        assert p.region == "NY"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Invalid proxy URL"):
            Proxy.from_url("not-a-proxy")

    def test_whitespace_stripped(self):
        p = Proxy.from_url("  http://host:1234  ")
        assert p.host == "host"
        assert p.port == 1234

    def test_roundtrip_url(self):
        """from_url -> .url should produce equivalent URL."""
        original = "http://user:pass@host:8080"
        p = Proxy.from_url(original)
        assert p.url == original


# ---------------------------------------------------------------------------
# FileProxyProvider
# ---------------------------------------------------------------------------


class TestFileProxyProvider:
    @pytest.mark.asyncio
    async def test_load_url_format(self, tmp_path):
        f = tmp_path / "proxies.txt"
        f.write_text(
            "http://user:pass@proxy1.com:8080\n"
            "# comment line\n"
            "socks5://proxy2.com:1080\n"
            "\n"  # blank line
        )
        provider = FileProxyProvider(str(f), format="url")
        proxies = await provider.get_proxies()

        assert len(proxies) == 2
        assert proxies[0].host == "proxy1.com"
        assert proxies[0].username == "user"
        assert proxies[1].protocol == "socks5"

    @pytest.mark.asyncio
    async def test_load_json_url_strings(self, tmp_path):
        f = tmp_path / "proxies.json"
        data = [
            "http://user:pass@proxy1.com:8080",
            "http://proxy2.com:3128",
        ]
        f.write_text(json.dumps(data))

        provider = FileProxyProvider(str(f), format="json")
        proxies = await provider.get_proxies()

        assert len(proxies) == 2
        assert proxies[0].host == "proxy1.com"

    @pytest.mark.asyncio
    async def test_load_json_dict_objects(self, tmp_path):
        f = tmp_path / "proxies.json"
        data = [
            {"host": "1.2.3.4", "port": 80, "protocol": "http", "geo": "US"},
            {"host": "5.6.7.8", "port": 443, "protocol": "https"},
        ]
        f.write_text(json.dumps(data))

        provider = FileProxyProvider(str(f), format="json")
        proxies = await provider.get_proxies()

        assert len(proxies) == 2
        assert proxies[0].geo == "US"
        assert proxies[1].port == 443

    @pytest.mark.asyncio
    async def test_invalid_lines_skipped(self, tmp_path):
        f = tmp_path / "proxies.txt"
        f.write_text("http://good:8080\nnot_valid\nhttp://also-good:9090\n")

        provider = FileProxyProvider(str(f))
        proxies = await provider.get_proxies()

        assert len(proxies) == 2

    @pytest.mark.asyncio
    async def test_refresh_returns_same_as_get(self, tmp_path):
        f = tmp_path / "proxies.txt"
        f.write_text("http://host:1234\n")

        provider = FileProxyProvider(str(f))
        a = await provider.get_proxies()
        b = await provider.refresh()

        assert len(a) == len(b) == 1
        assert a[0].host == b[0].host


# ---------------------------------------------------------------------------
# ListProxyProvider
# ---------------------------------------------------------------------------


class TestListProxyProvider:
    @pytest.mark.asyncio
    async def test_basic(self):
        urls = [
            "http://a:b@host1:80",
            "socks5://host2:1080",
        ]
        provider = ListProxyProvider(urls)
        proxies = await provider.get_proxies()

        assert len(proxies) == 2
        assert proxies[0].username == "a"
        assert proxies[1].protocol == "socks5"

    @pytest.mark.asyncio
    async def test_empty_list(self):
        provider = ListProxyProvider([])
        proxies = await provider.get_proxies()
        assert proxies == []

    @pytest.mark.asyncio
    async def test_implements_protocol(self):
        provider = ListProxyProvider(["http://h:1"])
        assert isinstance(provider, ProxyProvider)


# ---------------------------------------------------------------------------
# RotatingProxyProvider
# ---------------------------------------------------------------------------


class TestRotatingProxyProvider:
    @pytest.mark.asyncio
    async def test_generates_sessions(self):
        provider = RotatingProxyProvider(
            host="brd.superproxy.io",
            port=22225,
            username="brd-customer-123",
            password="secret",
            num_sessions=5,
            session_prefix="sess",
        )
        proxies = await provider.get_proxies()

        assert len(proxies) == 5
        assert proxies[0].username == "brd-customer-123-sess-0"
        assert proxies[4].username == "brd-customer-123-sess-4"
        assert all(p.password == "secret" for p in proxies)
        assert all(p.session_id is not None for p in proxies)


# ---------------------------------------------------------------------------
# Sticky sessions
# ---------------------------------------------------------------------------


class TestStickySessions:
    def test_same_domain_returns_same_proxy(self):
        p1 = Proxy(host="a", port=1)
        p2 = Proxy(host="b", port=2)
        adapter = ProxyAdapter(
            proxies=[p1, p2],
            strategy="round_robin",
            sticky_session_duration=600.0,
        )

        first = adapter.get_proxy(domain="example.com", sticky=True)
        # Subsequent calls for the same domain should return the same proxy
        for _ in range(5):
            again = adapter.get_proxy(domain="example.com", sticky=True)
            assert again is not None
            assert again.host == first.host and again.port == first.port

    def test_different_domains_can_get_different_proxies(self):
        proxies = [Proxy(host=f"h{i}", port=i) for i in range(20)]
        adapter = ProxyAdapter(
            proxies=proxies,
            strategy="random",
            sticky_session_duration=600.0,
        )

        p_a = adapter.get_proxy(domain="a.com", sticky=True)
        p_b = adapter.get_proxy(domain="b.com", sticky=True)
        # With 20 proxies and random strategy, there is a small chance they
        # are the same, but we mainly test that both return something.
        assert p_a is not None
        assert p_b is not None

    def test_sticky_session_expires(self):
        p1 = Proxy(host="a", port=1)
        p2 = Proxy(host="b", port=2)
        adapter = ProxyAdapter(
            proxies=[p1, p2],
            strategy="round_robin",
            sticky_session_duration=0.0,  # expires immediately
        )

        first = adapter.get_proxy(domain="example.com", sticky=True)
        # The session duration is 0 so the entry is already expired
        second = adapter.get_proxy(domain="example.com", sticky=True)
        # Should go through normal strategy, which is round_robin by last_used
        assert second is not None

    def test_sticky_without_domain_is_noop(self):
        adapter = ProxyAdapter(
            proxies=[Proxy(host="a", port=1)],
            strategy="random",
        )
        p = adapter.get_proxy(sticky=True)
        assert p is not None


# ---------------------------------------------------------------------------
# least_used strategy
# ---------------------------------------------------------------------------


class TestLeastUsedStrategy:
    def test_picks_least_used_proxy(self):
        p1 = Proxy(host="a", port=1, total_requests=100)
        p2 = Proxy(host="b", port=2, total_requests=5)
        p3 = Proxy(host="c", port=3, total_requests=50)
        adapter = ProxyAdapter(proxies=[p1, p2, p3], strategy="least_used")

        chosen = adapter.get_proxy()
        assert chosen is not None
        assert chosen.host == "b"

    def test_least_used_skips_cooldown(self):
        p1 = Proxy(host="a", port=1, total_requests=0, cooldown_until=time.time() + 9999)
        p2 = Proxy(host="b", port=2, total_requests=100)
        adapter = ProxyAdapter(proxies=[p1, p2], strategy="least_used")

        chosen = adapter.get_proxy()
        assert chosen is not None
        assert chosen.host == "b"


# ---------------------------------------------------------------------------
# Geo filtering
# ---------------------------------------------------------------------------


class TestGeoFiltering:
    def test_filter_by_country(self):
        p_us = Proxy(host="us", port=1, geo="US")
        p_de = Proxy(host="de", port=2, geo="DE")
        p_none = Proxy(host="x", port=3)
        adapter = ProxyAdapter(proxies=[p_us, p_de, p_none], strategy="random")

        for _ in range(10):
            chosen = adapter.get_proxy(geo="US")
            assert chosen is not None
            assert chosen.host == "us"

    def test_filter_by_country_case_insensitive(self):
        p = Proxy(host="de", port=1, geo="DE")
        adapter = ProxyAdapter(proxies=[p], strategy="random")

        chosen = adapter.get_proxy(geo="de")
        assert chosen is not None
        assert chosen.host == "de"

    def test_filter_by_region(self):
        p_ny = Proxy(host="ny", port=1, geo="US", region="NY")
        p_ca = Proxy(host="ca", port=2, geo="US", region="CA")
        adapter = ProxyAdapter(proxies=[p_ny, p_ca], strategy="random")

        for _ in range(10):
            chosen = adapter.get_proxy(geo="US", region="CA")
            assert chosen is not None
            assert chosen.host == "ca"

    def test_geo_no_match_returns_none(self):
        p = Proxy(host="de", port=1, geo="DE")
        adapter = ProxyAdapter(proxies=[p], strategy="random")

        assert adapter.get_proxy(geo="JP") is None


# ---------------------------------------------------------------------------
# get_best_proxies
# ---------------------------------------------------------------------------


class TestGetBestProxies:
    def test_returns_top_n(self):
        proxies = []
        for i in range(10):
            p = Proxy(host=f"h{i}", port=i)
            p.total_requests = 100
            p.successful_requests = 50 + i * 5  # increasing success rate
            proxies.append(p)

        adapter = ProxyAdapter(proxies=proxies)
        best = adapter.get_best_proxies(3)

        assert len(best) == 3
        # Scores should be in descending order
        assert best[0].score >= best[1].score >= best[2].score
        # Best proxy should be h9 (highest success rate)
        assert best[0].host == "h9"

    def test_excludes_proxies_on_cooldown(self):
        p_good = Proxy(host="good", port=1, total_requests=10, successful_requests=10)
        p_cool = Proxy(
            host="cool",
            port=2,
            total_requests=10,
            successful_requests=10,
            cooldown_until=time.time() + 9999,
        )
        adapter = ProxyAdapter(proxies=[p_good, p_cool])

        best = adapter.get_best_proxies(5)
        assert len(best) == 1
        assert best[0].host == "good"

    def test_empty_pool(self):
        adapter = ProxyAdapter()
        assert adapter.get_best_proxies(5) == []

    def test_n_larger_than_pool(self):
        adapter = ProxyAdapter(proxies=[Proxy(host="a", port=1)])
        best = adapter.get_best_proxies(100)
        assert len(best) == 1


# ---------------------------------------------------------------------------
# remove_proxy
# ---------------------------------------------------------------------------


class TestRemoveProxy:
    def test_remove_existing(self):
        p1 = Proxy(host="a", port=1)
        p2 = Proxy(host="b", port=2)
        adapter = ProxyAdapter(proxies=[p1, p2])

        adapter.remove_proxy(p1)
        assert adapter.pool_size == 1
        assert adapter.get_proxy().host == "b"

    def test_remove_nonexistent_is_noop(self):
        adapter = ProxyAdapter(proxies=[Proxy(host="a", port=1)])
        adapter.remove_proxy(Proxy(host="z", port=99))
        assert adapter.pool_size == 1
