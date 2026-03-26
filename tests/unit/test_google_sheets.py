"""Tests for Google Sheets connector and Keepa cache layer.

Covers:
- GoogleSheetsConnector initialization and configuration
- Row/dict conversion
- Staleness detection
- KeepaSheetCache hit/miss logic
- Column header management
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.connectors.google_sheets_connector import (
    DEFAULT_COLUMNS,
    GoogleSheetsConnector,
    KeepaSheetCache,
)


# ---------------------------------------------------------------------------
# GoogleSheetsConnector
# ---------------------------------------------------------------------------


class TestGoogleSheetsConnectorInit:

    def test_creates_with_env_defaults(self) -> None:
        """Connector can be created with default env-based config."""
        connector = GoogleSheetsConnector()
        assert connector._worksheet_name == "Products"
        assert connector._staleness_seconds == 24 * 3600
        assert not connector._initialized

    def test_creates_with_custom_params(self) -> None:
        """Connector accepts custom parameters."""
        connector = GoogleSheetsConnector(
            credentials_file="/path/to/creds.json",
            spreadsheet_id="abc123",
            worksheet_name="MyData",
            staleness_hours=48.0,
        )
        assert connector._credentials_file == "/path/to/creds.json"
        assert connector._spreadsheet_id == "abc123"
        assert connector._worksheet_name == "MyData"
        assert connector._staleness_seconds == 48 * 3600

    def test_default_columns_comprehensive(self) -> None:
        """Default columns cover all important product fields."""
        assert "asin" in DEFAULT_COLUMNS
        assert "name" in DEFAULT_COLUMNS
        assert "price" in DEFAULT_COLUMNS
        assert "rating" in DEFAULT_COLUMNS
        assert "last_updated" in DEFAULT_COLUMNS
        assert "raw_json" in DEFAULT_COLUMNS
        assert "domain" in DEFAULT_COLUMNS
        assert len(DEFAULT_COLUMNS) >= 20


class TestStalenessDetection:

    def test_fresh_data_not_stale(self) -> None:
        """Data updated recently is not stale."""
        connector = GoogleSheetsConnector(staleness_hours=24.0)
        product = {"last_updated": datetime.now(timezone.utc).isoformat()}
        assert connector._is_stale(product) is False

    def test_old_data_is_stale(self) -> None:
        """Data older than staleness threshold is stale."""
        connector = GoogleSheetsConnector(staleness_hours=24.0)
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        product = {"last_updated": old_time}
        assert connector._is_stale(product) is True

    def test_missing_timestamp_is_stale(self) -> None:
        """Data without last_updated is always stale."""
        connector = GoogleSheetsConnector(staleness_hours=24.0)
        assert connector._is_stale({}) is True
        assert connector._is_stale({"last_updated": ""}) is True

    def test_custom_staleness_threshold(self) -> None:
        """Custom staleness hours are respected."""
        connector = GoogleSheetsConnector(staleness_hours=1.0)
        # 2 hours ago — stale with 1-hour threshold
        old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        assert connector._is_stale({"last_updated": old_time}) is True

        # 30 minutes ago — fresh with 1-hour threshold
        recent_time = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        assert connector._is_stale({"last_updated": recent_time}) is False


class TestRowConversion:

    def test_dict_to_row(self) -> None:
        """Product dict converts to row matching header order."""
        connector = GoogleSheetsConnector()
        connector._headers = ["asin", "name", "price", "last_updated", "raw_json"]

        product = {"asin": "B123", "name": "Widget", "price": "29.99"}
        row = connector._dict_to_row(product, "2026-01-01T00:00:00+00:00")

        assert row[0] == "B123"
        assert row[1] == "Widget"
        assert row[2] == "29.99"
        assert row[3] == "2026-01-01T00:00:00+00:00"
        assert "B123" in row[4]  # raw_json contains the data

    def test_row_to_dict(self) -> None:
        """Row values convert back to dict using headers."""
        connector = GoogleSheetsConnector()
        connector._headers = ["asin", "name", "price"]

        row = ["B123", "Widget", "29.99"]
        result = connector._row_to_dict(row)

        assert result["asin"] == "B123"
        assert result["name"] == "Widget"
        assert result["price"] == "29.99"

    def test_col_index(self) -> None:
        """Column index lookup works correctly."""
        connector = GoogleSheetsConnector()
        connector._headers = ["asin", "name", "price", "rating"]

        assert connector._col_index("asin") == 1
        assert connector._col_index("name") == 2
        assert connector._col_index("price") == 3
        assert connector._col_index("rating") == 4
        assert connector._col_index("nonexistent") == 1  # Default


# ---------------------------------------------------------------------------
# KeepaSheetCache
# ---------------------------------------------------------------------------


class TestKeepaSheetCache:

    @pytest.mark.asyncio
    async def test_cache_hit_skips_keepa(self) -> None:
        """When data is in Sheet, Keepa is NOT called."""
        mock_keepa = AsyncMock()
        mock_sheets = AsyncMock()
        mock_sheets.get_products_by_asins = AsyncMock(return_value={
            "B123": {"asin": "B123", "name": "Cached Widget", "price": "19.99"},
        })

        cache = KeepaSheetCache(keepa=mock_keepa, sheets=mock_sheets)
        products = await cache.get_products(["B123"])

        assert len(products) == 1
        assert products[0]["name"] == "Cached Widget"
        mock_keepa.query_products.assert_not_called()
        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 0

    @pytest.mark.asyncio
    async def test_cache_miss_calls_keepa_and_writes(self) -> None:
        """When data is NOT in Sheet, Keepa is called and result written."""
        mock_keepa = AsyncMock()
        mock_keepa.query_products = AsyncMock(return_value=[
            {"asin": "B456", "name": "Fresh Widget", "price": "29.99"},
        ])

        mock_sheets = AsyncMock()
        mock_sheets.get_products_by_asins = AsyncMock(return_value={})
        mock_sheets.write_products = AsyncMock(return_value=1)

        cache = KeepaSheetCache(keepa=mock_keepa, sheets=mock_sheets)
        products = await cache.get_products(["B456"], domain="US")

        assert len(products) == 1
        assert products[0]["name"] == "Fresh Widget"
        mock_keepa.query_products.assert_called_once()
        mock_sheets.write_products.assert_called_once()
        assert cache.stats["hits"] == 0
        assert cache.stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_partial_cache_hit(self) -> None:
        """Some ASINs cached, others not — only missing ones hit Keepa."""
        mock_keepa = AsyncMock()
        mock_keepa.query_products = AsyncMock(return_value=[
            {"asin": "B789", "name": "New Product"},
        ])

        mock_sheets = AsyncMock()
        mock_sheets.get_products_by_asins = AsyncMock(return_value={
            "B123": {"asin": "B123", "name": "Cached Product"},
        })
        mock_sheets.write_products = AsyncMock(return_value=1)

        cache = KeepaSheetCache(keepa=mock_keepa, sheets=mock_sheets)
        products = await cache.get_products(["B123", "B789"])

        assert len(products) == 2
        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 1

        # Keepa should only be called for B789
        call_args = mock_keepa.query_products.call_args
        assert "B789" in call_args.kwargs["asins"]
        assert "B123" not in call_args.kwargs["asins"]

    @pytest.mark.asyncio
    async def test_stats_accumulate(self) -> None:
        """Hit/miss stats accumulate across calls."""
        mock_keepa = AsyncMock()
        mock_keepa.query_products = AsyncMock(return_value=[])
        mock_sheets = AsyncMock()
        mock_sheets.get_products_by_asins = AsyncMock(return_value={})
        mock_sheets.write_products = AsyncMock(return_value=0)

        cache = KeepaSheetCache(keepa=mock_keepa, sheets=mock_sheets)

        await cache.get_products(["A1", "A2"])
        await cache.get_products(["A3"])

        assert cache.stats["misses"] == 3
        assert cache.stats["total_queries"] == 3
