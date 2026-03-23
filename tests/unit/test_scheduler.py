"""Tests for TaskScheduler — cron parsing, interval scheduling, lifecycle."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from packages.contracts.task import Task, TaskStatus
from packages.core.scheduler import (
    TaskScheduler,
    ScheduleEntry,
    parse_cron,
    parse_schedule,
    cron_matches,
)


# ──────────────────────── Cron parsing tests ────────────────────────


class TestParseCron:

    def test_all_stars(self) -> None:
        """'* * * * *' should match every minute."""
        fields = parse_cron("* * * * *")
        assert len(fields) == 5
        assert fields[0] == set(range(0, 60))
        assert fields[1] == set(range(0, 24))
        assert fields[2] == set(range(1, 32))
        assert fields[3] == set(range(1, 13))
        assert fields[4] == set(range(0, 7))

    def test_specific_values(self) -> None:
        """'30 14 1 6 3' should match minute=30, hour=14, day=1, month=6, weekday=3."""
        fields = parse_cron("30 14 1 6 3")
        assert fields[0] == {30}
        assert fields[1] == {14}
        assert fields[2] == {1}
        assert fields[3] == {6}
        assert fields[4] == {3}

    def test_ranges(self) -> None:
        """'0-5 * * * *' should match minutes 0 through 5."""
        fields = parse_cron("0-5 * * * *")
        assert fields[0] == {0, 1, 2, 3, 4, 5}

    def test_step_values(self) -> None:
        """'*/15 * * * *' should match minutes 0,15,30,45."""
        fields = parse_cron("*/15 * * * *")
        assert fields[0] == {0, 15, 30, 45}

    def test_lists(self) -> None:
        """'0,15,30,45 * * * *' should match those specific minutes."""
        fields = parse_cron("0,15,30,45 * * * *")
        assert fields[0] == {0, 15, 30, 45}

    def test_invalid_field_count(self) -> None:
        """Non-5-field expressions should raise ValueError."""
        with pytest.raises(ValueError, match="5 fields"):
            parse_cron("* * *")

    def test_range_with_step(self) -> None:
        """'1-30/5 * * * *' should match 1,6,11,16,21,26."""
        fields = parse_cron("1-30/5 * * * *")
        assert fields[0] == {1, 6, 11, 16, 21, 26}


class TestCronMatches:

    def test_matches_specific_time(self) -> None:
        """Cron '30 14 * * *' should match 14:30 on any day."""
        fields = parse_cron("30 14 * * *")
        dt = datetime(2025, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        assert cron_matches(fields, dt) is True

    def test_no_match(self) -> None:
        """Cron '30 14 * * *' should not match 15:00."""
        fields = parse_cron("30 14 * * *")
        dt = datetime(2025, 6, 15, 15, 0, 0, tzinfo=timezone.utc)
        assert cron_matches(fields, dt) is False

    def test_weekday_match(self) -> None:
        """Cron '* * * * 0' (Sunday) should match a Sunday."""
        fields = parse_cron("* * * * 0")
        # 2025-06-15 is a Sunday
        dt = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        assert cron_matches(fields, dt) is True


# ──────────────────────── Schedule parsing tests ────────────────────────


class TestParseSchedule:

    def test_parse_interval_minutes(self) -> None:
        """'every 30 minutes' should produce an interval schedule."""
        entry = parse_schedule("every 30 minutes")
        assert entry.schedule_type == "interval"
        assert entry.interval_seconds == 1800.0

    def test_parse_interval_hours(self) -> None:
        """'every 2 hours' should produce an interval schedule."""
        entry = parse_schedule("every 2 hours")
        assert entry.schedule_type == "interval"
        assert entry.interval_seconds == 7200.0

    def test_parse_iso_datetime(self) -> None:
        """ISO-8601 datetime should produce a one-time schedule."""
        entry = parse_schedule("2025-06-15T10:30:00Z")
        assert entry.schedule_type == "once"
        assert entry.once_at is not None
        assert entry.once_at.hour == 10
        assert entry.once_at.minute == 30

    def test_parse_cron_expression(self) -> None:
        """Standard 5-field cron should be parsed as cron type."""
        entry = parse_schedule("*/15 * * * *")
        assert entry.schedule_type == "cron"
        assert entry.cron_fields is not None

    def test_invalid_schedule_raises(self) -> None:
        """Invalid schedule strings should raise ValueError."""
        with pytest.raises(ValueError, match="Cannot parse schedule"):
            parse_schedule("not a valid schedule at all!!!")


# ──────────────────────── TaskScheduler tests ────────────────────────


class TestTaskScheduler:

    @pytest.mark.asyncio
    async def test_add_schedule(self) -> None:
        """Adding a schedule should store it in the scheduler."""
        enqueue_fn = AsyncMock()
        scheduler = TaskScheduler(enqueue_fn=enqueue_fn)
        task = Task(
            tenant_id="t1",
            url="https://example.com",
            schedule="every 30 minutes",
        )
        entry = await scheduler.add_schedule(task)
        assert entry.schedule_type == "interval"
        assert entry.id in scheduler.schedules

    @pytest.mark.asyncio
    async def test_add_schedule_no_schedule_field(self) -> None:
        """Adding a task without a schedule field should raise ValueError."""
        enqueue_fn = AsyncMock()
        scheduler = TaskScheduler(enqueue_fn=enqueue_fn)
        task = Task(tenant_id="t1", url="https://example.com")
        with pytest.raises(ValueError, match="no schedule"):
            await scheduler.add_schedule(task)

    @pytest.mark.asyncio
    async def test_remove_schedule(self) -> None:
        """Removing a schedule should remove it from the scheduler."""
        enqueue_fn = AsyncMock()
        scheduler = TaskScheduler(enqueue_fn=enqueue_fn)
        task = Task(
            tenant_id="t1",
            url="https://example.com",
            schedule="every 10 minutes",
        )
        entry = await scheduler.add_schedule(task)
        removed = await scheduler.remove_schedule(entry.id)
        assert removed is True
        assert entry.id not in scheduler.schedules

    @pytest.mark.asyncio
    async def test_remove_nonexistent_schedule(self) -> None:
        """Removing a non-existent schedule should return False."""
        enqueue_fn = AsyncMock()
        scheduler = TaskScheduler(enqueue_fn=enqueue_fn)
        removed = await scheduler.remove_schedule(uuid4())
        assert removed is False

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self) -> None:
        """Scheduler should start and stop cleanly."""
        enqueue_fn = AsyncMock()
        scheduler = TaskScheduler(enqueue_fn=enqueue_fn, check_interval=0.05)
        await scheduler.start()
        assert scheduler._running is True
        assert scheduler._task is not None
        await scheduler.stop()
        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_interval_fires(self) -> None:
        """An interval schedule should fire and enqueue a cloned task."""
        enqueue_fn = AsyncMock()
        scheduler = TaskScheduler(enqueue_fn=enqueue_fn, check_interval=0.05)

        task = Task(
            tenant_id="t1",
            url="https://example.com",
            schedule="every 1 seconds",
        )
        entry = await scheduler.add_schedule(task)

        # Start scheduler and wait for it to fire
        await scheduler.start()
        await asyncio.sleep(0.2)
        await scheduler.stop()

        assert enqueue_fn.called
        # The enqueued task should be a clone (different ID, no schedule)
        cloned = enqueue_fn.call_args[0][0]
        assert cloned.id != task.id
        assert cloned.schedule is None
        assert str(cloned.url) == str(task.url)

    @pytest.mark.asyncio
    async def test_once_schedule_fires_and_removes(self) -> None:
        """A one-time schedule should fire once and then be removed."""
        enqueue_fn = AsyncMock()
        scheduler = TaskScheduler(enqueue_fn=enqueue_fn, check_interval=0.05)

        # Schedule in the past so it fires immediately
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        task = Task(
            tenant_id="t1",
            url="https://example.com",
            schedule=past,
        )
        entry = await scheduler.add_schedule(task)
        entry_id = entry.id

        await scheduler.start()
        await asyncio.sleep(0.2)
        await scheduler.stop()

        assert enqueue_fn.called
        # One-time schedule should be removed after firing
        assert entry_id not in scheduler.schedules

    @pytest.mark.asyncio
    async def test_fire_clones_with_pending_status(self) -> None:
        """Cloned tasks should have PENDING status."""
        enqueue_fn = AsyncMock()
        scheduler = TaskScheduler(enqueue_fn=enqueue_fn, check_interval=0.05)

        task = Task(
            tenant_id="t1",
            url="https://example.com",
            schedule="every 1 seconds",
            status=TaskStatus.COMPLETED,
        )
        await scheduler.add_schedule(task)

        await scheduler.start()
        await asyncio.sleep(0.2)
        await scheduler.stop()

        assert enqueue_fn.called
        cloned = enqueue_fn.call_args[0][0]
        assert cloned.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_enqueue_failure_does_not_crash_scheduler(self) -> None:
        """If enqueue_fn raises, the scheduler should continue running."""
        enqueue_fn = AsyncMock(side_effect=RuntimeError("enqueue failed"))
        scheduler = TaskScheduler(enqueue_fn=enqueue_fn, check_interval=0.05)

        task = Task(
            tenant_id="t1",
            url="https://example.com",
            schedule="every 1 seconds",
        )
        await scheduler.add_schedule(task)

        await scheduler.start()
        await asyncio.sleep(0.2)
        await scheduler.stop()

        # Scheduler should have tried to enqueue and survived the error
        assert enqueue_fn.called

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self) -> None:
        """Calling start() twice should not create duplicate background tasks."""
        enqueue_fn = AsyncMock()
        scheduler = TaskScheduler(enqueue_fn=enqueue_fn, check_interval=0.05)
        await scheduler.start()
        first_task = scheduler._task
        await scheduler.start()  # Should be a no-op
        assert scheduler._task is first_task
        await scheduler.stop()
