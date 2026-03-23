"""
Proxy Adapter — unified proxy management with rotation strategies.

Ported and refactored from scraper_pro/proxy_manager.py.
Supports file-based, API-based, rotating-service, and inline proxy sources.
Features sticky sessions, geo-targeting, least-used strategy, and pool management.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class Proxy:
    """Represents a single proxy with health tracking."""

    host: str
    port: int
    protocol: str = "http"  # http, https, socks5
    username: Optional[str] = None
    password: Optional[str] = None
    geo: Optional[str] = None
    region: Optional[str] = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_used: float = 0.0
    cooldown_until: float = 0.0
    response_times: list[float] = field(default_factory=list)
    session_id: Optional[str] = None

    @property
    def url(self) -> str:
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.protocol}://{auth}{self.host}:{self.port}"

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times[-20:]) / len(self.response_times[-20:])

    @property
    def score(self) -> float:
        return self.success_rate * 0.7 + (1.0 - min(self.avg_response_time / 10.0, 1.0)) * 0.3

    @property
    def is_available(self) -> bool:
        return time.time() >= self.cooldown_until

    @classmethod
    def from_url(cls, url: str, **kwargs: object) -> Proxy:
        """Parse proxy from URL string.

        Supported formats:
            protocol://user:pass@host:port
            protocol://host:port
            host:port  (defaults to http)
        """
        pattern = r"^(https?|socks5)?:?/?/?(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$"
        match = re.match(pattern, url.strip())

        if not match:
            raise ValueError(f"Invalid proxy URL: {url}")

        protocol, username, password, host, port = match.groups()
        return cls(
            host=host,
            port=int(port),
            username=username or None,
            password=password or None,
            protocol=protocol or "http",
            **kwargs,  # type: ignore[arg-type]
        )


@runtime_checkable
class ProxyProvider(Protocol):
    """Interface for proxy sources."""

    async def get_proxies(self) -> list[Proxy]: ...

    async def refresh(self) -> list[Proxy]: ...


# ---------------------------------------------------------------------------
# Concrete Providers
# ---------------------------------------------------------------------------


class FileProxyProvider:
    """Load proxies from a file (URL format one per line, or JSON)."""

    def __init__(self, filepath: str | Path, format: str = "url") -> None:
        self.filepath = Path(filepath)
        self.format = format

    async def get_proxies(self) -> list[Proxy]:
        return await asyncio.to_thread(self._load)

    async def refresh(self) -> list[Proxy]:
        return await self.get_proxies()

    def _load(self) -> list[Proxy]:
        proxies: list[Proxy] = []
        text = self.filepath.read_text()

        if self.format == "json":
            data = json.loads(text)
            for item in data:
                if isinstance(item, str):
                    proxies.append(Proxy.from_url(item))
                elif isinstance(item, dict):
                    proxies.append(Proxy(**item))
        else:
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        proxies.append(Proxy.from_url(line))
                    except ValueError:
                        logger.warning("Skipping invalid proxy line: %s", line)

        return proxies


class ListProxyProvider:
    """Create proxies from a list of URL strings."""

    def __init__(self, proxy_urls: list[str]) -> None:
        self.proxy_urls = proxy_urls

    async def get_proxies(self) -> list[Proxy]:
        return [Proxy.from_url(u) for u in self.proxy_urls]

    async def refresh(self) -> list[Proxy]:
        return await self.get_proxies()


class IPRoyalProxyProvider:
    """IPRoyal residential proxy provider.

    Uses IPRoyal's residential proxy gateway with session-based rotation.
    Endpoint: geo.iproyal.com:12321 (HTTP/HTTPS) or :32325 (SOCKS5).
    """

    DEFAULT_HOST = "geo.iproyal.com"
    HTTP_PORT = 12321
    SOCKS5_PORT = 32325

    def __init__(
        self,
        api_key: str,
        country: str = "",
        protocol: str = "http",
        num_sessions: int = 10,
        session_lifetime: str = "5m",
    ) -> None:
        self._api_key = api_key
        self._country = country
        self._protocol = protocol
        self._num_sessions = num_sessions
        self._session_lifetime = session_lifetime

    async def get_proxies(self) -> list[Proxy]:
        port = self.SOCKS5_PORT if self._protocol == "socks5" else self.HTTP_PORT
        proxies: list[Proxy] = []
        for i in range(self._num_sessions):
            # IPRoyal format: username_country-XX_session-ID_lifetime-5m
            username_parts = [self._api_key]
            if self._country:
                username_parts.append(f"country-{self._country}")
            username_parts.append(f"session-scraper{i}")
            username_parts.append(f"lifetime-{self._session_lifetime}")
            username = "_".join(username_parts)

            proxies.append(
                Proxy(
                    host=self.DEFAULT_HOST,
                    port=port,
                    username=username,
                    password=self._api_key,
                    protocol=self._protocol,
                    geo=self._country.upper() if self._country else None,
                    session_id=f"iproyal_{i}",
                )
            )
        return proxies

    async def refresh(self) -> list[Proxy]:
        return await self.get_proxies()


class RotatingProxyProvider:
    """Provider for rotating proxy services (e.g. BrightData, SmartProxy).

    These services use a single endpoint with session-based usernames to pin
    exit IPs for the duration of a session.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        protocol: str = "http",
        session_prefix: str = "session",
        num_sessions: int = 10,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.protocol = protocol
        self.session_prefix = session_prefix
        self.num_sessions = num_sessions

    async def get_proxies(self) -> list[Proxy]:
        proxies: list[Proxy] = []
        for i in range(self.num_sessions):
            session_user = f"{self.username}-{self.session_prefix}-{i}"
            proxies.append(
                Proxy(
                    host=self.host,
                    port=self.port,
                    username=session_user,
                    password=self.password,
                    protocol=self.protocol,
                    session_id=f"session_{i}",
                )
            )
        return proxies

    async def refresh(self) -> list[Proxy]:
        return await self.get_proxies()


# ---------------------------------------------------------------------------
# Sticky session record
# ---------------------------------------------------------------------------

@dataclass
class _StickyEntry:
    proxy_key: str
    expires: float


# ---------------------------------------------------------------------------
# ProxyAdapter
# ---------------------------------------------------------------------------


class ProxyAdapter:
    """Manages proxy pool with rotation strategies and health tracking.

    Strategies: weighted, round_robin, random, least_used.
    Supports sticky (domain-affinity) sessions and geo-targeting.
    """

    def __init__(
        self,
        proxies: Optional[list[Proxy]] = None,
        strategy: str = "weighted",
        cooldown_seconds: float = 60.0,
        max_failures: int = 5,
        sticky_session_duration: float = 600.0,
    ) -> None:
        self._proxies: list[Proxy] = proxies or []
        self._strategy = strategy
        self._cooldown_seconds = cooldown_seconds
        self._max_failures = max_failures
        self._sticky_session_duration = sticky_session_duration
        self._provider: Optional[ProxyProvider] = None

        # Round-robin index
        self._rr_index: int = 0

        # Domain -> sticky entry mapping
        self._sticky_sessions: dict[str, _StickyEntry] = {}

    # -- provider management -------------------------------------------------

    def set_provider(self, provider: ProxyProvider) -> None:
        """Set a proxy provider for automatic refresh."""
        self._provider = provider

    # -- pool mutation -------------------------------------------------------

    def add_proxy(self, proxy: Proxy) -> None:
        """Add a proxy to the pool."""
        self._proxies.append(proxy)

    def remove_proxy(self, proxy: Proxy) -> None:
        """Remove a proxy from the pool (matched by host:port)."""
        self._proxies = [
            p for p in self._proxies
            if not (p.host == proxy.host and p.port == proxy.port)
        ]

    # -- selection -----------------------------------------------------------

    def get_proxy(
        self,
        geo: Optional[str] = None,
        region: Optional[str] = None,
        domain: Optional[str] = None,
        sticky: bool = False,
    ) -> Optional[Proxy]:
        """Get next proxy based on rotation strategy.

        Args:
            geo: Filter by country code (matched against ``Proxy.geo``).
            region: Filter by region (matched against ``Proxy.region``).
            domain: Target domain — used together with *sticky*.
            sticky: When True, reuse the same proxy for *domain* within
                    the configured sticky session duration.
        """
        now = time.time()

        # Sticky session lookup
        if sticky and domain:
            entry = self._sticky_sessions.get(domain)
            if entry and entry.expires > now:
                for p in self._proxies:
                    key = f"{p.host}:{p.port}"
                    if key == entry.proxy_key and p.is_available:
                        p.last_used = now
                        return p

        # Build candidate list
        available = [p for p in self._proxies if p.is_available]
        if geo:
            available = [p for p in available if p.geo and p.geo.upper() == geo.upper()]
        if region:
            available = [p for p in available if p.region and p.region.upper() == region.upper()]

        if not available:
            logger.warning("No available proxies in pool")
            return None

        # Strategy dispatch
        if self._strategy == "round_robin":
            available.sort(key=lambda p: p.last_used)
            proxy = available[0]
        elif self._strategy == "random":
            proxy = random.choice(available)
        elif self._strategy == "least_used":
            available.sort(key=lambda p: p.total_requests)
            proxy = available[0]
        elif self._strategy == "weighted":
            weights = [max(p.score, 0.01) for p in available]
            proxy = random.choices(available, weights=weights, k=1)[0]
        else:
            proxy = available[0]

        proxy.last_used = now

        # Register sticky session
        if sticky and domain:
            self._sticky_sessions[domain] = _StickyEntry(
                proxy_key=f"{proxy.host}:{proxy.port}",
                expires=now + self._sticky_session_duration,
            )

        return proxy

    # -- reporting -----------------------------------------------------------

    def mark_success(self, proxy: Proxy, response_time: float = 0.0) -> None:
        """Record a successful proxy use."""
        proxy.total_requests += 1
        proxy.successful_requests += 1
        if response_time > 0:
            proxy.response_times.append(response_time)

    def mark_failure(self, proxy: Proxy) -> None:
        """Record a failed proxy use and apply cooldown if needed."""
        proxy.total_requests += 1
        proxy.failed_requests += 1

        if proxy.failed_requests >= self._max_failures:
            proxy.cooldown_until = time.time() + self._cooldown_seconds
            logger.info(
                "Proxy put on cooldown",
                extra={"proxy": proxy.host, "seconds": self._cooldown_seconds},
            )

    # -- bulk queries --------------------------------------------------------

    def get_best_proxies(self, n: int = 10) -> list[Proxy]:
        """Return the top *n* available proxies sorted by score (descending)."""
        available = [p for p in self._proxies if p.is_available]
        available.sort(key=lambda p: p.score, reverse=True)
        return available[:n]

    # -- refresh -------------------------------------------------------------

    async def refresh(self) -> None:
        """Refresh proxy pool from provider."""
        if self._provider:
            self._proxies = await self._provider.refresh()
            logger.info("Proxy pool refreshed", extra={"count": len(self._proxies)})

    # -- introspection -------------------------------------------------------

    @property
    def pool_size(self) -> int:
        return len(self._proxies)

    @property
    def available_count(self) -> int:
        return sum(1 for p in self._proxies if p.is_available)
