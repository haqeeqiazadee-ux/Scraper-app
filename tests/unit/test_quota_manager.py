"""Tests for packages.core.quota_manager — quota enforcement."""

from __future__ import annotations

from datetime import date

import pytest

from packages.contracts.billing import PlanTier, TenantQuota, UsageCounters
from packages.core.quota_manager import (
    QuotaExceededError,
    QuotaManager,
    QuotaStatus,
    UsageType,
)


@pytest.fixture
def manager() -> QuotaManager:
    return QuotaManager()


@pytest.fixture
def free_quota() -> TenantQuota:
    return TenantQuota(
        tenant_id="t1",
        plan=PlanTier.FREE,
        max_tasks_per_day=50,
        max_concurrent_tasks=2,
        max_browser_minutes_per_day=10,
        max_ai_tokens_per_day=10_000,
        max_storage_bytes=100 * 1024 * 1024,
        max_proxy_requests_per_day=100,
    )


class TestQuotaManager:
    @pytest.mark.asyncio
    async def test_check_quota_ok_when_no_quota_registered(
        self, manager: QuotaManager
    ) -> None:
        result = await manager.check_quota("unknown-tenant")
        assert result.status == QuotaStatus.OK
        assert result.exceeded_resources == []

    @pytest.mark.asyncio
    async def test_check_quota_ok_when_within_limits(
        self, manager: QuotaManager, free_quota: TenantQuota
    ) -> None:
        await manager.set_quota(free_quota)
        result = await manager.check_quota("t1")
        assert result.status == QuotaStatus.OK

    @pytest.mark.asyncio
    async def test_record_usage_increments_counter(
        self, manager: QuotaManager, free_quota: TenantQuota
    ) -> None:
        await manager.set_quota(free_quota)
        await manager.record_usage("t1", UsageType.TASKS, 5)
        usage = await manager.get_usage("t1")
        assert usage.tasks_today == 5

    @pytest.mark.asyncio
    async def test_record_usage_raises_when_exceeded(
        self, manager: QuotaManager, free_quota: TenantQuota
    ) -> None:
        free_quota.max_tasks_per_day = 3
        await manager.set_quota(free_quota)
        await manager.record_usage("t1", UsageType.TASKS, 3)
        with pytest.raises(QuotaExceededError) as exc_info:
            await manager.record_usage("t1", UsageType.TASKS, 1)
        assert exc_info.value.resource == "tasks"
        assert exc_info.value.tenant_id == "t1"

    @pytest.mark.asyncio
    async def test_check_quota_exceeded_status(
        self, manager: QuotaManager, free_quota: TenantQuota
    ) -> None:
        free_quota.max_tasks_per_day = 2
        free_quota.current_usage = UsageCounters(tasks_today=5)
        await manager.set_quota(free_quota)
        result = await manager.check_quota("t1")
        assert result.status == QuotaStatus.EXCEEDED
        assert "tasks" in result.exceeded_resources

    @pytest.mark.asyncio
    async def test_check_quota_warning_at_threshold(
        self, manager: QuotaManager, free_quota: TenantQuota
    ) -> None:
        free_quota.max_tasks_per_day = 10
        free_quota.current_usage = UsageCounters(tasks_today=9)  # 90% > 80%
        await manager.set_quota(free_quota)
        result = await manager.check_quota("t1")
        assert result.status == QuotaStatus.WARNING
        assert "tasks" in result.warning_resources

    @pytest.mark.asyncio
    async def test_check_quota_or_raise_throws(
        self, manager: QuotaManager, free_quota: TenantQuota
    ) -> None:
        free_quota.max_tasks_per_day = 1
        free_quota.current_usage = UsageCounters(tasks_today=5)
        await manager.set_quota(free_quota)
        with pytest.raises(QuotaExceededError):
            await manager.check_quota_or_raise("t1")

    @pytest.mark.asyncio
    async def test_reset_usage_clears_counters(
        self, manager: QuotaManager, free_quota: TenantQuota
    ) -> None:
        await manager.set_quota(free_quota)
        await manager.record_usage("t1", UsageType.TASKS, 10)
        await manager.reset_usage("t1")
        usage = await manager.get_usage("t1")
        assert usage.tasks_today == 0

    @pytest.mark.asyncio
    async def test_set_quota_from_plan(self, manager: QuotaManager) -> None:
        quota = await manager.set_quota_from_plan("t2", PlanTier.PRO)
        assert quota.max_tasks_per_day == 5_000
        assert quota.plan == PlanTier.PRO

    @pytest.mark.asyncio
    async def test_record_no_quota_is_noop(self, manager: QuotaManager) -> None:
        """Recording usage for a tenant with no quota should not raise."""
        await manager.record_usage("ghost", UsageType.TASKS, 100)
        usage = await manager.get_usage("ghost")
        assert usage.tasks_today == 0  # no quota, returns empty counters

    @pytest.mark.asyncio
    async def test_multiple_resource_types(
        self, manager: QuotaManager, free_quota: TenantQuota
    ) -> None:
        await manager.set_quota(free_quota)
        await manager.record_usage("t1", UsageType.TASKS, 5)
        await manager.record_usage("t1", UsageType.AI_TOKENS, 1000)
        await manager.record_usage("t1", UsageType.PROXY_REQUESTS, 10)
        usage = await manager.get_usage("t1")
        assert usage.tasks_today == 5
        assert usage.ai_tokens_today == 1000
        assert usage.proxy_requests_today == 10

    @pytest.mark.asyncio
    async def test_daily_reset_on_date_change(
        self, manager: QuotaManager, free_quota: TenantQuota
    ) -> None:
        """Simulate a date rollover by back-dating the billing_cycle_start."""
        free_quota.current_usage = UsageCounters(tasks_today=40)
        free_quota.billing_cycle_start = date(2020, 1, 1)  # far in the past
        await manager.set_quota(free_quota)
        result = await manager.check_quota("t1")
        # After auto-reset, tasks_today should be 0
        assert result.usage.tasks_today == 0
        assert result.status == QuotaStatus.OK
