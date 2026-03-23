"""Tests for Task contract schema validation."""

import pytest
from uuid import uuid4
from datetime import datetime

from packages.contracts.task import Task, TaskCreate, TaskUpdate, TaskStatus, TaskType


class TestTaskCreate:
    """Tests for TaskCreate validation."""

    def test_valid_task_create_minimal(self):
        """Minimal valid task creation with just URL."""
        task = TaskCreate(url="https://example.com/products")
        assert str(task.url) == "https://example.com/products"
        assert task.task_type == TaskType.SCRAPE
        assert task.priority == 5
        assert task.policy_id is None
        assert task.schedule is None
        assert task.callback_url is None
        assert task.metadata == {}

    def test_valid_task_create_full(self):
        """Full task creation with all fields."""
        policy_id = str(uuid4())
        task = TaskCreate(
            url="https://shop.com/items",
            task_type=TaskType.MONITOR,
            policy_id=policy_id,
            priority=10,
            schedule="0 9 * * *",
            callback_url="https://webhook.example.com/callback",
            metadata={"source": "dashboard", "tags": ["electronics"]},
        )
        assert task.task_type == TaskType.MONITOR
        assert task.policy_id == policy_id
        assert task.priority == 10
        assert task.schedule == "0 9 * * *"
        assert task.metadata["source"] == "dashboard"

    def test_invalid_url_rejected(self):
        """Invalid URLs should be rejected."""
        with pytest.raises(Exception):
            TaskCreate(url="not-a-url")

    def test_priority_bounds(self):
        """Priority must be between 0 and 10."""
        task_min = TaskCreate(url="https://example.com", priority=0)
        assert task_min.priority == 0

        task_max = TaskCreate(url="https://example.com", priority=10)
        assert task_max.priority == 10

        with pytest.raises(Exception):
            TaskCreate(url="https://example.com", priority=-1)

        with pytest.raises(Exception):
            TaskCreate(url="https://example.com", priority=11)

    def test_task_type_enum(self):
        """All task types should be valid."""
        for task_type in TaskType:
            task = TaskCreate(url="https://example.com", task_type=task_type)
            assert task.task_type == task_type


class TestTask:
    """Tests for full Task model."""

    def test_task_defaults(self):
        """Task should have sensible defaults."""
        task = Task(tenant_id="t1", url="https://example.com")
        assert task.id is not None
        assert task.tenant_id == "t1"
        assert task.status == TaskStatus.PENDING
        assert task.task_type == TaskType.SCRAPE
        assert task.priority == 5
        assert isinstance(task.created_at, datetime)

    def test_task_serialization_roundtrip(self):
        """Task should serialize to dict and back."""
        task = Task(
            tenant_id="t1",
            url="https://example.com/products",
            task_type=TaskType.EXTRACT,
            priority=8,
            metadata={"key": "value"},
        )
        data = task.model_dump()
        restored = Task(**data)
        assert restored.tenant_id == task.tenant_id
        assert str(restored.url) == str(task.url)
        assert restored.task_type == task.task_type
        assert restored.priority == task.priority
        assert restored.metadata == task.metadata

    def test_task_json_roundtrip(self):
        """Task should serialize to JSON and back."""
        task = Task(tenant_id="t1", url="https://example.com")
        json_str = task.model_dump_json()
        restored = Task.model_validate_json(json_str)
        assert restored.id == task.id
        assert restored.tenant_id == task.tenant_id

    def test_task_status_values(self):
        """All status values should be valid."""
        for status in TaskStatus:
            task = Task(tenant_id="t1", url="https://example.com", status=status)
            assert task.status == status


class TestTaskUpdate:
    """Tests for TaskUpdate partial updates."""

    def test_empty_update(self):
        """Empty update should have all None fields."""
        update = TaskUpdate()
        data = update.model_dump(exclude_unset=True)
        assert data == {}

    def test_partial_update(self):
        """Should allow updating only specific fields."""
        update = TaskUpdate(status=TaskStatus.RUNNING, priority=9)
        data = update.model_dump(exclude_unset=True)
        assert data["status"] == TaskStatus.RUNNING
        assert data["priority"] == 9
        assert "schedule" not in data

    def test_update_priority_bounds(self):
        """Update priority must respect bounds."""
        with pytest.raises(Exception):
            TaskUpdate(priority=15)
