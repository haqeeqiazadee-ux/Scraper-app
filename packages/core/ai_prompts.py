"""
AI Prompt Templates — reusable prompts for extraction, normalization, and repair.

Ported from scraper_pro/ai_scraper_v3.py with improvements.
"""

from __future__ import annotations


PRODUCT_EXTRACTION_PROMPT = """Analyze this HTML page and extract ALL product information as a JSON array.

URL: {url}

For each product found, extract these fields (leave empty string if not found):
- name: Product name/title
- sku: Product SKU or ID
- price: Current price (number only)
- original_price: Price before discount
- currency: Currency code (USD, EUR, PKR, etc.)
- discount: Discount percentage
- description: Short product description
- brand: Brand name
- category: Product category
- rating: Customer rating (number)
- reviews_count: Number of reviews (number)
- stock_status: "In Stock" or "Out of Stock"
- image_url: Main product image URL (absolute)
- product_url: Link to product page (absolute)

Return ONLY a valid JSON array. No markdown, no explanation, no code blocks.

HTML (may be truncated):
{html}"""


SCHEMA_NORMALIZATION_PROMPT = """Normalize this extracted data to match the target schema.

Rules:
1. Map field names to canonical names (e.g., "product_name" → "name", "cost" → "price")
2. Fix data types: prices should be numbers, ratings should be numbers
3. Clean values: remove HTML tags, fix encoding issues, trim whitespace
4. Convert relative URLs to absolute URLs using base URL: {base_url}
5. Standardize currency codes (e.g., "$" → "USD", "Rs" → "PKR", "€" → "EUR")

Input data:
{data}

Target schema fields: {schema_fields}

Return ONLY valid JSON. No explanation."""


DATA_REPAIR_PROMPT = """Fix the following extracted data that has quality issues.

Issues to fix:
- Truncated fields: complete partial text where obvious
- Garbled text: fix encoding issues
- Missing fields: infer from context if possible (e.g., currency from domain)
- Price format: ensure numeric format
- URL format: ensure absolute URLs

Data to repair:
{data}

Source URL: {url}

Return ONLY the repaired JSON. No explanation."""


DEDUP_PROMPT = """Compare these two product records and determine if they represent the same product.

Record A:
{record_a}

Record B:
{record_b}

If they are the same product, merge them into a single record keeping the most complete information from both.
If they are different products, return null.

Return ONLY the merged JSON record or the word "null". No explanation."""


CLASSIFICATION_PROMPT = """Classify this URL into one of these categories:
{categories}

URL: {url}
Page title: {title}

Respond with ONLY the category name, nothing else."""


def build_extraction_prompt(html: str, url: str, max_html_chars: int = 100_000) -> str:
    """Build product extraction prompt with truncated HTML."""
    truncated = html[:max_html_chars] if len(html) > max_html_chars else html
    return PRODUCT_EXTRACTION_PROMPT.format(url=url, html=truncated)


def build_normalization_prompt(data: dict, base_url: str, schema_fields: list[str]) -> str:
    """Build schema normalization prompt."""
    import json
    return SCHEMA_NORMALIZATION_PROMPT.format(
        data=json.dumps(data, indent=2),
        base_url=base_url,
        schema_fields=", ".join(schema_fields),
    )


def build_repair_prompt(data: dict, url: str) -> str:
    """Build data repair prompt."""
    import json
    return DATA_REPAIR_PROMPT.format(data=json.dumps(data, indent=2), url=url)


def build_dedup_prompt(record_a: dict, record_b: dict) -> str:
    """Build deduplication comparison prompt."""
    import json
    return DEDUP_PROMPT.format(
        record_a=json.dumps(record_a, indent=2),
        record_b=json.dumps(record_b, indent=2),
    )
