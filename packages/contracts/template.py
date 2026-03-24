"""Template contract — defines reusable scraping template schema."""

from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class TemplateCategory(StrEnum):
    ECOMMERCE = "ecommerce"
    MARKETPLACE = "marketplace"
    SOCIAL_MEDIA = "social_media"
    VIDEOS = "videos"
    NEWS = "news"
    JOBS = "jobs"
    REAL_ESTATE = "real_estate"
    REVIEWS = "reviews"
    GENERAL = "general"


class FieldDefinition(BaseModel):
    """Defines a single extractable field."""

    name: str = Field(min_length=1)
    description: str = ""
    css_selector: Optional[str] = None
    xpath_selector: Optional[str] = None
    json_path: Optional[str] = None
    ai_hint: Optional[str] = None
    field_type: str = "text"  # text, number, url, image, html, list, json
    required: bool = False


class TemplateConfig(BaseModel):
    """Extraction and execution configuration for a template."""

    target_domains: list[str] = Field(default_factory=list)
    example_urls: list[str] = Field(default_factory=list)
    fields: list[FieldDefinition] = Field(default_factory=list)
    preferred_lane: str = "auto"  # api, http, browser, hard_target, auto
    extraction_type: str = "auto"  # auto, css, xpath, ai
    pagination: Optional[dict] = None  # {"type": "next_button", "selector": ".next"}
    rate_limit_rpm: int = Field(default=30, ge=1)
    proxy_required: bool = False
    proxy_type: Optional[str] = None  # datacenter, residential, mobile
    browser_required: bool = False
    stealth_required: bool = False
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    robots_compliance: bool = True
    extraction_rules: dict = Field(default_factory=dict)


class Template(BaseModel):
    """A reusable scraping template for common use cases."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    category: TemplateCategory = TemplateCategory.GENERAL
    tags: list[str] = Field(default_factory=list)
    icon: str = ""  # emoji or icon name
    platform: str = ""  # target platform name (e.g. "Amazon", "Shopify")
    version: str = "1.0.0"
    config: TemplateConfig = Field(default_factory=TemplateConfig)

    model_config = {"from_attributes": True}
