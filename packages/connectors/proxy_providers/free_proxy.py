"""
Free proxy list scraper and validator.

Scrapes publicly available free proxy lists, validates them,
and caches working ones. Intended for testing and development use only.
Free proxies are unreliable and should not be used in production.

No config required — works out of the box.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from packages.connectors.proxy_providers.base import ProxyInfo, ProxyUsage

logger = logging.getLogger(__name__)

# Public free proxy list sources
_FREE_PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all",
    "https://www.proxy-list.download/api/v1/get?type=http",
]

_VALIDATION_URL = "https://httpbin.org/ip"
_VALIDATION_TIMEOUT = 10.0
_CACHE_TTL_SECONDS = 600  # 10 minutes


class FreeProxyProvider:
    """Free proxy provider that scrapes and validates public proxy lists.

    Caches validated proxies for a configurable TTL.
    Not recommended for production use.
    """

    def __init__(
        self,
        sources: Optional[list[str]] = None,
        validation_url: str = _VALIDATION_URL,
        validation_timeout: float = _VALIDATION_TIMEOUT,
        cache_ttl: float = _CACHE_TTL_SECONDS,
        max_concurrent_validations: int = 20,
    ) -> None:
        self._sources = sources or list(_FREE_PROXY_SOURCES)
        self._validation_url = validation_url
        self._validation_timeout = validation_timeout
        self._cache_ttl = cache_ttl
        self._max_concurrent = max_concurrent_validations

        # Lazy HTTP client
        self._client: Any = None

        # Cached validated proxies
        self._cached_proxies: list[ProxyInfo] = []
        self._cache_time: float = 0.0

        # Rotation index
        self._rotation_index = 0

    @property
    def name(self) -> str:
        return "free_proxy"

    async def _get_client(self) -> Any:
        """Lazy-initialize httpx async client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=self._validation_timeout)
        return self._client

    def _is_cache_valid(self) -> bool:
        """Check if the cached proxy list is still fresh."""
        return (
            len(self._cached_proxies) > 0
            and (time.time() - self._cache_time) < self._cache_ttl
        )

    async def _fetch_proxy_list(self) -> list[tuple[str, int]]:
        """Fetch raw proxy host:port pairs from free sources."""
        raw_proxies: list[tuple[str, int]] = []
        client = await self._get_client()

        for source_url in self._sources:
            try:
                resp = await client.get(source_url, follow_redirects=True)
                if resp.status_code == 200:
                    text = resp.text
                    for line in text.strip().splitlines():
                        line = line.strip()
                        if ":" in line:
                            parts = line.split(":")
                            if len(parts) == 2:
                                try:
                                    host = parts[0].strip()
                                    port = int(parts[1].strip())
                                    if 0 < port < 65536:
                                        raw_proxies.append((host, port))
                                except (ValueError, IndexError):
                                    continue
            except Exception:
                logger.warning("Failed to fetch from source: %s", source_url)

        # Deduplicate
        seen = set()
        unique: list[tuple[str, int]] = []
        for hp in raw_proxies:
            if hp not in seen:
                seen.add(hp)
                unique.append(hp)

        logger.info("Fetched %d unique free proxies from %d sources", len(unique), len(self._sources))
        return unique

    async def validate_proxy(self, host: str, port: int) -> bool:
        """Test if a proxy is working by making a request through it."""
        try:
            import httpx
            proxy_url = f"http://{host}:{port}"
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=self._validation_timeout,
            ) as test_client:
                resp = await test_client.get(self._validation_url)
                return resp.status_code == 200
        except Exception:
            return False

    async def refresh_list(self) -> list[ProxyInfo]:
        """Fetch, validate, and cache free proxies."""
        raw = await self._fetch_proxy_list()

        # Validate in parallel with semaphore
        sem = asyncio.Semaphore(self._max_concurrent)
        validated: list[ProxyInfo] = []

        async def _check(host: str, port: int) -> Optional[ProxyInfo]:
            async with sem:
                if await self.validate_proxy(host, port):
                    return ProxyInfo(
                        host=host,
                        port=port,
                        protocol="http",
                        provider_name=self.name,
                        pool_type="free",
                    )
                return None

        tasks = [_check(h, p) for h, p in raw[:100]]  # Limit to first 100 candidates
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, ProxyInfo):
                validated.append(result)

        self._cached_proxies = validated
        self._cache_time = time.time()
        self._rotation_index = 0

        logger.info("Validated %d working free proxies out of %d candidates", len(validated), len(tasks))
        return validated

    async def get_proxy(
        self,
        country: Optional[str] = None,
        session_type: str = "rotating",
    ) -> ProxyInfo:
        """Get a free proxy.

        Args:
            country: Not reliably supported for free proxies (best effort).
            session_type: Ignored — free proxies don't support sticky sessions.

        Raises:
            RuntimeError: If no working proxies are available.
        """
        if not self._is_cache_valid():
            await self.refresh_list()

        proxies = self._cached_proxies
        if country:
            # Free proxies rarely have geo info, filter if available
            geo_filtered = [p for p in proxies if p.country and p.country.upper() == country.upper()]
            if geo_filtered:
                proxies = geo_filtered

        if not proxies:
            raise RuntimeError("No working free proxies available. Call refresh_list() first.")

        # Round-robin selection
        proxy = proxies[self._rotation_index % len(proxies)]
        self._rotation_index += 1
        return proxy

    async def rotate(self) -> ProxyInfo:
        """Get the next proxy in rotation."""
        return await self.get_proxy()

    async def health_check(self) -> bool:
        """Check if we have any working proxies cached."""
        if self._is_cache_valid() and len(self._cached_proxies) > 0:
            return True
        try:
            await self.refresh_list()
            return len(self._cached_proxies) > 0
        except Exception:
            return False

    async def get_usage(self) -> ProxyUsage:
        """Free proxies have no usage tracking."""
        return ProxyUsage(
            provider_name=self.name,
            active_sessions=len(self._cached_proxies),
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
