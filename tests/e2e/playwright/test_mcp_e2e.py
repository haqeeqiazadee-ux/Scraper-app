"""E2E tests for the MCP Server page."""

import pytest
from playwright.sync_api import Page, expect

MCP_URL = "/mcp"


@pytest.fixture(autouse=True)
def navigate_to_mcp(page: Page, frontend_server):
    page.goto(MCP_URL)
    page.wait_for_load_state("networkidle")


# ------------------------------------------------------------------
# 1. Page renders with correct title
# ------------------------------------------------------------------
def test_mcp_page_renders(page: Page):
    heading = page.locator("h1", has_text="MCP Server")
    expect(heading).to_be_visible()


# ------------------------------------------------------------------
# 2. Quick Start section visible
# ------------------------------------------------------------------
def test_mcp_has_quick_start(page: Page):
    section = page.locator("h2", has_text="Quick Start")
    expect(section).to_be_visible()


# ------------------------------------------------------------------
# 3. Five tool cards visible
# ------------------------------------------------------------------
def test_mcp_has_tool_cards(page: Page):
    # Each tool card contains the tool name in a div with font-weight 700
    tool_names = ["scrape", "crawl", "search", "extract", "route"]
    for name in tool_names:
        card = page.locator("div", has_text=name).first
        expect(card).to_be_visible()

    # The "Available Tools" section has a grid of cards
    tools_heading = page.locator("h2", has_text="Available Tools")
    expect(tools_heading).to_be_visible()


# ------------------------------------------------------------------
# 4. Each tool name text visible
# ------------------------------------------------------------------
def test_mcp_tool_names_visible(page: Page):
    tool_names = ["scrape", "crawl", "search", "extract", "route"]
    for name in tool_names:
        # Tool name appears as bold text in the card
        tool_label = page.locator(
            "div >> text='{}'".format(name)
        ).first
        expect(tool_label).to_be_visible()


# ------------------------------------------------------------------
# 5. Claude Desktop and VS Code sections visible
# ------------------------------------------------------------------
def test_mcp_has_connection_config(page: Page):
    claude_tab = page.locator("button", has_text="Claude Desktop")
    expect(claude_tab).to_be_visible()

    vscode_tab = page.locator("button", has_text="VS Code")
    expect(vscode_tab).to_be_visible()


# ------------------------------------------------------------------
# 6. At least one <pre> code block visible
# ------------------------------------------------------------------
def test_mcp_has_code_blocks(page: Page):
    code_blocks = page.locator("pre")
    count = code_blocks.count()
    assert count >= 1, f"Expected at least 1 <pre> code block, found {count}"
    expect(code_blocks.first).to_be_visible()


# ------------------------------------------------------------------
# 7. Copy buttons visible
# ------------------------------------------------------------------
def test_mcp_copy_buttons_exist(page: Page):
    copy_buttons = page.locator("button", has_text="Copy")
    count = copy_buttons.count()
    assert count >= 1, f"Expected at least 1 Copy button, found {count}"
    expect(copy_buttons.first).to_be_visible()


# ------------------------------------------------------------------
# 8. Page is purely informational — no /api network requests
# ------------------------------------------------------------------
def test_mcp_no_api_calls(page: Page):
    api_requests = []

    def handle_request(request):
        if "/api" in request.url:
            api_requests.append(request.url)

    page.on("request", handle_request)

    # Re-navigate to capture all requests from page load
    page.goto(MCP_URL)
    page.wait_for_load_state("networkidle")

    # Filter out Vite dev server module requests and background React Query fetches
    mcp_api_requests = [
        url for url in api_requests
        if not url.endswith(".ts")
        and not url.endswith(".tsx")
        and "/api/v1/tasks" not in url
        and "/api/v1/policies" not in url
        and "/health" not in url
        and "/@" not in url
        and "/node_modules/" not in url
        and "/src/" not in url
    ]
    assert len(mcp_api_requests) == 0, (
        f"Expected no MCP-specific /api requests on MCP page, but found: {mcp_api_requests}"
    )
