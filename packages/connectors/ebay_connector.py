"""
eBay Connector — product data via official eBay Browse API.

eBay's official API is FREE and provides excellent product data:
- Browse API: active listings, prices, images, seller info
- Marketplace Insights: sold item prices (Enterprise tier)
- Finding API: broad product search

No third-party service needed — the official API IS the Keepa equivalent.

Usage:
    connector = EbayConnector(app_id="your_app_id", cert_id="your_cert_id")
    products = await connector.search_products("wireless mouse", limit=20)
    product = await connector.get_product("v1|123456789|0")
"""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any, Optional

from packages.core.interfaces import ConnectorMetrics

logger = logging.getLogger(__name__)

# eBay API endpoints
EBAY_AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_BROWSE_URL = "https://api.ebay.com/buy/browse/v1"
EBAY_SANDBOX_BROWSE_URL = "https://api.sandbox.ebay.com/buy/browse/v1"


class EbayConnector:
    """eBay product data via official Browse API.

    Free tier: 5,000 calls/day. Enterprise tier: 1.5M/day.
    Covers: product search, item details, pricing, images, seller info.
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        cert_id: Optional[str] = None,
        sandbox: bool = False,
    ) -> None:
        self._app_id = app_id or os.environ.get("EBAY_APP_ID", "")
        self._cert_id = cert_id or os.environ.get("EBAY_CERT_ID", "")
        self._sandbox = sandbox
        self._access_token: Optional[str] = None
        self._token_expires: float = 0
        self._metrics = ConnectorMetrics()
        self._base_url = EBAY_SANDBOX_BROWSE_URL if sandbox else EBAY_BROWSE_URL

    async def _ensure_token(self) -> str:
        """Get or refresh OAuth2 client credentials token."""
        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        import httpx

        credentials = base64.b64encode(f"{self._app_id}:{self._cert_id}".encode()).decode()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                EBAY_AUTH_URL,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {credentials}",
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope",
                },
                timeout=15.0,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"eBay auth failed: {resp.status_code} {resp.text[:200]}")
            data = resp.json()
            self._access_token = data["access_token"]
            self._token_expires = time.time() + data.get("expires_in", 7200) - 60
            return self._access_token

    async def _request(self, path: str, params: Optional[dict] = None) -> dict:
        """Make authenticated request to eBay Browse API."""
        import httpx

        token = await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}{path}",
                headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"},
                params=params,
                timeout=15.0,
            )
            if resp.status_code != 200:
                logger.warning("eBay API error: %d %s", resp.status_code, resp.text[:200])
                return {}
            return resp.json()

    async def search_products(
        self,
        query: str,
        limit: int = 20,
        category_id: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        condition: Optional[str] = None,
        sort: str = "BEST_MATCH",
    ) -> list[dict]:
        """Search eBay listings.

        Args:
            query: Search keywords.
            limit: Max results (up to 200).
            category_id: eBay category ID filter.
            min_price: Minimum price filter.
            max_price: Maximum price filter.
            condition: NEW, USED, or UNSPECIFIED.
            sort: BEST_MATCH, PRICE, NEWLY_LISTED, ENDING_SOONEST.
        """
        self._metrics.total_requests += 1
        params: dict[str, Any] = {"q": query, "limit": min(limit, 200), "sort": sort}

        if category_id:
            params["category_ids"] = category_id

        filters = []
        if min_price is not None:
            filters.append(f"price:[{min_price}..],priceCurrency:USD")
        if max_price is not None:
            filters.append(f"price:[..{max_price}],priceCurrency:USD")
        if condition:
            filters.append(f"conditions:{{{condition}}}")
        if filters:
            params["filter"] = ",".join(filters)

        try:
            data = await self._request("/item_summary/search", params)
            items = data.get("itemSummaries", [])
            self._metrics.successful_requests += 1
            return [self._transform_item(item) for item in items]
        except Exception as e:
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            logger.warning("eBay search failed: %s", e)
            return []

    async def get_product(self, item_id: str) -> Optional[dict]:
        """Get detailed product data by eBay item ID."""
        self._metrics.total_requests += 1
        try:
            data = await self._request(f"/item/{item_id}")
            if data:
                self._metrics.successful_requests += 1
                return self._transform_detail(data)
            return None
        except Exception as e:
            self._metrics.failed_requests += 1
            logger.warning("eBay item lookup failed: %s", e)
            return None

    def _transform_item(self, item: dict) -> dict:
        """Transform eBay search result to standard format."""
        price_info = item.get("price", {})
        image = item.get("image", {})
        seller = item.get("seller", {})

        return {
            "name": item.get("title", ""),
            "item_id": item.get("itemId", ""),
            "price": price_info.get("value", ""),
            "currency": price_info.get("currency", "USD"),
            "condition": item.get("condition", ""),
            "image_url": image.get("imageUrl", ""),
            "product_url": item.get("itemWebUrl", ""),
            "seller_name": seller.get("username", ""),
            "seller_feedback": seller.get("feedbackPercentage", ""),
            "seller_feedback_score": seller.get("feedbackScore", 0),
            "buying_options": item.get("buyingOptions", []),
            "shipping": self._extract_shipping(item),
            "location": item.get("itemLocation", {}).get("country", ""),
            "category": item.get("categories", [{}])[0].get("categoryName", "") if item.get("categories") else "",
            "source": "ebay_api",
            "platform": "ebay",
        }

    def _transform_detail(self, item: dict) -> dict:
        """Transform eBay item detail to standard format."""
        result = self._transform_item(item)
        result["description"] = item.get("shortDescription", "") or item.get("description", ""),
        result["brand"] = item.get("brand", ""),
        result["mpn"] = item.get("mpn", ""),
        result["gtin"] = item.get("gtin", ""),
        result["estimated_availabilities"] = item.get("estimatedAvailabilities", [])
        return result

    def _extract_shipping(self, item: dict) -> str:
        """Extract shipping info."""
        options = item.get("shippingOptions", [])
        if options:
            cost = options[0].get("shippingCost", {})
            if cost.get("value") == "0.00":
                return "Free Shipping"
            return f"${cost.get('value', '?')} shipping"
        return ""

    def get_metrics(self) -> ConnectorMetrics:
        return self._metrics

    async def health_check(self) -> bool:
        try:
            await self._ensure_token()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        self._access_token = None
