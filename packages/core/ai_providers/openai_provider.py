"""
OpenAI AI provider — GPT integration for extraction and normalization.

Supports GPT-4o-mini (default), GPT-4o, and other chat models.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from packages.core.ai_providers.base import BaseAIProvider

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Analyze this HTML page and extract ALL product information as a JSON array.

URL: {url}

For each product found, extract these fields (leave empty string if not found):
- name: Product name/title
- sku: Product SKU or ID
- price: Current price (number only)
- original_price: Price before discount
- currency: Currency code (USD, EUR, etc.)
- discount: Discount percentage
- description: Short product description
- brand: Brand name
- category: Product category
- rating: Customer rating
- reviews_count: Number of reviews
- stock_status: In Stock / Out of Stock
- image_url: Main product image URL
- product_url: Link to product page

Return ONLY a valid JSON array. No markdown, no explanation.

HTML (truncated):
{html}"""

NORMALIZATION_PROMPT = """Normalize this extracted data to match the target schema.
Map field names, fix data types, clean values.

Data: {data}
Target schema fields: {schema}

Return ONLY valid JSON. No explanation."""


class OpenAIProvider(BaseAIProvider):
    """OpenAI GPT provider for extraction and normalization."""

    MODELS = [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
    ]

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        super().__init__(name="openai")
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):  # type: ignore[no-untyped-def]
        """Lazy-initialize OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError("Install openai: pip install openai")
        return self._client

    def _chat(self, prompt: str, max_tokens: int = 4096) -> str:
        """Send a chat completion request and return the response text."""
        client = self._get_client()
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "You are a data extraction assistant. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.1,
        )
        self._token_count += response.usage.total_tokens if response.usage else 0
        return response.choices[0].message.content or ""

    async def extract(self, html: str, url: str, prompt: Optional[str] = None) -> list[dict]:
        """Extract product data using OpenAI."""
        truncated_html = self._truncate_html(html)
        extraction_prompt = prompt or EXTRACTION_PROMPT.format(url=url, html=truncated_html)

        try:
            text = self._chat(extraction_prompt)
            return self._parse_json_response(text)
        except Exception as e:
            logger.warning(f"OpenAI extraction failed: {e}", extra={"model": self._model, "url": url})
            raise

    async def classify(self, text: str, labels: list[str]) -> str:
        """Classify text using OpenAI."""
        prompt = f"Classify this text into exactly one of these categories: {', '.join(labels)}\n\nText: {text}\n\nRespond with ONLY the category name."

        try:
            result = self._chat(prompt, max_tokens=50)
            result = result.strip().strip('"').strip("'")
            for label in labels:
                if label.lower() in result.lower():
                    return label
            return labels[0]
        except Exception as e:
            logger.warning(f"OpenAI classify failed: {e}")
            raise

    async def normalize(self, data: dict, target_schema: dict) -> dict:
        """Normalize data using OpenAI."""
        prompt = NORMALIZATION_PROMPT.format(data=json.dumps(data), schema=json.dumps(target_schema))

        try:
            text = self._chat(prompt)
            parsed = self._parse_json_response(text)
            return parsed[0] if parsed else data
        except Exception as e:
            logger.warning(f"OpenAI normalize failed: {e}")
            raise

    def _parse_json_response(self, text: str) -> list[dict]:
        """Parse JSON from AI response, handling markdown code blocks."""
        text = text.strip()
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        text = text.strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                return [parsed]
            return []
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning("Failed to parse JSON from OpenAI response")
            return []
