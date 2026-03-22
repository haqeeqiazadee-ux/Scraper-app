"""
🛒 MYSHOP.PK SCRAPER
====================
Scrapes laptops from myshop.pk with full product details.

Run: python scrape_myshop.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scrapling.fetchers import StealthyFetcher
from smart_exporter import SmartExcelExporter

def scrape_myshop_laptops():
    """Scrape laptops from myshop.pk"""
    
    url = "https://myshop.pk/laptops-desktops-computers/laptops"
    
    print("=" * 60)
    print("🛒 MYSHOP.PK LAPTOP SCRAPER")
    print("=" * 60)
    print(f"\nFetching: {url}")
    print("-" * 60)
    
    # Fetch the page
    page = StealthyFetcher.fetch(
        url,
        timeout=60000,  # 60 seconds
        network_idle=True
    )
    
    print(f"✅ Status: {page.status}")
    
    # Find all product items
    products = []
    product_items = page.css(".product-item")
    
    print(f"✅ Found {len(product_items)} products")
    print("-" * 60)
    
    for item in product_items:
        try:
            product = {}
            
            # Product name - try multiple selectors
            name_el = item.css(".product-item-link") or item.css(".product-name a") or item.css("a.product-item-link")
            if name_el:
                product['name'] = name_el[0].text.strip() if hasattr(name_el[0], 'text') and name_el[0].text else name_el[0].attrib.get('title', '')
            
            # Price - try multiple selectors
            price_el = item.css(".price") or item.css(".special-price .price") or item.css("[data-price-amount]")
            if price_el:
                price_text = price_el[0].text if hasattr(price_el[0], 'text') else ''
                product['price'] = price_text.strip() if price_text else ''
            
            # Original price (if on sale)
            old_price_el = item.css(".old-price .price") or item.css(".regular-price")
            if old_price_el:
                old_price_text = old_price_el[0].text if hasattr(old_price_el[0], 'text') else ''
                product['original_price'] = old_price_text.strip() if old_price_text else ''
            
            # Product URL
            link_el = item.css("a.product-item-link") or item.css("a[href*='product']") or item.css(".product-item-info a")
            if link_el:
                product['url'] = link_el[0].attrib.get('href', '')
            
            # Image URL
            img_el = item.css("img.product-image-photo") or item.css(".product-image img") or item.css("img")
            if img_el:
                product['image'] = img_el[0].attrib.get('src', '') or img_el[0].attrib.get('data-src', '')
            
            # Rating (if available)
            rating_el = item.css(".rating-result") or item.css("[class*='rating']")
            if rating_el:
                # Try to extract rating percentage or value
                rating_style = rating_el[0].attrib.get('style', '')
                if 'width' in rating_style:
                    # Extract percentage from style="width: 80%"
                    import re
                    match = re.search(r'width:\s*(\d+)%', rating_style)
                    if match:
                        product['rating'] = f"{int(match.group(1)) / 20:.1f}/5"
            
            # Only add if we got at least a name
            if product.get('name'):
                products.append(product)
                print(f"  📦 {product['name'][:50]}... - {product.get('price', 'N/A')}")
        
        except Exception as e:
            print(f"  ⚠️ Error extracting product: {e}")
            continue
    
    print("-" * 60)
    print(f"\n✅ Successfully extracted {len(products)} products")
    
    # Export to Excel
    if products:
        print("\n📊 Exporting to Excel...")
        
        exporter = SmartExcelExporter()
        output_file = "myshop_laptops.xlsx"
        
        result = exporter.export(
            products, 
            output_file,
            sheet_name="Laptops",
            add_summary=True,
            highlight_deals=True
        )
        
        if result:
            import os
            file_size = os.path.getsize(result)
            print(f"✅ Saved to: {result}")
            print(f"✅ File size: {file_size:,} bytes")
            print(f"\n🎉 Done! Open {output_file} to see your data.")
        else:
            print("❌ Export failed")
    
    return products


if __name__ == "__main__":
    products = scrape_myshop_laptops()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    if products:
        # Show price range
        prices = []
        for p in products:
            price_str = p.get('price', '')
            # Extract numbers from price string
            import re
            numbers = re.findall(r'[\d,]+', price_str.replace(',', ''))
            if numbers:
                try:
                    prices.append(int(numbers[0].replace(',', '')))
                except:
                    pass
        
        if prices:
            print(f"  Total products: {len(products)}")
            print(f"  Price range: Rs. {min(prices):,} - Rs. {max(prices):,}")
            print(f"  Average price: Rs. {sum(prices)//len(prices):,}")
