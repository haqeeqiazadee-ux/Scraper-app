"""
🛒 INTELLIGENT PRODUCT SCRAPER
===============================
Scrapes ALL product data from any e-commerce page.
Works with both category pages and single product pages.

Run: python smart_scraper.py <url>
Example: python smart_scraper.py https://myshop.pk/laptops-desktops-computers/laptops
"""

import sys
import re
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scrapling.fetchers import StealthyFetcher
from smart_exporter import SmartExcelExporter


class IntelligentProductScraper:
    """
    Intelligent scraper that extracts ALL product information.
    Auto-detects page type (category vs product detail).
    """
    
    def __init__(self, timeout=60000):
        self.timeout = timeout
        self.products = []
    
    def fetch(self, url: str):
        """Fetch page with stealth mode"""
        print(f"🌐 Fetching: {url}")
        page = StealthyFetcher.fetch(
            url,
            timeout=self.timeout,
            network_idle=True
        )
        print(f"✅ Status: {page.status}")
        return page
    
    def detect_page_type(self, page) -> str:
        """Detect if it's a category page or product detail page"""
        # Check for multiple product items (category page)
        product_grids = page.css(".product-item, .product-card, .product-grid-item, [data-product-id]")
        
        if len(product_grids) > 1:
            return "category"
        
        # Check for single product indicators
        add_to_cart = page.css("button[id*='add-to-cart'], .add-to-cart, #product-addtocart-button")
        product_info = page.css(".product-info-main, .product-detail, #product-info")
        
        if add_to_cart or product_info:
            return "product"
        
        # Default to category if we found at least some products
        if product_grids:
            return "category"
        
        return "unknown"
    
    def extract_text(self, element, selector: str) -> str:
        """Safely extract text from element"""
        try:
            els = element.css(selector)
            if els:
                text = els[0].text if hasattr(els[0], 'text') else ''
                return text.strip() if text else ''
        except:
            pass
        return ''
    
    def extract_attr(self, element, selector: str, attr: str) -> str:
        """Safely extract attribute from element"""
        try:
            els = element.css(selector)
            if els:
                return els[0].attrib.get(attr, '')
        except:
            pass
        return ''
    
    def extract_all_text(self, element, selector: str) -> list:
        """Extract text from all matching elements"""
        try:
            els = element.css(selector)
            return [el.text.strip() for el in els if hasattr(el, 'text') and el.text]
        except:
            pass
        return []
    
    def clean_price(self, price_str: str) -> str:
        """Clean and format price string"""
        if not price_str:
            return ''
        # Remove extra whitespace
        price_str = ' '.join(price_str.split())
        return price_str
    
    def extract_from_category_page(self, page) -> list:
        """Extract products from category/listing page"""
        products = []
        
        # Try multiple selectors for product containers
        container_selectors = [
            ".product-item",
            ".product-card",
            ".product-grid-item",
            ".products-grid .item",
            ".product-items .product-item",
            "[data-product-id]",
            ".product",
        ]
        
        product_items = []
        for selector in container_selectors:
            items = page.css(selector)
            if items:
                product_items = items
                print(f"📦 Found {len(items)} products with selector: {selector}")
                break
        
        for item in product_items:
            product = self._extract_product_from_grid(item)
            if product.get('name') or product.get('title'):
                products.append(product)
        
        return products
    
    def _extract_product_from_grid(self, item) -> dict:
        """Extract all data from a product grid item"""
        product = {}
        
        # ===== PRODUCT NAME / TITLE =====
        name_selectors = [
            ".product-item-link",
            ".product-name a",
            ".product-title",
            "a.product-item-link",
            ".product-item-name a",
            "h2.product-name",
            "h3.product-name",
            ".name a",
            "a[title]",
        ]
        
        for selector in name_selectors:
            name = self.extract_text(item, selector)
            if not name:
                # Try getting from title attribute
                name = self.extract_attr(item, selector, 'title')
            if name:
                product['name'] = name
                break
        
        # ===== SKU / PRODUCT ID =====
        sku_selectors = [
            "[data-product-sku]",
            ".sku .value",
            ".product-sku",
            "[data-sku]",
            ".sku",
        ]
        
        for selector in sku_selectors:
            sku = self.extract_text(item, selector)
            if not sku:
                sku = self.extract_attr(item, selector, 'data-product-sku')
            if not sku:
                sku = self.extract_attr(item, selector, 'data-sku')
            if sku:
                product['sku'] = sku
                break
        
        # Also try data attributes on container
        if not product.get('sku'):
            product['sku'] = item.attrib.get('data-product-sku', '') or item.attrib.get('data-sku', '') or item.attrib.get('data-product-id', '')
        
        # ===== PRICE =====
        price_selectors = [
            ".price-box .price",
            ".special-price .price",
            ".price",
            "[data-price-amount]",
            ".product-price",
            ".final-price",
            ".current-price",
        ]
        
        for selector in price_selectors:
            price = self.extract_text(item, selector)
            if price:
                product['price'] = self.clean_price(price)
                break
            # Try data attribute
            price_amount = self.extract_attr(item, selector, 'data-price-amount')
            if price_amount:
                product['price'] = f"Rs {float(price_amount):,.2f}"
                break
        
        # ===== ORIGINAL PRICE (if on sale) =====
        old_price_selectors = [
            ".old-price .price",
            ".regular-price .price",
            ".was-price",
            ".original-price",
            "del .price",
            ".price-old",
        ]
        
        for selector in old_price_selectors:
            old_price = self.extract_text(item, selector)
            if old_price:
                product['original_price'] = self.clean_price(old_price)
                break
        
        # ===== DISCOUNT =====
        discount_selectors = [
            ".discount-percent",
            ".sale-badge",
            ".discount-label",
            ".save-percent",
            ".discount",
        ]
        
        for selector in discount_selectors:
            discount = self.extract_text(item, selector)
            if discount:
                product['discount'] = discount
                break
        
        # ===== DESCRIPTION / SPECS =====
        desc_selectors = [
            ".product-item-description",
            ".product-description",
            ".description",
            ".short-description",
            ".product-specs",
            ".specs",
        ]
        
        for selector in desc_selectors:
            desc = self.extract_text(item, selector)
            if desc:
                product['description'] = desc
                break
        
        # ===== RATING =====
        rating_selectors = [
            ".rating-result",
            ".rating",
            "[class*='rating']",
            ".stars",
            ".review-rating",
        ]
        
        for selector in rating_selectors:
            els = item.css(selector)
            if els:
                # Try to get rating from style (width percentage)
                style = els[0].attrib.get('style', '')
                if 'width' in style:
                    match = re.search(r'width:\s*(\d+)%', style)
                    if match:
                        product['rating'] = f"{int(match.group(1)) / 20:.1f}/5"
                        break
                # Try title attribute
                title = els[0].attrib.get('title', '')
                if title:
                    product['rating'] = title
                    break
        
        # ===== REVIEW COUNT =====
        review_selectors = [
            ".reviews-count",
            ".review-count",
            ".rating-count",
            ".num-reviews",
        ]
        
        for selector in review_selectors:
            reviews = self.extract_text(item, selector)
            if reviews:
                product['reviews'] = reviews
                break
        
        # ===== PRODUCT URL =====
        url_selectors = [
            "a.product-item-link",
            "a.product-item-photo",
            ".product-item-info a",
            "a[href*='product']",
            ".product-name a",
            "a",
        ]
        
        for selector in url_selectors:
            url = self.extract_attr(item, selector, 'href')
            if url and '/product' in url.lower() or url and not url.startswith('#'):
                product['url'] = url
                break
        
        # ===== IMAGE URL =====
        img_selectors = [
            "img.product-image-photo",
            ".product-image img",
            ".product-item-photo img",
            "img[src*='product']",
            "img",
        ]
        
        for selector in img_selectors:
            img = self.extract_attr(item, selector, 'src')
            if not img:
                img = self.extract_attr(item, selector, 'data-src')
            if not img:
                img = self.extract_attr(item, selector, 'data-lazy')
            if img:
                product['image'] = img
                break
        
        # ===== STOCK STATUS =====
        stock_selectors = [
            ".stock",
            ".availability",
            ".in-stock",
            ".out-of-stock",
            "[class*='stock']",
        ]
        
        for selector in stock_selectors:
            stock = self.extract_text(item, selector)
            if stock:
                product['stock'] = stock
                break
        
        # ===== BRAND =====
        brand_selectors = [
            ".product-brand",
            ".brand",
            "[data-brand]",
            ".manufacturer",
        ]
        
        for selector in brand_selectors:
            brand = self.extract_text(item, selector)
            if not brand:
                brand = self.extract_attr(item, selector, 'data-brand')
            if brand:
                product['brand'] = brand
                break
        
        # ===== BADGES (New, Sale, etc) =====
        badge_selectors = [
            ".product-label",
            ".badge",
            ".tag",
            ".label",
            ".new-label",
            ".sale-label",
        ]
        
        badges = []
        for selector in badge_selectors:
            badge_texts = self.extract_all_text(item, selector)
            badges.extend(badge_texts)
        if badges:
            product['badges'] = ', '.join(badges)
        
        # ===== DELIVERY INFO =====
        delivery_selectors = [
            ".delivery-info",
            ".shipping-info",
            ".delivery",
            "[class*='delivery']",
            ".same-day",
        ]
        
        for selector in delivery_selectors:
            delivery = self.extract_text(item, selector)
            if delivery:
                product['delivery'] = delivery
                break
        
        return product
    
    def extract_from_product_page(self, page, url: str) -> dict:
        """Extract all data from a single product page"""
        product = {'url': url}
        
        # ===== PRODUCT NAME =====
        name_selectors = [
            "h1.page-title",
            ".product-info-main h1",
            "h1.product-name",
            ".product-title",
            "h1",
        ]
        
        for selector in name_selectors:
            name = self.extract_text(page, selector)
            if name:
                product['name'] = name
                break
        
        # ===== SKU =====
        sku_selectors = [
            ".product-info-stock-sku .value",
            ".sku .value",
            "[itemprop='sku']",
            ".product-sku",
        ]
        
        for selector in sku_selectors:
            sku = self.extract_text(page, selector)
            if sku:
                product['sku'] = sku
                break
        
        # ===== PRICE =====
        price_selectors = [
            ".product-info-price .price",
            ".price-box .price",
            "[data-price-amount]",
            ".product-price",
        ]
        
        for selector in price_selectors:
            price = self.extract_text(page, selector)
            if price:
                product['price'] = self.clean_price(price)
                break
        
        # ===== ORIGINAL PRICE =====
        old_selectors = [".old-price .price", ".was-price", "del .price"]
        for selector in old_selectors:
            old = self.extract_text(page, selector)
            if old:
                product['original_price'] = self.clean_price(old)
                break
        
        # ===== DESCRIPTION =====
        desc_selectors = [
            ".product-info-main .description",
            ".product-description",
            "#description",
            ".short-description",
            "[itemprop='description']",
        ]
        
        for selector in desc_selectors:
            desc = self.extract_text(page, selector)
            if desc:
                product['description'] = desc
                break
        
        # ===== FULL SPECIFICATIONS =====
        # Try to find spec table
        spec_selectors = [
            ".product-attributes",
            ".additional-attributes",
            "#product-attributes",
            ".specifications",
            "table.data-table",
        ]
        
        specs = {}
        for selector in spec_selectors:
            spec_table = page.css(selector)
            if spec_table:
                rows = spec_table[0].css("tr")
                for row in rows:
                    th = self.extract_text(row, "th")
                    td = self.extract_text(row, "td")
                    if th and td:
                        specs[th] = td
                break
        
        if specs:
            product['specifications'] = json.dumps(specs)
            # Also add individual spec columns
            for key, value in specs.items():
                clean_key = key.lower().replace(' ', '_').replace('-', '_')
                product[f'spec_{clean_key}'] = value
        
        # ===== IMAGES (all) =====
        images = []
        img_selectors = [
            ".fotorama__stage img",
            ".product-image-gallery img",
            ".gallery-placeholder img",
            ".product-image img",
        ]
        
        for selector in img_selectors:
            imgs = page.css(selector)
            for img in imgs:
                src = img.attrib.get('src', '') or img.attrib.get('data-src', '')
                if src and src not in images:
                    images.append(src)
        
        if images:
            product['image'] = images[0]
            product['all_images'] = ', '.join(images[:5])  # First 5 images
        
        # ===== STOCK =====
        stock_selectors = [".stock", ".availability", "[class*='stock']"]
        for selector in stock_selectors:
            stock = self.extract_text(page, selector)
            if stock:
                product['stock'] = stock
                break
        
        # ===== BRAND =====
        brand_selectors = [".brand", "[itemprop='brand']", ".manufacturer"]
        for selector in brand_selectors:
            brand = self.extract_text(page, selector)
            if brand:
                product['brand'] = brand
                break
        
        # ===== CATEGORY =====
        breadcrumb = page.css(".breadcrumbs a, .breadcrumb a")
        if breadcrumb:
            categories = [bc.text.strip() for bc in breadcrumb if hasattr(bc, 'text') and bc.text]
            product['category'] = ' > '.join(categories)
        
        return product
    
    def scrape(self, url: str) -> list:
        """Main scrape method - auto-detects page type"""
        page = self.fetch(url)
        page_type = self.detect_page_type(page)
        
        print(f"📄 Page type detected: {page_type}")
        
        if page_type == "category":
            products = self.extract_from_category_page(page)
        elif page_type == "product":
            product = self.extract_from_product_page(page, url)
            products = [product] if product.get('name') else []
        else:
            # Try category extraction anyway
            products = self.extract_from_category_page(page)
        
        self.products = products
        return products
    
    def export(self, filename: str = "products.xlsx"):
        """Export scraped products to Excel"""
        if not self.products:
            print("❌ No products to export")
            return None
        
        exporter = SmartExcelExporter()
        result = exporter.export(
            self.products,
            filename,
            add_summary=True,
            highlight_deals=True
        )
        
        if result:
            import os
            size = os.path.getsize(result)
            print(f"✅ Exported {len(self.products)} products to {result} ({size:,} bytes)")
        
        return result


def main():
    """Main entry point"""
    print("=" * 70)
    print("🛒 INTELLIGENT PRODUCT SCRAPER")
    print("=" * 70)
    
    # Get URL from command line or use default
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://myshop.pk/laptops-desktops-computers/laptops"
    
    print(f"\nTarget: {url}\n")
    
    # Scrape
    scraper = IntelligentProductScraper(timeout=60000)
    products = scraper.scrape(url)
    
    print(f"\n{'='*70}")
    print(f"📊 RESULTS: {len(products)} products extracted")
    print("=" * 70)
    
    # Show sample
    if products:
        print("\nSample products:")
        print("-" * 70)
        for i, p in enumerate(products[:5], 1):
            print(f"\n{i}. {p.get('name', 'Unknown')[:60]}")
            print(f"   SKU: {p.get('sku', 'N/A')}")
            print(f"   Price: {p.get('price', 'N/A')}")
            if p.get('original_price'):
                print(f"   Was: {p.get('original_price')}")
            if p.get('description'):
                print(f"   Specs: {p.get('description', '')[:80]}...")
            if p.get('rating'):
                print(f"   Rating: {p.get('rating')}")
        
        if len(products) > 5:
            print(f"\n... and {len(products) - 5} more products")
        
        # Export
        print(f"\n{'='*70}")
        output_file = "scraped_products.xlsx"
        scraper.export(output_file)
        print("=" * 70)
    else:
        print("❌ No products found")


if __name__ == "__main__":
    main()
