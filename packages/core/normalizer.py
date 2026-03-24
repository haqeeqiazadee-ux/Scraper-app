"""
Result Normalizer — maps heterogeneous extraction results to canonical schema.

Handles field aliasing, type coercion, and data cleaning.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Field aliases: variant → canonical name
FIELD_ALIASES: dict[str, str] = {
    # Name variants
    "product_name": "name", "title": "name", "product_title": "name",
    "item_name": "name", "heading": "name",
    # Price variants
    "cost": "price", "amount": "price", "product_price": "price",
    "current_price": "price", "sale_price": "price",
    # Original price
    "regular_price": "original_price", "was_price": "original_price",
    "list_price": "original_price", "mrp": "original_price",
    # Image
    "img": "image_url", "image": "image_url", "photo": "image_url",
    "thumbnail": "image_url", "main_image": "image_url",
    # URL
    "link": "product_url", "href": "product_url", "url": "product_url",
    "product_link": "product_url",
    # Description
    "desc": "description", "product_description": "description",
    "summary": "description",
    # Rating
    "stars": "rating", "score": "rating", "review_score": "rating",
    # Reviews
    "review_count": "reviews_count", "num_reviews": "reviews_count",
    "total_reviews": "reviews_count",
    # Stock
    "availability": "stock_status", "in_stock": "stock_status",
    # Brand
    "manufacturer": "brand", "vendor": "brand",
    # Category
    "department": "category", "product_category": "category",
}

# Price cleaning regex
PRICE_CLEAN = re.compile(r'[^\d.,]')


def normalize_items(items: list[dict]) -> list[dict]:
    """Normalize a list of extracted items to canonical schema."""
    return [normalize_item(item) for item in items]


def normalize_item(item: dict) -> dict:
    """Normalize a single extracted item."""
    normalized = {}

    for key, value in item.items():
        # Map to canonical field name
        canonical_key = FIELD_ALIASES.get(key.lower().strip(), key.lower().strip())

        # Clean and coerce value
        cleaned = clean_value(canonical_key, value)

        # Keep the most complete value if duplicate
        if canonical_key in normalized:
            existing = normalized[canonical_key]
            if not existing and cleaned:
                normalized[canonical_key] = cleaned
        else:
            normalized[canonical_key] = cleaned

    return normalized


def clean_value(field_name: str, value: Any) -> Any:
    """Clean and coerce a value based on field type."""
    if value is None:
        return ""

    if isinstance(value, (list, dict)):
        return value

    value = str(value).strip()

    # Price fields: extract numeric value
    if field_name in ("price", "original_price", "discount"):
        return clean_price(value)

    # Rating: extract numeric
    if field_name == "rating":
        return clean_rating(value)

    # Review count: extract integer
    if field_name == "reviews_count":
        return clean_integer(value)

    # URLs: ensure valid
    if field_name in ("image_url", "product_url"):
        return clean_url(value)

    return value


def clean_price(value: str) -> str:
    """Extract numeric price from various formats."""
    if not value:
        return ""
    # Remove currency symbols and whitespace, keep digits and decimal
    cleaned = PRICE_CLEAN.sub("", value)
    # Remove leading/trailing dots
    cleaned = cleaned.strip(".")
    # Handle comma: if followed by exactly 3 digits it's a thousands separator
    if "," in cleaned and "." not in cleaned:
        # Check if comma is thousands separator (e.g., 5,000 or 1,234,567)
        if re.match(r'^\d{1,3}(,\d{3})+$', cleaned):
            cleaned = cleaned.replace(",", "")
        else:
            # Comma as decimal separator (e.g., 29,99)
            cleaned = cleaned.replace(",", ".")
    # Handle comma as thousands separator when both exist
    elif "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    return cleaned


def clean_rating(value: str) -> str:
    """Extract numeric rating."""
    if not value:
        return ""
    # Match patterns like "4.5/5", "4.5 stars", "4.5"
    match = re.search(r'(\d+\.?\d*)', value)
    return match.group(1) if match else ""


def clean_integer(value: str) -> str:
    """Extract integer from string."""
    if not value:
        return ""
    match = re.search(r'(\d+)', value.replace(",", ""))
    return match.group(1) if match else ""


def clean_url(value: str) -> str:
    """Clean and validate a URL."""
    if not value:
        return ""
    value = value.strip()
    if value.startswith("//"):
        value = "https:" + value
    if not value.startswith(("http://", "https://", "data:")):
        return ""
    return value


class Normalizer:
    """Stateless normalizer — convenience wrapper around module-level functions."""

    def normalize_batch(self, items: list[dict]) -> list[dict]:
        """Normalize a list of extracted items to canonical schema."""
        return normalize_items(items)

    def normalize_one(self, item: dict) -> dict:
        """Normalize a single extracted item."""
        return normalize_item(item)
