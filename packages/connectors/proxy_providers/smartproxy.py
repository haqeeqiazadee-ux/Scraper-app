"""
Smartproxy provider integration.

Supports residential and datacenter proxy pools with geo-targeting
down to the city level.

Config (env vars):
    SMARTPROXY_USERNAME — account username
    SMARTPROXY_PASSWORD — account password
    SMARTPROXY_ENDPOINT — proxy gateway (default: gate.smartproxy.com)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from packages.connectors.proxy_providers.base import ProxyInfo, ProxyUsage

logger = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = "gate.smartproxy.com"
_RESIDENTIAL_PORT = 7000
_DATACENTER_PORT = 10000
_API_BASE = "https://api.smartproxy.com/v1"


class SmartproxyProvider:
    """Smartproxy provider with residential and datacenter pool support."""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        endpoint: Optional[str] = None,
        pool_type: str = "residential",
    ) -> None:
        self._username = username or os.environ.get("SMARTPROXY_USERNAME", "")
        self._password = password or os.environ.get("SMARTPROXY_PASSWORD", "")
        self._endpoint = endpoint or os.environ.get("SMARTPROXY_ENDPOINT", _DEFAULT_ENDPOINT)
        self._pool_type = pool_type

        # Lazy HTTP client
        self._client: Any = None

        # Session counter
        self._session_counter = 0

    @property
    def name(self) -> str:
        return "smartproxy"

    async def _get_client(self) -> Any:
        """Lazy-initialize httpx async client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _get_port(self) -> int:
        """Return the proxy port based on pool type."""
        if self._pool_type == "datacenter":
            return _DATACENTER_PORT
        return _RESIDENTIAL_PORT

    def _build_username(
        self,
        country: Optional[str] = None,
        city: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Build Smartproxy formatted username.

        Format: user-country-{cc}-city-{city}-session-{sid}
        """
        parts = [self._username]
        if country:
            parts.append(f"country-{country.lower()}")
        if city:
            parts.append(f"city-{city.lower()}")
        if session_id:
            parts.append(f"session-{session_id}")
        return "-".join(parts)

    async def get_proxy(
        self,
        country: Optional[str] = None,
        city: Optional[str] = None,
        session_type: str = "rotating",
    ) -> ProxyInfo:
        """Get a Smartproxy proxy with optional geo-targeting.

        Args:
            country: ISO country code.
            city: City name for city-level targeting.
            session_type: 'rotating' or 'sticky'.
        """
        session_id: Optional[str] = None
        if session_type == "sticky":
            self._session_counter += 1
            session_id = f"sp_{self._session_counter}"

        username = self._build_username(
            country=country,
            city=city,
            session_id=session_id,
        )

        return ProxyInfo(
            host=self._endpoint,
            port=self._get_port(),
            username=username,
            password=self._password,
            protocol="http",
            country=country,
            city=city,
            session_id=session_id,
            provider_name=self.name,
            pool_type=self._pool_type,
            metadata={"endpoint": self._endpoint},
        )

    async def rotate(self) -> ProxyInfo:
        """Force rotation by getting a new rotating proxy."""
        return await self.get_proxy(session_type="rotating")

    async def health_check(self) -> bool:
        """Check connectivity to Smartproxy API."""
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{_API_BASE}/user",
                auth=(self._username, self._password),
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Smartproxy health check failed")
            return False

    async def get_bandwidth_usage(self) -> ProxyUsage:
        """Fetch bandwidth usage from Smartproxy API."""
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{_API_BASE}/subscriptions",
                auth=(self._username, self._password),
            )
            if resp.status_code == 200:
                data = resp.json()
                # Smartproxy returns subscription list
                if isinstance(data, list) and data:
                    sub = data[0]
                    return ProxyUsage(
                        bytes_used=int(sub.get("traffic_used", 0)),
                        bytes_limit=int(sub.get("traffic_limit", 0)),
                        provider_name=self.name,
                    )
        except Exception:
            logger.exception("Failed to fetch Smartproxy bandwidth usage")

        return ProxyUsage(provider_name=self.name)

    async def get_usage(self) -> ProxyUsage:
        """Alias for get_bandwidth_usage to satisfy protocol."""
        return await self.get_bandwidth_usage()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
