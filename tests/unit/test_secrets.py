"""Tests for secrets management."""

import os
import pytest
from packages.core.secrets import SecretsManager, EnvSecretProvider


class TestSecretsManager:

    @pytest.fixture
    def manager(self):
        return SecretsManager()

    def test_get_from_env(self, manager, monkeypatch):
        monkeypatch.setenv("TEST_SECRET", "my-value")
        assert manager.get("TEST_SECRET") == "my-value"

    def test_get_missing_returns_default(self, manager):
        assert manager.get("NONEXISTENT", "fallback") == "fallback"

    def test_get_missing_returns_none(self, manager):
        assert manager.get("NONEXISTENT") is None

    def test_require_exists(self, manager, monkeypatch):
        monkeypatch.setenv("REQUIRED_KEY", "value")
        assert manager.require("REQUIRED_KEY") == "value"

    def test_require_missing_raises(self, manager):
        with pytest.raises(ValueError, match="Required secret not found"):
            manager.require("DEFINITELY_MISSING_KEY_12345")

    def test_get_ai_key_gemini(self, manager, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
        assert manager.get_ai_key("gemini") == "gemini-key"

    def test_get_ai_key_openai(self, manager, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
        assert manager.get_ai_key("openai") == "openai-key"

    def test_get_database_url_default(self, manager):
        url = manager.get_database_url()
        assert "sqlite" in url

    def test_get_database_url_from_env(self, manager, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
        assert manager.get_database_url() == "postgresql://user:pass@host/db"

    def test_custom_provider(self, manager):
        class DictProvider:
            def __init__(self):
                self._store = {"CUSTOM_KEY": "custom-value"}
            def get_secret(self, key):
                return self._store.get(key)
            def set_secret(self, key, value):
                self._store[key] = value

        manager.add_provider(DictProvider())
        assert manager.get("CUSTOM_KEY") == "custom-value"
