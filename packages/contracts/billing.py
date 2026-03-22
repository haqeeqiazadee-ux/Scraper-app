"""Billing contract — defines tenant quota and usage tracking schema."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class PlanTier(StrEnum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UsageCounters(BaseModel):
    """Rolling usage counters for the current billing cycle."""

    tasks_today: int = Field(default=0, ge=0)
    browser_minutes_today: float = Field(default=0.0, ge=0.0)
    ai_tokens_today: int = Field(default=0, ge=0)
    storage_bytes_used: int = Field(default=0, ge=0)
    proxy_requests_today: int = Field(default=0, ge=0)


# Default quota limits per plan tier
PLAN_DEFAULTS: dict[PlanTier, dict] = {
    PlanTier.FREE: {
        "max_tasks_per_day": 50,
        "max_concurrent_tasks": 2,
        "max_browser_minutes_per_day": 10,
        "max_ai_tokens_per_day": 10_000,
        "max_storage_bytes": 100 * 1024 * 1024,  # 100MB
        "max_proxy_requests_per_day": 100,
    },
    PlanTier.STARTER: {
        "max_tasks_per_day": 500,
        "max_concurrent_tasks": 5,
        "max_browser_minutes_per_day": 60,
        "max_ai_tokens_per_day": 100_000,
        "max_storage_bytes": 1024 * 1024 * 1024,  # 1GB
        "max_proxy_requests_per_day": 1_000,
    },
    PlanTier.PRO: {
        "max_tasks_per_day": 5_000,
        "max_concurrent_tasks": 20,
        "max_browser_minutes_per_day": 600,
        "max_ai_tokens_per_day": 1_000_000,
        "max_storage_bytes": 10 * 1024 * 1024 * 1024,  # 10GB
        "max_proxy_requests_per_day": 10_000,
    },
    PlanTier.ENTERPRISE: {
        "max_tasks_per_day": 1_000_000,
        "max_concurrent_tasks": 100,
        "max_browser_minutes_per_day": 6_000,
        "max_ai_tokens_per_day": 10_000_000,
        "max_storage_bytes": 100 * 1024 * 1024 * 1024,  # 100GB
        "max_proxy_requests_per_day": 100_000,
    },
}


class TenantQuota(BaseModel):
    """Tenant quota and usage tracking."""

    tenant_id: str
    plan: PlanTier = PlanTier.FREE
    max_tasks_per_day: int = Field(default=50, ge=0)
    max_concurrent_tasks: int = Field(default=2, ge=1)
    max_browser_minutes_per_day: int = Field(default=10, ge=0)
    max_ai_tokens_per_day: int = Field(default=10_000, ge=0)
    max_storage_bytes: int = Field(default=100 * 1024 * 1024, ge=0)
    max_proxy_requests_per_day: int = Field(default=100, ge=0)
    current_usage: UsageCounters = Field(default_factory=UsageCounters)
    billing_cycle_start: date = Field(default_factory=date.today)
    billing_cycle_end: date = Field(default_factory=date.today)

    def is_within_quota(self, resource: str) -> bool:
        """Check if current usage is within quota for a given resource."""
        limits = {
            "tasks": (self.current_usage.tasks_today, self.max_tasks_per_day),
            "browser_minutes": (self.current_usage.browser_minutes_today, self.max_browser_minutes_per_day),
            "ai_tokens": (self.current_usage.ai_tokens_today, self.max_ai_tokens_per_day),
            "storage": (self.current_usage.storage_bytes_used, self.max_storage_bytes),
            "proxy_requests": (self.current_usage.proxy_requests_today, self.max_proxy_requests_per_day),
        }
        if resource not in limits:
            return True
        current, maximum = limits[resource]
        return current < maximum

    model_config = {"from_attributes": True}
