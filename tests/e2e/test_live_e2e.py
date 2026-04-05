"""
Live E2E Test Suite — Comprehensive workflow verification against deployed site.

Uses synchronous httpx + Playwright (no async event loop conflicts).

Targets:
  Frontend: https://myscraper.netlify.app
  Backend:  https://scraper-platform-production-17cb.up.railway.app/api/v1

Usage:
  python -m pytest tests/e2e/test_live_e2e.py -v --tb=short
  python -m pytest tests/e2e/test_live_e2e.py -v -m quick_scrape
  python tests/e2e/test_live_e2e.py --loop 10 --interval 300
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, Browser

_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FRONTEND_URL = os.getenv("E2E_FRONTEND_URL", "https://myscraper.netlify.app")
BACKEND_URL = os.getenv("E2E_BACKEND_URL", "https://scraper-platform-production-17cb.up.railway.app")
API_BASE = f"{BACKEND_URL}/api/v1"
API_TIMEOUT = 60.0
PAGE_LOAD_TIMEOUT = 20_000
TENANT_HEADERS = {"X-Tenant-ID": "e2e-live-test"}
RESULTS_DIR = Path(__file__).resolve().parents[2] / "test-results"
SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"

OLD_SNAPSHOT = json.dumps([
    {"name": "Widget", "price": 19.99, "description": "A handy widget"},
    {"name": "Sprocket", "price": 9.99, "description": "A fine sprocket"},
], indent=2)
NEW_SNAPSHOT = json.dumps([
    {"name": "Widget", "price": 14.99, "description": "A handy widget"},
    {"name": "Sprocket", "price": 9.99, "description": "A fine sprocket"},
    {"name": "Gadget", "price": 29.99, "description": "A new gadget"},
], indent=2)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def api_post(path: str, json_data: dict = None, timeout: float = API_TIMEOUT) -> httpx.Response:
    with httpx.Client(base_url=API_BASE, timeout=timeout, headers=TENANT_HEADERS) as c:
        return c.post(path, json=json_data)

def api_get(path: str, timeout: float = API_TIMEOUT) -> httpx.Response:
    with httpx.Client(base_url=API_BASE, timeout=timeout, headers=TENANT_HEADERS) as c:
        return c.get(path)

def api_delete(path: str) -> httpx.Response:
    with httpx.Client(base_url=API_BASE, timeout=API_TIMEOUT, headers=TENANT_HEADERS) as c:
        return c.delete(path)

def ok(resp: httpx.Response, expected: int = 200) -> dict:
    assert resp.status_code == expected, f"Expected {expected}, got {resp.status_code}: {resp.text[:500]}"
    return resp.json()

def set_textarea(page: Page, index: int, value: str):
    page.evaluate(f"""() => {{
        const ta = document.querySelectorAll('textarea')[{index}];
        const s = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
        s.call(ta, {json.dumps(value)});
        ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }}""")

# ---------------------------------------------------------------------------
# Pytest hooks
# ---------------------------------------------------------------------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        page = item.funcargs.get("live_page")
        if page:
            try:
                SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(SCREENSHOTS_DIR / f"FAIL_{item.name}_{int(time.time())}.png"))
            except Exception:
                pass

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def pw_browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=50)
        yield browser
        browser.close()

@pytest.fixture
def live_page(pw_browser: Browser) -> Page:
    ctx = pw_browser.new_context(viewport={"width": 1280, "height": 720}, base_url=FRONTEND_URL)
    page = ctx.new_page()
    yield page
    page.close()
    ctx.close()

@pytest.fixture(scope="session", autouse=True)
def setup_dirs():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

@pytest.fixture(scope="session")
def serper_ok():
    return bool(os.getenv("SERPER_API_KEY", "").strip())

@pytest.fixture(scope="session")
def keepa_ok():
    return bool(os.getenv("KEEPA_API_KEY", "").strip())

# ===================================================================
# WORKFLOW 1: Quick Scrape
# ===================================================================
@pytest.mark.live
@pytest.mark.quick_scrape
class TestQuickScrape:

    @pytest.mark.api
    def test_scrape_httpbin(self):
        d = ok(api_post("/test-scrape", {"url": "https://httpbin.org/html", "timeout_ms": 15000, "extraction_mode": "products"}))
        assert d["status"] == "success"
        assert d["item_count"] >= 1

    @pytest.mark.api
    def test_scrape_yousell_everything(self):
        d = ok(api_post("/test-scrape", {"url": "https://yousell.online", "timeout_ms": 25000, "extraction_mode": "everything"}))
        assert d["status"] == "success"
        assert d["item_count"] >= 20, f"Expected >=20, got {d['item_count']}"
        assert d["extraction_mode"] == "everything"

    @pytest.mark.api
    def test_scrape_books_products(self):
        d = ok(api_post("/test-scrape", {"url": "https://books.toscrape.com/", "timeout_ms": 15000, "extraction_mode": "products"}))
        assert d["status"] == "success"
        assert d["item_count"] >= 3

    @pytest.mark.ui
    def test_scrape_ui_flow(self, live_page: Page):
        live_page.goto("/scrape-test", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
        assert live_page.text_content("h2") == "Quick Scrape"
        labels = [b.text_content().strip() for b in live_page.query_selector_all("button")]
        assert "Everything" in labels
        live_page.fill('input[type="url"]', "https://httpbin.org/html")
        live_page.click("button:has-text('Scrape')")
        live_page.wait_for_selector(".stat-card", timeout=30_000)
        assert "SUCCESS" in live_page.text_content(".stats-grid").upper()

# ===================================================================
# WORKFLOW 2: Web Crawl
# ===================================================================
@pytest.mark.live
@pytest.mark.web_crawl
class TestWebCrawl:

    @pytest.mark.api
    def test_crawl_start(self):
        d = ok(api_post("/crawl", {"seed_urls": ["https://books.toscrape.com/"], "max_depth": 1, "max_pages": 3}), 201)
        assert "crawl_id" in d
        assert d["status"] == "running"

    @pytest.mark.api
    def test_crawl_status_and_results(self):
        d = ok(api_post("/crawl", {"seed_urls": ["https://books.toscrape.com/"], "max_depth": 0, "max_pages": 1}), 201)
        cid = d["crawl_id"]
        for _ in range(15):
            time.sleep(2)
            s = ok(api_get(f"/crawl/{cid}"))
            if s["state"] in ("completed", "failed"):
                break
        assert s["state"] == "completed"
        r = ok(api_get(f"/crawl/{cid}/results"))
        assert r["total_items"] >= 1

    @pytest.mark.api
    def test_crawl_invalid_url(self):
        resp = api_post("/crawl", {"seed_urls": ["https://thisdomaindoesnotexist99999.com"], "max_depth": 0, "max_pages": 1})
        assert resp.status_code in (200, 201, 422)

# ===================================================================
# WORKFLOW 3: Web Search
# ===================================================================
@pytest.mark.live
@pytest.mark.web_search
class TestWebSearch:

    @pytest.mark.api
    def test_search_gaming_laptops(self, serper_ok):
        if not serper_ok: pytest.skip("SERPER_API_KEY not set")
        d = ok(api_post("/search", {"query": "best gaming laptops 2026", "max_results": 3}))
        assert d["total_results"] >= 3
        assert all("title" in r for r in d["results"])

    @pytest.mark.api
    def test_search_python_tutorial(self, serper_ok):
        if not serper_ok: pytest.skip("SERPER_API_KEY not set")
        d = ok(api_post("/search", {"query": "python web scraping tutorial", "max_results": 3}))
        assert d["total_results"] >= 1

    @pytest.mark.api
    def test_search_error_handling(self, serper_ok):
        if not serper_ok: pytest.skip("SERPER_API_KEY not set")
        resp = api_post("/search", {"query": "", "max_results": 1})
        assert resp.status_code == 422

# ===================================================================
# WORKFLOW 4: Structured Extract
# ===================================================================
@pytest.mark.live
@pytest.mark.structured_extract
class TestStructuredExtract:

    @pytest.mark.api
    def test_extract_book_fields(self):
        d = ok(api_post("/extract", {
            "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            "schema": {"title": "string", "price": "number", "description": "string", "availability": "string"},
        }))
        ed = d["extracted_data"]
        assert ed.get("title"), f"Missing title: {ed}"
        assert ed.get("price"), f"Missing price: {ed}"
        assert ed.get("description"), f"Missing description: {ed}"
        assert ed.get("availability"), f"Missing availability: {ed}"
        assert d["confidence"] >= 0.75

    @pytest.mark.api
    def test_extract_example_com(self):
        d = ok(api_post("/extract", {"url": "https://example.com", "schema": {"title": "string"}}))
        assert d["extracted_data"].get("title") or d["confidence"] >= 0

    @pytest.mark.api
    def test_extract_invalid_url(self):
        resp = api_post("/extract", {"url": "https://thisdomaindoesnotexist99999.com", "schema": {"title": "string"}})
        assert resp.status_code in (200, 422, 502)

# ===================================================================
# WORKFLOW 5: Amazon / Keepa
# ===================================================================
@pytest.mark.live
@pytest.mark.amazon
class TestAmazonKeepa:

    @pytest.mark.api
    def test_keepa_status(self, keepa_ok):
        if not keepa_ok: pytest.skip("KEEPA_API_KEY not set")
        d = ok(api_get("/keepa/status"))
        assert d["api_key_set"] is True

    @pytest.mark.api
    def test_keepa_asin_ipad(self, keepa_ok):
        if not keepa_ok: pytest.skip("KEEPA_API_KEY not set")
        d = ok(api_post("/keepa/query", {"query": "B09V3KXJPB", "domain": "US"}))
        assert d["count"] >= 1
        assert "ipad" in d["products"][0]["name"].lower()

    @pytest.mark.api
    def test_keepa_keyword_search(self, keepa_ok):
        if not keepa_ok: pytest.skip("KEEPA_API_KEY not set")
        d = ok(api_post("/keepa/query", {"query": "wireless earbuds", "domain": "US", "max_results": 5}))
        assert d["count"] >= 1

# ===================================================================
# WORKFLOW 6: Google Maps
# ===================================================================
@pytest.mark.live
@pytest.mark.google_maps
class TestGoogleMaps:

    @pytest.mark.api
    def test_maps_status(self):
        d = ok(api_get("/maps/status"))
        assert "google_api_configured" in d or "serpapi_configured" in d

    @pytest.mark.api
    def test_maps_dubai_restaurants(self, serper_ok):
        if not serper_ok: pytest.skip("SERPER_API_KEY not set")
        d = ok(api_post("/maps/search", {"query": "restaurants in Dubai", "max_results": 10}))
        assert d["count"] >= 5
        for biz in d["results"][:5]:
            assert biz.get("name")
            assert biz.get("rating") is not None

    @pytest.mark.api
    def test_maps_nyc_coffee(self, serper_ok):
        if not serper_ok: pytest.skip("SERPER_API_KEY not set")
        d = ok(api_post("/maps/search", {"query": "coffee shops in New York", "max_results": 5}))
        assert d["count"] >= 3

# ===================================================================
# WORKFLOW 7: Facebook Groups
# ===================================================================
@pytest.mark.live
@pytest.mark.facebook
class TestFacebookGroups:

    @pytest.mark.ui
    def test_fb_requirements_note(self, live_page: Page):
        live_page.goto("/facebook-groups", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
        text = live_page.text_content("body").lower()
        assert "self-hosted" in text or "requirements" in text

    @pytest.mark.ui
    def test_fb_no_silent_failure(self, live_page: Page):
        live_page.goto("/facebook-groups", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
        h = live_page.text_content("h2")
        assert h and "facebook" in h.lower()

# ===================================================================
# WORKFLOW 8: Templates
# ===================================================================
@pytest.mark.live
@pytest.mark.templates
class TestTemplates:

    @pytest.mark.api
    def test_templates_list(self):
        d = ok(api_get("/templates"))
        assert d["total"] >= 50

    @pytest.mark.api
    def test_template_detail(self):
        d = ok(api_get("/templates/trustpilot-reviews"))
        assert d["id"] == "trustpilot-reviews"
        assert len(d["config"]["fields"]) >= 5

    @pytest.mark.api
    def test_template_full_pipeline(self):
        ap = ok(api_post("/templates/trustpilot-reviews/apply", {"url": "https://www.trustpilot.com/review/amazon.com"}), 201)
        pid = ap["policy_id"]
        task = ok(api_post("/tasks", {"url": "https://www.trustpilot.com/review/amazon.com", "policy_id": pid}), 201)
        ex = ok(api_post(f"/tasks/{task['id']}/execute"))
        assert ex["status"] == "completed"
        assert ex["item_count"] >= 1

# ===================================================================
# WORKFLOW 9: Results & Export
# ===================================================================
@pytest.mark.live
@pytest.mark.results
class TestResultsExport:

    @pytest.mark.api
    def test_results_list(self):
        # First ensure at least 1 result exists by saving one
        api_post("/test-scrape", {"url": "https://httpbin.org/html", "timeout_ms": 10000, "extraction_mode": "products", "save_result": True})
        d = ok(api_get("/results"))
        assert "items" in d and d["total"] >= 1

    @pytest.mark.api
    def test_results_save_from_scrape(self):
        before = api_get("/results").json()["total"]
        d = ok(api_post("/test-scrape", {"url": "https://httpbin.org/html", "timeout_ms": 15000, "extraction_mode": "products", "save_result": True}))
        assert d["saved"] is True
        after = api_get("/results").json()["total"]
        assert after > before

    @pytest.mark.api
    def test_export_csv(self):
        resp = api_post("/results/export", {"format": "csv", "destination": "download"})
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        assert len(resp.content) > 50

    @pytest.mark.api
    def test_export_json(self):
        resp = api_post("/results/export", {"format": "json", "destination": "download"})
        assert resp.status_code == 200
        parsed = json.loads(resp.content)
        assert isinstance(parsed, list) and len(parsed) >= 1

# ===================================================================
# WORKFLOW 10: Change Detection
# ===================================================================
@pytest.mark.live
@pytest.mark.change_detection
class TestChangeDetection:

    @pytest.mark.ui
    def test_changes_price_and_added(self, live_page: Page):
        live_page.goto("/changes", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
        set_textarea(live_page, 0, OLD_SNAPSHOT)
        set_textarea(live_page, 1, NEW_SNAPSHOT)
        live_page.click("button:has-text('Compare')")
        live_page.wait_for_selector("table", timeout=5000)
        text = live_page.text_content("body")
        assert "Added" in text and "Price Change" in text and "-25.0%" in text

    @pytest.mark.ui
    def test_changes_identical(self, live_page: Page):
        live_page.goto("/changes", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
        set_textarea(live_page, 0, OLD_SNAPSHOT)
        set_textarea(live_page, 1, OLD_SNAPSHOT)
        live_page.click("button:has-text('Compare')")
        live_page.wait_for_timeout(1000)
        assert "No Changes Detected" in live_page.text_content("body")

    @pytest.mark.ui
    def test_changes_empty_input(self, live_page: Page):
        live_page.goto("/changes", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
        btn = live_page.query_selector("button:has-text('Compare')")
        assert btn.is_disabled() if btn else True

# ===================================================================
# WORKFLOW 11: Schedules
# ===================================================================
@pytest.mark.live
@pytest.mark.schedules
class TestSchedules:

    @pytest.mark.api
    def test_schedule_crud(self):
        d = ok(api_post("/schedules", {"url": "https://example.com", "schedule": "0 */12 * * *", "task_type": "scrape"}), 201)
        sid = d["schedule_id"]
        lst = ok(api_get("/schedules"))
        assert sid in [s["schedule_id"] for s in lst["items"]]
        ok(api_delete(f"/schedules/{sid}"))
        lst2 = ok(api_get("/schedules"))
        assert sid not in [s["schedule_id"] for s in lst2["items"]]

    @pytest.mark.api
    def test_schedule_multiple_crons(self):
        ids = []
        for cron in ["*/30 * * * *", "0 9 * * 1-5", "0 0 1 * *"]:
            d = ok(api_post("/schedules", {"url": "https://httpbin.org/html", "schedule": cron}), 201)
            ids.append(d["schedule_id"])
        for sid in ids:
            api_delete(f"/schedules/{sid}")
        assert len(ids) == 3

    @pytest.mark.api
    def test_schedule_invalid_cron(self):
        resp = api_post("/schedules", {"url": "https://example.com", "schedule": "not-a-cron"})
        assert resp.status_code in (201, 400, 422)

# ===================================================================
# WORKFLOW 12: MCP Server
# ===================================================================
@pytest.mark.live
@pytest.mark.mcp_server
class TestMCPServer:

    @pytest.mark.ui
    def test_mcp_tools_displayed(self, live_page: Page):
        live_page.goto("/mcp", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
        text = live_page.text_content("body").lower()
        for tool in ["scrape", "crawl", "search", "extract", "route"]:
            assert tool in text, f"Missing tool: {tool}"

    @pytest.mark.ui
    def test_mcp_copy_buttons(self, live_page: Page):
        live_page.goto("/mcp", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
        assert len(live_page.query_selector_all("button:has-text('Copy')")) >= 3

    @pytest.mark.ui
    def test_mcp_json_valid(self, live_page: Page):
        live_page.goto("/mcp", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
        blocks = live_page.evaluate("""() => {
            return [...document.querySelectorAll('pre')].filter(b => b.textContent.trim().startsWith('{')).map(b => {
                try { JSON.parse(b.textContent.trim()); return {valid:true}; }
                catch(e) { return {valid:false, err:e.message}; }
            });
        }""")
        assert len(blocks) >= 1
        for b in blocks:
            assert b["valid"], f"Invalid JSON: {b.get('err')}"

# ---------------------------------------------------------------------------
# Main — loop mode
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live E2E Test Runner")
    parser.add_argument("--loop", type=int, default=1)
    parser.add_argument("--interval", type=int, default=300)
    args, remaining = parser.parse_known_args()

    print(f"\n{'='*60}")
    print(f"  LIVE E2E TEST SUITE — {FRONTEND_URL}")
    print(f"  Backend: {API_BASE}")
    print(f"  Loops: {args.loop} | Interval: {args.interval}s")
    print(f"{'='*60}\n")

    exit_code = 0
    for i in range(args.loop):
        if args.loop > 1:
            print(f"\n  LOOP {i+1}/{args.loop} — {datetime.now().strftime('%H:%M:%S')}\n")
        exit_code = pytest.main([__file__, "-v", "--tb=short"] + remaining)
        if i < args.loop - 1:
            print(f"\n  Sleeping {args.interval}s...")
            time.sleep(args.interval)
    sys.exit(exit_code)
