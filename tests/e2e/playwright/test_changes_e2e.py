"""E2E tests for the Changes (Change Detection) page."""

import pytest
from playwright.sync_api import Page, expect

CHANGES_URL = "/changes"

OLD_DATA = '[{"name": "Widget", "price": "$19.99", "product_url": "https://example.com/widget"}]'
NEW_DATA = '[{"name": "Widget", "price": "$14.99", "product_url": "https://example.com/widget"}, {"name": "Gadget", "price": "$29.99", "product_url": "https://example.com/gadget"}]'


@pytest.fixture(autouse=True)
def navigate_to_changes(page: Page, frontend_server):
    page.goto(CHANGES_URL)
    page.wait_for_load_state("networkidle")


# ------------------------------------------------------------------
# 1. Page renders with correct title
# ------------------------------------------------------------------
def test_changes_page_renders(page: Page):
    heading = page.locator("h1", has_text="Change Detection")
    expect(heading).to_be_visible()


# ------------------------------------------------------------------
# 2. Two textareas visible (old and new snapshot)
# ------------------------------------------------------------------
def test_changes_has_two_textareas(page: Page):
    textareas = page.locator("textarea")
    expect(textareas).to_have_count(2)
    expect(textareas.nth(0)).to_be_visible()
    expect(textareas.nth(1)).to_be_visible()


# ------------------------------------------------------------------
# 3. Compare button visible
# ------------------------------------------------------------------
def test_changes_has_compare_button(page: Page):
    button = page.locator("button", has_text="Compare")
    expect(button).to_be_visible()


# ------------------------------------------------------------------
# 4. Price threshold input visible
# ------------------------------------------------------------------
def test_changes_has_threshold_input(page: Page):
    threshold_input = page.locator('input[type="number"]')
    expect(threshold_input).to_be_visible()
    expect(threshold_input).to_have_value("10")


# ------------------------------------------------------------------
# 5. No results shown initially (empty state)
# ------------------------------------------------------------------
def test_changes_empty_state(page: Page):
    empty_msg = page.locator("h3", has_text="Paste two JSON snapshots to compare")
    expect(empty_msg).to_be_visible()


# ------------------------------------------------------------------
# 6. Invalid JSON shows error
# ------------------------------------------------------------------
def test_changes_invalid_json_error(page: Page):
    old_textarea = page.locator("textarea").nth(0)
    new_textarea = page.locator("textarea").nth(1)

    old_textarea.fill("not valid json")
    new_textarea.fill('[{"name": "test"}]')

    button = page.locator("button", has_text="Compare")
    button.click()

    error_banner = page.locator(".form-error-banner")
    expect(error_banner).to_be_visible()
    expect(error_banner).to_contain_text("Failed to parse")


# ------------------------------------------------------------------
# 7. Valid comparison shows results
# ------------------------------------------------------------------
def test_changes_valid_comparison(page: Page):
    old_textarea = page.locator("textarea").nth(0)
    new_textarea = page.locator("textarea").nth(1)

    old_textarea.fill(OLD_DATA)
    new_textarea.fill(NEW_DATA)

    button = page.locator("button", has_text="Compare")
    button.click()

    # Summary cards should appear
    added_label = page.locator("text=Added")
    expect(added_label.first).to_be_visible()

    # Changes table should appear
    table = page.locator("table")
    expect(table).to_be_visible()


# ------------------------------------------------------------------
# 8. Detects added items
# ------------------------------------------------------------------
def test_changes_detects_added_items(page: Page):
    old_textarea = page.locator("textarea").nth(0)
    new_textarea = page.locator("textarea").nth(1)

    old_textarea.fill(OLD_DATA)
    new_textarea.fill(NEW_DATA)

    page.locator("button", has_text="Compare").click()

    # Look for "Added" badge in the table
    added_badge = page.locator("table span", has_text="Added")
    expect(added_badge).to_be_visible()

    # The Gadget item should be referenced
    gadget_cell = page.locator("table td", has_text="example.com/gadget")
    expect(gadget_cell).to_be_visible()


# ------------------------------------------------------------------
# 9. Detects price change with delta
# ------------------------------------------------------------------
def test_changes_detects_price_change(page: Page):
    old_textarea = page.locator("textarea").nth(0)
    new_textarea = page.locator("textarea").nth(1)

    # Use threshold of 0 so any price change is detected
    threshold_input = page.locator('input[type="number"]')
    threshold_input.fill("0")

    old_textarea.fill(OLD_DATA)
    new_textarea.fill(NEW_DATA)

    page.locator("button", has_text="Compare").click()

    # Look for "Price Change" badge in the table
    price_badge = page.locator("table span", has_text="Price Change")
    expect(price_badge).to_be_visible()

    # The price delta should contain an arrow and percentage
    delta_cell = page.locator("table td", has_text="\u2192")
    expect(delta_cell).to_be_visible()


# ------------------------------------------------------------------
# 10. Identical data shows "no changes"
# ------------------------------------------------------------------
def test_changes_identical_data(page: Page):
    old_textarea = page.locator("textarea").nth(0)
    new_textarea = page.locator("textarea").nth(1)

    old_textarea.fill(OLD_DATA)
    new_textarea.fill(OLD_DATA)

    page.locator("button", has_text="Compare").click()

    no_changes = page.locator("h3", has_text="No Changes Detected")
    expect(no_changes).to_be_visible()
