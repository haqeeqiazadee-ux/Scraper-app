"""
🧪 Test scraping myshop.pk
"""

from scrapling.fetchers import StealthyFetcher

url = "https://myshop.pk/laptops-desktops-computers/laptops"

print(f"Testing: {url}")
print("-" * 60)

try:
    page = StealthyFetcher.fetch(
        url,
        timeout=60000,  # 60 seconds - some sites are slow
        network_idle=True,
        headless=True
    )
    
    print(f"✅ Status: {page.status}")
    
    # Try to find products
    # Common e-commerce selectors
    selectors_to_try = [
        ".product-item",
        ".product-card", 
        ".product",
        "[data-product]",
        ".item",
        ".product-box",
        ".product-wrapper",
        "article.product",
        ".products-grid .item",
        ".category-products .item",
    ]
    
    for selector in selectors_to_try:
        items = page.css(selector)
        if items:
            print(f"✅ Found {len(items)} items with selector: {selector}")
            break
    else:
        print("❌ No products found with common selectors")
        
        # Show page structure
        print("\nPage structure hints:")
        all_classes = set()
        for el in page.css("*[class]")[:100]:
            classes = el.attrib.get('class', '').split()
            for c in classes:
                if 'product' in c.lower() or 'item' in c.lower():
                    all_classes.add(c)
        
        if all_classes:
            print(f"Classes containing 'product' or 'item': {all_classes}")
        
        # Show a snippet of HTML
        print("\nHTML snippet (first 2000 chars):")
        html = page.html_content if hasattr(page, 'html_content') else str(page.body[:2000])
        print(html[:2000] if isinstance(html, str) else html.decode('utf-8', errors='ignore')[:2000])

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
