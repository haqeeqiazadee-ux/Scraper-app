"""E2E tests for monitoring, tool, and account pages."""
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.playwright.conftest import FRONTEND_URL


# --- Templates ---
def test_templates_page_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/templates")
    page.wait_for_timeout(1000)
    content = page.content()
    assert "template" in content.lower()


# --- Route Tester ---
def test_route_tester_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/route-tester")
    page.wait_for_timeout(1000)
    content = page.content()
    assert "route" in content.lower()


# --- Scrape Tester ---
def test_scrape_tester_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/scrape-test")
    page.wait_for_timeout(1000)


# --- Amazon ---
def test_amazon_page_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/amazon")
    page.wait_for_timeout(1000)
    content = page.content()
    assert "amazon" in content.lower() or "keepa" in content.lower()


def test_amazon_has_query_types(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/amazon")
    expect(page.get_by_text("ASIN Lookup").first).to_be_visible()


# --- Google Maps ---
def test_maps_page_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/google-maps")
    page.wait_for_timeout(1000)
    content = page.content()
    assert "map" in content.lower() or "business" in content.lower()


# --- Sessions ---
def test_sessions_page_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/sessions")
    page.wait_for_timeout(1000)


# --- Proxies ---
def test_proxies_page_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/proxies")
    page.wait_for_timeout(1000)


# --- Webhooks ---
def test_webhooks_page_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/webhooks")
    page.wait_for_timeout(1000)


# --- Billing ---
def test_billing_page_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/billing")
    page.wait_for_timeout(1000)
    content = page.content()
    assert "billing" in content.lower() or "plan" in content.lower()
