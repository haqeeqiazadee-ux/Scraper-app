"""
🧠 SCRAPLING PRO - AI Layout Detection
=======================================
Automatically detect and extract data from any webpage using AI.

Features:
- Natural language extraction ("find all product prices")
- Visual understanding of page layout
- Self-healing selectors that survive redesigns
- Zero-config scraping for common patterns
- Multiple AI backends (Claude, OpenAI, local LLM, heuristics)

Usage:
    from ai_extractor import AIExtractor
    
    # Simple extraction
    extractor = AIExtractor(api_key="your-claude-api-key")
    
    products = extractor.extract(
        html=page_html,
        prompt="Extract all products with their name, price, and image URL"
    )
    
    # Or use auto-detection
    data = extractor.auto_extract(html, url)  # Automatically detects page type
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

logger = logging.getLogger("AIExtractor")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ExtractionResult:
    """Result from AI extraction"""
    success: bool
    data: List[Dict]
    method: str  # "claude", "openai", "heuristic", "schema"
    confidence: float  # 0-1
    selectors_found: Dict[str, str] = field(default_factory=dict)  # For caching
    error: Optional[str] = None
    tokens_used: int = 0
    

@dataclass
class PageAnalysis:
    """Analysis of page structure"""
    page_type: str  # "product", "listing", "article", "search", "unknown"
    detected_elements: Dict[str, int]  # {"products": 10, "prices": 10, etc}
    suggested_selectors: Dict[str, str]
    schema_data: Dict  # JSON-LD/microdata if found
    confidence: float


# ============================================================================
# SCHEMA.ORG EXTRACTOR (Free, Fast)
# ============================================================================

class SchemaExtractor:
    """
    Extract structured data using Schema.org markup.
    This is the fastest and most reliable method when available.
    """
    
    def extract(self, html: str, url: str = "") -> Dict[str, Any]:
        """Extract Schema.org data from HTML"""
        try:
            import extruct
            from w3lib.html import get_base_url
            
            base_url = get_base_url(html, url) if url else ""
            data = extruct.extract(html, base_url=base_url, 
                                   syntaxes=['json-ld', 'microdata', 'opengraph'])
            
            return {
                'json_ld': data.get('json-ld', []),
                'microdata': data.get('microdata', []),
                'opengraph': data.get('opengraph', []),
            }
        except ImportError:
            logger.warning("extruct not installed, schema extraction disabled")
            return {}
        except Exception as e:
            logger.error(f"Schema extraction failed: {e}")
            return {}
    
    def extract_products(self, html: str, url: str = "") -> List[Dict]:
        """Extract product data from Schema.org markup"""
        schema = self.extract(html, url)
        products = []
        
        # Check JSON-LD
        for item in schema.get('json_ld', []):
            if item.get('@type') == 'Product':
                products.append(self._parse_product(item))
            elif item.get('@type') == 'ItemList':
                for elem in item.get('itemListElement', []):
                    if elem.get('item', {}).get('@type') == 'Product':
                        products.append(self._parse_product(elem['item']))
        
        # Check microdata
        for item in schema.get('microdata', []):
            if 'Product' in str(item.get('type', '')):
                products.append(self._parse_product_microdata(item))
        
        return products
    
    def _parse_product(self, item: Dict) -> Dict:
        """Parse JSON-LD Product"""
        offers = item.get('offers', {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        
        return {
            'name': item.get('name'),
            'description': item.get('description', '')[:200],
            'price': offers.get('price'),
            'currency': offers.get('priceCurrency'),
            'image': item.get('image'),
            'sku': item.get('sku'),
            'brand': item.get('brand', {}).get('name') if isinstance(item.get('brand'), dict) else item.get('brand'),
            'rating': item.get('aggregateRating', {}).get('ratingValue'),
            'reviews': item.get('aggregateRating', {}).get('reviewCount'),
            'availability': offers.get('availability', '').split('/')[-1],
            'url': item.get('url'),
        }
    
    def _parse_product_microdata(self, item: Dict) -> Dict:
        """Parse microdata Product"""
        props = item.get('properties', {})
        return {
            'name': props.get('name'),
            'price': props.get('price'),
            'image': props.get('image'),
        }


# ============================================================================
# HEURISTIC EXTRACTOR (Free, Fast)
# ============================================================================

class HeuristicExtractor:
    """
    Extract data using common HTML patterns and heuristics.
    No AI required, works offline.
    """
    
    # Common selector patterns for different data types
    PATTERNS = {
        'product_container': [
            '[data-product]', '[itemtype*="Product"]', '.product', '.product-card',
            '.product-item', '.product-tile', 'article.product', '.item',
            '[data-component="product"]', '.goods-item', '.listing-item'
        ],
        'price': [
            '[itemprop="price"]', '.price', '.product-price', '.sale-price',
            '.current-price', '[data-price]', '.amount', '.cost',
            'span[class*="price"]', 'div[class*="price"]', '.offer-price'
        ],
        'title': [
            '[itemprop="name"]', 'h1', 'h2', 'h3', '.title', '.product-title',
            '.product-name', '.name', '[data-title]', '.item-title'
        ],
        'image': [
            '[itemprop="image"]', 'img.product-image', 'img.primary',
            '.product-image img', '.gallery img', 'img[data-src]',
            'img.lazy', 'picture img', '.image img'
        ],
        'description': [
            '[itemprop="description"]', '.description', '.product-description',
            '.details', '.info', 'p.description', '.summary'
        ],
        'rating': [
            '[itemprop="ratingValue"]', '.rating', '.stars', '.star-rating',
            '[class*="rating"]', '[class*="stars"]', '.review-rating'
        ],
        'review_count': [
            '[itemprop="reviewCount"]', '.review-count', '.reviews-count',
            '[class*="review"]', '.ratings-count'
        ],
        'sku': [
            '[itemprop="sku"]', '.sku', '.product-sku', '[data-sku]',
            '.item-number', '.model-number'
        ],
        'availability': [
            '[itemprop="availability"]', '.availability', '.stock',
            '.in-stock', '.out-of-stock', '[class*="stock"]'
        ],
    }
    
    def find_selectors(self, html: str) -> Dict[str, str]:
        """Find working selectors for each data type"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        found_selectors = {}
        
        for data_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                try:
                    elements = soup.select(pattern)
                    if elements:
                        found_selectors[data_type] = pattern
                        break
                except Exception:
                    continue
        
        return found_selectors
    
    def extract_products(self, html: str) -> List[Dict]:
        """Extract products using heuristics"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        selectors = self.find_selectors(html)
        products = []
        
        # Find product containers
        container_selector = selectors.get('product_container')
        if not container_selector:
            return []
        
        containers = soup.select(container_selector)
        
        for container in containers:
            product = {}
            
            # Extract each field
            for field in ['title', 'price', 'image', 'description', 'rating', 'sku']:
                selector = selectors.get(field)
                if selector:
                    # Try to find within container first
                    el = container.select_one(selector.split('[')[0] if '[' in selector else selector)
                    if el:
                        if field == 'image':
                            product[field] = el.get('src') or el.get('data-src') or ''
                        elif field == 'price':
                            product[field] = self._clean_price(el.get_text(strip=True))
                        else:
                            product[field] = el.get_text(strip=True)
            
            if product.get('title') or product.get('price'):
                products.append(product)
        
        return products
    
    def _clean_price(self, text: str) -> str:
        """Clean price text"""
        # Remove extra whitespace and common prefixes
        text = re.sub(r'\s+', ' ', text).strip()
        # Try to extract just the price
        match = re.search(r'[\$€£¥₹]?\s*[\d,]+\.?\d*', text)
        return match.group(0) if match else text
    
    def detect_page_type(self, html: str, url: str = "") -> str:
        """Detect type of page"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check URL patterns
        url_lower = url.lower()
        if any(x in url_lower for x in ['/product/', '/item/', '/p/', '/dp/']):
            return 'product_detail'
        if any(x in url_lower for x in ['/category/', '/collection/', '/shop/', '/products']):
            return 'product_listing'
        if any(x in url_lower for x in ['/article/', '/post/', '/blog/', '/news/']):
            return 'article'
        if any(x in url_lower for x in ['/search', '?q=', '?query=']):
            return 'search_results'
        
        # Check page content
        products = soup.select('[itemtype*="Product"], .product, .product-card')
        articles = soup.select('article, .article, .post')
        
        if len(products) > 3:
            return 'product_listing'
        elif len(products) == 1:
            return 'product_detail'
        elif len(articles) > 0:
            return 'article'
        
        return 'unknown'


# ============================================================================
# AI EXTRACTOR (Claude/OpenAI)
# ============================================================================

class AIExtractor:
    """
    AI-powered data extraction using LLMs.
    
    Supports:
    - Anthropic Claude (recommended)
    - OpenAI GPT-4
    - Fallback to heuristics
    
    Usage:
        extractor = AIExtractor(
            anthropic_api_key="sk-ant-...",
            # or openai_api_key="sk-..."
        )
        
        # Natural language extraction
        result = extractor.extract(
            html=page_html,
            prompt="Extract all products with name, price, rating, and image URL"
        )
        
        # Auto-detect and extract
        result = extractor.auto_extract(html, url)
    """
    
    def __init__(
        self,
        anthropic_api_key: str = None,
        openai_api_key: str = None,
        model: str = None,
        use_cache: bool = True,
        fallback_to_heuristics: bool = True,
    ):
        self.anthropic_api_key = anthropic_api_key
        self.openai_api_key = openai_api_key
        self.model = model
        self.use_cache = use_cache
        self.fallback_to_heuristics = fallback_to_heuristics
        
        # Determine which AI to use
        if anthropic_api_key:
            self.ai_provider = "claude"
            self.model = model or "claude-sonnet-4-20250514"
        elif openai_api_key:
            self.ai_provider = "openai"
            self.model = model or "gpt-4o-mini"
        else:
            self.ai_provider = None
            logger.info("No AI API key provided, using heuristics only")
        
        # Cache for selectors
        self._selector_cache: Dict[str, Dict] = {}
        
        # Sub-extractors
        self.schema_extractor = SchemaExtractor()
        self.heuristic_extractor = HeuristicExtractor()
    
    def extract(
        self,
        html: str,
        prompt: str,
        url: str = "",
        max_items: int = 50,
    ) -> ExtractionResult:
        """
        Extract data using natural language prompt.
        
        Args:
            html: Page HTML content
            prompt: Natural language description of what to extract
                    e.g., "Extract all products with name, price, and image"
            url: Page URL (optional, helps with context)
            max_items: Maximum items to extract
            
        Returns:
            ExtractionResult with extracted data
        """
        # Try Schema.org first (fastest, most reliable)
        if "product" in prompt.lower():
            schema_products = self.schema_extractor.extract_products(html, url)
            if schema_products:
                return ExtractionResult(
                    success=True,
                    data=schema_products[:max_items],
                    method="schema",
                    confidence=0.95,
                )
        
        # Try AI extraction
        if self.ai_provider:
            try:
                result = self._extract_with_ai(html, prompt, url, max_items)
                if result.success:
                    return result
            except Exception as e:
                logger.warning(f"AI extraction failed: {e}")
        
        # Fallback to heuristics
        if self.fallback_to_heuristics:
            return self._extract_with_heuristics(html, prompt, url, max_items)
        
        return ExtractionResult(
            success=False,
            data=[],
            method="none",
            confidence=0,
            error="No extraction method available"
        )
    
    def auto_extract(self, html: str, url: str = "") -> ExtractionResult:
        """
        Automatically detect page type and extract relevant data.
        """
        # Detect page type
        page_type = self.heuristic_extractor.detect_page_type(html, url)
        
        # Choose extraction prompt based on page type
        prompts = {
            'product_detail': "Extract the product details: name, price, description, images, rating, reviews, availability, SKU",
            'product_listing': "Extract all products with their name, price, image, and link",
            'article': "Extract the article: title, author, date, content, images",
            'search_results': "Extract all search results with title, snippet, and link",
        }
        
        prompt = prompts.get(page_type, "Extract the main content and any structured data")
        
        return self.extract(html, prompt, url)
    
    def find_selectors(
        self,
        html: str,
        fields: List[str],
        url: str = "",
    ) -> Dict[str, str]:
        """
        Use AI to find CSS selectors for specified fields.
        
        This is useful for creating reusable scrapers.
        
        Args:
            html: Page HTML
            fields: List of fields to find selectors for
                    e.g., ["product_name", "price", "image", "rating"]
            url: Page URL
            
        Returns:
            Dict mapping field names to CSS selectors
        """
        # Check cache
        cache_key = hashlib.md5(f"{url}:{','.join(fields)}".encode()).hexdigest()
        if self.use_cache and cache_key in self._selector_cache:
            return self._selector_cache[cache_key]
        
        # Try heuristics first
        heuristic_selectors = self.heuristic_extractor.find_selectors(html)
        
        # Map to requested fields
        field_mapping = {
            'product_name': 'title',
            'name': 'title',
            'title': 'title',
            'price': 'price',
            'image': 'image',
            'description': 'description',
            'rating': 'rating',
            'reviews': 'review_count',
            'sku': 'sku',
            'availability': 'availability',
            'stock': 'availability',
        }
        
        result = {}
        for field in fields:
            mapped = field_mapping.get(field.lower(), field.lower())
            if mapped in heuristic_selectors:
                result[field] = heuristic_selectors[mapped]
        
        # If AI available and some fields missing, use AI
        missing_fields = [f for f in fields if f not in result]
        if missing_fields and self.ai_provider:
            ai_selectors = self._find_selectors_with_ai(html, missing_fields)
            result.update(ai_selectors)
        
        # Cache result
        if self.use_cache:
            self._selector_cache[cache_key] = result
        
        return result
    
    def _extract_with_ai(
        self,
        html: str,
        prompt: str,
        url: str,
        max_items: int,
    ) -> ExtractionResult:
        """Extract using AI (Claude or OpenAI)"""
        
        # Truncate HTML if too long
        max_html_chars = 100000  # ~25k tokens
        if len(html) > max_html_chars:
            # Keep head and truncate body intelligently
            html = self._truncate_html(html, max_html_chars)
        
        system_prompt = """You are an expert web scraper. Extract structured data from HTML based on the user's request.

IMPORTANT RULES:
1. Return ONLY valid JSON - no explanations, no markdown, just the JSON array
2. Extract ALL matching items, not just examples
3. Use null for missing values, don't skip fields
4. Clean the data (remove extra whitespace, normalize prices)
5. For prices, extract just the number (e.g., "29.99" not "$29.99 USD")
6. For images, return the full URL if possible

Example output format:
[
  {"name": "Product 1", "price": 29.99, "image": "https://..."},
  {"name": "Product 2", "price": 39.99, "image": "https://..."}
]"""

        user_prompt = f"""URL: {url}

TASK: {prompt}

HTML:
{html}

Extract the data and return as a JSON array. Return ONLY the JSON, no other text."""

        if self.ai_provider == "claude":
            return self._call_claude(system_prompt, user_prompt, max_items)
        elif self.ai_provider == "openai":
            return self._call_openai(system_prompt, user_prompt, max_items)
        
        return ExtractionResult(success=False, data=[], method="ai", confidence=0, error="No AI provider")
    
    def _call_claude(self, system: str, user: str, max_items: int) -> ExtractionResult:
        """Call Claude API"""
        try:
            import requests
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 4096,
                    "system": system,
                    "messages": [{"role": "user", "content": user}]
                },
                timeout=60
            )
            
            if response.status_code != 200:
                return ExtractionResult(
                    success=False, data=[], method="claude", confidence=0,
                    error=f"API error: {response.status_code}"
                )
            
            result = response.json()
            content = result.get('content', [{}])[0].get('text', '[]')
            tokens = result.get('usage', {}).get('input_tokens', 0) + result.get('usage', {}).get('output_tokens', 0)
            
            # Parse JSON
            data = self._parse_json_response(content)
            
            return ExtractionResult(
                success=bool(data),
                data=data[:max_items] if data else [],
                method="claude",
                confidence=0.9 if data else 0,
                tokens_used=tokens
            )
            
        except Exception as e:
            return ExtractionResult(
                success=False, data=[], method="claude", confidence=0,
                error=str(e)
            )
    
    def _call_openai(self, system: str, user: str, max_items: int) -> ExtractionResult:
        """Call OpenAI API"""
        try:
            import requests
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                    "max_tokens": 4096,
                    "temperature": 0,
                },
                timeout=60
            )
            
            if response.status_code != 200:
                return ExtractionResult(
                    success=False, data=[], method="openai", confidence=0,
                    error=f"API error: {response.status_code}"
                )
            
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '[]')
            tokens = result.get('usage', {}).get('total_tokens', 0)
            
            # Parse JSON
            data = self._parse_json_response(content)
            
            return ExtractionResult(
                success=bool(data),
                data=data[:max_items] if data else [],
                method="openai",
                confidence=0.85 if data else 0,
                tokens_used=tokens
            )
            
        except Exception as e:
            return ExtractionResult(
                success=False, data=[], method="openai", confidence=0,
                error=str(e)
            )
    
    def _find_selectors_with_ai(self, html: str, fields: List[str]) -> Dict[str, str]:
        """Use AI to find CSS selectors"""
        # Truncate HTML
        html = self._truncate_html(html, 50000)
        
        prompt = f"""Analyze this HTML and find the CSS selectors for these fields: {', '.join(fields)}

Return ONLY a JSON object mapping field names to CSS selectors.
Example: {{"price": ".product-price", "title": "h1.product-name"}}

HTML:
{html}

JSON:"""

        if self.ai_provider == "claude":
            result = self._call_claude("You find CSS selectors in HTML. Return only valid JSON.", prompt, 100)
        elif self.ai_provider == "openai":
            result = self._call_openai("You find CSS selectors in HTML. Return only valid JSON.", prompt, 100)
        else:
            return {}
        
        if result.success and result.data:
            # Result should be a dict, not a list
            if isinstance(result.data, dict):
                return result.data
            elif isinstance(result.data, list) and len(result.data) > 0:
                return result.data[0] if isinstance(result.data[0], dict) else {}
        
        return {}
    
    def _extract_with_heuristics(
        self,
        html: str,
        prompt: str,
        url: str,
        max_items: int,
    ) -> ExtractionResult:
        """Extract using heuristics"""
        if "product" in prompt.lower():
            data = self.heuristic_extractor.extract_products(html)
            return ExtractionResult(
                success=bool(data),
                data=data[:max_items],
                method="heuristic",
                confidence=0.6 if data else 0,
            )
        
        return ExtractionResult(
            success=False,
            data=[],
            method="heuristic",
            confidence=0,
            error="No matching heuristic pattern"
        )
    
    def _parse_json_response(self, text: str) -> Union[List, Dict]:
        """Parse JSON from AI response, handling common issues"""
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON array or object
        array_match = re.search(r'\[[\s\S]*\]', text)
        if array_match:
            try:
                return json.loads(array_match.group(0))
            except json.JSONDecodeError:
                pass
        
        obj_match = re.search(r'\{[\s\S]*\}', text)
        if obj_match:
            try:
                return json.loads(obj_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return []
    
    def _truncate_html(self, html: str, max_chars: int) -> str:
        """Intelligently truncate HTML"""
        if len(html) <= max_chars:
            return html
        
        # Try to keep structure intact
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove scripts, styles, comments
        for tag in soup.find_all(['script', 'style', 'noscript', 'iframe']):
            tag.decompose()
        
        # Get cleaned HTML
        cleaned = str(soup)
        
        if len(cleaned) <= max_chars:
            return cleaned
        
        # Still too long, truncate body
        body = soup.find('body')
        if body:
            body_html = str(body)
            if len(body_html) > max_chars - 1000:
                # Keep first portion of body
                return body_html[:max_chars]
        
        return cleaned[:max_chars]


# ============================================================================
# SELF-HEALING SELECTORS
# ============================================================================

class SelfHealingSelector:
    """
    Selectors that automatically update when page structure changes.
    
    Uses multiple identification strategies:
    1. Original CSS selector
    2. Element attributes (id, data-*, aria-*)
    3. Text content patterns
    4. Position relative to landmarks
    5. AI-based re-detection
    
    Usage:
        selector = SelfHealingSelector(
            name="product_price",
            original_selector=".price-tag",
            sample_values=["$29.99", "$39.99"],
            ai_extractor=extractor  # Optional
        )
        
        elements = selector.find(page)  # Auto-heals if original fails
    """
    
    def __init__(
        self,
        name: str,
        original_selector: str,
        sample_values: List[str] = None,
        value_pattern: str = None,  # Regex pattern for values
        ai_extractor: AIExtractor = None,
    ):
        self.name = name
        self.original_selector = original_selector
        self.current_selector = original_selector
        self.sample_values = sample_values or []
        self.value_pattern = value_pattern
        self.ai_extractor = ai_extractor
        
        self.healing_attempts = 0
        self.last_healed = None
    
    def find(self, page_or_html, soup=None) -> List:
        """Find elements, auto-healing if needed"""
        if soup is None:
            from bs4 import BeautifulSoup
            html = page_or_html if isinstance(page_or_html, str) else page_or_html.html
            soup = BeautifulSoup(html, 'html.parser')
        
        # Try current selector
        elements = soup.select(self.current_selector)
        if elements and self._validate_elements(elements):
            return elements
        
        # Try original selector
        if self.current_selector != self.original_selector:
            elements = soup.select(self.original_selector)
            if elements and self._validate_elements(elements):
                self.current_selector = self.original_selector
                return elements
        
        # Attempt healing
        healed_selector = self._heal(soup)
        if healed_selector:
            self.current_selector = healed_selector
            self.healing_attempts += 1
            self.last_healed = datetime.now().isoformat()
            
            elements = soup.select(healed_selector)
            if elements:
                logger.info(f"Selector healed: {self.name} -> {healed_selector}")
                return elements
        
        logger.warning(f"Could not heal selector: {self.name}")
        return []
    
    def _validate_elements(self, elements: List) -> bool:
        """Check if elements contain expected values"""
        if not self.sample_values and not self.value_pattern:
            return bool(elements)
        
        for el in elements:
            text = el.get_text(strip=True)
            
            # Check sample values
            if self.sample_values:
                if any(sample in text for sample in self.sample_values):
                    return True
            
            # Check pattern
            if self.value_pattern:
                if re.search(self.value_pattern, text):
                    return True
        
        return False
    
    def _heal(self, soup) -> Optional[str]:
        """Attempt to find a working selector"""
        # Strategy 1: Find by text content
        if self.sample_values:
            for sample in self.sample_values:
                elements = soup.find_all(string=re.compile(re.escape(sample)))
                for el in elements:
                    parent = el.parent
                    if parent and parent.name:
                        # Build selector from parent
                        selector = self._build_selector(parent)
                        if selector:
                            return selector
        
        # Strategy 2: Find by pattern
        if self.value_pattern:
            for el in soup.find_all(string=re.compile(self.value_pattern)):
                parent = el.parent
                if parent and parent.name:
                    selector = self._build_selector(parent)
                    if selector:
                        return selector
        
        # Strategy 3: Common patterns for known field types
        common_patterns = {
            'price': ['.price', '[class*="price"]', '[itemprop="price"]'],
            'title': ['h1', 'h2', '.title', '[itemprop="name"]'],
            'image': ['img.product', '.product-image img', '[itemprop="image"]'],
        }
        
        for field, patterns in common_patterns.items():
            if field in self.name.lower():
                for pattern in patterns:
                    try:
                        elements = soup.select(pattern)
                        if elements and self._validate_elements(elements):
                            return pattern
                    except Exception:
                        continue
        
        # Strategy 4: AI-based detection (if available)
        if self.ai_extractor and self.ai_extractor.ai_provider:
            selectors = self.ai_extractor._find_selectors_with_ai(
                str(soup), [self.name]
            )
            if self.name in selectors:
                return selectors[self.name]
        
        return None
    
    def _build_selector(self, element) -> Optional[str]:
        """Build CSS selector from element"""
        # Use ID if available
        if element.get('id'):
            return f"#{element['id']}"
        
        # Use data attributes
        for attr in element.attrs:
            if attr.startswith('data-') and element[attr]:
                return f"[{attr}=\"{element[attr]}\"]"
        
        # Use class combination
        classes = element.get('class', [])
        if classes:
            selector = element.name + '.' + '.'.join(classes)
            return selector
        
        # Use itemprop
        if element.get('itemprop'):
            return f"[itemprop=\"{element['itemprop']}\"]"
        
        return None


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🧠 Scrapling Pro - AI Layout Detection")
    print("=" * 50)
    print("""
Usage:

    from ai_extractor import AIExtractor
    
    # With Claude API (recommended)
    extractor = AIExtractor(anthropic_api_key="sk-ant-...")
    
    # Or with OpenAI
    extractor = AIExtractor(openai_api_key="sk-...")
    
    # Or without API (heuristics only)
    extractor = AIExtractor()
    
    # Natural language extraction
    result = extractor.extract(
        html=page_html,
        prompt="Extract all products with name, price, and image"
    )
    
    print(f"Found {len(result.data)} items via {result.method}")
    
    # Auto-detect page type and extract
    result = extractor.auto_extract(html, url)
    
    # Find CSS selectors for custom scraper
    selectors = extractor.find_selectors(
        html=page_html,
        fields=["product_name", "price", "image", "rating"]
    )
    print(selectors)
    # {'product_name': '.product-title', 'price': '.price', ...}
    
Methods (in order of preference):
    1. Schema.org (JSON-LD, microdata) - fastest, most reliable
    2. Claude/OpenAI - best understanding, handles any layout
    3. Heuristics - free, offline, good for common patterns
    """)
