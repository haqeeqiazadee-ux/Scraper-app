"""
🔍 Check Scrapling Response Object Attributes
"""

from scrapling.fetchers import StealthyFetcher

print("Fetching a page...")
page = StealthyFetcher.fetch("https://httpbin.org/get", timeout=30000)

print(f"\nType: {type(page)}")
print(f"\nAll attributes:")
for attr in dir(page):
    if not attr.startswith('_'):
        print(f"  - {attr}")

print("\n\nTrying common content attributes:")
attrs_to_try = ['html', 'text', 'content', 'body', 'source', 'page_source', 'get_text']

for attr in attrs_to_try:
    if hasattr(page, attr):
        val = getattr(page, attr)
        if callable(val):
            print(f"  ✅ {attr}() - callable")
        else:
            preview = str(val)[:100] if val else "None"
            print(f"  ✅ {attr} = {preview}...")
    else:
        print(f"  ❌ {attr} - not found")

# Check if we can get the HTML content somehow
print("\n\nActual content access:")
try:
    # Try .text
    if hasattr(page, 'text'):
        print(f"page.text[:200] = {page.text[:200]}")
except Exception as e:
    print(f"page.text error: {e}")

try:
    # Try getting body
    if hasattr(page, 'body'):
        body = page.body
        if hasattr(body, 'html'):
            print(f"page.body.html[:200] = {body.html[:200]}")
        else:
            print(f"page.body = {str(body)[:200]}")
except Exception as e:
    print(f"page.body error: {e}")

# Try str(page)
try:
    print(f"\nstr(page)[:200] = {str(page)[:200]}")
except Exception as e:
    print(f"str(page) error: {e}")
