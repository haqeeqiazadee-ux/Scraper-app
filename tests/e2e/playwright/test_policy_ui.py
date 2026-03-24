"""
E2E tests for Policy UI.

Covers:
  UC-4.1.1 — Navigate to Policies → Click "Create" → form renders
  UC-4.3.2 — Policy dropdown shows all available policies (in Task form)
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


def login(page: Page) -> None:
    """Helper: log in and land on dashboard."""
    page.goto("/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[id="login-username"]', "testuser")
    page.fill('input[id="login-password"]', "testpass123")
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard", timeout=10000)


class TestPolicyPage:
    """UC-4.1.1 — Policy create form renders."""

    def test_policies_page_loads(self, page: Page):
        """Navigate to policies page, verify it renders."""
        login(page)
        page.goto("/policies")
        page.wait_for_load_state("networkidle")

        expect(page.locator("h2")).to_contain_text("Policies")
        expect(page.locator("text=Create Policy")).to_be_visible()

    def test_create_policy_form_opens(self, page: Page):
        """Clicking 'Create Policy' opens the create form modal."""
        login(page)
        page.goto("/policies")
        page.wait_for_load_state("networkidle")

        page.click("text=+ Create Policy")
        page.wait_for_timeout(500)

        # Form should be visible
        expect(page.locator("h3:has-text('Create Policy')")).to_be_visible()
        expect(page.locator('input[id="policy-name"]')).to_be_visible()
        expect(page.locator('select[id="policy-lane"]')).to_be_visible()
        expect(page.locator('input[id="policy-domains"]')).to_be_visible()
        expect(page.locator('input[id="policy-timeout"]')).to_be_visible()

    def test_create_policy_lane_options(self, page: Page):
        """Lane dropdown shows Auto/API/HTTP/Browser/Hard Target options."""
        login(page)
        page.goto("/policies")
        page.wait_for_load_state("networkidle")

        page.click("text=+ Create Policy")
        page.wait_for_timeout(500)

        # Check lane dropdown options
        options = page.locator('select[id="policy-lane"] option').all_text_contents()
        assert "Auto" in options
        assert "HTTP" in options
        assert "Browser" in options
        assert "Hard Target" in options

    def test_create_policy_successfully(self, page: Page):
        """Create a policy via form and verify it appears in the list."""
        login(page)
        page.goto("/policies")
        page.wait_for_load_state("networkidle")

        page.click("text=+ Create Policy")
        page.wait_for_timeout(500)

        # Fill form
        page.fill('input[id="policy-name"]', "E2E Test Policy")
        page.select_option('select[id="policy-lane"]', "browser")
        page.fill('input[id="policy-domains"]', "example.com, test.com")

        # Submit
        page.click("button[type='submit']:has-text('Create Policy')")
        page.wait_for_timeout(1000)
        page.wait_for_load_state("networkidle")

        # Policy should appear in the table
        body = page.locator("body").inner_text()
        assert "E2E Test Policy" in body, f"Created policy not in list: {body[:300]}"

    def test_create_policy_validates_name(self, page: Page):
        """Submitting without a name shows an error."""
        login(page)
        page.goto("/policies")
        page.wait_for_load_state("networkidle")

        page.click("text=+ Create Policy")
        page.wait_for_timeout(500)

        # Submit with empty name
        page.click("button[type='submit']:has-text('Create Policy')")
        page.wait_for_timeout(300)

        # Error should appear
        expect(page.locator(".form-error-banner")).to_be_visible()


class TestPolicyDropdownInTaskForm:
    """UC-4.3.2 — Policy dropdown in task form shows available policies."""

    def test_task_form_shows_policy_dropdown(self, page: Page):
        """Policy dropdown in task form lists created policies."""
        login(page)

        # First create a policy
        page.goto("/policies")
        page.wait_for_load_state("networkidle")
        page.click("text=+ Create Policy")
        page.wait_for_timeout(500)
        page.fill('input[id="policy-name"]', "Dropdown Test Policy")
        page.select_option('select[id="policy-lane"]', "http")
        page.click("button[type='submit']:has-text('Create Policy')")
        page.wait_for_timeout(1000)

        # Now go to tasks and open create form
        page.goto("/tasks")
        page.wait_for_load_state("networkidle")
        page.click("text=+ Create Task")
        page.wait_for_timeout(500)

        # The policy dropdown should contain our policy
        options = page.locator('select[id="task-policy"] option').all_text_contents()
        policy_found = any("Dropdown Test Policy" in opt for opt in options)
        assert policy_found, f"Policy not found in dropdown. Options: {options}"
