"""
AI Routing Classifier — predicts best execution lane for a URL.

Uses URL patterns, domain heuristics, and optional AI classification.
Caches results for repeated domain lookups.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urlparse

from packages.core.router import Lane

logger = logging.getLogger(__name__)

# URL patterns that indicate API availability
API_PATTERNS = [
    re.compile(r'/products\.json', re.IGNORECASE),
    re.compile(r'/api/v\d+/', re.IGNORECASE),
    re.compile(r'/feed/?$', re.IGNORECASE),
    re.compile(r'\.(xml|rss|atom)$', re.IGNORECASE),
    re.compile(r'/graphql', re.IGNORECASE),
]

# URL patterns that likely need browser rendering
BROWSER_PATTERNS = [
    re.compile(r'(instagram|facebook|twitter|tiktok|linkedin)\.com', re.IGNORECASE),
    re.compile(r'#!', re.IGNORECASE),  # Hashbang URLs
    re.compile(r'/app/', re.IGNORECASE),  # SPA routes
]

# URL patterns for common e-commerce (usually HTTP-friendly with JSON-LD)
HTTP_FRIENDLY_PATTERNS = [
    re.compile(r'(books\.toscrape|quotes\.toscrape)', re.IGNORECASE),
    re.compile(r'\.(html|htm|php|asp)$', re.IGNORECASE),
    re.compile(r'/product/', re.IGNORECASE),
    re.compile(r'/category/', re.IGNORECASE),
]


class URLClassifier:
    """Classifies URLs to predict best execution lane."""

    def __init__(self) -> None:
        self._cache: dict[str, Lane] = {}

    def classify(self, url: str) -> Lane:
        """Predict best lane for a URL."""
        domain = self._extract_domain(url)

        # Check cache
        if domain in self._cache:
            return self._cache[domain]

        # Pattern matching
        lane = self._classify_by_pattern(url)
        self._cache[domain] = lane
        return lane

    def _classify_by_pattern(self, url: str) -> Lane:
        """Classify using URL pattern matching."""
        # Check API patterns
        for pattern in API_PATTERNS:
            if pattern.search(url):
                return Lane.API

        # Check browser-required patterns
        for pattern in BROWSER_PATTERNS:
            if pattern.search(url):
                return Lane.BROWSER

        # Check HTTP-friendly patterns
        for pattern in HTTP_FRIENDLY_PATTERNS:
            if pattern.search(url):
                return Lane.HTTP

        # Default: HTTP (cheapest, try first)
        return Lane.HTTP

    def update_cache(self, domain: str, lane: Lane) -> None:
        """Update classification cache based on actual results."""
        self._cache[domain] = lane

    def clear_cache(self) -> None:
        self._cache.clear()

    def _extract_domain(self, url: str) -> str:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
