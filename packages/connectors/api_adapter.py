"""
API Adapter — connector for known platform APIs (Shopify, WooCommerce, RSS feeds).

Implements the Connector protocol for the API execution lane.
"""

from __future__ import annotations

import logging
from typing import Optional

from packages.core.interfaces import Connector, ConnectorMetrics, FetchRequest, FetchResponse

logger = logging.getLogger(__name__)


class ApiAdapter:
    """API connector for known e-commerce and data platform APIs."""

    def __init__(self, api_type: str = "generic", api_key: Optional[str] = None) -> None:
        self._api_type = api_type
        self._api_key = api_key
        self._metrics = ConnectorMetrics()
        self._client = None

    async def _get_client(self):  # type: ignore[no-untyped-def]
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch data from an API endpoint."""
        import httpx

        client = await self._get_client()
        self._metrics.total_requests += 1

        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        headers.update(request.headers)

        try:
            response = await client.request(
                method=request.method,
                url=request.url,
                headers=headers,
                timeout=httpx.Timeout(request.timeout_ms / 1000),
            )
            self._metrics.successful_requests += 1
            text = response.text
            return FetchResponse(
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                text=text,
                body=response.content,
                elapsed_ms=int(response.elapsed.total_seconds() * 1000) if response.elapsed else 0,
            )
        except Exception as e:
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            logger.warning("API fetch failed", extra={"url": request.url, "error": str(e)})
            return FetchResponse(url=request.url, status_code=0, error=str(e))

    async def health_check(self) -> bool:
        return True

    def get_metrics(self) -> ConnectorMetrics:
        return self._metrics

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
