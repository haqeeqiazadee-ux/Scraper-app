"""
TikTok Connector — shop product data via TikTok Shop API + Piloterr fallback.

Tier 1: TikTok Shop Open Platform API (FREE — needs partner approval)
  - Product listings, prices, variants, categories
  - Only for shops that authorize your app

Tier 2: Piloterr API ($49-299/mo — third-party, broader coverage)
  - TikTok user profiles, video data, shop product listings

Direct scraping is NOT recommended — TikTok has aggressive anti-bot
(encrypted signatures, device fingerprinting, rapid rotation).

Usage:
    connector = TikTokConnector(piloterr_key="your_key")
    products = await connector.search_shop_products("shop_id", limit=20)
    profile = await connector.get_user_profile("username")
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from packages.core.interfaces import ConnectorMetrics

logger = logging.getLogger(__name__)

PILOTERR_BASE = "https://piloterr.com/api/v2"
TIKTOK_SHOP_API_BASE = "https://open-api.tiktokglobalshop.com"


class TikTokConnector:
    """TikTok data via Shop API + Piloterr fallback.

    Tier 1: TikTok Shop Open Platform (free, gated access)
    Tier 2: Piloterr API ($49+/mo, broader coverage)
    """

    def __init__(
        self,
        shop_app_key: Optional[str] = None,
        shop_app_secret: Optional[str] = None,
        shop_access_token: Optional[str] = None,
        piloterr_key: Optional[str] = None,
    ) -> None:
        self._shop_app_key = shop_app_key or os.environ.get("TIKTOK_SHOP_APP_KEY", "")
        self._shop_app_secret = shop_app_secret or os.environ.get("TIKTOK_SHOP_APP_SECRET", "")
        self._shop_access_token = shop_access_token or os.environ.get("TIKTOK_SHOP_ACCESS_TOKEN", "")
        self._piloterr_key = piloterr_key or os.environ.get("PILOTERR_API_KEY", "")
        self._metrics = ConnectorMetrics()

    async def search_shop_products(
        self,
        keyword: str,
        limit: int = 20,
    ) -> list[dict]:
        """Search TikTok Shop products."""
        self._metrics.total_requests += 1

        # Tier 1: TikTok Shop API
        if self._shop_access_token:
            results = await self._search_shop_api(keyword, limit)
            if results:
                return results

        # Tier 2: Piloterr
        if self._piloterr_key:
            results = await self._search_piloterr_shop(keyword, limit)
            if results:
                return results

        self._metrics.failed_requests += 1
        logger.warning("No TikTok API configured")
        return []

    async def get_user_profile(self, username: str) -> Optional[dict]:
        """Get TikTok user profile data."""
        self._metrics.total_requests += 1

        if self._piloterr_key:
            return await self._get_piloterr_user(username)
        return None

    async def get_video_data(self, video_url: str) -> Optional[dict]:
        """Get TikTok video metadata."""
        self._metrics.total_requests += 1

        if self._piloterr_key:
            return await self._get_piloterr_video(video_url)
        return None

    async def get_trending_products(self, region: str = "US", limit: int = 20) -> list[dict]:
        """Get trending TikTok Shop products."""
        self._metrics.total_requests += 1

        if self._piloterr_key:
            return await self._get_piloterr_trending(region, limit)
        return []

    # ---- Tier 1: TikTok Shop API ------------------------------------------

    async def _search_shop_api(self, keyword: str, limit: int) -> list[dict]:
        """Search via TikTok Shop Open Platform API."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{TIKTOK_SHOP_API_BASE}/product/202309/products/search",
                    headers={
                        "x-tts-access-token": self._shop_access_token,
                        "Content-Type": "application/json",
                    },
                    json={"keyword": keyword, "page_size": min(limit, 100)},
                )
                if resp.status_code != 200:
                    logger.debug("TikTok Shop API: %d", resp.status_code)
                    return []
                data = resp.json()
                products = data.get("data", {}).get("products", [])
                self._metrics.successful_requests += 1
                return [self._transform_shop_product(p) for p in products]
        except Exception as e:
            logger.debug("TikTok Shop API failed: %s", e)
            return []

    def _transform_shop_product(self, p: dict) -> dict:
        """Transform TikTok Shop product to standard format."""
        skus = p.get("skus", [])
        price = ""
        if skus:
            price_info = skus[0].get("price", {})
            price = price_info.get("sale_price", price_info.get("original_price", ""))

        images = p.get("main_images", [])
        return {
            "name": p.get("title", ""),
            "product_id": p.get("id", ""),
            "price": str(price),
            "currency": p.get("currency", "USD"),
            "image_url": images[0].get("url", "") if images else "",
            "category": p.get("category_name", ""),
            "status": p.get("status", ""),
            "variants": len(skus),
            "source": "tiktok_shop_api",
            "platform": "tiktok",
        }

    # ---- Tier 2: Piloterr API ---------------------------------------------

    async def _piloterr_request(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        """Make request to Piloterr API."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{PILOTERR_BASE}{endpoint}",
                    headers={"x-api-key": self._piloterr_key},
                    params=params,
                )
                if resp.status_code != 200:
                    return None
                return resp.json()
        except Exception as e:
            logger.debug("Piloterr request failed: %s", e)
            return None

    async def _search_piloterr_shop(self, keyword: str, limit: int) -> list[dict]:
        """Search TikTok Shop via Piloterr."""
        data = await self._piloterr_request("/tiktok/shop/search", {"keyword": keyword, "limit": limit})
        if not data:
            return []
        products = data.get("products", data.get("items", []))
        self._metrics.successful_requests += 1
        return [self._transform_piloterr_product(p) for p in products[:limit]]

    async def _get_piloterr_user(self, username: str) -> Optional[dict]:
        """Get user profile via Piloterr."""
        data = await self._piloterr_request("/tiktok/user", {"username": username})
        if not data:
            return None
        self._metrics.successful_requests += 1
        return {
            "username": data.get("username", username),
            "display_name": data.get("nickname", ""),
            "bio": data.get("signature", ""),
            "followers": data.get("follower_count", 0),
            "following": data.get("following_count", 0),
            "likes": data.get("heart_count", 0),
            "videos": data.get("video_count", 0),
            "verified": data.get("verified", False),
            "avatar": data.get("avatar_url", ""),
            "source": "piloterr",
            "platform": "tiktok",
        }

    async def _get_piloterr_video(self, video_url: str) -> Optional[dict]:
        """Get video data via Piloterr."""
        data = await self._piloterr_request("/tiktok/video", {"url": video_url})
        if not data:
            return None
        self._metrics.successful_requests += 1
        return {
            "video_id": data.get("id", ""),
            "description": data.get("desc", ""),
            "likes": data.get("digg_count", 0),
            "comments": data.get("comment_count", 0),
            "shares": data.get("share_count", 0),
            "plays": data.get("play_count", 0),
            "author": data.get("author", {}).get("nickname", ""),
            "music": data.get("music", {}).get("title", ""),
            "source": "piloterr",
            "platform": "tiktok",
        }

    async def _get_piloterr_trending(self, region: str, limit: int) -> list[dict]:
        """Get trending products via Piloterr."""
        data = await self._piloterr_request("/tiktok/shop/trending", {"region": region, "limit": limit})
        if not data:
            return []
        products = data.get("products", [])
        self._metrics.successful_requests += 1
        return [self._transform_piloterr_product(p) for p in products[:limit]]

    def _transform_piloterr_product(self, p: dict) -> dict:
        """Transform Piloterr product to standard format."""
        return {
            "name": p.get("title", p.get("name", "")),
            "product_id": p.get("id", ""),
            "price": str(p.get("price", "")),
            "image_url": p.get("image", p.get("cover", "")),
            "rating": p.get("rating", ""),
            "sold": p.get("sold", 0),
            "shop_name": p.get("shop_name", ""),
            "product_url": p.get("url", ""),
            "source": "piloterr",
            "platform": "tiktok",
        }

    def get_metrics(self) -> ConnectorMetrics:
        return self._metrics

    async def health_check(self) -> bool:
        return bool(self._shop_access_token or self._piloterr_key)

    async def close(self) -> None:
        pass
