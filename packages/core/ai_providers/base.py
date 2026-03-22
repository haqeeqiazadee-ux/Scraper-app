"""
Base AI provider and factory.

The factory creates providers based on configuration and supports
fallback chains (e.g., Gemini → OpenAI → deterministic).
"""

from __future__ import annotations

import logging
from typing import Optional

from packages.core.interfaces import AIProvider

logger = logging.getLogger(__name__)


class BaseAIProvider:
    """Base class for AI providers with common utilities."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._token_count = 0

    def get_token_usage(self) -> int:
        return self._token_count

    def _truncate_html(self, html: str, max_chars: int = 100_000) -> str:
        """Truncate HTML to fit within token limits."""
        if len(html) <= max_chars:
            return html
        # Keep head and first portion of body
        return html[:max_chars] + "\n<!-- TRUNCATED -->"


class AIProviderFactory:
    """Factory for creating AI providers with fallback chain."""

    _providers: list[AIProvider] = []

    @classmethod
    def create(
        cls,
        provider_type: str = "deterministic",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AIProvider:
        """Create a single AI provider."""
        if provider_type == "gemini" and api_key:
            from packages.core.ai_providers.gemini import GeminiProvider
            return GeminiProvider(api_key=api_key, model=model or "gemini-1.5-flash")
        elif provider_type == "openai" and api_key:
            from packages.core.ai_providers.openai_provider import OpenAIProvider
            return OpenAIProvider(api_key=api_key, model=model or "gpt-4o-mini")
        else:
            from packages.core.ai_providers.deterministic import DeterministicProvider
            return DeterministicProvider()

    @classmethod
    def create_chain(cls, configs: list[dict]) -> "AIProviderChain":
        """Create a fallback chain of providers."""
        providers = []
        for config in configs:
            try:
                provider = cls.create(**config)
                providers.append(provider)
            except Exception as e:
                logger.warning(f"Failed to create provider {config.get('provider_type')}: {e}")

        # Always add deterministic as final fallback
        from packages.core.ai_providers.deterministic import DeterministicProvider
        if not any(isinstance(p, DeterministicProvider) for p in providers):
            providers.append(DeterministicProvider())

        return AIProviderChain(providers)


class AIProviderChain:
    """Chain of AI providers with automatic fallback."""

    def __init__(self, providers: list[AIProvider]) -> None:
        self._providers = providers
        self._token_count = 0

    async def extract(self, html: str, url: str, prompt: Optional[str] = None) -> list[dict]:
        """Try each provider in order until one succeeds."""
        last_error = None
        for provider in self._providers:
            try:
                result = await provider.extract(html, url, prompt)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Provider {getattr(provider, 'name', '?')} failed: {e}")
                last_error = e
                continue

        logger.error(f"All AI providers failed. Last error: {last_error}")
        return []

    async def classify(self, text: str, labels: list[str]) -> str:
        for provider in self._providers:
            try:
                return await provider.classify(text, labels)
            except Exception:
                continue
        return labels[0] if labels else ""

    async def normalize(self, data: dict, target_schema: dict) -> dict:
        for provider in self._providers:
            try:
                return await provider.normalize(data, target_schema)
            except Exception:
                continue
        return data

    def get_token_usage(self) -> int:
        return sum(p.get_token_usage() for p in self._providers)
