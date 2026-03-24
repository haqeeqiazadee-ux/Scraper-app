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
# 18. Amazon Seller Scraper
# ---------------------------------------------------------------------------
AMAZON_SELLER = Template(
    id="amazon-seller",
    name="Amazon Seller Scraper",
    description=(
        "Extract Amazon seller/merchant data — store name, total reviews, "
        "product listings, feedback ratings, and contact details."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["amazon", "seller", "merchant", "storefront"],
    icon="🏢",
    platform="Amazon",
    config=TemplateConfig(
        target_domains=["amazon.com", "amazon.co.uk", "amazon.de"],
        example_urls=[
            "https://www.amazon.com/sp?seller=A1B2C3D4E5",
        ],
        fields=[
            _field("seller_name", "Seller/store name", required=True),
            _field("seller_id", "Amazon seller ID"),
            _field("rating", "Feedback rating percentage", field_type="number"),
            _field("total_ratings", "Lifetime rating count", field_type="number"),
            _field("positive_last_12m", "Positive feedback last 12 months", field_type="number"),
            _field("business_name", "Registered business name"),
            _field("business_address", "Business address"),
            _field("product_count", "Number of listed products", field_type="number"),
            _field("storefront_url", "Seller storefront URL", field_type="url"),
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
# 19. Amazon Search Results Scraper
# ---------------------------------------------------------------------------
AMAZON_SEARCH = Template(
    id="amazon-search",
    name="Amazon Search Results Scraper",
    description=(
        "Extract real-time search results from Amazon — product titles, prices, "
        "ratings, sponsored flags, and ranking positions for any keyword."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["amazon", "search", "serp", "keyword", "ranking"],
    icon="🔎",
    platform="Amazon",
    config=TemplateConfig(
        target_domains=["amazon.com", "amazon.co.uk", "amazon.de"],
        example_urls=[
            "https://www.amazon.com/s?k=wireless+earbuds",
        ],
        fields=[
            _field("position", "Organic rank position", field_type="number", required=True),
            _field("title", "Product title", required=True),
            _field("price", "Current price", field_type="number"),
            _field("rating", "Star rating", field_type="number"),
            _field("review_count", "Number of reviews", field_type="number"),
            _field("asin", "ASIN identifier"),
            _field("is_sponsored", "Sponsored listing flag"),
            _field("is_prime", "Prime eligible"),
            _field("image_url", "Product thumbnail", field_type="image"),
            _field("product_url", "Product page URL", field_type="url"),
            _field("badge", "Badge text (Best Seller, Choice, etc.)"),
        ],
        preferred_lane="browser",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        proxy_type="residential",
        rate_limit_rpm=15,
        timeout_ms=45000,
        pagination={"type": "next_button", "selector": "a.s-pagination-next"},
    ),
)


# ---------------------------------------------------------------------------
# 20. Amazon Product Details Scraper
# ---------------------------------------------------------------------------
AMAZON_PRODUCT_DETAILS = Template(
    id="amazon-product-details",
    name="Amazon Product Details Scraper",
    description=(
        "Deep extraction of Amazon product pages — full specifications, "
        "variant data (colors/sizes), A+ content, comparison tables, "
        "and frequently bought together items."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["amazon", "product", "specifications", "variants", "detailed"],
    icon="📋",
    platform="Amazon",
    config=TemplateConfig(
        target_domains=["amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
                        "amazon.it", "amazon.es", "amazon.ca", "amazon.co.jp",
                        "amazon.in", "amazon.com.au"],
        example_urls=[
            "https://www.amazon.com/dp/B0BSHF7WHW",
        ],
        fields=[
            _field("title", "Product title", required=True),
            _field("price", "Current price", field_type="number", required=True),
            _field("specifications", "Technical specifications table", field_type="json"),
            _field("variants", "All variants (color, size, style)", field_type="json"),
            _field("frequently_bought_together", "FBT product ASINs", field_type="list"),
            _field("similar_items", "Similar/compared items", field_type="list"),
            _field("a_plus_content", "A+ / Enhanced brand content", field_type="html"),
            _field("dimensions", "Product dimensions"),
            _field("weight", "Item weight"),
            _field("manufacturer", "Manufacturer name"),
            _field("country_of_origin", "Country of origin"),
            _field("date_first_available", "Date first available"),
            _field("all_images", "All product images", field_type="list"),
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
# 21. TikTok Shop Scraper
# ---------------------------------------------------------------------------
TIKTOK_SHOP = Template(
    id="tiktok-shop",
    name="TikTok Shop Scraper",
    description=(
        "Extract product data from TikTok Shop — prices, sales volume, "
        "seller details, and trending product insights for e-commerce analysis."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["tiktok", "shop", "social-commerce", "trending", "viral"],
    icon="🎵",
    platform="TikTok Shop",
    config=TemplateConfig(
        target_domains=["tiktok.com", "shop.tiktok.com"],
        example_urls=[
            "https://shop.tiktok.com/view/product/12345",
        ],
        fields=[
            _field("title", "Product name", required=True),
            _field("price", "Current price", field_type="number", required=True),
            _field("original_price", "Original price", field_type="number"),
            _field("sold_count", "Total units sold", field_type="number"),
            _field("rating", "Product rating", field_type="number"),
            _field("review_count", "Number of reviews", field_type="number"),
            _field("seller_name", "Shop/seller name"),
            _field("seller_rating", "Seller rating", field_type="number"),
            _field("image_url", "Product image", field_type="image"),
            _field("product_url", "Product page URL", field_type="url"),
            _field("category", "Product category"),
            _field("variations", "Product variations (size, color)", field_type="json"),
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
# 22. Trustpilot Reviews Scraper
# ---------------------------------------------------------------------------
TRUSTPILOT_REVIEWS = Template(
    id="trustpilot-reviews",
    name="Trustpilot Reviews Scraper",
    description=(
        "Extract company reviews from Trustpilot — review text, scores, "
        "dates, reviewer info, company responses. Filter by star rating or date."
    ),
    category=TemplateCategory.REVIEWS,
    tags=["trustpilot", "reviews", "reputation", "ratings", "trust"],
    icon="🛡️",
    platform="Trustpilot",
    config=TemplateConfig(
        target_domains=["trustpilot.com"],
        example_urls=[
            "https://www.trustpilot.com/review/example.com",
        ],
        fields=[
            _field("review_title", "Review headline", required=True),
            _field("review_text", "Full review body", required=True),
            _field("score", "Star rating (1-5)", field_type="number"),
            _field("date", "Review date"),
            _field("reviewer_name", "Reviewer display name"),
            _field("reviewer_country", "Reviewer country"),
            _field("reviewer_reviews_count", "Total reviews by this reviewer", field_type="number"),
            _field("company_response", "Company reply text"),
            _field("verified", "Verified order flag"),
            _field("experience_date", "Date of experience"),
        ],
        preferred_lane="http",
        browser_required=False,
        rate_limit_rpm=30,
        timeout_ms=20000,
        pagination={"type": "page_param", "param": "page", "start": 1, "items_per_page": 20},
    ),
)


# ---------------------------------------------------------------------------
# 23. Yelp Business Scraper
# ---------------------------------------------------------------------------
YELP_BUSINESS = Template(
    id="yelp-business",
    name="Yelp Business Scraper",
    description=(
        "Scrape Yelp for restaurant and business data — ratings, reviews, "
        "amenities, operating hours, photos, and detailed business info."
    ),
    category=TemplateCategory.REVIEWS,
    tags=["yelp", "restaurant", "business", "reviews", "local"],
    icon="🍽️",
    platform="Yelp",
    config=TemplateConfig(
        target_domains=["yelp.com"],
        example_urls=[
            "https://www.yelp.com/search?find_desc=restaurants&find_loc=New+York",
            "https://www.yelp.com/biz/example-restaurant",
        ],
        fields=[
            _field("name", "Business name", required=True),
            _field("rating", "Star rating (1-5)", field_type="number", required=True),
            _field("review_count", "Total number of reviews", field_type="number"),
            _field("price_range", "Price range ($ to $$$$)"),
            _field("categories", "Business categories", field_type="list"),
            _field("address", "Full street address"),
            _field("phone", "Phone number"),
            _field("hours", "Operating hours", field_type="json"),
            _field("amenities", "Business amenities/attributes", field_type="list"),
            _field("photos_count", "Number of photos", field_type="number"),
            _field("website", "Business website URL", field_type="url"),
            _field("top_reviews", "Top/highlighted reviews", field_type="json"),
        ],
        preferred_lane="browser",
        browser_required=True,
        stealth_required=True,
        proxy_required=True,
        rate_limit_rpm=15,
        timeout_ms=30000,
    ),
)


# ---------------------------------------------------------------------------
# 24. Facebook Ads Library Scraper
# ---------------------------------------------------------------------------
FACEBOOK_ADS_LIBRARY = Template(
    id="facebook-ads-library",
    name="Facebook Ads Library Scraper",
    description=(
        "Extract ads from Meta Ad Library — ad creatives, spend ranges, "
        "impressions, run dates, targeting regions across Facebook, Instagram, "
        "WhatsApp, and Threads."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["facebook", "meta", "ads", "advertising", "competitive-intelligence"],
    icon="📢",
    platform="Facebook Ads Library",
    config=TemplateConfig(
        target_domains=["facebook.com"],
        example_urls=[
            "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&q=shoes",
        ],
        fields=[
            _field("ad_id", "Ad library ID", required=True),
            _field("page_name", "Advertiser page name", required=True),
            _field("ad_creative_body", "Ad copy / body text"),
            _field("ad_creative_link_title", "Link headline"),
            _field("ad_creative_link_description", "Link description"),
            _field("ad_image_url", "Ad image URL", field_type="image"),
            _field("ad_video_url", "Ad video URL", field_type="url"),
            _field("start_date", "Ad start date"),
            _field("end_date", "Ad end date (if stopped)"),
            _field("spend_lower", "Spend range lower bound", field_type="number"),
            _field("spend_upper", "Spend range upper bound", field_type="number"),
            _field("impressions_lower", "Impressions lower bound", field_type="number"),
            _field("impressions_upper", "Impressions upper bound", field_type="number"),
            _field("platforms", "Platforms (Facebook, Instagram, etc.)", field_type="list"),
            _field("region_distribution", "Audience region breakdown", field_type="json"),
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
# 25. Google Ads Scraper
# ---------------------------------------------------------------------------
GOOGLE_ADS = Template(
    id="google-ads",
    name="Google Ads Transparency Scraper",
    description=(
        "Extract advertising data from Google Ads Transparency Center — "
        "ad creatives, text/image/video ads, locations, and advertiser details."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["google", "ads", "advertising", "transparency", "serp"],
    icon="📣",
    platform="Google Ads",
    config=TemplateConfig(
        target_domains=["adstransparency.google.com"],
        example_urls=[
            "https://adstransparency.google.com/?region=US&topic=shopping",
        ],
        fields=[
            _field("advertiser_name", "Advertiser name", required=True),
            _field("ad_format", "Ad format (text, image, video)", required=True),
            _field("ad_text", "Ad headline and description"),
            _field("display_url", "Display URL shown in ad"),
            _field("landing_page", "Landing page URL", field_type="url"),
            _field("ad_image_url", "Ad creative image", field_type="image"),
            _field("last_shown", "Date last shown"),
            _field("region", "Target region/country"),
            _field("topic", "Ad topic category"),
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
# 26. eBay Product Details Scraper
# ---------------------------------------------------------------------------
EBAY_PRODUCT_DETAILS = Template(
    id="ebay-product-details",
    name="eBay Product Details Scraper",
    description=(
        "Deep extraction from individual eBay product pages — seller stats, "
        "item specifics, shipping details, return policy, and full description."
    ),
    category=TemplateCategory.MARKETPLACE,
    tags=["ebay", "product", "details", "seller", "specifics"],
    icon="🔍",
    platform="eBay",
    config=TemplateConfig(
        target_domains=["ebay.com", "ebay.co.uk", "ebay.de"],
        example_urls=[
            "https://www.ebay.com/itm/123456789",
        ],
        fields=[
            _field("title", "Item title", required=True),
            _field("price", "Current/BIN price", field_type="number", required=True),
            _field("condition", "Item condition with details"),
            _field("seller_name", "Seller username"),
            _field("seller_feedback_score", "Seller feedback score", field_type="number"),
            _field("seller_positive_pct", "Positive feedback %", field_type="number"),
            _field("item_specifics", "Item specifics (brand, model, etc.)", field_type="json"),
            _field("shipping_cost", "Shipping cost", field_type="number"),
            _field("shipping_service", "Shipping service name"),
            _field("returns_accepted", "Returns accepted flag"),
            _field("return_period", "Return window (days)"),
            _field("description_html", "Full item description", field_type="html"),
            _field("images", "All listing images", field_type="list"),
            _field("watchers", "Number of watchers", field_type="number"),
        ],
        preferred_lane="http",
        browser_required=False,
        rate_limit_rpm=25,
        timeout_ms=30000,
    ),
)


# ---------------------------------------------------------------------------
# 27. eBay Reviews Scraper
# ---------------------------------------------------------------------------
EBAY_REVIEWS = Template(
    id="ebay-reviews",
    name="eBay Product Reviews Scraper",
    description=(
        "Extract product reviews from eBay with advanced filters — "
        "sort by rating, filter verified purchases, image-only reviews."
    ),
    category=TemplateCategory.REVIEWS,
    tags=["ebay", "reviews", "ratings", "feedback"],
    icon="💬",
    platform="eBay",
    config=TemplateConfig(
        target_domains=["ebay.com", "ebay.co.uk", "ebay.de"],
        example_urls=[
            "https://www.ebay.com/itm/123456789#UserReviews",
        ],
        fields=[
            _field("review_title", "Review headline", required=True),
            _field("review_text", "Full review body", required=True),
            _field("rating", "Star rating (1-5)", field_type="number"),
            _field("review_date", "Date of review"),
            _field("reviewer_name", "Reviewer username"),
            _field("verified_purchase", "Verified purchase flag"),
            _field("has_images", "Review includes images"),
            _field("helpful_count", "Helpfulness votes", field_type="number"),
        ],
        preferred_lane="http",
        browser_required=False,
        rate_limit_rpm=25,
        timeout_ms=30000,
        pagination={"type": "page_param", "param": "pgn", "start": 1, "items_per_page": 20},
    ),
)


# ---------------------------------------------------------------------------
# 28. Zalando Product Scraper
# ---------------------------------------------------------------------------
ZALANDO_PRODUCT = Template(
    id="zalando-product",
    name="Zalando Product Scraper",
    description=(
        "Scrape Zalando product data across all European markets — prices, "
        "brands, discounts, sizes, colors, and product descriptions."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["zalando", "fashion", "europe", "clothing", "shoes"],
    icon="👗",
    platform="Zalando",
    config=TemplateConfig(
        target_domains=["zalando.com", "zalando.de", "zalando.fr", "zalando.it",
                        "zalando.es", "zalando.nl", "zalando.pl", "zalando.co.uk"],
        example_urls=[
            "https://www.zalando.de/herrenschuhe/",
            "https://www.zalando.com/men-shoes/",
        ],
        fields=[
            _field("title", "Product name", required=True),
            _field("brand", "Brand name", required=True),
            _field("price", "Current price", field_type="number", required=True),
            _field("original_price", "Original price", field_type="number"),
            _field("discount_pct", "Discount percentage", field_type="number"),
            _field("currency", "Price currency"),
            _field("color", "Product color"),
            _field("sizes_available", "Available sizes", field_type="list"),
            _field("image_url", "Main product image", field_type="image"),
            _field("description", "Product description"),
            _field("product_url", "Product page URL", field_type="url"),
            _field("category", "Product category"),
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
# 29. Mercado Libre Scraper
# ---------------------------------------------------------------------------
MERCADO_LIBRE = Template(
    id="mercado-libre",
    name="Mercado Libre Scraper",
    description=(
        "Extract products, sellers, and listings from Mercado Libre — "
        "Latin America's largest e-commerce marketplace. Supports all country domains."
    ),
    category=TemplateCategory.MARKETPLACE,
    tags=["mercadolibre", "latin-america", "marketplace", "mexico", "brazil"],
    icon="🌎",
    platform="Mercado Libre",
    config=TemplateConfig(
        target_domains=["mercadolibre.com", "mercadolibre.com.mx", "mercadolibre.com.ar",
                        "mercadolibre.com.co", "mercadolibre.cl", "mercadolivre.com.br"],
        example_urls=[
            "https://www.mercadolibre.com.mx/ofertas",
        ],
        fields=[
            _field("title", "Product title", required=True),
            _field("price", "Current price", field_type="number", required=True),
            _field("original_price", "Original price", field_type="number"),
            _field("currency", "Price currency (MXN, ARS, BRL, etc.)"),
            _field("seller_name", "Seller name"),
            _field("seller_reputation", "Seller reputation level"),
            _field("condition", "New / Used / Refurbished"),
            _field("free_shipping", "Free shipping flag"),
            _field("sold_count", "Units sold", field_type="number"),
            _field("rating", "Product rating", field_type="number"),
            _field("image_url", "Product image", field_type="image"),
            _field("product_url", "Listing URL", field_type="url"),
            _field("location", "Seller location"),
        ],
        preferred_lane="browser",
        browser_required=True,
        proxy_required=True,
        rate_limit_rpm=20,
        timeout_ms=30000,
        pagination={"type": "next_button", "selector": "a.andes-pagination__link--next"},
    ),
)


# ---------------------------------------------------------------------------
# 30. Naver Shopping Scraper
# ---------------------------------------------------------------------------
NAVER_SHOPPING = Template(
    id="naver-shopping",
    name="Naver Shopping Scraper",
    description=(
        "Extract product data from Naver Shopping — South Korea's dominant "
        "e-commerce search engine. Prices, seller info, and reviews."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["naver", "korea", "shopping", "asia"],
    icon="🇰🇷",
    platform="Naver Shopping",
    config=TemplateConfig(
        target_domains=["shopping.naver.com"],
        example_urls=[
            "https://shopping.naver.com/search/all?query=headphones",
        ],
        fields=[
            _field("title", "Product name", required=True),
            _field("price", "Lowest price", field_type="number", required=True),
            _field("mall_name", "Seller/mall name"),
            _field("category", "Product category"),
            _field("review_count", "Number of reviews", field_type="number"),
            _field("rating", "Product rating", field_type="number"),
            _field("image_url", "Product thumbnail", field_type="image"),
            _field("product_url", "Product page URL", field_type="url"),
            _field("delivery_info", "Delivery/shipping info"),
        ],
        preferred_lane="browser",
        browser_required=True,
        proxy_required=True,
        proxy_type="residential",
        rate_limit_rpm=15,
        timeout_ms=30000,
    ),
)


# ---------------------------------------------------------------------------
# 31. Kickstarter Scraper
# ---------------------------------------------------------------------------
KICKSTARTER = Template(
    id="kickstarter",
    name="Kickstarter Project Scraper",
    description=(
        "Scrape Kickstarter project data — funding progress, backer counts, "
        "reward tiers, project descriptions, and creator info."
    ),
    category=TemplateCategory.MARKETPLACE,
    tags=["kickstarter", "crowdfunding", "projects", "startups"],
    icon="🚀",
    platform="Kickstarter",
    config=TemplateConfig(
        target_domains=["kickstarter.com"],
        example_urls=[
            "https://www.kickstarter.com/discover/advanced?category_id=16&sort=magic",
        ],
        fields=[
            _field("title", "Project name", required=True),
            _field("pledged", "Amount pledged", field_type="number", required=True),
            _field("goal", "Funding goal", field_type="number"),
            _field("percent_funded", "Funding percentage", field_type="number"),
            _field("backers_count", "Number of backers", field_type="number"),
            _field("currency", "Currency code"),
            _field("creator_name", "Creator/company name"),
            _field("category", "Project category"),
            _field("location", "Creator location"),
            _field("status", "Project status (live, successful, failed)"),
            _field("end_date", "Campaign end date"),
            _field("description", "Project blurb/description"),
            _field("image_url", "Project hero image", field_type="image"),
            _field("project_url", "Project page URL", field_type="url"),
        ],
        preferred_lane="http",
        browser_required=False,
        rate_limit_rpm=30,
        timeout_ms=20000,
    ),
)


# ---------------------------------------------------------------------------
# 32. Shopify Lead Scraper
# ---------------------------------------------------------------------------
SHOPIFY_LEADS = Template(
    id="shopify-leads",
    name="Shopify Lead Scraper",
    description=(
        "Extract e-commerce leads from Shopify-powered stores — shop emails, "
        "business contact info, technology stack, and store metadata."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["shopify", "leads", "email", "b2b", "prospecting"],
    icon="📧",
    platform="Shopify",
    config=TemplateConfig(
        target_domains=["*.myshopify.com"],
        example_urls=[],
        fields=[
            _field("shop_name", "Store name", required=True),
            _field("shop_url", "Store URL", field_type="url", required=True),
            _field("email", "Contact email"),
            _field("phone", "Contact phone number"),
            _field("country", "Store country"),
            _field("currency", "Store currency"),
            _field("product_count", "Number of products", field_type="number"),
            _field("social_links", "Social media links", field_type="json"),
            _field("shopify_plan", "Shopify plan tier"),
            _field("theme", "Active Shopify theme"),
        ],
        preferred_lane="api",
        browser_required=False,
        rate_limit_rpm=40,
        timeout_ms=15000,
    ),
)


# ---------------------------------------------------------------------------
# 33. AI Product Matcher
# ---------------------------------------------------------------------------
AI_PRODUCT_MATCHER = Template(
    id="ai-product-matcher",
    name="AI Product Matcher",
    description=(
        "AI-powered cross-site product matching — find the same product across "
        "multiple e-commerce websites for price comparison and arbitrage detection."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["ai", "matching", "comparison", "arbitrage", "cross-site"],
    icon="🔗",
    platform="Any",
    config=TemplateConfig(
        target_domains=[],
        example_urls=[],
        fields=[
            _field("product_title", "Product name from source", required=True),
            _field("source_url", "Source product URL", field_type="url", required=True),
            _field("source_price", "Price on source site", field_type="number"),
            _field("matched_url", "Matched product URL on target site", field_type="url"),
            _field("matched_price", "Price on target site", field_type="number"),
            _field("match_confidence", "AI match confidence (0-1)", field_type="number"),
            _field("price_difference", "Price delta", field_type="number"),
            _field("match_method", "How match was determined (UPC, title, image)"),
        ],
        preferred_lane="auto",
        extraction_type="ai",
        rate_limit_rpm=20,
        timeout_ms=45000,
        extraction_rules={
            "strategy": "ai_matching",
            "matching_signals": ["upc", "ean", "title_similarity", "image_hash", "brand+model"],
            "min_confidence": 0.85,
        },
    ),
)


# ---------------------------------------------------------------------------
# 34. Google Play Store Scraper
# ---------------------------------------------------------------------------
GOOGLE_PLAY = Template(
    id="google-play",
    name="Google Play Store Scraper",
    description=(
        "Extract app data and reviews from Google Play Store — ratings, "
        "download counts, pricing, developer info, and user reviews."
    ),
    category=TemplateCategory.ECOMMERCE,
    tags=["google-play", "apps", "mobile", "reviews", "android"],
    icon="📱",
    platform="Google Play",
    config=TemplateConfig(
        target_domains=["play.google.com"],
        example_urls=[
            "https://play.google.com/store/apps/details?id=com.example.app",
        ],
        fields=[
            _field("app_name", "App title", required=True),
            _field("developer", "Developer name", required=True),
            _field("rating", "Average rating", field_type="number"),
            _field("review_count", "Number of reviews", field_type="number"),
            _field("installs", "Install count range"),
            _field("price", "App price (0 if free)", field_type="number"),
            _field("category", "App category"),
            _field("description", "App description"),
            _field("whats_new", "Latest update notes"),
            _field("version", "Current version"),
            _field("size", "App size"),
            _field("icon_url", "App icon", field_type="image"),
            _field("screenshots", "Screenshot URLs", field_type="list"),
        ],
        preferred_lane="http",
        browser_required=False,
        rate_limit_rpm=30,
        timeout_ms=20000,
    ),
)


# ---------------------------------------------------------------------------
# 35. eBay Store Scraper
# ---------------------------------------------------------------------------
EBAY_STORE = Template(
    id="ebay-store",
    name="eBay Store Scraper",
    description=(
        "Extract all products from a specific eBay seller's store — "
        "complete inventory with prices, conditions, and shipping details."
    ),
    category=TemplateCategory.MARKETPLACE,
    tags=["ebay", "store", "seller", "inventory", "bulk"],
    icon="🏪",
    platform="eBay",
    config=TemplateConfig(
        target_domains=["ebay.com", "ebay.co.uk", "ebay.de"],
        example_urls=[
            "https://www.ebay.com/str/sellername",
        ],
        fields=[
            _field("title", "Item title", required=True),
            _field("price", "Current price", field_type="number", required=True),
            _field("condition", "Item condition"),
            _field("shipping_cost", "Shipping cost", field_type="number"),
            _field("free_shipping", "Free shipping flag"),
            _field("listing_type", "Auction / Buy It Now"),
            _field("image_url", "Item thumbnail", field_type="image"),
            _field("item_url", "Listing URL", field_type="url"),
            _field("sold_count", "Quantity sold", field_type="number"),
            _field("watchers", "Number of watchers", field_type="number"),
        ],
        preferred_lane="http",
        browser_required=False,
        rate_limit_rpm=25,
        timeout_ms=30000,
        pagination={"type": "next_button", "selector": "a.pagination__next"},
    ),
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BUILT_IN_TEMPLATES: list[Template] = [
    # Amazon ecosystem
    AMAZON_PRODUCT,
    AMAZON_REVIEWS,
    AMAZON_BESTSELLERS,
    AMAZON_SELLER,
    AMAZON_SEARCH,
    AMAZON_PRODUCT_DETAILS,
    # Shopify ecosystem
    SHOPIFY_STORE,
    SHOPIFY_LEADS,
    # eBay ecosystem
    EBAY_ITEMS,
    EBAY_PRODUCT_DETAILS,
    EBAY_REVIEWS,
    EBAY_STORE,
    # Major retailers
    WALMART_PRODUCT,
    TARGET_PRODUCT,
    BESTBUY_PRODUCT,
    COSTCO_PRODUCT,
    # Marketplaces
    ETSY_LISTINGS,
    ALIEXPRESS_PRODUCT,
    ALIBABA_SUPPLIER,
    FACEBOOK_MARKETPLACE,
    MERCADO_LIBRE,
    KICKSTARTER,
    TIKTOK_SHOP,
    # Fashion / Regional
    ZALANDO_PRODUCT,
    NAVER_SHOPPING,
    # WooCommerce
    WOOCOMMERCE_STORE,
    # Ads / Competitive Intelligence
    FACEBOOK_ADS_LIBRARY,
    GOOGLE_ADS,
    GOOGLE_SHOPPING,
    # Reviews platforms
    TRUSTPILOT_REVIEWS,
    YELP_BUSINESS,
    # Apps
    GOOGLE_PLAY,
    # AI-powered / Universal
    UNIVERSAL_ECOMMERCE,
    AI_PRODUCT_MATCHER,
    PRICE_MONITOR,
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
