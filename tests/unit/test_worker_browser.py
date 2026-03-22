"""Tests for Browser lane worker."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.core.interfaces import FetchResponse
from packages.core.ai_providers.deterministic import DeterministicProvider
from services.worker_browser.worker import BrowserLaneWorker


SAMPLE_HTML = """
<html>
<head><title>Test Product Page</title></head>
<body>
<script type="application/ld+json">
{
    "@type": "Product",
    "name": "Browser Product",
    "sku": "BP-001",
    "offers": {"price": "79.99", "priceCurrency": "USD"}
}
</script>
</body>
</html>
"""

EMPTY_HTML = "<html><body>Nothing here</body></html>"


@pytest.fixture
def worker():
    return BrowserLaneWorker(ai_provider=DeterministicProvider(), headless=True)


def _ok_response(url: str = "https://example.com/product", html: str = SAMPLE_HTML) -> FetchResponse:
    """Helper to create a successful FetchResponse."""
    return FetchResponse(
        url=url,
        status_code=200,
        html=html,
        text=html,
        body=html.encode("utf-8"),
    )


def _failed_response(url: str = "https://blocked.com", status_code: int = 0, error: str = "Timeout") -> FetchResponse:
    """Helper to create a failed FetchResponse."""
    return FetchResponse(
        url=url,
        status_code=status_code,
        error=error,
    )


class TestBrowserLaneWorker:

    @pytest.mark.asyncio
    async def test_process_task_success(self, worker):
        """Successful browser extraction with JSON-LD."""
        mock_response = _ok_response()

        with patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({
                "url": "https://example.com/product",
                "tenant_id": "t1",
                "task_id": "task-browser-1",
            })

        assert result["status"] == "success"
        assert result["status_code"] == 200
        assert result["item_count"] >= 1
        assert result["extracted_data"][0]["name"] == "Browser Product"
        assert result["lane"] == "browser"
        assert result["connector"] == "playwright_browser"
        assert result["task_id"] == "task-browser-1"
        assert result["should_escalate"] is False
        assert result["scrolled"] is False
        assert result["waited_for_selector"] is False

    @pytest.mark.asyncio
    async def test_process_task_fetch_failure_status_zero(self, worker):
        """Browser fetch with status 0 (network error) returns failed with escalation."""
        mock_response = _failed_response(
            url="https://down.com", status_code=0, error="Connection refused",
        )

        with patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({
                "url": "https://down.com",
                "tenant_id": "t1",
            })

        assert result["status"] == "failed"
        assert result["status_code"] == 0
        assert result["should_escalate"] is True
        assert result["item_count"] == 0
        assert "Connection refused" in result["error"]

    @pytest.mark.asyncio
    async def test_process_task_fetch_failure_403(self, worker):
        """Browser fetch with HTTP 403 returns failed with escalation."""
        mock_response = FetchResponse(
            url="https://blocked.com",
            status_code=403,
            error="Forbidden",
        )

        with patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({
                "url": "https://blocked.com",
                "tenant_id": "t1",
            })

        assert result["status"] == "failed"
        assert result["status_code"] == 403
        assert result["should_escalate"] is True
        assert result["item_count"] == 0
        assert result["lane"] == "browser"

    @pytest.mark.asyncio
    async def test_scroll_behavior(self, worker):
        """When scroll=True, scroll_to_bottom and get_page_html are called."""
        mock_response = _ok_response()
        scrolled_html = SAMPLE_HTML  # same content, but proving the path is taken

        with (
            patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response),
            patch.object(worker._browser_worker, "scroll_to_bottom", new_callable=AsyncMock, return_value=5000) as mock_scroll,
            patch.object(worker._browser_worker, "get_page_html", new_callable=AsyncMock, return_value=scrolled_html) as mock_html,
        ):
            result = await worker.process_task({
                "url": "https://example.com/infinite",
                "tenant_id": "t1",
                "scroll": True,
                "max_scrolls": 10,
            })

            assert result["status"] == "success"
            assert result["scrolled"] is True
            mock_scroll.assert_awaited_once_with(max_scrolls=10)
            mock_html.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_scroll_default_max_scrolls(self, worker):
        """When scroll=True without max_scrolls, uses default of 50."""
        mock_response = _ok_response()

        with (
            patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response),
            patch.object(worker._browser_worker, "scroll_to_bottom", new_callable=AsyncMock, return_value=5000) as mock_scroll,
            patch.object(worker._browser_worker, "get_page_html", new_callable=AsyncMock, return_value=SAMPLE_HTML),
        ):
            result = await worker.process_task({
                "url": "https://example.com/scroll",
                "tenant_id": "t1",
                "scroll": True,
            })

            mock_scroll.assert_awaited_once_with(max_scrolls=50)
            assert result["scrolled"] is True

    @pytest.mark.asyncio
    async def test_wait_for_selector_behavior(self, worker):
        """When wait_selector is provided, wait_for_selector is called."""
        mock_response = _ok_response()

        with (
            patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response),
            patch.object(worker._browser_worker, "wait_for_selector", new_callable=AsyncMock, return_value=True) as mock_wait,
            patch.object(worker._browser_worker, "get_page_html", new_callable=AsyncMock, return_value=SAMPLE_HTML) as mock_html,
        ):
            result = await worker.process_task({
                "url": "https://example.com/spa",
                "tenant_id": "t1",
                "wait_selector": ".product-card",
                "wait_timeout_ms": 10000,
            })

            assert result["status"] == "success"
            assert result["waited_for_selector"] is True
            mock_wait.assert_awaited_once_with(
                ".product-card", timeout_ms=10000,
            )
            mock_html.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_wait_for_selector_not_found(self, worker):
        """When wait_for_selector returns False, waited_for_selector is False and initial HTML is used."""
        mock_response = _ok_response()

        with (
            patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response),
            patch.object(worker._browser_worker, "wait_for_selector", new_callable=AsyncMock, return_value=False),
        ):
            result = await worker.process_task({
                "url": "https://example.com/spa",
                "tenant_id": "t1",
                "wait_selector": ".never-appears",
            })

        assert result["status"] == "success"
        assert result["waited_for_selector"] is False
        # get_page_html should NOT be called since waited_for_selector is False and scroll is False
        # extraction still proceeds with the initial response HTML

    @pytest.mark.asyncio
    async def test_should_escalate_when_empty_results(self, worker):
        """Empty extraction should set should_escalate to True."""
        mock_response = FetchResponse(
            url="https://example.com/empty",
            status_code=200,
            html=EMPTY_HTML,
            text=EMPTY_HTML,
            body=EMPTY_HTML.encode("utf-8"),
        )

        # Use a provider that returns nothing
        mock_ai = AsyncMock()
        mock_ai.extract = AsyncMock(return_value=[])
        worker._ai = mock_ai

        with patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({
                "url": "https://example.com/empty",
                "tenant_id": "t1",
            })

        assert result["status"] == "success"
        assert result["item_count"] == 0
        assert result["should_escalate"] is True
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_with_ai_provider(self, worker):
        """When a non-deterministic AI provider is used, extraction_method reflects it."""
        mock_ai = AsyncMock()
        mock_ai.extract = AsyncMock(return_value=[{"name": "AI Product", "price": "99.99"}])
        worker._ai = mock_ai

        mock_response = _ok_response(html="<html><body>some content</body></html>")

        with patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({
                "url": "https://example.com/ai-page",
                "tenant_id": "t1",
            })

        assert result["status"] == "success"
        assert result["extraction_method"] == "ai"
        assert result["item_count"] == 1
        assert result["extracted_data"][0]["name"] == "AI Product"
        assert result["confidence"] > 0
        mock_ai.extract.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_confidence_calculation(self, worker):
        """Confidence should be ratio of filled fields to total fields."""
        mock_ai = AsyncMock()
        # 4 fields, 2 filled -> confidence = 0.5
        mock_ai.extract = AsyncMock(return_value=[
            {"name": "Product", "price": "", "sku": "ABC", "description": ""},
        ])
        worker._ai = mock_ai

        mock_response = _ok_response()

        with patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({
                "url": "https://example.com/partial",
                "tenant_id": "t1",
            })

        assert result["confidence"] == 0.5
        assert result["should_escalate"] is False

    @pytest.mark.asyncio
    async def test_process_task_defaults(self, worker):
        """Task with minimal fields should use defaults."""
        mock_response = _ok_response(url="https://x.com", html="<html></html>")

        with patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({"url": "https://x.com"})

        assert result["tenant_id"] == "default"
        assert result["lane"] == "browser"
        assert result["connector"] == "playwright_browser"
        assert "duration_ms" in result
        assert "run_id" in result
        assert "task_id" in result

    @pytest.mark.asyncio
    async def test_scroll_and_wait_combined(self, worker):
        """Both scroll and wait_selector can be used together."""
        mock_response = _ok_response()

        with (
            patch.object(worker._browser_worker, "fetch", new_callable=AsyncMock, return_value=mock_response),
            patch.object(worker._browser_worker, "scroll_to_bottom", new_callable=AsyncMock, return_value=8000) as mock_scroll,
            patch.object(worker._browser_worker, "wait_for_selector", new_callable=AsyncMock, return_value=True) as mock_wait,
            patch.object(worker._browser_worker, "get_page_html", new_callable=AsyncMock, return_value=SAMPLE_HTML) as mock_html,
        ):
            result = await worker.process_task({
                "url": "https://example.com/combo",
                "tenant_id": "t1",
                "scroll": True,
                "wait_selector": ".loaded",
            })

            assert result["scrolled"] is True
            assert result["waited_for_selector"] is True
            mock_scroll.assert_awaited_once()
            mock_wait.assert_awaited_once()
            mock_html.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close(self, worker):
        """Close should delegate to browser worker."""
        with patch.object(worker._browser_worker, "close", new_callable=AsyncMock) as mock_close:
            await worker.close()
            mock_close.assert_awaited_once()
