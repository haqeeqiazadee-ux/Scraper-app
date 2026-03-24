"""
Selector cache — stores discovered CSS selectors per domain.

When DOM auto-discovery or LLM selector generation finds working selectors
for a domain, they are cached here so subsequent requests skip the
discovery step and go straight to deterministic extraction.

Storage: simple JSON file on disk (works for desktop + self-hosted).
For cloud deployments, swap to Redis/DB via the CacheBackend interface.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Default cache location
DEFAULT_CACHE_DIR = os.path.join(
    os.environ.get("SCRAPER_DATA_DIR", "/tmp/scraper_cache"),
    "selector_cache",
)

# Cache TTL: 7 days (selectors may need refreshing as sites update)
DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60


def _domain_key(url: str) -> str:
    """Extract a cache key from a URL (domain + path pattern)."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        # Use domain + first path segment as key
        # e.g., "example.com/products" for "https://example.com/products/123"
        path_parts = [p for p in parsed.path.split("/") if p]
        path_prefix = path_parts[0] if path_parts else ""
        raw_key = f"{parsed.netloc}/{path_prefix}"
        return hashlib.md5(raw_key.encode()).hexdigest()
    except Exception:
        return hashlib.md5(url.encode()).hexdigest()


class SelectorCache:
    """File-based cache for CSS selectors discovered per domain/path."""

    def __init__(
        self,
        cache_dir: str = DEFAULT_CACHE_DIR,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self._cache_dir = cache_dir
        self._ttl = ttl_seconds
        # In-memory LRU to avoid repeated disk reads
        self._memory: dict[str, dict] = {}

    def _ensure_dir(self) -> None:
        os.makedirs(self._cache_dir, exist_ok=True)

    def _file_path(self, key: str) -> str:
        return os.path.join(self._cache_dir, f"{key}.json")

    def get(self, url: str) -> Optional[dict]:
        """Get cached selectors for a URL's domain pattern.

        Returns:
            Dict with keys: "card_selector" (str), "field_selectors" (dict),
            "discovered_at" (float), "source" (str).
            Or None if not cached / expired.
        """
        key = _domain_key(url)

        # Check memory first
        if key in self._memory:
            entry = self._memory[key]
            if time.time() - entry.get("discovered_at", 0) < self._ttl:
                return entry
            else:
                del self._memory[key]
                return None

        # Check disk
        path = self._file_path(key)
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r") as f:
                entry = json.load(f)
            if time.time() - entry.get("discovered_at", 0) >= self._ttl:
                # Expired
                os.remove(path)
                return None
            self._memory[key] = entry
            return entry
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("Failed to read selector cache %s: %s", path, exc)
            return None

    def put(
        self,
        url: str,
        card_selector: str,
        field_selectors: dict[str, str],
        source: str = "dom_discovery",
    ) -> None:
        """Cache discovered selectors for a URL's domain pattern.

        Args:
            url: The URL the selectors were discovered on.
            card_selector: CSS selector for the repeating card container.
            field_selectors: Mapping of field name → CSS selector within the card.
            source: How the selectors were discovered ("dom_discovery" or "llm").
        """
        key = _domain_key(url)
        entry = {
            "card_selector": card_selector,
            "field_selectors": field_selectors,
            "discovered_at": time.time(),
            "source": source,
            "url": url,
        }

        self._memory[key] = entry

        try:
            self._ensure_dir()
            with open(self._file_path(key), "w") as f:
                json.dump(entry, f, indent=2)
        except OSError as exc:
            logger.debug("Failed to write selector cache: %s", exc)

    def invalidate(self, url: str) -> None:
        """Remove cached selectors for a URL's domain pattern."""
        key = _domain_key(url)
        self._memory.pop(key, None)
        path = self._file_path(key)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
