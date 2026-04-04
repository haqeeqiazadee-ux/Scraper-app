"""Tests for content filter."""

import pytest
from unittest.mock import patch, MagicMock

from packages.core.content_filter import ContentFilter


@pytest.fixture
def content_filter():
    return ContentFilter()


@pytest.fixture
def sample_products():
    """Realistic product items for testing."""
    return [
        {
            "name": "Apple MacBook Pro 16-inch M3",
            "price": "2499.00",
            "description": "Professional laptop with M3 chip, 36GB RAM, 512GB SSD.",
            "category": "Laptops",
            "brand": "Apple",
            "url": "https://store.example.com/macbook-pro-16",
            "rating": "4.8",
        },
        {
            "name": "Samsung Galaxy S24 Ultra",
            "price": "1199.99",
            "description": "Flagship smartphone with S Pen, 200MP camera, titanium frame.",
            "category": "Smartphones",
            "brand": "Samsung",
            "url": "https://store.example.com/galaxy-s24-ultra",
            "rating": "4.6",
        },
        {
            "name": "Sony WH-1000XM5 Headphones",
            "price": "349.99",
            "description": "Industry-leading noise cancelling wireless headphones.",
            "category": "Audio",
            "brand": "Sony",
            "url": "https://store.example.com/sony-wh1000xm5",
            "rating": "4.7",
        },
        {
            "name": "Dell XPS 15 Laptop",
            "price": "1799.00",
            "description": "Premium ultrabook with OLED display, Intel i9, 32GB RAM.",
            "category": "Laptops",
            "brand": "Dell",
            "url": "https://store.example.com/dell-xps-15",
            "rating": "4.5",
        },
        {
            "name": "Logitech MX Master 3S Mouse",
            "price": "99.99",
            "description": "Ergonomic wireless mouse for productivity and creative work.",
            "category": "Accessories",
            "brand": "Logitech",
            "url": "https://store.example.com/mx-master-3s",
            "rating": "4.9",
        },
    ]


@pytest.fixture
def products_with_string_prices():
    """Products with various price string formats."""
    return [
        {"name": "Widget A", "price": "$29.99", "category": "Widgets"},
        {"name": "Widget B", "price": "$149.50", "category": "Widgets"},
        {"name": "Widget C", "price": "€89,99", "category": "Widgets"},
        {"name": "Widget D", "price": "Free", "category": "Widgets"},
        {"name": "Widget E", "price": "$1,299.00", "category": "Widgets"},
    ]


class TestFilterByRelevance:

    @patch("packages.core.content_filter.BM25Okapi")
    def test_filter_by_relevance_basic(self, mock_bm25_cls, content_filter, sample_products):
        """BM25 sorts items by relevance to query."""
        mock_bm25 = MagicMock()
        mock_bm25_cls.return_value = mock_bm25
        # Return scores that rank laptops higher for "laptop" query
        mock_bm25.get_scores.return_value = [0.8, 0.1, 0.0, 0.9, 0.0]

        result = content_filter.filter_by_relevance(
            sample_products, query="laptop"
        )

        assert len(result) > 0
        # Higher-scoring items should come first
        scores = [item.get("_relevance_score", 0) for item in result]
        assert scores == sorted(scores, reverse=True)

    @patch("packages.core.content_filter.BM25Okapi")
    def test_filter_by_relevance_threshold(self, mock_bm25_cls, content_filter, sample_products):
        """Items below the relevance threshold are removed."""
        mock_bm25 = MagicMock()
        mock_bm25_cls.return_value = mock_bm25
        mock_bm25.get_scores.return_value = [0.9, 0.1, 0.05, 0.8, 0.02]

        result = content_filter.filter_by_relevance(
            sample_products, query="laptop", threshold=0.3
        )

        # Only items with score >= 0.3 should remain
        for item in result:
            assert item["_relevance_score"] >= 0.3

    @patch("packages.core.content_filter.BM25Okapi")
    def test_filter_by_relevance_empty_query(self, mock_bm25_cls, content_filter, sample_products):
        """Empty query returns all items unchanged."""
        result = content_filter.filter_by_relevance(
            sample_products, query=""
        )

        assert len(result) == len(sample_products)

    @patch("packages.core.content_filter.BM25Okapi")
    def test_filter_by_relevance_empty_items(self, mock_bm25_cls, content_filter):
        """Empty items list returns empty list."""
        result = content_filter.filter_by_relevance([], query="laptop")

        assert result == []

    @patch("packages.core.content_filter.BM25Okapi")
    def test_filter_by_relevance_adds_score(self, mock_bm25_cls, content_filter, sample_products):
        """Each returned item has a _relevance_score field."""
        mock_bm25 = MagicMock()
        mock_bm25_cls.return_value = mock_bm25
        mock_bm25.get_scores.return_value = [0.5, 0.4, 0.3, 0.2, 0.1]

        result = content_filter.filter_by_relevance(
            sample_products, query="electronics"
        )

        for item in result:
            assert "_relevance_score" in item
            assert isinstance(item["_relevance_score"], float)


class TestFilterByKeywords:

    def test_filter_by_keywords_match(self, content_filter, sample_products):
        """Items containing the keyword are kept."""
        result = content_filter.filter_by_keywords(
            sample_products, keywords=["laptop"]
        )

        assert len(result) >= 1
        for item in result:
            text = " ".join(str(v) for v in item.values()).lower()
            assert "laptop" in text

    def test_filter_by_keywords_no_match(self, content_filter, sample_products):
        """Items without any matching keyword are removed."""
        result = content_filter.filter_by_keywords(
            sample_products, keywords=["nonexistent_xyz_keyword"]
        )

        assert len(result) == 0

    def test_filter_by_keywords_specific_fields(self, content_filter, sample_products):
        """Only specified fields are searched for keywords."""
        # "laptop" appears in name and description but not in category for some items
        result = content_filter.filter_by_keywords(
            sample_products, keywords=["Laptops"], fields=["category"]
        )

        assert len(result) == 2  # MacBook Pro and Dell XPS
        for item in result:
            assert item["category"] == "Laptops"

    def test_filter_by_keywords_case_insensitive(self, content_filter, sample_products):
        """Keyword matching is case-insensitive."""
        result_lower = content_filter.filter_by_keywords(
            sample_products, keywords=["apple"]
        )
        result_upper = content_filter.filter_by_keywords(
            sample_products, keywords=["APPLE"]
        )
        result_mixed = content_filter.filter_by_keywords(
            sample_products, keywords=["Apple"]
        )

        assert len(result_lower) == len(result_upper) == len(result_mixed)
        assert len(result_lower) >= 1

    def test_filter_by_keywords_multiple_keywords(self, content_filter, sample_products):
        """Multiple keywords use OR logic — item matches if any keyword found."""
        result = content_filter.filter_by_keywords(
            sample_products, keywords=["headphones", "mouse"]
        )

        assert len(result) == 2
        names = [item["name"] for item in result]
        assert any("Headphones" in n for n in names)
        assert any("Mouse" in n for n in names)


class TestFilterByPriceRange:

    def test_filter_by_price_range_min(self, content_filter, sample_products):
        """min_price filter removes items below the minimum."""
        result = content_filter.filter_by_price_range(
            sample_products, min_price=1000
        )

        for item in result:
            assert float(item["price"]) >= 1000

    def test_filter_by_price_range_max(self, content_filter, sample_products):
        """max_price filter removes items above the maximum."""
        result = content_filter.filter_by_price_range(
            sample_products, max_price=500
        )

        for item in result:
            assert float(item["price"]) <= 500

    def test_filter_by_price_range_both(self, content_filter, sample_products):
        """min and max price filters applied together."""
        result = content_filter.filter_by_price_range(
            sample_products, min_price=300, max_price=1500
        )

        for item in result:
            price = float(item["price"])
            assert 300 <= price <= 1500

    def test_filter_by_price_handles_string_prices(self, content_filter, products_with_string_prices):
        """Price strings like '$29.99' are parsed correctly for filtering."""
        result = content_filter.filter_by_price_range(
            products_with_string_prices, min_price=50, max_price=200
        )

        # "$29.99" is below min, "$149.50" and "€89,99" (89.99) should match,
        # "Free" should be excluded, "$1,299.00" is above max
        assert len(result) >= 1
        names = [item["name"] for item in result]
        assert "Widget B" in names  # $149.50 is in range

    def test_filter_by_price_range_no_limits(self, content_filter, sample_products):
        """No price limits returns all items."""
        result = content_filter.filter_by_price_range(sample_products)

        assert len(result) == len(sample_products)


class TestFilterByFields:

    def test_filter_by_fields_required(self, content_filter):
        """Items missing required fields are filtered out."""
        items = [
            {"name": "Complete Item", "price": "29.99", "url": "https://example.com/1"},
            {"name": "Missing URL", "price": "19.99"},
            {"name": "Missing Price", "url": "https://example.com/3"},
        ]

        result = content_filter.filter_by_fields(
            items, required_fields=["name", "price", "url"]
        )

        assert len(result) == 1
        assert result[0]["name"] == "Complete Item"

    def test_filter_by_fields_empty_values(self, content_filter):
        """Empty string values for required fields cause item to be filtered."""
        items = [
            {"name": "Good Item", "price": "29.99", "sku": "ABC-123"},
            {"name": "", "price": "19.99", "sku": "DEF-456"},
            {"name": "No Price", "price": "", "sku": "GHI-789"},
        ]

        result = content_filter.filter_by_fields(
            items, required_fields=["name", "price"]
        )

        assert len(result) == 1
        assert result[0]["name"] == "Good Item"

    def test_filter_by_fields_no_requirements(self, content_filter, sample_products):
        """No required fields means all items pass."""
        result = content_filter.filter_by_fields(
            sample_products, required_fields=[]
        )

        assert len(result) == len(sample_products)


class TestApplyFilters:

    @patch("packages.core.content_filter.BM25Okapi")
    def test_apply_filters_combined(self, mock_bm25_cls, content_filter, sample_products):
        """Multiple filters applied in sequence narrow the result set."""
        mock_bm25 = MagicMock()
        mock_bm25_cls.return_value = mock_bm25
        # All items get a high relevance score so relevance doesn't filter any out
        mock_bm25.get_scores.return_value = [0.9, 0.8, 0.7, 0.85, 0.6]

        filters = {
            "query": "electronics",
            "keywords": ["laptop"],
            "min_price": 1000,
            "max_price": 3000,
            "required_fields": ["name", "price", "url"],
        }

        result = content_filter.apply_filters(sample_products, **filters)

        # Should only return laptops in the price range with all required fields
        assert len(result) >= 1
        for item in result:
            text = " ".join(str(v) for v in item.values()).lower()
            assert "laptop" in text
            assert float(item["price"]) >= 1000
            assert float(item["price"]) <= 3000
            assert item.get("name")
            assert item.get("price")
            assert item.get("url")

    def test_apply_filters_no_filters(self, content_filter, sample_products):
        """No filters specified returns all items unchanged."""
        result = content_filter.apply_filters(sample_products)

        assert len(result) == len(sample_products)

    def test_apply_filters_empty_items(self, content_filter):
        """Empty items list with filters returns empty list."""
        result = content_filter.apply_filters(
            [],
            query="laptop",
            keywords=["test"],
            min_price=10,
        )

        assert result == []

    @patch("packages.core.content_filter.BM25Okapi")
    def test_apply_filters_preserves_item_data(self, mock_bm25_cls, content_filter, sample_products):
        """Filtering does not mutate or lose original item fields."""
        mock_bm25 = MagicMock()
        mock_bm25_cls.return_value = mock_bm25
        mock_bm25.get_scores.return_value = [0.9, 0.8, 0.7, 0.85, 0.6]

        result = content_filter.apply_filters(
            sample_products, query="electronics"
        )

        for item in result:
            assert "name" in item
            assert "price" in item
            assert "description" in item
            assert "brand" in item
