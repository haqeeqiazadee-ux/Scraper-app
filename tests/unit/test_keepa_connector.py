"""Tests for the Keepa connector and Amazon routing.

Covers:
- ASIN extraction from various Amazon URL formats
- Amazon domain detection
- Product data transformation (Keepa format → our format)
- Router Amazon routing (product pages → Keepa API, search → browser)
- KeepaConnector protocol compliance
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.connectors.keepa_connector import (
    KeepaConnector,
    extract_asin,
    detect_amazon_domain,
    is_amazon_url,
    AMAZON_TLD_TO_DOMAIN,
)
from packages.core.interfaces import FetchRequest


# ---------------------------------------------------------------------------
# ASIN Extraction
# ---------------------------------------------------------------------------


class TestASINExtraction:

    def test_extract_from_dp_url(self) -> None:
        assert extract_asin("https://www.amazon.com/dp/B09V3KXJPB") == "B09V3KXJPB"

    def test_extract_from_dp_url_with_title(self) -> None:
        url = "https://www.amazon.com/Some-Product-Name/dp/B09V3KXJPB/ref=sr_1_1"
        assert extract_asin(url) == "B09V3KXJPB"

    def test_extract_from_gp_product(self) -> None:
        assert extract_asin("https://www.amazon.com/gp/product/B09V3KXJPB") == "B09V3KXJPB"

    def test_extract_from_asin_path(self) -> None:
        assert extract_asin("https://www.amazon.com/ASIN/B09V3KXJPB") == "B09V3KXJPB"

    def test_extract_from_international(self) -> None:
        assert extract_asin("https://www.amazon.co.uk/dp/B08N5WRWNW") == "B08N5WRWNW"
        assert extract_asin("https://www.amazon.de/dp/B08N5WRWNW") == "B08N5WRWNW"

    def test_no_asin_in_search_url(self) -> None:
        assert extract_asin("https://www.amazon.com/s?k=wireless+mouse") is None

    def test_no_asin_in_homepage(self) -> None:
        assert extract_asin("https://www.amazon.com/") is None

    def test_no_asin_in_deals(self) -> None:
        assert extract_asin("https://www.amazon.com/events/deals") is None


# ---------------------------------------------------------------------------
# Domain Detection
# ---------------------------------------------------------------------------


class TestDomainDetection:

    def test_us_domain(self) -> None:
        assert detect_amazon_domain("https://www.amazon.com/dp/B123") == "US"

    def test_uk_domain(self) -> None:
        assert detect_amazon_domain("https://www.amazon.co.uk/dp/B123") == "GB"

    def test_de_domain(self) -> None:
        assert detect_amazon_domain("https://www.amazon.de/dp/B123") == "DE"

    def test_jp_domain(self) -> None:
        assert detect_amazon_domain("https://www.amazon.co.jp/dp/B123") == "JP"

    def test_in_domain(self) -> None:
        assert detect_amazon_domain("https://www.amazon.in/dp/B123") == "IN"

    def test_all_domains_covered(self) -> None:
        """Every entry in AMAZON_TLD_TO_DOMAIN resolves correctly."""
        for tld, code in AMAZON_TLD_TO_DOMAIN.items():
            url = f"https://www.{tld}/dp/B000000000"
            assert detect_amazon_domain(url) == code, f"{tld} should map to {code}"

    def test_unknown_defaults_to_us(self) -> None:
        assert detect_amazon_domain("https://www.example.com/dp/B123") == "US"


class TestIsAmazonURL:

    def test_amazon_com(self) -> None:
        assert is_amazon_url("https://www.amazon.com/dp/B123") is True

    def test_amazon_de(self) -> None:
        assert is_amazon_url("https://amazon.de/dp/B123") is True

    def test_not_amazon(self) -> None:
        assert is_amazon_url("https://www.ebay.com/itm/123") is False

    def test_not_amazon_subdomain(self) -> None:
        assert is_amazon_url("https://amazonclone.com/dp/B123") is False


# ---------------------------------------------------------------------------
# Router Amazon Routing
# ---------------------------------------------------------------------------


class TestRouterAmazonRouting:

    def test_amazon_product_url_routes_to_api(self) -> None:
        """Amazon /dp/ URLs route to API lane (Keepa)."""
        from packages.contracts.task import Task
        from packages.core.router import ExecutionRouter, Lane

        router = ExecutionRouter()
        task = Task(tenant_id="t1", url="https://www.amazon.com/dp/B09V3KXJPB")
        decision = router.route(task)
        assert decision.lane == Lane.API
        assert "Keepa" in decision.reason or "ASIN" in decision.reason

    def test_amazon_search_url_routes_to_api(self) -> None:
        """Amazon search URLs route to Keepa API (priority for ALL Amazon queries)."""
        from packages.contracts.task import Task
        from packages.core.router import ExecutionRouter, Lane

        router = ExecutionRouter()
        task = Task(tenant_id="t1", url="https://www.amazon.com/s?k=wireless+mouse")
        decision = router.route(task)
        assert decision.lane == Lane.API
        assert Lane.BROWSER in decision.fallback_lanes

    def test_amazon_deals_url_routes_to_api(self) -> None:
        """Amazon deals URLs route to Keepa API first."""
        from packages.contracts.task import Task
        from packages.core.router import ExecutionRouter, Lane

        router = ExecutionRouter()
        task = Task(tenant_id="t1", url="https://www.amazon.com/events/deals")
        decision = router.route(task)
        assert decision.lane == Lane.API
        assert Lane.BROWSER in decision.fallback_lanes

    def test_amazon_product_has_browser_fallback(self) -> None:
        """Amazon product pages fall back to browser if Keepa fails."""
        from packages.contracts.task import Task
        from packages.core.router import ExecutionRouter, Lane

        router = ExecutionRouter()
        task = Task(tenant_id="t1", url="https://www.amazon.com/dp/B09V3KXJPB")
        decision = router.route(task)
        assert Lane.BROWSER in decision.fallback_lanes

    def test_amazon_international_product_routes_to_api(self) -> None:
        """International Amazon product pages also route to Keepa API."""
        from packages.contracts.task import Task
        from packages.core.router import ExecutionRouter, Lane

        router = ExecutionRouter()
        task = Task(tenant_id="t1", url="https://www.amazon.de/dp/B08N5WRWNW")
        decision = router.route(task)
        assert decision.lane == Lane.API


# ---------------------------------------------------------------------------
# Product Data Transformation
# ---------------------------------------------------------------------------


class TestProductTransformation:

    def test_transform_basic_product(self) -> None:
        """Keepa product dict transforms to our format."""
        import numpy as np

        connector = KeepaConnector(api_key="test_key")
        raw = {
            "asin": "B09V3KXJPB",
            "title": "Test Product Widget Pro",
            "brand": "TestBrand",
            "manufacturer": "TestMfg",
            "imagesCSV": "41abc123.jpg,42def456.jpg",
            "availabilityAmazon": 0,
            "data": {
                "AMAZON": np.array([2999.0, 2899.0, 2799.0]),
                "BUY_BOX_SHIPPING": np.array([2999.0, 2899.0, 2799.0]),
                "LISTPRICE": np.array([3999.0]),
                "RATING": np.array([45.0]),
                "COUNT_REVIEWS": np.array([1234.0]),
                "SALES": np.array([5678.0]),
                "COUNT_NEW": np.array([15.0]),
                "COUNT_USED": np.array([8.0]),
            },
        }

        product = connector._transform_product(raw, "USD", "US")

        assert product is not None
        assert product["name"] == "Test Product Widget Pro"
        assert product["asin"] == "B09V3KXJPB"
        assert product["brand"] == "TestBrand"
        assert product["price"] == "27.99"  # 2799 cents → $27.99
        assert product["original_price"] == "39.99"
        assert product["rating"] == "4.5"
        assert product["reviews_count"] == "1234"
        assert product["sales_rank"] == 5678
        assert product["stock_status"] == "InStock"
        assert product["currency"] == "USD"
        assert product["source"] == "keepa_api"
        assert "amazon.com/dp/B09V3KXJPB" in product["product_url"]
        assert product["offer_count_new"] == 15
        assert product["offer_count_used"] == 8

    def test_transform_empty_product_returns_none(self) -> None:
        connector = KeepaConnector(api_key="test_key")
        assert connector._transform_product({}, "USD", "US") is None
        assert connector._transform_product({"title": ""}, "USD", "US") is None


# ---------------------------------------------------------------------------
# Connector Protocol
# ---------------------------------------------------------------------------


class TestKeepaConnectorProtocol:

    def test_creates_without_error(self) -> None:
        connector = KeepaConnector(api_key="test_key_abc123")
        assert connector._api_key == "test_key_abc123"
        assert connector._api is None

    def test_metrics_initially_zero(self) -> None:
        connector = KeepaConnector(api_key="test")
        metrics = connector.get_metrics()
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0

    @pytest.mark.asyncio
    async def test_fetch_non_amazon_returns_404(self) -> None:
        """fetch() with non-Amazon URL returns 404 (no Keepa data)."""
        connector = KeepaConnector(api_key="test")
        # A URL with no ASIN and no search keyword will fail gracefully
        request = FetchRequest(url="https://www.amazon.com/")
        response = await connector.fetch(request)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_close_clears_api(self) -> None:
        connector = KeepaConnector(api_key="test")
        connector._api = MagicMock()
        await connector.close()
        assert connector._api is None
