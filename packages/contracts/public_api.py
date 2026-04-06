"""Public API contracts — request/response schemas for the Zero Checksum API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field, HttpUrl


T = TypeVar("T")


# ---------------------------------------------------------------------------
# Shared envelope
# ---------------------------------------------------------------------------

class ApiMeta(BaseModel):
    """Metadata attached to every API response."""

    credits_used: int
    credits_remaining: Optional[int] = None
    duration_ms: int
    timestamp: datetime


class ApiError(BaseModel):
    """Structured error detail."""

    code: str
    message: str
    field: Optional[str] = None


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""

    request_id: str
    idempotency_key: Optional[str] = None
    status: Literal["success", "error", "accepted"]
    data: Optional[T] = None
    meta: ApiMeta
    errors: Optional[list[ApiError]] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------

class ScrapeRequest(BaseModel):
    """Request schema for the /scrape endpoint."""

    url: HttpUrl
    formats: list[str] = Field(default_factory=lambda: ["json"])
    wait_for: Optional[str] = None
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)
    headers: dict[str, str] = Field(default_factory=dict)
    webhook_url: Optional[HttpUrl] = None
    async_mode: bool = False


class ScrapeResult(BaseModel):
    """Result payload returned from a scrape operation."""

    url: str
    extracted_data: list[dict]
    markdown: Optional[str] = None
    html: Optional[str] = None
    item_count: int
    confidence: float
    extraction_method: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Crawl
# ---------------------------------------------------------------------------

class CrawlRequest(BaseModel):
    """Request schema for the /crawl endpoint."""

    url: HttpUrl
    max_depth: int = Field(default=3, ge=0, le=100)
    max_pages: int = Field(default=100, ge=1, le=10000)
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    formats: list[str] = Field(default_factory=lambda: ["json"])
    webhook_url: Optional[HttpUrl] = None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    """Request schema for the /search endpoint."""

    query: str = Field(min_length=1, max_length=400)
    max_results: int = Field(default=5, ge=1, le=20)
    scrape_results: bool = True
    formats: list[str] = Field(default_factory=lambda: ["json"])
    webhook_url: Optional[HttpUrl] = None


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------

class ExtractRequest(BaseModel):
    """Request schema for the /extract endpoint."""

    url: HttpUrl
    schema: dict
    formats: list[str] = Field(default_factory=lambda: ["json"])
    webhook_url: Optional[HttpUrl] = None


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

class JobStatus(BaseModel):
    """Status of an async job."""

    job_id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    progress: Optional[dict] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobResults(BaseModel):
    """Paginated results for a completed async job."""

    job_id: str
    items: list[dict]
    total_items: int
    has_more: bool


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------

class WebhookRegistration(BaseModel):
    """Schema for registering a webhook."""

    url: HttpUrl
    events: list[str] = Field(default_factory=lambda: ["job.completed", "job.failed"])
    secret: Optional[str] = None


# ---------------------------------------------------------------------------
# Usage / Account
# ---------------------------------------------------------------------------

class UsageRecord(BaseModel):
    """Single usage record."""

    request_id: str
    endpoint: str
    credits_used: int
    timestamp: datetime


class UsageResponse(BaseModel):
    """Aggregated usage for a billing period."""

    total_credits_used: int
    period_start: date
    period_end: date
    records: list[UsageRecord]


class AccountInfo(BaseModel):
    """Current account information."""

    tenant_id: str
    plan: str
    credits_remaining: int
    credits_limit: int
    api_keys: list[dict]


# ---------------------------------------------------------------------------
# API Key management
# ---------------------------------------------------------------------------

class ApiKeyCreate(BaseModel):
    """Schema for creating a new API key."""

    name: str
    scopes: list[str] = Field(default_factory=lambda: ["*"])
    expires_in_days: Optional[int] = None


class ApiKeyResponse(BaseModel):
    """API key info (without the secret key)."""

    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyResponse):
    """Returned once when a key is first created — includes the full key."""

    key: str


# ---------------------------------------------------------------------------
# Auth Scrape
# ---------------------------------------------------------------------------

class AuthSessionRequest(BaseModel):
    """Request to create an authenticated session from uploaded cookies."""

    cookies: list[dict[str, Any]]
    target_domain: Optional[str] = None


class AuthScrapeRequest(BaseModel):
    """Request to scrape a page using an authenticated session."""

    session_id: str
    target_url: HttpUrl
    extraction_mode: Literal["everything", "table", "fields", "links"] = "everything"
    schema: Optional[dict[str, Any]] = None
    max_pages: int = Field(default=1, ge=1, le=100)


# ---------------------------------------------------------------------------
# Amazon / Keepa
# ---------------------------------------------------------------------------

class AmazonProductRequest(BaseModel):
    """Look up an Amazon product by ASIN, URL, or keyword."""

    query: str = Field(min_length=1, description="ASIN, Amazon URL, or keyword")
    domain: str = "US"
    max_results: int = Field(default=10, ge=1, le=50)


class AmazonSearchRequest(BaseModel):
    """Advanced Amazon product search with filters."""

    title: Optional[str] = None
    brand: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    domain: str = "US"
    max_results: int = Field(default=10, ge=1, le=50)


class AmazonDealsRequest(BaseModel):
    """Find current Amazon deals."""

    min_discount_percent: int = Field(default=20, ge=1, le=99)
    domain: str = "US"


# ---------------------------------------------------------------------------
# Google Maps
# ---------------------------------------------------------------------------

class MapsSearchRequest(BaseModel):
    """Search Google Maps for businesses."""

    query: str = Field(min_length=1, max_length=500)
    max_results: int = Field(default=20, ge=1, le=50)
    location: Optional[str] = None


# ---------------------------------------------------------------------------
# Facebook
# ---------------------------------------------------------------------------

class FacebookSessionRequest(BaseModel):
    """Upload Facebook cookies for authenticated access."""

    cookies: list[dict[str, Any]]


class FacebookScrapeRequest(BaseModel):
    """Scrape a Facebook group."""

    url: HttpUrl
    max_posts: int = Field(default=100, ge=1, le=1000)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

class TemplateRunRequest(BaseModel):
    """Run a scraper template against a URL."""

    url: HttpUrl
    overrides: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------

class ScheduleCreateRequest(BaseModel):
    """Create a scheduled scrape."""

    url: HttpUrl
    schedule: str = Field(description="Cron expression, e.g. '0 */6 * * *'")
    task_type: str = "scrape"
