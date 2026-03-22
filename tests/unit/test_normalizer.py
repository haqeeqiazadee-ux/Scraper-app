"""Tests for result normalizer."""

import pytest
from packages.core.normalizer import (
    normalize_item, normalize_items, clean_price, clean_rating,
    clean_integer, clean_url,
)


class TestNormalizeItem:

    def test_field_aliases(self):
        item = {"product_name": "Widget", "cost": "$29.99", "img": "https://x.com/a.jpg"}
        result = normalize_item(item)
        assert result["name"] == "Widget"
        assert result["price"] == "29.99"
        assert result["image_url"] == "https://x.com/a.jpg"

    def test_preserves_canonical_fields(self):
        item = {"name": "Widget", "price": "29.99", "sku": "W-001"}
        result = normalize_item(item)
        assert result["name"] == "Widget"
        assert result["price"] == "29.99"
        assert result["sku"] == "W-001"

    def test_lowercases_keys(self):
        item = {"Product_Name": "Widget", "PRICE": "$10"}
        result = normalize_item(item)
        assert "name" in result or "product_name" in result

    def test_handles_none_values(self):
        item = {"name": None, "price": None}
        result = normalize_item(item)
        assert result["name"] == ""
        assert result["price"] == ""

    def test_keeps_dict_and_list_values(self):
        item = {"specifications": {"weight": "1kg"}, "features": ["fast", "reliable"]}
        result = normalize_item(item)
        assert result["specifications"] == {"weight": "1kg"}
        assert result["features"] == ["fast", "reliable"]


class TestNormalizeItems:

    def test_normalizes_multiple(self):
        items = [
            {"product_name": "A", "cost": "$10"},
            {"product_name": "B", "cost": "$20"},
        ]
        results = normalize_items(items)
        assert len(results) == 2
        assert results[0]["name"] == "A"
        assert results[1]["name"] == "B"


class TestCleanPrice:

    def test_usd(self):
        assert clean_price("$29.99") == "29.99"

    def test_euro(self):
        assert clean_price("€29,99") == "29.99"

    def test_with_thousands(self):
        assert clean_price("$1,299.99") == "1299.99"

    def test_currency_code(self):
        assert clean_price("29.99 USD") == "29.99"

    def test_empty(self):
        assert clean_price("") == ""

    def test_pkr(self):
        assert clean_price("Rs. 5,000") == "5000"


class TestCleanRating:

    def test_simple(self):
        assert clean_rating("4.5") == "4.5"

    def test_out_of_five(self):
        assert clean_rating("4.5/5") == "4.5"

    def test_stars(self):
        assert clean_rating("4.5 stars") == "4.5"

    def test_empty(self):
        assert clean_rating("") == ""


class TestCleanInteger:

    def test_simple(self):
        assert clean_integer("128") == "128"

    def test_with_comma(self):
        assert clean_integer("1,234") == "1234"

    def test_with_text(self):
        assert clean_integer("128 reviews") == "128"

    def test_empty(self):
        assert clean_integer("") == ""


class TestCleanUrl:

    def test_valid_https(self):
        assert clean_url("https://example.com/img.jpg") == "https://example.com/img.jpg"

    def test_protocol_relative(self):
        assert clean_url("//example.com/img.jpg") == "https://example.com/img.jpg"

    def test_invalid(self):
        assert clean_url("not-a-url") == ""

    def test_empty(self):
        assert clean_url("") == ""

    def test_whitespace(self):
        assert clean_url("  https://x.com  ") == "https://x.com"
