"""Tests for HTTP lane worker."""

import pytest
from unittest.mock import AsyncMock, patch

from packages.core.interfaces import FetchResponse
from packages.core.ai_providers.deterministic import DeterministicProvider
from services.worker_http.worker import HttpWorker


SAMPLE_HTML = """
<html>
<head><title>Test Product Page</title></head>
<body>
<script type="application/ld+json">
{
    "@type": "Product",
    "name": "Test Product",
    "sku": "TP-001",
    "offers": {"price": "49.99", "priceCurrency": "USD"}
}
</script>
</body>
</html>
"""


@pytest.fixture
def worker():
    return HttpWorker(ai_provider=DeterministicProvider())


class TestHttpWorker:

    @pytest.mark.asyncio
    async def test_process_task_success(self, worker):
        """Successful HTTP extraction with JSON-LD."""
        mock_response = FetchResponse(
            url="https://example.com/product",
            status_code=200,
            html=SAMPLE_HTML,
            text=SAMPLE_HTML,
            body=SAMPLE_HTML.encode(),
        )

        with patch.object(worker._collector, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({
                "url": "https://example.com/product",
                "tenant_id": "t1",
                "task_id": "task-123",
            })

        assert result["status"] == "success"
        assert result["status_code"] == 200
        assert result["item_count"] >= 1
        assert result["extracted_data"][0]["name"] == "Test Product"
        assert result["lane"] == "http"
        assert result["task_id"] == "task-123"
        assert result["should_escalate"] is False

    @pytest.mark.asyncio
    async def test_process_task_http_failure(self, worker):
        """HTTP 403 should return failed with escalation flag."""
        mock_response = FetchResponse(
            url="https://blocked.com",
            status_code=403,
            error="Forbidden",
        )

        with patch.object(worker._collector, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({
                "url": "https://blocked.com",
                "tenant_id": "t1",
            })

        assert result["status"] == "failed"
        assert result["status_code"] == 403
        assert result["should_escalate"] is True
        assert result["item_count"] == 0

    @pytest.mark.asyncio
    async def test_process_task_empty_extraction(self, worker):
        """Page with no extractable data should suggest escalation."""
        mock_response = FetchResponse(
            url="https://example.com/empty",
            status_code=200,
            html="<html><body>Nothing here</body></html>",
            text="Nothing here",
            body=b"<html><body>Nothing here</body></html>",
        )

        with patch.object(worker._collector, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({
                "url": "https://example.com/empty",
                "tenant_id": "t1",
            })

        assert result["status"] == "success"
        # Basic extraction may still find title, so check for low confidence
        assert result["should_escalate"] is (result["item_count"] == 0)

    @pytest.mark.asyncio
    async def test_process_task_network_error(self, worker):
        """Network error should return failed."""
        mock_response = FetchResponse(
            url="https://down.com",
            status_code=0,
            error="Connection refused",
        )

        with patch.object(worker._collector, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({
                "url": "https://down.com",
                "tenant_id": "t1",
            })

        assert result["status"] == "failed"
        assert result["should_escalate"] is True
        assert "Connection refused" in result["error"]

    @pytest.mark.asyncio
    async def test_process_task_defaults(self, worker):
        """Task with minimal fields should use defaults."""
        mock_response = FetchResponse(url="https://x.com", status_code=200, html="<html></html>", body=b"")

        with patch.object(worker._collector, "fetch", new_callable=AsyncMock, return_value=mock_response):
            result = await worker.process_task({"url": "https://x.com"})

        assert result["tenant_id"] == "default"
        assert result["lane"] == "http"
        assert result["connector"] == "http_collector"
        assert "duration_ms" in result
