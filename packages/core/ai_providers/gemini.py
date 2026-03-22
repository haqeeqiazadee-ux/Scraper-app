"""
Gemini AI provider — Google Gemini integration for extraction.

Ported from scraper_pro/ai_scraper_v3.py GeminiAI class.
Supports multiple Gemini models with automatic fallback.
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


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider for extraction and normalization."""

    MODELS = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-2.0-flash",
    ]

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        super().__init__(name="gemini")
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):  # type: ignore[no-untyped-def]
        """Lazy-initialize Gemini client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except ImportError:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=self._api_key)
                    self._client = genai
                except ImportError:
                    raise ImportError("Install google-genai: pip install google-genai")
        return self._client

    async def extract(self, html: str, url: str, prompt: Optional[str] = None) -> list[dict]:
        """Extract product data using Gemini AI."""
        client = self._get_client()
        truncated_html = self._truncate_html(html)

        extraction_prompt = prompt or EXTRACTION_PROMPT.format(url=url, html=truncated_html)

        try:
            response = client.models.generate_content(
                model=self._model,
                contents=extraction_prompt,
            )
            text = response.text
            self._token_count += getattr(response, "usage_metadata", None) and getattr(response.usage_metadata, "total_token_count", 0) or 0

            return self._parse_json_response(text)
        except Exception as e:
            logger.warning(f"Gemini extraction failed: {e}", extra={"model": self._model, "url": url})
            raise

    async def classify(self, text: str, labels: list[str]) -> str:
        """Classify text using Gemini."""
        client = self._get_client()
        prompt = f"Classify this text into exactly one of these categories: {', '.join(labels)}\n\nText: {text}\n\nRespond with ONLY the category name."

        try:
            response = client.models.generate_content(model=self._model, contents=prompt)
            result = response.text.strip()
            # Find closest matching label
            for label in labels:
                if label.lower() in result.lower():
                    return label
            return labels[0]
        except Exception as e:
            logger.warning(f"Gemini classify failed: {e}")
            raise

    async def normalize(self, data: dict, target_schema: dict) -> dict:
        """Normalize data using Gemini."""
        client = self._get_client()
        prompt = NORMALIZATION_PROMPT.format(data=json.dumps(data), schema=json.dumps(target_schema))

        try:
            response = client.models.generate_content(model=self._model, contents=prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.warning(f"Gemini normalize failed: {e}")
            raise

    def _parse_json_response(self, text: str) -> list[dict]:
        """Parse JSON from AI response, handling markdown code blocks."""
        text = text.strip()
        # Remove markdown code blocks
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
            # Try to find JSON array in text
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning("Failed to parse JSON from AI response")
            return []
