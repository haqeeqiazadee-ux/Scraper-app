"""
Unit tests for platform-specific social media extractors.

Tests each extractor against realistic HTML fixtures containing embedded
JSON data structures (ytInitialData, __UNIVERSAL_DATA_FOR_REHYDRATION__, etc.)
to verify correct field extraction without hitting live sites.
"""

from __future__ import annotations

import json
import pytest

from packages.core.ai_providers.social.base import (
    parse_count,
    parse_duration,
    parse_timestamp,
    extract_meta_tags,
    extract_json_from_script,
    deep_get,
    find_key_recursive,
    matches_domain,
)
from packages.core.ai_providers.social.youtube import YouTubeExtractor
from packages.core.ai_providers.social.tiktok import TikTokExtractor
from packages.core.ai_providers.social.instagram import InstagramExtractor
from packages.core.ai_providers.social.facebook import FacebookExtractor
from packages.core.ai_providers.social.dispatcher import SocialMediaProvider


# ===========================================================================
# Base utility tests
# ===========================================================================


class TestParseCount:
    """Test abbreviated count parsing."""

    def test_plain_integer(self):
        assert parse_count("12345") == 12345

    def test_comma_separated(self):
        assert parse_count("1,234,567") == 1234567

    def test_k_suffix(self):
        assert parse_count("13K") == 13000

    def test_m_suffix(self):
        assert parse_count("1.5M") == 1500000

    def test_b_suffix(self):
        assert parse_count("2.3B") == 2300000000

    def test_with_label(self):
        assert parse_count("13K views") == 13000

    def test_with_subscribers(self):
        assert parse_count("2.1M subscribers") == 2100000

    def test_none(self):
        assert parse_count(None) is None

    def test_empty(self):
        assert parse_count("") is None

    def test_no_number(self):
        assert parse_count("No views") is None


class TestParseDuration:
    """Test duration parsing."""

    def test_seconds(self):
        assert parse_duration("125") == "2:05"

    def test_mm_ss(self):
        assert parse_duration("3:45") == "3:45"

    def test_hh_mm_ss(self):
        assert parse_duration("1:23:45") == "1:23:45"

    def test_iso_8601(self):
        assert parse_duration("PT1H2M3S") == "1:02:03"

    def test_iso_minutes_only(self):
        assert parse_duration("PT5M30S") == "5:30"

    def test_none(self):
        assert parse_duration(None) is None


class TestParseTimestamp:
    """Test timestamp conversion."""

    def test_unix_int(self):
        result = parse_timestamp(1700000000)
        assert result is not None
        assert "2023" in result

    def test_unix_string(self):
        result = parse_timestamp("1700000000")
        assert result is not None

    def test_iso_passthrough(self):
        assert parse_timestamp("2024-01-15T10:30:00Z") == "2024-01-15T10:30:00Z"

    def test_none(self):
        assert parse_timestamp(None) is None


class TestExtractMetaTags:
    """Test meta tag extraction from HTML."""

    def test_og_tags(self):
        html = '''
        <html><head>
        <meta property="og:title" content="Test Title">
        <meta property="og:description" content="Test Description">
        <meta property="og:image" content="https://example.com/img.jpg">
        </head></html>
        '''
        tags = extract_meta_tags(html)
        assert tags["og:title"] == "Test Title"
        assert tags["og:description"] == "Test Description"
        assert tags["og:image"] == "https://example.com/img.jpg"

    def test_name_tags(self):
        html = '<meta name="description" content="A description">'
        tags = extract_meta_tags(html)
        assert tags["description"] == "A description"

    def test_reversed_attribute_order(self):
        html = '<meta content="Reversed" property="og:title">'
        tags = extract_meta_tags(html)
        assert tags["og:title"] == "Reversed"


class TestExtractJsonFromScript:
    """Test JSON extraction from script tags."""

    def test_by_script_id(self):
        html = '<script id="test-data" type="application/json">{"key": "value"}</script>'
        result = extract_json_from_script(html, script_id="test-data")
        assert result == {"key": "value"}

    def test_by_var_name(self):
        html = '<script>var myData = {"name": "test"};</script>'
        result = extract_json_from_script(html, var_name="myData")
        assert result == {"name": "test"}

    def test_missing_returns_none(self):
        html = "<html><body>No scripts here</body></html>"
        assert extract_json_from_script(html, var_name="missing") is None


class TestDeepGet:
    """Test nested dict access."""

    def test_simple(self):
        assert deep_get({"a": {"b": "c"}}, "a", "b") == "c"

    def test_list_index(self):
        assert deep_get({"items": [{"name": "first"}]}, "items", "0", "name") == "first"

    def test_missing_key(self):
        assert deep_get({"a": 1}, "b", default="x") == "x"

    def test_none_data(self):
        assert deep_get(None, "a", default="x") == "x"


class TestMatchesDomain:
    """Test URL domain matching."""

    def test_exact_match(self):
        assert matches_domain("https://www.youtube.com/watch?v=abc", ["youtube.com"])

    def test_subdomain(self):
        assert matches_domain("https://m.youtube.com/watch", ["youtube.com"])

    def test_no_match(self):
        assert not matches_domain("https://example.com", ["youtube.com"])


# ===========================================================================
# YouTube extractor tests
# ===========================================================================


class TestYouTubeExtractor:
    """Test YouTube-specific extraction logic."""

    def setup_method(self):
        self.extractor = YouTubeExtractor()

    def _make_youtube_html(self, video_details: dict | None = None,
                           initial_data: dict | None = None,
                           meta: dict | None = None) -> str:
        """Build realistic YouTube HTML with embedded data."""
        parts = ["<html><head>"]

        if meta:
            for prop, content in meta.items():
                parts.append(f'<meta property="{prop}" content="{content}">')

        parts.append("<title>Test Video - YouTube</title></head><body>")

        if video_details:
            player = {"videoDetails": video_details}
            parts.append(f"<script>var ytInitialPlayerResponse = {json.dumps(player)};</script>")

        if initial_data:
            parts.append(f"<script>var ytInitialData = {json.dumps(initial_data)};</script>")

        parts.append("</body></html>")
        return "\n".join(parts)

    def test_video_basic_extraction(self):
        """Test extraction of core video fields from ytInitialPlayerResponse."""
        html = self._make_youtube_html(
            video_details={
                "videoId": "dQw4w9WgXcQ",
                "title": "Rick Astley - Never Gonna Give You Up",
                "viewCount": "1500000000",
                "author": "Rick Astley",
                "channelId": "UCuAXFkgsw1L7xaCfnd5JJOw",
                "lengthSeconds": "213",
                "shortDescription": "The official video for Never Gonna Give You Up",
                "keywords": ["rick astley", "never gonna give you up"],
                "thumbnail": {
                    "thumbnails": [
                        {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg"},
                        {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"},
                    ]
                },
            },
            meta={
                "og:title": "Rick Astley - Never Gonna Give You Up",
                "og:image": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
            },
        )

        results = self.extractor.extract(html, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert len(results) == 1

        video = results[0]
        assert video["title"] == "Rick Astley - Never Gonna Give You Up"
        assert video["video_id"] == "dQw4w9WgXcQ"
        assert video["view_count"] == 1500000000
        assert video["channel_name"] == "Rick Astley"
        assert video["channel_id"] == "UCuAXFkgsw1L7xaCfnd5JJOw"
        assert video["duration"] == "3:33"
        assert "never gonna give you up" in video["description"].lower()
        assert isinstance(video["tags"], list)
        assert "rick astley" in video["tags"]
        assert video["thumbnail_url"].endswith("maxresdefault.jpg")

    def test_video_meta_fallback(self):
        """Test that meta tags are used when embedded JSON is missing."""
        html = self._make_youtube_html(
            meta={
                "og:title": "Fallback Title",
                "og:description": "Fallback Description",
                "og:image": "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
            },
        )

        results = self.extractor.extract(html, "https://www.youtube.com/watch?v=abc123")
        assert len(results) == 1
        assert results[0]["title"] == "Fallback Title"
        assert results[0]["video_id"] == "abc123"

    def test_channel_extraction(self):
        """Test channel metadata extraction from ytInitialData."""
        html = self._make_youtube_html(
            initial_data={
                "metadata": {
                    "channelMetadataRenderer": {
                        "title": "Test Channel",
                        "externalId": "UC123456",
                        "description": "A great channel",
                        "country": "US",
                    }
                },
            },
            meta={"og:title": "Test Channel"},
        )

        results = self.extractor.extract(html, "https://www.youtube.com/@TestChannel")
        assert len(results) == 1
        channel = results[0]
        assert channel["channel_name"] == "Test Channel"
        assert channel["channel_id"] == "UC123456"
        assert channel["country"] == "US"

    def test_search_extraction(self):
        """Test search results extraction."""
        html = self._make_youtube_html(
            initial_data={
                "contents": {
                    "twoColumnSearchResultsRenderer": {
                        "primaryContents": {
                            "sectionListRenderer": {
                                "contents": [{
                                    "itemSectionRenderer": {
                                        "contents": [{
                                            "videoRenderer": {
                                                "videoId": "vid123",
                                                "title": {"runs": [{"text": "Python Tutorial"}]},
                                                "ownerText": {"runs": [{"text": "CodeChannel"}]},
                                                "viewCountText": {"simpleText": "1.5M views"},
                                                "lengthText": {"simpleText": "10:30"},
                                            }
                                        }]
                                    }
                                }]
                            }
                        }
                    }
                }
            },
        )

        results = self.extractor.extract(html, "https://www.youtube.com/results?search_query=python")
        assert len(results) >= 1
        assert results[0]["title"] == "Python Tutorial"
        assert results[0]["video_id"] == "vid123"
        assert results[0]["channel_name"] == "CodeChannel"

    def test_video_id_extraction(self):
        """Test video ID extraction from various URL formats."""
        assert YouTubeExtractor._extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ) == "dQw4w9WgXcQ"
        assert YouTubeExtractor._extract_video_id(
            "https://youtu.be/dQw4w9WgXcQ"
        ) == "dQw4w9WgXcQ"
        assert YouTubeExtractor._extract_video_id(
            "https://www.youtube.com/shorts/abc123"
        ) == "abc123"

    def test_shorts_uses_video_extraction(self):
        """Test that shorts URLs use the video extraction path."""
        html = self._make_youtube_html(
            video_details={
                "videoId": "short123",
                "title": "Cool Short",
                "viewCount": "500000",
                "author": "Creator",
                "lengthSeconds": "30",
            },
        )

        results = self.extractor.extract(html, "https://www.youtube.com/shorts/short123")
        assert len(results) == 1
        assert results[0]["title"] == "Cool Short"


# ===========================================================================
# TikTok extractor tests
# ===========================================================================


class TestTikTokExtractor:
    """Test TikTok-specific extraction logic."""

    def setup_method(self):
        self.extractor = TikTokExtractor()

    def _make_tiktok_html(self, rehydration_data: dict | None = None,
                          sigi_data: dict | None = None,
                          meta: dict | None = None) -> str:
        """Build realistic TikTok HTML with embedded data."""
        parts = ["<html><head>"]

        if meta:
            for prop, content in meta.items():
                parts.append(f'<meta property="{prop}" content="{content}">')

        parts.append("<title>TikTok</title></head><body>")

        if rehydration_data:
            full_data = {"__DEFAULT_SCOPE__": rehydration_data}
            parts.append(
                f'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" '
                f'type="application/json">{json.dumps(full_data)}</script>'
            )

        if sigi_data:
            parts.append(
                f'<script id="SIGI_STATE" type="application/json">'
                f'{json.dumps(sigi_data)}</script>'
            )

        parts.append("</body></html>")
        return "\n".join(parts)

    def test_video_extraction_rehydration(self):
        """Test video extraction from __UNIVERSAL_DATA_FOR_REHYDRATION__."""
        html = self._make_tiktok_html(
            rehydration_data={
                "webapp.video-detail": {
                    "itemInfo": {
                        "itemStruct": {
                            "id": "7123456789",
                            "desc": "Check out this dance! #fyp #dance",
                            "createTime": "1700000000",
                            "stats": {
                                "playCount": 5000000,
                                "diggCount": 250000,
                                "commentCount": 15000,
                                "shareCount": 8000,
                            },
                            "video": {
                                "duration": 15,
                                "cover": "https://p16.tiktokcdn.com/cover.jpg",
                            },
                            "author": {
                                "uniqueId": "dancer123",
                                "nickname": "Dance Star",
                            },
                            "music": {
                                "title": "Original Sound",
                                "authorName": "Artist Name",
                            },
                            "challenges": [
                                {"title": "fyp"},
                                {"title": "dance"},
                            ],
                        }
                    }
                }
            },
        )

        results = self.extractor.extract(html, "https://www.tiktok.com/@dancer123/video/7123456789")
        assert len(results) == 1

        video = results[0]
        assert video["video_id"] == "7123456789"
        assert video["caption"] == "Check out this dance! #fyp #dance"
        assert video["view_count"] == 5000000
        assert video["like_count"] == 250000
        assert video["comment_count"] == 15000
        assert video["share_count"] == 8000
        assert video["creator_username"] == "dancer123"
        assert video["creator_nickname"] == "Dance Star"
        assert video["music_title"] == "Original Sound"
        assert video["hashtags"] == ["fyp", "dance"]

    def test_profile_extraction_rehydration(self):
        """Test profile extraction from __UNIVERSAL_DATA_FOR_REHYDRATION__."""
        html = self._make_tiktok_html(
            rehydration_data={
                "webapp.user-detail": {
                    "userInfo": {
                        "user": {
                            "uniqueId": "tiktok",
                            "nickname": "TikTok",
                            "signature": "Make Your Day",
                            "verified": True,
                            "avatarLarger": "https://p16.tiktokcdn.com/avatar.jpg",
                        },
                        "stats": {
                            "followerCount": 80000000,
                            "followingCount": 500,
                            "heartCount": 3000000000,
                            "videoCount": 250,
                        },
                    }
                }
            },
        )

        results = self.extractor.extract(html, "https://www.tiktok.com/@tiktok")
        assert len(results) == 1

        profile = results[0]
        assert profile["username"] == "tiktok"
        assert profile["nickname"] == "TikTok"
        assert profile["bio"] == "Make Your Day"
        assert profile["verified"] is True
        assert profile["follower_count"] == 80000000
        assert profile["following_count"] == 500
        assert profile["total_likes"] == 3000000000
        assert profile["video_count"] == 250

    def test_profile_extraction_sigi(self):
        """Test profile extraction from SIGI_STATE (legacy format)."""
        html = self._make_tiktok_html(
            sigi_data={
                "UserModule": {
                    "users": {
                        "testuser": {
                            "uniqueId": "testuser",
                            "nickname": "Test User",
                            "signature": "Hello world",
                            "verified": False,
                            "avatarLarger": "https://cdn.tiktok.com/avatar.jpg",
                        }
                    },
                    "stats": {
                        "testuser": {
                            "followerCount": 10000,
                            "followingCount": 200,
                            "heartCount": 500000,
                            "videoCount": 50,
                        }
                    },
                }
            },
        )

        results = self.extractor.extract(html, "https://www.tiktok.com/@testuser")
        assert len(results) == 1
        profile = results[0]
        assert profile["username"] == "testuser"
        assert profile["follower_count"] == 10000

    def test_meta_fallback(self):
        """Test fallback to meta tags when embedded JSON is unavailable."""
        html = self._make_tiktok_html(
            meta={
                "og:title": "TikTok User (@testuser)",
                "og:description": "Test bio here",
                "og:image": "https://cdn.tiktok.com/avatar.jpg",
            },
        )

        results = self.extractor.extract(html, "https://www.tiktok.com/@testuser")
        assert len(results) == 1
        assert results[0]["username"] == "testuser"


# ===========================================================================
# Instagram extractor tests
# ===========================================================================


class TestInstagramExtractor:
    """Test Instagram-specific extraction logic."""

    def setup_method(self):
        self.extractor = InstagramExtractor()

    def _make_instagram_html(self, shared_data: dict | None = None,
                             graphql_media: dict | None = None,
                             meta: dict | None = None) -> str:
        """Build realistic Instagram HTML."""
        parts = ["<html><head>"]

        if meta:
            for prop, content in meta.items():
                parts.append(f'<meta property="{prop}" content="{content}">')

        parts.append("<title>Instagram</title></head><body>")

        if shared_data:
            parts.append(
                f'<script>window._sharedData = {json.dumps(shared_data)};</script>'
            )

        if graphql_media:
            # Embed as shortcode_media in a script
            embedded = json.dumps({"shortcode_media": graphql_media})
            parts.append(f'<script>window.__additionalData = {embedded};</script>')
            # Also embed directly for the regex to find
            parts.append(f'<script>"shortcode_media": {json.dumps(graphql_media)}</script>')

        parts.append("</body></html>")
        return "\n".join(parts)

    def test_reel_extraction_graphql(self):
        """Test reel extraction from embedded GraphQL data."""
        html = self._make_instagram_html(
            graphql_media={
                "shortcode": "CxYz123",
                "video_view_count": 500000,
                "edge_media_preview_like": {"count": 25000},
                "edge_media_to_parent_comment": {"count": 1200},
                "edge_media_to_caption": {
                    "edges": [{"node": {"text": "Amazing sunset! #nature #beautiful"}}]
                },
                "owner": {
                    "username": "photographer",
                    "edge_followed_by": {"count": 50000},
                },
                "taken_at_timestamp": 1700000000,
                "display_url": "https://scontent.cdninstagram.com/display.jpg",
                "is_video": True,
                "video_url": "https://scontent.cdninstagram.com/video.mp4",
                "clips_music_attribution_info": {
                    "song_name": "Sunset Vibes",
                },
            },
        )

        results = self.extractor.extract(html, "https://www.instagram.com/reel/CxYz123/")
        assert len(results) == 1

        reel = results[0]
        assert reel["reel_id"] == "CxYz123"
        assert reel["view_count"] == 500000
        assert reel["like_count"] == 25000
        assert reel["comment_count"] == 1200
        assert "sunset" in reel["caption"].lower()
        assert reel["author_username"] == "photographer"
        assert reel["author_followers"] == 50000
        assert "nature" in reel["hashtags"]
        assert reel["music_name"] == "Sunset Vibes"

    def test_reel_meta_fallback(self):
        """Test reel extraction from meta tags only."""
        html = self._make_instagram_html(
            meta={
                "og:title": "@user on Instagram",
                "og:description": "1,234 likes, 56 comments - user: Check this out #cool",
                "og:image": "https://scontent.cdninstagram.com/thumb.jpg",
            },
        )

        results = self.extractor.extract(html, "https://www.instagram.com/reel/AbC123/")
        assert len(results) == 1
        reel = results[0]
        assert reel["reel_id"] == "AbC123"
        assert reel["like_count"] == 1234
        assert reel["comment_count"] == 56

    def test_profile_extraction_shared_data(self):
        """Test profile extraction from window._sharedData."""
        html = self._make_instagram_html(
            shared_data={
                "entry_data": {
                    "ProfilePage": [{
                        "graphql": {
                            "user": {
                                "username": "instagram",
                                "full_name": "Instagram",
                                "biography": "Bringing you closer to the people and things you love.",
                                "edge_followed_by": {"count": 500000000},
                                "edge_follow": {"count": 300},
                                "edge_owner_to_timeline_media": {"count": 7500},
                                "is_verified": True,
                                "profile_pic_url_hd": "https://scontent.cdninstagram.com/pic.jpg",
                            }
                        }
                    }]
                }
            },
        )

        results = self.extractor.extract(html, "https://www.instagram.com/instagram/")
        assert len(results) == 1

        profile = results[0]
        assert profile["username"] == "instagram"
        assert profile["full_name"] == "Instagram"
        assert profile["follower_count"] == 500000000
        assert profile["following_count"] == 300
        assert profile["post_count"] == 7500
        assert profile["verified"] is True

    def test_profile_meta_fallback(self):
        """Test profile extraction from meta description with follower counts."""
        html = self._make_instagram_html(
            meta={
                "og:title": "Instagram Official (@instagram)",
                "og:description": "500M Followers, 300 Following, 7.5K Posts - Bringing you closer.",
                "og:image": "https://scontent.cdninstagram.com/pic.jpg",
            },
        )

        results = self.extractor.extract(html, "https://www.instagram.com/instagram/")
        assert len(results) == 1
        profile = results[0]
        assert profile["username"] == "instagram"
        assert profile["follower_count"] == 500000000

    def test_shortcode_extraction(self):
        """Test shortcode extraction from various URL formats."""
        assert InstagramExtractor._extract_shortcode(
            "https://www.instagram.com/reel/CxYz123/"
        ) == "CxYz123"
        assert InstagramExtractor._extract_shortcode(
            "https://www.instagram.com/p/AbC456/"
        ) == "AbC456"


# ===========================================================================
# Facebook extractor tests
# ===========================================================================


class TestFacebookExtractor:
    """Test Facebook-specific extraction logic."""

    def setup_method(self):
        self.extractor = FacebookExtractor()

    def _make_facebook_html(self, meta: dict | None = None,
                            embedded: dict | None = None) -> str:
        """Build realistic Facebook HTML."""
        parts = ["<html><head>"]

        if meta:
            for prop, content in meta.items():
                parts.append(f'<meta property="{prop}" content="{content}">')

        parts.append("<title>Facebook</title></head><body>")

        if embedded:
            # Simulate Facebook's embedded JSON patterns
            for key, value in embedded.items():
                parts.append(f'<script>"{key}": {json.dumps(value)}</script>')

        parts.append("</body></html>")
        return "\n".join(parts)

    def test_reel_extraction_meta_tags(self):
        """Test reel extraction using Open Graph meta tags."""
        html = self._make_facebook_html(
            meta={
                "og:title": "John Doe - Check out this amazing view!",
                "og:description": "1.2K likes, 45 comments, 23 shares",
                "og:image": "https://scontent.facebook.com/thumb.jpg",
                "og:video": "https://video.facebook.com/reel.mp4",
                "article:published_time": "2024-06-15T14:30:00Z",
            },
        )

        results = self.extractor.extract(html, "https://www.facebook.com/reel/123456789")
        assert len(results) == 1

        reel = results[0]
        assert reel["reel_id"] == "123456789"
        assert "amazing view" in reel["caption"].lower()
        assert reel["like_count"] == 1200
        assert reel["comment_count"] == 45
        assert reel["share_count"] == 23
        assert reel["author_name"] == "John Doe"
        assert reel["thumbnail_url"].endswith("thumb.jpg")
        assert reel["video_url"].endswith("reel.mp4")

    def test_reel_embedded_json(self):
        """Test reel extraction from embedded feedback data."""
        html = self._make_facebook_html(
            meta={
                "og:title": "Cool Reel",
                "og:image": "https://scontent.facebook.com/thumb.jpg",
            },
            embedded={
                "feedback": {
                    "reaction_count": {"count": 5000},
                    "comment_count": {"total_count": 200},
                    "share_count": {"count": 100},
                },
                "video": {
                    "play_count": 50000,
                },
            },
        )

        results = self.extractor.extract(html, "https://www.facebook.com/reel/987654321")
        assert len(results) == 1
        reel = results[0]
        assert reel["like_count"] == 5000
        assert reel["comment_count"] == 200
        assert reel["share_count"] == 100
        assert reel["play_count"] == 50000

    def test_marketplace_extraction(self):
        """Test marketplace listing extraction."""
        html = self._make_facebook_html(
            meta={
                "og:title": "iPhone 15 Pro - $999",
                "og:description": "Barely used iPhone 15 Pro, great condition",
                "og:image": "https://scontent.facebook.com/phone.jpg",
            },
        )

        results = self.extractor.extract(html, "https://www.facebook.com/marketplace/item/12345")
        assert len(results) == 1
        item = results[0]
        assert "iPhone 15 Pro" in item["title"]
        assert item["price"] == "999"

    def test_page_extraction(self):
        """Test Facebook page extraction."""
        html = self._make_facebook_html(
            meta={
                "og:title": "Test Business Page",
                "og:description": "A business page with 10K followers, 8K likes",
                "og:type": "website",
            },
        )

        results = self.extractor.extract(html, "https://www.facebook.com/testbusiness")
        assert len(results) == 1
        page = results[0]
        assert page["name"] == "Test Business Page"
        assert page["follower_count"] == 10000

    def test_reel_id_extraction(self):
        """Test reel ID extraction from URLs."""
        assert FacebookExtractor._extract_reel_id(
            "https://www.facebook.com/reel/123456789"
        ) == "123456789"
        assert FacebookExtractor._extract_reel_id(
            "https://www.facebook.com/page/about"
        ) is None


# ===========================================================================
# Dispatcher tests
# ===========================================================================


class TestSocialMediaProvider:
    """Test the SocialMediaProvider dispatcher."""

    def setup_method(self):
        self.provider = SocialMediaProvider()

    def test_can_handle_youtube(self):
        assert self.provider.can_handle("https://www.youtube.com/watch?v=abc")

    def test_can_handle_tiktok(self):
        assert self.provider.can_handle("https://www.tiktok.com/@user")

    def test_can_handle_instagram(self):
        assert self.provider.can_handle("https://www.instagram.com/reel/abc")

    def test_can_handle_facebook(self):
        assert self.provider.can_handle("https://www.facebook.com/reel/123")

    def test_cannot_handle_generic(self):
        assert not self.provider.can_handle("https://www.example.com")

    def test_cannot_handle_ecommerce(self):
        assert not self.provider.can_handle("https://www.amazon.com/dp/B123")

    @pytest.mark.asyncio
    async def test_extract_youtube(self):
        """Test that YouTube URLs are routed to YouTubeExtractor."""
        html = """
        <html><head>
        <meta property="og:title" content="Test Video">
        <title>Test Video - YouTube</title>
        </head><body>
        <script>var ytInitialPlayerResponse = {"videoDetails": {
            "videoId": "test123", "title": "Test Video", "viewCount": "1000"
        }};</script>
        </body></html>
        """
        results = await self.provider.extract(html, "https://www.youtube.com/watch?v=test123")
        assert len(results) == 1
        assert results[0]["title"] == "Test Video"
        assert results[0]["video_id"] == "test123"

    @pytest.mark.asyncio
    async def test_extract_non_social_returns_empty(self):
        """Test that non-social URLs return empty results."""
        html = "<html><body>Not social media</body></html>"
        results = await self.provider.extract(html, "https://www.example.com")
        assert results == []


# ===========================================================================
# Integration test: DeterministicProvider routes to social
# ===========================================================================


class TestDeterministicSocialIntegration:
    """Test that DeterministicProvider correctly routes social URLs."""

    @pytest.mark.asyncio
    async def test_youtube_url_uses_social_extractor(self):
        """Verify YouTube URLs get routed through social extraction."""
        from packages.core.ai_providers.deterministic import DeterministicProvider
        provider = DeterministicProvider()

        html = """
        <html><head>
        <meta property="og:title" content="Integration Test Video">
        </head><body>
        <script>var ytInitialPlayerResponse = {"videoDetails": {
            "videoId": "int123", "title": "Integration Test Video",
            "viewCount": "5000", "author": "Test Channel",
            "lengthSeconds": "120"
        }};</script>
        </body></html>
        """
        results = await provider.extract(html, "https://www.youtube.com/watch?v=int123")
        assert len(results) == 1
        assert results[0]["title"] == "Integration Test Video"
        assert results[0]["video_id"] == "int123"
        assert results[0]["channel_name"] == "Test Channel"

    @pytest.mark.asyncio
    async def test_ecommerce_url_uses_original_pipeline(self):
        """Verify non-social URLs still use the original e-commerce pipeline."""
        from packages.core.ai_providers.deterministic import DeterministicProvider
        provider = DeterministicProvider()

        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "Product", "name": "Widget", "offers": {"price": "29.99", "priceCurrency": "USD"}}
        </script>
        </head><body></body></html>
        """
        results = await provider.extract(html, "https://www.example.com/product/widget")
        assert len(results) == 1
        assert results[0]["name"] == "Widget"
        assert results[0]["price"] == "29.99"
