"""Tests for Redis queue and cache backends (mocked Redis)."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from packages.core.storage.redis_queue import (
    RedisQueue,
    PENDING_PREFIX,
    RETRY_PREFIX,
    DLQ_SUFFIX,
)
from packages.core.storage.redis_cache import RedisCache
from packages.core.queue_factory import create_queue, create_cache


# =============================================================================
# Helpers
# =============================================================================


def _make_mock_redis() -> AsyncMock:
    """Create a mock async Redis client with commonly used methods."""
    client = AsyncMock()
    client.lpush = AsyncMock()
    client.rpop = AsyncMock(return_value=None)
    client.brpop = AsyncMock(return_value=None)
    client.llen = AsyncMock(return_value=0)
    client.lrange = AsyncMock(return_value=[])
    client.hset = AsyncMock()
    client.hget = AsyncMock(return_value=None)
    client.hdel = AsyncMock()
    client.hlen = AsyncMock(return_value=0)
    client.incr = AsyncMock(return_value=1)
    client.delete = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    client.setex = AsyncMock()
    client.exists = AsyncMock(return_value=0)
    client.scan = AsyncMock(return_value=("0", []))
    client.aclose = AsyncMock()
    return client


# =============================================================================
# RedisQueue Tests
# =============================================================================


class TestRedisQueue:

    @pytest.fixture
    def mock_client(self):
        return _make_mock_redis()

    @pytest.fixture
    def queue(self, mock_client):
        q = RedisQueue(redis_url="redis://test:6379/0")
        q._client = mock_client
        return q

    @pytest.mark.asyncio
    async def test_enqueue_calls_lpush(self, queue, mock_client):
        msg_id = await queue.enqueue("tasks", {"url": "https://example.com"})
        assert msg_id is not None
        mock_client.lpush.assert_called_once()
        call_args = mock_client.lpush.call_args
        assert call_args[0][0] == "tasks"
        # Verify the payload is valid JSON with expected structure
        payload = json.loads(call_args[0][1])
        assert payload["_id"] == msg_id
        assert payload["_payload"]["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_dequeue_non_blocking_rpop(self, queue, mock_client):
        msg = {"url": "https://example.com"}
        wrapped = json.dumps({"_id": "test-id", "_payload": msg})
        mock_client.rpop = AsyncMock(return_value=wrapped)

        result = await queue.dequeue("tasks")
        assert result is not None
        assert result["url"] == "https://example.com"
        assert result["_msg_id"] == "test-id"
        mock_client.rpop.assert_called_once_with("tasks")

    @pytest.mark.asyncio
    async def test_dequeue_blocking_brpop(self, queue, mock_client):
        msg = {"url": "https://example.com"}
        wrapped = json.dumps({"_id": "test-id", "_payload": msg})
        mock_client.brpop = AsyncMock(return_value=("tasks", wrapped))

        result = await queue.dequeue("tasks", timeout_seconds=5)
        assert result is not None
        assert result["url"] == "https://example.com"
        mock_client.brpop.assert_called_once_with("tasks", timeout=5)

    @pytest.mark.asyncio
    async def test_dequeue_empty_returns_none(self, queue, mock_client):
        mock_client.rpop = AsyncMock(return_value=None)
        result = await queue.dequeue("tasks")
        assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_blocking_timeout_returns_none(self, queue, mock_client):
        mock_client.brpop = AsyncMock(return_value=None)
        result = await queue.dequeue("tasks", timeout_seconds=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_tracks_pending(self, queue, mock_client):
        wrapped = json.dumps({"_id": "msg-1", "_payload": {"data": "test"}})
        mock_client.rpop = AsyncMock(return_value=wrapped)

        await queue.dequeue("tasks")

        pending_key = f"{PENDING_PREFIX}tasks"
        mock_client.hset.assert_called_once_with(
            pending_key, "msg-1", json.dumps({"data": "test"})
        )

    @pytest.mark.asyncio
    async def test_ack_removes_from_pending(self, queue, mock_client):
        await queue.ack("tasks", "msg-1")

        pending_key = f"{PENDING_PREFIX}tasks"
        retry_key = f"{RETRY_PREFIX}tasks:msg-1"
        mock_client.hdel.assert_called_once_with(pending_key, "msg-1")
        mock_client.delete.assert_called_once_with(retry_key)

    @pytest.mark.asyncio
    async def test_nack_requeues_within_max_retries(self, queue, mock_client):
        payload = {"data": "retry-me"}
        mock_client.hget = AsyncMock(return_value=json.dumps(payload))
        mock_client.incr = AsyncMock(return_value=1)  # first retry

        await queue.nack("tasks", "msg-1")

        # Should hdel the pending entry
        pending_key = f"{PENDING_PREFIX}tasks"
        mock_client.hdel.assert_called_once_with(pending_key, "msg-1")
        # Should re-enqueue via lpush (enqueue is called internally)
        assert mock_client.lpush.call_count == 1

    @pytest.mark.asyncio
    async def test_nack_moves_to_dlq_after_max_retries(self, queue, mock_client):
        payload = {"data": "dead-letter"}
        mock_client.hget = AsyncMock(return_value=json.dumps(payload))
        mock_client.incr = AsyncMock(return_value=3)  # max retries reached

        await queue.nack("tasks", "msg-1")

        # Should push to DLQ
        dlq_name = f"tasks{DLQ_SUFFIX}"
        dlq_call = mock_client.lpush.call_args
        assert dlq_call[0][0] == dlq_name
        dlq_payload = json.loads(dlq_call[0][1])
        assert dlq_payload["_id"] == "msg-1"
        assert dlq_payload["_retries"] == 3

    @pytest.mark.asyncio
    async def test_nack_unknown_message_does_not_raise(self, queue, mock_client):
        mock_client.hget = AsyncMock(return_value=None)
        # Should not raise
        await queue.nack("tasks", "nonexistent")

    @pytest.mark.asyncio
    async def test_queue_size(self, queue, mock_client):
        mock_client.llen = AsyncMock(return_value=42)
        size = await queue.queue_size("tasks")
        assert size == 42
        mock_client.llen.assert_called_once_with("tasks")

    @pytest.mark.asyncio
    async def test_peek_returns_messages(self, queue, mock_client):
        items = [
            json.dumps({"_id": "1", "_payload": {"url": "a"}}),
            json.dumps({"_id": "2", "_payload": {"url": "b"}}),
        ]
        mock_client.lrange = AsyncMock(return_value=items)

        result = await queue.peek("tasks", count=2)
        assert len(result) == 2
        # Peek reverses to show dequeue order
        assert result[0]["url"] == "b"
        assert result[1]["url"] == "a"

    @pytest.mark.asyncio
    async def test_dlq_size(self, queue, mock_client):
        mock_client.llen = AsyncMock(return_value=5)
        size = await queue.dlq_size("tasks")
        assert size == 5
        mock_client.llen.assert_called_once_with(f"tasks{DLQ_SUFFIX}")

    @pytest.mark.asyncio
    async def test_pending_count(self, queue, mock_client):
        mock_client.hlen = AsyncMock(return_value=3)
        count = await queue.pending_count("tasks")
        assert count == 3
        mock_client.hlen.assert_called_once_with(f"{PENDING_PREFIX}tasks")

    @pytest.mark.asyncio
    async def test_close(self, queue, mock_client):
        await queue.close()
        mock_client.aclose.assert_called_once()
        assert queue._client is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self):
        q = RedisQueue()
        # Should not raise
        await q.close()

    @pytest.mark.asyncio
    async def test_lazy_client_initialization(self):
        q = RedisQueue(redis_url="redis://test:6379/0")
        assert q._client is None

        # Mock the redis.asyncio module at import time inside _get_client
        mock_aioredis = MagicMock()
        mock_client = _make_mock_redis()
        mock_aioredis.from_url.return_value = mock_client
        mock_redis = MagicMock()
        mock_redis.asyncio = mock_aioredis

        with patch.dict("sys.modules", {"redis": mock_redis, "redis.asyncio": mock_aioredis}):
            client = await q._get_client()
            assert client is mock_client
            mock_aioredis.from_url.assert_called_once_with(
                "redis://test:6379/0", decode_responses=True
            )


# =============================================================================
# RedisCache Tests
# =============================================================================


class TestRedisCache:

    @pytest.fixture
    def mock_client(self):
        return _make_mock_redis()

    @pytest.fixture
    def cache(self, mock_client):
        c = RedisCache(redis_url="redis://test:6379/0", key_prefix="test:")
        c._client = mock_client
        return c

    @pytest.mark.asyncio
    async def test_set_without_ttl(self, cache, mock_client):
        await cache.set("key1", "value1")
        mock_client.set.assert_called_once_with("test:key1", json.dumps("value1"))

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache, mock_client):
        await cache.set("key1", "value1", ttl_seconds=60)
        mock_client.setex.assert_called_once_with(
            "test:key1", 60, json.dumps("value1")
        )

    @pytest.mark.asyncio
    async def test_get_existing_key(self, cache, mock_client):
        mock_client.get = AsyncMock(return_value=json.dumps("hello"))
        result = await cache.get("key1")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache, mock_client):
        mock_client.get = AsyncMock(return_value=None)
        result = await cache.get("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache, mock_client):
        await cache.delete("key1")
        mock_client.delete.assert_called_once_with("test:key1")

    @pytest.mark.asyncio
    async def test_exists_true(self, cache, mock_client):
        mock_client.exists = AsyncMock(return_value=1)
        assert await cache.exists("key1") is True

    @pytest.mark.asyncio
    async def test_exists_false(self, cache, mock_client):
        mock_client.exists = AsyncMock(return_value=0)
        assert await cache.exists("key1") is False

    @pytest.mark.asyncio
    async def test_increment_new_key(self, cache, mock_client):
        mock_client.get = AsyncMock(return_value=None)
        result = await cache.increment("counter", 1)
        assert result == 1

    @pytest.mark.asyncio
    async def test_increment_existing_key(self, cache, mock_client):
        mock_client.get = AsyncMock(return_value=json.dumps("5"))
        result = await cache.increment("counter", 3)
        assert result == 8

    @pytest.mark.asyncio
    async def test_close(self, cache, mock_client):
        await cache.close()
        mock_client.aclose.assert_called_once()
        assert cache._client is None


# =============================================================================
# Queue Factory Tests
# =============================================================================


class TestQueueFactory:

    def test_create_memory_queue_default(self):
        from packages.core.storage.memory_queue import InMemoryQueue

        q = create_queue(backend="memory")
        assert isinstance(q, InMemoryQueue)

    def test_create_redis_queue(self):
        q = create_queue(backend="redis", redis_url="redis://test:6379/0")
        assert isinstance(q, RedisQueue)

    def test_create_memory_cache_default(self):
        from packages.core.storage.memory_cache import InMemoryCache

        c = create_cache(backend="memory")
        assert isinstance(c, InMemoryCache)

    def test_create_redis_cache(self):
        c = create_cache(backend="redis", redis_url="redis://test:6379/0")
        assert isinstance(c, RedisCache)

    @patch.dict("os.environ", {"QUEUE_BACKEND": "redis", "REDIS_URL": "redis://env:6379/0"})
    def test_factory_reads_env_var(self):
        q = create_queue()
        assert isinstance(q, RedisQueue)

    @patch.dict("os.environ", {}, clear=True)
    def test_factory_defaults_to_memory(self):
        from packages.core.storage.memory_queue import InMemoryQueue

        q = create_queue()
        assert isinstance(q, InMemoryQueue)
