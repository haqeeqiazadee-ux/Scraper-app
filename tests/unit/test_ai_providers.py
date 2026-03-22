"""Tests for AI provider abstraction (deterministic provider, factory, chain)."""

import pytest

from packages.core.ai_providers.base import AIProviderFactory, AIProviderChain
from packages.core.ai_providers.deterministic import DeterministicProvider


SAMPLE_JSONLD_HTML = """
<html>
<head><title>Test Product</title></head>
<body>
<script type="application/ld+json">
{
    "@type": "Product",
    "name": "Test Widget",
    "description": "A great widget",
    "sku": "WDG-001",
    "brand": {"@type": "Brand", "name": "WidgetCo"},
    "image": "https://example.com/widget.jpg",
    "offers": {
        "@type": "Offer",
        "price": "29.99",
        "priceCurrency": "USD",
        "availability": "InStock"
    },
    "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": "4.5",
        "reviewCount": "128"
    }
}
</script>
</body>
</html>
"""

SAMPLE_BASIC_HTML = """
<html>
<head><title>Laptop XYZ - Buy Now for $999.99</title></head>
<body>
<h1>Laptop XYZ</h1>
<span class="price">$999.99 USD</span>
</body>
</html>
"""


class TestDeterministicProvider:

    @pytest.fixture
    def provider(self):
        return DeterministicProvider()

    @pytest.mark.asyncio
    async def test_extract_jsonld(self, provider):
        """Should extract product data from JSON-LD."""
        products = await provider.extract(SAMPLE_JSONLD_HTML, "https://example.com/product")
        assert len(products) == 1
        product = products[0]
        assert product["name"] == "Test Widget"
        assert product["sku"] == "WDG-001"
        assert product["price"] == "29.99"
        assert product["currency"] == "USD"
        assert product["brand"] == "WidgetCo"
        assert product["rating"] == "4.5"
        assert product["reviews_count"] == "128"

    @pytest.mark.asyncio
    async def test_extract_basic_html(self, provider):
        """Should extract basic data when no JSON-LD present."""
        products = await provider.extract(SAMPLE_BASIC_HTML, "https://example.com/laptop")
        assert len(products) == 1
        product = products[0]
        assert "Laptop XYZ" in product.get("name", "")
        assert product.get("product_url") == "https://example.com/laptop"

    @pytest.mark.asyncio
    async def test_extract_empty_html(self, provider):
        """Should handle empty HTML gracefully."""
        products = await provider.extract("", "https://example.com")
        assert isinstance(products, list)

    @pytest.mark.asyncio
    async def test_classify(self, provider):
        """Should classify based on keyword frequency."""
        result = await provider.classify(
            "This laptop has great performance and battery life",
            ["electronics", "clothing", "food"],
        )
        assert isinstance(result, str)
        assert result in ["electronics", "clothing", "food"]

    @pytest.mark.asyncio
    async def test_normalize(self, provider):
        """Should map common field aliases."""
        data = {
            "product_name": "Widget",
            "cost": "29.99",
            "img": "https://example.com/img.jpg",
        }
        result = await provider.normalize(data, {})
        assert result["name"] == "Widget"
        assert result["price"] == "29.99"
        assert result["image_url"] == "https://example.com/img.jpg"

    def test_token_usage(self, provider):
        """Deterministic provider should report 0 tokens."""
        assert provider.get_token_usage() == 0


class TestAIProviderFactory:

    def test_create_deterministic(self):
        provider = AIProviderFactory.create("deterministic")
        assert isinstance(provider, DeterministicProvider)

    def test_create_unknown_falls_back(self):
        provider = AIProviderFactory.create("unknown_provider")
        assert isinstance(provider, DeterministicProvider)

    def test_create_gemini_without_key_falls_back(self):
        provider = AIProviderFactory.create("gemini", api_key=None)
        assert isinstance(provider, DeterministicProvider)


class TestAIProviderChain:

    @pytest.mark.asyncio
    async def test_chain_uses_first_provider(self):
        provider = DeterministicProvider()
        chain = AIProviderChain([provider])

        products = await chain.extract(SAMPLE_JSONLD_HTML, "https://example.com")
        assert len(products) == 1

    @pytest.mark.asyncio
    async def test_chain_token_usage(self):
        chain = AIProviderChain([DeterministicProvider()])
        assert chain.get_token_usage() == 0

    @pytest.mark.asyncio
    async def test_chain_classify(self):
        chain = AIProviderChain([DeterministicProvider()])
        result = await chain.classify("test", ["a", "b"])
        assert result in ["a", "b"]

    @pytest.mark.asyncio
    async def test_chain_normalize(self):
        chain = AIProviderChain([DeterministicProvider()])
        result = await chain.normalize({"product_name": "X"}, {})
        assert result["name"] == "X"

    @pytest.mark.asyncio
    async def test_factory_create_chain(self):
        chain = AIProviderFactory.create_chain([
            {"provider_type": "deterministic"},
        ])
        products = await chain.extract(SAMPLE_JSONLD_HTML, "https://example.com")
        assert len(products) >= 1
