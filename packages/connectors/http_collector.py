"""
HTTP Collector — stealth HTTP fetcher with browser-grade TLS impersonation.

Uses curl_cffi to produce browser-matching TLS (JA3/JA4), HTTP/2 SETTINGS
frames, and header ordering. Falls back to httpx if curl_cffi is unavailable.

Implements the Connector protocol for the HTTP execution lane.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from packages.core.device_profiles import DeviceProfile, get_headers_for_profile, get_referer_for_url
from packages.core.interfaces import Connector, ConnectorMetrics, FetchRequest, FetchResponse

logger = logging.getLogger(__name__)

# Flag: is curl_cffi available?
_HAS_CURL_CFFI = False
try:
    from curl_cffi.requests import AsyncSession  # noqa: F401
    _HAS_CURL_CFFI = True
except ImportError:
    logger.info("curl_cffi not installed — falling back to httpx (TLS fingerprint will be Python/OpenSSL)")


class HttpCollector:
    """HTTP connector using curl_cffi for browser-grade TLS impersonation.

    Key improvements over plain httpx:
    - TLS fingerprint matches real Chrome/Firefox/Safari (JA3/JA4)
    - HTTP/2 with browser-matching SETTINGS frames and pseudo-header order
    - Header ordering matches real browser output
    - Coherent device profiles (UA, locale, timezone all consistent)
    - Falls back to httpx gracefully if curl_cffi is not installed
    """

    def __init__(self, proxy: Optional[str] = None, profile: Optional[DeviceProfile] = None) -> None:
        self._proxy = proxy
        self._profile = profile
        self._metrics = ConnectorMetrics()
        self._latency_samples: list[int] = []
        self._client = None
        self._client_type: str = ""  # "curl_cffi" or "httpx"

    async def _get_client(self):  # type: ignore[no-untyped-def]
        """Lazy-initialize HTTP client, preferring curl_cffi."""
        if self._client is not None:
            return self._client

        profile = self._profile or DeviceProfile.random()

        if _HAS_CURL_CFFI:
            from curl_cffi.requests import AsyncSession

            self._client = AsyncSession(
                impersonate=profile.impersonate_target,
                timeout=30,
                proxy=self._proxy,
                allow_redirects=True,
                verify=True,
            )
            self._client_type = "curl_cffi"
            logger.debug("Initialized curl_cffi client with impersonate=%s", profile.impersonate_target)
        else:
            import httpx

            self._client = httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(30.0),
                proxy=self._proxy,
                http2=True,
            )
            self._client_type = "httpx"
            logger.debug("Initialized httpx fallback client (no TLS impersonation)")

        return self._client

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch a URL with browser-grade TLS impersonation."""
        client = await self._get_client()
        self._metrics.total_requests += 1

        # Pick a fresh profile per request for fingerprint diversity
        profile = self._profile or DeviceProfile.random()

        # Build headers from device profile (correct order for the browser type)
        headers = get_headers_for_profile(profile)

        # Add referrer for session credibility
        referer = get_referer_for_url(request.url)
        if referer:
            headers["Referer"] = referer

        # Merge any request-specific headers (override profile defaults)
        headers.update(request.headers)

        start_ms = time.monotonic()

        try:
            if self._client_type == "curl_cffi":
                response = await client.request(
                    method=request.method,
                    url=request.url,
                    headers=headers,
                    cookies=request.cookies or None,
                    timeout=request.timeout_ms / 1000,
                    impersonate=profile.impersonate_target,
                    allow_redirects=request.follow_redirects,
                )
                elapsed_ms = int((time.monotonic() - start_ms) * 1000)
                text = response.text
                return FetchResponse(
                    url=str(response.url),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    cookies={k: v for k, v in response.cookies.items()},
                    body=response.content,
                    text=text,
                    html=text,
                    elapsed_ms=elapsed_ms,
                )
            else:
                # httpx fallback
                import httpx

                response = await client.request(
                    method=request.method,
                    url=request.url,
                    headers=headers,
                    cookies=request.cookies,
                    timeout=httpx.Timeout(request.timeout_ms / 1000),
                )
                elapsed_ms = int((time.monotonic() - start_ms) * 1000)
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
            elapsed_ms = int((time.monotonic() - start_ms) * 1000)
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            logger.warning("HTTP fetch failed", extra={"url": request.url, "client": self._client_type, "error": str(e)})
            return FetchResponse(
                url=request.url,
                status_code=0,
                error=str(e),
                elapsed_ms=elapsed_ms,
            )
        else:
            self._metrics.successful_requests += 1
            self._latency_samples.append(elapsed_ms)

    async def health_check(self) -> bool:
        """Check if the HTTP client is healthy."""
        try:
            client = await self._get_client()
            if self._client_type == "curl_cffi":
                resp = await client.get("https://httpbin.org/status/200", timeout=5)
            else:
                resp = await client.get("https://httpbin.org/status/200", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def get_metrics(self) -> ConnectorMetrics:
        """Return current metrics."""
        if self._latency_samples:
            self._metrics.avg_latency_ms = sum(self._latency_samples) / len(self._latency_samples)
        return self._metrics

    @property
    def client_type(self) -> str:
        """Return which HTTP backend is active."""
        return self._client_type

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            if self._client_type == "curl_cffi":
                await self._client.close()
            else:
                await self._client.aclose()
            self._client = None
