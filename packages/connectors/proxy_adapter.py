"""
Proxy Adapter — unified proxy management with rotation strategies.

Ported and refactored from scraper_pro/proxy_manager.py.
Supports file-based, API-based, and inline proxy sources.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
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
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_used: float = 0.0
    cooldown_until: float = 0.0
    response_times: list[float] = field(default_factory=list)

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


@runtime_checkable
class ProxyProvider(Protocol):
    """Interface for proxy sources."""

    async def get_proxies(self) -> list[Proxy]: ...

    async def refresh(self) -> list[Proxy]: ...


class ProxyAdapter:
    """Manages proxy pool with rotation strategies and health tracking."""

    def __init__(
        self,
        proxies: Optional[list[Proxy]] = None,
        strategy: str = "weighted",
        cooldown_seconds: float = 60.0,
        max_failures: int = 5,
    ) -> None:
        self._proxies: list[Proxy] = proxies or []
        self._strategy = strategy
        self._cooldown_seconds = cooldown_seconds
        self._max_failures = max_failures
        self._provider: Optional[ProxyProvider] = None

    def set_provider(self, provider: ProxyProvider) -> None:
        """Set a proxy provider for automatic refresh."""
        self._provider = provider

    def add_proxy(self, proxy: Proxy) -> None:
        """Add a proxy to the pool."""
        self._proxies.append(proxy)

    def get_proxy(self, geo: Optional[str] = None) -> Optional[Proxy]:
        """Get next proxy based on rotation strategy."""
        available = [p for p in self._proxies if p.is_available]
        if geo:
            available = [p for p in available if p.geo == geo]

        if not available:
            logger.warning("No available proxies in pool")
            return None

        if self._strategy == "round_robin":
            # Sort by last_used, pick oldest
            available.sort(key=lambda p: p.last_used)
            proxy = available[0]
        elif self._strategy == "random":
            proxy = random.choice(available)
        elif self._strategy == "weighted":
            # Weighted by score
            weights = [max(p.score, 0.01) for p in available]
            proxy = random.choices(available, weights=weights, k=1)[0]
        else:
            proxy = available[0]

        proxy.last_used = time.time()
        return proxy

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

        consecutive_failures = proxy.failed_requests - proxy.successful_requests
        if consecutive_failures >= self._max_failures:
            proxy.cooldown_until = time.time() + self._cooldown_seconds
            logger.info("Proxy put on cooldown", extra={"proxy": proxy.host, "seconds": self._cooldown_seconds})

    async def refresh(self) -> None:
        """Refresh proxy pool from provider."""
        if self._provider:
            self._proxies = await self._provider.refresh()
            logger.info("Proxy pool refreshed", extra={"count": len(self._proxies)})

    @property
    def pool_size(self) -> int:
        return len(self._proxies)

    @property
    def available_count(self) -> int:
        return sum(1 for p in self._proxies if p.is_available)
