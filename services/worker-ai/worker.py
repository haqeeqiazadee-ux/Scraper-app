"""
AI Normalization Worker — WORKER-003

Takes raw extraction results and normalizes them using deterministic
normalization first, then optionally AI-based schema mapping when
confidence is below a configurable threshold.

Pipeline per result:
  1. Deterministic field normalization (normalize_items)
  2. Deduplication (DedupEngine)
  3. Optional AI schema mapping when confidence < threshold
  4. Confidence recalculation
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from packages.core.dedup import DedupEngine
from packages.core.interfaces import AIProvider
from packages.core.normalizer import normalize_items

logger = logging.getLogger(__name__)

# Canonical fields we expect in a well-normalised product record.
CANONICAL_FIELDS = frozenset({
    "name", "price", "original_price", "image_url", "product_url",
    "description", "rating", "reviews_count", "stock_status",
    "brand", "category", "sku", "currency",
})

# Target schema passed to AI provider for normalisation.
TARGET_SCHEMA: dict[str, str] = {f: "string" for f in CANONICAL_FIELDS}


def _field_coverage(item: dict) -> float:
    """Return the fraction of canonical fields that have non-empty values."""
    if not item:
        return 0.0
    filled = sum(
        1 for f in CANONICAL_FIELDS
        if str(item.get(f, "")).strip()
    )
    return filled / len(CANONICAL_FIELDS)


def _compute_confidence(items: list[dict], base_confidence: float) -> float:
    """Recompute confidence based on field coverage of normalised items."""
    if not items:
        return base_confidence
    avg_coverage = sum(_field_coverage(it) for it in items) / len(items)
    # Blend: 60 % original confidence + 40 % field-coverage signal.
    return round(0.6 * base_confidence + 0.4 * avg_coverage, 4)


class AINormalizationWorker:
    """Worker that normalises raw extraction results.

    Parameters
    ----------
    ai_provider:
        Optional ``AIProvider`` implementation used for AI-assisted
        schema mapping when deterministic normalisation yields low
        confidence.  If *None*, only deterministic normalisation is
        performed.
    confidence_threshold:
        Results with a confidence **below** this value will be sent to
        the AI provider for additional normalisation (if one is
        configured).
    similarity_threshold:
        Threshold passed to ``DedupEngine`` for fuzzy duplicate
        detection.
    """

    def __init__(
        self,
        ai_provider: Optional[AIProvider] = None,
        confidence_threshold: float = 0.5,
        similarity_threshold: float = 0.85,
    ) -> None:
        self._ai_provider = ai_provider
        self._confidence_threshold = confidence_threshold
        self._dedup = DedupEngine(similarity_threshold=similarity_threshold)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def normalize(self, result: dict) -> dict:
        """Normalise a single extraction result dict.

        Expected *result* shape::

            {
                "extracted_data": [ {…}, {…}, … ],
                "confidence": 0.65,
                ...                       # other keys are preserved
            }

        Returns a **new** dict with the same shape but normalised /
        deduplicated ``extracted_data`` and an updated ``confidence``.
        """
        result = dict(result)  # shallow copy — don't mutate caller's dict
        raw_items: list[dict] = result.get("extracted_data", [])
        confidence: float = float(result.get("confidence", 0.0))

        if not raw_items:
            result["extracted_data"] = []
            result["confidence"] = confidence
            return result

        # Step 1 — deterministic normalisation
        items = normalize_items(raw_items)

        # Step 2 — deduplication
        items = self._dedup.deduplicate(items)

        # Step 3 — optional AI normalisation for low-confidence results
        if confidence < self._confidence_threshold and self._ai_provider is not None:
            items = await self._ai_normalize_items(items)
            logger.info(
                "AI normalisation applied",
                extra={"items": len(items), "original_confidence": confidence},
            )

        # Step 4 — recalculate confidence
        new_confidence = _compute_confidence(items, confidence)

        result["extracted_data"] = items
        result["confidence"] = new_confidence
        # Ensure output_format is always present in the result (pass-through)
        result.setdefault("output_format", "json")
        return result

    async def process_batch(self, results: list[dict]) -> list[dict]:
        """Normalise a list of extraction results."""
        return [await self.normalize(r) for r in results]

    async def close(self) -> None:
        """Release any resources held by the worker."""
        # Nothing to release currently; placeholder for future cleanup
        # (e.g. closing AI provider sessions).
        pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ai_normalize_items(self, items: list[dict]) -> list[dict]:
        """Run each item through the AI provider's ``normalize`` method."""
        assert self._ai_provider is not None
        normalised: list[dict] = []
        for item in items:
            try:
                mapped = await self._ai_provider.normalize(item, TARGET_SCHEMA)
                normalised.append(mapped)
            except Exception:
                logger.warning(
                    "AI normalisation failed for item; keeping original",
                    exc_info=True,
                )
                normalised.append(item)
        return normalised
