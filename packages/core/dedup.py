"""
Deduplication Engine — detect and merge duplicate records.

Uses fuzzy matching on product name + URL, and exact matching on SKU/GTIN.
"""

from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_SIMILARITY_THRESHOLD = 0.85


class DedupEngine:
    """Detect and merge duplicate extracted records."""

    def __init__(self, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> None:
        self._threshold = similarity_threshold

    def deduplicate(self, items: list[dict]) -> list[dict]:
        """Remove duplicates from a list of extracted items."""
        if len(items) <= 1:
            return items

        unique: list[dict] = []
        for item in items:
            duplicate_idx = self._find_duplicate(item, unique)
            if duplicate_idx is not None:
                # Merge into existing
                unique[duplicate_idx] = self._merge(unique[duplicate_idx], item)
                logger.debug("Duplicate merged", extra={
                    "name": item.get("name", "?"),
                })
            else:
                unique.append(item)

        if len(unique) < len(items):
            logger.info(
                "Dedup complete",
                extra={"original": len(items), "unique": len(unique), "removed": len(items) - len(unique)},
            )
        return unique

    def _find_duplicate(self, item: dict, existing: list[dict]) -> Optional[int]:
        """Find the index of a duplicate in the existing list, or None."""
        for idx, other in enumerate(existing):
            if self._is_duplicate(item, other):
                return idx
        return None

    def _is_duplicate(self, a: dict, b: dict) -> bool:
        """Determine if two items are duplicates."""
        # Exact match on SKU/GTIN
        sku_a = str(a.get("sku", "")).strip()
        sku_b = str(b.get("sku", "")).strip()
        if sku_a and sku_b and sku_a == sku_b:
            return True

        # Exact match on product_url (skip base domain URLs — they're not real product links)
        url_a = str(a.get("product_url", "")).strip().rstrip("/")
        url_b = str(b.get("product_url", "")).strip().rstrip("/")
        if url_a and url_b and url_a == url_b:
            # Reject matches on bare domain URLs (e.g. "https://example.com")
            from urllib.parse import urlparse
            parsed = urlparse(url_a)
            if parsed.path and parsed.path not in ("", "/"):
                return True

        # Fuzzy match on name
        name_a = str(a.get("name", "")).strip().lower()
        name_b = str(b.get("name", "")).strip().lower()
        if name_a and name_b:
            similarity = SequenceMatcher(None, name_a, name_b).ratio()
            if similarity >= self._threshold:
                return True

        return False

    def _merge(self, existing: dict, new: dict) -> dict:
        """Merge two duplicate records, keeping the most complete data."""
        merged = dict(existing)
        for key, value in new.items():
            # Keep existing value if it's more complete
            existing_val = str(merged.get(key, "")).strip()
            new_val = str(value).strip() if not isinstance(value, (list, dict)) else value

            if isinstance(value, (list, dict)):
                if not merged.get(key):
                    merged[key] = value
                elif isinstance(value, list) and len(value) > len(merged.get(key, [])):
                    merged[key] = value
            elif not existing_val and new_val:
                merged[key] = value
            elif new_val and len(str(new_val)) > len(existing_val):
                merged[key] = value

        return merged
