"""
Rate limiter — token bucket algorithm for per-tenant and per-policy rate limiting.

Provides an in-memory implementation with an extension point for Redis-backed
storage.  Thread-safe via asyncio.Lock.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket with configurable refill rates."""

    max_tokens: float
    refill_rate: float  # tokens per second
    tokens: float = -1.0  # sentinel: -1 means "use max_tokens"
    last_refill: float = -1.0  # sentinel: -1 means "use now"

    def __post_init__(self) -> None:
        if self.last_refill < 0.0:
            self.last_refill = time.monotonic()
        if self.tokens < 0.0:
            self.tokens = self.max_tokens

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def try_consume(self, count: float = 1.0) -> bool:
        """Try to consume tokens.  Returns True if successful."""
        self._refill()
        if self.tokens >= count:
            self.tokens -= count
            return True
        return False

    @property
    def remaining(self) -> int:
        """Return remaining tokens (after refill)."""
        self._refill()
        return int(self.tokens)

    @property
    def retry_after(self) -> float:
        """Seconds until at least 1 token is available."""
        self._refill()
        if self.tokens >= 1.0:
            return 0.0
        deficit = 1.0 - self.tokens
        return deficit / self.refill_rate if self.refill_rate > 0 else 0.0


@dataclass
class RateLimitConfig:
    """Rate limiting parameters for a tenant or policy."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10


@dataclass
class _TenantBuckets:
    """Holds per-minute and per-hour buckets for a tenant."""

    minute_bucket: TokenBucket
    hour_bucket: TokenBucket
    policy_buckets: dict[str, TokenBucket] = field(default_factory=dict)


class RateLimitBackend(Protocol):
    """Extension point for external rate-limit storage (e.g. Redis)."""

    async def acquire(self, key: str, config: RateLimitConfig) -> bool: ...

    async def get_remaining(self, key: str) -> int: ...


class InMemoryRateLimiter:
    """In-memory, asyncio-safe rate limiter using token buckets.

    Suitable for single-process deployments.  For multi-process / distributed
    setups, swap in a Redis-backed ``RateLimitBackend``.
    """

    def __init__(self, default_config: Optional[RateLimitConfig] = None) -> None:
        self._default_config = default_config or RateLimitConfig()
        self._tenants: dict[str, _TenantBuckets] = {}
        self._configs: dict[str, RateLimitConfig] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure_tenant(self, tenant_id: str, config: RateLimitConfig) -> None:
        """Set rate-limit configuration for a specific tenant."""
        self._configs[tenant_id] = config

    def configure_policy(
        self, tenant_id: str, policy_id: str, config: RateLimitConfig
    ) -> None:
        """Set rate-limit configuration for a specific policy under a tenant."""
        key = f"{tenant_id}:{policy_id}"
        self._configs[key] = config

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_config(self, tenant_id: str, policy_id: Optional[str] = None) -> RateLimitConfig:
        """Resolve the effective config — policy > tenant > default."""
        if policy_id:
            key = f"{tenant_id}:{policy_id}"
            if key in self._configs:
                return self._configs[key]
        if tenant_id in self._configs:
            return self._configs[tenant_id]
        return self._default_config

    def _ensure_buckets(self, tenant_id: str) -> _TenantBuckets:
        """Lazily create tenant-level buckets (always uses tenant config, not policy)."""
        if tenant_id not in self._tenants:
            tenant_config = self._get_config(tenant_id, policy_id=None)
            self._tenants[tenant_id] = _TenantBuckets(
                minute_bucket=TokenBucket(
                    max_tokens=float(tenant_config.burst_size),
                    refill_rate=tenant_config.requests_per_minute / 60.0,
                ),
                hour_bucket=TokenBucket(
                    max_tokens=float(tenant_config.requests_per_hour),
                    refill_rate=tenant_config.requests_per_hour / 3600.0,
                ),
            )
        return self._tenants[tenant_id]

    def _ensure_policy_bucket(
        self,
        buckets: _TenantBuckets,
        policy_id: str,
        config: RateLimitConfig,
    ) -> TokenBucket:
        """Lazily create a per-policy bucket."""
        if policy_id not in buckets.policy_buckets:
            buckets.policy_buckets[policy_id] = TokenBucket(
                max_tokens=float(config.burst_size),
                refill_rate=config.requests_per_minute / 60.0,
            )
        return buckets.policy_buckets[policy_id]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def acquire(
        self,
        tenant_id: str,
        policy_id: Optional[str] = None,
    ) -> bool:
        """Try to acquire a rate-limit token.

        Returns True if the request is allowed, False if rate-limited.
        """
        async with self._lock:
            buckets = self._ensure_buckets(tenant_id)

            # Check tenant-level minute bucket
            if not buckets.minute_bucket.try_consume():
                logger.warning(
                    "Rate limit exceeded (per-minute)",
                    extra={"tenant_id": tenant_id, "policy_id": policy_id},
                )
                return False

            # Check tenant-level hour bucket
            if not buckets.hour_bucket.try_consume():
                # Refund the minute token
                buckets.minute_bucket.tokens = min(
                    buckets.minute_bucket.max_tokens,
                    buckets.minute_bucket.tokens + 1,
                )
                logger.warning(
                    "Rate limit exceeded (per-hour)",
                    extra={"tenant_id": tenant_id, "policy_id": policy_id},
                )
                return False

            # Check policy-level bucket if applicable
            if policy_id:
                policy_config = self._get_config(tenant_id, policy_id)
                pb = self._ensure_policy_bucket(buckets, policy_id, policy_config)
                if not pb.try_consume():
                    # Refund tenant-level tokens
                    buckets.minute_bucket.tokens = min(
                        buckets.minute_bucket.max_tokens,
                        buckets.minute_bucket.tokens + 1,
                    )
                    buckets.hour_bucket.tokens = min(
                        buckets.hour_bucket.max_tokens,
                        buckets.hour_bucket.tokens + 1,
                    )
                    logger.warning(
                        "Rate limit exceeded (policy)",
                        extra={"tenant_id": tenant_id, "policy_id": policy_id},
                    )
                    return False

            return True

    async def get_remaining(self, tenant_id: str) -> int:
        """Return the minimum remaining tokens across all tenant buckets."""
        async with self._lock:
            if tenant_id not in self._tenants:
                config = self._get_config(tenant_id)
                return config.burst_size
            buckets = self._tenants[tenant_id]
            return min(buckets.minute_bucket.remaining, buckets.hour_bucket.remaining)

    async def get_limit(self, tenant_id: str) -> int:
        """Return the per-minute limit for a tenant."""
        config = self._get_config(tenant_id)
        return config.requests_per_minute

    async def get_retry_after(self, tenant_id: str) -> float:
        """Return seconds until next token is available."""
        async with self._lock:
            if tenant_id not in self._tenants:
                return 0.0
            buckets = self._tenants[tenant_id]
            return max(
                buckets.minute_bucket.retry_after,
                buckets.hour_bucket.retry_after,
            )

    async def reset(self, tenant_id: str) -> None:
        """Reset all buckets for a tenant."""
        async with self._lock:
            self._tenants.pop(tenant_id, None)
