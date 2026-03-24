"""
Platform-specific social media extractors.

Each extractor knows how to parse embedded JSON, meta tags, and DOM elements
for its respective platform (YouTube, TikTok, Instagram, Facebook).
"""

from packages.core.ai_providers.social.youtube import YouTubeExtractor
from packages.core.ai_providers.social.tiktok import TikTokExtractor
from packages.core.ai_providers.social.instagram import InstagramExtractor
from packages.core.ai_providers.social.facebook import FacebookExtractor
from packages.core.ai_providers.social.dispatcher import SocialMediaProvider

__all__ = [
    "YouTubeExtractor",
    "TikTokExtractor",
    "InstagramExtractor",
    "FacebookExtractor",
    "SocialMediaProvider",
]
