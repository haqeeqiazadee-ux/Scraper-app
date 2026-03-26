"""
Deduplication Engine — detect and merge duplicate records.

Uses fuzzy matching on product name + URL, and exact matching on SKU/GTIN.
Includes URL-level dedup to prevent scraping the same URL twice.
"""

from __future__ import annotations

import logging
import time
from difflib import SequenceMatcher
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_SIMILARITY_THRESHOLD = 0.85


class URLDedup:
    """Track seen URLs to avoid scraping the same URL twice.

    Used at the task/session level to prevent wasted requests.
    Pro scrapers never hit the same URL twice in the same job.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._seen: dict[str, float] = {}  # normalized_url -> timestamp
        self._ttl = ttl_seconds

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL for dedup comparison."""
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
        parsed = urlparse(url.lower().strip())
        # Remove fragment, trailing slash, www prefix
        netloc = parsed.netloc.replace("www.", "")
        path = parsed.path.rstrip("/") or "/"
        # Sort query params for consistent comparison
        params = parse_qs(parsed.query, keep_blank_values=True)
        sorted_query = urlencode(sorted(params.items()), doseq=True)
        return urlunparse((parsed.scheme, netloc, path, "", sorted_query, ""))

    def is_seen(self, url: str) -> bool:
        """Check if a URL has already been scraped."""
        self._evict_expired()
        normalized = self._normalize_url(url)
        return normalized in self._seen

    def mark_seen(self, url: str) -> None:
        """Mark a URL as scraped."""
        normalized = self._normalize_url(url)
        self._seen[normalized] = time.time()

    def check_and_mark(self, url: str) -> bool:
        """Check if seen, and mark if not. Returns True if already seen."""
        if self.is_seen(url):
            return True
        self.mark_seen(url)
        return False

    def _evict_expired(self) -> None:
        """Remove URLs older than TTL."""
        now = time.time()
        cutoff = now - self._ttl
        expired = [url for url, ts in self._seen.items() if ts < cutoff]
        for url in expired:
            del self._seen[url]

    @property
    def seen_count(self) -> int:
        return len(self._seen)

    def clear(self) -> None:
        self._seen.clear()


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

        # Fuzzy match on name — only when URLs also match or are absent.
        # Names like "Multisure For Women" vs "Multisure For Men" score >0.95
        # but are distinct products, so name similarity alone is not enough.
        name_a = str(a.get("name", "")).strip().lower()
        name_b = str(b.get("name", "")).strip().lower()
        if name_a and name_b:
            similarity = SequenceMatcher(None, name_a, name_b).ratio()
            if similarity >= 0.9999:
                return True  # Exact name match — always a duplicate
            if similarity >= self._threshold:
                # Near-match: only merge if URLs also match
                url_a = str(a.get("product_url", "")).strip().rstrip("/")
                url_b = str(b.get("product_url", "")).strip().rstrip("/")
                if url_a and url_b and url_a == url_b:
                    return True
                # Both lack URLs but names are very similar
                if not url_a and not url_b and similarity >= 0.95:
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
