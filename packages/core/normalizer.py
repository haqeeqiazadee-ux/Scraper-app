"""
Result Normalizer — maps heterogeneous extraction results to canonical schema.

Handles field aliasing, type coercion, data cleaning, and AI-enhanced
normalization (currency, title repair, HTML artifact removal).
"""

from __future__ import annotations

import html as html_lib
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Currency mapping — symbol / locale → ISO code
# ---------------------------------------------------------------------------

CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD", "US$": "USD",
    "\u20ac": "EUR", "EUR": "EUR",
    "\u00a3": "GBP", "GBP": "GBP",
    "\u00a5": "JPY", "JP\u00a5": "JPY",
    "CN\u00a5": "CNY", "RMB": "CNY",
    "\u20b9": "INR", "Rs": "INR", "Rs.": "INR",
    "CA$": "CAD", "C$": "CAD",
    "A$": "AUD", "AU$": "AUD",
    "R$": "BRL",
    "\u20a9": "KRW",
    "\u20bd": "RUB",
    "CHF": "CHF",
    "kr": "SEK",  # also NOK/DKK, but SEK as default
    "z\u0142": "PLN",
    "\u20ba": "TRY",
    "R": "ZAR",
    "MX$": "MXN",
    "S$": "SGD",
    "HK$": "HKD",
    "NT$": "TWD",
    "\u0e3f": "THB",
    "\u20ab": "VND",
    "RM": "MYR",
    "\u20b1": "PHP",
    "AED": "AED",
    "SAR": "SAR",
}

DOMAIN_CURRENCY: dict[str, str] = {
    ".co.uk": "GBP", ".uk": "GBP",
    ".de": "EUR", ".fr": "EUR", ".it": "EUR", ".es": "EUR", ".nl": "EUR",
    ".co.jp": "JPY", ".jp": "JPY",
    ".cn": "CNY",
    ".in": "INR", ".co.in": "INR",
    ".ca": "CAD",
    ".com.au": "AUD", ".au": "AUD",
    ".com.br": "BRL", ".br": "BRL",
    ".kr": "KRW",
    ".ru": "RUB",
    ".ch": "CHF",
    ".se": "SEK",
    ".pl": "PLN",
    ".com.tr": "TRY",
    ".za": "ZAR",
    ".mx": "MXN", ".com.mx": "MXN",
    ".sg": "SGD",
    ".hk": "HKD",
    ".tw": "TWD",
    ".th": "THB",
    ".vn": "VND",
    ".my": "MYR",
    ".ph": "PHP",
    ".ae": "AED",
    ".sa": "SAR",
    ".com": "USD",  # default for .com
}

# HTML tag removal
HTML_TAG_RE = re.compile(r'<[^>]+>')
HTML_ENTITY_RE = re.compile(r'&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;')

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
    """Extract numeric price from various formats.

    Handles: $19.99, £1,234.56, 29,99 €, 1.234,56 EUR, ¥19800, ₹1,23,456
    """
    if not value:
        return ""
    from html import unescape
    value = unescape(value)
    # Remove currency symbols and whitespace, keep digits and decimal
    cleaned = PRICE_CLEAN.sub("", value)
    cleaned = cleaned.strip(".")

    last_comma = cleaned.rfind(",")
    last_dot = cleaned.rfind(".")

    if last_comma > last_dot:
        # Comma appears last — likely decimal separator (European: 1.234,56)
        # or thousands separator (US: 1,234,567)
        after_comma = cleaned[last_comma + 1:]
        if len(after_comma) <= 2:
            # Comma is decimal: 29,99 or 1.234,56
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # Comma is thousands: 1,234,567
            cleaned = cleaned.replace(",", "")
    elif last_dot > last_comma:
        # Dot appears last — standard decimal (US: 1,234.56)
        cleaned = cleaned.replace(",", "")
    else:
        # Only one separator or none
        if "," in cleaned:
            after_comma = cleaned[last_comma + 1:]
            if len(after_comma) <= 2:
                cleaned = cleaned.replace(",", ".")
            else:
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


def detect_currency(price_str: str, url: str = "") -> str:
    """Detect currency from price string or URL domain.

    UC-10.1.3 — Mixed currency formats normalized to consistent format.
    UC-10.2.2 — Missing currency inferred from domain/locale.
    """
    if not price_str:
        return ""

    # 1. Check for explicit currency symbols in the price string
    # Sort by length descending so "R$" matches before "$"
    for symbol, code in sorted(CURRENCY_SYMBOLS.items(), key=lambda x: -len(x[0])):
        if symbol in price_str:
            return code

    # 2. Check for 3-letter currency codes in the price string
    code_match = re.search(r'\b([A-Z]{3})\b', price_str)
    if code_match and code_match.group(1) in CURRENCY_SYMBOLS.values():
        return code_match.group(1)

    # 3. Infer from URL domain
    if url:
        url_lower = url.lower()
        for domain_suffix, code in sorted(DOMAIN_CURRENCY.items(), key=lambda x: -len(x[0])):
            if domain_suffix in url_lower:
                return code

    return ""


def strip_html_artifacts(text: str) -> str:
    """Remove HTML tags and decode entities from text fields.

    UC-10.2.3 — HTML artifacts in text fields cleaned.
    """
    if not text or not isinstance(text, str):
        return text or ""

    # Remove HTML tags
    cleaned = HTML_TAG_RE.sub("", text)
    # Decode HTML entities (&amp; → &, &#8221; → ", etc.)
    cleaned = html_lib.unescape(cleaned)
    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def repair_truncated_title(title: str) -> str:
    """Repair obviously truncated titles.

    UC-10.2.1 — Truncated product title repaired.
    Detects trailing '...' or incomplete words and cleans up.
    """
    if not title:
        return title

    title = strip_html_artifacts(title)

    # Remove trailing ellipsis and incomplete words after it
    if title.endswith("...") or title.endswith("\u2026"):
        title = title.rstrip(".\u2026").rstrip()
        # Remove partial word (non-space chars at end that don't end a word)
        title = re.sub(r'\s+\S{1,3}$', '', title)
        if title and not title.endswith((".", "!", "?", ")", '"', "'")):
            title = title.rstrip(",;:-")

    return title.strip()


class Normalizer:
    """Normalizer with optional AI-enhanced features.

    Deterministic normalization always runs. When an AI provider is
    attached, AI-powered repair (title, currency, HTML cleanup) is
    available via ``normalize_with_ai``.
    """

    def __init__(self, ai_provider: Optional[Any] = None) -> None:
        self._ai = ai_provider
        self._token_usage = 0

    @property
    def token_usage(self) -> int:
        """Total AI tokens consumed by this normalizer."""
        if self._ai and hasattr(self._ai, "get_token_usage"):
            return self._ai.get_token_usage()
        return self._token_usage

    def normalize_batch(self, items: list[dict], url: str = "") -> list[dict]:
        """Normalize a list of extracted items to canonical schema."""
        return [self.normalize_one(item, url=url) for item in items]

    def normalize_one(self, item: dict, url: str = "") -> dict:
        """Normalize a single extracted item with full cleaning pipeline."""
        result = normalize_item(item)

        # Currency detection / normalization
        if "currency" not in result or not result.get("currency"):
            price_raw = item.get("price") or item.get("cost") or item.get("amount") or ""
            detected = detect_currency(str(price_raw), url)
            if detected:
                result["currency"] = detected

        # HTML artifact removal from text fields
        for field in ("name", "description", "brand", "category"):
            if field in result and isinstance(result[field], str):
                result[field] = strip_html_artifacts(result[field])

        # Title repair
        if "name" in result:
            result["name"] = repair_truncated_title(result["name"])

        return result

    async def normalize_with_ai(self, item: dict, url: str = "") -> dict:
        """Normalize with deterministic pipeline + AI repair.

        UC-10.5.3 — AI-only extraction confidence recorded.
        """
        # First, deterministic normalization
        result = self.normalize_one(item, url=url)
        confidence = 0.7  # base confidence for deterministic

        # If AI is available, use it for fields that are still poor
        if self._ai:
            missing_fields = [f for f in ("name", "price", "currency")
                              if not result.get(f)]
            if missing_fields:
                try:
                    ai_result = await self._ai.normalize(
                        item,
                        {"fields": ["name", "price", "currency", "description"]},
                    )
                    for field in missing_fields:
                        if ai_result.get(field):
                            result[field] = ai_result[field]
                    confidence = 0.9  # AI-enhanced confidence
                except Exception as e:
                    logger.warning(f"AI normalization failed: {e}")

        result["_confidence"] = confidence
        return result
