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
from packages.core.rate_limiter import InMemoryRateLimiter
from packages.core.quota_manager import QuotaManager, QuotaExceededError, UsageType

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
# Note: Amazon domains are handled separately via AMAZON_DOMAINS (Keepa API for product pages)
BROWSER_REQUIRED_DOMAINS: set[str] = {
    "instagram.com", "tiktok.com", "twitter.com",
}


def _is_amazon_product_url(url: str) -> bool:
    """Check if an Amazon URL is a product detail page (vs search/deals/category).

    Product pages contain /dp/ASIN or /gp/product/ASIN patterns.
    These go through Keepa API. Everything else goes through browser.
    """
    import re
    return bool(re.search(r"/(?:dp|gp/product|ASIN)/[A-Z0-9]{10}", url))

# Domains with known APIs
API_AVAILABLE_DOMAINS: dict[str, str] = {
    "shopify.com": "shopify_api",
    "myshopify.com": "shopify_api",
}

# Amazon domains — routed to Keepa API for product pages, browser for search/deals
AMAZON_DOMAINS: set[str] = {
    "amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr",
    "amazon.co.jp", "amazon.ca", "amazon.it", "amazon.es",
    "amazon.in", "amazon.com.mx", "amazon.com.br",
    # Additional Amazon TLDs (not all supported by Keepa — fall back to browser)
    "amazon.com.au", "amazon.nl", "amazon.sg", "amazon.ae",
    "amazon.sa", "amazon.pl", "amazon.se", "amazon.com.tr",
}

# Domains known to require hard-target (aggressive anti-bot protection)
HARD_TARGET_DOMAINS: set[str] = {
    "linkedin.com",
    "zillow.com",
    "indeed.com",
    "glassdoor.com",
    "nike.com",
    "ticketmaster.com",
}

# B4: WooCommerce URL pattern
WOOCOMMERCE_PATH_MARKER = "/wp-json/wc/"

# B4: RSS/feed URL suffixes and patterns
RSS_SUFFIXES = ("/feed", "/rss", ".xml", "/feed/", "/rss/")


def _is_woocommerce_url(url: str) -> bool:
    """Return True if the URL looks like a WooCommerce REST API endpoint."""
    return WOOCOMMERCE_PATH_MARKER in url


def _is_rss_url(url: str) -> bool:
    """Return True if the URL looks like an RSS or XML feed."""
    # Strip query string and fragment for suffix check
    from urllib.parse import urlparse
    path = urlparse(url).path.lower().rstrip("/")
    return any(path.endswith(suffix.rstrip("/")) for suffix in RSS_SUFFIXES) or path.endswith(".xml")


class RateLimitExceededError(Exception):
    """Raised when a tenant's rate limit is exceeded during routing."""

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        super().__init__(f"Rate limit exceeded for tenant '{tenant_id}'")


class ExecutionRouter:
    """Routes tasks to the appropriate execution lane."""

    def __init__(
        self,
        rate_limiter: Optional[InMemoryRateLimiter] = None,
        quota_manager: Optional[QuotaManager] = None,
    ) -> None:
        self._site_profiles: dict[str, Lane] = {}
        self._success_history: dict[str, dict[str, float]] = {}
        self._rate_limiter = rate_limiter
        self._quota_manager = quota_manager

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

        # 4. Amazon smart routing — Keepa API for product pages, browser for search/deals
        if self._match_domain(domain, {d: True for d in AMAZON_DOMAINS}):
            raw_url = str(task.url)
            if _is_amazon_product_url(raw_url):
                return RouteDecision(
                    lane=Lane.API,
                    reason=f"Amazon product page → Keepa API (ASIN detected)",
                    fallback_lanes=[Lane.BROWSER, Lane.HARD_TARGET],
                )
            else:
                return RouteDecision(
                    lane=Lane.BROWSER,
                    reason=f"Amazon search/deals page → browser rendering",
                    fallback_lanes=[Lane.HARD_TARGET],
                )

        # 5. Check if domain requires hard-target (exact or suffix match)
        if self._match_domain(domain, {d: True for d in HARD_TARGET_DOMAINS}):
            return RouteDecision(
                lane=Lane.HARD_TARGET,
                reason=f"{domain} requires hard-target stealth browser",
                fallback_lanes=[],
            )

        # 6. Check if domain requires browser (exact or suffix match)
        if self._match_domain(domain, {d: True for d in BROWSER_REQUIRED_DOMAINS}):
            return RouteDecision(
                lane=Lane.BROWSER,
                reason=f"{domain} requires browser rendering",
                fallback_lanes=[Lane.HARD_TARGET],
            )

        # 6. B4: WooCommerce REST API → use API lane
        raw_url = str(task.url)
        if _is_woocommerce_url(raw_url):
            return RouteDecision(
                lane=Lane.API,
                reason="WooCommerce REST API detected (/wp-json/wc/)",
                fallback_lanes=[Lane.HTTP],
            )

        # 7. B4: RSS / XML feed → use HTTP lane (lightweight, no JS needed)
        if _is_rss_url(raw_url):
            return RouteDecision(
                lane=Lane.HTTP,
                reason="RSS/XML feed detected — HTTP lane sufficient",
                fallback_lanes=[],
                confidence=0.9,
            )

        # 8. Default: try HTTP first
        return RouteDecision(
            lane=Lane.HTTP,
            reason="Default: try HTTP lane first",
            fallback_lanes=[Lane.BROWSER, Lane.HARD_TARGET],
            confidence=0.5,
        )

    async def route_with_checks(
        self, task: Task, policy: Optional[Policy] = None
    ) -> RouteDecision:
        """Route a task after enforcing rate limits and quota checks.

        Raises RateLimitExceededError or QuotaExceededError if the tenant
        is not allowed to proceed.
        """
        tenant_id = task.tenant_id
        policy_id = str(policy.id) if policy else None

        # 1. Rate limit check
        if self._rate_limiter is not None:
            allowed = await self._rate_limiter.acquire(tenant_id, policy_id)
            if not allowed:
                logger.warning(
                    "Task rejected: rate limit exceeded",
                    extra={"tenant_id": tenant_id, "task_id": str(task.id)},
                )
                raise RateLimitExceededError(tenant_id)

        # 2. Quota check
        if self._quota_manager is not None:
            await self._quota_manager.check_quota_or_raise(tenant_id)
            # Record task usage
            await self._quota_manager.record_usage(
                tenant_id, UsageType.TASKS, 1.0
            )

        # 3. Route normally
        return self.route(task, policy)

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
