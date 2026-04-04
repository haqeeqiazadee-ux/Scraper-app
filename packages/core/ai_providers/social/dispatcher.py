"""
Social media provider dispatcher.

Routes extraction requests to the appropriate platform-specific extractor
based on URL domain matching. Acts as a drop-in replacement for the
DeterministicProvider when the URL matches a known social media platform.
"""

from __future__ import annotations

import logging
from typing import Optional

from packages.core.ai_providers.base import BaseAIProvider
from packages.core.ai_providers.social.base import matches_domain

logger = logging.getLogger(__name__)


class SocialMediaProvider(BaseAIProvider):
    """Dispatches extraction to platform-specific social media extractors.

    This provider checks if the URL belongs to a known social media platform
    and routes to the appropriate extractor. If the URL doesn't match any
    platform, it returns an empty list (allowing fallback to other providers).
    """

    def __init__(self) -> None:
        super().__init__(name="social-media")
        # Lazy-initialize extractors on first use
        self._extractors: list | None = None

    def _get_extractors(self) -> list:
        """Lazily initialize platform extractors."""
        if self._extractors is None:
            from packages.core.ai_providers.social.youtube import YouTubeExtractor
            from packages.core.ai_providers.social.tiktok import TikTokExtractor
            from packages.core.ai_providers.social.instagram import InstagramExtractor
            from packages.core.ai_providers.social.facebook import FacebookExtractor
            from packages.core.ai_providers.social.amazon import AmazonExtractor
            from packages.core.ai_providers.social.twitter import TwitterExtractor
            from packages.core.ai_providers.social.linkedin import LinkedInExtractor

            self._extractors = [
                (AmazonExtractor.DOMAINS, AmazonExtractor()),
                (YouTubeExtractor.DOMAINS, YouTubeExtractor()),
                (TikTokExtractor.DOMAINS, TikTokExtractor()),
                (InstagramExtractor.DOMAINS, InstagramExtractor()),
                (FacebookExtractor.DOMAINS, FacebookExtractor()),
                (TwitterExtractor.DOMAINS, TwitterExtractor()),
                (LinkedInExtractor.DOMAINS, LinkedInExtractor()),
            ]
        return self._extractors

    def can_handle(self, url: str) -> bool:
        """Check if this provider can handle the given URL."""
        for domains, _ in self._get_extractors():
            if matches_domain(url, domains):
                return True
        return False

    async def extract(
        self,
        html: str,
        url: str,
        prompt: Optional[str] = None,
        css_selectors: Optional[dict] = None,
    ) -> list[dict]:
        """Extract data using the appropriate platform extractor.

        Args:
            html: Raw HTML content.
            url: Source URL (used for platform routing and relative URL resolution).
            prompt: Optional prompt (unused by social extractors).
            css_selectors: Optional CSS selector overrides (unused — social extractors
                          use platform-specific embedded JSON and meta tags).

        Returns:
            List of extracted data dicts, or empty list if URL doesn't match
            any known social media platform.
        """
        for domains, extractor in self._get_extractors():
            if matches_domain(url, domains):
                try:
                    results = extractor.extract(html, url)
                    if results:
                        logger.debug(
                            "Social extractor %s extracted %d items from %s",
                            type(extractor).__name__,
                            len(results),
                            url,
                        )
                    return results
                except Exception as exc:
                    logger.warning(
                        "Social extractor %s failed for %s: %s",
                        type(extractor).__name__,
                        url,
                        exc,
                    )
                    return []

        # URL doesn't match any known social platform
        return []

    async def classify(self, text: str, labels: list[str]) -> str:
        """Simple keyword-based classification."""
        text_lower = text.lower()
        scores = {}
        for label in labels:
            scores[label] = text_lower.count(label.lower())
        return max(scores, key=scores.get) if scores else labels[0]

    async def normalize(self, data: dict, target_schema: dict) -> dict:
        """Pass-through normalization (social extractors return clean data)."""
        return data
