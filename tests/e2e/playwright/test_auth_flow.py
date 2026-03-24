"""
E2E tests for authentication flow.

Covers:
  UC-1.3.1 — Web dashboard loads at deployed URL
  UC-1.3.2 — Login page renders at /login
  UC-1.3.3 — Browser console shows no CORS errors on API calls
  UC-1.3.4 — API_URL environment variable points to correct backend
  UC-2.1.3 — Access /dashboard without login → redirected to /login
  UC-2.1.4 — JWT token stored in browser after successful login
  UC-2.2.1 — Refresh page while logged in → stays logged in
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, BrowserContext, expect


class TestLoginPage:
    """UC-1.3.2 — Login page renders correctly."""

    def test_login_page_renders(self, page: Page):
        """Login page loads and shows the sign-in form."""
        page.goto("/login")
        page.wait_for_load_state("networkidle")

        # Title/heading visible
        expect(page.locator("h1")).to_contain_text("Scraper AI Platform")

        # Form elements present
        expect(page.locator('input[id="login-username"]')).to_be_visible()
        expect(page.locator('input[id="login-password"]')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_contain_text("Sign In")

    def test_login_page_has_register_toggle(self, page: Page):
        """Login page has a toggle to switch to registration mode."""
        page.goto("/login")
        page.wait_for_load_state("networkidle")

        # Click "Create one" to switch to register mode
        page.click("text=Create one")
        expect(page.locator('button[type="submit"]')).to_contain_text("Create Account")

        # Click "Sign in" to switch back
        page.click("text=Sign in")
        expect(page.locator('button[type="submit"]')).to_contain_text("Sign In")


class TestDashboardRedirect:
    """UC-2.1.3 — Unauthenticated users are redirected to login."""

    def test_dashboard_redirects_to_login(self, page: Page):
        """Accessing /dashboard without login redirects to /login."""
        page.goto("/dashboard")
        page.wait_for_url("**/login", timeout=5000)
        expect(page.locator('input[id="login-username"]')).to_be_visible()

    def test_tasks_redirects_to_login(self, page: Page):
        """Accessing /tasks without login redirects to /login."""
        page.goto("/tasks")
        page.wait_for_url("**/login", timeout=5000)

    def test_root_redirects_to_login(self, page: Page):
        """Accessing / without login redirects to /login."""
        page.goto("/")
        page.wait_for_url("**/login", timeout=5000)


class TestLoginFlow:
    """UC-2.1.4, UC-1.3.3 — Login flow and JWT storage."""

    def test_successful_login(self, page: Page):
        """Login with valid credentials stores JWT and redirects to dashboard."""
        # Track console errors for CORS check
        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        page.goto("/login")
        page.wait_for_load_state("networkidle")

        # Fill credentials
        page.fill('input[id="login-username"]', "testuser")
        page.fill('input[id="login-password"]', "testpass123")
        page.click('button[type="submit"]')

        # Should redirect to dashboard
        page.wait_for_url("**/dashboard", timeout=10000)

        # UC-2.1.4 — JWT stored in localStorage
        token = page.evaluate("localStorage.getItem('auth_token')")
        assert token is not None, "JWT token should be stored in localStorage"
        assert len(token) > 20, "JWT token should be a non-trivial string"

        # UC-1.3.3 — No CORS errors
        cors_errors = [e for e in console_errors if "CORS" in e.upper()]
        assert len(cors_errors) == 0, f"CORS errors detected: {cors_errors}"

    def test_login_disables_button_when_empty(self, page: Page):
        """Submit button is disabled when fields are empty."""
        page.goto("/login")
        page.wait_for_load_state("networkidle")

        submit = page.locator('button[type="submit"]')
        expect(submit).to_be_disabled()

        # Fill only username
        page.fill('input[id="login-username"]', "user")
        expect(submit).to_be_disabled()

        # Fill password too — should become enabled
        page.fill('input[id="login-password"]', "pass")
        expect(submit).to_be_enabled()


class TestSessionPersistence:
    """UC-2.2.1 — Session persists across page refreshes."""

    def test_refresh_stays_logged_in(self, page: Page):
        """After login, refreshing the page keeps the user authenticated."""
        # Login first
        page.goto("/login")
        page.wait_for_load_state("networkidle")
        page.fill('input[id="login-username"]', "testuser")
        page.fill('input[id="login-password"]', "testpass123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/dashboard", timeout=10000)

        # Refresh the page
        page.reload()
        page.wait_for_load_state("networkidle")

        # Should still be on dashboard, not redirected to login
        assert "/dashboard" in page.url, f"Expected /dashboard, got {page.url}"

        # Token should still be in localStorage
        token = page.evaluate("localStorage.getItem('auth_token')")
        assert token is not None, "JWT token should persist after refresh"


class TestDashboardLoads:
    """UC-1.3.1 — Dashboard loads and renders."""

    def test_dashboard_renders_after_login(self, page: Page):
        """Dashboard page loads with expected content after authentication."""
        # Login
        page.goto("/login")
        page.wait_for_load_state("networkidle")
        page.fill('input[id="login-username"]', "testuser")
        page.fill('input[id="login-password"]', "testpass123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/dashboard", timeout=10000)
        page.wait_for_load_state("networkidle")

        # Dashboard should have some meaningful content
        body_text = page.locator("body").inner_text()
        assert len(body_text) > 50, "Dashboard should render substantial content"

    def test_api_url_points_to_backend(self, page: Page):
        """UC-1.3.4 — API calls go through proxy to the correct backend."""
        page.goto("/login")
        page.wait_for_load_state("networkidle")

        # Make a direct API call via the page context to verify proxy works
        response = page.evaluate("""
            async () => {
                const resp = await fetch('/api/v1/health');
                return { status: resp.status, ok: resp.ok };
            }
        """)
        assert response["ok"], f"API health check failed: {response}"
        assert response["status"] == 200
