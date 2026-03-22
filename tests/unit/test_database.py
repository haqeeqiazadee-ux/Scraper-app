"""Tests for SQLAlchemy database layer (using SQLite in-memory)."""

import pytest
from uuid import uuid4

from packages.core.storage.database import Database
from packages.core.storage.repositories import TaskRepository, PolicyRepository, RunRepository, ResultRepository


@pytest.fixture
async def db():
    """Create an in-memory SQLite database for testing."""
    database = Database(url="sqlite+aiosqlite:///:memory:")
    await database.create_tables()
    yield database
    await database.drop_tables()
    await database.close()


@pytest.fixture
async def task_repo(db):
    async with db.session() as session:
        yield TaskRepository(session)
        await session.commit()


# =============================================================================
# Database + Table Creation Tests
# =============================================================================

class TestDatabase:

    @pytest.mark.asyncio
    async def test_create_tables(self):
        db = Database(url="sqlite+aiosqlite:///:memory:")
        await db.create_tables()
        # Should not raise
        await db.close()

    @pytest.mark.asyncio
    async def test_session_creation(self):
        db = Database(url="sqlite+aiosqlite:///:memory:")
        await db.create_tables()
        async with db.session() as session:
            assert session is not None
        await db.close()


# =============================================================================
# Task Repository Tests
# =============================================================================

class TestTaskRepository:

    @pytest.mark.asyncio
    async def test_create_task(self, db):
        async with db.session() as session:
            repo = TaskRepository(session)
            task = await repo.create(
                tenant_id="t1",
                url="https://example.com/products",
                task_type="scrape",
                priority=5,
            )
            await session.commit()
            assert task.id is not None
            assert task.tenant_id == "t1"
            assert task.url == "https://example.com/products"
            assert task.status == "pending"

    @pytest.mark.asyncio
    async def test_get_task(self, db):
        async with db.session() as session:
            repo = TaskRepository(session)
            task = await repo.create(tenant_id="t1", url="https://example.com")
            await session.commit()

            found = await repo.get(task.id, "t1")
            assert found is not None
            assert found.id == task.id

    @pytest.mark.asyncio
    async def test_get_task_wrong_tenant(self, db):
        async with db.session() as session:
            repo = TaskRepository(session)
            task = await repo.create(tenant_id="t1", url="https://example.com")
            await session.commit()

            found = await repo.get(task.id, "t2")  # Wrong tenant
            assert found is None

    @pytest.mark.asyncio
    async def test_list_tasks(self, db):
        async with db.session() as session:
            repo = TaskRepository(session)
            await repo.create(tenant_id="t1", url="https://a.com")
            await repo.create(tenant_id="t1", url="https://b.com")
            await repo.create(tenant_id="t2", url="https://c.com")  # Different tenant
            await session.commit()

            tasks, total = await repo.list("t1")
            assert len(tasks) == 2
            assert total == 2

    @pytest.mark.asyncio
    async def test_list_tasks_filter_status(self, db):
        async with db.session() as session:
            repo = TaskRepository(session)
            await repo.create(tenant_id="t1", url="https://a.com", status="pending")
            await repo.create(tenant_id="t1", url="https://b.com", status="completed")
            await session.commit()

            tasks, total = await repo.list("t1", status="completed")
            assert len(tasks) == 1
            assert total == 1

    @pytest.mark.asyncio
    async def test_update_task(self, db):
        async with db.session() as session:
            repo = TaskRepository(session)
            task = await repo.create(tenant_id="t1", url="https://example.com")
            await session.commit()

            updated = await repo.update(task.id, "t1", status="running", priority=10)
            await session.commit()
            assert updated is not None
            assert updated.status == "running"
            assert updated.priority == 10

    @pytest.mark.asyncio
    async def test_delete_task(self, db):
        async with db.session() as session:
            repo = TaskRepository(session)
            task = await repo.create(tenant_id="t1", url="https://example.com")
            await session.commit()

            deleted = await repo.delete(task.id, "t1")
            await session.commit()
            assert deleted is True

            found = await repo.get(task.id, "t1")
            assert found is None


# =============================================================================
# Policy Repository Tests
# =============================================================================

class TestPolicyRepository:

    @pytest.mark.asyncio
    async def test_create_policy(self, db):
        async with db.session() as session:
            repo = PolicyRepository(session)
            policy = await repo.create(
                tenant_id="t1",
                name="Test Policy",
                target_domains=["example.com"],
                preferred_lane="http",
                timeout_ms=30000,
            )
            await session.commit()
            assert policy.id is not None
            assert policy.name == "Test Policy"

    @pytest.mark.asyncio
    async def test_get_policy(self, db):
        async with db.session() as session:
            repo = PolicyRepository(session)
            policy = await repo.create(tenant_id="t1", name="Test")
            await session.commit()

            found = await repo.get(policy.id, "t1")
            assert found is not None

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, db):
        async with db.session() as session:
            repo = PolicyRepository(session)
            policy = await repo.create(tenant_id="t1", name="Private")
            await session.commit()

            found = await repo.get(policy.id, "t2")
            assert found is None

    @pytest.mark.asyncio
    async def test_list_policies(self, db):
        async with db.session() as session:
            repo = PolicyRepository(session)
            await repo.create(tenant_id="t1", name="P1")
            await repo.create(tenant_id="t1", name="P2")
            await session.commit()

            policies, total = await repo.list("t1")
            assert len(policies) == 2
            assert total == 2

    @pytest.mark.asyncio
    async def test_delete_policy(self, db):
        async with db.session() as session:
            repo = PolicyRepository(session)
            policy = await repo.create(tenant_id="t1", name="ToDelete")
            await session.commit()

            deleted = await repo.delete(policy.id, "t1")
            await session.commit()
            assert deleted is True
