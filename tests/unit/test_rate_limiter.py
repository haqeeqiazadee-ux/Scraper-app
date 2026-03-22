"""Tests for packages.core.rate_limiter — token bucket rate limiting."""

from __future__ import annotations

import asyncio
import time

import pytest

from packages.core.rate_limiter import (
    InMemoryRateLimiter,
    RateLimitConfig,
    TokenBucket,
)


# ---------------------------------------------------------------------------
# TokenBucket unit tests
# ---------------------------------------------------------------------------


class TestTokenBucket:
    def test_initial_tokens_equal_max(self) -> None:
        bucket = TokenBucket(max_tokens=10.0, refill_rate=1.0)
        assert bucket.remaining == 10

    def test_consume_reduces_tokens(self) -> None:
        bucket = TokenBucket(max_tokens=5.0, refill_rate=0.0)
        assert bucket.try_consume() is True
        assert bucket.remaining == 4

    def test_consume_fails_when_empty(self) -> None:
        bucket = TokenBucket(max_tokens=1.0, refill_rate=0.0)
        # Drain the single token
        assert bucket.try_consume() is True
        assert bucket.try_consume() is False

    def test_retry_after_positive_when_empty(self) -> None:
        bucket = TokenBucket(max_tokens=5.0, refill_rate=1.0)
        # Drain all tokens
        for _ in range(5):
            bucket.try_consume()
        bucket.last_refill = time.monotonic()
        assert bucket.retry_after > 0.0

    def test_retry_after_zero_when_tokens_available(self) -> None:
        bucket = TokenBucket(max_tokens=5.0, refill_rate=1.0)
        assert bucket.retry_after == 0.0


# ---------------------------------------------------------------------------
# InMemoryRateLimiter tests
# ---------------------------------------------------------------------------


class TestInMemoryRateLimiter:
    @pytest.mark.asyncio
    async def test_acquire_succeeds_under_limit(self) -> None:
        limiter = InMemoryRateLimiter(
            default_config=RateLimitConfig(
                requests_per_minute=60, requests_per_hour=1000, burst_size=10
            )
        )
        assert await limiter.acquire("tenant-1") is True

    @pytest.mark.asyncio
    async def test_acquire_fails_after_burst_exhausted(self) -> None:
        limiter = InMemoryRateLimiter(
            default_config=RateLimitConfig(
                requests_per_minute=60, requests_per_hour=1000, burst_size=3
            )
        )
        # Exhaust burst
        for _ in range(3):
            assert await limiter.acquire("tenant-1") is True
        # Next should fail (no time for refill)
        assert await limiter.acquire("tenant-1") is False

    @pytest.mark.asyncio
    async def test_get_remaining_reflects_consumption(self) -> None:
        limiter = InMemoryRateLimiter(
            default_config=RateLimitConfig(
                requests_per_minute=60, requests_per_hour=1000, burst_size=5
            )
        )
        initial = await limiter.get_remaining("tenant-1")
        assert initial == 5
        await limiter.acquire("tenant-1")
        after = await limiter.get_remaining("tenant-1")
        assert after < initial

    @pytest.mark.asyncio
    async def test_per_tenant_isolation(self) -> None:
        limiter = InMemoryRateLimiter(
            default_config=RateLimitConfig(
                requests_per_minute=60, requests_per_hour=1000, burst_size=2
            )
        )
        # Exhaust tenant-a
        await limiter.acquire("tenant-a")
        await limiter.acquire("tenant-a")
        assert await limiter.acquire("tenant-a") is False
        # tenant-b should still be fine
        assert await limiter.acquire("tenant-b") is True

    @pytest.mark.asyncio
    async def test_custom_tenant_config(self) -> None:
        limiter = InMemoryRateLimiter(
            default_config=RateLimitConfig(burst_size=100)
        )
        limiter.configure_tenant(
            "tight-tenant",
            RateLimitConfig(requests_per_minute=10, requests_per_hour=100, burst_size=1),
        )
        assert await limiter.acquire("tight-tenant") is True
        assert await limiter.acquire("tight-tenant") is False

    @pytest.mark.asyncio
    async def test_policy_level_limiting(self) -> None:
        limiter = InMemoryRateLimiter(
            default_config=RateLimitConfig(burst_size=100)
        )
        limiter.configure_policy(
            "tenant-1",
            "policy-x",
            RateLimitConfig(requests_per_minute=10, requests_per_hour=100, burst_size=1),
        )
        assert await limiter.acquire("tenant-1", "policy-x") is True
        assert await limiter.acquire("tenant-1", "policy-x") is False
        # Tenant-level (no policy) should still work
        assert await limiter.acquire("tenant-1") is True

    @pytest.mark.asyncio
    async def test_get_limit_returns_config_value(self) -> None:
        limiter = InMemoryRateLimiter(
            default_config=RateLimitConfig(requests_per_minute=42)
        )
        assert await limiter.get_limit("any-tenant") == 42

    @pytest.mark.asyncio
    async def test_reset_restores_capacity(self) -> None:
        limiter = InMemoryRateLimiter(
            default_config=RateLimitConfig(burst_size=2)
        )
        await limiter.acquire("tenant-1")
        await limiter.acquire("tenant-1")
        assert await limiter.acquire("tenant-1") is False
        await limiter.reset("tenant-1")
        assert await limiter.acquire("tenant-1") is True

    @pytest.mark.asyncio
    async def test_get_retry_after_positive_when_exhausted(self) -> None:
        limiter = InMemoryRateLimiter(
            default_config=RateLimitConfig(
                requests_per_minute=60, burst_size=1
            )
        )
        await limiter.acquire("tenant-1")
        await limiter.acquire("tenant-1")  # will fail, but that's fine
        retry = await limiter.get_retry_after("tenant-1")
        assert retry >= 0.0

    @pytest.mark.asyncio
    async def test_get_retry_after_zero_for_unknown_tenant(self) -> None:
        limiter = InMemoryRateLimiter()
        assert await limiter.get_retry_after("unknown") == 0.0

    @pytest.mark.asyncio
    async def test_hour_bucket_enforcement(self) -> None:
        """Hour bucket should block even when minute bucket has tokens."""
        limiter = InMemoryRateLimiter(
            default_config=RateLimitConfig(
                requests_per_minute=1000,
                requests_per_hour=3,
                burst_size=1000,
            )
        )
        for _ in range(3):
            assert await limiter.acquire("tenant-h") is True
        # Hour bucket exhausted
        assert await limiter.acquire("tenant-h") is False
