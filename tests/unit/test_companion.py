"""Tests for the native messaging companion host."""

from __future__ import annotations

import json
import struct

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from apps.companion.native_host import NativeMessageHost
from apps.companion.install import get_manifest, APP_NAME


class TestNativeMessageHost:
    def test_init_default(self):
        host = NativeMessageHost()
        assert host._api_base == "http://localhost:8000"

    def test_init_custom_base(self):
        host = NativeMessageHost(api_base="http://custom:9000")
        assert host._api_base == "http://custom:9000"

    @pytest.mark.asyncio
    async def test_handle_ping(self):
        host = NativeMessageHost()
        resp = await host.handle_message({"action": "ping"})
        assert resp["success"] is True
        assert resp["message"] == "pong"
        assert "version" in resp

    @pytest.mark.asyncio
    async def test_handle_unknown_action(self):
        host = NativeMessageHost()
        resp = await host.handle_message({"action": "nonexistent"})
        assert resp["success"] is False
        assert "Unknown action" in resp["error"]

    @pytest.mark.asyncio
    async def test_handle_scrape_no_url(self):
        host = NativeMessageHost()
        resp = await host.handle_message({"action": "scrape"})
        assert resp["success"] is False
        assert "URL required" in resp["error"]

    @pytest.mark.asyncio
    async def test_handle_extract_page_no_html(self):
        host = NativeMessageHost()
        resp = await host.handle_message({"action": "extract_page"})
        assert resp["success"] is False

    @pytest.mark.asyncio
    async def test_handle_extract_page_with_html(self):
        host = NativeMessageHost()
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "Product", "name": "Test Product", "offers": {"price": "9.99"}}
        </script>
        </head><body></body></html>
        """
        resp = await host.handle_message({
            "action": "extract_page",
            "html": html,
            "url": "https://example.com/product",
        })
        assert resp["success"] is True
        assert resp["item_count"] >= 0
        assert resp["method"] == "deterministic"

    @pytest.mark.asyncio
    async def test_handle_get_config(self):
        host = NativeMessageHost()
        resp = await host.handle_message({"action": "get_config"})
        assert resp["success"] is True
        assert resp["config"]["mode"] == "desktop"

    @pytest.mark.asyncio
    async def test_handle_status_offline(self):
        host = NativeMessageHost(api_base="http://localhost:99999")
        resp = await host.handle_message({"action": "status"})
        assert resp["server"] == "offline"

    def test_send_message(self):
        host = NativeMessageHost()
        mock_stdout = MagicMock()
        mock_stdout.buffer = MagicMock()

        with patch("sys.stdout", mock_stdout):
            host.send_message({"test": True})

        # Check that length prefix was written
        calls = mock_stdout.buffer.write.call_args_list
        assert len(calls) == 2  # length + payload
        length_bytes = calls[0][0][0]
        assert struct.unpack("<I", length_bytes)[0] > 0

    def test_read_message(self):
        host = NativeMessageHost()
        payload = json.dumps({"action": "ping"}).encode("utf-8")
        data = struct.pack("<I", len(payload)) + payload

        mock_stdin = MagicMock()
        mock_stdin.buffer.read.side_effect = [data[:4], data[4:]]

        with patch("sys.stdin", mock_stdin):
            msg = host.read_message()

        assert msg == {"action": "ping"}

    def test_read_message_eof(self):
        host = NativeMessageHost()
        mock_stdin = MagicMock()
        mock_stdin.buffer.read.return_value = b""

        with patch("sys.stdin", mock_stdin):
            msg = host.read_message()

        assert msg is None


class TestInstaller:
    def test_manifest_structure(self):
        manifest = get_manifest()
        assert manifest["name"] == APP_NAME
        assert manifest["type"] == "stdio"
        assert "allowed_origins" in manifest
        assert isinstance(manifest["allowed_origins"], list)
