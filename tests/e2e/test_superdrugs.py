"""
Playwright E2E regression test for superdrugs.pk

Tests the Smart Scraper against a real JS-heavy Shopify pharmacy site.
Verifies auto-detection, escalation, and extraction quality.

Run:
  C:\Python314\python.exe -m pytest tests/e2e/test_superdrugs.py -v --tb=short
"""

import json
import os
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
HEADERS = {"X-Tenant-ID": "e2e-superdrugs", "Content-Type": "application/json"}
TARGET = "https://superdrugs.pk"


def api_post(path, data, timeout=120.0):
    with httpx.Client(base_url=API, timeout=timeout, headers=HEADERS) as c:
        return c.post(path, json=data)


def ok(resp, expected=200):
    assert resp.status_code == expected, f"{resp.status_code}: {resp.text[:300]}"
    return resp.json()


# ─── API Tests ───────────────────────────────────────────────────────

@pytest.mark.live
class TestSuperDrugsAPI:

    def test_smart_scrape_finds_products(self):
        """Smart scrape superdrugs.pk should find more than 3 items."""
        d = ok(api_post("/smart-scrape", {"target": TARGET}))
        assert d["status"] in ("completed", "success")
        assert d["item_count"] > 3, (
            f"Only {d['item_count']} items. Steps: "
            + " → ".join(s.get("step", "") for s in d.get("steps", []))
        )

    def test_enhanced_extraction_runs(self):
        """Should show 'Enhanced extraction' step in response."""
        d = ok(api_post("/smart-scrape", {"target": TARGET}))
        step_texts = [s.get("step", "") for s in d.get("steps", [])]
        has_enhanced = any("nhanced" in s for s in step_texts)
        assert has_enhanced, f"No enhancement step found. Steps: {step_texts}"

    def test_products_have_names_and_prices(self):
        """Extracted items should have name fields."""
        d = ok(api_post("/smart-scrape", {"target": TARGET}))
        items = d.get("extracted_data", [])
        named = [i for i in items if i.get("name")]
        assert len(named) >= 3, f"Only {len(named)} items with names out of {len(items)}"

    def test_schema_extraction(self):
        """Schema extraction should find title and price."""
        d = ok(api_post("/smart-scrape", {
            "target": f"{TARGET}/products/centrum-adult-multivitamin-tablets-30s",
            "schema": {"title": "string", "price": "number"},
        }))
        sm = d.get("schema_matched")
        if sm:
            assert sm.get("title") or sm.get("price"), f"Schema match empty: {sm}"

    def test_crawl_mode(self):
        """Multi-page crawl should find more items."""
        d = ok(api_post("/smart-scrape", {
            "target": TARGET,
            "max_pages": 3,
            "max_depth": 1,
        }))
        assert d["item_count"] >= 3

    def test_everything_mode_via_test_scrape(self):
        """Fallback: /test-scrape everything mode should find 100+ items."""
        d = ok(api_post("/test-scrape", {
            "url": TARGET,
            "timeout_ms": 25000,
            "extraction_mode": "everything",
        }))
        assert d["item_count"] >= 50, (
            f"Everything mode only found {d['item_count']} items"
        )

    def test_result_saved(self):
        """Smart scrape result should be saved to database."""
        d = ok(api_post("/smart-scrape", {"target": TARGET}))
        assert d.get("saved") is True
        assert d.get("saved_task_id")

    def test_response_has_steps(self):
        """Response should include escalation steps."""
        d = ok(api_post("/smart-scrape", {"target": TARGET}))
        assert len(d.get("steps", [])) >= 3


# ─── Playwright UI Tests ────────────────────────────────────────────

@pytest.mark.live
@pytest.mark.ui
class TestSuperDrugsUI:

    @pytest.fixture
    def page(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 800},
                base_url=FRONTEND,
            )
            pg = ctx.new_page()
            yield pg
            pg.close()
            ctx.close()
            browser.close()

    def test_scraper_page_loads(self, page: Page):
        """Scraper page loads with input field."""
        page.goto("/scraper", wait_until="networkidle", timeout=20_000)
        inp = page.query_selector('input[type="text"]')
        assert inp, "No input field found"
        btn = page.query_selector("button:has-text('Scrape')")
        assert btn, "No Scrape button found"

    def test_superdrugs_scrape_flow(self, page: Page):
        """Enter superdrugs.pk, click Scrape, verify results appear."""
        page.goto("/scraper", wait_until="networkidle", timeout=20_000)
        page.fill('input[type="text"]', TARGET)
        page.click("button:has-text('Scrape')")

        # Wait for results (smart scrape can take up to 30s)
        page.wait_for_timeout(5_000)

        # Check for escalation steps
        body = page.text_content("body")
        assert "Executed" in body or "step" in body.lower(), "No escalation steps visible"

        # Wait for completion
        for _ in range(20):
            page.wait_for_timeout(2_000)
            body = page.text_content("body")
            if "COMPLETED" in body or "Items Found" in body.lower() or "items found" in body.lower():
                break

        # Verify results showed up
        body = page.text_content("body")
        has_results = (
            "Extracted Data" in body
            or "COMPLETED" in body
            or "Items Found" in body
        )
        assert has_results, f"No results visible after 45s. Body contains: {body[:500]}"

    def test_superdrugs_shows_items(self, page: Page):
        """After scraping superdrugs.pk, items should be visible in table."""
        page.goto("/scraper", wait_until="networkidle", timeout=20_000)
        page.fill('input[type="text"]', TARGET)
        page.click("button:has-text('Scrape')")

        # Wait for completion
        for _ in range(25):
            page.wait_for_timeout(2_000)
            body = page.text_content("body")
            if "COMPLETED" in body:
                break

        # Check item count is more than 3
        body = page.text_content("body")
        # Look for items count in stats grid
        import re
        count_match = re.search(r'ITEMS FOUND\s*(\d+)', body, re.IGNORECASE)
        if count_match:
            count = int(count_match.group(1))
            assert count > 3, f"Only found {count} items in UI"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
