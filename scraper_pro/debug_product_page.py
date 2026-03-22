"""
🔍 Debug script to analyze myshop.pk product page HTML structure
"""

from scrapling.fetchers import StealthyFetcher

url = "https://myshop.pk/hp-notebook-15-fd0532nia-pakistan.html"

print(f"Fetching: {url}")
page = StealthyFetcher.fetch(url, timeout=60000, network_idle=True)

print(f"Status: {page.status}")
print("\n" + "="*70)
print("ANALYZING PAGE STRUCTURE")
print("="*70)

# Check for product name
print("\n📦 PRODUCT NAME:")
name_selectors = [
    "h1.page-title",
    "h1.product-name", 
    ".product-info-main h1",
    "h1[itemprop='name']",
    ".product-title",
    "h1",
]
for sel in name_selectors:
    els = page.css(sel)
    if els:
        text = els[0].text if hasattr(els[0], 'text') else 'N/A'
        print(f"  ✅ {sel}: {text[:80] if text else 'empty'}")
    else:
        print(f"  ❌ {sel}: not found")

# Check for SKU
print("\n🏷️ SKU:")
sku_selectors = [
    ".product-info-stock-sku .value",
    ".sku .value",
    "[itemprop='sku']",
    ".product.attribute.sku .value",
    "div.sku",
    "[data-product-sku]",
]
for sel in sku_selectors:
    els = page.css(sel)
    if els:
        text = els[0].text if hasattr(els[0], 'text') else els[0].attrib.get('content', 'N/A')
        print(f"  ✅ {sel}: {text}")
    else:
        print(f"  ❌ {sel}: not found")

# Check for price
print("\n💰 PRICE:")
price_selectors = [
    ".product-info-price .price",
    ".price-box .price",
    "[data-price-amount]",
    ".price-final_price .price",
    ".special-price .price",
    "span.price",
]
for sel in price_selectors:
    els = page.css(sel)
    if els:
        text = els[0].text if hasattr(els[0], 'text') else ''
        attr = els[0].attrib.get('data-price-amount', '')
        print(f"  ✅ {sel}: text='{text}' | data-price-amount='{attr}'")
    else:
        print(f"  ❌ {sel}: not found")

# Check for description
print("\n📝 DESCRIPTION:")
desc_selectors = [
    ".product.attribute.description .value",
    ".product-info-main .description",
    "#description .value",
    ".product-description",
    "[itemprop='description']",
    ".short-description",
]
for sel in desc_selectors:
    els = page.css(sel)
    if els:
        text = els[0].text if hasattr(els[0], 'text') else 'N/A'
        print(f"  ✅ {sel}: {text[:100] if text else 'empty'}...")
    else:
        print(f"  ❌ {sel}: not found")

# Check for specifications table
print("\n📋 SPECIFICATIONS:")
spec_selectors = [
    "#product-attribute-specs-table",
    ".additional-attributes",
    "table.data-table",
    ".product-attributes",
    "#additional",
    ".product-specs",
]
for sel in spec_selectors:
    els = page.css(sel)
    if els:
        rows = els[0].css("tr")
        print(f"  ✅ {sel}: Found table with {len(rows)} rows")
        for row in rows[:3]:  # Show first 3 specs
            th = row.css("th")
            td = row.css("td")
            if th and td:
                th_text = th[0].text if hasattr(th[0], 'text') else ''
                td_text = td[0].text if hasattr(td[0], 'text') else ''
                print(f"      {th_text}: {td_text}")
    else:
        print(f"  ❌ {sel}: not found")

# Check for images
print("\n🖼️ IMAGES:")
img_selectors = [
    ".fotorama__stage img",
    ".gallery-placeholder img",
    ".product-image-container img",
    ".product.media img",
    "img.gallery-placeholder__image",
]
for sel in img_selectors:
    els = page.css(sel)
    if els:
        src = els[0].attrib.get('src', '') or els[0].attrib.get('data-src', '')
        print(f"  ✅ {sel}: {src[:80]}...")
    else:
        print(f"  ❌ {sel}: not found")

# Show all h1 tags
print("\n🔍 ALL H1 TAGS:")
h1s = page.css("h1")
for h1 in h1s[:5]:
    classes = h1.attrib.get('class', 'no-class')
    text = h1.text if hasattr(h1, 'text') else 'no-text'
    print(f"  - class='{classes}' text='{text}'")

# Show page title
print("\n🔍 PAGE TITLE:")
title = page.css("title")
if title:
    print(f"  {title[0].text}")

# Show some HTML structure
print("\n🔍 MAIN PRODUCT CONTAINER:")
containers = [
    ".product-info-main",
    ".product-info",
    "#maincontent",
    ".column.main",
]
for sel in containers:
    els = page.css(sel)
    if els:
        children = els[0].css("> *")
        print(f"  ✅ {sel}: found with {len(children)} direct children")
        for child in children[:5]:
            tag = child.tag if hasattr(child, 'tag') else 'unknown'
            classes = child.attrib.get('class', '')[:50]
            print(f"      <{tag}> class='{classes}'")
    else:
        print(f"  ❌ {sel}: not found")
