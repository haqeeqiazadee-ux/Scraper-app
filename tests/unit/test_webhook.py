"""Tests for WebhookExecutor — callback delivery on task completion."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from packages.contracts.task import Task, TaskStatus
from packages.contracts.result import Result
from packages.core.webhook import (
    WebhookExecutor,
    WebhookDeliveryResult,
    _build_payload,
    _compute_signature,
)


@pytest.fixture
def task_with_callback() -> Task:
    """Task with a callback URL configured."""
    return Task(
        tenant_id="test-tenant",
        url="https://example.com/products",
        callback_url="https://hooks.example.com/callback",
        status=TaskStatus.COMPLETED,
    )


@pytest.fixture
def task_with_secret() -> Task:
    """Task with callback URL and webhook secret."""
    return Task(
        tenant_id="test-tenant",
        url="https://example.com/products",
        callback_url="https://hooks.example.com/callback",
        webhook_secret="my-secret-key",
        status=TaskStatus.COMPLETED,
    )


@pytest.fixture
def task_no_callback() -> Task:
    """Task without a callback URL."""
    return Task(
        tenant_id="test-tenant",
        url="https://example.com/products",
        status=TaskStatus.COMPLETED,
    )


@pytest.fixture
def sample_result(task_with_callback: Task) -> Result:
    """A sample extraction result."""
    return Result(
        task_id=task_with_callback.id,
        run_id=task_with_callback.id,  # reuse for simplicity
        tenant_id="test-tenant",
        url="https://example.com/products",
        item_count=42,
        confidence=0.95,
        extraction_method="deterministic",
    )


class TestBuildPayload:

    def test_payload_includes_task_fields(self, task_with_callback: Task) -> None:
        """Payload should contain task_id, status, url, and timestamps."""
        payload = _build_payload(task_with_callback, None)
        assert payload["task_id"] == str(task_with_callback.id)
        assert payload["status"] == "completed"
        assert payload["url"] == str(task_with_callback.url)
        assert "completed_at" in payload
        assert "created_at" in payload

    def test_payload_includes_result_summary(
        self, task_with_callback: Task, sample_result: Result
    ) -> None:
        """Payload should include result summary when result is provided."""
        payload = _build_payload(task_with_callback, sample_result)
        assert "result" in payload
        assert payload["result"]["item_count"] == 42
        assert payload["result"]["confidence"] == 0.95
        assert payload["result"]["extraction_method"] == "deterministic"

    def test_payload_no_result(self, task_with_callback: Task) -> None:
        """Payload should not have result key when result is None."""
        payload = _build_payload(task_with_callback, None)
        assert "result" not in payload


class TestComputeSignature:

    def test_signature_is_hmac_sha256(self) -> None:
        """Signature should be a valid HMAC-SHA256 hex digest."""
        payload = b'{"task_id": "123"}'
        secret = "test-secret"
        sig = _compute_signature(payload, secret)
        expected = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        assert sig == expected

    def test_different_secrets_produce_different_signatures(self) -> None:
        """Different secrets must produce different signatures."""
        payload = b'{"task_id": "123"}'
        sig1 = _compute_signature(payload, "secret-a")
        sig2 = _compute_signature(payload, "secret-b")
        assert sig1 != sig2


class TestWebhookExecutor:

    @pytest.mark.asyncio
    async def test_no_callback_url_skips_send(self, task_no_callback: Task) -> None:
        """When no callback_url is set, send should return success with 0 attempts."""
        executor = WebhookExecutor()
        result = await executor.send(task_no_callback)
        assert result.success is True
        assert result.attempts == 0
        await executor.close()

    @pytest.mark.asyncio
    async def test_successful_delivery(self, task_with_callback: Task) -> None:
        """Webhook should be delivered on 200 response."""
        mock_response = httpx.Response(200, request=httpx.Request("POST", "https://hooks.example.com/callback"))
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        executor = WebhookExecutor(client=mock_client)
        delivery = await executor.send(task_with_callback)

        assert delivery.success is True
        assert delivery.status_code == 200
        assert delivery.attempts == 1
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_server_error(self, task_with_callback: Task) -> None:
        """Webhook should retry on 500 responses up to max_retries."""
        mock_response = httpx.Response(500, request=httpx.Request("POST", "https://hooks.example.com/callback"))
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        executor = WebhookExecutor(max_retries=3, base_delay=0.01, client=mock_client)
        delivery = await executor.send(task_with_callback)

        assert delivery.success is False
        assert delivery.attempts == 3
        assert delivery.status_code == 500
        assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self, task_with_callback: Task) -> None:
        """Webhook should retry when requests time out."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        executor = WebhookExecutor(max_retries=2, base_delay=0.01, client=mock_client)
        delivery = await executor.send(task_with_callback)

        assert delivery.success is False
        assert delivery.attempts == 2
        assert delivery.error == "Request timed out"
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self, task_with_callback: Task) -> None:
        """Webhook should retry on connection errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        executor = WebhookExecutor(max_retries=2, base_delay=0.01, client=mock_client)
        delivery = await executor.send(task_with_callback)

        assert delivery.success is False
        assert delivery.attempts == 2
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_signature_header_sent(self, task_with_secret: Task) -> None:
        """When webhook_secret is set, X-Webhook-Signature header should be included."""
        mock_response = httpx.Response(200, request=httpx.Request("POST", "https://hooks.example.com/callback"))
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        executor = WebhookExecutor(client=mock_client)
        delivery = await executor.send(task_with_secret)

        assert delivery.success is True
        # Verify that the headers include the signature
        call_kwargs = mock_client.post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert "X-Webhook-Signature" in headers
        assert headers["X-Webhook-Signature"].startswith("sha256=")

    @pytest.mark.asyncio
    async def test_no_signature_without_secret(self, task_with_callback: Task) -> None:
        """When no webhook_secret is set, X-Webhook-Signature header should not be present."""
        mock_response = httpx.Response(200, request=httpx.Request("POST", "https://hooks.example.com/callback"))
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        executor = WebhookExecutor(client=mock_client)
        delivery = await executor.send(task_with_callback)

        assert delivery.success is True
        call_kwargs = mock_client.post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert "X-Webhook-Signature" not in headers

    @pytest.mark.asyncio
    async def test_retry_then_success(self, task_with_callback: Task) -> None:
        """Webhook should succeed after initial failures if a retry succeeds."""
        fail_response = httpx.Response(503, request=httpx.Request("POST", "https://hooks.example.com/callback"))
        ok_response = httpx.Response(200, request=httpx.Request("POST", "https://hooks.example.com/callback"))
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(side_effect=[fail_response, ok_response])

        executor = WebhookExecutor(max_retries=3, base_delay=0.01, client=mock_client)
        delivery = await executor.send(task_with_callback)

        assert delivery.success is True
        assert delivery.attempts == 2
        assert delivery.status_code == 200

    @pytest.mark.asyncio
    async def test_delivery_result_repr(self) -> None:
        """WebhookDeliveryResult repr should be informative."""
        dr = WebhookDeliveryResult(success=True, status_code=200, attempts=1)
        assert "success=True" in repr(dr)
        assert "200" in repr(dr)
