"""
Oxylabs proxy provider integration.

Supports residential, datacenter, and ISP proxy pools with
real-time usage statistics.

Config (env vars):
    OXYLABS_USERNAME — account username
    OXYLABS_PASSWORD — account password
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from packages.connectors.proxy_providers.base import ProxyInfo, ProxyUsage

logger = logging.getLogger(__name__)

_RESIDENTIAL_HOST = "pr.oxylabs.io"
_DATACENTER_HOST = "dc.pr.oxylabs.io"
_ISP_HOST = "isp.oxylabs.io"
_DEFAULT_PORT = 7777
_API_BASE = "https://api.oxylabs.io/v1"

_POOL_HOSTS = {
    "residential": _RESIDENTIAL_HOST,
    "datacenter": _DATACENTER_HOST,
    "isp": _ISP_HOST,
}


class OxylabsProvider:
    """Oxylabs proxy provider with residential, datacenter, and ISP pools."""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        pool_type: str = "residential",
    ) -> None:
        self._username = username or os.environ.get("OXYLABS_USERNAME", "")
        self._password = password or os.environ.get("OXYLABS_PASSWORD", "")
        self._pool_type = pool_type

        # Lazy HTTP client
        self._client: Any = None

        # Session counter
        self._session_counter = 0

    @property
    def name(self) -> str:
        return "oxylabs"

    async def _get_client(self) -> Any:
        """Lazy-initialize httpx async client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _get_host(self) -> str:
        """Return proxy host based on pool type."""
        return _POOL_HOSTS.get(self._pool_type, _RESIDENTIAL_HOST)

    def _build_username(
        self,
        country: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Build Oxylabs formatted username.

        Format: customer-{user}-cc-{CC}[-sessid-{sid}]
        """
        parts = [f"customer-{self._username}"]
        if country:
            parts.append(f"cc-{country.upper()}")
        if session_id:
            parts.append(f"sessid-{session_id}")
        return "-".join(parts)

    async def get_proxy(
        self,
        country: Optional[str] = None,
        session_type: str = "rotating",
    ) -> ProxyInfo:
        """Get an Oxylabs proxy.

        Args:
            country: ISO country code for geo-targeting.
            session_type: 'rotating' or 'sticky'.
        """
        session_id: Optional[str] = None
        if session_type == "sticky":
            self._session_counter += 1
            session_id = f"oxy_{self._session_counter}"

        username = self._build_username(country=country, session_id=session_id)

        return ProxyInfo(
            host=self._get_host(),
            port=_DEFAULT_PORT,
            username=username,
            password=self._password,
            protocol="http",
            country=country,
            session_id=session_id,
            provider_name=self.name,
            pool_type=self._pool_type,
            metadata={"pool": self._pool_type},
        )

    async def rotate(self) -> ProxyInfo:
        """Force rotation by getting a new rotating proxy."""
        return await self.get_proxy(session_type="rotating")

    async def health_check(self) -> bool:
        """Verify credentials via Oxylabs API."""
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{_API_BASE}/user",
                auth=(self._username, self._password),
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Oxylabs health check failed")
            return False

    async def get_realtime_stats(self) -> dict[str, Any]:
        """Fetch real-time proxy usage statistics from Oxylabs API."""
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{_API_BASE}/stats/realtime",
                auth=(self._username, self._password),
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            logger.exception("Failed to fetch Oxylabs realtime stats")
        return {}

    async def get_usage(self) -> ProxyUsage:
        """Return current usage statistics."""
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{_API_BASE}/stats/traffic",
                auth=(self._username, self._password),
            )
            if resp.status_code == 200:
                data = resp.json()
                return ProxyUsage(
                    bytes_used=int(data.get("traffic_used", 0)),
                    bytes_limit=int(data.get("traffic_limit", 0)),
                    requests_used=int(data.get("requests_used", 0)),
                    requests_limit=int(data.get("requests_limit", 0)),
                    provider_name=self.name,
                )
        except Exception:
            logger.exception("Failed to fetch Oxylabs usage")

        return ProxyUsage(provider_name=self.name)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
