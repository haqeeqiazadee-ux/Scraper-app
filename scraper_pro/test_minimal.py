"""
🧪 MINIMAL SCRAPE TEST
=======================
This test bypasses all our code and tests Scrapling directly.

Run: python test_minimal.py
"""

print("=" * 60)
print("🧪 MINIMAL SCRAPLING TEST")
print("=" * 60)
print()

# Test 1: Direct Scrapling fetch with correct timeout
print("TEST 1: Direct StealthyFetcher with timeout=30000ms")
print("-" * 60)

try:
    from scrapling.fetchers import StealthyFetcher
    
    page = StealthyFetcher.fetch(
        "https://books.toscrape.com",
        timeout=30000,  # 30 seconds in milliseconds
        network_idle=True
    )
    
    print(f"✅ Status: {page.status}")
    
    # Extract products using .css() method
    products = page.css("article.product_pod")
    print(f"✅ Found {len(products)} products")
    
    # Get first product title
    if products:
        first = products[0]
        title_link = first.css("h3 a")
        if title_link:
            # Scrapling uses .attrib for attributes
            title = title_link[0].attrib.get('title', 'Unknown')
            print(f"✅ First product: {title}")
        
        price_el = first.css(".price_color")
        if price_el:
            # Use .text for text content  
            price = price_el[0].text
            print(f"✅ First price: {price}")
    
    print()
    print("🎉 SCRAPLING WORKS CORRECTLY!")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("TEST 2: Using our Engine v2")
print("-" * 60)

try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    
    from engine_v2 import ScrapingEngine
    
    # Create engine with 30 second timeout
    engine = ScrapingEngine(mode="stealthy", timeout=30)
    
    print(f"Engine timeout: {engine.timeout}s = {engine.timeout_ms}ms")
    
    # Fetch
    page = engine.fetch("https://books.toscrape.com")
    
    if page:
        print(f"✅ Status: {page.status}")
        
        products = page.css("article.product_pod")
        print(f"✅ Found {len(products)} products")
        
        print()
        print("🎉 ENGINE v2 WORKS CORRECTLY!")
    else:
        print("❌ Page is None")
        
except Exception as e:
    print(f"❌ ENGINE ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("TEST 3: Full workflow with Excel export")  
print("-" * 60)

try:
    from engine_v2 import ScrapingEngine
    from smart_exporter import SmartExcelExporter
    import tempfile
    import os
    
    # Fetch
    engine = ScrapingEngine(mode="stealthy", timeout=30)
    page = engine.fetch("https://books.toscrape.com")
    
    if not page:
        raise Exception("Failed to fetch page")
    
    # Extract products
    products = []
    for article in page.css("article.product_pod")[:5]:
        title_link = article.css("h3 a")
        price_el = article.css(".price_color")
        
        title = title_link[0].attrib.get('title', 'Unknown') if title_link else 'Unknown'
        price = price_el[0].text if price_el else '$0'
        
        products.append({
            "title": title,
            "price": price,
            "category": "Books"
        })
    
    print(f"✅ Extracted {len(products)} products")
    
    # Export to Excel
    exporter = SmartExcelExporter()
    
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        filepath = f.name
    
    result = exporter.export(products, filepath, add_summary=True)
    
    if result and os.path.exists(result):
        file_size = os.path.getsize(result)
        print(f"✅ Created Excel: {file_size:,} bytes")
        print(f"✅ Location: {result}")
        
        # Show content
        print()
        print("Products extracted:")
        for i, p in enumerate(products, 1):
            print(f"  {i}. {p['title'][:50]} - {p['price']}")
        
        print()
        print("🎉 FULL WORKFLOW COMPLETE!")
        
        # Don't delete - user can check it
        print(f"\n📁 Excel file saved at: {result}")
    else:
        print("❌ Export failed")
        
except Exception as e:
    print(f"❌ WORKFLOW ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("DONE")
print("=" * 60)
