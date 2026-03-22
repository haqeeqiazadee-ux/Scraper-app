"""
Native Messaging Host — bridges Chrome extension to local scraping engine.

Chrome extensions communicate with native applications via stdin/stdout
using a length-prefixed JSON protocol (Chrome Native Messaging).

Protocol:
  - Read: 4-byte little-endian length prefix, then JSON payload
  - Write: 4-byte little-endian length prefix, then JSON payload
"""

from __future__ import annotations

import asyncio
import json
import logging
import struct
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class NativeMessageHost:
    """Chrome Native Messaging host for local scraping."""

    def __init__(self, api_base: str = "http://localhost:8000") -> None:
        self._api_base = api_base
        self._running = False

    def read_message(self) -> Optional[dict]:
        """Read a native message from stdin."""
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length or len(raw_length) < 4:
            return None

        length = struct.unpack("<I", raw_length)[0]
        if length > 1024 * 1024:  # 1MB limit
            logger.error("Message too large: %d bytes", length)
            return None

        raw_message = sys.stdin.buffer.read(length)
        if len(raw_message) < length:
            return None

        return json.loads(raw_message.decode("utf-8"))

    def send_message(self, message: dict) -> None:
        """Send a native message to stdout."""
        encoded = json.dumps(message).encode("utf-8")
        sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()

    async def handle_message(self, message: dict) -> dict:
        """Process an incoming message and return response."""
        action = message.get("action", "")

        handlers = {
            "ping": self._handle_ping,
            "scrape": self._handle_scrape,
            "status": self._handle_status,
            "extract_page": self._handle_extract_page,
            "get_config": self._handle_get_config,
        }

        handler = handlers.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}", "success": False}

        try:
            return await handler(message)
        except Exception as e:
            logger.exception("Handler error for action: %s", action)
            return {"error": str(e), "success": False}

    async def _handle_ping(self, _message: dict) -> dict:
        return {"success": True, "message": "pong", "version": "0.1.0"}

    async def _handle_scrape(self, message: dict) -> dict:
        """Forward scrape request to local control plane."""
        url = message.get("url")
        if not url:
            return {"error": "URL required", "success": False}

        try:
            import httpx
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self._api_base}/api/v1/tasks",
                    json={
                        "url": url,
                        "task_type": message.get("task_type", "scrape"),
                        "metadata": message.get("metadata", {}),
                    },
                    headers={"X-Tenant-ID": "desktop"},
                )
                return {"success": resp.status_code == 201, "data": resp.json()}
        except Exception as e:
            return {"error": str(e), "success": False}

    async def _handle_status(self, _message: dict) -> dict:
        """Check local server status."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._api_base}/health")
                return {"success": True, "server": resp.json()}
        except Exception:
            return {"success": False, "server": "offline"}

    async def _handle_extract_page(self, message: dict) -> dict:
        """Extract data from HTML sent by extension."""
        html = message.get("html", "")
        url = message.get("url", "")

        if not html:
            return {"error": "HTML content required", "success": False}

        from packages.core.ai_providers.deterministic import DeterministicProvider
        provider = DeterministicProvider()
        items = await provider.extract(html, url)

        return {
            "success": True,
            "extracted_data": items,
            "item_count": len(items),
            "method": "deterministic",
        }

    async def _handle_get_config(self, _message: dict) -> dict:
        return {
            "success": True,
            "config": {
                "api_base": self._api_base,
                "version": "0.1.0",
                "mode": "desktop",
            },
        }

    def run(self) -> None:
        """Main loop — read messages from stdin, process, write to stdout."""
        self._running = True
        logger.info("Native messaging host started")

        while self._running:
            message = self.read_message()
            if message is None:
                break

            response = asyncio.run(self.handle_message(message))
            self.send_message(response)

        logger.info("Native messaging host stopped")

    def stop(self) -> None:
        self._running = False


def main() -> None:
    """Entry point for native messaging host."""
    logging.basicConfig(
        level=logging.INFO,
        filename="companion.log",
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    host = NativeMessageHost()
    host.run()


if __name__ == "__main__":
    main()
