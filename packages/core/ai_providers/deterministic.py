"""
Deterministic provider — rule-based extraction without AI.

Uses CSS selectors, JSON-LD, regex patterns as fallback when
AI providers are unavailable or unnecessary.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from packages.core.ai_providers.base import BaseAIProvider

logger = logging.getLogger(__name__)

# Common CSS selectors for product data
PRODUCT_SELECTORS = {
    "name": [
        'h1[itemprop="name"]', "h1.product-title", "h1.product-name",
        "h1.product_title", ".product-info h1", "#product-name", "h1",
    ],
    "price": [
        '[itemprop="price"]', ".price", ".product-price", ".current-price",
        "#price", ".offer-price", "span.price",
    ],
}

# Regex patterns for common data
PRICE_PATTERN = re.compile(r'[\$\£\€\₹]?\s*(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d{2})?)')
CURRENCY_PATTERN = re.compile(r'(USD|EUR|GBP|PKR|INR|AUD|CAD)')


class DeterministicProvider(BaseAIProvider):
    """Rule-based extraction without AI dependencies."""

    def __init__(self) -> None:
        super().__init__(name="deterministic")

    async def extract(self, html: str, url: str, prompt: Optional[str] = None) -> list[dict]:
        """Extract structured data using deterministic methods."""
        products = []

        # 1. Try JSON-LD extraction (most reliable)
        jsonld_products = self._extract_jsonld(html)
        if jsonld_products:
            return jsonld_products

        # 2. Try basic HTML pattern matching
        basic = self._extract_basic(html, url)
        if basic:
            products.append(basic)

        return products

    async def classify(self, text: str, labels: list[str]) -> str:
        """Simple keyword-based classification."""
        text_lower = text.lower()
        scores = {}
        for label in labels:
            scores[label] = text_lower.count(label.lower())
        return max(scores, key=scores.get) if scores else labels[0]

    async def normalize(self, data: dict, target_schema: dict) -> dict:
        """Basic field mapping normalization."""
        normalized = {}
        field_aliases = {
            "product_name": "name", "title": "name", "product_title": "name",
            "cost": "price", "amount": "price", "product_price": "price",
            "img": "image_url", "image": "image_url", "photo": "image_url",
            "link": "product_url", "href": "product_url",
        }
        for key, value in data.items():
            mapped_key = field_aliases.get(key.lower(), key)
            normalized[mapped_key] = value
        return normalized

    def _extract_jsonld(self, html: str) -> list[dict]:
        """Extract product data from JSON-LD script tags."""
        products = []
        pattern = re.compile(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            try:
                data = json.loads(match.group(1).strip())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and item.get("@type") in ("Product", "IndividualProduct"):
                        product = {
                            "name": item.get("name", ""),
                            "description": item.get("description", ""),
                            "brand": item.get("brand", {}).get("name", "") if isinstance(item.get("brand"), dict) else str(item.get("brand", "")),
                            "sku": item.get("sku", ""),
                            "image_url": item.get("image", ""),
                            "product_url": url if (url := item.get("url", "")) else "",
                        }
                        # Extract price from offers
                        offers = item.get("offers", {})
                        if isinstance(offers, dict):
                            product["price"] = offers.get("price", "")
                            product["currency"] = offers.get("priceCurrency", "")
                            product["stock_status"] = offers.get("availability", "")
                        elif isinstance(offers, list) and offers:
                            product["price"] = offers[0].get("price", "")
                            product["currency"] = offers[0].get("priceCurrency", "")

                        # Extract rating
                        rating = item.get("aggregateRating", {})
                        if isinstance(rating, dict):
                            product["rating"] = rating.get("ratingValue", "")
                            product["reviews_count"] = rating.get("reviewCount", "")

                        products.append(product)
            except (json.JSONDecodeError, AttributeError):
                continue
        return products

    def _extract_basic(self, html: str, url: str) -> dict:
        """Basic regex-based extraction as last resort."""
        result = {"product_url": url}

        # Extract title from <title> tag
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            result["name"] = title_match.group(1).strip()

        # Extract prices
        prices = PRICE_PATTERN.findall(html)
        if prices:
            # Take the most common price-like value
            result["price"] = prices[0].replace(",", "")

        # Extract currency
        currency_match = CURRENCY_PATTERN.search(html)
        if currency_match:
            result["currency"] = currency_match.group(1)

        return result
