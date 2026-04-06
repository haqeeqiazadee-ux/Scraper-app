"""
Crawl Manager — BFS recursive crawl engine.

Manages full-site crawls using breadth-first traversal. Integrates with
the queue, router, dedup, url_discovery, circuit breaker, and rate limiter
modules to provide a production-grade crawl pipeline.

Usage:
    manager = CrawlManager()
    crawl_id = await manager.start_crawl(CrawlConfig(seed_urls=["https://example.com"]))
    job = await manager.get_crawl(crawl_id)
    results = await manager.get_results(crawl_id)
    await manager.stop_crawl(crawl_id)
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from bs4 import BeautifulSoup

from packages.core.circuit_breaker import CircuitBreaker
from packages.core.dedup import URLDedup
from packages.core.storage.memory_queue import InMemoryQueue
from packages.core.url_discovery import RobotsChecker

logger = logging.getLogger(__name__)

__all__ = [
    "CrawlConfig",
    "CrawlState",
    "CrawlStats",
    "CrawlJob",
    "CrawlManager",
]


@dataclass
class CrawlConfig:
    """Configuration for a crawl job."""

    seed_urls: list[str]
    max_depth: int = 3
    max_pages: int = 100
    url_patterns: list[str] = field(default_factory=list)
    deny_patterns: list[str] = field(default_factory=list)
    follow_external: bool = False
    respect_robots: bool = True
    output_format: str = "json"
    crawl_delay: float = 1.0
    concurrent_limit: int = 5


class CrawlState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class CrawlStats:
    """Real-time crawl statistics."""

    pages_crawled: int = 0
    pages_queued: int = 0
    pages_failed: int = 0
    items_extracted: int = 0
    bytes_downloaded: int = 0
    start_time: float = 0.0
    elapsed_seconds: float = 0.0
    pages_per_second: float = 0.0
    current_depth: int = 0

    def update_rates(self) -> None:
        """Recalculate derived stats."""
        if self.start_time > 0:
            self.elapsed_seconds = time.time() - self.start_time
            if self.elapsed_seconds > 0:
                self.pages_per_second = round(
                    self.pages_crawled / self.elapsed_seconds, 2
                )


@dataclass
class CrawlJob:
    """A running or completed crawl job."""

    crawl_id: str
    config: CrawlConfig
    state: CrawlState = CrawlState.PENDING
    stats: CrawlStats = field(default_factory=CrawlStats)
    results: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CrawlManager:
    """Manages full-site recursive crawls.

    Orchestrates BFS crawling by integrating the queue, URL dedup,
    robots.txt checker, circuit breaker, and concurrency controls.

    Usage:
        manager = CrawlManager()
        crawl_id = await manager.start_crawl(config)
        job = await manager.get_crawl(crawl_id)
        await manager.stop_crawl(crawl_id)
    """

    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreaker] = None,
        robots_checker: Optional[RobotsChecker] = None,
    ) -> None:
        self._crawls: dict[str, CrawlJob] = {}
        self._tasks: dict[str, asyncio.Task] = {}  # crawl_id -> background task
        self._url_depths: dict[str, dict[str, int]] = {}  # crawl_id -> {url: depth}
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._robots_checker = robots_checker or RobotsChecker()
        self._queue = InMemoryQueue()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_crawl(self, config: CrawlConfig) -> str:
        """Start a new crawl job. Returns crawl_id."""
        crawl_id = str(uuid4())
        job = CrawlJob(crawl_id=crawl_id, config=config)
        self._crawls[crawl_id] = job
        self._url_depths[crawl_id] = {}

        # Seed the queue
        queue_name = self._queue_name(crawl_id)
        for url in config.seed_urls:
            await self._queue.enqueue(queue_name, {"url": url, "depth": 0})
            self._url_depths[crawl_id][url] = 0

        job.stats.pages_queued = len(config.seed_urls)
        job.state = CrawlState.RUNNING
        job.stats.start_time = time.time()
        job.updated_at = datetime.now(timezone.utc)

        # Launch BFS loop as a background task
        task = asyncio.create_task(self._crawl_loop(job))
        self._tasks[crawl_id] = task

        logger.info(
            "Crawl started",
            extra={
                "crawl_id": crawl_id,
                "seed_urls": config.seed_urls,
                "max_depth": config.max_depth,
                "max_pages": config.max_pages,
            },
        )
        return crawl_id

    async def get_crawl(self, crawl_id: str) -> Optional[CrawlJob]:
        """Get crawl job status and stats."""
        job = self._crawls.get(crawl_id)
        if job is not None:
            job.stats.update_rates()
        return job

    async def get_results(self, crawl_id: str) -> list[dict]:
        """Get extracted results for a crawl."""
        job = self._crawls.get(crawl_id)
        if job is None:
            return []
        return list(job.results)

    async def stop_crawl(self, crawl_id: str) -> bool:
        """Stop a running crawl."""
        job = self._crawls.get(crawl_id)
        if job is None:
            return False

        if job.state not in (CrawlState.RUNNING, CrawlState.PAUSED):
            return False

        job.state = CrawlState.STOPPED
        job.updated_at = datetime.now(timezone.utc)

        # Cancel the background task
        task = self._tasks.pop(crawl_id, None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        job.stats.update_rates()
        logger.info(
            "Crawl stopped",
            extra={"crawl_id": crawl_id, "pages_crawled": job.stats.pages_crawled},
        )
        return True

    async def list_crawls(self) -> list[CrawlJob]:
        """List all crawl jobs."""
        for job in self._crawls.values():
            job.stats.update_rates()
        return list(self._crawls.values())

    # ------------------------------------------------------------------
    # BFS crawl loop
    # ------------------------------------------------------------------

    async def _crawl_loop(self, job: CrawlJob) -> None:
        """Main BFS crawl loop."""
        crawl_id = job.crawl_id
        config = job.config
        queue_name = self._queue_name(crawl_id)
        url_dedup = URLDedup()
        semaphore = asyncio.Semaphore(config.concurrent_limit)

        # Track last request time per domain for rate limiting
        domain_last_request: dict[str, float] = {}

        # Determine seed domains for scope filtering
        seed_domains: set[str] = set()
        for seed_url in config.seed_urls:
            seed_domains.add(self._extract_domain(seed_url))

        # Mark seed URLs as seen
        for seed_url in config.seed_urls:
            url_dedup.mark_seen(seed_url)

        try:
            while job.state == CrawlState.RUNNING:
                # Check page limit
                if job.stats.pages_crawled >= config.max_pages:
                    logger.info(
                        "Page limit reached",
                        extra={"crawl_id": crawl_id, "max_pages": config.max_pages},
                    )
                    break

                # Pop URL from queue with timeout (not instant get_nowait)
                message = await self._queue.dequeue(queue_name, timeout_seconds=2)
                if message is None:
                    # Queue may be temporarily empty while in-flight pages
                    # are extracting links. Retry with backoff before giving up.
                    found = False
                    for retry_wait in [0.5, 1.0, 1.5, 2.0, 3.0]:
                        await asyncio.sleep(retry_wait)
                        message = await self._queue.dequeue(queue_name)
                        if message is not None:
                            found = True
                            break
                    if not found:
                        logger.info(
                            "Queue empty after retries, crawl complete",
                            extra={"crawl_id": crawl_id, "pages_crawled": job.stats.pages_crawled},
                        )
                        break

                url: str = message["url"]
                depth: int = message.get("depth", 0)
                msg_id: str = message.get("_msg_id", "")

                # Check depth limit
                if depth > config.max_depth:
                    if msg_id:
                        await self._queue.ack(queue_name, msg_id)
                    continue

                # Check URL dedup (might have been enqueued multiple times)
                if url_dedup.is_seen(url) and url not in config.seed_urls:
                    if msg_id:
                        await self._queue.ack(queue_name, msg_id)
                    continue

                url_dedup.mark_seen(url)

                # Process this URL with concurrency control
                async with semaphore:
                    await self._process_url(
                        job=job,
                        url=url,
                        depth=depth,
                        msg_id=msg_id,
                        queue_name=queue_name,
                        url_dedup=url_dedup,
                        seed_domains=seed_domains,
                        domain_last_request=domain_last_request,
                    )

        except asyncio.CancelledError:
            logger.info("Crawl loop cancelled", extra={"crawl_id": crawl_id})
            raise
        except Exception:
            logger.exception("Crawl loop failed", extra={"crawl_id": crawl_id})
            job.state = CrawlState.FAILED
            job.updated_at = datetime.now(timezone.utc)
            return

        # Mark completed if not already stopped/failed
        if job.state == CrawlState.RUNNING:
            job.state = CrawlState.COMPLETED
        job.stats.update_rates()
        job.updated_at = datetime.now(timezone.utc)

        logger.info(
            "Crawl finished",
            extra={
                "crawl_id": crawl_id,
                "state": job.state,
                "pages_crawled": job.stats.pages_crawled,
                "pages_failed": job.stats.pages_failed,
            },
        )

    async def _process_url(
        self,
        *,
        job: CrawlJob,
        url: str,
        depth: int,
        msg_id: str,
        queue_name: str,
        url_dedup: URLDedup,
        seed_domains: set[str],
        domain_last_request: dict[str, float],
    ) -> None:
        """Fetch a single URL, extract links, store results."""
        config = job.config
        domain = self._extract_domain(url)

        # 1. Check robots.txt
        if config.respect_robots and not self._robots_checker.can_fetch(url):
            logger.debug("Blocked by robots.txt: %s", url)
            if msg_id:
                await self._queue.ack(queue_name, msg_id)
            return

        # 2. Check circuit breaker
        if not self._circuit_breaker.can_request(domain):
            logger.debug("Circuit open for domain %s, skipping %s", domain, url)
            if msg_id:
                await self._queue.nack(queue_name, msg_id)
            job.errors.append({
                "url": url,
                "error": "circuit_breaker_open",
                "domain": domain,
                "timestamp": time.time(),
            })
            return

        # 3. Per-domain rate limiting
        now = time.time()
        last_req = domain_last_request.get(domain, 0.0)
        wait_time = config.crawl_delay - (now - last_req)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        domain_last_request[domain] = time.time()

        # 4. Fetch the page
        try:
            html, status_code, content_length = await self._fetch_page(url)
        except Exception as e:
            logger.warning("Fetch failed for %s: %s", url, e)
            self._circuit_breaker.record_failure(domain)
            job.stats.pages_failed += 1
            job.errors.append({
                "url": url,
                "error": str(e),
                "depth": depth,
                "timestamp": time.time(),
            })
            if msg_id:
                await self._queue.ack(queue_name, msg_id)
            return

        if html is None:
            logger.warning("Empty response for %s (status=%s)", url, status_code)
            self._circuit_breaker.record_failure(domain)
            job.stats.pages_failed += 1
            job.errors.append({
                "url": url,
                "error": f"http_{status_code}",
                "depth": depth,
                "timestamp": time.time(),
            })
            if msg_id:
                await self._queue.ack(queue_name, msg_id)
            return

        # Success
        self._circuit_breaker.record_success(domain)

        # 5. Update stats
        job.stats.pages_crawled += 1
        job.stats.bytes_downloaded += content_length
        if depth > job.stats.current_depth:
            job.stats.current_depth = depth
        job.stats.update_rates()

        # 6. Extract and store page data
        page_result = self._extract_page_data(url, html, depth, config.output_format)
        job.results.append(page_result)
        job.stats.items_extracted += 1
        job.updated_at = datetime.now(timezone.utc)

        # 7. Extract links and enqueue new ones
        if depth < config.max_depth and job.stats.pages_crawled < config.max_pages:
            raw_links = self._extract_links(html, url)
            filtered_links = self._filter_links(
                raw_links, config, seed_domains, depth,
            )

            new_depth = depth + 1
            for link in filtered_links:
                # Dedup check before enqueue
                if url_dedup.check_and_mark(link):
                    continue
                # Respect page limit on queue size too
                await self._queue.enqueue(queue_name, {"url": link, "depth": new_depth})
                self._url_depths[job.crawl_id][link] = new_depth
                job.stats.pages_queued += 1

        # 8. Ack the message
        if msg_id:
            await self._queue.ack(queue_name, msg_id)

    # ------------------------------------------------------------------
    # HTTP fetching
    # ------------------------------------------------------------------

    async def _fetch_page(self, url: str) -> tuple[Optional[str], int, int]:
        """Fetch a page and return (html, status_code, content_length).

        Tries curl_cffi first, falls back to httpx.
        Returns (None, status_code, 0) on non-200 responses.
        """
        try:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession() as session:
                resp = await session.get(url, timeout=30, allow_redirects=True)
                content = resp.text
                content_length = len(content.encode("utf-8", errors="replace")) if content else 0
                if resp.status_code == 200 and content:
                    return content, resp.status_code, content_length
                return None, resp.status_code, 0
        except ImportError:
            pass

        import httpx

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url)
            content = resp.text
            content_length = len(content.encode("utf-8", errors="replace")) if content else 0
            if resp.status_code == 200 and content:
                return content, resp.status_code, content_length
            return None, resp.status_code, 0

    # ------------------------------------------------------------------
    # Link extraction and filtering
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_links(html: str, base_url: str) -> list[str]:
        """Extract all <a href> links from HTML, resolve relative URLs."""
        links: list[str] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all("a", href=True):
                href = tag["href"].strip()
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                absolute = urljoin(base_url, href)
                # Strip fragments
                parsed = urlparse(absolute)
                clean = parsed._replace(fragment="").geturl()
                links.append(clean)
        except Exception:
            logger.debug("Link extraction failed for %s", base_url, exc_info=True)
        return links

    @staticmethod
    def _filter_links(
        links: list[str],
        config: CrawlConfig,
        seed_domains: set[str],
        current_depth: int,
    ) -> list[str]:
        """Filter links by allow/deny patterns, domain scope, external policy."""
        filtered: list[str] = []

        # Compile patterns once
        allow_patterns = [re.compile(p) for p in config.url_patterns] if config.url_patterns else []
        deny_patterns = [re.compile(p) for p in config.deny_patterns] if config.deny_patterns else []

        for link in links:
            parsed = urlparse(link)

            # Only http/https
            if parsed.scheme not in ("http", "https"):
                continue

            # Domain scope check
            link_domain = parsed.netloc.lower().replace("www.", "")
            if ":" in link_domain:
                link_domain = link_domain.split(":")[0]

            if not config.follow_external and link_domain not in seed_domains:
                continue

            # Deny patterns
            if any(p.search(link) for p in deny_patterns):
                continue

            # Allow patterns (empty = allow all)
            if allow_patterns and not any(p.search(link) for p in allow_patterns):
                continue

            # Skip common non-page extensions
            path_lower = parsed.path.lower()
            skip_extensions = (
                ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
                ".css", ".js", ".woff", ".woff2", ".ttf", ".eot",
                ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3", ".avi",
            )
            if any(path_lower.endswith(ext) for ext in skip_extensions):
                continue

            filtered.append(link)

        return filtered

    # ------------------------------------------------------------------
    # Data extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_page_data(
        url: str, html: str, depth: int, output_format: str
    ) -> dict[str, Any]:
        """Extract structured data from a fetched page."""
        result: dict[str, Any] = {
            "url": url,
            "depth": depth,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        if output_format == "raw":
            result["content"] = html
            return result

        if output_format == "html":
            result["html"] = html
            return result

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            result["content"] = html
            return result

        # Extract title
        title_tag = soup.find("title")
        result["title"] = title_tag.get_text(strip=True) if title_tag else ""

        # Extract meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        result["meta_description"] = (
            meta_desc.get("content", "") if meta_desc else ""
        )

        if output_format == "markdown":
            result["content"] = _html_to_text(soup)
        else:
            # Default: json — extract structured text content
            result["content"] = _html_to_text(soup)
            result["headings"] = [
                {"level": tag.name, "text": tag.get_text(strip=True)}
                for tag in soup.find_all(re.compile(r"^h[1-6]$"))
            ]
            result["links_count"] = len(soup.find_all("a", href=True))
            result["images_count"] = len(soup.find_all("img"))

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _queue_name(crawl_id: str) -> str:
        """Generate a queue name for a crawl job."""
        return f"crawl:{crawl_id}"

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract normalized domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if ":" in domain:
            domain = domain.split(":")[0]
        return domain


def _html_to_text(soup: BeautifulSoup) -> str:
    """Extract readable text from a BeautifulSoup tree."""
    # Remove script and style tags
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Collapse multiple blank lines
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
