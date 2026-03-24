"""
Tests for AI-enhanced normalization features.

Covers:
  UC-10.1.3 — Mixed currency formats normalized to consistent format
  UC-10.2.1 — Truncated product title repaired
  UC-10.2.2 — Missing currency inferred from domain/locale
  UC-10.2.3 — HTML artifacts in text fields cleaned
  UC-10.4.3 — AI token usage tracked per request
  UC-10.5.3 — AI-only extraction confidence recorded
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from packages.core.normalizer import (
    Normalizer,
    detect_currency,
    strip_html_artifacts,
    repair_truncated_title,
    clean_price,
)


# ---------------------------------------------------------------------------
# UC-10.1.3 — Mixed currency format normalization
# ---------------------------------------------------------------------------

class TestCurrencyDetection:
    """Detect currency from price strings and URLs."""

    def test_dollar_sign(self):
        assert detect_currency("$19.99") == "USD"

    def test_euro_sign(self):
        assert detect_currency("\u20ac29.99") == "EUR"

    def test_pound_sign(self):
        assert detect_currency("\u00a314.99") == "GBP"

    def test_yen_sign(self):
        assert detect_currency("\u00a52000") == "JPY"

    def test_rupee_sign(self):
        assert detect_currency("\u20b9999") == "INR"

    def test_rs_prefix(self):
        assert detect_currency("Rs. 1499") == "INR"

    def test_real_sign(self):
        assert detect_currency("R$49.90") == "BRL"

    def test_explicit_code(self):
        assert detect_currency("19.99 EUR") == "EUR"

    def test_infer_from_uk_domain(self):
        assert detect_currency("19.99", "https://www.shop.co.uk/item") == "GBP"

    def test_infer_from_de_domain(self):
        assert detect_currency("29,99", "https://www.amazon.de/product") == "EUR"

    def test_infer_from_jp_domain(self):
        assert detect_currency("2000", "https://www.shop.co.jp/item") == "JPY"

    def test_infer_from_in_domain(self):
        assert detect_currency("999", "https://www.flipkart.co.in/item") == "INR"

    def test_infer_from_com_domain_default_usd(self):
        assert detect_currency("19.99", "https://www.amazon.com/item") == "USD"

    def test_no_currency_no_url(self):
        assert detect_currency("19.99") == ""

    def test_empty_string(self):
        assert detect_currency("") == ""


class TestMixedCurrencyNormalization:
    """Full pipeline: price + currency together."""

    def test_usd_price(self):
        n = Normalizer()
        result = n.normalize_one({"price": "$19.99"})
        assert result["price"] == "19.99"
        assert result["currency"] == "USD"

    def test_eur_comma_price(self):
        n = Normalizer()
        result = n.normalize_one({"price": "19,99 EUR"})
        assert result["price"] == "19.99"
        assert result["currency"] == "EUR"

    def test_inr_price(self):
        n = Normalizer()
        result = n.normalize_one({"price": "\u20b91,499"})
        assert result["price"] == "1499"
        assert result["currency"] == "INR"

    def test_currency_from_url(self):
        n = Normalizer()
        result = n.normalize_one({"price": "29.99"}, url="https://shop.co.uk/item")
        assert result["price"] == "29.99"
        assert result["currency"] == "GBP"


# ---------------------------------------------------------------------------
# UC-10.2.1 — Truncated title repair
# ---------------------------------------------------------------------------

class TestTitleRepair:
    """Repair truncated product titles."""

    def test_trailing_ellipsis(self):
        assert repair_truncated_title("Premium Wireless Headphones with Noise Cance...") == \
               "Premium Wireless Headphones with Noise Cance"

    def test_unicode_ellipsis(self):
        assert repair_truncated_title("Premium Wireless Headphones\u2026") == \
               "Premium Wireless Headphones"

    def test_no_ellipsis_unchanged(self):
        assert repair_truncated_title("Normal Title") == "Normal Title"

    def test_empty_string(self):
        assert repair_truncated_title("") == ""

    def test_html_in_title_cleaned(self):
        assert repair_truncated_title("<b>Product</b> Name") == "Product Name"

    def test_entity_decoded(self):
        assert repair_truncated_title("Ben &amp; Jerry&#8217;s") == "Ben & Jerry\u2019s"


# ---------------------------------------------------------------------------
# UC-10.2.3 — HTML artifacts cleaned from text fields
# ---------------------------------------------------------------------------

class TestHTMLCleanup:
    """Remove HTML tags and decode entities."""

    def test_strip_tags(self):
        assert strip_html_artifacts("<b>Bold</b> text") == "Bold text"

    def test_strip_nested_tags(self):
        result = strip_html_artifacts("<div><span class='x'>Hello</span> <em>World</em></div>")
        assert result == "Hello World"

    def test_decode_amp(self):
        assert strip_html_artifacts("Tom &amp; Jerry") == "Tom & Jerry"

    def test_decode_numeric(self):
        assert strip_html_artifacts("Price: &#36;19.99") == "Price: $19.99"

    def test_decode_hex(self):
        assert strip_html_artifacts("&#x20AC;29.99") == "\u20ac29.99"

    def test_collapse_whitespace(self):
        assert strip_html_artifacts("  hello   world  ") == "hello world"

    def test_empty_returns_empty(self):
        assert strip_html_artifacts("") == ""

    def test_none_returns_empty(self):
        assert strip_html_artifacts(None) == ""

    def test_plain_text_unchanged(self):
        assert strip_html_artifacts("Normal text") == "Normal text"


class TestNormalizerHTMLCleanup:
    """Normalizer applies HTML cleanup to text fields."""

    def test_name_cleaned(self):
        n = Normalizer()
        result = n.normalize_one({"name": "<b>Product</b> &amp; More"})
        assert result["name"] == "Product & More"

    def test_description_cleaned(self):
        n = Normalizer()
        result = n.normalize_one({"description": "<p>Great <em>item</em>.</p>"})
        assert result["description"] == "Great item."

    def test_brand_cleaned(self):
        n = Normalizer()
        result = n.normalize_one({"brand": "<span>Nike&trade;</span>"})
        assert "Nike" in result["brand"]
        assert "<span>" not in result["brand"]


# ---------------------------------------------------------------------------
# UC-10.4.3 — AI token usage tracked
# ---------------------------------------------------------------------------

class TestTokenTracking:
    """Token usage is tracked per normalizer instance."""

    def test_no_ai_zero_tokens(self):
        n = Normalizer()
        assert n.token_usage == 0

    def test_ai_provider_token_tracking(self):
        mock_ai = MagicMock()
        mock_ai.get_token_usage.return_value = 150
        n = Normalizer(ai_provider=mock_ai)
        assert n.token_usage == 150

    def test_token_usage_accumulates(self):
        mock_ai = MagicMock()
        mock_ai.get_token_usage.side_effect = [50, 100, 200]
        n = Normalizer(ai_provider=mock_ai)
        assert n.token_usage == 50
        assert n.token_usage == 100
        assert n.token_usage == 200


# ---------------------------------------------------------------------------
# UC-10.5.3 — AI-only extraction confidence recorded
# ---------------------------------------------------------------------------

class TestAINormalization:
    """AI-enhanced normalization with confidence scoring."""

    @pytest.mark.asyncio
    async def test_deterministic_confidence(self):
        """Without AI, confidence is base level (0.7)."""
        n = Normalizer()
        result = await n.normalize_with_ai(
            {"name": "Test Product", "price": "$10"},
        )
        assert result["_confidence"] == 0.7
        assert result["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_ai_enhanced_confidence(self):
        """With AI filling missing fields, confidence increases to 0.9."""
        mock_ai = AsyncMock()
        mock_ai.get_token_usage = MagicMock(return_value=100)
        mock_ai.normalize = AsyncMock(return_value={"currency": "USD"})

        n = Normalizer(ai_provider=mock_ai)
        result = await n.normalize_with_ai(
            {"name": "Test", "price": "10"},
        )
        assert result["_confidence"] == 0.9
        assert result["currency"] == "USD"
        mock_ai.normalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_ai_failure_graceful(self):
        """If AI fails, falls back to deterministic with base confidence."""
        mock_ai = AsyncMock()
        mock_ai.get_token_usage = MagicMock(return_value=0)
        mock_ai.normalize = AsyncMock(side_effect=Exception("API down"))

        n = Normalizer(ai_provider=mock_ai)
        result = await n.normalize_with_ai(
            {"name": "Test", "price": "10"},
        )
        assert result["_confidence"] == 0.7  # falls back

    @pytest.mark.asyncio
    async def test_all_fields_present_no_ai_call(self):
        """When no fields are missing, AI is not called."""
        mock_ai = AsyncMock()
        mock_ai.get_token_usage = MagicMock(return_value=0)

        n = Normalizer(ai_provider=mock_ai)
        result = await n.normalize_with_ai(
            {"name": "Test", "price": "$10", "currency": "USD"},
        )
        assert result["_confidence"] == 0.7
        mock_ai.normalize.assert_not_called()


# ---------------------------------------------------------------------------
# Batch normalization with URL context
# ---------------------------------------------------------------------------

class TestBatchNormalization:
    """Batch normalization passes URL context."""

    def test_batch_with_url(self):
        n = Normalizer()
        items = [
            {"name": "Item 1", "price": "19.99"},
            {"name": "Item 2", "price": "29.99"},
        ]
        results = n.normalize_batch(items, url="https://shop.co.uk/products")
        for r in results:
            assert r["currency"] == "GBP"

    def test_batch_mixed_currencies(self):
        n = Normalizer()
        items = [
            {"name": "Item 1", "price": "$19.99"},
            {"name": "Item 2", "price": "\u20ac29.99"},
        ]
        results = n.normalize_batch(items)
        assert results[0]["currency"] == "USD"
        assert results[1]["currency"] == "EUR"
