"""
Bright Data (formerly Luminati) proxy provider integration.

Uses Bright Data's super proxy infrastructure for residential,
datacenter, and ISP proxy access with zone management.

Config (env vars):
    BRIGHTDATA_CUSTOMER_ID — account customer ID
    BRIGHTDATA_ZONE — proxy zone name (default: residential)
    BRIGHTDATA_PASSWORD — zone password
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Optional

from packages.connectors.proxy_providers.base import ProxyInfo, ProxyUsage

logger = logging.getLogger(__name__)

_SUPER_PROXY_HOST = "brd.superproxy.io"
_SUPER_PROXY_PORT = 22225
_API_BASE = "https://api.brightdata.com"


class BrightDataProvider:
    """Bright Data proxy provider with zone management and session control."""

    def __init__(
        self,
        customer_id: Optional[str] = None,
        zone: Optional[str] = None,
        password: Optional[str] = None,
        super_proxy_host: str = _SUPER_PROXY_HOST,
        super_proxy_port: int = _SUPER_PROXY_PORT,
    ) -> None:
        self._customer_id = customer_id or os.environ.get("BRIGHTDATA_CUSTOMER_ID", "")
        self._zone = zone or os.environ.get("BRIGHTDATA_ZONE", "residential")
        self._password = password or os.environ.get("BRIGHTDATA_PASSWORD", "")
        self._host = super_proxy_host
        self._port = super_proxy_port

        # Lazy HTTP client
        self._client: Any = None

        # Session counter for sticky sessions
        self._session_counter = 0

    @property
    def name(self) -> str:
        return "brightdata"

    async def _get_client(self) -> Any:
        """Lazy-initialize httpx async client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _build_username(
        self,
        country: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Build Bright Data formatted username with targeting options.

        Format: brd-customer-{id}-zone-{zone}[-country-{cc}][-session-{sid}]
        """
        parts = [
            f"brd-customer-{self._customer_id}",
            f"zone-{self._zone}",
        ]
        if country:
            parts.append(f"country-{country.lower()}")
        if session_id:
            parts.append(f"session-{session_id}")
        return "-".join(parts)

    async def get_proxy(
        self,
        country: Optional[str] = None,
        session_type: str = "rotating",
    ) -> ProxyInfo:
        """Get a Bright Data proxy.

        Args:
            country: ISO country code for geo-targeting.
            session_type: 'rotating' or 'sticky'.
        """
        session_id: Optional[str] = None
        if session_type == "sticky":
            self._session_counter += 1
            session_id = f"sess_{self._session_counter}"

        username = self._build_username(country=country, session_id=session_id)

        return ProxyInfo(
            host=self._host,
            port=self._port,
            username=username,
            password=self._password,
            protocol="http",
            country=country,
            session_id=session_id,
            provider_name=self.name,
            pool_type="residential",
            metadata={"zone": self._zone, "customer_id": self._customer_id},
        )

    async def rotate(self) -> ProxyInfo:
        """Force rotation by generating a new random session."""
        return await self.get_proxy(session_type="rotating")

    async def validate_credentials(self) -> bool:
        """Validate credentials against the Bright Data API."""
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{_API_BASE}/zone/get_status",
                params={"zone": self._zone, "customer": self._customer_id},
                headers={"Authorization": f"Bearer {self._password}"},
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Bright Data credential validation failed")
            return False

    async def health_check(self) -> bool:
        """Check provider health via credential validation."""
        return await self.validate_credentials()

    async def get_usage(self) -> ProxyUsage:
        """Fetch bandwidth usage from Bright Data API."""
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{_API_BASE}/zone/bw",
                params={"zone": self._zone, "customer": self._customer_id},
                headers={"Authorization": f"Bearer {self._password}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return ProxyUsage(
                    bytes_used=int(data.get("bw", 0)),
                    bytes_limit=int(data.get("bw_limit", 0)),
                    provider_name=self.name,
                )
        except Exception:
            logger.exception("Failed to fetch Bright Data usage")

        return ProxyUsage(provider_name=self.name)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
