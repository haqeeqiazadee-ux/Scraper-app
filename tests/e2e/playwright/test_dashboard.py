"""E2E tests for the Dashboard page."""
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.playwright.conftest import FRONTEND_URL


def test_dashboard_renders_title(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    expect(page.get_by_text("Dashboard")).to_be_visible()


def test_dashboard_has_stat_cards(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    expect(page.get_by_text("Total Tasks")).to_be_visible()
    expect(page.get_by_text("Running")).to_be_visible()
    expect(page.get_by_text("Completed")).to_be_visible()
    expect(page.get_by_text("Failed")).to_be_visible()


def test_dashboard_has_quick_actions(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    expect(page.get_by_text("New Task")).to_be_visible()
    expect(page.get_by_text("Templates")).to_be_visible()
    expect(page.get_by_text("Test URL")).to_be_visible()
    expect(page.get_by_text("Results")).to_be_visible()


def test_dashboard_has_hydra_quick_actions(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    expect(page.get_by_text("Start Crawl")).to_be_visible()
    expect(page.get_by_text("Web Search")).to_be_visible()
    expect(page.get_by_text("MCP Setup")).to_be_visible()


def test_quick_action_navigates_to_crawl(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    page.get_by_text("Start Crawl").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/crawl")


def test_quick_action_navigates_to_search(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    page.get_by_text("Web Search").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/search")


def test_quick_action_navigates_to_mcp(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    page.get_by_text("MCP Setup").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/mcp")


def test_dashboard_shows_health_badge(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    # Health badge should appear after API responds
    page.wait_for_timeout(2000)
    health_badge = page.locator(".badge")
    expect(health_badge.first).to_be_visible()


def test_dashboard_shows_recent_tasks_area(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    # Should show either task table or empty state
    page.wait_for_timeout(2000)
    has_table = page.locator("table").count() > 0
    has_empty = page.get_by_text("No tasks yet").count() > 0 or page.get_by_text("Create").count() > 0
    assert has_table or has_empty


def test_dashboard_last_refreshed_shows(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    expect(page.get_by_text("Last refreshed")).to_be_visible()
