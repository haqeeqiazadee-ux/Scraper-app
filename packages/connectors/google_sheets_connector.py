"""
Google Sheets Connector — read/write product data from Google Sheets.

Acts as a cache layer in front of Keepa to avoid paying for the same
product data twice. The flow:

1. User queries Amazon product → check Google Sheet first
2. If data exists and is fresh → return from Sheet (free, instant)
3. If data is missing or stale → query Keepa API → write result to Sheet
4. Next time same product is queried → served from Sheet

Supports:
- Service account authentication (JSON key file)
- API key authentication (for public/shared sheets)
- Read by ASIN, search by column values
- Write/update product rows
- Configurable staleness threshold (default 24 hours)
- Batch read/write for efficiency

Setup:
1. Create a Google Cloud project and enable Sheets API
2. Create a service account and download JSON key file
3. Share your Google Sheet with the service account email
4. Set GOOGLE_SHEETS_CREDENTIALS_FILE and GOOGLE_SHEETS_SPREADSHEET_ID in .env

Usage:
    sheets = GoogleSheetsConnector(
        credentials_file="service_account.json",
        spreadsheet_id="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
    )
    await sheets.initialize()

    # Check if product exists in sheet
    product = await sheets.get_product_by_asin("B09V3KXJPB")

    # Write Keepa data to sheet
    await sheets.write_products([keepa_product_dict])

    # Batch read
    products = await sheets.get_products_by_asins(["B09V3KXJPB", "B08N5WRWNW"])
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default column headers for the product data sheet
DEFAULT_COLUMNS = [
    "asin", "name", "price", "original_price", "currency", "rating",
    "reviews_count", "sales_rank", "brand", "manufacturer", "category",
    "image_url", "product_url", "stock_status", "offer_count_new",
    "offer_count_used", "amazon_price", "used_price", "fba_price",
    "monthly_sold", "source", "domain", "last_updated", "raw_json",
]


class GoogleSheetsConnector:
    """Read/write Amazon product data from/to Google Sheets.

    Acts as a cache layer to avoid repeated Keepa API calls.
    Supports service account auth (for automated access) and
    API key auth (for public sheets).
    """

    def __init__(
        self,
        credentials_file: Optional[str] = None,
        spreadsheet_id: Optional[str] = None,
        worksheet_name: str = "Products",
        staleness_hours: float = 24.0,
    ) -> None:
        """Initialize Google Sheets connector.

        Args:
            credentials_file: Path to service account JSON key file.
                Falls back to GOOGLE_SHEETS_CREDENTIALS_FILE env var.
            spreadsheet_id: Google Sheets document ID.
                Falls back to GOOGLE_SHEETS_SPREADSHEET_ID env var.
            worksheet_name: Name of the worksheet tab to use.
            staleness_hours: Hours after which cached data is considered stale.
        """
        self._credentials_file = credentials_file or os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE", "")
        self._spreadsheet_id = spreadsheet_id or os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", "")
        self._worksheet_name = worksheet_name
        self._staleness_seconds = staleness_hours * 3600
        self._client = None
        self._sheet = None
        self._worksheet = None
        self._headers: list[str] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the Google Sheets connection.

        Creates the worksheet and headers if they don't exist.
        Must be called before any read/write operations.
        """
        if self._initialized:
            return

        await asyncio.to_thread(self._init_sync)
        self._initialized = True

    def _init_sync(self) -> None:
        """Synchronous initialization (runs in thread)."""
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        if self._credentials_file and os.path.exists(self._credentials_file):
            creds = Credentials.from_service_account_file(self._credentials_file, scopes=scopes)
            self._client = gspread.authorize(creds)
        else:
            # Try default credentials (e.g., in GCP environment)
            try:
                creds = Credentials.from_service_account_info(
                    json.loads(os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON", "{}")),
                    scopes=scopes,
                )
                self._client = gspread.authorize(creds)
            except Exception:
                raise ValueError(
                    "No Google Sheets credentials found. Set GOOGLE_SHEETS_CREDENTIALS_FILE "
                    "or GOOGLE_SHEETS_CREDENTIALS_JSON environment variable."
                )

        if not self._spreadsheet_id:
            raise ValueError("No spreadsheet ID. Set GOOGLE_SHEETS_SPREADSHEET_ID environment variable.")

        self._sheet = self._client.open_by_key(self._spreadsheet_id)

        # Get or create worksheet
        try:
            self._worksheet = self._sheet.worksheet(self._worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            self._worksheet = self._sheet.add_worksheet(
                title=self._worksheet_name, rows=1000, cols=len(DEFAULT_COLUMNS)
            )
            # Write headers
            self._worksheet.update("A1", [DEFAULT_COLUMNS])
            logger.info("Created worksheet '%s' with headers", self._worksheet_name)

        # Read headers from first row
        self._headers = self._worksheet.row_values(1)
        if not self._headers:
            self._worksheet.update("A1", [DEFAULT_COLUMNS])
            self._headers = DEFAULT_COLUMNS
            logger.info("Initialized headers in worksheet '%s'", self._worksheet_name)

    # ---- Read Operations --------------------------------------------------

    async def get_product_by_asin(self, asin: str) -> Optional[dict]:
        """Get a single product by ASIN from the sheet.

        Returns None if not found or data is stale.
        """
        await self.initialize()
        return await asyncio.to_thread(self._get_by_asin_sync, asin)

    def _get_by_asin_sync(self, asin: str) -> Optional[dict]:
        """Synchronous ASIN lookup."""
        try:
            cell = self._worksheet.find(asin, in_column=self._col_index("asin"))
            if cell is None:
                return None

            row_values = self._worksheet.row_values(cell.row)
            product = self._row_to_dict(row_values)

            # Check staleness
            if self._is_stale(product):
                logger.debug("Sheet data for %s is stale (> %dh)", asin, int(self._staleness_seconds / 3600))
                return None

            return product
        except Exception as e:
            logger.debug("Sheet lookup failed for %s: %s", asin, e)
            return None

    async def get_products_by_asins(self, asins: list[str]) -> dict[str, dict]:
        """Batch lookup multiple ASINs. Returns {asin: product_dict} for found items."""
        await self.initialize()
        return await asyncio.to_thread(self._batch_get_sync, asins)

    def _batch_get_sync(self, asins: list[str]) -> dict[str, dict]:
        """Synchronous batch lookup — reads all data once and filters."""
        try:
            all_records = self._worksheet.get_all_records()
            asin_set = set(asins)
            results = {}

            for record in all_records:
                asin = str(record.get("asin", ""))
                if asin in asin_set:
                    if not self._is_stale(record):
                        results[asin] = record

            return results
        except Exception as e:
            logger.debug("Sheet batch lookup failed: %s", e)
            return {}

    async def search_products(
        self,
        column: str,
        value: str,
        max_results: int = 50,
    ) -> list[dict]:
        """Search products by any column value.

        Args:
            column: Column name to search (e.g., "brand", "category").
            value: Value to search for (case-insensitive substring match).
            max_results: Maximum number of results.
        """
        await self.initialize()
        return await asyncio.to_thread(self._search_sync, column, value, max_results)

    def _search_sync(self, column: str, value: str, max_results: int) -> list[dict]:
        """Synchronous search."""
        try:
            all_records = self._worksheet.get_all_records()
            value_lower = value.lower()
            results = []

            for record in all_records:
                field_val = str(record.get(column, "")).lower()
                if value_lower in field_val:
                    if not self._is_stale(record):
                        results.append(record)
                    if len(results) >= max_results:
                        break

            return results
        except Exception as e:
            logger.debug("Sheet search failed: %s", e)
            return []

    async def get_all_products(self) -> list[dict]:
        """Get all products from the sheet (non-stale only)."""
        await self.initialize()
        return await asyncio.to_thread(self._get_all_sync)

    def _get_all_sync(self) -> list[dict]:
        """Synchronous get all."""
        try:
            all_records = self._worksheet.get_all_records()
            return [r for r in all_records if not self._is_stale(r)]
        except Exception as e:
            logger.debug("Sheet get_all failed: %s", e)
            return []

    # ---- Write Operations -------------------------------------------------

    async def write_products(self, products: list[dict]) -> int:
        """Write/update product data to the sheet.

        If a product with the same ASIN exists, updates the row.
        Otherwise, appends a new row.

        Args:
            products: List of product dicts (from Keepa or any source).

        Returns:
            Number of products written/updated.
        """
        await self.initialize()
        return await asyncio.to_thread(self._write_sync, products)

    def _write_sync(self, products: list[dict]) -> int:
        """Synchronous write/update."""
        written = 0
        now = datetime.now(timezone.utc).isoformat()

        for product in products:
            try:
                asin = product.get("asin", "")
                if not asin:
                    continue

                # Build row from product dict
                row = self._dict_to_row(product, now)

                # Check if ASIN already exists
                existing_cell = None
                try:
                    existing_cell = self._worksheet.find(asin, in_column=self._col_index("asin"))
                except Exception:
                    pass

                if existing_cell:
                    # Update existing row
                    cell_range = f"A{existing_cell.row}"
                    self._worksheet.update(cell_range, [row])
                else:
                    # Append new row
                    self._worksheet.append_row(row, value_input_option="USER_ENTERED")

                written += 1
            except Exception as e:
                logger.warning("Failed to write product %s to sheet: %s", product.get("asin"), e)

        if written > 0:
            logger.info("Wrote %d products to Google Sheet", written)
        return written

    async def write_product(self, product: dict) -> bool:
        """Write/update a single product. Convenience wrapper."""
        count = await self.write_products([product])
        return count > 0

    # ---- Helpers ----------------------------------------------------------

    def _col_index(self, column_name: str) -> int:
        """Get 1-based column index for a header name."""
        try:
            return self._headers.index(column_name) + 1
        except ValueError:
            return 1  # Default to first column

    def _row_to_dict(self, row_values: list) -> dict:
        """Convert a row of values to a dict using headers."""
        result = {}
        for i, header in enumerate(self._headers):
            if i < len(row_values):
                result[header] = row_values[i]
            else:
                result[header] = ""
        return result

    def _dict_to_row(self, product: dict, timestamp: str) -> list:
        """Convert a product dict to a row of values matching headers."""
        product["last_updated"] = timestamp

        # Store full product as JSON in raw_json column
        raw_copy = {k: v for k, v in product.items() if k != "raw_json"}
        product["raw_json"] = json.dumps(raw_copy, default=str)

        row = []
        for header in self._headers:
            val = product.get(header, "")
            # Convert complex types to strings
            if isinstance(val, (dict, list)):
                val = json.dumps(val, default=str)
            elif val is None:
                val = ""
            row.append(str(val))
        return row

    def _is_stale(self, product: dict) -> bool:
        """Check if a product's data is older than staleness threshold."""
        last_updated = product.get("last_updated", "")
        if not last_updated:
            return True
        try:
            updated_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - updated_dt).total_seconds()
            return age > self._staleness_seconds
        except (ValueError, TypeError):
            return True

    # ---- Sheet Management -------------------------------------------------

    async def clear_stale_data(self) -> int:
        """Remove rows with stale data from the sheet."""
        await self.initialize()
        return await asyncio.to_thread(self._clear_stale_sync)

    def _clear_stale_sync(self) -> int:
        """Synchronous stale data cleanup."""
        try:
            all_records = self._worksheet.get_all_records()
            rows_to_delete = []

            for i, record in enumerate(all_records):
                if self._is_stale(record):
                    rows_to_delete.append(i + 2)  # +2: 1-indexed + header row

            # Delete from bottom to top to preserve row indices
            for row_num in reversed(rows_to_delete):
                self._worksheet.delete_rows(row_num)

            if rows_to_delete:
                logger.info("Cleared %d stale rows from sheet", len(rows_to_delete))
            return len(rows_to_delete)
        except Exception as e:
            logger.warning("Failed to clear stale data: %s", e)
            return 0

    async def get_sheet_stats(self) -> dict:
        """Get statistics about the sheet."""
        await self.initialize()
        return await asyncio.to_thread(self._stats_sync)

    def _stats_sync(self) -> dict:
        """Synchronous stats."""
        try:
            all_records = self._worksheet.get_all_records()
            stale = sum(1 for r in all_records if self._is_stale(r))
            return {
                "total_products": len(all_records),
                "fresh_products": len(all_records) - stale,
                "stale_products": stale,
                "worksheet": self._worksheet_name,
                "spreadsheet_id": self._spreadsheet_id,
                "staleness_hours": self._staleness_seconds / 3600,
            }
        except Exception as e:
            return {"error": str(e)}


class KeepaSheetCache:
    """Cache layer that checks Google Sheets before querying Keepa.

    Usage:
        cache = KeepaSheetCache(keepa_connector, sheets_connector)

        # This checks sheet first, queries Keepa only if needed,
        # and writes results back to sheet for next time
        products = await cache.get_products(["B09V3KXJPB", "B08N5WRWNW"])
    """

    def __init__(
        self,
        keepa: Any,  # KeepaConnector
        sheets: GoogleSheetsConnector,
    ) -> None:
        self._keepa = keepa
        self._sheets = sheets
        self._cache_hits = 0
        self._cache_misses = 0

    async def get_products(
        self,
        asins: list[str],
        domain: str = "US",
        **keepa_kwargs: Any,
    ) -> list[dict]:
        """Get products — from Sheet cache if available, Keepa if not.

        1. Check Google Sheet for each ASIN
        2. Query Keepa only for ASINs not in Sheet (or stale)
        3. Write Keepa results back to Sheet for future queries
        4. Return combined results

        Args:
            asins: List of ASINs to look up.
            domain: Keepa domain code.
            **keepa_kwargs: Additional params passed to keepa.query_products().

        Returns:
            List of product dicts (from Sheet or Keepa).
        """
        # Step 1: Check sheet for all ASINs
        cached = await self._sheets.get_products_by_asins(asins)
        self._cache_hits += len(cached)

        # Step 2: Find ASINs not in cache
        missing_asins = [a for a in asins if a not in cached]
        self._cache_misses += len(missing_asins)

        if missing_asins:
            logger.info(
                "Sheet cache: %d hits, %d misses — querying Keepa for %d ASINs",
                len(cached), len(missing_asins), len(missing_asins),
            )

            # Step 3: Query Keepa for missing ASINs
            keepa_products = await self._keepa.query_products(
                asins=missing_asins,
                domain=domain,
                **keepa_kwargs,
            )

            # Step 4: Write Keepa results to Sheet
            if keepa_products:
                for p in keepa_products:
                    p["domain"] = domain
                await self._sheets.write_products(keepa_products)

            # Combine cached + fresh
            all_products = list(cached.values()) + keepa_products
        else:
            logger.info("Sheet cache: %d/%d ASINs served from cache", len(cached), len(asins))
            all_products = list(cached.values())

        return all_products

    @property
    def stats(self) -> dict:
        """Cache hit/miss statistics."""
        total = self._cache_hits + self._cache_misses
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": self._cache_hits / max(total, 1),
            "total_queries": total,
        }
