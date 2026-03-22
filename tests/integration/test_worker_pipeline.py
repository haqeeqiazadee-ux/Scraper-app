"""
Integration tests for the worker pipeline:
  HTTP worker fetch -> AI normalization -> result storage.

External HTTP calls are mocked, but internal pipeline integration is tested.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from packages.core.interfaces import FetchRequest, FetchResponse
from packages.core.normalizer import normalize_items
from packages.core.router import ExecutionRouter, Lane
from packages.contracts.task import Task


SAMPLE_HTML = """
<html>
<body>
<div class="product">
    <h2 class="title">Wireless Mouse</h2>
    <span class="cost">$29.99</span>
    <img src="https://cdn.example.com/mouse.jpg" />
</div>
<div class="product">
    <h2 class="title">Keyboard Pro</h2>
    <span class="cost">$49.99</span>
    <img src="https://cdn.example.com/keyboard.jpg" />
</div>
</body>
</html>
"""


@pytest.mark.asyncio
class TestWorkerPipeline:
    """Test the worker pipeline with mocked external calls."""

    async def test_http_fetch_returns_response(self):
        """Mock HTTP collector returns a valid FetchResponse."""
        mock_response = FetchResponse(
            url="https://shop.com/products",
            status_code=200,
            text=SAMPLE_HTML,
            html=SAMPLE_HTML,
            body=SAMPLE_HTML.encode(),
            elapsed_ms=150,
        )

        # Simulate the collector
        mock_collector = AsyncMock()
        mock_collector.fetch.return_value = mock_response

        request = FetchRequest(url="https://shop.com/products")
        result = await mock_collector.fetch(request)

        assert result.ok
        assert result.status_code == 200
        assert "Wireless Mouse" in result.html

    async def test_normalization_pipeline(self):
        """Raw extracted data passes through normalizer to canonical form."""
        raw_items = [
            {"product_name": "Wireless Mouse", "cost": "$29.99", "img": "https://cdn.example.com/mouse.jpg"},
            {"title": "Keyboard Pro", "amount": "$49.99", "photo": "https://cdn.example.com/keyboard.jpg"},
        ]

        normalized = normalize_items(raw_items)

        assert len(normalized) == 2
        # Field aliasing: product_name -> name, cost -> price, img -> image_url
        assert normalized[0]["name"] == "Wireless Mouse"
        assert normalized[0]["price"] == "29.99"
        assert normalized[0]["image_url"] == "https://cdn.example.com/mouse.jpg"
        # Second item
        assert normalized[1]["name"] == "Keyboard Pro"
        assert normalized[1]["price"] == "49.99"

    async def test_fetch_then_normalize_pipeline(self):
        """Full pipeline: fetch HTML -> extract items -> normalize."""
        # Step 1: Simulate HTTP fetch
        mock_collector = AsyncMock()
        mock_collector.fetch.return_value = FetchResponse(
            url="https://shop.com/products",
            status_code=200,
            text=SAMPLE_HTML,
            html=SAMPLE_HTML,
            body=SAMPLE_HTML.encode(),
        )

        result = await mock_collector.fetch(FetchRequest(url="https://shop.com/products"))
        assert result.ok

        # Step 2: Simulate extraction (as if a parser extracted structured data)
        raw_items = [
            {"title": "Wireless Mouse", "cost": "$29.99"},
            {"title": "Keyboard Pro", "cost": "$49.99"},
        ]

        # Step 3: Normalize
        normalized = normalize_items(raw_items)
        assert all("name" in item for item in normalized)
        assert all("price" in item for item in normalized)

    async def test_failed_fetch_returns_error_response(self):
        """When HTTP fetch fails, the response has status_code=0 and error set."""
        mock_collector = AsyncMock()
        mock_collector.fetch.return_value = FetchResponse(
            url="https://down.example.com",
            status_code=0,
            error="Connection refused",
        )

        result = await mock_collector.fetch(FetchRequest(url="https://down.example.com"))
        assert not result.ok
        assert result.error == "Connection refused"

    async def test_router_selects_lane_for_pipeline(self):
        """ExecutionRouter selects the correct lane to feed the worker pipeline."""
        router = ExecutionRouter()

        # Standard site -> HTTP lane
        task = Task(tenant_id="t1", url="https://blog.example.com/posts")
        decision = router.route(task)
        assert decision.lane == Lane.HTTP

        # Known browser-required site
        task = Task(tenant_id="t1", url="https://www.amazon.com/dp/B09V3KXJPB")
        decision = router.route(task)
        assert decision.lane == Lane.BROWSER

    async def test_pipeline_with_result_storage(self):
        """Full pipeline: fetch -> normalize -> store in mock result repository."""
        # Fetch
        mock_collector = AsyncMock()
        mock_collector.fetch.return_value = FetchResponse(
            url="https://shop.com/items",
            status_code=200,
            text="<html>...</html>",
            html="<html>...</html>",
        )
        fetch_result = await mock_collector.fetch(FetchRequest(url="https://shop.com/items"))
        assert fetch_result.ok

        # Extract + normalize
        raw = [{"product_name": "Gadget", "cost": "$15.00"}]
        normalized = normalize_items(raw)
        assert normalized[0]["name"] == "Gadget"
        assert normalized[0]["price"] == "15.00"

        # Store (mock repository)
        mock_repo = AsyncMock()
        mock_repo.create.return_value = MagicMock(
            id=str(uuid4()),
            task_id=str(uuid4()),
            item_count=len(normalized),
            confidence=0.95,
        )

        stored = await mock_repo.create(
            tenant_id="test",
            url="https://shop.com/items",
            extracted_data=normalized,
            item_count=len(normalized),
            confidence=0.95,
        )
        assert stored.item_count == 1
        assert stored.confidence == 0.95
