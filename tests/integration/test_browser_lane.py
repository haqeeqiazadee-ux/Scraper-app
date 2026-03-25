"""
Integration tests for browser lane — tab switching and crash recovery.

Covers:
  UC-7.4.2 — Tab switching: multiple pages in same context
  UC-7.7.2 — Tab crash recovery: graceful handling of page crashes
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.core.interfaces import FetchRequest


class TestTabSwitching:
    """UC-7.4.2 — Browser can switch between tabs/pages."""

    @pytest.mark.asyncio
    async def test_multiple_pages_in_context(self):
        """Browser worker can create multiple pages (tabs) in a context."""
        from packages.connectors.browser_worker import PlaywrightBrowserWorker

        worker = PlaywrightBrowserWorker(headless=True)

        # Mock the browser and context
        mock_browser = AsyncMock()
        mock_context = AsyncMock()

        # Create distinct mock pages
        mock_page1 = AsyncMock()
        mock_page1.url = "https://example.com/page1"
        mock_page1.content = AsyncMock(return_value="<html><body>Page 1</body></html>")
        mock_page1.goto = AsyncMock(return_value=MagicMock(status=200))

        mock_page2 = AsyncMock()
        mock_page2.url = "https://example.com/page2"
        mock_page2.content = AsyncMock(return_value="<html><body>Page 2</body></html>")
        mock_page2.goto = AsyncMock(return_value=MagicMock(status=200))

        mock_context.new_page = AsyncMock(side_effect=[mock_page1, mock_page2])
        mock_browser.new_context = AsyncMock(return_value=mock_context)

        worker._browser = mock_browser

        # Fetch two pages sequentially (simulating tab switching)
        req1 = FetchRequest(url="https://example.com/page1")
        resp1 = await worker.fetch(req1)
        assert resp1.ok

        req2 = FetchRequest(url="https://example.com/page2")
        resp2 = await worker.fetch(req2)
        assert resp2.ok

        # Both pages were created
        assert mock_browser.new_context.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_returns_html_content(self):
        """Fetch returns the rendered HTML content."""
        from packages.connectors.browser_worker import PlaywrightBrowserWorker

        worker = PlaywrightBrowserWorker(headless=True)

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_page.url = "https://example.com"
        mock_page.content = AsyncMock(return_value="<html><body>Test Content</body></html>")
        mock_page.goto = AsyncMock(return_value=MagicMock(status=200))
        mock_page.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        worker._browser = mock_browser

        req = FetchRequest(url="https://example.com")
        resp = await worker.fetch(req)

        assert resp.ok
        assert "Test Content" in (resp.html or resp.text)


class TestCrashRecovery:
    """UC-7.7.2 — Browser handles page crashes gracefully."""

    @pytest.mark.asyncio
    async def test_page_crash_returns_failure(self):
        """When a page crashes/errors, fetch returns a failed response."""
        from packages.connectors.browser_worker import PlaywrightBrowserWorker

        worker = PlaywrightBrowserWorker(headless=True)

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Simulate page crash during goto
        mock_page.goto = AsyncMock(side_effect=Exception("Page crashed"))
        mock_page.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        worker._browser = mock_browser

        req = FetchRequest(url="https://example.com/crash")
        resp = await worker.fetch(req)

        assert not resp.ok
        assert resp.error is not None

    @pytest.mark.asyncio
    async def test_timeout_returns_failure(self):
        """When page times out, fetch returns a failed response."""
        from packages.connectors.browser_worker import PlaywrightBrowserWorker

        worker = PlaywrightBrowserWorker(headless=True)

        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        from playwright.async_api import TimeoutError as PlaywrightTimeout
        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeout("Timeout 30000ms exceeded"))
        mock_page.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        worker._browser = mock_browser

        req = FetchRequest(url="https://example.com/slow", timeout_ms=1000)
        resp = await worker.fetch(req)

        assert not resp.ok

    @pytest.mark.asyncio
    async def test_recovery_after_crash(self):
        """After a crash, the next fetch still works (new context)."""
        from packages.connectors.browser_worker import PlaywrightBrowserWorker

        worker = PlaywrightBrowserWorker(headless=True)

        mock_browser = AsyncMock()

        # First context/page: crash
        crash_page = AsyncMock()
        crash_page.goto = AsyncMock(side_effect=Exception("Page crashed"))
        crash_page.close = AsyncMock()
        crash_context = AsyncMock()
        crash_context.new_page = AsyncMock(return_value=crash_page)
        crash_context.close = AsyncMock()

        # Second context/page: success
        ok_page = AsyncMock()
        ok_page.url = "https://example.com/ok"
        ok_page.content = AsyncMock(return_value="<html>OK</html>")
        ok_page.goto = AsyncMock(return_value=MagicMock(status=200))
        ok_page.close = AsyncMock()
        ok_context = AsyncMock()
        ok_context.new_page = AsyncMock(return_value=ok_page)
        ok_context.close = AsyncMock()

        mock_browser.new_context = AsyncMock(side_effect=[crash_context, ok_context])
        worker._browser = mock_browser

        # First: crash
        req1 = FetchRequest(url="https://example.com/crash")
        resp1 = await worker.fetch(req1)
        assert not resp1.ok

        # Second: recovery
        req2 = FetchRequest(url="https://example.com/ok")
        resp2 = await worker.fetch(req2)
        assert resp2.ok

    @pytest.mark.asyncio
    async def test_close_cleans_up(self):
        """Calling close() cleans up browser resources."""
        from packages.connectors.browser_worker import PlaywrightBrowserWorker

        worker = PlaywrightBrowserWorker(headless=True)

        mock_browser = AsyncMock()
        mock_pw = AsyncMock()
        worker._browser = mock_browser
        worker._playwright = mock_pw

        await worker.close()

        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()
