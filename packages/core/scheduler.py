"""
Task Scheduler — manages periodic/scheduled task execution.

Supports:
- Cron expressions (standard 5-field: minute hour day month weekday)
- Interval schedules (every N minutes/hours)
- One-time schedules (at a specific datetime)

Uses asyncio background tasks to check schedules periodically and
enqueue cloned tasks when their schedule fires.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Awaitable, Optional
from uuid import UUID, uuid4

from packages.contracts.task import Task, TaskStatus

logger = logging.getLogger(__name__)

# Check interval for the scheduler loop (seconds)
DEFAULT_CHECK_INTERVAL = 15.0


@dataclass
class ScheduleEntry:
    """A registered schedule."""

    id: UUID
    task: Task
    schedule_type: str  # "cron", "interval", "once"
    cron_fields: Optional[list[set[int]]] = None  # [minutes, hours, days, months, weekdays]
    interval_seconds: Optional[float] = None
    once_at: Optional[datetime] = None
    last_fired: Optional[datetime] = None
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def parse_cron(expression: str) -> list[set[int]]:
    """Parse a standard 5-field cron expression into sets of valid values.

    Fields: minute(0-59) hour(0-23) day(1-31) month(1-12) weekday(0-6, 0=Sun)

    Supports: *, specific values, ranges (1-5), steps (*/5), lists (1,3,5).
    """
    fields = expression.strip().split()
    if len(fields) != 5:
        raise ValueError(f"Cron expression must have 5 fields, got {len(fields)}: '{expression}'")

    ranges = [
        (0, 59),   # minute
        (0, 23),   # hour
        (1, 31),   # day of month
        (1, 12),   # month
        (0, 6),    # day of week (0 = Sunday)
    ]

    result: list[set[int]] = []
    for i, (field_str, (low, high)) in enumerate(zip(fields, ranges)):
        values: set[int] = set()
        for part in field_str.split(","):
            part = part.strip()
            if part == "*":
                values.update(range(low, high + 1))
            elif "/" in part:
                # Step: */5 or 1-30/5
                base, step_str = part.split("/", 1)
                step = int(step_str)
                if base == "*":
                    start = low
                    end = high
                elif "-" in base:
                    start, end = (int(x) for x in base.split("-", 1))
                else:
                    start = int(base)
                    end = high
                values.update(range(start, end + 1, step))
            elif "-" in part:
                start, end = (int(x) for x in part.split("-", 1))
                values.update(range(start, end + 1))
            else:
                values.add(int(part))
        result.append(values)

    return result


def cron_matches(cron_fields: list[set[int]], dt: datetime) -> bool:
    """Check if a datetime matches a parsed cron expression."""
    minute = dt.minute
    hour = dt.hour
    day = dt.day
    month = dt.month
    weekday = (dt.weekday() + 1) % 7  # Python: 0=Mon -> cron: 0=Sun

    return (
        minute in cron_fields[0]
        and hour in cron_fields[1]
        and day in cron_fields[2]
        and month in cron_fields[3]
        and weekday in cron_fields[4]
    )


_INTERVAL_PATTERN = re.compile(
    r"^every\s+(\d+)\s*(minutes?|hours?|seconds?)$",
    re.IGNORECASE,
)


def parse_schedule(schedule_str: str) -> ScheduleEntry:
    """Parse a schedule string into a ScheduleEntry (without task/id).

    Formats:
      - Cron: "0 */2 * * *" (5-field cron)
      - Interval: "every 30 minutes", "every 2 hours"
      - One-time: ISO-8601 datetime "2024-06-15T10:30:00Z"

    Returns a partial ScheduleEntry (task and id must be set by caller).
    """
    schedule_str = schedule_str.strip()

    # Try interval pattern first
    interval_match = _INTERVAL_PATTERN.match(schedule_str)
    if interval_match:
        amount = int(interval_match.group(1))
        unit = interval_match.group(2).lower().rstrip("s")
        multipliers = {"minute": 60, "hour": 3600, "second": 1}
        seconds = amount * multipliers[unit]
        return ScheduleEntry(
            id=uuid4(),
            task=Task(tenant_id="", url="https://placeholder.invalid"),
            schedule_type="interval",
            interval_seconds=float(seconds),
        )

    # Try ISO-8601 datetime (one-time)
    try:
        dt = datetime.fromisoformat(schedule_str.replace("Z", "+00:00"))
        return ScheduleEntry(
            id=uuid4(),
            task=Task(tenant_id="", url="https://placeholder.invalid"),
            schedule_type="once",
            once_at=dt,
        )
    except ValueError:
        pass

    # Try cron expression
    try:
        cron_fields = parse_cron(schedule_str)
        return ScheduleEntry(
            id=uuid4(),
            task=Task(tenant_id="", url="https://placeholder.invalid"),
            schedule_type="cron",
            cron_fields=cron_fields,
        )
    except ValueError:
        pass

    raise ValueError(f"Cannot parse schedule: '{schedule_str}'")


# Type alias for task enqueue callback
EnqueueCallback = Callable[[Task], Awaitable[None]]


class TaskScheduler:
    """Manages scheduled tasks, checking periodically and enqueuing when due.

    Usage:
        scheduler = TaskScheduler(enqueue_fn=my_enqueue)
        await scheduler.add_schedule(task)
        await scheduler.start()
        # ...
        await scheduler.stop()
    """

    def __init__(
        self,
        enqueue_fn: EnqueueCallback,
        check_interval: float = DEFAULT_CHECK_INTERVAL,
    ) -> None:
        self._enqueue_fn = enqueue_fn
        self._check_interval = check_interval
        self._schedules: dict[UUID, ScheduleEntry] = {}
        self._task: Optional[asyncio.Task] = None
        self._running = False

    @property
    def schedules(self) -> dict[UUID, ScheduleEntry]:
        """Return a copy of active schedules."""
        return dict(self._schedules)

    async def add_schedule(self, task: Task) -> ScheduleEntry:
        """Register a task's schedule. Parses the task.schedule field.

        Args:
            task: Task with a non-empty schedule field.

        Returns:
            The created ScheduleEntry.

        Raises:
            ValueError: If task.schedule is empty or unparsable.
        """
        if not task.schedule:
            raise ValueError("Task has no schedule defined")

        entry = parse_schedule(task.schedule)
        entry.task = task
        entry.id = uuid4()
        self._schedules[entry.id] = entry

        logger.info(
            "Schedule added",
            extra={
                "schedule_id": str(entry.id),
                "task_id": str(task.id),
                "schedule_type": entry.schedule_type,
                "schedule": task.schedule,
            },
        )
        return entry

    async def remove_schedule(self, schedule_id: UUID) -> bool:
        """Remove a schedule by ID. Returns True if found and removed."""
        entry = self._schedules.pop(schedule_id, None)
        if entry is None:
            logger.warning("Schedule not found for removal", extra={"schedule_id": str(schedule_id)})
            return False
        logger.info(
            "Schedule removed",
            extra={
                "schedule_id": str(schedule_id),
                "task_id": str(entry.task.id),
            },
        )
        return True

    async def start(self) -> None:
        """Start the scheduler background loop."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started", extra={"check_interval": self._check_interval})

    async def stop(self) -> None:
        """Stop the scheduler background loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop — checks and fires due schedules."""
        while self._running:
            try:
                await self._check_schedules()
            except Exception:
                logger.exception("Error in scheduler loop")
            await asyncio.sleep(self._check_interval)

    async def _check_schedules(self) -> None:
        """Check all schedules and fire those that are due."""
        now = datetime.now(timezone.utc)
        to_remove: list[UUID] = []

        for schedule_id, entry in list(self._schedules.items()):
            if not entry.active:
                continue

            should_fire = False

            if entry.schedule_type == "cron" and entry.cron_fields is not None:
                if cron_matches(entry.cron_fields, now):
                    # Only fire once per minute window
                    if entry.last_fired is None or (
                        now - entry.last_fired
                    ).total_seconds() >= 60:
                        should_fire = True

            elif entry.schedule_type == "interval" and entry.interval_seconds is not None:
                if entry.last_fired is None:
                    should_fire = True
                elif (now - entry.last_fired).total_seconds() >= entry.interval_seconds:
                    should_fire = True

            elif entry.schedule_type == "once" and entry.once_at is not None:
                if now >= entry.once_at and entry.last_fired is None:
                    should_fire = True
                    to_remove.append(schedule_id)

            if should_fire:
                await self._fire_schedule(entry)
                entry.last_fired = now

        # Remove one-time schedules that have fired
        for sid in to_remove:
            self._schedules.pop(sid, None)

    async def _fire_schedule(self, entry: ScheduleEntry) -> None:
        """Clone the task and enqueue it."""
        cloned = entry.task.model_copy(
            update={
                "id": uuid4(),
                "status": TaskStatus.PENDING,
                "schedule": None,  # Cloned task is a one-off execution
                "created_at": datetime.now(timezone.utc),
                "updated_at": None,
            }
        )
        logger.info(
            "Schedule fired — enqueuing cloned task",
            extra={
                "schedule_id": str(entry.id),
                "original_task_id": str(entry.task.id),
                "cloned_task_id": str(cloned.id),
            },
        )
        try:
            await self._enqueue_fn(cloned)
        except Exception:
            logger.exception(
                "Failed to enqueue scheduled task",
                extra={
                    "schedule_id": str(entry.id),
                    "task_id": str(entry.task.id),
                },
            )
