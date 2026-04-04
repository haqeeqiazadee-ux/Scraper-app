"""
Deterministic provider — rule-based extraction without AI.

Uses CSS selectors, JSON-LD, regex patterns as fallback when
AI providers are unavailable or unnecessary.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from packages.core.ai_providers.base import BaseAIProvider

logger = logging.getLogger(__name__)

# Common CSS selectors for product data
PRODUCT_SELECTORS = {
    "name": [
        'h1[itemprop="name"]', "h1.product-title", "h1.product-name",
        "h1.product_title", ".product-info h1", "#product-name", "h1",
    ],
    "price": [
        '[itemprop="price"]', ".price", ".product-price", ".current-price",
        "#price", ".offer-price", "span.price",
    ],
}

# Regex patterns for common data
PRICE_PATTERN = re.compile(r'[\$\£\€\₹]?\s*(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d{2})?)')
CURRENCY_PATTERN = re.compile(r'(USD|EUR|GBP|PKR|INR|AUD|CAD)')


class DeterministicProvider(BaseAIProvider):
    """Rule-based extraction without AI dependencies."""

    def __init__(self) -> None:
        super().__init__(name="deterministic")
        self._social_provider = None

    def _get_social_provider(self):
        """Lazily initialize the social media provider."""
        if self._social_provider is None:
            from packages.core.ai_providers.social.dispatcher import SocialMediaProvider
            self._social_provider = SocialMediaProvider()
        return self._social_provider

    def _get_adaptive_engine(self):
        """Lazily initialize the adaptive selector engine."""
        if not hasattr(self, '_adaptive'):
            from packages.core.adaptive_selectors import AdaptiveSelectorEngine
            self._adaptive = AdaptiveSelectorEngine()
        return self._adaptive

    def _get_converter(self):
        """Lazily initialize the markdown/trafilatura converter."""
        if not hasattr(self, '_converter'):
            from packages.core.markdown_converter import MarkdownConverter
            self._converter = MarkdownConverter()
        return self._converter

    async def extract(
        self,
        html: str,
        url: str,
        prompt: Optional[str] = None,
        css_selectors: Optional[dict] = None,
    ) -> list[dict]:
        """Extract structured data using deterministic methods.

        Extraction cascade (most reliable → least reliable):
        0a. Social media platform-specific handlers
        0b. Custom CSS selectors (user-provided / policy)
        1.  JSON-LD structured data (schema.org)
        2.  Microdata / RDFa (schema.org in HTML attributes)
        3.  Open Graph meta tags (og:type=product)
        4.  Adaptive selectors (fuzzy-matched from cache)
        5.  DOM auto-discovery (repeating groups)
        6.  CSS selector extraction (common card patterns)
        7.  Trafilatura content extraction (article/blog/non-product)
        8.  Validated basic fallback (single product from title/meta)
        9.  LLM extraction (only when all tiers fail AND confidence < 0.3)
        """
        # 0a. Try social media platform-specific extraction first
        social = self._get_social_provider()
        if social.can_handle(url):
            social_result = await social.extract(html, url)
            if social_result:
                return social_result

        # 0b. If custom selectors are provided, run a targeted single-item pass first
        if css_selectors:
            custom_result = self._extract_with_custom_selectors(html, url, css_selectors)
            if custom_result:
                return [custom_result]

        # 1. Try JSON-LD extraction (most reliable structured data)
        jsonld_products = self._extract_jsonld(html)
        if jsonld_products:
            return jsonld_products

        # 2. Try microdata extraction (schema.org in HTML attributes)
        microdata_products = self._extract_microdata(html, url)
        if microdata_products:
            return microdata_products

        # 3. Try Open Graph meta tags (og:type=product)
        og_product = self._extract_opengraph(html, url)
        if og_product:
            return [og_product]

        # 4. Try adaptive selectors (fuzzy-matched from cache)
        try:
            adaptive = self._get_adaptive_engine()
            selectors = adaptive.get_selectors(url)
            if selectors:
                result = self._extract_with_custom_selectors(
                    html, url, selectors.get("field_selectors", {})
                )
                if result:
                    adaptive.record_success(url, selectors, html)
                    return [result]
                else:
                    # Try adapting stale selectors
                    adapted = adaptive.adapt_selectors(url, html)
                    if adapted:
                        result = self._extract_with_custom_selectors(
                            html, url, adapted.get("field_selectors", {})
                        )
                        if result:
                            adaptive.record_success(url, adapted, html)
                            return [result]
                    adaptive.record_failure(url, selectors)
        except Exception as exc:
            logger.debug("Adaptive selector extraction failed: %s", exc)

        # 5. Try DOM auto-discovery (finds repeating groups without selectors)
        dom_products = self._extract_dom_discovery(html, url)
        if dom_products:
            return dom_products

        # 6. Try CSS selector extraction (multi-item capable)
        css_products = self._extract_css(html, url)
        if css_products:
            return css_products

        # 7. Try trafilatura for article/blog content extraction
        try:
            converter = self._get_converter()
            traf_result = converter.convert(html, url, output_format="html")
            if traf_result.content and len(traf_result.content) > 100:
                return [{
                    "name": traf_result.title or "Article",
                    "description": traf_result.content[:500],
                    "product_url": url,
                    "content_type": "article",
                    "full_content": traf_result.content,
                    "estimated_tokens": traf_result.estimated_tokens,
                    "_confidence": 0.4,
                    "_extraction_method": "trafilatura",
                }]
        except Exception as exc:
            logger.debug("Trafilatura content extraction failed: %s", exc)

        # 8. Validated basic fallback (only returns if actually looks like a product)
        basic = self._extract_basic(html, url)
        if basic:
            return [basic]

        # 9. LLM extraction fallback — triggered in the AI normalization worker
        # when all deterministic tiers above fail AND confidence < 0.3.
        # Return empty with a low-confidence marker so the caller knows to
        # escalate to LLM-based extraction.
        return [{"_confidence": 0.0, "_extraction_method": "none", "product_url": url}]

    async def classify(self, text: str, labels: list[str]) -> str:
        """Simple keyword-based classification."""
        text_lower = text.lower()
        scores = {}
        for label in labels:
            scores[label] = text_lower.count(label.lower())
        return max(scores, key=scores.get) if scores else labels[0]

    async def normalize(self, data: dict, target_schema: dict) -> dict:
        """Basic field mapping normalization."""
        normalized = {}
        field_aliases = {
            "product_name": "name", "title": "name", "product_title": "name",
            "cost": "price", "amount": "price", "product_price": "price",
            "img": "image_url", "image": "image_url", "photo": "image_url",
            "link": "product_url", "href": "product_url",
        }
        for key, value in data.items():
            mapped_key = field_aliases.get(key.lower(), key)
            normalized[mapped_key] = value
        return normalized

    def _extract_with_custom_selectors(self, html: str, url: str, css_selectors: dict) -> dict:
        """Extract a single product using caller-supplied CSS selectors.

        Args:
            html: Raw HTML content.
            url: Source URL.
            css_selectors: Mapping of field name -> CSS selector string.

        Returns:
            Extracted product dict, or empty dict if nothing matched.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return {}

        soup = BeautifulSoup(html, "html.parser")
        result: dict = {"product_url": url}

        for field, selector in css_selectors.items():
            try:
                el = soup.select_one(selector)
                if el:
                    value = el.get("content") or el.get("value") or el.get_text(strip=True)
                    if value:
                        result[field] = value
            except Exception:
                continue

        # Only return if we extracted at least one meaningful field
        meaningful_fields = {k for k in result if k != "product_url"}
        return result if meaningful_fields else {}

    def _extract_dom_discovery(self, html: str, url: str) -> list[dict]:
        """Extract items via DOM auto-discovery of repeating groups.

        This finds structurally similar sibling elements (e.g., product cards)
        without any site-specific selectors. Zero cost, works on any site
        that uses template-generated repeating structures.
        """
        try:
            from packages.core.dom_discovery import discover_items
            items = discover_items(html, url)
            if items:
                logger.debug(
                    "DOM discovery extracted %d items from %s", len(items), url
                )
            return items
        except Exception as exc:
            logger.debug("DOM discovery failed: %s", exc)
            return []

    def _extract_css(self, html: str, url: str) -> list[dict]:
        """Extract multiple products using CSS selectors and BeautifulSoup."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []

        soup = BeautifulSoup(html, "html.parser")
        products = []

        # Common card container selectors (ordered by specificity)
        # Covers: Shopify, WooCommerce, Magento, BigCommerce, PrestaShop,
        # OpenCart, Bootstrap, Tailwind, and generic patterns
        card_selectors = [
            # Schema.org microdata
            '[itemtype*="schema.org/Product"]',
            'li[itemtype*="Product"]',
            'div[itemtype*="Product"]',
            # Shopify
            ".product-card",
            ".product-item",
            ".collection-product-card",
            ".grid-view-item",
            ".grid-product",
            ".product-grid-item",
            "[data-product]",
            "[data-product-id]",
            ".product-card-wrapper",
            # WooCommerce
            "li.product",
            ".product-item-info",
            ".product-layout",
            ".products .product",
            # Magento
            ".item.product-item",
            ".product-item",
            # BigCommerce
            ".card",
            ".productCard",
            # PrestaShop
            ".product-miniature",
            ".product-container",
            # OpenCart
            ".product-thumb",
            # General e-commerce
            ".product-card",
            ".product-tile",
            ".product-box",
            ".product-wrapper",
            ".product-block",
            ".product-listing",
            ".product-figure",
            # Generic catalog patterns
            ".catalog-item",
            ".search-result-item",
            ".listing-item",
            ".grid-item",
            ".card-product",
            # Data attribute patterns
            "[data-product-card]",
            "[data-item]",
            "[data-testid*='product']",
            "[data-component*='product']",
            # Generic containers
            "article.product_pod",       # books.toscrape.com
            "div.quote",                 # quotes.toscrape.com
            ".product",
            ".item",
        ]

        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if len(cards) >= 2:
                break

        if len(cards) < 2:
            return []

        for card in cards:
            product: dict[str, str] = {"product_url": url}

            # Extract name from heading, title, or text element
            name_el = card.select_one(
                "h3 a, h2 a, h4 a, h1 a, h5 a, h6 a,"
                " .product-name, .product-title, .product__title,"
                " .card-title, .card__title, .card-name,"
                " .product-item-name, .product-item-link,"
                " [itemprop='name'], [data-product-name],"
                " .title a, a[title], a.product-link,"
                " h3, h2, h4"
            )
            if name_el:
                product["name"] = (
                    name_el.get("data-product-title")
                    or name_el.get("title")
                    or name_el.get_text(strip=True)
                )
                href = name_el.get("href", "")
                if href and not href.startswith(("http://", "https://")):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                if href:
                    product["product_url"] = href

            # Extract author (for quote-type content)
            author_el = card.select_one("small.author, .author, [itemprop='author']")
            if author_el:
                product["author"] = author_el.get_text(strip=True)

            # Extract price
            price_el = card.select_one(
                "[itemprop='price'], .price_color, .price,"
                " .product-price, .product__price, .card-price,"
                " .sale-price, .current-price, .special-price,"
                " .offer-price, ins .amount, .woocommerce-Price-amount,"
                " [data-price], [data-product-price], span.amount"
            )
            if price_el:
                price_text = price_el.get_text(strip=True)
                price_match = PRICE_PATTERN.search(price_text)
                if price_match:
                    product["price"] = price_match.group(1).replace(",", "")

            # Extract image
            img_el = card.select_one("img")
            if img_el:
                src = img_el.get("src") or img_el.get("data-src", "")
                if src and not src.startswith(("http://", "https://")):
                    from urllib.parse import urljoin
                    src = urljoin(url, src)
                if src:
                    product["image_url"] = src

            # Extract rating (e.g., star-rating class)
            rating_el = card.select_one("[class*='star-rating'], .rating")
            if rating_el:
                classes = rating_el.get("class", [])
                rating_map = {"One": "1", "Two": "2", "Three": "3", "Four": "4", "Five": "5"}
                for cls in classes:
                    if cls in rating_map:
                        product["rating"] = rating_map[cls]
                        break

            # Only include items that look like real products — not nav labels
            # Require a name AND at least one product signal (price, image, or rating)
            name = product.get("name", "").strip()
            if name:
                has_signal = any([
                    product.get("price"),
                    product.get("image_url"),
                    product.get("rating"),
                ])
                if has_signal:
                    products.append(product)

        return products

    def _extract_microdata(self, html: str, url: str) -> list[dict]:
        """Extract products from schema.org microdata (HTML attributes).

        Handles `itemscope itemtype="https://schema.org/Product"` markup.
        This is the second most common structured data format after JSON-LD.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []

        soup = BeautifulSoup(html, "html.parser")
        products = []

        # Find all elements with Product itemtype
        for item in soup.select('[itemtype*="schema.org/Product"]'):
            product: dict = {"product_url": url}

            # Extract itemprop fields
            name_el = item.select_one('[itemprop="name"]')
            if name_el:
                product["name"] = name_el.get("content") or name_el.get_text(strip=True)

            desc_el = item.select_one('[itemprop="description"]')
            if desc_el:
                product["description"] = desc_el.get("content") or desc_el.get_text(strip=True)

            img_el = item.select_one('[itemprop="image"]')
            if img_el:
                src = img_el.get("content") or img_el.get("src") or img_el.get("href", "")
                if src:
                    from urllib.parse import urljoin as _urljoin
                    product["image_url"] = _urljoin(url, src) if not src.startswith("http") else src

            sku_el = item.select_one('[itemprop="sku"]')
            if sku_el:
                product["sku"] = sku_el.get("content") or sku_el.get_text(strip=True)

            brand_el = item.select_one('[itemprop="brand"] [itemprop="name"], [itemprop="brand"]')
            if brand_el:
                product["brand"] = brand_el.get("content") or brand_el.get_text(strip=True)

            url_el = item.select_one('[itemprop="url"]')
            if url_el:
                href = url_el.get("href") or url_el.get("content", "")
                if href:
                    from urllib.parse import urljoin as _urljoin
                    product["product_url"] = _urljoin(url, href) if not href.startswith("http") else href

            # Price from Offer
            offer = item.select_one('[itemtype*="schema.org/Offer"], [itemprop="offers"]')
            if offer:
                price_el = offer.select_one('[itemprop="price"]')
                if price_el:
                    product["price"] = price_el.get("content") or price_el.get_text(strip=True)
                currency_el = offer.select_one('[itemprop="priceCurrency"]')
                if currency_el:
                    product["currency"] = currency_el.get("content") or currency_el.get_text(strip=True)
                avail_el = offer.select_one('[itemprop="availability"]')
                if avail_el:
                    avail = avail_el.get("content") or avail_el.get("href", "")
                    if avail:
                        product["stock_status"] = avail.split("/")[-1] if "/" in avail else avail

            # Rating
            rating_el = item.select_one('[itemprop="ratingValue"]')
            if rating_el:
                product["rating"] = rating_el.get("content") or rating_el.get_text(strip=True)
            reviews_el = item.select_one('[itemprop="reviewCount"]')
            if reviews_el:
                product["reviews_count"] = reviews_el.get("content") or reviews_el.get_text(strip=True)

            if product.get("name"):
                products.append(product)

        return products

    def _extract_opengraph(self, html: str, url: str) -> Optional[dict]:
        """Extract product data from Open Graph meta tags.

        Works when og:type=product or og:price:amount is present.
        Common on single product pages for social media sharing.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return None

        soup = BeautifulSoup(html, "html.parser")

        # Check if this page is tagged as a product
        og_type = soup.select_one('meta[property="og:type"]')
        og_price = soup.select_one('meta[property="og:price:amount"], meta[property="product:price:amount"]')

        # Only use OG if page is explicitly a product or has price tags
        if not og_type and not og_price:
            return None
        if og_type and og_type.get("content", "").lower() not in ("product", "og:product", "product.item"):
            if not og_price:
                return None

        product: dict = {"product_url": url}

        og_title = soup.select_one('meta[property="og:title"]')
        if og_title and og_title.get("content"):
            product["name"] = og_title["content"]

        og_desc = soup.select_one('meta[property="og:description"]')
        if og_desc and og_desc.get("content"):
            product["description"] = og_desc["content"]

        og_image = soup.select_one('meta[property="og:image"]')
        if og_image and og_image.get("content"):
            product["image_url"] = og_image["content"]

        if og_price and og_price.get("content"):
            product["price"] = og_price["content"]

        og_currency = soup.select_one('meta[property="og:price:currency"], meta[property="product:price:currency"]')
        if og_currency and og_currency.get("content"):
            product["currency"] = og_currency["content"]

        og_avail = soup.select_one('meta[property="og:availability"], meta[property="product:availability"]')
        if og_avail and og_avail.get("content"):
            product["stock_status"] = og_avail["content"]

        og_brand = soup.select_one('meta[property="product:brand"]')
        if og_brand and og_brand.get("content"):
            product["brand"] = og_brand["content"]

        # Only return if we got a name and at least one product signal
        if product.get("name") and (product.get("price") or product.get("image_url")):
            return product
        return None

    def _extract_jsonld(self, html: str) -> list[dict]:
        """Extract product data from JSON-LD script tags."""
        products = []
        pattern = re.compile(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            try:
                data = json.loads(match.group(1).strip())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and item.get("@type") in ("Product", "IndividualProduct"):
                        product = {
                            "name": item.get("name", ""),
                            "description": item.get("description", ""),
                            "brand": item.get("brand", {}).get("name", "") if isinstance(item.get("brand"), dict) else str(item.get("brand", "")),
                            "sku": item.get("sku", ""),
                            "image_url": item.get("image", ""),
                            "product_url": url if (url := item.get("url", "")) else "",
                        }
                        # Extract price from offers
                        offers = item.get("offers", {})
                        if isinstance(offers, dict):
                            product["price"] = offers.get("price", "")
                            product["currency"] = offers.get("priceCurrency", "")
                            # B6: stock/availability from single offer
                            availability = offers.get("availability", "")
                            if availability:
                                product["stock_status"] = availability.split("/")[-1] if "/" in availability else availability
                        elif isinstance(offers, list) and offers:
                            product["price"] = offers[0].get("price", "")
                            product["currency"] = offers[0].get("priceCurrency", "")
                            # B6: stock/availability from first offer in list
                            availability = offers[0].get("availability", "")
                            if availability:
                                product["stock_status"] = availability.split("/")[-1] if "/" in availability else availability

                        # B6: Extract variant data from hasVariant or offers array
                        variants = []
                        has_variant = item.get("hasVariant", [])
                        if isinstance(has_variant, list):
                            for v in has_variant:
                                if not isinstance(v, dict):
                                    continue
                                variant: dict = {}
                                if v.get("name"):
                                    variant["name"] = v["name"]
                                if v.get("color"):
                                    variant["color"] = v["color"]
                                if v.get("size"):
                                    variant["size"] = v["size"]
                                v_offers = v.get("offers", {})
                                if isinstance(v_offers, dict) and v_offers.get("price"):
                                    variant["price"] = v_offers["price"]
                                    v_avail = v_offers.get("availability", "")
                                    if v_avail:
                                        variant["stock_status"] = v_avail.split("/")[-1] if "/" in v_avail else v_avail
                                if variant:
                                    variants.append(variant)

                        # Also extract size/color variants from offers list when multiple offers exist
                        if not variants and isinstance(offers, list) and len(offers) > 1:
                            for o in offers:
                                if not isinstance(o, dict):
                                    continue
                                variant = {}
                                if o.get("name"):
                                    variant["name"] = o["name"]
                                if o.get("color"):
                                    variant["color"] = o["color"]
                                if o.get("size"):
                                    variant["size"] = o["size"]
                                if o.get("price"):
                                    variant["price"] = o["price"]
                                o_avail = o.get("availability", "")
                                if o_avail:
                                    variant["stock_status"] = o_avail.split("/")[-1] if "/" in o_avail else o_avail
                                if variant:
                                    variants.append(variant)

                        if variants:
                            product["variants"] = variants

                        # Extract rating
                        rating = item.get("aggregateRating", {})
                        if isinstance(rating, dict):
                            product["rating"] = rating.get("ratingValue", "")
                            product["reviews_count"] = rating.get("reviewCount", "")

                        products.append(product)
            except (json.JSONDecodeError, AttributeError):
                continue
        return products

    def _extract_basic(self, html: str, url: str) -> Optional[dict]:
        """Validated basic extraction as last resort.

        Only returns a result if the page genuinely looks like a product page.
        Returns None (not empty dict) if the page doesn't have enough product signals.
        This prevents garbage items (site title + random price) from being returned
        as successful extractions.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return self._extract_basic_regex(html, url)

        soup = BeautifulSoup(html, "html.parser")
        result: dict = {"product_url": url}
        product_signals = 0

        # Try to get a product name (not site title)
        # Look for h1 first (usually the product title on PDPs)
        h1 = soup.select_one("h1")
        if h1:
            name = h1.get_text(strip=True)
            if name and len(name) > 2 and len(name) < 200:
                result["name"] = name
                product_signals += 1

        # If no h1, try og:title (but clean site name suffix)
        if "name" not in result:
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
                # Remove common site name suffixes
                for sep in [" | ", " - ", " – ", " — ", " :: "]:
                    if sep in title:
                        title = title.split(sep)[0].strip()
                if title and len(title) > 2:
                    result["name"] = title
                    product_signals += 1

        # Look for price in dedicated price elements (not random text)
        price_el = soup.select_one(
            '[itemprop="price"], .price, .product-price, #price,'
            ' .offer-price, .current-price, .sale-price'
        )
        if price_el:
            price_text = price_el.get("content") or price_el.get_text(strip=True)
            if price_text:
                price_match = PRICE_PATTERN.search(price_text)
                if price_match:
                    result["price"] = price_match.group(1).replace(",", "")
                    product_signals += 1

        # Check for add-to-cart (strong product page signal)
        add_to_cart = soup.select_one(
            'button[name*="add"], button[class*="add-to-cart"],'
            ' input[value*="Add to Cart"], [data-action*="cart"],'
            ' form[action*="cart"], button[class*="buy"]'
        )
        if add_to_cart:
            product_signals += 1

        # Image
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image and og_image.get("content"):
            result["image_url"] = og_image["content"]
        else:
            main_img = soup.select_one('.product-image img, .product img, #product-image img')
            if main_img:
                src = main_img.get("src") or main_img.get("data-src", "")
                if src:
                    from urllib.parse import urljoin as _urljoin
                    result["image_url"] = _urljoin(url, src) if not src.startswith("http") else src

        # Currency
        currency_match = CURRENCY_PATTERN.search(html)
        if currency_match:
            result["currency"] = currency_match.group(1)

        # Only return if page has enough product signals (name + price minimum)
        if product_signals >= 2 and result.get("name"):
            return result
        return None

    def _extract_basic_regex(self, html: str, url: str) -> Optional[dict]:
        """Regex-only fallback when BeautifulSoup is not available."""
        result: dict = {"product_url": url}
        signals = 0

        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            name = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            if name and len(name) > 2:
                result["name"] = name
                signals += 1

        prices = PRICE_PATTERN.findall(html)
        if prices:
            result["price"] = prices[0].replace(",", "")
            signals += 1

        if signals >= 2 and result.get("name"):
            return result
        return None
