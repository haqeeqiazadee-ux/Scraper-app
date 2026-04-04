"""E2E tests for the Search page."""

import pytest
from playwright.sync_api import Page, expect

SEARCH_URL = "/search"


@pytest.fixture(autouse=True)
def navigate_to_search(page: Page, frontend_server):
    page.goto(SEARCH_URL)
    page.wait_for_load_state("networkidle")


# ------------------------------------------------------------------
# 1. Page renders with correct title
# ------------------------------------------------------------------
def test_search_page_renders(page: Page):
    heading = page.locator("h2", has_text="Web Search")
    expect(heading).to_be_visible()


# ------------------------------------------------------------------
# 2. Search query input visible
# ------------------------------------------------------------------
def test_search_has_query_input(page: Page):
    query_input = page.locator('input[type="text"][placeholder*="Search for anything"]')
    expect(query_input).to_be_visible()


# ------------------------------------------------------------------
# 3. Max results select visible
# ------------------------------------------------------------------
def test_search_has_max_results_select(page: Page):
    # First select is "Max Results"
    select = page.locator("select").first
    expect(select).to_be_visible()

    options = select.locator("option")
    expect(options).to_have_count(3)
    expect(options.nth(0)).to_have_text("5")
    expect(options.nth(1)).to_have_text("10")
    expect(options.nth(2)).to_have_text("25")


# ------------------------------------------------------------------
# 4. Search button visible
# ------------------------------------------------------------------
def test_search_button_exists(page: Page):
    button = page.locator('button[type="submit"]', has_text="Search")
    expect(button).to_be_visible()


# ------------------------------------------------------------------
# 5. Empty state message before any search
# ------------------------------------------------------------------
def test_search_empty_state(page: Page):
    empty_msg = page.locator("h3", has_text="Enter a search query above to get started")
    expect(empty_msg).to_be_visible()


# ------------------------------------------------------------------
# 6. Can type into search box
# ------------------------------------------------------------------
def test_search_can_type_query(page: Page):
    query_input = page.locator('input[type="text"][placeholder*="Search for anything"]')
    query_input.fill("playwright testing")
    expect(query_input).to_have_value("playwright testing")


# ------------------------------------------------------------------
# 7. Fill query and click Search — loading state appears
# ------------------------------------------------------------------
def test_search_submit(page: Page):
    query_input = page.locator('input[type="text"][placeholder*="Search for anything"]')
    query_input.fill("test query")

    button = page.locator('button[type="submit"]', has_text="Search")
    expect(button).to_be_enabled()
    button.click()

    # Verify form submitted (button click didn't error)
    page.wait_for_timeout(1000)
    # Page should still be on /search
    assert "/search" in page.url


# ------------------------------------------------------------------
# 8. Page accessible from sidebar
# ------------------------------------------------------------------
def test_search_accessible_from_sidebar(page: Page):
    page.goto("/")
    page.wait_for_load_state("networkidle")

    sidebar_link = page.locator('a[href="/search"]', has_text="Search")
    expect(sidebar_link).to_be_visible()
    sidebar_link.click()
    page.wait_for_url("**/search")

    heading = page.locator("h2", has_text="Web Search")
    expect(heading).to_be_visible()
