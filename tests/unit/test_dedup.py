"""Tests for deduplication engine."""

import pytest
from packages.core.dedup import DedupEngine


@pytest.fixture
def engine():
    return DedupEngine(similarity_threshold=0.85)


class TestDedupEngine:

    def test_no_duplicates(self, engine):
        items = [
            {"name": "Apple MacBook Pro 16", "price": "2499"},
            {"name": "Samsung Galaxy S24 Ultra", "price": "1199"},
        ]
        result = engine.deduplicate(items)
        assert len(result) == 2

    def test_exact_sku_duplicate(self, engine):
        items = [
            {"name": "Widget", "sku": "W-001", "price": "10"},
            {"name": "Widget v2", "sku": "W-001", "price": "12"},
        ]
        result = engine.deduplicate(items)
        assert len(result) == 1
        # Should keep the more complete/longer name
        assert result[0]["sku"] == "W-001"

    def test_exact_url_duplicate(self, engine):
        items = [
            {"name": "Product", "product_url": "https://shop.com/product/1"},
            {"name": "Product", "product_url": "https://shop.com/product/1"},
        ]
        result = engine.deduplicate(items)
        assert len(result) == 1

    def test_url_trailing_slash(self, engine):
        items = [
            {"name": "Product", "product_url": "https://shop.com/product/1/"},
            {"name": "Product", "product_url": "https://shop.com/product/1"},
        ]
        result = engine.deduplicate(items)
        assert len(result) == 1

    def test_fuzzy_name_match(self, engine):
        items = [
            {"name": "Apple MacBook Pro 16-inch", "price": "2499"},
            {"name": "Apple MacBook Pro 16 inch", "price": "2499"},
        ]
        result = engine.deduplicate(items)
        assert len(result) == 1

    def test_different_products_not_merged(self, engine):
        items = [
            {"name": "Apple MacBook Pro", "price": "2499"},
            {"name": "Dell XPS 15", "price": "1999"},
        ]
        result = engine.deduplicate(items)
        assert len(result) == 2

    def test_merge_keeps_most_complete(self, engine):
        items = [
            {"name": "Widget", "sku": "W-001", "price": "10", "brand": ""},
            {"name": "Widget", "sku": "W-001", "price": "10", "brand": "WidgetCo", "description": "Great widget"},
        ]
        result = engine.deduplicate(items)
        assert len(result) == 1
        assert result[0]["brand"] == "WidgetCo"
        assert result[0]["description"] == "Great widget"

    def test_empty_list(self, engine):
        assert engine.deduplicate([]) == []

    def test_single_item(self, engine):
        items = [{"name": "Product"}]
        assert engine.deduplicate(items) == items

    def test_three_duplicates(self, engine):
        items = [
            {"name": "Widget", "sku": "W-001"},
            {"name": "Widget", "sku": "W-001", "price": "10"},
            {"name": "Widget", "sku": "W-001", "price": "10", "brand": "WidgetCo"},
        ]
        result = engine.deduplicate(items)
        assert len(result) == 1
        assert result[0]["brand"] == "WidgetCo"
        assert result[0]["price"] == "10"

    def test_custom_threshold(self):
        # Lower threshold = more aggressive dedup
        engine = DedupEngine(similarity_threshold=0.5)
        items = [
            {"name": "Laptop Pro Max"},
            {"name": "Laptop Pro"},
        ]
        result = engine.deduplicate(items)
        assert len(result) == 1

    def test_high_threshold_preserves(self):
        # Higher threshold = less aggressive
        engine = DedupEngine(similarity_threshold=0.99)
        items = [
            {"name": "Laptop Pro Max"},
            {"name": "Laptop Pro"},
        ]
        result = engine.deduplicate(items)
        assert len(result) == 2
