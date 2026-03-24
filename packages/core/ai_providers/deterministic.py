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

    async def extract(
        self,
        html: str,
        url: str,
        prompt: Optional[str] = None,
        css_selectors: Optional[dict] = None,
    ) -> list[dict]:
        """Extract structured data using deterministic methods.

        Args:
            html: Raw HTML content to extract from.
            url: Source URL (used for resolving relative links).
            prompt: Optional prompt (unused by deterministic provider).
            css_selectors: Optional dict of field -> CSS selector overrides.
                           Overrides the default PRODUCT_SELECTORS for a single
                           product extraction pass when provided.
        """
        # 0. If custom selectors are provided, run a targeted single-item pass first
        if css_selectors:
            custom_result = self._extract_with_custom_selectors(html, url, css_selectors)
            if custom_result:
                return [custom_result]

        # 1. Try JSON-LD extraction (most reliable)
        jsonld_products = self._extract_jsonld(html)
        if jsonld_products:
            return jsonld_products

        # 2. Try CSS selector extraction (multi-item capable)
        css_products = self._extract_css(html, url)
        if css_products:
            return css_products

        # 3. Fall back to basic HTML pattern matching (single item)
        basic = self._extract_basic(html, url)
        return [basic] if basic else []

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

    def _extract_with_custom_selectors(self, html: str, url: str, css_selectors: dict) -> dict:
        """Extract a single product using caller-supplied CSS selectors.

        Args:
            html: Raw HTML content.
            url: Source URL.
            css_selectors: Mapping of field name -> CSS selector string.

        Returns:
            Extracted product dict, or empty dict if nothing matched.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return {}

        soup = BeautifulSoup(html, "html.parser")
        result: dict = {"product_url": url}

        for field, selector in css_selectors.items():
            try:
                el = soup.select_one(selector)
                if el:
                    value = el.get("content") or el.get("value") or el.get_text(strip=True)
                    if value:
                        result[field] = value
            except Exception:
                continue

        # Only return if we extracted at least one meaningful field
        meaningful_fields = {k for k in result if k != "product_url"}
        return result if meaningful_fields else {}

    def _extract_css(self, html: str, url: str) -> list[dict]:
        """Extract multiple products using CSS selectors and BeautifulSoup."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []

        soup = BeautifulSoup(html, "html.parser")
        products = []

        # Common card container selectors (ordered by specificity)
        card_selectors = [
            "article.product_pod",       # books.toscrape.com
            "div.quote",                 # quotes.toscrape.com
            ".product-card",
            ".product-item",
            "[data-product]",
            ".product",
            ".quote",
            ".item",
            'li[itemtype*="Product"]',
            'div[itemtype*="Product"]',
        ]

        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if len(cards) >= 2:
                break

        if len(cards) < 2:
            return []

        for card in cards:
            product: dict[str, str] = {"product_url": url}

            # Extract name from heading, title, or text element
            name_el = card.select_one("h3 a, h2 a, h4 a, .product-name, .title a, a[title], span.text, .text")
            if name_el:
                product["name"] = name_el.get("title") or name_el.get_text(strip=True)
                href = name_el.get("href", "")
                if href and not href.startswith(("http://", "https://")):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                if href:
                    product["product_url"] = href

            # Extract author (for quote-type content)
            author_el = card.select_one("small.author, .author, [itemprop='author']")
            if author_el:
                product["author"] = author_el.get_text(strip=True)

            # Extract price
            price_el = card.select_one(".price_color, .price, .product-price, [itemprop='price']")
            if price_el:
                price_text = price_el.get_text(strip=True)
                price_match = PRICE_PATTERN.search(price_text)
                if price_match:
                    product["price"] = price_match.group(1).replace(",", "")

            # Extract image
            img_el = card.select_one("img")
            if img_el:
                src = img_el.get("src") or img_el.get("data-src", "")
                if src and not src.startswith(("http://", "https://")):
                    from urllib.parse import urljoin
                    src = urljoin(url, src)
                if src:
                    product["image_url"] = src

            # Extract rating (e.g., star-rating class)
            rating_el = card.select_one("[class*='star-rating'], .rating")
            if rating_el:
                classes = rating_el.get("class", [])
                rating_map = {"One": "1", "Two": "2", "Three": "3", "Four": "4", "Five": "5"}
                for cls in classes:
                    if cls in rating_map:
                        product["rating"] = rating_map[cls]
                        break

            # Only include items that have a name — price-only items are noise
            # (e.g. stray price tags outside of actual product cards)
            if product.get("name"):
                products.append(product)

        return products

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
                            # B6: stock/availability from single offer
                            availability = offers.get("availability", "")
                            if availability:
                                product["stock_status"] = availability.split("/")[-1] if "/" in availability else availability
                        elif isinstance(offers, list) and offers:
                            product["price"] = offers[0].get("price", "")
                            product["currency"] = offers[0].get("priceCurrency", "")
                            # B6: stock/availability from first offer in list
                            availability = offers[0].get("availability", "")
                            if availability:
                                product["stock_status"] = availability.split("/")[-1] if "/" in availability else availability

                        # B6: Extract variant data from hasVariant or offers array
                        variants = []
                        has_variant = item.get("hasVariant", [])
                        if isinstance(has_variant, list):
                            for v in has_variant:
                                if not isinstance(v, dict):
                                    continue
                                variant: dict = {}
                                if v.get("name"):
                                    variant["name"] = v["name"]
                                if v.get("color"):
                                    variant["color"] = v["color"]
                                if v.get("size"):
                                    variant["size"] = v["size"]
                                v_offers = v.get("offers", {})
                                if isinstance(v_offers, dict) and v_offers.get("price"):
                                    variant["price"] = v_offers["price"]
                                    v_avail = v_offers.get("availability", "")
                                    if v_avail:
                                        variant["stock_status"] = v_avail.split("/")[-1] if "/" in v_avail else v_avail
                                if variant:
                                    variants.append(variant)

                        # Also extract size/color variants from offers list when multiple offers exist
                        if not variants and isinstance(offers, list) and len(offers) > 1:
                            for o in offers:
                                if not isinstance(o, dict):
                                    continue
                                variant = {}
                                if o.get("name"):
                                    variant["name"] = o["name"]
                                if o.get("color"):
                                    variant["color"] = o["color"]
                                if o.get("size"):
                                    variant["size"] = o["size"]
                                if o.get("price"):
                                    variant["price"] = o["price"]
                                o_avail = o.get("availability", "")
                                if o_avail:
                                    variant["stock_status"] = o_avail.split("/")[-1] if "/" in o_avail else o_avail
                                if variant:
                                    variants.append(variant)

                        if variants:
                            product["variants"] = variants

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
