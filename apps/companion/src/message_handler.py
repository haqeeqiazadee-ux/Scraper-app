"""
Message Handler — receives native messages from the Chrome extension and
routes them to the local control plane API.

Supported message types:
  - execute_task   : Submit a scraping task to the local control plane
  - get_status     : Check task status by task_id
  - get_results    : Retrieve extraction results for a task
  - health_check   : Verify companion + control plane health

Message protocol (from extension):
  { "type": "<message_type>", "payload": { ... }, "id": "<correlation_id>" }

Response protocol (to extension):
  { "type": "<message_type>_response", "payload": { ... }, "id": "<correlation_id>",
    "success": true/false, "error": "<error_message if failed>" }
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default local control plane endpoint
DEFAULT_API_BASE = "http://localhost:8000"

# Timeout for HTTP requests to the control plane (seconds)
REQUEST_TIMEOUT = 30


class MessageHandler:
    """Routes incoming native messages to the local control plane."""

    def __init__(self, api_base: str = DEFAULT_API_BASE) -> None:
        self._api_base = api_base.rstrip("/")
        self._client: Any = None  # Lazy httpx.AsyncClient

    async def _get_client(self) -> Any:
        """Lazy-initialize the HTTP client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(
                base_url=self._api_base,
                timeout=REQUEST_TIMEOUT,
                headers={"X-Tenant-ID": "desktop"},
            )
        return self._client

    async def handle(self, message: dict) -> dict:
        """
        Dispatch a message to the appropriate handler.

        Parameters
        ----------
        message : dict
            The incoming message with ``type``, ``payload``, and ``id`` keys.

        Returns
        -------
        dict
            Response message with ``type``, ``payload``, ``id``, ``success``,
            and optionally ``error`` keys.
        """
        msg_type = message.get("type", "")
        msg_id = message.get("id", "")
        payload = message.get("payload", {})

        handler_map = {
            "execute_task": self._handle_execute_task,
            "get_status": self._handle_get_status,
            "get_results": self._handle_get_results,
            "health_check": self._handle_health_check,
        }

        handler = handler_map.get(msg_type)
        if handler is None:
            return self._response(
                msg_type, msg_id, success=False,
                error=f"Unknown message type: {msg_type}",
            )

        try:
            result = await handler(payload)
            return self._response(msg_type, msg_id, success=True, payload=result)
        except Exception as exc:
            logger.exception("Handler error for type=%s", msg_type)
            return self._response(
                msg_type, msg_id, success=False, error=str(exc),
            )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    async def _handle_execute_task(self, payload: dict) -> dict:
        """Submit a scraping task to the local control plane."""
        url = payload.get("url")
        if not url:
            raise ValueError("URL is required in payload")

        client = await self._get_client()

        # If HTML is provided, use local extraction via extract endpoint
        if payload.get("html"):
            resp = await client.post(
                "/api/v1/extract",
                json={
                    "url": url,
                    "html": payload["html"],
                    "mode": payload.get("mode", "auto"),
                },
            )
        else:
            # Submit as a task
            resp = await client.post(
                "/api/v1/tasks",
                json={
                    "url": url,
                    "task_type": payload.get("task_type", "scrape"),
                    "metadata": payload.get("metadata", {}),
                },
            )

        resp.raise_for_status()
        data = resp.json()
        return {
            "task_id": data.get("id"),
            "status": data.get("status", "submitted"),
            "data": data,
        }

    async def _handle_get_status(self, payload: dict) -> dict:
        """Check task status by task_id."""
        task_id = payload.get("task_id")
        if not task_id:
            raise ValueError("task_id is required in payload")

        client = await self._get_client()
        resp = await client.get(f"/api/v1/tasks/{task_id}")
        resp.raise_for_status()
        data = resp.json()
        return {
            "task_id": task_id,
            "status": data.get("status", "unknown"),
            "data": data,
        }

    async def _handle_get_results(self, payload: dict) -> dict:
        """Retrieve extraction results for a task."""
        task_id = payload.get("task_id")
        if not task_id:
            raise ValueError("task_id is required in payload")

        client = await self._get_client()
        resp = await client.get(f"/api/v1/tasks/{task_id}/results")
        resp.raise_for_status()
        data = resp.json()
        return {
            "task_id": task_id,
            "results": data,
        }

    async def _handle_health_check(self, _payload: dict) -> dict:
        """Check that the companion and local control plane are alive."""
        companion_ok = True
        server_ok = False
        version = "0.1.0"

        try:
            client = await self._get_client()
            resp = await client.get("/health")
            server_ok = resp.status_code == 200
            health_data = resp.json()
            version = health_data.get("version", version)
        except Exception as exc:
            logger.warning("Health check to control plane failed: %s", exc)

        return {
            "companion": companion_ok,
            "server": server_ok,
            "version": version,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _response(
        msg_type: str,
        msg_id: str,
        *,
        success: bool,
        payload: dict | None = None,
        error: str | None = None,
    ) -> dict:
        """Build a response message envelope."""
        resp: dict[str, Any] = {
            "type": f"{msg_type}_response",
            "id": msg_id,
            "success": success,
            "payload": payload or {},
        }
        if error:
            resp["error"] = error
        return resp

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
