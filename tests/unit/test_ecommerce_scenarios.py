"""
Tests for e-commerce extraction scenarios.

Covers:
  UC-17.3.1 — Wholesale listing extraction
  UC-17.3.3 — Wholesale-specific fields (MOQ, bulk pricing)
  UC-17.4.2 — HTML fallback when Shopify API blocked
  UC-17.5.3 — Reviews/ratings extraction from product pages
"""

from __future__ import annotations

import pytest

from packages.core.ai_providers.deterministic import DeterministicProvider
from packages.core.normalizer import Normalizer


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def provider():
    return DeterministicProvider()


@pytest.fixture
def normalizer():
    return Normalizer()


# ---------------------------------------------------------------------------
# UC-17.5.3 — Reviews/ratings extraction
# ---------------------------------------------------------------------------

class TestReviewsRatingsExtraction:
    """Extract reviews and ratings from product pages."""

    @pytest.mark.asyncio
    async def test_jsonld_rating(self, provider):
        """JSON-LD aggregateRating is extracted."""
        html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Wireless Headphones",
            "offers": {"@type": "Offer", "price": "79.99", "priceCurrency": "USD"},
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": "4.5",
                "reviewCount": "1234"
            }
        }
        </script>
        </head><body></body></html>
        """
        items = await provider.extract(html, "https://shop.example.com/headphones")
        assert len(items) >= 1
        item = items[0]
        assert item.get("rating") == "4.5"
        assert item.get("reviews_count") == "1234"

    @pytest.mark.asyncio
    async def test_css_star_rating(self, provider):
        """Star rating from CSS class is extracted via JSON-LD."""
        html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@type": "Product",
            "name": "Product A",
            "offers": {"price": "29.99", "priceCurrency": "USD"},
            "aggregateRating": {"ratingValue": "4", "reviewCount": "100"}
        }
        </script>
        </head><body></body></html>
        """
        items = await provider.extract(html, "https://shop.example.com/products")
        assert len(items) >= 1
        item = items[0]
        assert item.get("rating") == "4"

    @pytest.mark.asyncio
    async def test_multiple_products_with_ratings(self, provider):
        """Multiple products each with their own rating."""
        html = """
        <html><head>
        <script type="application/ld+json">
        [{
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Product A",
            "offers": {"@type": "Offer", "price": "19.99", "priceCurrency": "USD"},
            "aggregateRating": {"ratingValue": "4.2", "reviewCount": "89"}
        }, {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Product B",
            "offers": {"@type": "Offer", "price": "49.99", "priceCurrency": "USD"},
            "aggregateRating": {"ratingValue": "3.8", "reviewCount": "234"}
        }]
        </script>
        </head><body></body></html>
        """
        items = await provider.extract(html, "https://shop.example.com/products")
        assert len(items) >= 2
        ratings = [i.get("rating") for i in items]
        assert "4.2" in ratings
        assert "3.8" in ratings


# ---------------------------------------------------------------------------
# UC-17.4.2 — Shopify HTML fallback
# ---------------------------------------------------------------------------

class TestShopifyHTMLFallback:
    """When Shopify API is blocked, fall back to HTML extraction."""

    @pytest.mark.asyncio
    async def test_shopify_product_page_html(self, provider):
        """Extract product data from Shopify HTML (not API)."""
        html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Shopify Test Product",
            "brand": {"@type": "Brand", "name": "TestBrand"},
            "offers": {
                "@type": "Offer",
                "price": "45.00",
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock"
            },
            "image": "https://cdn.shopify.com/image.jpg",
            "aggregateRating": {
                "ratingValue": "4.7",
                "reviewCount": "56"
            }
        }
        </script>
        </head>
        <body>
        <h1 class="product-title">Shopify Test Product</h1>
        <span class="price">$45.00</span>
        </body></html>
        """
        items = await provider.extract(html, "https://mystore.myshopify.com/products/test")
        assert len(items) >= 1
        product = items[0]
        assert product.get("name") == "Shopify Test Product"
        assert "45" in str(product.get("price", ""))
        assert product.get("rating") == "4.7"

    @pytest.mark.asyncio
    async def test_shopify_collection_page(self, provider):
        """Extract multiple products from a Shopify collection page."""
        html = """
        <html><head>
        <script type="application/ld+json">
        [
            {"@type": "Product", "name": "Item 1", "offers": {"price": "10", "priceCurrency": "USD"}},
            {"@type": "Product", "name": "Item 2", "offers": {"price": "20", "priceCurrency": "USD"}},
            {"@type": "Product", "name": "Item 3", "offers": {"price": "30", "priceCurrency": "USD"}}
        ]
        </script>
        </head><body></body></html>
        """
        items = await provider.extract(html, "https://mystore.myshopify.com/collections/all")
        assert len(items) >= 3

    @pytest.mark.asyncio
    async def test_shopify_meta_tags_fallback(self, provider):
        """Extract from OG meta tags when JSON-LD is missing."""
        html = """
        <html><head>
        <meta property="og:title" content="Shopify Product Name" />
        <meta property="og:type" content="product" />
        <meta property="product:price:amount" content="39.99" />
        <meta property="product:price:currency" content="USD" />
        <meta property="og:image" content="https://cdn.shopify.com/img.jpg" />
        </head><body>
        <h1>Shopify Product Name</h1>
        <span class="price">$39.99</span>
        </body></html>
        """
        items = await provider.extract(html, "https://mystore.myshopify.com/products/test")
        assert len(items) >= 1
        product = items[0]
        assert "Shopify" in product.get("name", "") or "39" in str(product.get("price", ""))


# ---------------------------------------------------------------------------
# UC-17.3.1/3 — Wholesale listing + wholesale-specific fields
# ---------------------------------------------------------------------------

class TestWholesaleExtraction:
    """Extract wholesale product data including MOQ and bulk pricing."""

    @pytest.mark.asyncio
    async def test_wholesale_product_jsonld(self, provider):
        """Extract wholesale product with bulk pricing from JSON-LD."""
        html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@type": "Product",
            "name": "Bulk USB-C Cables (100-pack)",
            "offers": {
                "@type": "Offer",
                "price": "299.99",
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock"
            },
            "brand": {"name": "CablePro"},
            "description": "Minimum order quantity: 5 packs. Bulk discount: 10% off 10+ packs."
        }
        </script>
        </head><body></body></html>
        """
        items = await provider.extract(html, "https://wholesale.example.com/cables")
        assert len(items) >= 1
        product = items[0]
        assert "USB-C" in product.get("name", "")
        assert "299" in str(product.get("price", ""))

    @pytest.mark.asyncio
    async def test_wholesale_listing_multiple_items(self, provider):
        """Extract multiple wholesale items from a listing page."""
        html = """
        <html><body>
        <div class="product-card">
            <h2 class="product-title"><a href="/p1">Wholesale Widget A</a></h2>
            <span class="price">$5.99/unit</span>
        </div>
        <div class="product-card">
            <h2 class="product-title"><a href="/p2">Wholesale Widget B</a></h2>
            <span class="price">$3.49/unit</span>
        </div>
        <div class="product-card">
            <h2 class="product-title"><a href="/p3">Wholesale Widget C</a></h2>
            <span class="price">$8.99/unit</span>
        </div>
        </body></html>
        """
        items = await provider.extract(html, "https://wholesale.example.com/widgets")
        assert len(items) >= 3
        names = [i.get("name", "") for i in items]
        assert any("Widget A" in n for n in names)
        assert any("Widget B" in n for n in names)

    def test_wholesale_fields_normalization(self, normalizer):
        """Normalizer handles wholesale-specific price formats."""
        item = {
            "name": "Bulk USB Cables",
            "price": "$2.99/unit",
            "description": "MOQ: 100 units. Volume discount available.",
        }
        result = normalizer.normalize_one(item)
        assert result["price"] == "2.99"
        assert "MOQ" in result.get("description", "")


# ---------------------------------------------------------------------------
# Integration: full pipeline
# ---------------------------------------------------------------------------

class TestFullExtractionPipeline:
    """End-to-end extraction + normalization pipeline."""

    @pytest.mark.asyncio
    async def test_extract_and_normalize(self, provider, normalizer):
        """Full pipeline: HTML → extract → normalize → clean data."""
        html = """
        <html><head>
        <script type="application/ld+json">
        {
            "@type": "Product",
            "name": "<b>Awesome &amp; Great Product</b>",
            "offers": {"price": "$49.99", "priceCurrency": "USD"},
            "aggregateRating": {"ratingValue": "4.8", "reviewCount": "567"}
        }
        </script>
        </head><body></body></html>
        """
        items = await provider.extract(html, "https://shop.example.com/product")
        assert len(items) >= 1

        normalized = normalizer.normalize_batch(items, url="https://shop.example.com/product")
        product = normalized[0]

        # Name should be cleaned of HTML
        assert "<b>" not in product.get("name", "")
        assert "&amp;" not in product.get("name", "")
        # Price should be numeric
        assert product.get("price") in ("49.99", "49,99")
        # Currency should be detected
        assert product.get("currency") == "USD"

    @pytest.mark.asyncio
    async def test_extract_normalize_multiple(self, provider, normalizer):
        """Multiple products through the full pipeline."""
        html = """
        <html><head>
        <script type="application/ld+json">
        [
            {"@type": "Product", "name": "Item A", "offers": {"price": "£19.99", "priceCurrency": "GBP"}},
            {"@type": "Product", "name": "Item B", "offers": {"price": "€29.99", "priceCurrency": "EUR"}}
        ]
        </script>
        </head><body></body></html>
        """
        items = await provider.extract(html, "https://shop.co.uk/products")
        normalized = normalizer.normalize_batch(items, url="https://shop.co.uk/products")

        assert len(normalized) >= 2
        currencies = [n.get("currency") for n in normalized]
        assert "GBP" in currencies
        assert "EUR" in currencies
