"""
Template registry — built-in scraping templates for common e-commerce use cases.

Inspired by popular scraping platforms (Apify, ScrapingBee, etc.), these templates
provide pre-configured extraction rules, field definitions, and execution policies
for the most common scraping scenarios.
"""

from __future__ import annotations

from packages.contracts.template import (
    FieldDefinition,
    Template,
    TemplateCategory,
    TemplateConfig,
)


# ---------------------------------------------------------------------------
# Helper to reduce boilerplate
# ---------------------------------------------------------------------------

def _field(name: str, description: str, *, css: str | None = None,
           xpath: str | None = None, json_path: str | None = None,
           ai_hint: str | None = None, field_type: str = "text",
           required: bool = False) -> FieldDefinition:
    return FieldDefinition(
        name=name, description=description, css_selector=css,
        xpath_selector=xpath, json_path=json_path, ai_hint=ai_hint,
        field_type=field_type, required=required,
    )


# ---------------------------------------------------------------------------
# 1. Amazon Product Scraper
# ---------------------------------------------------------------------------
AMAZON_PRODUCT = Template(
    id="amazon-product",
    name="Amazon Product Scraper",
    description=(
        "Extract product data from Amazon — titles, prices, ratings, reviews, "
        "ASINs, images, Prime eligibility, seller info. Supports 10+ Amazon marketplaces."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["amazon", "product", "pricing", "asin", "prime"],
    icon="🛒",
    platform="Amazon",
    config=TemplateConfig(
        target_domains=["amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
                        "amazon.it", "amazon.es", "amazon.ca", "amazon.co.jp",
                        "amazon.in", "amazon.com.au"],
        example_urls=[
            "https://www.amazon.com/dp/B0BSHF7WHW",
            "https://www.amazon.com/s?k=wireless+headphones",
        ],
        fields=[
            _field("title", "Product title", css="#productTitle", required=True),
            _field("price", "Current price", css=".a-price .a-offscreen", field_type="number", required=True),
            _field("original_price", "Original/list price", css=".a-text-price .a-offscreen", field_type="number"),
            _field("rating", "Star rating (0-5)", css="#acrPopover span.a-size-base", field_type="number"),
            _field("review_count", "Number of reviews", css="#acrCustomerReviewText", field_type="number"),
            _field("asin", "Amazon Standard Identification Number", ai_hint="Extract ASIN from URL or page"),
            _field("image_url", "Main product image", css="#landingImage", field_type="image"),
            _field("brand", "Product brand", css="#bylineInfo"),
            _field("availability", "Stock status", css="#availability span"),
            _field("prime", "Prime eligible", ai_hint="Check if Prime badge is present", field_type="text"),
            _field("seller", "Seller name", css="#merchant-info"),
            _field("category", "Product category breadcrumb", css="#wayfinding-breadcrumbs_container"),
            _field("description", "Product description", css="#productDescription"),
            _field("features", "Bullet point features", css="#feature-bullets li", field_type="list"),
        ],
        preferred_lane="browser",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        proxy_type="residential",
        rate_limit_rpm=20,
        timeout_ms=45000,
    ),
)


# ---------------------------------------------------------------------------
# 2. Amazon Reviews Scraper
# ---------------------------------------------------------------------------
AMAZON_REVIEWS = Template(
    id="amazon-reviews",
    name="Amazon Reviews Scraper",
    description=(
        "Extract customer reviews from Amazon products — full text, star ratings, "
        "dates, verified purchase flags, helpfulness votes. Ideal for sentiment analysis."
    ),
    category=TemplateCategory.REVIEWS,
    tags=["amazon", "reviews", "sentiment", "ratings"],
    icon="⭐",
    platform="Amazon",
    config=TemplateConfig(
        target_domains=["amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
                        "amazon.it", "amazon.es", "amazon.ca"],
        example_urls=[
            "https://www.amazon.com/product-reviews/B0BSHF7WHW",
        ],
        fields=[
            _field("review_title", "Review headline", css="[data-hook='review-title'] span", required=True),
            _field("review_text", "Full review body", css="[data-hook='review-body'] span", required=True),
            _field("star_rating", "Star rating (1-5)", css="[data-hook='review-star-rating'] span", field_type="number"),
            _field("review_date", "Date of review", css="[data-hook='review-date']"),
            _field("verified_purchase", "Verified purchase badge", css="[data-hook='avp-badge']"),
            _field("helpful_votes", "Helpfulness vote count", css="[data-hook='helpful-vote-statement']", field_type="number"),
            _field("reviewer_name", "Reviewer name", css=".a-profile-name"),
            _field("reviewer_profile", "Link to reviewer profile", css=".a-profile", field_type="url"),
        ],
        preferred_lane="browser",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        proxy_type="residential",
        rate_limit_rpm=15,
        timeout_ms=45000,
        pagination={"type": "next_button", "selector": "li.a-last a"},
    ),
)


# ---------------------------------------------------------------------------
# 3. Amazon Bestsellers Scraper
# ---------------------------------------------------------------------------
AMAZON_BESTSELLERS = Template(
    id="amazon-bestsellers",
    name="Amazon Bestsellers Scraper",
    description=(
        "Track Amazon Best Sellers rankings across any category. Extract BSR rank, "
        "ASIN, price, review count, and listing URL."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["amazon", "bestsellers", "ranking", "bsr"],
    icon="🏆",
    platform="Amazon",
    config=TemplateConfig(
        target_domains=["amazon.com"],
        example_urls=[
            "https://www.amazon.com/Best-Sellers/zgbs",
            "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics",
        ],
        fields=[
            _field("rank", "Best Seller rank position", css=".zg-bdg-text", field_type="number", required=True),
            _field("title", "Product title", css=".p13n-sc-truncate-desktop-type2", required=True),
            _field("price", "Current price", css=".a-price .a-offscreen", field_type="number"),
            _field("rating", "Star rating", field_type="number"),
            _field("review_count", "Number of reviews", field_type="number"),
            _field("asin", "ASIN identifier", ai_hint="Extract from product link"),
            _field("product_url", "Product page URL", field_type="url"),
            _field("image_url", "Product thumbnail", field_type="image"),
        ],
        preferred_lane="browser",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        proxy_type="residential",
        rate_limit_rpm=15,
        timeout_ms=45000,
        pagination={"type": "next_button", "selector": "ul.a-pagination li.a-last a"},
    ),
)


# ---------------------------------------------------------------------------
# 4. Shopify Store Scraper
# ---------------------------------------------------------------------------
SHOPIFY_STORE = Template(
    id="shopify-store",
    name="Shopify Store Scraper",
    description=(
        "Extract entire product catalogs from any Shopify-powered store. Uses "
        "Shopify's internal /products.json endpoint for fast, lightweight extraction."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["shopify", "product", "catalog", "dtc", "variants"],
    icon="🏪",
    platform="Shopify",
    config=TemplateConfig(
        target_domains=["*.myshopify.com"],
        example_urls=[
            "https://store.example.com/products.json",
            "https://store.example.com/collections/all",
        ],
        fields=[
            _field("title", "Product title", json_path="$.title", required=True),
            _field("handle", "URL slug", json_path="$.handle"),
            _field("vendor", "Brand / vendor", json_path="$.vendor"),
            _field("product_type", "Product type", json_path="$.product_type"),
            _field("price", "Price (lowest variant)", json_path="$.variants[0].price", field_type="number", required=True),
            _field("compare_at_price", "Original / compare price", json_path="$.variants[0].compare_at_price", field_type="number"),
            _field("sku", "SKU", json_path="$.variants[0].sku"),
            _field("available", "In stock", json_path="$.variants[0].available"),
            _field("description", "Product description (HTML)", json_path="$.body_html", field_type="html"),
            _field("image_url", "Main image", json_path="$.images[0].src", field_type="image"),
            _field("tags", "Product tags", json_path="$.tags", field_type="list"),
            _field("variants", "All variants with prices/SKUs", json_path="$.variants", field_type="json"),
            _field("created_at", "Date added", json_path="$.created_at"),
        ],
        preferred_lane="api",
        extraction_type="auto",
        browser_required=False,
        rate_limit_rpm=60,
        timeout_ms=15000,
        pagination={"type": "page_param", "param": "page", "start": 1, "items_per_page": 30},
    ),
)


# ---------------------------------------------------------------------------
# 5. eBay Items Scraper
# ---------------------------------------------------------------------------
EBAY_ITEMS = Template(
    id="ebay-items",
    name="eBay Items Scraper",
    description=(
        "Extract eBay listings — prices, seller reputation, auction vs buy-it-now, "
        "shipping costs, item condition. Supports search results and category pages."
    ),
    category=TemplateCategory.MARKETPLACE,
    tags=["ebay", "auction", "marketplace", "listings"],
    icon="🔨",
    platform="eBay",
    config=TemplateConfig(
        target_domains=["ebay.com", "ebay.co.uk", "ebay.de", "ebay.fr", "ebay.com.au"],
        example_urls=[
            "https://www.ebay.com/sch/i.html?_nkw=vintage+watches",
            "https://www.ebay.com/itm/123456789",
        ],
        fields=[
            _field("title", "Item title", css=".s-item__title", required=True),
            _field("price", "Current/buy-it-now price", css=".s-item__price", field_type="number", required=True),
            _field("shipping_cost", "Shipping price", css=".s-item__shipping", field_type="number"),
            _field("condition", "Item condition (new/used/refurbished)", css=".SECONDARY_INFO"),
            _field("listing_type", "Auction or Buy It Now", ai_hint="Check for bid count vs buy-it-now"),
            _field("bid_count", "Number of bids (auctions)", css=".s-item__bidCount", field_type="number"),
            _field("time_left", "Time remaining (auctions)", css=".s-item__time-left"),
            _field("seller_name", "Seller username", css=".s-item__seller-info-text"),
            _field("seller_rating", "Seller feedback percentage", field_type="number"),
            _field("item_url", "Listing URL", css=".s-item__link", field_type="url"),
            _field("image_url", "Item image", css=".s-item__image-img", field_type="image"),
            _field("location", "Item location", css=".s-item__location"),
            _field("sold_count", "Number sold", css=".s-item__quantitySold", field_type="number"),
        ],
        preferred_lane="http",
        browser_required=False,
        rate_limit_rpm=30,
        timeout_ms=30000,
        pagination={"type": "next_button", "selector": "a.pagination__next"},
    ),
)


# ---------------------------------------------------------------------------
# 6. Walmart Product Scraper
# ---------------------------------------------------------------------------
WALMART_PRODUCT = Template(
    id="walmart-product",
    name="Walmart Product Scraper",
    description=(
        "Scrape Walmart product data — prices, reviews, stock availability, "
        "pickup/delivery options, seller info, and product specifications."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["walmart", "product", "pricing", "grocery", "retail"],
    icon="🏬",
    platform="Walmart",
    config=TemplateConfig(
        target_domains=["walmart.com"],
        example_urls=[
            "https://www.walmart.com/ip/product-name/123456789",
            "https://www.walmart.com/search?q=laptop",
        ],
        fields=[
            _field("title", "Product name", required=True),
            _field("price", "Current price", field_type="number", required=True),
            _field("was_price", "Previous/strikethrough price", field_type="number"),
            _field("rating", "Average star rating", field_type="number"),
            _field("review_count", "Number of reviews", field_type="number"),
            _field("availability", "In stock / out of stock"),
            _field("pickup_available", "Available for store pickup"),
            _field("delivery_available", "Available for delivery"),
            _field("seller", "Sold by (marketplace seller or Walmart)"),
            _field("brand", "Product brand"),
            _field("category", "Product category breadcrumb"),
            _field("image_url", "Main product image", field_type="image"),
            _field("product_url", "Product page URL", field_type="url"),
            _field("specifications", "Product specs key-value pairs", field_type="json"),
        ],
        preferred_lane="browser",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        proxy_type="residential",
        rate_limit_rpm=15,
        timeout_ms=45000,
    ),
)


# ---------------------------------------------------------------------------
# 7. Etsy Listings Scraper
# ---------------------------------------------------------------------------
ETSY_LISTINGS = Template(
    id="etsy-listings",
    name="Etsy Listings Scraper",
    description=(
        "Extract Etsy marketplace listings — handmade items, vintage goods, "
        "pricing, shop metadata, reviews. Great for niche market research."
    ),
    category=TemplateCategory.MARKETPLACE,
    tags=["etsy", "handmade", "vintage", "marketplace", "crafts"],
    icon="🎨",
    platform="Etsy",
    config=TemplateConfig(
        target_domains=["etsy.com"],
        example_urls=[
            "https://www.etsy.com/search?q=handmade+jewelry",
            "https://www.etsy.com/listing/123456789",
        ],
        fields=[
            _field("title", "Listing title", required=True),
            _field("price", "Item price", field_type="number", required=True),
            _field("currency", "Price currency (USD, EUR, etc.)"),
            _field("shop_name", "Seller shop name"),
            _field("shop_rating", "Shop star rating", field_type="number"),
            _field("shop_sales", "Total shop sales count", field_type="number"),
            _field("item_reviews", "Number of item reviews", field_type="number"),
            _field("shipping", "Shipping info (free / cost)"),
            _field("image_url", "Main listing image", field_type="image"),
            _field("listing_url", "Listing page URL", field_type="url"),
            _field("tags", "Item tags", field_type="list"),
            _field("materials", "Materials used", field_type="list"),
            _field("favorited_count", "Number of favorites", field_type="number"),
        ],
        preferred_lane="browser",
        browser_required=True,
        proxy_required=True,
        rate_limit_rpm=20,
        timeout_ms=30000,
        pagination={"type": "next_button", "selector": "a[data-page-next]"},
    ),
)


# ---------------------------------------------------------------------------
# 8. Target Product Scraper
# ---------------------------------------------------------------------------
TARGET_PRODUCT = Template(
    id="target-product",
    name="Target Product Scraper",
    description=(
        "Extract product data from Target.com — prices, availability, "
        "same-day delivery options, store pickup, and Circle offers."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["target", "retail", "pricing", "grocery"],
    icon="🎯",
    platform="Target",
    config=TemplateConfig(
        target_domains=["target.com"],
        example_urls=[
            "https://www.target.com/p/product-name/-/A-12345678",
            "https://www.target.com/s?searchTerm=headphones",
        ],
        fields=[
            _field("title", "Product name", required=True),
            _field("price", "Current price", field_type="number", required=True),
            _field("regular_price", "Regular price", field_type="number"),
            _field("rating", "Average rating", field_type="number"),
            _field("review_count", "Number of reviews", field_type="number"),
            _field("availability", "Stock status"),
            _field("delivery_options", "Shipping/pickup/same-day options", field_type="list"),
            _field("brand", "Product brand"),
            _field("tcin", "Target item ID (TCIN)"),
            _field("image_url", "Main product image", field_type="image"),
            _field("description", "Product description"),
        ],
        preferred_lane="browser",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        proxy_type="residential",
        rate_limit_rpm=15,
        timeout_ms=45000,
    ),
)


# ---------------------------------------------------------------------------
# 9. Best Buy Product Scraper
# ---------------------------------------------------------------------------
BESTBUY_PRODUCT = Template(
    id="bestbuy-product",
    name="Best Buy Product Scraper",
    description=(
        "Extract electronics and tech products from Best Buy — prices, specs, "
        "open-box deals, availability, and customer reviews."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["bestbuy", "electronics", "tech", "pricing"],
    icon="💻",
    platform="Best Buy",
    config=TemplateConfig(
        target_domains=["bestbuy.com"],
        example_urls=[
            "https://www.bestbuy.com/site/product/12345678.p",
            "https://www.bestbuy.com/site/searchpage.jsp?st=laptop",
        ],
        fields=[
            _field("title", "Product name", required=True),
            _field("price", "Current price", field_type="number", required=True),
            _field("was_price", "Original price", field_type="number"),
            _field("savings", "Discount amount", field_type="number"),
            _field("rating", "Star rating", field_type="number"),
            _field("review_count", "Number of reviews", field_type="number"),
            _field("sku", "Best Buy SKU"),
            _field("model_number", "Manufacturer model number"),
            _field("availability", "In stock / sold out"),
            _field("open_box_price", "Open-box deal price", field_type="number"),
            _field("brand", "Brand name"),
            _field("specifications", "Technical specifications", field_type="json"),
            _field("image_url", "Product image", field_type="image"),
        ],
        preferred_lane="browser",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        rate_limit_rpm=20,
        timeout_ms=30000,
    ),
)


# ---------------------------------------------------------------------------
# 10. AliExpress Product Scraper
# ---------------------------------------------------------------------------
ALIEXPRESS_PRODUCT = Template(
    id="aliexpress-product",
    name="AliExpress Product Scraper",
    description=(
        "Scrape AliExpress for product data — prices, seller ratings, shipping "
        "estimates, order counts, and product variations."
    ),
    category=TemplateCategory.MARKETPLACE,
    tags=["aliexpress", "dropshipping", "wholesale", "china"],
    icon="📦",
    platform="AliExpress",
    config=TemplateConfig(
        target_domains=["aliexpress.com", "aliexpress.us"],
        example_urls=[
            "https://www.aliexpress.com/item/123456789.html",
            "https://www.aliexpress.com/wholesale?SearchText=bluetooth+earbuds",
        ],
        fields=[
            _field("title", "Product title", required=True),
            _field("price", "Current price (USD)", field_type="number", required=True),
            _field("original_price", "Original price", field_type="number"),
            _field("discount_percent", "Discount percentage", field_type="number"),
            _field("orders", "Number of orders", field_type="number"),
            _field("rating", "Star rating", field_type="number"),
            _field("review_count", "Number of reviews", field_type="number"),
            _field("seller_name", "Store name"),
            _field("seller_rating", "Store positive feedback %", field_type="number"),
            _field("shipping_cost", "Shipping estimate", field_type="number"),
            _field("shipping_time", "Estimated delivery days"),
            _field("variations", "Color/size/style options", field_type="json"),
            _field("image_url", "Main product image", field_type="image"),
        ],
        preferred_lane="browser",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        proxy_type="residential",
        rate_limit_rpm=15,
        timeout_ms=60000,
    ),
)


# ---------------------------------------------------------------------------
# 11. WooCommerce Store Scraper
# ---------------------------------------------------------------------------
WOOCOMMERCE_STORE = Template(
    id="woocommerce-store",
    name="WooCommerce Store Scraper",
    description=(
        "Extract products from WooCommerce-powered stores. Auto-detects WooCommerce "
        "REST API or falls back to HTML extraction with structured data."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["woocommerce", "wordpress", "product", "catalog"],
    icon="🔌",
    platform="WooCommerce",
    config=TemplateConfig(
        target_domains=[],  # any WooCommerce site
        example_urls=[
            "https://store.example.com/shop/",
            "https://store.example.com/wp-json/wc/v3/products",
        ],
        fields=[
            _field("title", "Product name", css=".woocommerce-loop-product__title", required=True),
            _field("price", "Current price", css=".price .woocommerce-Price-amount", field_type="number", required=True),
            _field("sale_price", "Sale price", css=".price ins .woocommerce-Price-amount", field_type="number"),
            _field("regular_price", "Regular price", css=".price del .woocommerce-Price-amount", field_type="number"),
            _field("sku", "Product SKU"),
            _field("categories", "Product categories", field_type="list"),
            _field("description", "Product description", css=".woocommerce-product-details__short-description"),
            _field("image_url", "Product image", css=".woocommerce-product-gallery__image img", field_type="image"),
            _field("in_stock", "Stock status"),
            _field("rating", "Average rating", field_type="number"),
        ],
        preferred_lane="http",
        extraction_type="css",
        browser_required=False,
        rate_limit_rpm=40,
        timeout_ms=20000,
        pagination={"type": "next_button", "selector": "a.next.page-numbers"},
    ),
)


# ---------------------------------------------------------------------------
# 12. Universal E-commerce Scraper (AI-powered)
# ---------------------------------------------------------------------------
UNIVERSAL_ECOMMERCE = Template(
    id="universal-ecommerce",
    name="Universal E-commerce Scraper",
    description=(
        "AI-powered universal product extractor that works on any e-commerce site. "
        "Auto-detects product data using JSON-LD, Open Graph, microdata, and AI fallback. "
        "Supports Amazon, eBay, Walmart, Shopify, WooCommerce, and hundreds more."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["universal", "ai", "any-site", "product", "auto-detect"],
    icon="🤖",
    platform="Any",
    config=TemplateConfig(
        target_domains=[],  # works on any domain
        example_urls=[
            "https://www.amazon.com/dp/B0BSHF7WHW",
            "https://www.walmart.com/ip/product/123456",
            "https://www.target.com/p/product/-/A-12345678",
        ],
        fields=[
            _field("title", "Product name", ai_hint="Main product title on the page", required=True),
            _field("price", "Current selling price", ai_hint="Primary price displayed", field_type="number", required=True),
            _field("original_price", "Original/compare price", ai_hint="Strikethrough or 'was' price", field_type="number"),
            _field("currency", "Price currency code", ai_hint="USD, EUR, GBP, etc."),
            _field("brand", "Product brand or manufacturer", ai_hint="Brand name from page or structured data"),
            _field("description", "Product description", ai_hint="Main product description text"),
            _field("rating", "Average customer rating", ai_hint="Star rating out of 5", field_type="number"),
            _field("review_count", "Number of customer reviews", field_type="number"),
            _field("availability", "Stock status", ai_hint="In stock, out of stock, limited"),
            _field("image_url", "Main product image URL", field_type="image"),
            _field("product_url", "Canonical product URL", field_type="url"),
            _field("sku", "Product SKU or identifier"),
            _field("category", "Product category"),
        ],
        preferred_lane="auto",
        extraction_type="ai",
        browser_required=False,
        rate_limit_rpm=30,
        timeout_ms=30000,
        extraction_rules={
            "strategy": "cascade",
            "steps": [
                {"method": "json_ld", "schema": "Product"},
                {"method": "open_graph"},
                {"method": "microdata", "itemtype": "Product"},
                {"method": "css_heuristics"},
                {"method": "ai_extraction"},
            ],
        },
    ),
)


# ---------------------------------------------------------------------------
# 13. Price Monitoring Template
# ---------------------------------------------------------------------------
PRICE_MONITOR = Template(
    id="price-monitor",
    name="Price Monitor",
    description=(
        "Track product prices across multiple e-commerce sites over time. "
        "Configured for scheduled re-scraping with change detection."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["pricing", "monitoring", "alerts", "competitive-intelligence"],
    icon="📊",
    platform="Any",
    config=TemplateConfig(
        target_domains=[],
        example_urls=[],
        fields=[
            _field("title", "Product name", required=True),
            _field("price", "Current price", field_type="number", required=True),
            _field("currency", "Currency code"),
            _field("availability", "In stock / out of stock"),
            _field("url", "Product page URL", field_type="url"),
            _field("timestamp", "Scrape timestamp"),
        ],
        preferred_lane="auto",
        extraction_type="ai",
        rate_limit_rpm=60,
        timeout_ms=20000,
        extraction_rules={
            "strategy": "cascade",
            "steps": [
                {"method": "json_ld", "schema": "Product"},
                {"method": "open_graph"},
                {"method": "ai_extraction"},
            ],
            "scheduling": {
                "recommended_interval": "6h",
                "change_detection": ["price", "availability"],
            },
        },
    ),
)


# ---------------------------------------------------------------------------
# 14. Alibaba Supplier Scraper
# ---------------------------------------------------------------------------
ALIBABA_SUPPLIER = Template(
    id="alibaba-supplier",
    name="Alibaba Supplier Scraper",
    description=(
        "Extract supplier and product data from Alibaba.com — MOQs, pricing tiers, "
        "supplier verification, trade assurance, and company profiles."
    ),
    category=TemplateCategory.MARKETPLACE,
    tags=["alibaba", "b2b", "wholesale", "suppliers", "moq"],
    icon="🏭",
    platform="Alibaba",
    config=TemplateConfig(
        target_domains=["alibaba.com"],
        example_urls=[
            "https://www.alibaba.com/trade/search?SearchText=bluetooth+speaker",
        ],
        fields=[
            _field("title", "Product name", required=True),
            _field("price_range", "Price range (min-max)", required=True),
            _field("moq", "Minimum order quantity", field_type="number"),
            _field("supplier_name", "Company name"),
            _field("supplier_years", "Years on Alibaba", field_type="number"),
            _field("verified", "Verified supplier badge"),
            _field("trade_assurance", "Trade Assurance enabled"),
            _field("response_rate", "Supplier response rate", field_type="number"),
            _field("location", "Supplier location (city, province)"),
            _field("image_url", "Product image", field_type="image"),
            _field("product_url", "Listing URL", field_type="url"),
        ],
        preferred_lane="browser",
        browser_required=True,
        proxy_required=True,
        rate_limit_rpm=15,
        timeout_ms=45000,
    ),
)


# ---------------------------------------------------------------------------
# 15. Costco Product Scraper
# ---------------------------------------------------------------------------
COSTCO_PRODUCT = Template(
    id="costco-product",
    name="Costco Product Scraper",
    description=(
        "Scrape Costco.com for bulk product pricing, member-only deals, "
        "warehouse availability, and product specifications."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["costco", "bulk", "wholesale", "pricing"],
    icon="🛍️",
    platform="Costco",
    config=TemplateConfig(
        target_domains=["costco.com"],
        example_urls=[
            "https://www.costco.com/electronics.html",
        ],
        fields=[
            _field("title", "Product name", required=True),
            _field("price", "Member price", field_type="number", required=True),
            _field("item_number", "Costco item number"),
            _field("brand", "Brand"),
            _field("rating", "Star rating", field_type="number"),
            _field("review_count", "Number of reviews", field_type="number"),
            _field("availability", "Online / warehouse availability"),
            _field("shipping_info", "Shipping and handling details"),
            _field("image_url", "Product image", field_type="image"),
        ],
        preferred_lane="browser",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        rate_limit_rpm=10,
        timeout_ms=45000,
    ),
)


# ---------------------------------------------------------------------------
# 16. Facebook Marketplace Scraper
# ---------------------------------------------------------------------------
FACEBOOK_MARKETPLACE = Template(
    id="facebook-marketplace",
    name="Facebook Marketplace Scraper",
    description=(
        "Extract listings from Facebook Marketplace — prices, seller details, "
        "item descriptions, photos, and location info."
    ),
    category=TemplateCategory.MARKETPLACE,
    tags=["facebook", "marketplace", "local", "classifieds"],
    icon="📘",
    platform="Facebook Marketplace",
    config=TemplateConfig(
        target_domains=["facebook.com"],
        example_urls=[
            "https://www.facebook.com/marketplace/category/electronics",
        ],
        fields=[
            _field("title", "Item title", required=True),
            _field("price", "Listing price", field_type="number", required=True),
            _field("description", "Item description"),
            _field("condition", "Item condition"),
            _field("location", "Seller location"),
            _field("seller_name", "Seller name"),
            _field("image_url", "Listing photo", field_type="image"),
            _field("listing_url", "Marketplace listing URL", field_type="url"),
            _field("posted_date", "Date posted"),
        ],
        preferred_lane="hard_target",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        proxy_type="residential",
        rate_limit_rpm=10,
        timeout_ms=60000,
    ),
)


# ---------------------------------------------------------------------------
# 17. Google Shopping Scraper
# ---------------------------------------------------------------------------
GOOGLE_SHOPPING = Template(
    id="google-shopping",
    name="Google Shopping Scraper",
    description=(
        "Extract product listings from Google Shopping — prices across retailers, "
        "ratings, shipping info, and merchant details."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["google", "shopping", "comparison", "pricing"],
    icon="🔍",
    platform="Google Shopping",
    config=TemplateConfig(
        target_domains=["google.com"],
        example_urls=[
            "https://www.google.com/search?tbm=shop&q=wireless+headphones",
        ],
        fields=[
            _field("title", "Product name", required=True),
            _field("price", "Listed price", field_type="number", required=True),
            _field("merchant", "Seller/store name"),
            _field("rating", "Product rating", field_type="number"),
            _field("review_count", "Number of reviews", field_type="number"),
            _field("shipping", "Shipping cost/info"),
            _field("image_url", "Product thumbnail", field_type="image"),
            _field("product_url", "Link to merchant page", field_type="url"),
            _field("condition", "New/refurbished/used"),
        ],
        preferred_lane="browser",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        proxy_type="residential",
        rate_limit_rpm=10,
        timeout_ms=30000,
    ),
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BUILT_IN_TEMPLATES: list[Template] = [
    AMAZON_PRODUCT,
    AMAZON_REVIEWS,
    AMAZON_BESTSELLERS,
    SHOPIFY_STORE,
    EBAY_ITEMS,
    WALMART_PRODUCT,
    ETSY_LISTINGS,
    TARGET_PRODUCT,
    BESTBUY_PRODUCT,
    ALIEXPRESS_PRODUCT,
    WOOCOMMERCE_STORE,
    UNIVERSAL_ECOMMERCE,
    PRICE_MONITOR,
    ALIBABA_SUPPLIER,
    COSTCO_PRODUCT,
    FACEBOOK_MARKETPLACE,
    GOOGLE_SHOPPING,
]

_TEMPLATE_INDEX: dict[str, Template] = {t.id: t for t in BUILT_IN_TEMPLATES}


def get_template(template_id: str) -> Template | None:
    """Look up a built-in template by ID."""
    return _TEMPLATE_INDEX.get(template_id)


def list_templates(
    category: str | None = None,
    platform: str | None = None,
    tag: str | None = None,
) -> list[Template]:
    """Return templates, optionally filtered by category, platform, or tag."""
    results = BUILT_IN_TEMPLATES
    if category:
        results = [t for t in results if t.category == category]
    if platform:
        platform_lower = platform.lower()
        results = [t for t in results if t.platform.lower() == platform_lower]
    if tag:
        tag_lower = tag.lower()
        results = [t for t in results if tag_lower in [tg.lower() for tg in t.tags]]
    return results


def search_templates(query: str) -> list[Template]:
    """Search templates by keyword across name, description, tags, and platform."""
    query_lower = query.lower()
    scored: list[tuple[int, Template]] = []
    for t in BUILT_IN_TEMPLATES:
        score = 0
        if query_lower in t.name.lower():
            score += 10
        if query_lower in t.platform.lower():
            score += 8
        if any(query_lower in tag.lower() for tag in t.tags):
            score += 5
        if query_lower in t.description.lower():
            score += 2
        if score > 0:
            scored.append((score, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored]
