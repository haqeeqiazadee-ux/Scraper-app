"""
Core engine package — shared interfaces, router, session manager, AI provider, storage.

This package defines the Protocol interfaces that all implementations must follow,
ensuring consistent behavior across cloud, self-hosted, and desktop runtime modes.
"""

from packages.core.interfaces import (
    Fetcher,
    FetchRequest,
    FetchResponse,
    BrowserWorker,
    Connector,
    ConnectorMetrics,
    ObjectStore,
    MetadataStore,
    QueueBackend,
    CacheBackend,
    AIProvider,
)

from packages.core.content_filter import ContentFilter

__all__ = [
    "Fetcher", "FetchRequest", "FetchResponse",
    "BrowserWorker",
    "Connector", "ConnectorMetrics",
    "ObjectStore", "MetadataStore", "QueueBackend", "CacheBackend",
    "AIProvider",
    "ContentFilter",
]
