"""Cost Tracker -- Track real $ cost of every external API call.

Every scrape operation creates a CostTracker instance.
As external APIs are called, costs are recorded.
The final cost breakdown is returned to the caller with every response.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any


# Real costs per API call (USD)
COST_TABLE: dict[str, float] = {
    # Amazon
    "keepa_asin": 0.01,         # ~1 token per ASIN
    "keepa_search": 0.02,       # keyword search
    "keepa_deals": 0.02,        # deals lookup
    # Search
    "serper_search": 0.002,     # Google search
    "serper_places": 0.002,     # Google Maps
    # TikTok
    "scrapecreators_shop": 0.0019,
    "scrapecreators_tiktok": 0.0019,
    "tiktok_api": 0.0,          # davidteather -- free
    # Platform APIs (free)
    "shopify_api": 0.0,
    "woocommerce_api": 0.0,
    # Infrastructure
    "playwright_page": 0.0001,  # browser rendering CPU
    "curl_cffi_page": 0.00001,  # HTTP fetch
    "facebook_playwright": 0.0002,
}


@dataclass
class CostRecord:
    """A single cost entry for one API call (or batch of calls)."""

    api: str
    calls: int
    cost_usd: float
    detail: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "api": self.api,
            "calls": self.calls,
            "cost_usd": round(self.cost_usd, 6),
            "detail": self.detail,
        }


class CostTracker:
    """Accumulates cost records for a single request/operation."""

    def __init__(self) -> None:
        self._records: list[CostRecord] = []

    def record(self, api: str, calls: int = 1, detail: str = "") -> None:
        """Record a cost entry for an external API call."""
        unit_cost = COST_TABLE.get(api, 0.0)
        total = unit_cost * calls
        self._records.append(
            CostRecord(api=api, calls=calls, cost_usd=total, detail=detail)
        )

    def total_usd(self) -> float:
        """Return the total accumulated cost in USD."""
        return sum(r.cost_usd for r in self._records)

    def total_calls(self) -> int:
        """Return the total number of external API calls."""
        return sum(r.calls for r in self._records)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the tracker to a dict suitable for JSON responses."""
        return {
            "total_usd": round(self.total_usd(), 6),
            "total_api_calls": self.total_calls(),
            "breakdown": [r.to_dict() for r in self._records],
        }

    def merge(self, other: "CostTracker") -> None:
        """Merge another tracker's records into this one."""
        self._records.extend(other._records)

    @property
    def records(self) -> list[CostRecord]:
        """Read-only access to the underlying records."""
        return list(self._records)
