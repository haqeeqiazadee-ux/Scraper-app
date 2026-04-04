"""Tests for the CrawlManager crawl engine."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from packages.core.crawl_manager import (
    CrawlConfig,
    CrawlJob,
    CrawlManager,
    CrawlState,
    CrawlStats,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    """Minimal crawl config for testing."""
    return CrawlConfig(
        seed_urls=["https://example.com"],
        max_depth=2,
        max_pages=10,
        crawl_delay=0.0,
        concurrent_limit=1,
        respect_robots=False,
    )


@pytest.fixture
def manager():
    """CrawlManager with a stubbed-out robots checker."""
    robots = MagicMock()
    robots.can_fetch = MagicMock(return_value=True)
    cb = MagicMock()
    cb.can_request = MagicMock(return_value=True)
    cb.record_success = MagicMock()
    cb.record_failure = MagicMock()
    return CrawlManager(circuit_breaker=cb, robots_checker=robots)


SIMPLE_HTML = """
<html><body>
  <a href="/page2">Page 2</a>
  <a href="https://example.com/page3">Page 3</a>
  <a href="#section1">Section</a>
  <a href="javascript:void(0)">Click</a>
  <a href="mailto:test@example.com">Email</a>
</body></html>
"""

RELATIVE_HTML = """
<html><body>
  <a href="../other/page">Other</a>
  <a href="child">Child</a>
</body></html>
"""


# ---------------------------------------------------------------------------
# start / get / stop lifecycle
# ---------------------------------------------------------------------------

class TestCrawlLifecycle:

    @pytest.mark.asyncio
    async def test_start_crawl_returns_id(self, manager, config):
        with patch.object(manager, "_crawl_loop", new_callable=AsyncMock):
            crawl_id = await manager.start_crawl(config)
        assert isinstance(crawl_id, str)
        assert len(crawl_id) > 0

    @pytest.mark.asyncio
    async def test_get_crawl_not_found(self, manager):
        result = await manager.get_crawl("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_crawl_running(self, manager, config):
        with patch.object(manager, "_crawl_loop", new_callable=AsyncMock):
            crawl_id = await manager.start_crawl(config)
        job = await manager.get_crawl(crawl_id)
        assert job is not None
        assert job.state == CrawlState.RUNNING

    @pytest.mark.asyncio
    async def test_stop_crawl(self, manager, config):
        with patch.object(manager, "_crawl_loop", new_callable=AsyncMock):
            crawl_id = await manager.start_crawl(config)
        stopped = await manager.stop_crawl(crawl_id)
        assert stopped is True
        job = await manager.get_crawl(crawl_id)
        assert job.state == CrawlState.STOPPED

    @pytest.mark.asyncio
    async def test_stop_crawl_not_found(self, manager):
        result = await manager.stop_crawl("does-not-exist")
        assert result is False


# ---------------------------------------------------------------------------
# Link extraction
# ---------------------------------------------------------------------------

class TestExtractLinks:

    def test_extract_links_basic(self):
        links = CrawlManager._extract_links(SIMPLE_HTML, "https://example.com/")
        urls = [l for l in links]
        assert "https://example.com/page2" in urls
        assert "https://example.com/page3" in urls

    def test_extract_links_resolves_relative(self):
        links = CrawlManager._extract_links(
            RELATIVE_HTML, "https://example.com/dir/page"
        )
        assert "https://example.com/other/page" in links
        assert "https://example.com/dir/child" in links

    def test_extract_links_ignores_fragments(self):
        links = CrawlManager._extract_links(SIMPLE_HTML, "https://example.com/")
        # Fragment-only links (#section1) should be filtered, and
        # fragments should be stripped from any remaining URLs
        for link in links:
            assert "#" not in link

    def test_extract_links_ignores_javascript(self):
        links = CrawlManager._extract_links(SIMPLE_HTML, "https://example.com/")
        for link in links:
            assert not link.startswith("javascript:")


# ---------------------------------------------------------------------------
# Link filtering
# ---------------------------------------------------------------------------

class TestFilterLinks:

    def _seed_domains(self):
        return {"example.com"}

    def test_filter_links_by_pattern(self):
        config = CrawlConfig(
            seed_urls=["https://example.com"],
            url_patterns=[r"/products/"],
            deny_patterns=[r"/admin"],
        )
        links = [
            "https://example.com/products/1",
            "https://example.com/products/2",
            "https://example.com/admin/dashboard",
            "https://example.com/about",
        ]
        result = CrawlManager._filter_links(links, config, self._seed_domains(), 0)
        assert "https://example.com/products/1" in result
        assert "https://example.com/products/2" in result
        assert "https://example.com/admin/dashboard" not in result
        assert "https://example.com/about" not in result

    def test_filter_links_by_domain(self):
        config = CrawlConfig(
            seed_urls=["https://example.com"],
            follow_external=False,
        )
        links = [
            "https://example.com/page1",
            "https://external.com/page2",
        ]
        result = CrawlManager._filter_links(links, config, self._seed_domains(), 0)
        assert "https://example.com/page1" in result
        assert "https://external.com/page2" not in result

    def test_filter_links_allows_external(self):
        config = CrawlConfig(
            seed_urls=["https://example.com"],
            follow_external=True,
        )
        links = [
            "https://example.com/page1",
            "https://external.com/page2",
        ]
        result = CrawlManager._filter_links(links, config, self._seed_domains(), 0)
        assert "https://example.com/page1" in result
        assert "https://external.com/page2" in result


# ---------------------------------------------------------------------------
# CrawlConfig defaults
# ---------------------------------------------------------------------------

class TestCrawlConfig:

    def test_crawl_config_defaults(self):
        cfg = CrawlConfig(seed_urls=["https://example.com"])
        assert cfg.max_depth == 3
        assert cfg.max_pages == 100
        assert cfg.follow_external is False
        assert cfg.respect_robots is True
        assert cfg.output_format == "json"
        assert cfg.crawl_delay == 1.0
        assert cfg.concurrent_limit == 5
        assert cfg.url_patterns == []
        assert cfg.deny_patterns == []


# ---------------------------------------------------------------------------
# CrawlStats
# ---------------------------------------------------------------------------

class TestCrawlStats:

    def test_crawl_stats_update(self):
        stats = CrawlStats()
        stats.pages_crawled = 5
        stats.items_extracted = 3
        assert stats.pages_crawled == 5
        assert stats.items_extracted == 3

        stats.start_time = 1000.0
        with patch("packages.core.crawl_manager.time") as mock_time:
            mock_time.time.return_value = 1010.0
            stats.update_rates()
        assert stats.elapsed_seconds == 10.0
        assert stats.pages_per_second == 0.5


# ---------------------------------------------------------------------------
# Depth and page limits (tested via the _process_url / _crawl_loop logic)
# ---------------------------------------------------------------------------

class TestCrawlLimits:

    @pytest.mark.asyncio
    async def test_max_depth_respected(self, manager):
        """Links beyond max_depth should not be enqueued for processing."""
        config = CrawlConfig(
            seed_urls=["https://example.com"],
            max_depth=1,
            max_pages=50,
            crawl_delay=0.0,
            respect_robots=False,
        )

        page_html = '<html><body><a href="/deeper">Deeper</a></body></html>'

        call_count = 0

        async def fake_fetch(url):
            nonlocal call_count
            call_count += 1
            return page_html, 200, len(page_html)

        with patch.object(manager, "_fetch_page", side_effect=fake_fetch):
            crawl_id = await manager.start_crawl(config)
            # Wait for the crawl loop to finish
            task = manager._tasks.get(crawl_id)
            if task:
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass

        job = await manager.get_crawl(crawl_id)
        # Seed is depth 0, /deeper is depth 1.  No depth-2 pages should be fetched.
        assert job.stats.current_depth <= config.max_depth

    @pytest.mark.asyncio
    async def test_max_pages_respected(self, manager):
        """The crawl should stop once max_pages is reached."""
        config = CrawlConfig(
            seed_urls=["https://example.com"],
            max_depth=10,
            max_pages=3,
            crawl_delay=0.0,
            respect_robots=False,
        )

        counter = 0

        async def fake_fetch(url):
            nonlocal counter
            counter += 1
            return (
                f'<html><body><a href="/p{counter}a">A</a>'
                f'<a href="/p{counter}b">B</a></body></html>',
                200,
                100,
            )

        with patch.object(manager, "_fetch_page", side_effect=fake_fetch):
            crawl_id = await manager.start_crawl(config)
            task = manager._tasks.get(crawl_id)
            if task:
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass

        job = await manager.get_crawl(crawl_id)
        assert job.stats.pages_crawled <= config.max_pages
