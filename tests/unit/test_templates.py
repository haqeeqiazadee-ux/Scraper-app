"""Tests for the template registry and template contracts."""

from __future__ import annotations

import pytest

from packages.contracts.template import (
    FieldDefinition,
    Template,
    TemplateCategory,
    TemplateConfig,
)
from packages.core.template_registry import (
    BUILT_IN_TEMPLATES,
    get_template,
    list_templates,
    search_templates,
)


# ---------------------------------------------------------------------------
# Contract / schema tests
# ---------------------------------------------------------------------------

class TestTemplateContract:
    """Validate Template Pydantic schema."""

    def test_field_definition_minimal(self):
        f = FieldDefinition(name="price")
        assert f.name == "price"
        assert f.field_type == "text"
        assert f.required is False

    def test_field_definition_full(self):
        f = FieldDefinition(
            name="title",
            description="Product title",
            css_selector="h1.title",
            field_type="text",
            required=True,
        )
        assert f.css_selector == "h1.title"
        assert f.required is True

    def test_template_config_defaults(self):
        cfg = TemplateConfig()
        assert cfg.preferred_lane == "auto"
        assert cfg.rate_limit_rpm == 30
        assert cfg.timeout_ms == 30000
        assert cfg.robots_compliance is True

    def test_template_minimal(self):
        t = Template(id="test", name="Test Template")
        assert t.category == TemplateCategory.GENERAL
        assert t.version == "1.0.0"
        assert len(t.config.fields) == 0

    def test_template_category_enum(self):
        assert TemplateCategory.ECOMMERCE == "ecommerce"
        assert TemplateCategory.MARKETPLACE == "marketplace"
        assert TemplateCategory.REVIEWS == "reviews"


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestTemplateRegistry:
    """Test the built-in template registry."""

    def test_builtin_templates_not_empty(self):
        assert len(BUILT_IN_TEMPLATES) >= 55

    def test_all_templates_have_unique_ids(self):
        ids = [t.id for t in BUILT_IN_TEMPLATES]
        assert len(ids) == len(set(ids)), "Duplicate template IDs found"

    def test_all_templates_have_required_fields(self):
        for t in BUILT_IN_TEMPLATES:
            assert t.id, f"Template missing id"
            assert t.name, f"Template {t.id} missing name"
            assert t.description, f"Template {t.id} missing description"
            assert t.category, f"Template {t.id} missing category"
            assert len(t.config.fields) > 0, f"Template {t.id} has no fields"

    def test_all_templates_have_at_least_one_required_field(self):
        for t in BUILT_IN_TEMPLATES:
            required_fields = [f for f in t.config.fields if f.required]
            assert len(required_fields) >= 1, (
                f"Template {t.id} has no required fields"
            )

    def test_get_template_found(self):
        t = get_template("amazon-product")
        assert t is not None
        assert t.name == "Amazon Product Scraper"
        assert t.platform == "Amazon"

    def test_get_template_not_found(self):
        assert get_template("nonexistent-template") is None

    def test_list_templates_all(self):
        all_t = list_templates()
        assert len(all_t) == len(BUILT_IN_TEMPLATES)

    def test_list_templates_by_category(self):
        ecom = list_templates(category="ecommerce")
        assert len(ecom) >= 10
        for t in ecom:
            assert t.category == TemplateCategory.ECOMMERCE

    def test_list_templates_by_platform(self):
        amazon = list_templates(platform="Amazon")
        assert len(amazon) >= 6
        for t in amazon:
            assert t.platform == "Amazon"

    def test_list_templates_by_tag(self):
        pricing = list_templates(tag="pricing")
        assert len(pricing) >= 2
        for t in pricing:
            assert "pricing" in [tag.lower() for tag in t.tags]

    def test_search_templates_by_name(self):
        results = search_templates("Amazon")
        assert len(results) >= 3
        assert results[0].platform == "Amazon"

    def test_search_templates_by_keyword(self):
        results = search_templates("dropshipping")
        assert len(results) >= 1

    def test_search_templates_no_results(self):
        results = search_templates("xyznonexistent123")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Specific template validation
# ---------------------------------------------------------------------------

class TestSpecificTemplates:
    """Validate individual template configurations."""

    def test_amazon_product_template(self):
        t = get_template("amazon-product")
        assert t is not None
        assert t.config.browser_required is True
        assert t.config.stealth_required is True
        assert t.config.proxy_required is True
        assert "amazon.com" in t.config.target_domains
        field_names = [f.name for f in t.config.fields]
        assert "title" in field_names
        assert "price" in field_names
        assert "asin" in field_names

    def test_shopify_store_template(self):
        t = get_template("shopify-store")
        assert t is not None
        assert t.config.preferred_lane == "api"
        assert t.config.browser_required is False
        field_names = [f.name for f in t.config.fields]
        assert "title" in field_names
        assert "variants" in field_names

    def test_universal_ecommerce_template(self):
        t = get_template("universal-ecommerce")
        assert t is not None
        assert t.config.extraction_type == "ai"
        assert "strategy" in t.config.extraction_rules
        assert t.config.extraction_rules["strategy"] == "cascade"

    def test_ebay_template(self):
        t = get_template("ebay-items")
        assert t is not None
        assert "ebay.com" in t.config.target_domains
        field_names = [f.name for f in t.config.fields]
        assert "bid_count" in field_names
        assert "listing_type" in field_names

    def test_price_monitor_template(self):
        t = get_template("price-monitor")
        assert t is not None
        assert t.config.extraction_rules.get("scheduling") is not None

    def test_walmart_template(self):
        t = get_template("walmart-product")
        assert t is not None
        assert t.config.stealth_required is True
        assert "walmart.com" in t.config.target_domains

    def test_facebook_marketplace_template(self):
        t = get_template("facebook-marketplace")
        assert t is not None
        assert t.config.preferred_lane == "hard_target"
        assert t.config.stealth_required is True

    def test_amazon_seller_template(self):
        t = get_template("amazon-seller")
        assert t is not None
        assert t.platform == "Amazon"
        field_names = [f.name for f in t.config.fields]
        assert "seller_name" in field_names
        assert "seller_id" in field_names

    def test_amazon_search_template(self):
        t = get_template("amazon-search")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "position" in field_names
        assert "is_sponsored" in field_names

    def test_tiktok_shop_template(self):
        t = get_template("tiktok-shop")
        assert t is not None
        assert t.config.preferred_lane == "hard_target"
        assert "tiktok.com" in t.config.target_domains

    def test_trustpilot_reviews_template(self):
        t = get_template("trustpilot-reviews")
        assert t is not None
        assert t.category == TemplateCategory.REVIEWS
        assert t.config.pagination is not None

    def test_yelp_business_template(self):
        t = get_template("yelp-business")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "hours" in field_names
        assert "amenities" in field_names

    def test_facebook_ads_library_template(self):
        t = get_template("facebook-ads-library")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "spend_lower" in field_names
        assert "impressions_upper" in field_names

    def test_zalando_template(self):
        t = get_template("zalando-product")
        assert t is not None
        assert "zalando.de" in t.config.target_domains
        field_names = [f.name for f in t.config.fields]
        assert "sizes_available" in field_names

    def test_mercado_libre_template(self):
        t = get_template("mercado-libre")
        assert t is not None
        assert "mercadolibre.com.mx" in t.config.target_domains

    def test_naver_shopping_template(self):
        t = get_template("naver-shopping")
        assert t is not None
        assert t.platform == "Naver Shopping"

    def test_kickstarter_template(self):
        t = get_template("kickstarter")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "pledged" in field_names
        assert "backers_count" in field_names

    def test_ebay_store_template(self):
        t = get_template("ebay-store")
        assert t is not None
        assert t.platform == "eBay"

    def test_ebay_reviews_template(self):
        t = get_template("ebay-reviews")
        assert t is not None
        assert t.category == TemplateCategory.REVIEWS

    def test_google_play_template(self):
        t = get_template("google-play")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "app_name" in field_names
        assert "installs" in field_names

    def test_ai_product_matcher_template(self):
        t = get_template("ai-product-matcher")
        assert t is not None
        assert t.config.extraction_type == "ai"
        assert "strategy" in t.config.extraction_rules

    def test_shopify_leads_template(self):
        t = get_template("shopify-leads")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "email" in field_names

    def test_google_ads_template(self):
        t = get_template("google-ads")
        assert t is not None
        assert t.config.stealth_required is True

    def test_amazon_product_details_template(self):
        t = get_template("amazon-product-details")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "specifications" in field_names
        assert "variants" in field_names
        assert "frequently_bought_together" in field_names


class TestVideoTemplates:
    """Validate video/social media templates."""

    def test_video_category_count(self):
        videos = list_templates(category="videos")
        assert len(videos) >= 20

    def test_youtube_video_template(self):
        t = get_template("youtube-video")
        assert t is not None
        assert t.platform == "YouTube"
        assert t.category == TemplateCategory.VIDEOS
        field_names = [f.name for f in t.config.fields]
        assert "view_count" in field_names
        assert "like_count" in field_names

    def test_youtube_channel_template(self):
        t = get_template("youtube-channel")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "subscriber_count" in field_names
        assert "social_links" in field_names

    def test_youtube_comments_template(self):
        t = get_template("youtube-comments")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "comment_text" in field_names
        assert "reply_count" in field_names

    def test_youtube_transcript_template(self):
        t = get_template("youtube-transcript")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "transcript_text" in field_names
        assert "segments" in field_names

    def test_youtube_shorts_template(self):
        t = get_template("youtube-shorts")
        assert t is not None
        assert t.platform == "YouTube"

    def test_youtube_search_template(self):
        t = get_template("youtube-search")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "result_type" in field_names

    def test_youtube_trending_template(self):
        t = get_template("youtube-trending")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "position" in field_names

    def test_youtube_downloader_template(self):
        t = get_template("youtube-downloader")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "download_url" in field_names
        assert "quality" in field_names

    def test_tiktok_video_template(self):
        t = get_template("tiktok-video")
        assert t is not None
        assert t.config.stealth_required is True
        field_names = [f.name for f in t.config.fields]
        assert "share_count" in field_names
        assert "music_title" in field_names
        assert "download_url" in field_names

    def test_tiktok_profile_template(self):
        t = get_template("tiktok-profile")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "follower_count" in field_names
        assert "verified" in field_names

    def test_tiktok_comments_template(self):
        t = get_template("tiktok-comments")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "comment_text" in field_names

    def test_tiktok_hashtag_template(self):
        t = get_template("tiktok-hashtag")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "hashtag" in field_names

    def test_tiktok_trending_template(self):
        t = get_template("tiktok-trending")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "trending_rank" in field_names

    def test_tiktok_sound_template(self):
        t = get_template("tiktok-sound")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "music_id" in field_names

    def test_instagram_reel_template(self):
        t = get_template("instagram-reel")
        assert t is not None
        assert t.config.preferred_lane == "hard_target"
        field_names = [f.name for f in t.config.fields]
        assert "transcript" in field_names
        assert "download_url" in field_names

    def test_instagram_stories_template(self):
        t = get_template("instagram-stories")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "expiry_time" in field_names

    def test_instagram_video_downloader_template(self):
        t = get_template("instagram-video-downloader")
        assert t is not None
        field_names = [f.name for f in t.config.fields]
        assert "download_url" in field_names

    def test_facebook_reels_template(self):
        t = get_template("facebook-reels")
        assert t is not None
        assert t.config.preferred_lane == "hard_target"
        field_names = [f.name for f in t.config.fields]
        assert "play_count" in field_names

    def test_multi_platform_transcriber_template(self):
        t = get_template("multi-platform-transcriber")
        assert t is not None
        assert t.config.extraction_type == "ai"
        assert "strategy" in t.config.extraction_rules

    def test_multi_platform_downloader_template(self):
        t = get_template("multi-platform-downloader")
        assert t is not None
        assert len(t.config.target_domains) >= 5

    def test_search_youtube_templates(self):
        results = search_templates("youtube")
        assert len(results) >= 8

    def test_search_tiktok_templates(self):
        results = search_templates("tiktok")
        assert len(results) >= 6

    def test_search_instagram_templates(self):
        results = search_templates("instagram")
        assert len(results) >= 3
