"""Test ALL templates via Playwright CDP browser + HTTP fallback."""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

import types
sd = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services")
for h in ["control-plane", "worker-http", "worker-browser", "worker-ai", "worker-hard-target"]:
    mn = f"services.{h.replace('-', '_')}"
    d = os.path.join(sd, h)
    if os.path.isdir(d) and mn not in sys.modules:
        m = types.ModuleType(mn)
        m.__path__ = [d]
        m.__package__ = mn
        sys.modules[mn] = m

from services.worker_http.worker import HttpWorker
from packages.core.ai_providers.deterministic import DeterministicProvider

CDP_URL = "http://127.0.0.1:9222"

TESTS = [
    # (name, url, category)
    ("Shopify: Allbirds", "https://www.allbirds.com/collections/mens", "ecommerce"),
    ("Shopify: ColourPop", "https://colourpop.com/collections/all", "ecommerce"),
    ("Shopify: Gymshark", "https://www.gymshark.com/collections/all", "ecommerce"),
    ("WooCommerce", "https://developer.woocommerce.com/", "ecommerce"),
    ("Google Play", "https://play.google.com/store/apps/details?id=com.whatsapp", "ecommerce"),
    ("Google Shopping", "https://shopping.google.com/search?q=laptop", "ecommerce"),
    ("eBay Search UK", "https://www.ebay.co.uk/sch/i.html?_nkw=rtx+4070", "marketplace"),
    ("eBay Search US", "https://www.ebay.com/sch/i.html?_nkw=iphone+15", "marketplace"),
    ("Kickstarter", "https://www.kickstarter.com/discover/advanced?sort=magic", "marketplace"),
    ("Alibaba", "https://www.alibaba.com/products/laptop.html", "marketplace"),
    ("Etsy", "https://www.etsy.com/search?q=handmade+jewelry", "marketplace"),
    ("Trustpilot Amazon", "https://www.trustpilot.com/review/amazon.com", "reviews"),
    ("Trustpilot Gymshark", "https://www.trustpilot.com/review/gymshark.com", "reviews"),
    ("YouTube Video", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "videos"),
    ("YouTube Search", "https://www.youtube.com/results?search_query=python", "videos"),
    ("YouTube Channel", "https://www.youtube.com/@MrBeast", "videos"),
    ("YouTube Trending", "https://www.youtube.com/feed/trending", "videos"),
    ("Books Toscrape", "https://books.toscrape.com/", "test_site"),
    ("Quotes Toscrape", "https://quotes.toscrape.com/", "test_site"),
    ("Hacker News", "https://news.ycombinator.com/", "news"),
    ("BBC News", "https://www.bbc.co.uk/news", "news"),
    ("GitHub Trending", "https://github.com/trending", "dev"),
    ("Wikipedia", "https://en.wikipedia.org/wiki/Web_scraping", "content"),
    ("Amazon UK", "https://www.amazon.co.uk/dp/B0D1XD1ZV3", "ecommerce"),
    ("Amazon US", "https://www.amazon.com/dp/B09V3KXJPB", "ecommerce"),
    ("Walmart", "https://www.walmart.com/browse/electronics/tvs/3944_1060825_447913", "ecommerce"),
    ("Target", "https://www.target.com/", "ecommerce"),
    ("Reddit", "https://old.reddit.com/r/technology/", "content"),
    ("TikTok Profile", "https://www.tiktok.com/@khaby.lame", "social"),
    ("Instagram Profile", "https://www.instagram.com/cristiano/", "social"),
]

results = []


async def test_http(name, url):
    w = HttpWorker()
    try:
        r = await w.process_task({"url": url, "tenant_id": "test"})
        items = r.get("extracted_data", [])
        count = len(items) if isinstance(items, list) else 0
        if count > 0:
            sample = items[0] if items else {}
            fields = list(sample.keys())[:4] if isinstance(sample, dict) else []
            return "PASS", count, ", ".join(fields), "http"
        return "EMPTY", 0, f"code={r.get('status_code', '?')}", "http"
    except Exception as e:
        return "ERROR", 0, str(e)[:50], "http"


async def test_browser(name, url):
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp(CDP_URL)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            await page.wait_for_timeout(5000)

        html = await page.content()
        await page.close()
        await pw.stop()

        provider = DeterministicProvider()
        items = await provider.extract(html, url)
        count = len(items) if isinstance(items, list) else 0
        if count > 0:
            sample = items[0] if items else {}
            fields = list(sample.keys())[:4] if isinstance(sample, dict) else []
            return "PASS", count, ", ".join(fields), "browser"

        from packages.core.markdown_converter import MarkdownConverter
        converter = MarkdownConverter()
        result = converter.convert(html, url, output_format="markdown")
        if result.content and len(result.content) > 100:
            return "PASS", 1, f"article: {(result.title or 'untitled')[:30]}", "browser+trafilatura"

        return "EMPTY", 0, "no data after render", "browser"
    except Exception as e:
        try:
            await pw.stop()
        except Exception:
            pass
        return "ERROR", 0, str(e)[:50], "browser"


async def main():
    for i, (name, url, cat) in enumerate(TESTS, 1):
        print(f"[{i:2d}/{len(TESTS)}] {name}...", end=" ", flush=True)

        # Try HTTP first
        status, count, info, lane = await test_http(name, url)

        # If HTTP failed, try browser
        if status != "PASS":
            print(f"HTTP={status}, trying browser...", end=" ", flush=True)
            status, count, info, lane = await test_browser(name, url)

        results.append({
            "name": name,
            "url": url,
            "category": cat,
            "status": status,
            "items": count,
            "fields": info,
            "lane": lane,
        })
        print(f"{status} ({count} items via {lane})")

    # Summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    print(f"\n{'='*60}")
    print(f"TOTAL: {passed}/{len(results)} PASS")
    print(f"{'='*60}")
    for r in results:
        s = r["status"]
        marker = "OK" if s == "PASS" else "XX"
        print(f"  [{marker}] {r['name']:25s} | {r['items']:3d} | {r['lane']:20s} | {r['fields'][:40]}")

    # Save
    with open("all_templates_browser_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to all_templates_browser_results.json")


if __name__ == "__main__":
    asyncio.run(main())
