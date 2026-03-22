"""
Tests for services/worker-ai/worker.py — AI Normalization Worker (WORKER-003).
"""

from __future__ import annotations

from typing import Optional
from unittest.mock import AsyncMock

import pytest

from services.worker_ai.worker import (
    AINormalizationWorker,
    CANONICAL_FIELDS,
    _compute_confidence,
    _field_coverage,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class FakeAIProvider:
    """Minimal AI provider that uppercases the 'name' field for traceability."""

    def __init__(self) -> None:
        self._tokens = 0

    async def extract(self, html: str, url: str, prompt: Optional[str] = None) -> list[dict]:
        return []

    async def classify(self, text: str, labels: list[str]) -> str:
        return labels[0]

    async def normalize(self, data: dict, target_schema: dict) -> dict:
        self._tokens += 10
        result = dict(data)
        if "name" in result:
            result["name"] = result["name"].upper()
        # Simulate AI adding a missing canonical field
        result.setdefault("category", "AI-inferred")
        return result

    def get_token_usage(self) -> int:
        return self._tokens


class FailingAIProvider(FakeAIProvider):
    """AI provider whose normalize always raises."""

    async def normalize(self, data: dict, target_schema: dict) -> dict:
        raise RuntimeError("AI service unavailable")


@pytest.fixture
def fake_ai() -> FakeAIProvider:
    return FakeAIProvider()


@pytest.fixture
def failing_ai() -> FailingAIProvider:
    return FailingAIProvider()


def _make_result(items: list[dict], confidence: float = 0.7) -> dict:
    return {"extracted_data": items, "confidence": confidence, "task_id": "t-1"}


# ---------------------------------------------------------------------------
# Tests: deterministic normalization with messy field names
# ---------------------------------------------------------------------------


class TestDeterministicNormalization:
    """Verify that messy/aliased field names are mapped to canonical names."""

    @pytest.mark.asyncio
    async def test_field_aliases_are_resolved(self) -> None:
        worker = AINormalizationWorker()
        result = _make_result([
            {"product_name": "Widget", "cost": "$19.99", "img": "https://img.example.com/w.jpg"},
        ])
        out = await worker.normalize(result)
        item = out["extracted_data"][0]
        assert item["name"] == "Widget"
        assert item["price"] == "19.99"
        assert item["image_url"] == "https://img.example.com/w.jpg"

    @pytest.mark.asyncio
    async def test_price_cleaning(self) -> None:
        worker = AINormalizationWorker()
        result = _make_result([{"product_price": "  $1,299.00  "}])
        out = await worker.normalize(result)
        assert out["extracted_data"][0]["price"] == "1299.00"

    @pytest.mark.asyncio
    async def test_rating_cleaning(self) -> None:
        worker = AINormalizationWorker()
        result = _make_result([{"stars": "4.5 / 5 stars"}])
        out = await worker.normalize(result)
        assert out["extracted_data"][0]["rating"] == "4.5"

    @pytest.mark.asyncio
    async def test_url_cleaning_protocol(self) -> None:
        worker = AINormalizationWorker()
        result = _make_result([{"link": "//cdn.example.com/page"}])
        out = await worker.normalize(result)
        assert out["extracted_data"][0]["product_url"] == "https://cdn.example.com/page"

    @pytest.mark.asyncio
    async def test_empty_items_passthrough(self) -> None:
        worker = AINormalizationWorker()
        result = _make_result([])
        out = await worker.normalize(result)
        assert out["extracted_data"] == []


# ---------------------------------------------------------------------------
# Tests: deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    """Verify that duplicate items are merged / removed."""

    @pytest.mark.asyncio
    async def test_exact_url_dedup(self) -> None:
        worker = AINormalizationWorker()
        items = [
            {"title": "Widget A", "url": "https://example.com/a"},
            {"title": "Widget A copy", "url": "https://example.com/a"},
        ]
        out = await worker.normalize(_make_result(items))
        assert len(out["extracted_data"]) == 1

    @pytest.mark.asyncio
    async def test_fuzzy_name_dedup(self) -> None:
        worker = AINormalizationWorker()
        items = [
            {"title": "Super Widget Pro 3000", "cost": "$10"},
            {"title": "Super Widget Pro 3000", "cost": "$10"},
        ]
        out = await worker.normalize(_make_result(items))
        assert len(out["extracted_data"]) == 1

    @pytest.mark.asyncio
    async def test_distinct_items_kept(self) -> None:
        worker = AINormalizationWorker()
        items = [
            {"title": "Alpha Product", "cost": "$10"},
            {"title": "Beta Product", "cost": "$20"},
        ]
        out = await worker.normalize(_make_result(items))
        assert len(out["extracted_data"]) == 2


# ---------------------------------------------------------------------------
# Tests: AI fallback when confidence is low
# ---------------------------------------------------------------------------


class TestAIFallback:
    """Verify AI provider is invoked only when confidence < threshold."""

    @pytest.mark.asyncio
    async def test_ai_called_when_confidence_low(self, fake_ai: FakeAIProvider) -> None:
        worker = AINormalizationWorker(ai_provider=fake_ai, confidence_threshold=0.8)
        result = _make_result([{"title": "widget"}], confidence=0.3)
        out = await worker.normalize(result)
        # FakeAIProvider uppercases the name
        assert out["extracted_data"][0]["name"] == "WIDGET"
        # AI should have added category
        assert out["extracted_data"][0].get("category") == "AI-inferred"

    @pytest.mark.asyncio
    async def test_ai_not_called_when_confidence_high(self, fake_ai: FakeAIProvider) -> None:
        worker = AINormalizationWorker(ai_provider=fake_ai, confidence_threshold=0.5)
        result = _make_result([{"title": "widget"}], confidence=0.9)
        out = await worker.normalize(result)
        # Name should NOT be uppercased — AI was not called
        assert out["extracted_data"][0]["name"] == "widget"
        assert fake_ai.get_token_usage() == 0

    @pytest.mark.asyncio
    async def test_ai_failure_keeps_original(self, failing_ai: FailingAIProvider) -> None:
        worker = AINormalizationWorker(ai_provider=failing_ai, confidence_threshold=0.8)
        result = _make_result([{"title": "widget"}], confidence=0.2)
        out = await worker.normalize(result)
        # Should fall back to deterministic-only result
        assert out["extracted_data"][0]["name"] == "widget"

    @pytest.mark.asyncio
    async def test_no_ai_provider_skips_ai_step(self) -> None:
        worker = AINormalizationWorker(ai_provider=None, confidence_threshold=0.0)
        result = _make_result([{"title": "widget"}], confidence=0.0)
        out = await worker.normalize(result)
        # Should still produce a normalised result
        assert out["extracted_data"][0]["name"] == "widget"


# ---------------------------------------------------------------------------
# Tests: batch processing
# ---------------------------------------------------------------------------


class TestBatchProcessing:
    @pytest.mark.asyncio
    async def test_process_batch_returns_all(self) -> None:
        worker = AINormalizationWorker()
        results = [
            _make_result([{"title": "A"}], confidence=0.8),
            _make_result([{"title": "B"}], confidence=0.9),
            _make_result([{"title": "C"}], confidence=0.7),
        ]
        out = await worker.process_batch(results)
        assert len(out) == 3
        names = [r["extracted_data"][0]["name"] for r in out]
        assert names == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_batch_preserves_extra_keys(self) -> None:
        worker = AINormalizationWorker()
        result = {"extracted_data": [{"title": "X"}], "confidence": 0.9, "task_id": "t-42"}
        out = (await worker.process_batch([result]))[0]
        assert out["task_id"] == "t-42"


# ---------------------------------------------------------------------------
# Tests: passthrough when confidence is already high
# ---------------------------------------------------------------------------


class TestHighConfidencePassthrough:
    @pytest.mark.asyncio
    async def test_high_confidence_no_ai(self, fake_ai: FakeAIProvider) -> None:
        worker = AINormalizationWorker(ai_provider=fake_ai, confidence_threshold=0.5)
        result = _make_result(
            [{"name": "Already Clean", "price": "9.99"}],
            confidence=0.95,
        )
        out = await worker.normalize(result)
        # AI should NOT have been called
        assert fake_ai.get_token_usage() == 0
        assert out["extracted_data"][0]["name"] == "Already Clean"

    @pytest.mark.asyncio
    async def test_confidence_recalculated(self) -> None:
        worker = AINormalizationWorker()
        result = _make_result(
            [{"name": "Widget", "price": "10", "brand": "Acme"}],
            confidence=0.8,
        )
        out = await worker.normalize(result)
        # Confidence should be recalculated (blend of original + coverage)
        assert isinstance(out["confidence"], float)
        assert 0.0 <= out["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# Tests: helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_field_coverage_empty(self) -> None:
        assert _field_coverage({}) == 0.0

    def test_field_coverage_full(self) -> None:
        item = {f: "value" for f in CANONICAL_FIELDS}
        assert _field_coverage(item) == 1.0

    def test_field_coverage_partial(self) -> None:
        item = {"name": "X", "price": "10"}
        cov = _field_coverage(item)
        assert 0.0 < cov < 1.0
        assert cov == pytest.approx(2 / len(CANONICAL_FIELDS))

    def test_compute_confidence_blend(self) -> None:
        items = [{"name": "X", "price": "10"}]
        conf = _compute_confidence(items, 0.8)
        expected = round(0.6 * 0.8 + 0.4 * (2 / len(CANONICAL_FIELDS)), 4)
        assert conf == pytest.approx(expected)

    def test_compute_confidence_empty_items(self) -> None:
        assert _compute_confidence([], 0.5) == 0.5


# ---------------------------------------------------------------------------
# Tests: close
# ---------------------------------------------------------------------------


class TestClose:
    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        worker = AINormalizationWorker()
        await worker.close()
        await worker.close()  # should not raise
