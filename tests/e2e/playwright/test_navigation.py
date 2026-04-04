"""E2E tests for sidebar navigation and routing."""
import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.playwright.conftest import FRONTEND_URL


def test_app_opens_to_dashboard(page: Page, frontend_server):
    page.goto(FRONTEND_URL)
    expect(page).to_have_url(f"{FRONTEND_URL}/dashboard")


def test_no_login_screen(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/login")
    # Should redirect to dashboard, not show login form
    expect(page).to_have_url(f"{FRONTEND_URL}/dashboard")


def test_sidebar_has_core_section(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    expect(page.get_by_text("CORE")).to_be_visible()
    expect(page.get_by_text("Dashboard")).to_be_visible()
    expect(page.get_by_text("Tasks")).to_be_visible()
    expect(page.get_by_text("Policies")).to_be_visible()
    expect(page.get_by_text("Results")).to_be_visible()


def test_sidebar_has_tools_section(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    expect(page.get_by_text("TOOLS")).to_be_visible()
    expect(page.get_by_text("Crawl")).to_be_visible()
    expect(page.get_by_text("Search")).to_be_visible()
    expect(page.get_by_text("Extract")).to_be_visible()
    expect(page.get_by_text("Changes")).to_be_visible()


def test_sidebar_has_integration_section(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    expect(page.get_by_text("INTEGRATION")).to_be_visible()
    expect(page.get_by_text("MCP Server")).to_be_visible()


def test_sidebar_has_monitoring_section(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    expect(page.get_by_text("MONITORING")).to_be_visible()


def test_navigate_to_tasks(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    page.get_by_text("Tasks", exact=True).click()
    expect(page).to_have_url(f"{FRONTEND_URL}/tasks")


def test_navigate_to_crawl(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    page.get_by_text("Crawl", exact=True).click()
    expect(page).to_have_url(f"{FRONTEND_URL}/crawl")


def test_navigate_to_mcp(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/dashboard")
    page.get_by_text("MCP Server", exact=True).click()
    expect(page).to_have_url(f"{FRONTEND_URL}/mcp")


def test_unknown_route_redirects(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/nonexistent-page")
    expect(page).to_have_url(f"{FRONTEND_URL}/dashboard")


def test_active_nav_item_highlighted(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/tasks")
    tasks_link = page.locator("a[href='/tasks']")
    expect(tasks_link).to_have_class(re.compile(r"active"))
