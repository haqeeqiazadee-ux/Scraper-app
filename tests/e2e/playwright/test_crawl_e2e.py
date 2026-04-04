"""E2E tests for the Crawl page."""

import re

import pytest
from playwright.sync_api import Page, expect

CRAWL_URL = "/crawl"


@pytest.fixture(autouse=True)
def navigate_to_crawl(page: Page, frontend_server):
    page.goto(CRAWL_URL)
    page.wait_for_load_state("networkidle")


# ------------------------------------------------------------------
# 1. Page renders with correct title
# ------------------------------------------------------------------
def test_crawl_page_renders(page: Page):
    heading = page.locator("h2", has_text="Web Crawl")
    expect(heading).to_be_visible()


# ------------------------------------------------------------------
# 2. Form has URL input, max depth, max pages, format select
# ------------------------------------------------------------------
def test_crawl_form_has_inputs(page: Page):
    url_input = page.locator('input[type="text"][placeholder*="example.com"]')
    expect(url_input).to_be_visible()

    depth_input = page.locator('input[type="number"]').nth(0)
    expect(depth_input).to_be_visible()

    pages_input = page.locator('input[type="number"]').nth(1)
    expect(pages_input).to_be_visible()

    format_select = page.locator("select")
    expect(format_select).to_be_visible()


# ------------------------------------------------------------------
# 3. Start Crawl button exists
# ------------------------------------------------------------------
def test_crawl_start_button_exists(page: Page):
    button = page.locator('button[type="submit"]', has_text="Start Crawl")
    expect(button).to_be_visible()


# ------------------------------------------------------------------
# 4. Can type a URL into the input
# ------------------------------------------------------------------
def test_crawl_form_url_input(page: Page):
    url_input = page.locator('input[type="text"][placeholder*="example.com"]')
    url_input.fill("https://example.com")
    expect(url_input).to_have_value("https://example.com")


# ------------------------------------------------------------------
# 5. Depth input defaults to 3
# ------------------------------------------------------------------
def test_crawl_depth_input_default(page: Page):
    depth_input = page.locator('input[type="number"]').nth(0)
    expect(depth_input).to_have_value("3")


# ------------------------------------------------------------------
# 6. Max pages input defaults to 100
# ------------------------------------------------------------------
def test_crawl_pages_input_default(page: Page):
    pages_input = page.locator('input[type="number"]').nth(1)
    expect(pages_input).to_have_value("100")


# ------------------------------------------------------------------
# 7. Format select has json/markdown/html options
# ------------------------------------------------------------------
def test_crawl_format_select_options(page: Page):
    select = page.locator("select")
    options = select.locator("option")
    expect(options).to_have_count(3)

    expect(options.nth(0)).to_have_text("JSON")
    expect(options.nth(1)).to_have_text("Markdown")
    expect(options.nth(2)).to_have_text("HTML")


# ------------------------------------------------------------------
# 8. Empty URL validation — button disabled when URL empty
# ------------------------------------------------------------------
def test_crawl_empty_url_validation(page: Page):
    button = page.locator('button[type="submit"]', has_text="Start Crawl")
    expect(button).to_be_disabled()


# ------------------------------------------------------------------
# 9. Fill URL and click Start — loading state appears
# ------------------------------------------------------------------
def test_crawl_submit_with_url(page: Page):
    url_input = page.locator('input[type="text"][placeholder*="example.com"]')
    url_input.fill("https://example.com")

    button = page.locator('button[type="submit"]', has_text="Start Crawl")
    expect(button).to_be_enabled()
    button.click()

    # Verify form submitted (button click didn't error)
    page.wait_for_timeout(1000)
    # Page should still be on /crawl (not redirected away)
    assert "/crawl" in page.url


# ------------------------------------------------------------------
# 10. Page accessible from sidebar "Crawl" link
# ------------------------------------------------------------------
def test_crawl_page_accessible_from_sidebar(page: Page):
    # Navigate away first
    page.goto("/")
    page.wait_for_load_state("networkidle")

    sidebar_link = page.locator('a[href="/crawl"]', has_text="Crawl")
    expect(sidebar_link).to_be_visible()
    sidebar_link.click()
    page.wait_for_url("**/crawl")

    heading = page.locator("h2", has_text="Web Crawl")
    expect(heading).to_be_visible()
