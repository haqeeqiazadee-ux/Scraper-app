"""
URL Discovery — sitemap.xml parsing and robots.txt compliance.

Provides two key capabilities for production scraping:
1. Sitemap discovery: Parse sitemap.xml to find all product URLs without crawling
2. Robots compliance: Check robots.txt before scraping any URL

These are the first things a pro scraper does on any site.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Check robots.txt compliance before scraping.

    Caches parsed robots.txt per domain (1-hour TTL).
    Gracefully allows scraping if robots.txt is unreachable.

    Usage:
        checker = RobotsChecker()
        if checker.can_fetch("https://example.com/products"):
            # OK to scrape
        delay = checker.get_crawl_delay("https://example.com")
    """

    def __init__(self, user_agent: str = "ScraperPlatform/1.0") -> None:
        self._user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}
        self._cache_time: dict[str, float] = {}
        self._cache_ttl = 3600  # 1 hour

    def _get_parser(self, url: str) -> RobotFileParser:
        """Get or create a robots.txt parser for the URL's domain."""
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        now = time.time()
        if domain in self._cache:
            if now - self._cache_time.get(domain, 0) < self._cache_ttl:
                return self._cache[domain]

        rp = RobotFileParser()
        robots_url = f"{domain}/robots.txt"

        try:
            rp.set_url(robots_url)
            rp.read()
        except Exception as e:
            logger.debug("Could not fetch robots.txt for %s: %s", domain, e)
            # Permissive parser if robots.txt is unreachable
            rp = RobotFileParser()

        self._cache[domain] = rp
        self._cache_time[domain] = now
        return rp

    def can_fetch(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        try:
            rp = self._get_parser(url)
            return rp.can_fetch(self._user_agent, url)
        except Exception:
            return True  # Allow if check fails

    def get_crawl_delay(self, url: str) -> Optional[float]:
        """Get crawl delay for the URL's domain (seconds)."""
        try:
            rp = self._get_parser(url)
            delay = rp.crawl_delay(self._user_agent)
            return float(delay) if delay else None
        except Exception:
            return None

    def get_sitemaps(self, url: str) -> list[str]:
        """Get sitemap URLs declared in robots.txt."""
        try:
            rp = self._get_parser(url)
            return list(rp.site_maps() or [])
        except Exception:
            return []

    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._cache.clear()
        self._cache_time.clear()


class SitemapParser:
    """Parse sitemap.xml to discover URLs without crawling.

    Handles:
    - Standard XML sitemaps (<urlset> with <loc> tags)
    - Sitemap index files (<sitemapindex> with nested sitemaps)
    - Gzipped sitemaps (.xml.gz)
    - URL filtering by pattern

    Usage:
        parser = SitemapParser()
        urls = await parser.discover("https://example.com", filter_pattern="/products/")
    """

    def __init__(self, max_urls: int = 10000, max_depth: int = 3) -> None:
        self._max_urls = max_urls
        self._max_depth = max_depth

    async def discover(
        self,
        base_url: str,
        filter_pattern: Optional[str] = None,
        sitemap_url: Optional[str] = None,
    ) -> list[str]:
        """Discover URLs from a site's sitemap.

        Args:
            base_url: The site's base URL (e.g. "https://example.com")
            filter_pattern: Optional substring filter (e.g. "/products/", "/dp/")
            sitemap_url: Optional explicit sitemap URL. If None, tries common locations.

        Returns:
            List of discovered URLs matching the filter.
        """
        urls: list[str] = []
        tried_sitemaps: set[str] = set()

        # Build list of sitemap URLs to try
        candidates = []
        if sitemap_url:
            candidates.append(sitemap_url)
        else:
            parsed = urlparse(base_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            candidates.extend([
                f"{base}/sitemap.xml",
                f"{base}/sitemap_index.xml",
                f"{base}/sitemap-index.xml",
                f"{base}/sitemap1.xml",
                f"{base}/product-sitemap.xml",
                f"{base}/wp-sitemap.xml",           # WordPress
                f"{base}/wp-sitemap-posts-product-1.xml",  # WooCommerce
            ])

            # Also check robots.txt for declared sitemaps
            checker = RobotsChecker()
            robot_sitemaps = checker.get_sitemaps(base_url)
            candidates.extend(robot_sitemaps)

        # Fetch and parse each sitemap
        for url in candidates:
            if url in tried_sitemaps or len(urls) >= self._max_urls:
                break
            tried_sitemaps.add(url)
            new_urls = await self._fetch_and_parse(url, filter_pattern, tried_sitemaps, depth=0)
            urls.extend(new_urls)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)
            if len(unique) >= self._max_urls:
                break

        logger.info("Sitemap discovery found %d URLs from %s", len(unique), base_url)
        return unique

    async def _fetch_and_parse(
        self,
        sitemap_url: str,
        filter_pattern: Optional[str],
        tried: set[str],
        depth: int,
    ) -> list[str]:
        """Fetch a sitemap URL and extract <loc> entries."""
        if depth >= self._max_depth:
            return []

        try:
            xml_text = await self._fetch_sitemap(sitemap_url)
            if not xml_text:
                return []
        except Exception as e:
            logger.debug("Failed to fetch sitemap %s: %s", sitemap_url, e)
            return []

        urls: list[str] = []

        # Check if this is a sitemap index (contains <sitemap> entries)
        nested_sitemaps = re.findall(
            r'<sitemap>\s*<loc>(.*?)</loc>', xml_text, re.DOTALL
        )
        if nested_sitemaps:
            for nested_url in nested_sitemaps:
                nested_url = nested_url.strip()
                if nested_url not in tried and len(urls) < self._max_urls:
                    tried.add(nested_url)
                    child_urls = await self._fetch_and_parse(
                        nested_url, filter_pattern, tried, depth + 1
                    )
                    urls.extend(child_urls)
            return urls

        # Regular sitemap — extract <loc> URLs
        loc_urls = re.findall(r'<loc>(.*?)</loc>', xml_text)
        for loc_url in loc_urls:
            loc_url = loc_url.strip()
            if filter_pattern is None or filter_pattern in loc_url:
                urls.append(loc_url)
            if len(urls) >= self._max_urls:
                break

        return urls

    async def _fetch_sitemap(self, url: str) -> Optional[str]:
        """Fetch sitemap XML content. Handles gzip."""
        try:
            # Try curl_cffi first, fall back to httpx
            try:
                from curl_cffi.requests import AsyncSession
                async with AsyncSession() as session:
                    resp = await session.get(url, timeout=15, allow_redirects=True)
                    if resp.status_code == 200:
                        return resp.text
                    return None
            except ImportError:
                pass

            import httpx
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.text
                return None
        except Exception as e:
            logger.debug("Sitemap fetch error: %s", e)
            return None
