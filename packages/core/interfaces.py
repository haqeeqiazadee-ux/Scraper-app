"""
Protocol interfaces for all pluggable components.

These define the contracts that implementations must follow.
Using Protocol (structural subtyping) instead of ABC for flexibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


# =============================================================================
# Fetch Layer
# =============================================================================


@dataclass
class FetchRequest:
    """Request to fetch a URL."""

    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    proxy: Optional[str] = None
    timeout_ms: int = 30000
    follow_redirects: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchResponse:
    """Response from a fetch operation."""

    url: str
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    text: str = ""
    html: str = ""
    elapsed_ms: int = 0
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400


@runtime_checkable
class Fetcher(Protocol):
    """Interface for HTTP fetching (stealth, standard, etc.)."""

    async def fetch(self, request: FetchRequest) -> FetchResponse: ...

    async def close(self) -> None: ...


# =============================================================================
# Browser Layer
# =============================================================================


@runtime_checkable
class BrowserWorker(Protocol):
    """Interface for browser-based scraping (Playwright, etc.)."""

    async def fetch(self, request: FetchRequest) -> FetchResponse: ...

    async def scroll_to_bottom(self, max_scrolls: int = 50) -> int:
        """Scroll page to load dynamic content. Returns items found."""
        ...

    async def click_element(self, selector: str) -> bool:
        """Click an element on the page."""
        ...

    async def wait_for_selector(self, selector: str, timeout_ms: int = 5000) -> bool:
        """Wait for an element to appear."""
        ...

    async def get_page_html(self) -> str:
        """Get current page HTML after JS execution."""
        ...

    async def screenshot(self) -> bytes:
        """Take a screenshot of the current page."""
        ...

    async def close(self) -> None: ...


# =============================================================================
# Connector Layer
# =============================================================================


@dataclass
class ConnectorMetrics:
    """Metrics for a connector."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    last_error: Optional[str] = None


@runtime_checkable
class Connector(Protocol):
    """Interface for all connectors (HTTP, browser, proxy, CAPTCHA, API)."""

    async def fetch(self, request: FetchRequest) -> FetchResponse: ...

    async def health_check(self) -> bool: ...

    def get_metrics(self) -> ConnectorMetrics: ...


# =============================================================================
# Storage Layer
# =============================================================================


@runtime_checkable
class ObjectStore(Protocol):
    """Interface for object/artifact storage (S3, filesystem)."""

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str: ...

    async def get(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...

    async def list_keys(self, prefix: str = "") -> list[str]: ...

    async def get_presigned_url(self, key: str, ttl_seconds: int = 3600) -> str: ...


@runtime_checkable
class MetadataStore(Protocol):
    """Interface for relational metadata storage (PostgreSQL, SQLite)."""

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def execute(self, query: str, params: Optional[dict] = None) -> Any: ...

    async def health_check(self) -> bool: ...


@runtime_checkable
class QueueBackend(Protocol):
    """Interface for task queue (Redis, in-memory)."""

    async def enqueue(self, queue_name: str, message: dict) -> str: ...

    async def dequeue(self, queue_name: str, timeout_seconds: int = 0) -> Optional[dict]: ...

    async def ack(self, queue_name: str, message_id: str) -> None: ...

    async def nack(self, queue_name: str, message_id: str) -> None: ...

    async def queue_size(self, queue_name: str) -> int: ...


@runtime_checkable
class CacheBackend(Protocol):
    """Interface for cache/session store (Redis, in-memory)."""

    async def get(self, key: str) -> Optional[str]: ...

    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def increment(self, key: str, amount: int = 1) -> int: ...

    async def exists(self, key: str) -> bool: ...


# =============================================================================
# AI Layer
# =============================================================================


@runtime_checkable
class AIProvider(Protocol):
    """Interface for AI providers (Gemini, OpenAI, Ollama)."""

    async def extract(self, html: str, url: str, prompt: Optional[str] = None) -> list[dict]:
        """Extract structured data from HTML using AI."""
        ...

    async def classify(self, text: str, labels: list[str]) -> str:
        """Classify text into one of the given labels."""
        ...

    async def normalize(self, data: dict, target_schema: dict) -> dict:
        """Normalize extracted data to match a target schema."""
        ...

    def get_token_usage(self) -> int:
        """Return total tokens used in this session."""
        ...
