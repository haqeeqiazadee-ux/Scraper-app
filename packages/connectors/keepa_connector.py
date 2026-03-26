"""
Keepa Connector — Amazon product data via Keepa API.

Replaces browser scraping for Amazon product queries. Instead of fighting
AWS WAF, CAPTCHAs, and anti-bot detection, we call Keepa's API with an
ASIN and get back richer data than we could ever scrape:

- Complete price history (not just current price)
- Sales rank, buy box, offer counts
- Rating and review history
- Stock levels, FBA fees
- All without triggering any anti-bot detection

Usage:
    connector = KeepaConnector(api_key="your_64_char_key")
    products = await connector.query_products(["B09V3KXJPB"], domain="US")
    deals = await connector.find_deals(min_discount=30, category="Electronics")
    asins = await connector.search_products(title="wireless mouse", brand="Logitech")
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

from packages.core.interfaces import ConnectorMetrics, FetchRequest, FetchResponse

logger = logging.getLogger(__name__)

# Amazon TLD to Keepa domain code mapping (all supported marketplaces)
AMAZON_TLD_TO_DOMAIN: dict[str, str] = {
    "amazon.com": "US",
    "amazon.co.uk": "GB",
    "amazon.de": "DE",
    "amazon.fr": "FR",
    "amazon.co.jp": "JP",
    "amazon.ca": "CA",
    "amazon.it": "IT",
    "amazon.es": "ES",
    "amazon.in": "IN",
    "amazon.com.mx": "MX",
    "amazon.com.br": "BR",
    # These Amazon domains exist but Keepa doesn't support them yet —
    # they'll fall back to browser scraping via the router
    "amazon.com.au": "US",  # Fallback: not in Keepa
    "amazon.nl": "US",
    "amazon.sg": "US",
    "amazon.ae": "US",
    "amazon.sa": "US",
    "amazon.pl": "US",
    "amazon.se": "US",
    "amazon.com.tr": "US",
}

# Keepa domain code to currency
DOMAIN_CURRENCY: dict[str, str] = {
    "US": "USD", "GB": "GBP", "DE": "EUR", "FR": "EUR",
    "JP": "JPY", "CA": "CAD", "IT": "EUR", "ES": "EUR",
    "IN": "INR", "MX": "MXN", "BR": "BRL",
}

# Keepa-supported domain codes (for validation)
KEEPA_SUPPORTED_DOMAINS = {"US", "GB", "DE", "FR", "JP", "CA", "IT", "ES", "IN", "MX", "BR"}

# ASIN regex
ASIN_PATTERN = re.compile(r"\b([A-Z0-9]{10})\b")
ASIN_URL_PATTERN = re.compile(r"/(?:dp|gp/product|ASIN)/([A-Z0-9]{10})")


def extract_asin(url: str) -> Optional[str]:
    """Extract ASIN from an Amazon URL."""
    match = ASIN_URL_PATTERN.search(url)
    if match:
        return match.group(1)
    # Try bare ASIN in path
    path = urlparse(url).path
    match = ASIN_PATTERN.search(path)
    return match.group(1) if match else None


def detect_amazon_domain(url: str) -> str:
    """Detect Keepa domain code from an Amazon URL."""
    netloc = urlparse(url).netloc.lower().replace("www.", "")
    for tld, code in AMAZON_TLD_TO_DOMAIN.items():
        if netloc.endswith(tld):
            return code
    return "US"  # Default


def is_amazon_url(url: str) -> bool:
    """Check if a URL is from any Amazon marketplace."""
    netloc = urlparse(url).netloc.lower().replace("www.", "")
    return any(netloc.endswith(tld) for tld in AMAZON_TLD_TO_DOMAIN)


class KeepaConnector:
    """Keepa API connector for Amazon product data.

    Provides:
    - Product queries by ASIN (batch up to 100)
    - Product search by attributes (title, brand, price range, category)
    - Deal finding (price drops, lightning deals)
    - Best seller lists
    - Seller information
    - Category browsing

    Token management is handled automatically — the connector waits for
    token refills when rate-limited (429).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 15.0,
        sheets_cache: Optional[Any] = None,
    ) -> None:
        self._api_key = api_key or self._load_api_key()
        self._timeout = timeout
        self._api = None
        self._metrics = ConnectorMetrics()
        # Optional Google Sheets cache layer — if set, checks sheet before Keepa
        self._sheets_cache = sheets_cache  # KeepaSheetCache instance

    def _load_api_key(self) -> str:
        """Load Keepa API key from environment."""
        import os
        key = os.environ.get("KEEPA_API_KEY", "")
        if not key:
            logger.warning("KEEPA_API_KEY not set — Keepa queries will fail")
        return key

    async def _ensure_api(self) -> Any:
        """Lazy-initialize the async Keepa client."""
        if self._api is not None:
            return self._api
        try:
            import keepa
            self._api = await keepa.AsyncKeepa.create(self._api_key, timeout=self._timeout)
            logger.info("Keepa API initialized (tokens_left=%d)", self._api.tokens_left)
            return self._api
        except Exception as e:
            logger.error("Failed to initialize Keepa API: %s", e)
            raise

    # ---- Core Product Query ------------------------------------------------

    async def query_products(
        self,
        asins: list[str],
        domain: str = "US",
        include_offers: bool = False,
        include_buybox: bool = False,
        include_rating: bool = True,
        include_stock: bool = False,
        include_videos: bool = False,
        include_aplus: bool = False,
        stats_days: int = 90,
        history_days: Optional[int] = 30,
        update: Optional[int] = None,
        only_live_offers: Optional[bool] = None,
        product_code_is_asin: bool = True,
        extra_params: Optional[dict] = None,
    ) -> list[dict]:
        """Query product data by ASIN(s) or product codes.

        Args:
            asins: List of ASINs/UPCs/EANs (max 100 per batch).
            domain: Keepa domain code (US, GB, DE, etc.).
            include_offers: Include marketplace offers (+tokens). Enables offer extraction.
            include_buybox: Include buy box data (+2 tokens/product).
            include_rating: Include rating/review history (free).
            include_stock: Include stock levels for offers (requires include_offers).
            include_videos: Include video metadata (free).
            include_aplus: Include A+ content (free).
            stats_days: Stats period in days (free).
            history_days: Limit history to last N days (None=all).
            update: Force data refresh if older than X hours. 0=live (+1 token).
            only_live_offers: Only include live offers (reduces response size).
            product_code_is_asin: True for ASIN, False for UPC/EAN/ISBN-13.
            extra_params: Additional API parameters for future features.

        Returns:
            List of product dicts with our normalized format.
        """
        api = await self._ensure_api()
        self._metrics.total_requests += 1

        # Validate domain
        if domain not in KEEPA_SUPPORTED_DOMAINS:
            logger.warning("Domain %s not supported by Keepa, falling back to US", domain)
            domain = "US"

        try:
            raw_products = await api.query(
                items=asins,
                domain=domain,
                history=True,
                stats=stats_days,
                offers=20 if include_offers else None,
                buybox=include_buybox,
                rating=include_rating,
                stock=include_stock,
                days=history_days,
                update=update,
                only_live_offers=only_live_offers,
                videos=include_videos,
                aplus=include_aplus,
                product_code_is_asin=product_code_is_asin,
                to_datetime=True,
                out_of_stock_as_nan=True,
                progress_bar=False,
                wait=True,
                extra_params=extra_params or {},
            )

            self._metrics.successful_requests += 1
            currency = DOMAIN_CURRENCY.get(domain, "USD")

            # Transform Keepa's format to our platform's normalized format
            products = []
            for raw in raw_products:
                product = self._transform_product(raw, currency, domain, include_offers)
                if product:
                    products.append(product)

            logger.info(
                "Keepa query returned %d products for %d ASINs (domain=%s)",
                len(products), len(asins), domain,
            )
            return products

        except Exception as e:
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            error_str = str(e)

            # Distinguish transient vs permanent errors for upstream retry decisions
            if "NOT_ENOUGH_TOKEN" in error_str or "429" in error_str:
                logger.warning("Keepa rate limited (tokens exhausted): %s", e)
            elif "PAYMENT_REQUIRED" in error_str or "402" in error_str:
                logger.error("Keepa payment required — check subscription: %s", e)
            elif "REQUEST_REJECTED" in error_str or "400" in error_str:
                logger.error("Keepa rejected request (bad params): %s", e)
            else:
                logger.warning("Keepa query failed (may be transient): %s", e)

            return []

    def _transform_product(self, raw: dict, currency: str, domain: str, include_offers: bool = False) -> Optional[dict]:
        """Transform a Keepa product dict into our platform's normalized format."""
        if not raw or not raw.get("title"):
            return None

        product: dict[str, Any] = {
            "name": raw.get("title", ""),
            "asin": raw.get("asin", ""),
            "brand": raw.get("brand", ""),
            "manufacturer": raw.get("manufacturer", ""),
            "currency": currency,
            "source": "keepa_api",
        }

        # Product URL — use primary TLD for each Keepa domain code
        DOMAIN_TO_PRIMARY_TLD = {
            "US": "amazon.com", "GB": "amazon.co.uk", "DE": "amazon.de",
            "FR": "amazon.fr", "JP": "amazon.co.jp", "CA": "amazon.ca",
            "IT": "amazon.it", "ES": "amazon.es", "IN": "amazon.in",
            "MX": "amazon.com.mx", "BR": "amazon.com.br",
        }
        domain_tld = DOMAIN_TO_PRIMARY_TLD.get(domain, "amazon.com")
        product["product_url"] = f"https://www.{domain_tld}/dp/{raw.get('asin', '')}"

        # Images
        images_csv = raw.get("imagesCSV", "")
        if images_csv:
            first_image = images_csv.split(",")[0].strip()
            if first_image:
                product["image_url"] = f"https://images-na.ssl-images-amazon.com/images/I/{first_image}"

        # Current prices from data tracks
        # Priority: BUY_BOX (what customer actually pays) → NEW (lowest 3P) → AMAZON (Amazon's price)
        data = raw.get("data", {})
        price = self._get_current_price(data, "BUY_BOX_SHIPPING")
        if not price:
            price = self._get_current_price(data, "NEW")
        if not price:
            price = self._get_current_price(data, "AMAZON")
        if not price:
            price = self._get_current_price(data, "NEW_FBA")
        if price and price > 0:
            product["price"] = f"{price / 100:.2f}"  # Keepa stores prices in cents

        # Amazon's own price (may differ from buy box / lowest new)
        amazon_price = self._get_current_price(data, "AMAZON")
        if amazon_price and amazon_price > 0:
            product["amazon_price"] = f"{amazon_price / 100:.2f}"

        # Original/list price
        list_price = self._get_current_price(data, "LISTPRICE")
        if list_price and list_price > 0:
            product["original_price"] = f"{list_price / 100:.2f}"

        # Additional price tracks (used, refurbished, warehouse)
        for track, field in [
            ("USED", "used_price"),
            ("REFURBISHED", "refurbished_price"),
            ("WAREHOUSE", "warehouse_price"),
            ("NEW_FBA", "fba_price"),
            ("NEW_FBM_SHIPPING", "fbm_price"),
            ("COLLECTIBLE", "collectible_price"),
        ]:
            track_price = self._get_current_price(data, track)
            if track_price and track_price > 0:
                product[field] = f"{track_price / 100:.2f}"

        # Rating (Keepa stores 0-50, we use 0-5)
        rating = self._get_current_value(data, "RATING")
        if rating and rating > 0:
            product["rating"] = f"{rating / 10:.1f}"

        # Review count
        reviews = self._get_current_value(data, "COUNT_REVIEWS")
        if reviews and reviews > 0:
            product["reviews_count"] = str(int(reviews))

        # Sales rank
        sales_rank = self._get_current_value(data, "SALES")
        if sales_rank and sales_rank > 0:
            product["sales_rank"] = int(sales_rank)

        # Stats (if available)
        stats = raw.get("stats_parsed") or raw.get("stats")
        if stats:
            product["stats"] = self._extract_stats(stats)

        # Offer counts
        new_count = self._get_current_value(data, "COUNT_NEW")
        if new_count is not None:
            product["offer_count_new"] = int(new_count)
        used_count = self._get_current_value(data, "COUNT_USED")
        if used_count is not None:
            product["offer_count_used"] = int(used_count)

        # Availability
        avail = raw.get("availabilityAmazon")
        if avail is not None:
            product["stock_status"] = "InStock" if avail == 0 else "OutOfStock"

        # Categories
        category_tree = raw.get("categoryTree")
        if category_tree:
            product["category"] = " > ".join(
                c.get("name", "") for c in category_tree if isinstance(c, dict)
            )

        # Additional metadata
        product["sku"] = raw.get("asin", "")
        if raw.get("parentAsin"):
            product["parent_asin"] = raw["parentAsin"]
        if raw.get("variationCSV"):
            product["has_variants"] = True
        if raw.get("fbaFees"):
            product["fba_fees"] = raw["fbaFees"]
        if raw.get("monthlySold"):
            product["monthly_sold"] = raw["monthlySold"]

        # Description and features
        if raw.get("description"):
            product["description"] = raw["description"]
        if raw.get("features"):
            product["features"] = raw["features"]

        # Physical dimensions
        for dim_key in ["itemWeight", "itemHeight", "itemLength", "itemWidth",
                        "packageWeight", "packageHeight", "packageLength", "packageWidth"]:
            if raw.get(dim_key):
                product[dim_key] = raw[dim_key]

        # Offer data (when include_offers=True)
        if include_offers and raw.get("offers"):
            product["offers"] = self._extract_offers(raw["offers"], raw.get("liveOffersOrder"))
        if raw.get("buyBoxSellerIdHistory"):
            product["buybox_seller_history"] = True

        # Price history summary (last 30/90/180 day trends)
        product["price_history"] = self._build_price_summary(data)

        return product

    def _get_current_price(self, data: dict, key: str) -> Optional[float]:
        """Get the most recent non-NaN price from a data track."""
        prices = data.get(key)
        if prices is None:
            return None
        try:
            import numpy as np
            # Find last valid (non-NaN) price
            for i in range(len(prices) - 1, -1, -1):
                if not np.isnan(prices[i]) and prices[i] > 0:
                    return float(prices[i])
        except Exception:
            pass
        return None

    def _get_current_value(self, data: dict, key: str) -> Optional[float]:
        """Get the most recent value from a data track."""
        values = data.get(key)
        if values is None:
            return None
        try:
            import numpy as np
            for i in range(len(values) - 1, -1, -1):
                if not np.isnan(values[i]):
                    return float(values[i])
        except Exception:
            pass
        return None

    def _extract_stats(self, stats: dict) -> dict:
        """Extract useful stats summary."""
        summary = {}
        for key in ["current", "avg30", "avg90", "avg180", "min", "max"]:
            if key in stats:
                val = stats[key]
                if isinstance(val, list) and len(val) > 0:
                    # Index 0 = AMAZON price
                    amazon_val = val[0] if val[0] and val[0] > 0 else None
                    if amazon_val:
                        summary[f"{key}_amazon"] = f"{amazon_val / 100:.2f}"
                    # Index 18 = BUY_BOX_SHIPPING
                    if len(val) > 18:
                        bb_val = val[18] if val[18] and val[18] > 0 else None
                        if bb_val:
                            summary[f"{key}_buybox"] = f"{bb_val / 100:.2f}"
        return summary

    def _build_price_summary(self, data: dict) -> dict:
        """Build a human-readable price history summary across all tracks."""
        summary = {}
        for track in ["AMAZON", "NEW", "BUY_BOX_SHIPPING", "USED", "NEW_FBA",
                       "WAREHOUSE", "REFURBISHED", "COLLECTIBLE"]:
            prices = data.get(track)
            if prices is not None:
                try:
                    import numpy as np
                    valid = prices[~np.isnan(prices)]
                    if len(valid) > 0:
                        summary[track.lower()] = {
                            "current": f"{valid[-1] / 100:.2f}" if valid[-1] > 0 else None,
                            "min": f"{np.min(valid[valid > 0]) / 100:.2f}" if np.any(valid > 0) else None,
                            "max": f"{np.max(valid) / 100:.2f}" if len(valid) > 0 else None,
                        }
                except Exception:
                    pass
        return summary

    def _extract_offers(self, offers: list, live_order: Optional[list] = None) -> list[dict]:
        """Extract marketplace offer details from Keepa offer data."""
        result = []
        live_indices = set(live_order) if live_order else set()

        for i, offer in enumerate(offers):
            if not isinstance(offer, dict):
                continue
            o: dict[str, Any] = {
                "seller_id": offer.get("sellerId", ""),
                "condition": offer.get("condition", ""),
                "is_fba": offer.get("isFulfilledByAmazon", False),
                "is_prime": offer.get("isPrimeEligible", False),
                "is_live": i in live_indices,
            }
            # Current price
            price_ship = offer.get("priceShippingIfApplicable")
            if price_ship and price_ship > 0:
                o["price"] = f"{price_ship / 100:.2f}"
            # Stock
            stock = offer.get("stockLevel")
            if stock is not None:
                o["stock"] = stock
            result.append(o)

        return result

    # ---- Category Lookup --------------------------------------------------

    async def category_lookup(
        self,
        category_id: int = 0,
        domain: str = "US",
        include_parents: bool = False,
    ) -> dict:
        """Look up Amazon category tree by ID.

        Args:
            category_id: Category node ID. Use 0 for all root categories.
            domain: Keepa domain code.
            include_parents: Include parent categories in response.

        Returns:
            Dict of category objects keyed by category ID.
        """
        api = await self._ensure_api()
        try:
            return await api.category_lookup(
                category_id=category_id,
                domain=domain,
                include_parents=int(include_parents),
                wait=True,
            )
        except Exception as e:
            logger.warning("Keepa category_lookup failed: %s", e)
            return {}

    # ---- Product Search ---------------------------------------------------

    async def search_products(
        self,
        domain: str = "US",
        n_products: int = 50,
        **search_params: Any,
    ) -> list[str]:
        """Search for products by attributes using Keepa's product finder.

        Args:
            domain: Keepa domain code.
            n_products: Max number of ASINs to return.
            **search_params: Search filters. Common ones:
                title: str - Product title keyword
                brand: str - Brand name
                manufacturer: str - Manufacturer
                author: str - Author (books)
                rootCategory: int - Category ID
                current_AMAZON_gte: int - Min Amazon price (cents)
                current_AMAZON_lte: int - Max Amazon price (cents)
                salesRankRange: list[int] - [min, max] sales rank
                minRating: int - Min rating (0-50 scale, e.g. 40 = 4.0 stars)
                hasReviews: bool - Must have reviews

        Returns:
            List of ASINs matching the search criteria.
        """
        api = await self._ensure_api()
        self._metrics.total_requests += 1

        try:
            asins = await api.product_finder(
                product_parms=search_params,
                domain=domain,
                n_products=n_products,
                wait=True,
            )
            self._metrics.successful_requests += 1
            logger.info("Keepa product_finder returned %d ASINs", len(asins))
            return asins
        except Exception as e:
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            logger.warning("Keepa product_finder failed: %s", e)
            return []

    # ---- Deals ------------------------------------------------------------

    async def find_deals(
        self,
        domain: str = "US",
        min_discount_percent: int = 20,
        price_range: Optional[tuple[int, int]] = None,
        sales_rank_range: Optional[tuple[int, int]] = None,
        categories: Optional[list[int]] = None,
        min_rating: int = 0,
    ) -> list[dict]:
        """Find current Amazon deals (price drops).

        Args:
            domain: Keepa domain code.
            min_discount_percent: Minimum discount percentage (e.g. 20 = 20% off).
            price_range: (min_cents, max_cents) current price range.
            sales_rank_range: (min, max) sales rank filter.
            categories: List of category IDs to include.
            min_rating: Minimum rating (0-50 scale).

        Returns:
            List of deal product dicts.
        """
        api = await self._ensure_api()
        self._metrics.total_requests += 1

        deal_params: dict[str, Any] = {
            "priceTypes": [0],  # 0 = Amazon price
            "deltaPercentRange": [min_discount_percent, 100],
            "hasReviews": True,
        }
        if price_range:
            deal_params["currentRange"] = list(price_range)
        if sales_rank_range:
            deal_params["salesRankRange"] = list(sales_rank_range)
        if categories:
            deal_params["includeCategories"] = categories
        if min_rating > 0:
            deal_params["minRating"] = min_rating

        try:
            deals = await api.deals(deal_params, domain=domain, wait=True)
            self._metrics.successful_requests += 1
            logger.info("Keepa deals returned %d results", len(deals))
            return deals
        except Exception as e:
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            logger.warning("Keepa deals failed: %s", e)
            return []

    # ---- Best Sellers -----------------------------------------------------

    async def best_sellers(
        self,
        category: str,
        domain: str = "US",
    ) -> list[str]:
        """Get best seller ASINs for a category."""
        api = await self._ensure_api()
        self._metrics.total_requests += 1

        try:
            asins = await api.best_sellers_query(category=category, domain=domain, wait=True)
            self._metrics.successful_requests += 1
            return asins
        except Exception as e:
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            logger.warning("Keepa best_sellers failed: %s", e)
            return []

    # ---- Categories -------------------------------------------------------

    async def search_categories(self, term: str, domain: str = "US") -> dict:
        """Search Amazon category tree by keyword."""
        api = await self._ensure_api()
        try:
            return await api.search_for_categories(term, domain=domain, wait=True)
        except Exception as e:
            logger.warning("Keepa category search failed: %s", e)
            return {}

    # ---- Seller Info ------------------------------------------------------

    async def seller_info(
        self,
        seller_ids: list[str],
        domain: str = "US",
    ) -> list[dict]:
        """Get seller information."""
        api = await self._ensure_api()
        self._metrics.total_requests += 1

        try:
            sellers = await api.seller_query(seller_ids, domain=domain, wait=True)
            self._metrics.successful_requests += 1
            return sellers
        except Exception as e:
            self._metrics.failed_requests += 1
            logger.warning("Keepa seller query failed: %s", e)
            return []

    # ---- Connector Protocol -----------------------------------------------

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """Implement Connector protocol — handle ALL Amazon URLs via Keepa API.

        Automatically detects URL type and routes to the right Keepa method:
        - /dp/ASIN → query_products (single product lookup)
        - /s?k=keyword → search_products (product finder by title)
        - /gp/bestsellers/ → best_sellers (by category)
        - /events/deals → find_deals
        - Other → search_products with title extracted from URL

        Returns product data as JSON in the response body.
        Falls back with status 404 if no data found (triggers browser fallback).
        """
        import json
        from urllib.parse import urlparse, parse_qs

        url = request.url
        domain = detect_amazon_domain(url)
        parsed = urlparse(url)
        path = parsed.path.lower()
        query_params = parse_qs(parsed.query)

        products: list[dict] = []

        # Route 1: Product detail page (/dp/ASIN, /gp/product/ASIN)
        asin = extract_asin(url)
        if asin:
            # Check Google Sheets cache first (if configured)
            if self._sheets_cache:
                products = await self._sheets_cache.get_products(
                    asins=[asin], domain=domain, include_rating=True, stats_days=90,
                )
            else:
                products = await self.query_products(
                    asins=[asin],
                    domain=domain,
                    include_rating=True,
                    stats_days=90,
                )

        # Route 2: Search page (/s?k=keyword)
        elif "/s" in path and ("k" in query_params or "field-keywords" in query_params):
            keyword = (query_params.get("k") or query_params.get("field-keywords", [""]))[0]
            if keyword:
                asins = await self.search_products(
                    domain=domain,
                    n_products=20,
                    title=keyword,
                )
                if asins:
                    if self._sheets_cache:
                        products = await self._sheets_cache.get_products(
                            asins=asins[:20], domain=domain,
                            include_rating=True, stats_days=30, history_days=7,
                        )
                    else:
                        products = await self.query_products(
                            asins=asins[:20], domain=domain,
                            include_rating=True, stats_days=30, history_days=7,
                        )

        # Route 3: Best sellers (/gp/bestsellers/, /Best-Sellers)
        elif "bestseller" in path or "best-seller" in path:
            # Try to extract category from URL path
            # e.g., /gp/bestsellers/electronics/
            parts = [p for p in path.split("/") if p and p not in ("gp", "bestsellers", "best-sellers")]
            if parts:
                # Search for the category to get its ID
                categories = await self.search_categories(parts[0], domain=domain)
                if categories:
                    cat_id = list(categories.keys())[0]
                    asins = await self.best_sellers(category=cat_id, domain=domain)
                    if asins:
                        products = await self.query_products(
                            asins=asins[:20],
                            domain=domain,
                            include_rating=True,
                            stats_days=30,
                        )

        # Route 4: Deals (/events/deals, /deal, /gp/goldbox)
        elif any(d in path for d in ("deal", "goldbox", "events")):
            deals = await self.find_deals(domain=domain, min_discount_percent=10)
            if deals:
                # Deals return product objects directly
                products = deals[:20] if isinstance(deals, list) else []

        # No data found — return 404 so the router falls back to browser
        if not products:
            return FetchResponse(
                url=url,
                status_code=404,
                error=f"No Keepa data for URL: {url}",
            )

        # Return product data as JSON response
        json_body = json.dumps(products, default=str)
        return FetchResponse(
            url=url,
            status_code=200,
            text=json_body,
            html=json_body,
            body=json_body.encode("utf-8"),
        )

    async def health_check(self) -> bool:
        """Check if Keepa API is accessible."""
        try:
            api = await self._ensure_api()
            await api.update_status()
            return api.tokens_left > 0
        except Exception:
            return False

    def get_metrics(self) -> ConnectorMetrics:
        return self._metrics

    @property
    def tokens_left(self) -> int:
        """Current token balance."""
        if self._api:
            return self._api.tokens_left
        return 0

    async def close(self) -> None:
        """Clean up resources."""
        self._api = None
