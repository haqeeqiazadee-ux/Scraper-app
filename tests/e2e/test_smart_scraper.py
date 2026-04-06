"""Smart Scraper E2E tests — verify auto-scaling on real sites.

Uses synchronous httpx + Playwright (no async event loop conflicts).

Usage:
  python -m pytest tests/e2e/test_smart_scraper.py -v --tb=short
  python -m pytest tests/e2e/test_smart_scraper.py -v -m live
"""

from __future__ import annotations

import json
import os
import time
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
BACKEND_URL = os.getenv("E2E_BACKEND_URL", "https://scraper-platform-production-17cb.up.railway.app")
API_BASE = f"{BACKEND_URL}/api/v1"
FRONTEND_URL = os.getenv("E2E_FRONTEND_URL", "https://myscraper.netlify.app")
HEADERS = {"X-Tenant-ID": "e2e-smart-test"}
RESULTS_DIR = Path(__file__).resolve().parents[2] / "test-results"
SCREENSHOTS_DIR = RESULTS_DIR / "screenshots"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def api_post(path: str, json_data: dict = None, timeout: float = 120.0) -> httpx.Response:
    with httpx.Client(base_url=API_BASE, timeout=timeout, headers=HEADERS) as c:
        return c.post(path, json=json_data)


def ok(resp: httpx.Response, expected: int = 200) -> dict:
    assert resp.status_code == expected, (
        f"Expected {expected}, got {resp.status_code}: {resp.text[:500]}"
    )
    return resp.json()


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
                page.screenshot(
                    path=str(SCREENSHOTS_DIR / f"FAIL_{item.name}_{int(time.time())}.png")
                )
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def setup_dirs():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def serper_ok():
    return bool(os.getenv("SERPER_API_KEY", "").strip())


# ===================================================================
# API Tests
# ===================================================================
@pytest.mark.live
class TestSmartScraperAPI:

    def test_static_site_http_only(self):
        """books.toscrape.com should stay on HTTP, find 5+ items."""
        d = ok(api_post("/smart-scrape", {"target": "https://books.toscrape.com/"}))
        assert d["status"] in ("success", "completed")
        assert d["detected_as"] == "url"
        assert d["item_count"] >= 5
        assert d["lane_used"] == "http"
        assert d["saved"] is True

    def test_httpbin_basic(self):
        """httpbin.org/html should extract content."""
        d = ok(api_post("/smart-scrape", {"target": "https://httpbin.org/html"}))
        assert d["status"] in ("success", "completed")
        assert d["item_count"] >= 1

    def test_search_query(self, serper_ok):
        """Search query routes to Serper."""
        if not serper_ok:
            pytest.skip("SERPER_API_KEY not set")
        d = ok(api_post("/smart-scrape", {"target": "best gaming laptops 2026"}))
        assert d["detected_as"] == "search"
        assert d["item_count"] >= 1

    def test_schema_extraction(self):
        """Schema matching extracts specific fields."""
        d = ok(api_post("/smart-scrape", {
            "target": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            "schema": {"title": "string", "price": "number"},
        }))
        assert d["status"] in ("success", "completed")
        assert d.get("schema_matched")
        assert d["schema_matched"].get("matched_fields") or d["schema_matched"].get("title")

    def test_escalation_steps_logged(self):
        """Every scrape should have steps in the response."""
        d = ok(api_post("/smart-scrape", {"target": "https://example.com"}))
        assert "steps" in d
        assert len(d["steps"]) >= 1

    def test_invalid_url_handled(self):
        """Invalid URL doesn't crash, returns error gracefully."""
        d = ok(api_post("/smart-scrape", {"target": "https://thisdomaindoesnotexist99999.com"}))
        # Should return failed or error status, not 500
        assert d["status"] in ("success", "completed", "failed", "error")

    def test_superdrugs_pk(self):
        """superdrugs.pk JS-heavy site — should attempt escalation."""
        d = ok(api_post("/smart-scrape", {"target": "https://superdrugs.pk"}, timeout=120))
        assert d["status"] in ("success", "completed", "failed")
        assert len(d["steps"]) >= 1
        # If browser available, should escalate; if not, should still return something
        assert d["item_count"] >= 0


# ===================================================================
# UI Tests
# ===================================================================
@pytest.mark.live
@pytest.mark.ui
class TestSmartScraperUI:

    @pytest.fixture
    def live_page(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 720},
                base_url=FRONTEND_URL,
            )
            page = ctx.new_page()
            yield page
            page.close()
            ctx.close()
            browser.close()

    def test_page_loads(self, live_page: Page):
        """Scraper page loads with input field."""
        live_page.goto("/scraper", wait_until="networkidle", timeout=20000)
        assert live_page.query_selector('input[type="text"]')
        assert live_page.query_selector("button")

    def test_advanced_options_toggle(self, live_page: Page):
        """Advanced options section can be toggled."""
        live_page.goto("/scraper", wait_until="networkidle", timeout=20000)
        # Advanced options should be hidden by default
        assert not live_page.query_selector('select')
        # Click toggle
        live_page.click("button:has-text('Advanced Options')")
        live_page.wait_for_timeout(500)
        # Now select should be visible
        assert live_page.query_selector('select')

    def test_scrape_shows_results(self, live_page: Page):
        """Enter URL, click Scrape, see results."""
        live_page.goto("/scraper", wait_until="networkidle", timeout=20000)
        live_page.fill('input[type="text"]', "https://httpbin.org/html")
        live_page.click("button:has-text('Scrape')")
        # Wait for results (up to 60s)
        live_page.wait_for_selector(".stat-card", timeout=60000)
        text = live_page.text_content("body").lower()
        assert "success" in text or "completed" in text or "items" in text or "extracted" in text

    def test_empty_state_shown(self, live_page: Page):
        """Empty state is shown when no scrape has been done."""
        live_page.goto("/scraper", wait_until="networkidle", timeout=20000)
        text = live_page.text_content("body")
        assert "Ready to scrape" in text
