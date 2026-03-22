"""
Secrets management — secure access to API keys and credentials.

Supports multiple backends:
- Environment variables (default, works everywhere)
- .env file (development)
- Future: AWS Secrets Manager, HashiCorp Vault, OS keychain
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class SecretProvider(Protocol):
    """Interface for secret storage backends."""

    def get_secret(self, key: str) -> Optional[str]: ...

    def set_secret(self, key: str, value: str) -> None: ...


class EnvSecretProvider:
    """Secrets from environment variables (default)."""

    def get_secret(self, key: str) -> Optional[str]:
        value = os.environ.get(key)
        if value:
            logger.debug("Secret retrieved", extra={"key": key})
        return value

    def set_secret(self, key: str, value: str) -> None:
        os.environ[key] = value


class SecretsManager:
    """Central secrets manager with provider chain."""

    def __init__(self) -> None:
        self._providers: list[SecretProvider] = [EnvSecretProvider()]

    def add_provider(self, provider: SecretProvider) -> None:
        """Add a secret provider (checked before env vars)."""
        self._providers.insert(0, provider)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret by key. Tries providers in order."""
        for provider in self._providers:
            value = provider.get_secret(key)
            if value is not None:
                return value
        return default

    def require(self, key: str) -> str:
        """Get a secret or raise if not found."""
        value = self.get(key)
        if value is None:
            raise ValueError(f"Required secret not found: {key}")
        return value

    def get_ai_key(self, provider: str = "gemini") -> Optional[str]:
        """Convenience: get AI provider API key."""
        key_map = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        env_key = key_map.get(provider, f"{provider.upper()}_API_KEY")
        return self.get(env_key)

    def get_database_url(self) -> str:
        """Convenience: get database URL."""
        return self.get("DATABASE_URL", "sqlite+aiosqlite:///./scraper.db")

    def get_redis_url(self) -> Optional[str]:
        """Convenience: get Redis URL."""
        return self.get("REDIS_URL")


# Global instance
secrets = SecretsManager()
