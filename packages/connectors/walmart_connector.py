"""
Walmart Connector — product data via official Affiliate API + Rainforest fallback.

Tier 1: Walmart Affiliate API (FREE — needs affiliate account)
  - Product search, item details, pricing, stock
  - 20 calls/sec, 5,000 calls/day

Tier 2: Rainforest API ($49+/mo — for reviews, price history, heavy volume)
  - Full product details, individual reviews, category browsing

Usage:
    connector = WalmartConnector(api_key="your_affiliate_api_key")
    products = await connector.search_products("wireless mouse", limit=20)
    product = await connector.get_product("123456789")
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from packages.core.interfaces import ConnectorMetrics

logger = logging.getLogger(__name__)

WALMART_API_BASE = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2"
RAINFOREST_API_BASE = "https://api.rainforestapi.com/request"


class WalmartConnector:
    """Walmart product data — Affiliate API (free) + Rainforest API (paid fallback)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        rainforest_key: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("WALMART_API_KEY", "")
        self._rainforest_key = rainforest_key or os.environ.get("RAINFOREST_API_KEY", "")
        self._metrics = ConnectorMetrics()

    async def search_products(
        self,
        query: str,
        limit: int = 20,
        category_id: Optional[str] = None,
        sort: str = "relevance",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> list[dict]:
        """Search Walmart products."""
        self._metrics.total_requests += 1

        # Tier 1: Walmart Affiliate API
        if self._api_key:
            results = await self._search_affiliate(query, limit, category_id, sort, min_price, max_price)
            if results:
                return results

        # Tier 2: Rainforest API
        if self._rainforest_key:
            results = await self._search_rainforest(query, limit)
            if results:
                return results

        self._metrics.failed_requests += 1
        logger.warning("No Walmart API configured")
        return []

    async def get_product(self, item_id: str) -> Optional[dict]:
        """Get product details by Walmart item ID."""
        self._metrics.total_requests += 1

        if self._api_key:
            result = await self._get_affiliate(item_id)
            if result:
                return result

        if self._rainforest_key:
            result = await self._get_rainforest(item_id)
            if result:
                return result

        return None

    async def _search_affiliate(self, query: str, limit: int, category_id: Optional[str],
                                 sort: str, min_price: Optional[float], max_price: Optional[float]) -> list[dict]:
        """Search via Walmart Affiliate API (FREE)."""
        import httpx

        params: dict[str, Any] = {
            "query": query,
            "numItems": min(limit, 25),
            "sort": sort,
            "format": "json",
            "apiKey": self._api_key,
        }
        if category_id:
            params["categoryId"] = category_id
        if min_price is not None:
            params["minPrice"] = min_price
        if max_price is not None:
            params["maxPrice"] = max_price

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{WALMART_API_BASE}/search", params=params)
                if resp.status_code != 200:
                    logger.warning("Walmart API error: %d", resp.status_code)
                    return []
                data = resp.json()
                items = data.get("items", [])
                self._metrics.successful_requests += 1
                return [self._transform_affiliate_item(item) for item in items]
        except Exception as e:
            logger.warning("Walmart search failed: %s", e)
            return []

    async def _get_affiliate(self, item_id: str) -> Optional[dict]:
        """Get item via Walmart Affiliate API."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{WALMART_API_BASE}/items/{item_id}",
                    params={"format": "json", "apiKey": self._api_key},
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                self._metrics.successful_requests += 1
                return self._transform_affiliate_item(data)
        except Exception as e:
            logger.warning("Walmart item lookup failed: %s", e)
            return None

    async def _search_rainforest(self, query: str, limit: int) -> list[dict]:
        """Search via Rainforest API (paid fallback)."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(RAINFOREST_API_BASE, params={
                    "api_key": self._rainforest_key,
                    "type": "search",
                    "source": "walmart",
                    "search_term": query,
                })
                if resp.status_code != 200:
                    return []
                data = resp.json()
                results = data.get("search_results", [])
                self._metrics.successful_requests += 1
                return [self._transform_rainforest_item(r) for r in results[:limit]]
        except Exception as e:
            logger.warning("Rainforest search failed: %s", e)
            return []

    async def _get_rainforest(self, item_id: str) -> Optional[dict]:
        """Get item via Rainforest API."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(RAINFOREST_API_BASE, params={
                    "api_key": self._rainforest_key,
                    "type": "product",
                    "source": "walmart",
                    "item_id": item_id,
                })
                if resp.status_code != 200:
                    return None
                data = resp.json()
                product = data.get("product", {})
                self._metrics.successful_requests += 1
                return self._transform_rainforest_item(product)
        except Exception as e:
            logger.warning("Rainforest item lookup failed: %s", e)
            return None

    def _transform_affiliate_item(self, item: dict) -> dict:
        """Transform Walmart Affiliate API item to standard format."""
        return {
            "name": item.get("name", ""),
            "item_id": str(item.get("itemId", "")),
            "price": str(item.get("salePrice", item.get("msrp", ""))),
            "original_price": str(item.get("msrp", "")),
            "currency": "USD",
            "image_url": item.get("largeImage", item.get("mediumImage", item.get("thumbnailImage", ""))),
            "product_url": item.get("productUrl", item.get("productTrackingUrl", "")),
            "category": item.get("categoryPath", ""),
            "brand": item.get("brandName", ""),
            "rating": item.get("customerRating", ""),
            "reviews_count": str(item.get("numReviews", "")),
            "stock_status": "InStock" if item.get("stock") == "Available" else item.get("stock", ""),
            "upc": item.get("upc", ""),
            "model": item.get("modelNumber", ""),
            "short_description": item.get("shortDescription", ""),
            "seller": item.get("sellerInfo", "Walmart.com"),
            "shipping": "Free Shipping" if item.get("freeShippingOver35Dollars") else "",
            "source": "walmart_affiliate_api",
            "platform": "walmart",
        }

    def _transform_rainforest_item(self, item: dict) -> dict:
        """Transform Rainforest API item to standard format."""
        return {
            "name": item.get("title", item.get("name", "")),
            "item_id": str(item.get("item_id", item.get("id", ""))),
            "price": str(item.get("price", {}).get("value", "")) if isinstance(item.get("price"), dict) else str(item.get("price", "")),
            "currency": "USD",
            "image_url": item.get("main_image", {}).get("link", "") if isinstance(item.get("main_image"), dict) else item.get("image", ""),
            "product_url": item.get("link", ""),
            "rating": str(item.get("rating", "")),
            "reviews_count": str(item.get("ratings_total", "")),
            "brand": item.get("brand", ""),
            "source": "rainforest_api",
            "platform": "walmart",
        }

    def get_metrics(self) -> ConnectorMetrics:
        return self._metrics

    async def health_check(self) -> bool:
        return bool(self._api_key or self._rainforest_key)

    async def close(self) -> None:
        pass
