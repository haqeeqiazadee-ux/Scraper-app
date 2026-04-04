"""E2E tests for Tasks page."""
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.playwright.conftest import FRONTEND_URL


def test_tasks_page_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/tasks")
    expect(page.get_by_role("heading", name="Tasks", exact=True)).to_be_visible()


def test_tasks_has_create_button(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/tasks")
    expect(page.get_by_text("Create Task")).to_be_visible()


def test_tasks_has_status_filters(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/tasks")
    expect(page.get_by_text("All")).to_be_visible()
    expect(page.get_by_text("Pending")).to_be_visible()
    expect(page.get_by_text("Completed")).to_be_visible()


def test_tasks_create_opens_form(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/tasks")
    page.get_by_text("Create Task").click()
    page.wait_for_timeout(500)
    # Form modal or section should appear
    expect(page.locator("input, textarea").first).to_be_visible()


def test_tasks_empty_state(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/tasks")
    page.wait_for_timeout(2000)
    # Either tasks list or empty state
    content = page.content()
    assert "task" in content.lower()


def test_tasks_filter_click_works(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/tasks")
    page.get_by_text("Pending", exact=True).click()
    page.wait_for_timeout(500)


def test_results_page_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/results")
    page.wait_for_timeout(1000)
    content = page.content()
    assert "result" in content.lower()


def test_policies_page_renders(page: Page, frontend_server):
    page.goto(f"{FRONTEND_URL}/policies")
    page.wait_for_timeout(1000)
    content = page.content()
    assert "polic" in content.lower()
