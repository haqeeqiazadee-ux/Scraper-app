"""
Webhook Executor — sends POST callbacks when tasks complete.

Sends task completion notifications to configured callback URLs with:
- HMAC signature verification (X-Webhook-Signature header)
- Exponential backoff retry (3 retries: 2s, 4s, 8s)
- Per-request timeout (30 seconds)
- Structured logging of all attempts
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import httpx

from packages.contracts.task import Task
from packages.contracts.result import Result

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 30.0


class WebhookDeliveryResult:
    """Outcome of a webhook delivery attempt."""

    def __init__(
        self,
        success: bool,
        status_code: Optional[int] = None,
        attempts: int = 0,
        error: Optional[str] = None,
    ) -> None:
        self.success = success
        self.status_code = status_code
        self.attempts = attempts
        self.error = error

    def __repr__(self) -> str:
        return (
            f"WebhookDeliveryResult(success={self.success}, "
            f"status_code={self.status_code}, attempts={self.attempts})"
        )


def _build_payload(task: Task, result: Optional[Result]) -> dict[str, Any]:
    """Build the webhook POST payload from task and result."""
    payload: dict[str, Any] = {
        "task_id": str(task.id),
        "status": task.status.value if hasattr(task.status, "value") else str(task.status),
        "url": str(task.url),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }
    if result is not None:
        payload["result"] = {
            "result_id": str(result.id),
            "item_count": result.item_count,
            "confidence": result.confidence,
            "extraction_method": result.extraction_method,
            "schema_version": result.schema_version,
        }
    return payload


def _compute_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for the payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


class WebhookExecutor:
    """Sends webhook POST requests on task completion.

    Usage:
        executor = WebhookExecutor()
        delivery = await executor.send(task, result)
        if delivery.success:
            ...
    """

    def __init__(
        self,
        max_retries: int = MAX_RETRIES,
        base_delay: float = BASE_DELAY_SECONDS,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._timeout = timeout
        self._external_client = client is not None
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialize the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client if we own it."""
        if self._client is not None and not self._external_client:
            await self._client.aclose()
            self._client = None

    async def send(
        self,
        task: Task,
        result: Optional[Result] = None,
    ) -> WebhookDeliveryResult:
        """Send a webhook notification for a completed task.

        Args:
            task: The completed task (must have callback_url set).
            result: Optional extraction result to include in the payload.

        Returns:
            WebhookDeliveryResult with delivery outcome.
        """
        if not task.callback_url:
            logger.debug(
                "No callback_url set, skipping webhook",
                extra={"task_id": str(task.id)},
            )
            return WebhookDeliveryResult(success=True, attempts=0)

        callback_url = str(task.callback_url)
        payload = _build_payload(task, result)
        payload_bytes = json.dumps(payload, default=str).encode("utf-8")

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "AI-Scraping-Platform/0.1",
        }

        # Add HMAC signature if webhook_secret is configured
        if task.webhook_secret:
            signature = _compute_signature(payload_bytes, task.webhook_secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        client = await self._get_client()
        last_error: Optional[str] = None
        last_status: Optional[int] = None

        import asyncio

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.info(
                    "Sending webhook",
                    extra={
                        "task_id": str(task.id),
                        "callback_url": callback_url,
                        "attempt": attempt,
                    },
                )

                response = await client.post(
                    callback_url,
                    content=payload_bytes,
                    headers=headers,
                )
                last_status = response.status_code

                if 200 <= response.status_code < 300:
                    logger.info(
                        "Webhook delivered successfully",
                        extra={
                            "task_id": str(task.id),
                            "status_code": response.status_code,
                            "attempt": attempt,
                        },
                    )
                    return WebhookDeliveryResult(
                        success=True,
                        status_code=response.status_code,
                        attempts=attempt,
                    )

                # Non-2xx — treat as failure, will retry
                last_error = f"HTTP {response.status_code}"
                logger.warning(
                    "Webhook received non-2xx response",
                    extra={
                        "task_id": str(task.id),
                        "status_code": response.status_code,
                        "attempt": attempt,
                    },
                )

            except httpx.TimeoutException:
                last_error = "Request timed out"
                logger.warning(
                    "Webhook request timed out",
                    extra={
                        "task_id": str(task.id),
                        "attempt": attempt,
                        "timeout": self._timeout,
                    },
                )

            except httpx.HTTPError as exc:
                last_error = str(exc)
                logger.warning(
                    "Webhook request failed",
                    extra={
                        "task_id": str(task.id),
                        "attempt": attempt,
                        "error": last_error,
                    },
                )

            # Exponential backoff before next retry
            if attempt < self._max_retries:
                delay = self._base_delay * (2 ** (attempt - 1))
                logger.debug(
                    "Waiting before webhook retry",
                    extra={"delay_seconds": delay, "attempt": attempt},
                )
                await asyncio.sleep(delay)

        logger.error(
            "Webhook delivery failed after all retries",
            extra={
                "task_id": str(task.id),
                "callback_url": callback_url,
                "attempts": self._max_retries,
                "last_error": last_error,
            },
        )
        return WebhookDeliveryResult(
            success=False,
            status_code=last_status,
            attempts=self._max_retries,
            error=last_error,
        )
