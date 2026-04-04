"""E2E tests for the Extract page."""

import pytest
from playwright.sync_api import Page, expect

EXTRACT_URL = "/extract"


@pytest.fixture(autouse=True)
def navigate_to_extract(page: Page, frontend_server):
    page.goto(EXTRACT_URL)
    page.wait_for_load_state("networkidle")


# ------------------------------------------------------------------
# 1. Page renders with correct title
# ------------------------------------------------------------------
def test_extract_page_renders(page: Page):
    heading = page.locator("h2", has_text="Structured Extract")
    expect(heading).to_be_visible()


# ------------------------------------------------------------------
# 2. URL input visible
# ------------------------------------------------------------------
def test_extract_has_url_input(page: Page):
    url_input = page.locator('input[type="text"][placeholder*="example.com"]')
    expect(url_input).to_be_visible()


# ------------------------------------------------------------------
# 3. Schema textarea visible
# ------------------------------------------------------------------
def test_extract_has_schema_textarea(page: Page):
    textarea = page.locator("textarea")
    expect(textarea).to_be_visible()


# ------------------------------------------------------------------
# 4. Extract button visible
# ------------------------------------------------------------------
def test_extract_button_exists(page: Page):
    button = page.locator('button[type="submit"]', has_text="Extract")
    expect(button).to_be_visible()


# ------------------------------------------------------------------
# 5. Schema textarea has example JSON placeholder
# ------------------------------------------------------------------
def test_extract_schema_placeholder(page: Page):
    textarea = page.locator("textarea")
    placeholder = textarea.get_attribute("placeholder")
    assert placeholder is not None
    assert "name" in placeholder
    assert "price" in placeholder


# ------------------------------------------------------------------
# 6. Can type URL into input
# ------------------------------------------------------------------
def test_extract_can_type_url(page: Page):
    url_input = page.locator('input[type="text"][placeholder*="example.com"]')
    url_input.fill("https://example.com/product")
    expect(url_input).to_have_value("https://example.com/product")


# ------------------------------------------------------------------
# 7. Can type JSON into schema textarea
# ------------------------------------------------------------------
def test_extract_can_type_schema(page: Page):
    textarea = page.locator("textarea")
    schema = '{"title": "string", "price": "number"}'
    textarea.fill(schema)
    expect(textarea).to_have_value(schema)


# ------------------------------------------------------------------
# 8. Page accessible from sidebar
# ------------------------------------------------------------------
def test_extract_accessible_from_sidebar(page: Page):
    page.goto("/")
    page.wait_for_load_state("networkidle")

    sidebar_link = page.locator('a[href="/extract"]', has_text="Extract")
    expect(sidebar_link).to_be_visible()
    sidebar_link.click()
    page.wait_for_url("**/extract")

    heading = page.locator("h2", has_text="Structured Extract")
    expect(heading).to_be_visible()
