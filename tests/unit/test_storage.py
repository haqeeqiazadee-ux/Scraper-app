"""Tests for storage backends (filesystem, in-memory queue, in-memory cache)."""

import asyncio
import pytest
import tempfile
import time
from pathlib import Path

from packages.core.storage.filesystem_store import FilesystemObjectStore
from packages.core.storage.memory_queue import InMemoryQueue
from packages.core.storage.memory_cache import InMemoryCache


# =============================================================================
# Filesystem Object Store Tests
# =============================================================================

class TestFilesystemObjectStore:

    @pytest.fixture
    def store(self, tmp_path):
        return FilesystemObjectStore(base_path=str(tmp_path / "artifacts"))

    @pytest.mark.asyncio
    async def test_put_and_get(self, store):
        data = b"Hello, World!"
        await store.put("test/file.txt", data, "text/plain")
        result = await store.get("test/file.txt")
        assert result == data

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        with pytest.raises(FileNotFoundError):
            await store.get("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_delete(self, store):
        await store.put("to_delete.txt", b"data")
        await store.delete("to_delete.txt")
        with pytest.raises(FileNotFoundError):
            await store.get("to_delete.txt")

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, store):
        # Should not raise
        await store.delete("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_list_keys(self, store):
        await store.put("a/file1.txt", b"1")
        await store.put("a/file2.txt", b"2")
        await store.put("b/file3.txt", b"3")

        all_keys = await store.list_keys()
        assert len(all_keys) == 3

        a_keys = await store.list_keys("a")
        assert len(a_keys) == 2
        assert all(k.startswith("a/") for k in a_keys)

    @pytest.mark.asyncio
    async def test_list_keys_empty(self, store):
        keys = await store.list_keys()
        assert keys == []

    @pytest.mark.asyncio
    async def test_presigned_url(self, store):
        await store.put("test.txt", b"data")
        url = await store.get_presigned_url("test.txt")
        assert url.startswith("file://")

    @pytest.mark.asyncio
    async def test_checksum(self, store):
        data = b"test data for checksum"
        await store.put("checksum.txt", data)
        checksum = await store.get_checksum("checksum.txt")
        assert checksum.startswith("sha256:")
        assert len(checksum) > 10

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, store):
        with pytest.raises(ValueError, match="path traversal"):
            await store.put("../../etc/passwd", b"evil")

    @pytest.mark.asyncio
    async def test_nested_directories(self, store):
        await store.put("deep/nested/dir/file.txt", b"deep data")
        result = await store.get("deep/nested/dir/file.txt")
        assert result == b"deep data"

    @pytest.mark.asyncio
    async def test_overwrite(self, store):
        await store.put("file.txt", b"original")
        await store.put("file.txt", b"updated")
        result = await store.get("file.txt")
        assert result == b"updated"


# =============================================================================
# In-Memory Queue Tests
# =============================================================================

class TestInMemoryQueue:

    @pytest.fixture
    def queue(self):
        return InMemoryQueue()

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self, queue):
        msg_id = await queue.enqueue("tasks", {"url": "https://example.com"})
        assert msg_id is not None

        msg = await queue.dequeue("tasks")
        assert msg is not None
        assert msg["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_dequeue_empty(self, queue):
        msg = await queue.dequeue("tasks")
        assert msg is None

    @pytest.mark.asyncio
    async def test_fifo_order(self, queue):
        await queue.enqueue("tasks", {"order": 1})
        await queue.enqueue("tasks", {"order": 2})
        await queue.enqueue("tasks", {"order": 3})

        msg1 = await queue.dequeue("tasks")
        msg2 = await queue.dequeue("tasks")
        msg3 = await queue.dequeue("tasks")

        assert msg1["order"] == 1
        assert msg2["order"] == 2
        assert msg3["order"] == 3

    @pytest.mark.asyncio
    async def test_queue_size(self, queue):
        assert await queue.queue_size("tasks") == 0
        await queue.enqueue("tasks", {"a": 1})
        await queue.enqueue("tasks", {"b": 2})
        assert await queue.queue_size("tasks") == 2

    @pytest.mark.asyncio
    async def test_ack(self, queue):
        await queue.enqueue("tasks", {"data": "test"})
        msg = await queue.dequeue("tasks")
        msg_id = msg["_msg_id"]
        await queue.ack("tasks", msg_id)
        # Should not raise

    @pytest.mark.asyncio
    async def test_nack_requeues(self, queue):
        await queue.enqueue("tasks", {"data": "retry"})
        msg = await queue.dequeue("tasks")
        msg_id = msg["_msg_id"]
        await queue.nack("tasks", msg_id)

        # Message should be back in queue
        msg2 = await queue.dequeue("tasks")
        assert msg2 is not None

    @pytest.mark.asyncio
    async def test_separate_queues(self, queue):
        await queue.enqueue("queue_a", {"from": "a"})
        await queue.enqueue("queue_b", {"from": "b"})

        msg_a = await queue.dequeue("queue_a")
        msg_b = await queue.dequeue("queue_b")

        assert msg_a["from"] == "a"
        assert msg_b["from"] == "b"

    @pytest.mark.asyncio
    async def test_dequeue_timeout(self, queue):
        msg = await queue.dequeue("tasks", timeout_seconds=1)
        assert msg is None


# =============================================================================
# In-Memory Cache Tests
# =============================================================================

class TestInMemoryCache:

    @pytest.fixture
    def cache(self):
        return InMemoryCache()

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache):
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        await cache.set("key", "val")
        await cache.delete("key")
        assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_exists(self, cache):
        assert await cache.exists("key") is False
        await cache.set("key", "val")
        assert await cache.exists("key") is True

    @pytest.mark.asyncio
    async def test_increment_new_key(self, cache):
        result = await cache.increment("counter")
        assert result == 1

    @pytest.mark.asyncio
    async def test_increment_existing(self, cache):
        await cache.set("counter", "5")
        result = await cache.increment("counter", 3)
        assert result == 8

    @pytest.mark.asyncio
    async def test_ttl_expiry(self, cache):
        await cache.set("expiring", "value", ttl_seconds=1)
        assert await cache.get("expiring") == "value"
        time.sleep(1.1)
        assert await cache.get("expiring") is None

    @pytest.mark.asyncio
    async def test_no_ttl_persists(self, cache):
        await cache.set("persistent", "value")
        assert await cache.get("persistent") == "value"

    @pytest.mark.asyncio
    async def test_overwrite(self, cache):
        await cache.set("key", "old")
        await cache.set("key", "new")
        assert await cache.get("key") == "new"

    @pytest.mark.asyncio
    async def test_size(self, cache):
        assert cache.size == 0
        await cache.set("a", "1")
        await cache.set("b", "2")
        assert cache.size == 2
        await cache.delete("a")
        assert cache.size == 1
