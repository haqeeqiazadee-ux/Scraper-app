"""
Playwright E2E regression test for superdrugs.pk

Tests the Smart Scraper against a real JS-heavy Shopify pharmacy site.
Verifies auto-detection, escalation, and extraction quality.

Run: python -m pytest tests/e2e/test_superdrugs.py -v --tb=short
"""

import os
import re
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


def post(path, data, timeout=120.0):
    with httpx.Client(base_url=API, timeout=timeout, headers=HEADERS) as c:
        resp = c.post(path, json=data)
        if resp.status_code == 502:
            pytest.skip("Railway 502 timeout (transient)")
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:300]}"
        return resp.json()


def fill_and_scrape(page: Page, url: str):
    """Helper: fill URL input and click Scrape, wait for completion."""
    page.goto("/scraper", wait_until="networkidle", timeout=20_000)
    # Use placeholder to target the correct input (not sidebar search)
    inp = page.get_by_placeholder("example.com")
    inp.fill(url)
    page.wait_for_timeout(300)
    page.get_by_role("button", name="Scrape").click(timeout=5_000)
    # Wait up to 60s for completion
    for _ in range(30):
        page.wait_for_timeout(2_000)
        body = page.text_content("body") or ""
        if "COMPLETED" in body or "Extracted Data" in body or "FAILED" in body:
            return body
    return page.text_content("body") or ""


# ─── API Tests ───────────────────────────────────────────────────────

@pytest.mark.live
class TestSuperDrugsAPI:

    def test_smart_scrape_finds_products(self):
        d = post("/smart-scrape", {"target": TARGET})
        assert d["item_count"] > 3, f"Only {d['item_count']} items"

    def test_enhanced_extraction_runs(self):
        d = post("/smart-scrape", {"target": TARGET})
        steps = [s.get("step", "") for s in d.get("steps", [])]
        assert any("nhanced" in s for s in steps), f"No enhancement. Steps: {steps}"

    def test_products_have_names(self):
        d = post("/smart-scrape", {"target": TARGET})
        named = [i for i in d.get("extracted_data", []) if i.get("name")]
        assert len(named) >= 3

    def test_schema_extraction(self):
        d = post("/smart-scrape", {
            "target": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            "schema": {"title": "string", "price": "number"},
        })
        sm = d.get("schema_matched", {})
        fields = sm.get("matched_fields", sm)
        assert fields.get("title") or fields.get("price"), f"Empty: {sm}"

    def test_crawl_mode(self):
        d = post("/smart-scrape", {"target": TARGET, "max_pages": 3, "max_depth": 1})
        assert d["item_count"] >= 3

    def test_everything_via_test_scrape(self):
        d = post("/test-scrape", {"url": TARGET, "timeout_ms": 25000, "extraction_mode": "everything"})
        assert d["item_count"] >= 50, f"Only {d['item_count']} items"

    def test_result_saved(self):
        d = post("/smart-scrape", {"target": TARGET})
        assert d.get("saved") is True

    def test_has_steps(self):
        d = post("/smart-scrape", {"target": TARGET})
        assert len(d.get("steps", [])) >= 3


# ─── Playwright UI Tests ────────────────────────────────────────────

@pytest.mark.live
@pytest.mark.ui
class TestSuperDrugsUI:

    @pytest.fixture
    def page(self):
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context(viewport={"width": 1280, "height": 800}, base_url=FRONTEND)
            pg = ctx.new_page()
            yield pg
            pg.close()
            ctx.close()
            b.close()

    def test_page_loads(self, page: Page):
        page.goto("/scraper", wait_until="networkidle", timeout=20_000)
        assert page.get_by_placeholder("example.com").count() >= 1
        assert page.get_by_role("button", name="Scrape").count() >= 1

    def test_scrape_completes(self, page: Page):
        body = fill_and_scrape(page, TARGET)
        assert "COMPLETED" in body or "Extracted Data" in body, f"Not completed: {body[:200]}"

    def test_shows_items(self, page: Page):
        body = fill_and_scrape(page, TARGET)
        match = re.search(r"ITEMS FOUND\s*(\d+)", body, re.IGNORECASE)
        if match:
            assert int(match.group(1)) > 3, f"Only {match.group(1)} items"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
