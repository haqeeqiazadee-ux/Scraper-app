"""
Execution Router — routes tasks to the correct execution lane.

Lane selection logic:
1. Check policy.preferred_lane → if set, use it
2. Check site_profile(url) → if API available, use API lane
3. Try HTTP lane first (fast, cheap)
4. If HTTP returns incomplete/empty → escalate to Browser lane
5. If Browser hits anti-bot → escalate to Hard-Target lane
6. After extraction → run through AI Normalization if confidence < threshold
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from packages.contracts.policy import LanePreference, Policy
from packages.contracts.task import Task

logger = logging.getLogger(__name__)


class Lane(StrEnum):
    API = "api"
    HTTP = "http"
    BROWSER = "browser"
    HARD_TARGET = "hard_target"


@dataclass
class RouteDecision:
    """Result of routing a task to a lane."""

    lane: Lane
    reason: str
    fallback_lanes: list[Lane]
    confidence: float = 1.0


# Domains known to require browser rendering
BROWSER_REQUIRED_DOMAINS: set[str] = {
    "amazon.com", "amazon.co.uk", "amazon.de",
    "instagram.com", "tiktok.com", "twitter.com",
}

# Domains with known APIs
API_AVAILABLE_DOMAINS: dict[str, str] = {
    "shopify.com": "shopify_api",
    "myshopify.com": "shopify_api",
}


class ExecutionRouter:
    """Routes tasks to the appropriate execution lane."""

    def __init__(self) -> None:
        self._site_profiles: dict[str, Lane] = {}
        self._success_history: dict[str, dict[str, float]] = {}

    def route(self, task: Task, policy: Optional[Policy] = None) -> RouteDecision:
        """Determine which execution lane should handle this task."""
        domain = self._extract_domain(str(task.url))

        # 1. Check policy preferred lane
        if policy and policy.preferred_lane != LanePreference.AUTO:
            lane = Lane(policy.preferred_lane.value)
            return RouteDecision(
                lane=lane,
                reason=f"Policy '{policy.name}' specifies {lane} lane",
                fallback_lanes=self._get_fallback_lanes(lane),
            )

        # 2. Check for known API availability (exact or suffix match)
        api_match = self._match_domain(domain, API_AVAILABLE_DOMAINS)
        if api_match:
            return RouteDecision(
                lane=Lane.API,
                reason=f"Known API available for {domain} (matched {api_match})",
                fallback_lanes=[Lane.HTTP, Lane.BROWSER],
            )

        # 3. Check site profiles (learned from history)
        if domain in self._site_profiles:
            lane = self._site_profiles[domain]
            return RouteDecision(
                lane=lane,
                reason=f"Site profile recommends {lane} for {domain}",
                fallback_lanes=self._get_fallback_lanes(lane),
                confidence=0.8,
            )

        # 4. Check if domain requires browser (exact or suffix match)
        if self._match_domain(domain, {d: True for d in BROWSER_REQUIRED_DOMAINS}):
            return RouteDecision(
                lane=Lane.BROWSER,
                reason=f"{domain} requires browser rendering",
                fallback_lanes=[Lane.HARD_TARGET],
            )

        # 5. Default: try HTTP first
        return RouteDecision(
            lane=Lane.HTTP,
            reason="Default: try HTTP lane first",
            fallback_lanes=[Lane.BROWSER, Lane.HARD_TARGET],
            confidence=0.5,
        )

    def record_outcome(self, domain: str, lane: Lane, success: bool) -> None:
        """Record the outcome of a lane execution for future routing decisions."""
        if domain not in self._success_history:
            self._success_history[domain] = {}

        key = lane.value
        if key not in self._success_history[domain]:
            self._success_history[domain][key] = 0.5

        # Exponential moving average
        alpha = 0.3
        current = self._success_history[domain][key]
        self._success_history[domain][key] = alpha * (1.0 if success else 0.0) + (1 - alpha) * current

        # Update site profile if we have enough data
        if success:
            self._site_profiles[domain] = lane

        logger.info(
            "Route outcome recorded",
            extra={"domain": domain, "lane": lane, "success": success},
        )

    def get_next_lane(self, decision: RouteDecision) -> Optional[Lane]:
        """Get the next fallback lane after the current one fails."""
        if not decision.fallback_lanes:
            return None
        return decision.fallback_lanes[0]

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix and port
        if domain.startswith("www."):
            domain = domain[4:]
        if ":" in domain:
            domain = domain.split(":")[0]
        return domain

    def _match_domain(self, domain: str, lookup: dict) -> Optional[str]:
        """Match domain exactly or by suffix (e.g., store.myshopify.com matches myshopify.com)."""
        if domain in lookup:
            return domain
        for known_domain in lookup:
            if domain.endswith("." + known_domain):
                return known_domain
        return None

    def _get_fallback_lanes(self, current: Lane) -> list[Lane]:
        """Get ordered fallback lanes for a given lane."""
        escalation = {
            Lane.API: [Lane.HTTP, Lane.BROWSER, Lane.HARD_TARGET],
            Lane.HTTP: [Lane.BROWSER, Lane.HARD_TARGET],
            Lane.BROWSER: [Lane.HARD_TARGET],
            Lane.HARD_TARGET: [],
        }
        return escalation.get(current, [])
