"""
Quota manager — enforce per-tenant resource quotas.

Tracks daily usage counters and checks against TenantQuota limits before
task execution.  In-memory implementation suitable for single-process
deployments; persistence can be layered via a database or Redis backend.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Optional

from packages.contracts.billing import PlanTier, TenantQuota, UsageCounters, PLAN_DEFAULTS

logger = logging.getLogger(__name__)


class UsageType(StrEnum):
    """Resource usage categories."""

    TASKS = "tasks"
    BROWSER_MINUTES = "browser_minutes"
    AI_TOKENS = "ai_tokens"
    STORAGE = "storage"
    PROXY_REQUESTS = "proxy_requests"


class QuotaStatus(StrEnum):
    """Result of a quota check."""

    OK = "ok"
    WARNING = "warning"  # >80% used
    EXCEEDED = "exceeded"


class QuotaExceededError(Exception):
    """Raised when a tenant has exceeded their quota."""

    def __init__(
        self,
        tenant_id: str,
        resource: str,
        current: float,
        limit: float,
    ) -> None:
        self.tenant_id = tenant_id
        self.resource = resource
        self.current = current
        self.limit = limit
        super().__init__(
            f"Quota exceeded for tenant '{tenant_id}': "
            f"{resource} usage {current}/{limit}"
        )


@dataclass
class QuotaCheckResult:
    """Detailed quota check result."""

    status: QuotaStatus
    tenant_id: str
    usage: UsageCounters
    exceeded_resources: list[str]
    warning_resources: list[str]


class QuotaManager:
    """In-memory per-tenant quota manager.

    Thread-safe via asyncio.Lock.
    """

    WARNING_THRESHOLD: float = 0.8  # 80% usage triggers warning

    def __init__(self) -> None:
        self._quotas: dict[str, TenantQuota] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    async def set_quota(self, quota: TenantQuota) -> None:
        """Register or update a tenant's quota."""
        async with self._lock:
            self._quotas[quota.tenant_id] = quota
            logger.info(
                "Quota configured",
                extra={"tenant_id": quota.tenant_id, "plan": quota.plan},
            )

    async def set_quota_from_plan(
        self, tenant_id: str, plan: PlanTier
    ) -> TenantQuota:
        """Create a quota from plan defaults and register it."""
        defaults = PLAN_DEFAULTS[plan]
        quota = TenantQuota(
            tenant_id=tenant_id,
            plan=plan,
            **defaults,
        )
        await self.set_quota(quota)
        return quota

    async def get_quota(self, tenant_id: str) -> Optional[TenantQuota]:
        """Return the current quota object for a tenant."""
        async with self._lock:
            return self._quotas.get(tenant_id)

    # ------------------------------------------------------------------
    # Quota checking
    # ------------------------------------------------------------------

    async def check_quota(self, tenant_id: str) -> QuotaCheckResult:
        """Check all resources for a tenant.

        Returns a QuotaCheckResult indicating overall status and any
        exceeded or warning-level resources.
        """
        async with self._lock:
            quota = self._quotas.get(tenant_id)
            if quota is None:
                # No quota registered — allow by default (FREE tier defaults)
                return QuotaCheckResult(
                    status=QuotaStatus.OK,
                    tenant_id=tenant_id,
                    usage=UsageCounters(),
                    exceeded_resources=[],
                    warning_resources=[],
                )

            self._maybe_reset_daily(quota)

            exceeded: list[str] = []
            warning: list[str] = []

            checks = {
                "tasks": (quota.current_usage.tasks_today, quota.max_tasks_per_day),
                "browser_minutes": (
                    quota.current_usage.browser_minutes_today,
                    quota.max_browser_minutes_per_day,
                ),
                "ai_tokens": (
                    quota.current_usage.ai_tokens_today,
                    quota.max_ai_tokens_per_day,
                ),
                "storage": (
                    quota.current_usage.storage_bytes_used,
                    quota.max_storage_bytes,
                ),
                "proxy_requests": (
                    quota.current_usage.proxy_requests_today,
                    quota.max_proxy_requests_per_day,
                ),
            }

            for resource, (current, limit) in checks.items():
                if limit == 0:
                    continue
                ratio = current / limit
                if ratio >= 1.0:
                    exceeded.append(resource)
                elif ratio >= self.WARNING_THRESHOLD:
                    warning.append(resource)

            if exceeded:
                status = QuotaStatus.EXCEEDED
            elif warning:
                status = QuotaStatus.WARNING
            else:
                status = QuotaStatus.OK

            return QuotaCheckResult(
                status=status,
                tenant_id=tenant_id,
                usage=quota.current_usage.model_copy(),
                exceeded_resources=exceeded,
                warning_resources=warning,
            )

    async def check_quota_or_raise(self, tenant_id: str) -> QuotaCheckResult:
        """Check quota and raise QuotaExceededError if any resource is exceeded."""
        result = await self.check_quota(tenant_id)
        if result.status == QuotaStatus.EXCEEDED:
            # Report first exceeded resource
            resource = result.exceeded_resources[0]
            quota = self._quotas[tenant_id]
            current, limit = self._get_usage_and_limit(quota, resource)
            raise QuotaExceededError(
                tenant_id=tenant_id,
                resource=resource,
                current=current,
                limit=limit,
            )
        return result

    # ------------------------------------------------------------------
    # Usage recording
    # ------------------------------------------------------------------

    async def record_usage(
        self,
        tenant_id: str,
        usage_type: UsageType,
        amount: float = 1.0,
    ) -> None:
        """Record resource usage for a tenant.

        Raises QuotaExceededError if recording would exceed the limit.
        """
        async with self._lock:
            quota = self._quotas.get(tenant_id)
            if quota is None:
                logger.debug(
                    "No quota registered, skipping usage recording",
                    extra={"tenant_id": tenant_id},
                )
                return

            self._maybe_reset_daily(quota)
            usage = quota.current_usage

            if usage_type == UsageType.TASKS:
                if usage.tasks_today + amount > quota.max_tasks_per_day:
                    raise QuotaExceededError(
                        tenant_id, "tasks", usage.tasks_today, quota.max_tasks_per_day
                    )
                usage.tasks_today += int(amount)
            elif usage_type == UsageType.BROWSER_MINUTES:
                if usage.browser_minutes_today + amount > quota.max_browser_minutes_per_day:
                    raise QuotaExceededError(
                        tenant_id,
                        "browser_minutes",
                        usage.browser_minutes_today,
                        quota.max_browser_minutes_per_day,
                    )
                usage.browser_minutes_today += amount
            elif usage_type == UsageType.AI_TOKENS:
                if usage.ai_tokens_today + amount > quota.max_ai_tokens_per_day:
                    raise QuotaExceededError(
                        tenant_id,
                        "ai_tokens",
                        usage.ai_tokens_today,
                        quota.max_ai_tokens_per_day,
                    )
                usage.ai_tokens_today += int(amount)
            elif usage_type == UsageType.STORAGE:
                if usage.storage_bytes_used + amount > quota.max_storage_bytes:
                    raise QuotaExceededError(
                        tenant_id,
                        "storage",
                        usage.storage_bytes_used,
                        quota.max_storage_bytes,
                    )
                usage.storage_bytes_used += int(amount)
            elif usage_type == UsageType.PROXY_REQUESTS:
                if usage.proxy_requests_today + amount > quota.max_proxy_requests_per_day:
                    raise QuotaExceededError(
                        tenant_id,
                        "proxy_requests",
                        usage.proxy_requests_today,
                        quota.max_proxy_requests_per_day,
                    )
                usage.proxy_requests_today += int(amount)

            logger.debug(
                "Usage recorded",
                extra={
                    "tenant_id": tenant_id,
                    "usage_type": usage_type,
                    "amount": amount,
                },
            )

    async def get_usage(self, tenant_id: str) -> UsageCounters:
        """Return current usage counters for a tenant."""
        async with self._lock:
            quota = self._quotas.get(tenant_id)
            if quota is None:
                return UsageCounters()
            self._maybe_reset_daily(quota)
            return quota.current_usage.model_copy()

    # ------------------------------------------------------------------
    # Billing period management
    # ------------------------------------------------------------------

    async def reset_usage(self, tenant_id: str) -> None:
        """Manually reset usage counters for a tenant."""
        async with self._lock:
            quota = self._quotas.get(tenant_id)
            if quota is not None:
                quota.current_usage = UsageCounters()
                quota.billing_cycle_start = date.today()
                logger.info(
                    "Usage counters reset",
                    extra={"tenant_id": tenant_id},
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _maybe_reset_daily(self, quota: TenantQuota) -> None:
        """Reset daily counters if the billing day has rolled over."""
        today = date.today()
        if quota.billing_cycle_start < today:
            quota.current_usage.tasks_today = 0
            quota.current_usage.browser_minutes_today = 0.0
            quota.current_usage.ai_tokens_today = 0
            quota.current_usage.proxy_requests_today = 0
            quota.billing_cycle_start = today
            logger.info(
                "Daily counters auto-reset",
                extra={"tenant_id": quota.tenant_id},
            )

    @staticmethod
    def _get_usage_and_limit(
        quota: TenantQuota, resource: str
    ) -> tuple[float, float]:
        """Return (current_usage, limit) for a named resource."""
        mapping: dict[str, tuple[float, float]] = {
            "tasks": (quota.current_usage.tasks_today, quota.max_tasks_per_day),
            "browser_minutes": (
                quota.current_usage.browser_minutes_today,
                quota.max_browser_minutes_per_day,
            ),
            "ai_tokens": (
                quota.current_usage.ai_tokens_today,
                quota.max_ai_tokens_per_day,
            ),
            "storage": (
                quota.current_usage.storage_bytes_used,
                quota.max_storage_bytes,
            ),
            "proxy_requests": (
                quota.current_usage.proxy_requests_today,
                quota.max_proxy_requests_per_day,
            ),
        }
        return mapping.get(resource, (0, 0))
