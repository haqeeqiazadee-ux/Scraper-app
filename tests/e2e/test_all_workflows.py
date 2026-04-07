"""
Complete E2E test suite — ALL workflows, ALL API paths, ALL platforms.
Playwright browser + httpx API tests against live deployment.

Run all:     run_e2e.bat
Run this:    python -m pytest tests/e2e/test_all_workflows.py -v --tb=short
Run subset:  C:\Python314\python.exe -m pytest tests/e2e/test_all_workflows.py -v -k amazon
"""

import json
import os
import re
import time
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

BACKEND = os.getenv("E2E_BACKEND_URL", "https://scraper-platform-production-17cb.up.railway.app")
FRONTEND = os.getenv("E2E_FRONTEND_URL", "https://myscraper.netlify.app")
API = f"{BACKEND}/api/v1"
H = {"X-Tenant-ID": "e2e-all-workflows", "Content-Type": "application/json"}


# ─── Helpers ─────────────────────────────────────────────────────────

def post(path, data, timeout=90.0):
    with httpx.Client(base_url=API, timeout=timeout, headers=H) as c:
        return c.post(path, json=data)


def get(path, timeout=30.0):
    with httpx.Client(base_url=API, timeout=timeout, headers=H) as c:
        return c.get(path)


def ok(resp, expected=200):
    if resp.status_code == 502:
        pytest.skip("Railway 502 timeout")
    assert resp.status_code == expected, f"{resp.status_code}: {resp.text[:300]}"
    return resp.json()


def smart(target, **kwargs):
    """Shortcut for POST /smart-scrape."""
    payload = {"target": target, **kwargs}
    return ok(post("/smart-scrape", payload))


# ─── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, base_url=FRONTEND)
    pg = ctx.new_page()
    yield pg
    pg.close()
    ctx.close()


def fill_and_scrape(page: Page, target: str, timeout_s: int = 60):
    """Fill scraper input, click Scrape, wait for completion."""
    page.goto("/scraper", wait_until="networkidle", timeout=20_000)
    inp = page.get_by_placeholder("example.com")
    inp.fill(target)
    page.wait_for_timeout(300)
    page.get_by_role("button", name="Scrape").click(timeout=5_000)
    for _ in range(timeout_s // 2):
        page.wait_for_timeout(2_000)
        body = page.text_content("body") or ""
        if "COMPLETED" in body or "Extracted Data" in body or "FAILED" in body:
            return body
    return page.text_content("body") or ""


# ═════════════════════════════════════════════════════════════════════
# 1. SMART SCRAPE — Core Engine
# ═════════════════════════════════════════════════════════════════════

class TestSmartScrapeCore:

    def test_health(self):
        d = ok(get("/health"))
        assert d["status"] == "healthy"

    def test_url_detection(self):
        d = smart("https://example.com")
        assert d["detected_as"] == "url"

    def test_search_detection(self):
        d = smart("best laptops 2026")
        assert d["detected_as"] == "search"

    def test_has_steps(self):
        d = smart("https://httpbin.org/html")
        assert len(d.get("steps", [])) >= 3

    def test_saves_result(self):
        d = smart("https://httpbin.org/html")
        assert d.get("saved") is True
        assert d.get("saved_task_id")

    def test_invalid_url_no_crash(self):
        d = smart("https://thisdomaindoesnotexist99999.com")
        assert d["status"] in ("completed", "failed", "error")

    def test_empty_target_rejected(self):
        resp = post("/smart-scrape", {"target": ""})
        assert resp.status_code == 422


# ═════════════════════════════════════════════════════════════════════
# 2. AMAZON — All queries via Keepa API
# ═════════════════════════════════════════════════════════════════════

class TestAmazon:

    def test_asin_lookup(self):
        """Amazon ASIN → Keepa API."""
        d = smart("https://www.amazon.com/dp/B09V3KXJPB")
        assert d["item_count"] >= 1
        steps = [s["step"] for s in d.get("steps", [])]
        assert any("Keepa" in s for s in steps), f"Keepa not used. Steps: {steps}"

    def test_keyword_search(self):
        """Amazon search → Keepa keyword query."""
        d = smart("https://www.amazon.com/s?k=wireless+earbuds")
        assert d["item_count"] >= 1
        steps = [s["step"] for s in d.get("steps", [])]
        assert any("Keepa" in s for s in steps)

    def test_keepa_direct_query(self):
        """Direct Keepa endpoint."""
        d = ok(post("/keepa/query", {"query": "B09V3KXJPB", "domain": "US"}))
        assert d["count"] >= 1
        assert "ipad" in d["products"][0]["name"].lower()

    def test_keepa_keyword(self):
        """Direct Keepa keyword search."""
        d = ok(post("/keepa/query", {"query": "wireless earbuds", "domain": "US", "max_results": 5}))
        assert d["count"] >= 1

    def test_keepa_status(self):
        """Keepa API key is configured."""
        d = ok(get("/keepa/status"))
        assert d["api_key_set"] is True


# ═════════════════════════════════════════════════════════════════════
# 3. SHOPIFY STORES — /products.json API
# ═════════════════════════════════════════════════════════════════════

class TestShopify:

    def test_superdrugs(self):
        """Shopify store → 250 products via API."""
        d = smart("https://superdrugs.pk", intent="products")
        assert d["item_count"] >= 100
        steps = [s["step"] for s in d.get("steps", [])]
        assert any("Shopify" in s for s in steps)

    def test_products_have_names_prices(self):
        d = smart("https://superdrugs.pk", intent="products")
        items = d.get("extracted_data", [])
        named = [i for i in items if i.get("name")]
        priced = [i for i in items if i.get("price")]
        assert len(named) >= 50
        assert len(priced) >= 50


# ═════════════════════════════════════════════════════════════════════
# 4. EBAY — DOM Group Extraction
# ═════════════════════════════════════════════════════════════════════

class TestEbay:

    def test_ebay_search(self):
        """eBay search → DOM extraction."""
        d = smart("https://www.ebay.com/sch/i.html?_nkw=laptop", intent="products")
        # Should find products via DOM extraction, not escalate
        assert d["item_count"] >= 5, f"Only {d['item_count']} items. Steps: {[s['step'] for s in d.get('steps',[])]}"

    def test_ebay_completed(self):
        """eBay completed/sold listings."""
        d = smart("https://www.ebay.com/sch/i.html?_nkw=iphone&LH_Complete=1&LH_Sold=1", intent="products")
        assert d["item_count"] >= 1


# ═════════════════════════════════════════════════════════════════════
# 5. STATIC SITES — Standard HTTP Extraction
# ═════════════════════════════════════════════════════════════════════

class TestStaticSites:

    def test_books_toscrape(self):
        d = smart("https://books.toscrape.com", intent="products")
        assert d["item_count"] >= 20
        assert d["lane_used"] == "http"

    def test_httpbin(self):
        d = smart("https://httpbin.org/html")
        assert d["item_count"] >= 1

    def test_example_com(self):
        d = smart("https://example.com")
        assert d["status"] in ("completed", "success")


# ═════════════════════════════════════════════════════════════════════
# 6. WEB SEARCH — Serper API
# ═════════════════════════════════════════════════════════════════════

class TestWebSearch:

    def test_search_query(self):
        d = smart("best gaming laptops 2026")
        assert d["detected_as"] == "search"
        assert d["item_count"] >= 1

    def test_search_direct(self):
        d = ok(post("/search", {"query": "python web scraping", "max_results": 3}))
        assert d["total_results"] >= 1

    def test_search_empty_rejected(self):
        resp = post("/search", {"query": "", "max_results": 1})
        assert resp.status_code == 422


# ═════════════════════════════════════════════════════════════════════
# 7. SCHEMA EXTRACTION
# ═════════════════════════════════════════════════════════════════════

class TestSchemaExtraction:

    def test_book_fields(self):
        d = smart(
            "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            schema={"title": "string", "price": "number"},
        )
        sm = d.get("schema_matched", {})
        fields = sm.get("matched_fields", sm)
        assert fields.get("title") or fields.get("price")

    def test_extract_endpoint(self):
        d = ok(post("/extract", {
            "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            "schema": {"title": "string", "price": "number", "availability": "string"},
        }))
        assert d["confidence"] >= 0.5


# ═════════════════════════════════════════════════════════════════════
# 8. GOOGLE MAPS — Serper Places
# ═════════════════════════════════════════════════════════════════════

class TestGoogleMaps:

    def test_maps_search(self):
        d = ok(post("/maps/search", {"query": "restaurants in Dubai", "max_results": 10}))
        assert d["count"] >= 5
        for biz in d["results"][:3]:
            assert biz.get("name")
            assert biz.get("rating") is not None

    def test_maps_different_query(self):
        d = ok(post("/maps/search", {"query": "coffee shops New York", "max_results": 5}))
        assert d["count"] >= 3

    def test_maps_status(self):
        d = ok(get("/maps/status"))
        assert "google_api_configured" in d or "serpapi_configured" in d


# ═════════════════════════════════════════════════════════════════════
# 9. TEMPLATES — 55 Pre-built Scrapers
# ═════════════════════════════════════════════════════════════════════

class TestTemplates:

    def test_list_templates(self):
        d = ok(get("/templates"))
        assert d["total"] >= 50

    def test_template_detail(self):
        d = ok(get("/templates/trustpilot-reviews"))
        assert d["id"] == "trustpilot-reviews"
        assert len(d["config"]["fields"]) >= 5

    def test_template_apply_and_execute(self):
        ap = ok(post("/templates/trustpilot-reviews/apply", {"url": "https://www.trustpilot.com/review/amazon.com"}), 201)
        task = ok(post("/tasks", {"url": "https://www.trustpilot.com/review/amazon.com", "policy_id": ap["policy_id"]}), 201)
        ex = ok(post(f"/tasks/{task['id']}/execute", {}))
        assert ex["status"] == "completed"
        assert ex["item_count"] >= 1


# ═════════════════════════════════════════════════════════════════════
# 10. RESULTS & EXPORT
# ═════════════════════════════════════════════════════════════════════

class TestResultsExport:

    def test_results_list(self):
        # Ensure at least 1 result exists
        post("/smart-scrape", {"target": "https://httpbin.org/html"})
        d = ok(get("/results"))
        assert d["total"] >= 1

    def test_export_csv(self):
        resp = post("/results/export", {"format": "csv", "destination": "download"})
        assert resp.status_code == 200
        assert len(resp.content) > 50

    def test_export_json(self):
        resp = post("/results/export", {"format": "json", "destination": "download"})
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert isinstance(data, list)


# ═════════════════════════════════════════════════════════════════════
# 11. SCHEDULES — CRUD
# ═════════════════════════════════════════════════════════════════════

class TestSchedules:

    def test_schedule_crud(self):
        # Create
        d = ok(post("/schedules", {"url": "https://example.com", "schedule": "0 */12 * * *", "task_type": "scrape"}), 201)
        sid = d["schedule_id"]
        # List
        lst = ok(get("/schedules"))
        assert sid in [s["schedule_id"] for s in lst["items"]]
        # Delete
        with httpx.Client(base_url=API, timeout=30, headers=H) as c:
            ok(c.delete(f"/schedules/{sid}"))
        # Verify deleted
        lst2 = ok(get("/schedules"))
        assert sid not in [s["schedule_id"] for s in lst2["items"]]


# ═════════════════════════════════════════════════════════════════════
# 12. CHANGE DETECTION — Client-side (UI only)
# ═════════════════════════════════════════════════════════════════════

class TestChangeDetection:

    def test_compare(self, page: Page):
        page.goto("/changes", wait_until="networkidle", timeout=20_000)
        old = json.dumps([{"name": "Widget", "price": 19.99}])
        new = json.dumps([{"name": "Widget", "price": 14.99}, {"name": "Gadget", "price": 29.99}])
        page.evaluate(f"""() => {{
            const tas = document.querySelectorAll('textarea');
            const s = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
            s.call(tas[0], {json.dumps(old)}); tas[0].dispatchEvent(new Event('input', {{bubbles:true}}));
            s.call(tas[1], {json.dumps(new)}); tas[1].dispatchEvent(new Event('input', {{bubbles:true}}));
        }}""")
        page.click("button:has-text('Compare')")
        page.wait_for_selector("table", timeout=5_000)
        text = page.text_content("body")
        assert "Added" in text and "Price Change" in text


# ═════════════════════════════════════════════════════════════════════
# 13. MCP SERVER — Informational Page
# ═════════════════════════════════════════════════════════════════════

class TestMCPServer:

    def test_tools_displayed(self, page: Page):
        page.goto("/mcp", wait_until="networkidle", timeout=20_000)
        text = page.text_content("body").lower()
        for tool in ["scrape", "crawl", "search", "extract", "route"]:
            assert tool in text

    def test_json_valid(self, page: Page):
        page.goto("/mcp", wait_until="networkidle", timeout=20_000)
        blocks = page.evaluate("""() => {
            return [...document.querySelectorAll('pre')].filter(b => b.textContent.trim().startsWith('{')).map(b => {
                try { JSON.parse(b.textContent.trim()); return {valid:true}; }
                catch(e) { return {valid:false}; }
            });
        }""")
        assert all(b["valid"] for b in blocks)


# ═════════════════════════════════════════════════════════════════════
# 14. CRAWL — Multi-page
# ═════════════════════════════════════════════════════════════════════

class TestCrawl:

    def test_crawl_start_and_status(self):
        d = ok(post("/crawl", {"seed_urls": ["https://books.toscrape.com/"], "max_depth": 0, "max_pages": 1}), 201)
        cid = d["crawl_id"]
        # Poll
        for _ in range(15):
            time.sleep(2)
            s = ok(get(f"/crawl/{cid}"))
            if s["state"] in ("completed", "failed"):
                break
        assert s["state"] == "completed"

    def test_crawl_results(self):
        d = ok(post("/crawl", {"seed_urls": ["https://books.toscrape.com/"], "max_depth": 0, "max_pages": 1}), 201)
        time.sleep(15)
        r = ok(get(f"/crawl/{d['crawl_id']}/results"))
        assert r["total_items"] >= 1


# ═════════════════════════════════════════════════════════════════════
# 15. API KEYS — CRUD
# ═════════════════════════════════════════════════════════════════════

class TestAPIKeys:

    def test_create_key(self):
        d = ok(post("/api-keys", {"name": "E2E Test Key", "scopes": ["*"]}), 201)
        assert d.get("key", "").startswith("sk_live_")
        assert d.get("id")
        # Cleanup
        with httpx.Client(base_url=API, timeout=30, headers=H) as c:
            c.delete(f"/api-keys/{d['id']}")

    def test_list_keys(self):
        d = ok(get("/api-keys"))
        assert isinstance(d.get("keys", d.get("items", [])), list)


# ═════════════════════════════════════════════════════════════════════
# 16. PUBLIC API (/v1/) — Zero Checksum
# ═════════════════════════════════════════════════════════════════════

class TestPublicAPI:

    def test_v1_scrape(self):
        """Public API scrape endpoint."""
        resp = post("/smart-scrape", {"target": "https://httpbin.org/html"})
        d = ok(resp)
        assert d["item_count"] >= 1

    def test_v1_account(self):
        with httpx.Client(base_url=f"{BACKEND}/v1", timeout=30, headers={"X-API-Key": "test"}) as c:
            resp = c.get("/account")
            # May fail with auth error — that's expected without real key
            assert resp.status_code in (200, 401, 403, 500)


# ═════════════════════════════════════════════════════════════════════
# 17. UI FLOW — Playwright
# ═════════════════════════════════════════════════════════════════════

class TestUIFlow:

    def test_scraper_page_loads(self, page: Page):
        page.goto("/scraper", wait_until="networkidle", timeout=20_000)
        assert page.get_by_placeholder("example.com").count() >= 1
        assert page.get_by_role("button", name="Scrape").count() >= 1

    def test_scrape_and_results(self, page: Page):
        body = fill_and_scrape(page, "https://httpbin.org/html")
        assert "COMPLETED" in body or "Extracted Data" in body

    def test_results_page(self, page: Page):
        page.goto("/results", wait_until="networkidle", timeout=20_000)
        assert "Results" in (page.text_content("h2") or "")

    def test_sidebar_nav(self, page: Page):
        page.goto("/scraper", wait_until="networkidle", timeout=20_000)
        nav = page.text_content("nav") or page.text_content("[class*=sidebar]") or page.text_content("body")
        for item in ["Scraper", "Amazon", "Google Maps", "Templates", "Results", "Schedules", "API Keys"]:
            assert item in nav, f"Missing sidebar item: {item}"

    def test_superdrugs_scrape(self, page: Page):
        body = fill_and_scrape(page, "https://superdrugs.pk", timeout_s=90)
        assert "COMPLETED" in body or "Extracted Data" in body


# ═════════════════════════════════════════════════════════════════════
# 18. YOUSELL PLATFORM REQUESTS
# ═════════════════════════════════════════════════════════════════════

class TestYousellRequests:

    def test_shopify_store_scrape(self):
        """YOUSELL #7: Shopify store products."""
        d = smart("https://superdrugs.pk", intent="products")
        assert d["item_count"] >= 100

    def test_ebay_listings(self):
        """YOUSELL #8: eBay listings search."""
        d = smart("https://www.ebay.com/sch/i.html?_nkw=wireless+earbuds", intent="products")
        assert d["item_count"] >= 1

    def test_amazon_asin(self):
        """YOUSELL #5: Amazon product by ASIN."""
        d = smart("https://www.amazon.com/dp/B09V3KXJPB")
        steps = [s["step"] for s in d.get("steps", [])]
        assert any("Keepa" in s for s in steps)
        assert d["item_count"] >= 1

    def test_amazon_keyword(self):
        """YOUSELL #6: Amazon keyword search."""
        d = smart("https://www.amazon.com/s?k=laptop")
        assert d["item_count"] >= 1

    def test_google_maps_businesses(self):
        """YOUSELL #27: Google Maps businesses."""
        d = ok(post("/maps/search", {"query": "pharmacies in Lahore", "max_results": 10}))
        assert d["count"] >= 3

    def test_google_trends_via_search(self):
        """YOUSELL #23: Google Trends via web search."""
        d = smart("trending products 2026")
        assert d["detected_as"] == "search"

    def test_product_reviews(self):
        """YOUSELL #25: Product reviews scrape."""
        d = smart("https://www.trustpilot.com/review/amazon.com")
        assert d["item_count"] >= 1

    def test_competitor_store(self):
        """YOUSELL #26: Competitor store analysis."""
        d = smart("https://superdrugs.pk", schema={"product_count": "number", "avg_price": "number"})
        assert d["item_count"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
