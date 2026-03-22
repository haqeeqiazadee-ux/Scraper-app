"""
Base protocol and shared types for proxy providers.

All proxy provider implementations must satisfy the ProxyProviderProtocol.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class ProxyInfo:
    """Standardized proxy information returned by all providers."""

    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"  # http, https, socks5
    country: Optional[str] = None
    city: Optional[str] = None
    session_id: Optional[str] = None
    provider_name: str = ""
    pool_type: str = "residential"  # residential, datacenter, isp
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def url(self) -> str:
        """Build proxy URL string."""
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.protocol}://{auth}{self.host}:{self.port}"

    @property
    def display(self) -> str:
        """Human-readable representation (no credentials)."""
        geo = f" [{self.country}]" if self.country else ""
        return f"{self.protocol}://{self.host}:{self.port}{geo}"


@dataclass
class ProxyUsage:
    """Bandwidth and usage statistics from a proxy provider."""

    bytes_used: int = 0
    bytes_limit: int = 0
    requests_used: int = 0
    requests_limit: int = 0
    active_sessions: int = 0
    provider_name: str = ""

    @property
    def bytes_remaining(self) -> int:
        if self.bytes_limit <= 0:
            return -1  # unlimited
        return max(0, self.bytes_limit - self.bytes_used)

    @property
    def usage_percent(self) -> float:
        if self.bytes_limit <= 0:
            return 0.0
        return min(100.0, (self.bytes_used / self.bytes_limit) * 100)


@runtime_checkable
class ProxyProviderProtocol(Protocol):
    """Interface all proxy providers must satisfy."""

    @property
    def name(self) -> str:
        """Provider display name."""
        ...

    async def get_proxy(
        self,
        country: Optional[str] = None,
        session_type: str = "rotating",
    ) -> ProxyInfo:
        """Get a proxy, optionally filtered by country.

        Args:
            country: ISO 3166-1 alpha-2 country code (e.g. 'US', 'GB').
            session_type: 'rotating' for new IP each request, 'sticky' for
                          persistent session IP.
        """
        ...

    async def rotate(self) -> ProxyInfo:
        """Force rotation to a new proxy IP."""
        ...

    async def health_check(self) -> bool:
        """Verify provider credentials and connectivity."""
        ...

    async def get_usage(self) -> ProxyUsage:
        """Return current bandwidth / request usage."""
        ...
