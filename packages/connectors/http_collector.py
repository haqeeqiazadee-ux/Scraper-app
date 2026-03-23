"""
HTTP Collector — lightweight HTTP fetcher with stealth headers.

Implements the Connector protocol for the HTTP execution lane.
Uses httpx for async HTTP requests with browser-like headers.
"""

from __future__ import annotations

import logging
import random
from typing import Optional

from packages.core.interfaces import Connector, ConnectorMetrics, FetchRequest, FetchResponse

logger = logging.getLogger(__name__)

# Realistic browser User-Agent strings for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


class HttpCollector:
    """HTTP connector using httpx with stealth headers."""

    def __init__(self, proxy: Optional[str] = None) -> None:
        self._proxy = proxy
        self._metrics = ConnectorMetrics()
        self._latency_samples: list[int] = []
        self._client = None

    async def _get_client(self):  # type: ignore[no-untyped-def]
        """Lazy-initialize httpx client."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(30.0),
                proxy=self._proxy,
            )
        return self._client

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch a URL using HTTP with stealth headers."""
        import httpx

        client = await self._get_client()
        self._metrics.total_requests += 1

        # Build headers with randomized User-Agent
        headers = {**DEFAULT_HEADERS, "User-Agent": random.choice(USER_AGENTS)}
        headers.update(request.headers)

        try:
            response = await client.request(
                method=request.method,
                url=request.url,
                headers=headers,
                cookies=request.cookies,
                timeout=httpx.Timeout(request.timeout_ms / 1000),
            )

            self._metrics.successful_requests += 1
            elapsed_ms = int(response.elapsed.total_seconds() * 1000) if response.elapsed else 0
            self._latency_samples.append(elapsed_ms)
            text = response.text
            return FetchResponse(
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=dict(response.cookies),
                body=response.content,
                text=text,
                html=text,
                elapsed_ms=elapsed_ms,
            )
        except Exception as e:
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            logger.warning("HTTP fetch failed", extra={"url": request.url, "error": str(e)})
            return FetchResponse(
                url=request.url,
                status_code=0,
                error=str(e),
            )

    async def health_check(self) -> bool:
        """Check if the HTTP client is healthy."""
        try:
            client = await self._get_client()
            resp = await client.get("https://httpbin.org/status/200", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def get_metrics(self) -> ConnectorMetrics:
        """Return current metrics."""
        if self._metrics.total_requests > 0:
            self._metrics.avg_latency_ms = sum(self._latency_samples) / len(self._latency_samples) if self._latency_samples else 0
        return self._metrics

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
