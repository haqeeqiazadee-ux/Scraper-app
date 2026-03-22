"""
Integration tests for storage backends working together:
  metadata store + object storage + cache.

Verifies that tasks stored in the DB can have their results cached
and artifacts stored in the filesystem object store.
"""

from __future__ import annotations

import json
import tempfile
from uuid import uuid4

import pytest

from packages.core.storage.database import Database
from packages.core.storage.repositories import TaskRepository, RunRepository, ResultRepository
from packages.core.storage.filesystem_store import FilesystemObjectStore
from packages.core.storage.memory_cache import InMemoryCache


@pytest.fixture
async def storage_db():
    """In-memory database for storage integration tests."""
    db = Database(url="sqlite+aiosqlite:///:memory:")
    await db.create_tables()
    yield db
    await db.drop_tables()
    await db.close()


@pytest.fixture
def object_store(tmp_path):
    """Temporary filesystem object store."""
    return FilesystemObjectStore(base_path=str(tmp_path / "artifacts"))


@pytest.fixture
def cache():
    """In-memory cache instance."""
    return InMemoryCache()


TENANT = "storage-test-tenant"


@pytest.mark.asyncio
class TestStorageIntegration:
    """Test storage backends working together."""

    async def test_create_task_in_db_and_cache_it(self, storage_db: Database, cache: InMemoryCache):
        """Create a task in the database, then cache its data."""
        async with storage_db.session() as session:
            repo = TaskRepository(session)
            task = await repo.create(
                tenant_id=TENANT,
                id=str(uuid4()),
                url="https://example.com/products",
                task_type="scrape",
                status="pending",
            )
            await session.commit()
            task_id = task.id

        # Cache the task data
        cache_key = f"task:{task_id}"
        await cache.set(cache_key, json.dumps({"id": task_id, "url": task.url, "status": task.status}))

        # Verify cache retrieval
        cached = await cache.get(cache_key)
        assert cached is not None
        cached_data = json.loads(cached)
        assert cached_data["id"] == task_id
        assert cached_data["url"] == "https://example.com/products"

    async def test_store_result_in_object_store_and_cache(
        self, storage_db: Database, object_store: FilesystemObjectStore, cache: InMemoryCache,
    ):
        """Store extraction results as artifacts in object storage and cache a reference."""
        result_data = [
            {"name": "Widget A", "price": "19.99"},
            {"name": "Widget B", "price": "29.99"},
        ]
        result_bytes = json.dumps(result_data).encode()

        # Store in object storage
        artifact_key = f"results/{uuid4()}/data.json"
        stored_key = await object_store.put(artifact_key, result_bytes, content_type="application/json")
        assert stored_key == artifact_key

        # Cache the object store key for quick lookup
        cache_key = f"result-artifact:{uuid4()}"
        await cache.set(cache_key, artifact_key, ttl_seconds=3600)

        # Retrieve via cache -> object store chain
        cached_artifact_key = await cache.get(cache_key)
        assert cached_artifact_key == artifact_key

        retrieved = await object_store.get(cached_artifact_key)
        assert json.loads(retrieved) == result_data

    async def test_task_with_run_and_result_in_db(self, storage_db: Database):
        """Create a full task -> run -> result chain in the database."""
        task_id = str(uuid4())
        run_id = str(uuid4())
        result_id = str(uuid4())

        async with storage_db.session() as session:
            # Create task
            task_repo = TaskRepository(session)
            task = await task_repo.create(
                tenant_id=TENANT, id=task_id,
                url="https://shop.com/items", task_type="scrape", status="pending",
            )

            # Create run
            run_repo = RunRepository(session)
            run = await run_repo.create(
                tenant_id=TENANT, id=run_id, task_id=task_id,
                lane="http", connector="http_collector", status="running",
            )

            # Create result
            result_repo = ResultRepository(session)
            result = await result_repo.create(
                tenant_id=TENANT, id=result_id, task_id=task_id, run_id=run_id,
                url="https://shop.com/items",
                extracted_data=[{"name": "Item", "price": "9.99"}],
                item_count=1, confidence=0.9,
            )
            await session.commit()

        # Verify retrieval
        async with storage_db.session() as session:
            result_repo = ResultRepository(session)
            results = await result_repo.list_by_task(task_id, TENANT)
            assert len(results) == 1
            assert results[0].item_count == 1
            assert results[0].confidence == 0.9

    async def test_object_store_list_and_delete(self, object_store: FilesystemObjectStore):
        """Store multiple artifacts, list them, delete one, verify."""
        await object_store.put("tenant1/artifact1.json", b'{"a":1}')
        await object_store.put("tenant1/artifact2.json", b'{"b":2}')
        await object_store.put("tenant2/artifact3.json", b'{"c":3}')

        # List all under tenant1
        keys = await object_store.list_keys("tenant1")
        assert len(keys) == 2
        assert "tenant1/artifact1.json" in keys

        # Delete one
        await object_store.delete("tenant1/artifact1.json")
        keys = await object_store.list_keys("tenant1")
        assert len(keys) == 1
        assert "tenant1/artifact2.json" in keys

    async def test_cache_ttl_and_expiration(self, cache: InMemoryCache):
        """Cache entries with TTL should expire and return None."""
        import time

        # Set with very short TTL — need time to pass for float comparison
        await cache.set("ephemeral", "value", ttl_seconds=1)

        # Not yet expired — should still be available
        result = await cache.get("ephemeral")
        assert result == "value"

        # Manually expire by manipulating internal store
        key = "ephemeral"
        val, _ = cache._store[key]
        cache._store[key] = (val, time.time() - 1)  # Set to already-expired

        result = await cache.get("ephemeral")
        assert result is None

        # Non-expiring entry persists
        await cache.set("permanent", "data")
        assert await cache.get("permanent") == "data"

    async def test_cache_increment_counter(self, cache: InMemoryCache):
        """Cache increment should work for request counting."""
        count = await cache.increment("request_count")
        assert count == 1
        count = await cache.increment("request_count")
        assert count == 2
        count = await cache.increment("request_count", amount=5)
        assert count == 7
