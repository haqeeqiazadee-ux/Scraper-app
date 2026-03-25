"""
Amazon platform-specific extractor.

Extracts structured product data from Amazon pages by parsing:
1. Search results — [data-component-type="s-search-result"] elements
2. Deal/event pages — carousel cards with prices and deal badges
3. Product detail pages — #productTitle, .a-price, etc.

Works on all Amazon TLDs: .com, .co.uk, .de, .fr, .it, .es, .ca, .co.jp, .in, .com.au
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

AMAZON_DOMAINS = [
    "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
    "amazon.it", "amazon.es", "amazon.ca", "amazon.co.jp",
    "amazon.in", "amazon.com.au", "amazon.com.br", "amazon.nl",
    "amazon.sg", "amazon.sa", "amazon.ae", "amazon.com.mx",
]


class AmazonExtractor:
    """Extract structured product data from Amazon HTML pages."""

    DOMAINS = AMAZON_DOMAINS

    def extract(self, html: str, url: str) -> list[dict]:
        """Route to the appropriate extraction method based on URL pattern."""
        path = urlparse(url).path.lower()
        query = urlparse(url).query.lower()

        if "/dp/" in path or "/gp/product/" in path:
            return self._extract_product_detail(html, url)
        elif "/s?" in path or "/s?" in url or "rh=" in query or "k=" in query:
            return self._extract_search_results(html, url)
        elif "/events/" in path or "/deal" in path or "/gp/goldbox" in path:
            return self._extract_deals(html, url)
        elif "/bestsellers/" in path or "/new-releases/" in path:
            return self._extract_search_results(html, url)
        else:
            # Try search results first, then deals, then product
            results = self._extract_search_results(html, url)
            if results:
                return results
            results = self._extract_deals(html, url)
            if results:
                return results
            return self._extract_product_detail(html, url)

    # -------------------------------------------------------------------
    # Search results extraction
    # -------------------------------------------------------------------

    def _extract_search_results(self, html: str, url: str) -> list[dict]:
        """Extract products from Amazon search results pages."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []

        soup = BeautifulSoup(html, "html.parser")
        products: list[dict] = []

        # Primary: data-component-type="s-search-result" (standard search)
        result_divs = soup.select('[data-component-type="s-search-result"]')
        if not result_divs:
            # Fallback: .s-result-item
            result_divs = soup.select('.s-result-item[data-asin]')

        for div in result_divs:
            product = self._parse_search_result(div, url)
            if product and product.get("name"):
                products.append(product)

        return products

    def _parse_search_result(self, div, base_url: str) -> dict:
        """Parse a single search result div into a product dict."""
        product: dict[str, Any] = {}

        # ASIN
        asin = div.get("data-asin", "")
        if asin:
            product["asin"] = asin

        # Title — look in h2 > a > span, or h2 > span
        title_el = div.select_one("h2 a span") or div.select_one("h2 span")
        if title_el:
            product["name"] = title_el.get_text(strip=True)

        # Product URL
        link_el = div.select_one("h2 a[href]")
        if link_el:
            href = link_el.get("href", "")
            product["product_url"] = urljoin(base_url, href) if href else ""

        # Price — .a-price .a-offscreen (first one is current price)
        price_el = div.select_one(".a-price .a-offscreen")
        if price_el:
            product["price"] = price_el.get_text(strip=True)

        # Original price (strikethrough)
        orig_price_el = div.select_one(".a-price.a-text-price .a-offscreen")
        if orig_price_el:
            product["original_price"] = orig_price_el.get_text(strip=True)

        # Rating
        rating_el = div.select_one(".a-icon-alt")
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            match = re.search(r'([\d.]+)', rating_text)
            if match:
                product["rating"] = match.group(1)

        # Review count
        review_el = div.select_one('span[aria-label*="star"] + span a span') or \
                     div.select_one('.a-size-base.s-underline-text')
        if review_el:
            product["review_count"] = review_el.get_text(strip=True).replace(",", "")

        # Image
        img_el = div.select_one("img.s-image")
        if img_el:
            product["image_url"] = img_el.get("src", "")

        # Prime badge
        prime_el = div.select_one(".a-icon-prime, [aria-label*='Prime']")
        if prime_el:
            product["prime"] = True

        # Sponsored flag
        sponsored_el = div.select_one("[data-component-type='sp-sponsored-result']") or \
                        div.select_one(".puis-label-popover-default")
        if sponsored_el:
            product["sponsored"] = True

        # Delivery info
        delivery_el = div.select_one(".a-color-base.a-text-bold")
        if delivery_el:
            product["delivery"] = delivery_el.get_text(strip=True)

        return product

    # -------------------------------------------------------------------
    # Deal / Event page extraction
    # -------------------------------------------------------------------

    def _extract_deals(self, html: str, url: str) -> list[dict]:
        """Extract deals from Amazon deal/event pages (Big Spring Sale, etc.)."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []

        soup = BeautifulSoup(html, "html.parser")
        deals: list[dict] = []

        # Strategy 1: Carousel cards with prices
        carousel_cards = soup.select(".a-carousel-card")
        for card in carousel_cards:
            deal = self._parse_deal_card(card, url)
            if deal and deal.get("name") and deal.get("name") not in (
                "Big Spring Sale", "Deals", "Shop all deals",
            ):
                deals.append(deal)

        # Strategy 2: Deal grid cards
        deal_cards = soup.select('[class*="DealCard"], [class*="GridCard"], [class*="deal-card"]')
        for card in deal_cards:
            deal = self._parse_deal_card(card, url)
            if deal and deal.get("name"):
                deals.append(deal)

        # Strategy 3: Any element with a price + product link
        if not deals:
            price_containers = soup.select(".a-price")
            for price_el in price_containers:
                parent = price_el.find_parent(["div", "li", "article"], limit=5)
                if parent:
                    deal = self._parse_deal_card(parent, url)
                    if deal and deal.get("name") and len(deal.get("name", "")) > 10:
                        deals.append(deal)

        # Deduplicate by name
        seen: set[str] = set()
        unique: list[dict] = []
        for d in deals:
            key = d.get("name", "")
            if key and key not in seen:
                seen.add(key)
                unique.append(d)

        return unique

    def _parse_deal_card(self, card, base_url: str) -> dict:
        """Parse a deal card element into a deal dict."""
        deal: dict[str, Any] = {}

        # Title — try various patterns
        for sel in ["h3", "h2", ".a-text-normal", "[class*='Title']", "a[href*='/dp/']"]:
            el = card.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text and len(text) > 5:
                    deal["name"] = text[:200]
                    break

        # Price
        price_el = card.select_one(".a-price .a-offscreen") or card.select_one("[class*='price']")
        if price_el:
            deal["price"] = price_el.get_text(strip=True)

        # Discount percentage
        discount_el = card.select_one("[class*='discount'], [class*='saving'], [class*='off']")
        if discount_el:
            text = discount_el.get_text(strip=True)
            match = re.search(r'(\d+%)', text)
            if match:
                deal["discount"] = match.group(1)

        # Image
        img_el = card.select_one("img[src*='media-amazon'], img[src*='images-amazon']")
        if img_el:
            deal["image_url"] = img_el.get("src", "")

        # Product URL
        link_el = card.select_one("a[href*='/dp/']") or card.select_one("a[href*='/gp/']")
        if link_el:
            href = link_el.get("href", "")
            deal["product_url"] = urljoin(base_url, href) if href else ""

        return deal

    # -------------------------------------------------------------------
    # Product detail page extraction
    # -------------------------------------------------------------------

    def _extract_product_detail(self, html: str, url: str) -> list[dict]:
        """Extract product data from a single product detail page."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []

        soup = BeautifulSoup(html, "html.parser")
        product: dict[str, Any] = {"product_url": url}

        # Title
        title_el = soup.select_one("#productTitle")
        if title_el:
            product["name"] = title_el.get_text(strip=True)

        # Price
        price_el = soup.select_one("#priceblock_ourprice, #priceblock_dealprice, .a-price .a-offscreen")
        if price_el:
            product["price"] = price_el.get_text(strip=True)

        # Rating
        rating_el = soup.select_one("#acrPopover span.a-icon-alt, #averageCustomerReviews .a-icon-alt")
        if rating_el:
            text = rating_el.get_text(strip=True)
            match = re.search(r'([\d.]+)', text)
            if match:
                product["rating"] = match.group(1)

        # Review count
        review_el = soup.select_one("#acrCustomerReviewText")
        if review_el:
            text = review_el.get_text(strip=True)
            match = re.search(r'([\d,]+)', text)
            if match:
                product["review_count"] = match.group(1).replace(",", "")

        # Image
        img_el = soup.select_one("#landingImage, #imgBlkFront")
        if img_el:
            product["image_url"] = img_el.get("src", "") or img_el.get("data-old-hires", "")

        # Brand
        brand_el = soup.select_one("#bylineInfo")
        if brand_el:
            product["brand"] = brand_el.get_text(strip=True).replace("Visit the ", "").replace(" Store", "")

        # ASIN from URL
        match = re.search(r'/dp/([A-Z0-9]{10})', url)
        if match:
            product["asin"] = match.group(1)

        # Availability
        avail_el = soup.select_one("#availability span")
        if avail_el:
            product["availability"] = avail_el.get_text(strip=True)

        # Description
        desc_el = soup.select_one("#productDescription p")
        if desc_el:
            product["description"] = desc_el.get_text(strip=True)[:500]

        # Features (bullet points)
        features = []
        for li in soup.select("#feature-bullets li span.a-list-item"):
            text = li.get_text(strip=True)
            if text and len(text) > 5:
                features.append(text)
        if features:
            product["features"] = features

        if product.get("name"):
            return [product]
        return []
