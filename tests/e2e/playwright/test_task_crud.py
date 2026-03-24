"""
E2E tests for Task CRUD UI.

Covers:
  UC-3.1.1 — Navigate to Tasks → Click "Create Task" → form renders
  UC-3.2.1 — Task list page loads with pagination
  UC-3.2.3 — Task detail shows run history (initially empty)
  UC-3.4.2 — Confirm dialog shown before deletion
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, BrowserContext, expect


def login(page: Page) -> None:
    """Helper: log in and land on dashboard."""
    # Clear any stale auth state
    page.goto("/login")
    page.evaluate("localStorage.clear()")
    page.goto("/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[id="login-username"]', "testuser")
    page.fill('input[id="login-password"]', "testpass123")
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard", timeout=15000)


class TestTaskListPage:
    """UC-3.2.1 — Task list renders."""

    def test_tasks_page_loads(self, page: Page):
        """Navigate to tasks page, verify it renders."""
        login(page)
        page.goto("/tasks")
        page.wait_for_load_state("networkidle")

        # Page header
        expect(page.locator("h2")).to_contain_text("Tasks")

        # "Create Task" button visible
        create_btn = page.locator("text=Create Task")
        expect(create_btn).to_be_visible()

    def test_tasks_page_shows_empty_state(self, page: Page):
        """When no tasks exist, empty state message is shown."""
        login(page)
        page.goto("/tasks")
        page.wait_for_load_state("networkidle")

        # Should show "No tasks found" or "0 tasks"
        body = page.locator("body").inner_text()
        assert "0 task" in body or "No tasks" in body, f"Expected empty state, got: {body[:200]}"

    def test_status_filter_buttons_visible(self, page: Page):
        """Filter bar shows All/Pending/Running/Completed/Failed/Cancelled."""
        login(page)
        page.goto("/tasks")
        page.wait_for_load_state("networkidle")

        for status in ["All", "Pending", "Running", "Completed", "Failed", "Cancelled"]:
            expect(page.locator(f"button:has-text('{status}')")).to_be_visible()


class TestTaskForm:
    """UC-3.1.1 — Create Task form renders in modal."""

    def test_create_task_form_opens(self, page: Page):
        """Clicking 'Create Task' opens a modal with the form."""
        login(page)
        page.goto("/tasks")
        page.wait_for_load_state("networkidle")

        page.click("text=Create Task")
        page.wait_for_timeout(500)

        # Form should be visible in a modal
        expect(page.locator("h3:has-text('Create Task')")).to_be_visible()
        expect(page.locator('input[id="task-name"]')).to_be_visible()
        expect(page.locator('input[id="task-url"]')).to_be_visible()
        expect(page.locator('select[id="task-extraction-type"]')).to_be_visible()
        expect(page.locator('select[id="task-policy"]')).to_be_visible()
        expect(page.locator('input[id="task-priority"]')).to_be_visible()

    def test_create_task_form_validates(self, page: Page):
        """Submitting empty form shows validation errors."""
        login(page)
        page.goto("/tasks")
        page.wait_for_load_state("networkidle")

        page.click("text=Create Task")
        page.wait_for_timeout(500)

        # Submit empty form
        page.click("button:has-text('Create Task'):not(:has-text('+'))")
        page.wait_for_timeout(300)

        # Validation errors should appear
        errors = page.locator(".form-error").all()
        assert len(errors) >= 1, "Expected validation errors for empty form"

    def test_create_and_list_task(self, page: Page):
        """Create a task via the form and verify it appears in the list."""
        login(page)
        page.goto("/tasks")
        page.wait_for_load_state("networkidle")

        # Open form
        page.click("text=+ Create Task")
        page.wait_for_timeout(500)

        # Fill form
        page.fill('input[id="task-name"]', "E2E Test Task")
        page.fill('input[id="task-url"]', "https://example.com/products")

        # Submit — click the submit button inside the form
        page.click(".task-form button[type='submit']")
        page.wait_for_timeout(1000)

        # Task should appear in the list
        page.wait_for_load_state("networkidle")
        body = page.locator("body").inner_text()
        assert "E2E Test Task" in body, f"Created task not found in list: {body[:300]}"


class TestTaskDetail:
    """UC-3.2.3 — Task detail shows run history."""

    def test_task_detail_page_shows_run_history(self, page: Page):
        """Navigate to a task detail page and verify run history section."""
        login(page)
        page.goto("/tasks")
        page.wait_for_load_state("networkidle")

        # Create a task first
        page.click("text=+ Create Task")
        page.wait_for_timeout(500)
        page.fill('input[id="task-name"]', "Detail Test Task")
        page.fill('input[id="task-url"]', "https://example.com/detail")
        page.click(".task-form button[type='submit']")
        page.wait_for_timeout(1000)
        page.wait_for_load_state("networkidle")

        # Click on the task name to go to detail
        page.click("text=Detail Test Task")
        page.wait_for_load_state("networkidle")

        # Should show run history section
        expect(page.get_by_role("heading", name="Run History")).to_be_visible()


class TestTaskDelete:
    """UC-3.4.2 — Confirm dialog before deletion."""

    def test_delete_shows_confirm_dialog(self, page: Page):
        """Clicking Delete shows Confirm/No buttons, not immediate deletion."""
        login(page)
        page.goto("/tasks")
        page.wait_for_load_state("networkidle")

        # Create a task first
        page.click("text=+ Create Task")
        page.wait_for_timeout(500)
        page.fill('input[id="task-name"]', "Delete Test Task")
        page.fill('input[id="task-url"]', "https://example.com/delete")
        page.click(".task-form button[type='submit']")
        page.wait_for_timeout(1000)
        page.wait_for_load_state("networkidle")

        # Click Delete button
        page.click("button:has-text('Delete')")
        page.wait_for_timeout(300)

        # Confirm dialog should appear
        expect(page.locator("button:has-text('Confirm')")).to_be_visible()
        expect(page.locator("button:has-text('No')")).to_be_visible()

    def test_delete_cancel_via_no(self, page: Page):
        """Clicking 'No' in confirm dialog cancels the deletion."""
        login(page)
        page.goto("/tasks")
        page.wait_for_load_state("networkidle")

        # Create a task
        page.click("text=+ Create Task")
        page.wait_for_timeout(500)
        page.fill('input[id="task-name"]', "Keep This Task")
        page.fill('input[id="task-url"]', "https://example.com/keep")
        page.click(".task-form button[type='submit']")
        page.wait_for_timeout(1000)
        page.wait_for_load_state("networkidle")

        # Click Delete, then No
        page.click("button:has-text('Delete')")
        page.wait_for_timeout(300)
        page.click("button:has-text('No')")
        page.wait_for_timeout(300)

        # Task should still be there
        body = page.locator("body").inner_text()
        assert "Keep This Task" in body
