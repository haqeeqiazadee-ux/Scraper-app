"""
🤖 AI-ENHANCED INTELLIGENT SCRAPER
===================================
Uses AI (GPT/Gemini/Claude/Ollama) to intelligently extract product data.

The AI analyzes the HTML structure and extracts ALL relevant product information
without needing hardcoded selectors.

Supported AI Providers:
1. OpenAI GPT-4/GPT-3.5 (OPENAI_API_KEY)
2. Google Gemini (GOOGLE_API_KEY) - Free tier available!
3. Anthropic Claude (ANTHROPIC_API_KEY)
4. Ollama (Free, local) - No API key needed

Usage:
    # Set your API key
    set OPENAI_API_KEY=sk-xxx
    # Or
    set GOOGLE_API_KEY=xxx
    
    # Run
    python ai_scraper.py https://myshop.pk/laptops-desktops-computers/laptops

Author: Scrapling Pro
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("AI_Scraper")

# ============================================================================
# AI PROVIDERS
# ============================================================================

class AIProvider:
    """Base class for AI providers"""
    
    def extract(self, html: str, url: str, task: str = "products") -> dict:
        raise NotImplementedError


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.available = bool(self.api_key)
        
        if self.available:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info(f"✅ OpenAI initialized (model: {model})")
            except ImportError:
                logger.warning("OpenAI package not installed. Run: pip install openai")
                self.available = False
    
    def extract(self, html: str, url: str, task: str = "products") -> dict:
        if not self.available:
            return {"error": "OpenAI not available"}
        
        import openai
        
        # Truncate HTML to fit context window
        html_truncated = html[:50000] if len(html) > 50000 else html
        
        prompt = self._build_prompt(html_truncated, url, task)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return {"error": str(e)}
    
    def _get_system_prompt(self) -> str:
        return """You are an expert web scraping AI. Your job is to analyze HTML and extract ALL product information.

You MUST return valid JSON with this structure:
{
    "page_type": "category" or "product",
    "products": [
        {
            "name": "Product name",
            "sku": "Product SKU/ID",
            "price": "Current price with currency",
            "original_price": "Original price if on sale",
            "discount": "Discount percentage",
            "description": "Product description/specs",
            "brand": "Brand name",
            "category": "Product category",
            "rating": "Rating value",
            "reviews_count": "Number of reviews",
            "stock_status": "In stock/Out of stock",
            "image_url": "Main image URL",
            "product_url": "Link to product page",
            "specifications": {"key": "value"},
            "features": ["feature1", "feature2"],
            "delivery_info": "Delivery information"
        }
    ],
    "pagination": {
        "current_page": 1,
        "total_pages": 10,
        "next_page_url": "URL to next page"
    }
}

Extract EVERY piece of information you can find. Be thorough!
If a field is not found, use null instead of omitting it."""
    
    def _build_prompt(self, html: str, url: str, task: str) -> str:
        return f"""Analyze this e-commerce page and extract ALL product information.

URL: {url}
Task: Extract {task}

HTML Content:
```html
{html}
```

Instructions:
1. Identify if this is a category/listing page or a single product page
2. Extract ALL product information visible on the page
3. Include prices, SKUs, descriptions, specifications, images, etc.
4. Return as JSON format

Return the JSON response:"""


class GeminiProvider(AIProvider):
    """Google Gemini provider (FREE tier available!)"""
    
    def __init__(self, api_key: str = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.available = bool(self.api_key)
        
        if self.available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(model)
                logger.info(f"✅ Google Gemini initialized (model: {model})")
            except ImportError:
                logger.warning("Google Generative AI not installed. Run: pip install google-generativeai")
                self.available = False
    
    def extract(self, html: str, url: str, task: str = "products") -> dict:
        if not self.available:
            return {"error": "Gemini not available"}
        
        # Truncate HTML
        html_truncated = html[:100000] if len(html) > 100000 else html
        
        prompt = f"""You are an expert web scraping AI. Analyze this e-commerce HTML and extract ALL product information.

URL: {url}

Return ONLY valid JSON with this structure:
{{
    "page_type": "category" or "product",
    "products": [
        {{
            "name": "Product name",
            "sku": "SKU/Product ID",
            "price": "Current price",
            "original_price": "Original price if on sale",
            "discount": "Discount %",
            "description": "Description/specs",
            "brand": "Brand",
            "category": "Category",
            "rating": "Rating",
            "reviews_count": "Review count",
            "stock_status": "Stock status",
            "image_url": "Image URL",
            "product_url": "Product page URL",
            "specifications": {{"spec_name": "spec_value"}},
            "features": ["feature1", "feature2"],
            "delivery_info": "Delivery info"
        }}
    ],
    "pagination": {{
        "current_page": 1,
        "total_pages": null,
        "next_page_url": null
    }}
}}

Extract EVERY product and ALL their details. Be thorough!

HTML:
```html
{html_truncated}
```

Return ONLY the JSON, no other text:"""

        try:
            response = self.client.generate_content(prompt)
            
            # Extract JSON from response
            text = response.text
            
            # Clean up response - find JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            result = json.loads(text.strip())
            return result
            
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return {"error": str(e)}


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider"""
    
    def __init__(self, api_key: str = None, model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.available = bool(self.api_key)
        
        if self.available:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"✅ Claude initialized (model: {model})")
            except ImportError:
                logger.warning("Anthropic package not installed. Run: pip install anthropic")
                self.available = False
    
    def extract(self, html: str, url: str, task: str = "products") -> dict:
        if not self.available:
            return {"error": "Claude not available"}
        
        html_truncated = html[:80000] if len(html) > 80000 else html
        
        prompt = f"""Analyze this e-commerce HTML and extract ALL product information.

URL: {url}

Return ONLY valid JSON with this structure:
{{
    "page_type": "category" or "product",
    "products": [
        {{
            "name": "Product name",
            "sku": "SKU",
            "price": "Price",
            "original_price": "Original price",
            "discount": "Discount",
            "description": "Description",
            "brand": "Brand",
            "rating": "Rating",
            "stock_status": "Stock",
            "image_url": "Image",
            "product_url": "URL",
            "specifications": {{}},
            "features": []
        }}
    ]
}}

HTML:
{html_truncated}

JSON response:"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            
            text = response.content[0].text
            
            # Clean up
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
            
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return {"error": str(e)}


class OllamaProvider(AIProvider):
    """Ollama provider (FREE, runs locally!)"""
    
    def __init__(self, model: str = "llama3.2", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self.available = self._check_available()
        
        if self.available:
            logger.info(f"✅ Ollama initialized (model: {model})")
    
    def _check_available(self) -> bool:
        try:
            import requests
            response = requests.get(f"{self.host}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def extract(self, html: str, url: str, task: str = "products") -> dict:
        if not self.available:
            return {"error": "Ollama not available. Start Ollama first: ollama serve"}
        
        import requests
        
        # Truncate for local models
        html_truncated = html[:30000] if len(html) > 30000 else html
        
        prompt = f"""Extract product information from this HTML as JSON.

URL: {url}

Return JSON format:
{{"page_type": "category/product", "products": [{{"name": "", "sku": "", "price": "", "description": "", "image_url": "", "product_url": ""}}]}}

HTML:
{html_truncated}

JSON:"""

        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=120
            )
            
            result = response.json()
            text = result.get("response", "{}")
            
            return json.loads(text)
            
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return {"error": str(e)}


# ============================================================================
# AI-ENHANCED SCRAPER
# ============================================================================

class AIEnhancedScraper:
    """
    AI-powered web scraper that uses LLMs to intelligently extract data.
    
    Features:
    - Auto-detects page type (category vs product)
    - Extracts ALL product information
    - No hardcoded selectors - AI figures it out!
    - Supports multiple AI providers
    - Falls back to heuristics if AI unavailable
    """
    
    def __init__(
        self,
        provider: str = "auto",
        timeout: int = 60000,
        openai_key: str = None,
        google_key: str = None,
        anthropic_key: str = None,
    ):
        self.timeout = timeout
        self.products = []
        
        # Initialize AI providers
        self.providers = {}
        self._init_providers(provider, openai_key, google_key, anthropic_key)
        
        # Select active provider
        self.active_provider = self._select_provider(provider)
        
        if self.active_provider:
            logger.info(f"🤖 Using AI provider: {self.active_provider.__class__.__name__}")
        else:
            logger.warning("⚠️ No AI provider available. Will use heuristic extraction.")
    
    def _init_providers(self, provider: str, openai_key, google_key, anthropic_key):
        """Initialize all available AI providers"""
        
        # Try OpenAI
        try:
            self.providers['openai'] = OpenAIProvider(api_key=openai_key)
        except Exception as e:
            logger.debug(f"OpenAI init failed: {e}")
        
        # Try Gemini (FREE!)
        try:
            self.providers['gemini'] = GeminiProvider(api_key=google_key)
        except Exception as e:
            logger.debug(f"Gemini init failed: {e}")
        
        # Try Claude
        try:
            self.providers['claude'] = ClaudeProvider(api_key=anthropic_key)
        except Exception as e:
            logger.debug(f"Claude init failed: {e}")
        
        # Try Ollama (FREE, local)
        try:
            self.providers['ollama'] = OllamaProvider()
        except Exception as e:
            logger.debug(f"Ollama init failed: {e}")
    
    def _select_provider(self, preference: str) -> Optional[AIProvider]:
        """Select the best available AI provider"""
        
        if preference != "auto" and preference in self.providers:
            provider = self.providers[preference]
            if provider.available:
                return provider
        
        # Auto-select: prefer Gemini (free), then OpenAI, then Claude, then Ollama
        priority = ['gemini', 'openai', 'claude', 'ollama']
        
        for name in priority:
            if name in self.providers and self.providers[name].available:
                return self.providers[name]
        
        return None
    
    def fetch(self, url: str):
        """Fetch page using Scrapling"""
        from scrapling.fetchers import StealthyFetcher
        
        logger.info(f"🌐 Fetching: {url}")
        page = StealthyFetcher.fetch(
            url,
            timeout=self.timeout,
            network_idle=True
        )
        logger.info(f"✅ Status: {page.status}")
        return page
    
    def get_html(self, page) -> str:
        """Extract HTML content from page"""
        if hasattr(page, 'html_content'):
            return page.html_content
        elif hasattr(page, 'body'):
            body = page.body
            if isinstance(body, bytes):
                return body.decode('utf-8', errors='ignore')
            return str(body)
        else:
            return str(page)
    
    def scrape(self, url: str) -> List[dict]:
        """Main scrape method using AI extraction"""
        
        # Fetch page
        page = self.fetch(url)
        html = self.get_html(page)
        
        logger.info(f"📄 HTML size: {len(html):,} characters")
        
        # Extract using AI
        if self.active_provider:
            logger.info("🤖 Extracting with AI...")
            result = self.active_provider.extract(html, url, "products")
            
            if "error" not in result:
                page_type = result.get("page_type", "unknown")
                products = result.get("products", [])
                
                logger.info(f"📄 Page type: {page_type}")
                logger.info(f"📦 Products found: {len(products)}")
                
                # Clean up products
                self.products = self._clean_products(products, url)
                return self.products
            else:
                logger.warning(f"AI extraction failed: {result['error']}")
        
        # Fallback to heuristic extraction
        logger.info("🔧 Falling back to heuristic extraction...")
        self.products = self._heuristic_extract(page, url)
        return self.products
    
    def _clean_products(self, products: List[dict], base_url: str) -> List[dict]:
        """Clean and normalize product data"""
        from urllib.parse import urljoin
        
        cleaned = []
        for p in products:
            if not p:
                continue
            
            product = {}
            
            # Map fields with various possible names
            field_mappings = {
                'name': ['name', 'title', 'product_name', 'productName'],
                'sku': ['sku', 'product_id', 'productId', 'id', 'item_id'],
                'price': ['price', 'current_price', 'sale_price', 'finalPrice'],
                'original_price': ['original_price', 'regular_price', 'was_price', 'oldPrice'],
                'discount': ['discount', 'discount_percent', 'savings'],
                'description': ['description', 'short_description', 'specs', 'summary'],
                'brand': ['brand', 'manufacturer', 'vendor'],
                'category': ['category', 'categories', 'breadcrumb'],
                'rating': ['rating', 'stars', 'review_rating', 'averageRating'],
                'reviews_count': ['reviews_count', 'review_count', 'numReviews'],
                'stock_status': ['stock_status', 'availability', 'in_stock', 'stock'],
                'image_url': ['image_url', 'image', 'thumbnail', 'main_image', 'imageUrl'],
                'product_url': ['product_url', 'url', 'link', 'href', 'productUrl'],
                'specifications': ['specifications', 'specs', 'attributes', 'details'],
                'features': ['features', 'highlights', 'key_features'],
                'delivery_info': ['delivery_info', 'shipping', 'delivery', 'shipping_info'],
            }
            
            for target_field, source_fields in field_mappings.items():
                for source in source_fields:
                    if source in p and p[source]:
                        value = p[source]
                        
                        # Handle URLs
                        if target_field in ['image_url', 'product_url'] and value:
                            if isinstance(value, str) and not value.startswith('http'):
                                value = urljoin(base_url, value)
                        
                        # Handle specifications dict
                        if target_field == 'specifications' and isinstance(value, dict):
                            value = json.dumps(value)
                        
                        # Handle features list
                        if target_field == 'features' and isinstance(value, list):
                            value = ', '.join(str(f) for f in value)
                        
                        product[target_field] = value
                        break
            
            # Only add if we have at least a name
            if product.get('name'):
                cleaned.append(product)
        
        return cleaned
    
    def _heuristic_extract(self, page, url: str) -> List[dict]:
        """Fallback heuristic extraction when AI is unavailable"""
        from smart_scraper import IntelligentProductScraper
        
        scraper = IntelligentProductScraper(timeout=self.timeout)
        scraper.products = []
        
        # Detect page type and extract
        page_type = scraper.detect_page_type(page)
        
        if page_type == "category":
            return scraper.extract_from_category_page(page)
        else:
            product = scraper.extract_from_product_page(page, url)
            return [product] if product.get('name') else []
    
    def export(self, filename: str = "ai_scraped_products.xlsx"):
        """Export products to Excel"""
        if not self.products:
            logger.warning("❌ No products to export")
            return None
        
        from smart_exporter import SmartExcelExporter
        
        exporter = SmartExcelExporter()
        result = exporter.export(
            self.products,
            filename,
            add_summary=True,
            highlight_deals=True
        )
        
        if result:
            import os
            size = os.path.getsize(result)
            logger.info(f"✅ Exported {len(self.products)} products to {result} ({size:,} bytes)")
        
        return result


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    print("=" * 70)
    print("🤖 AI-ENHANCED INTELLIGENT SCRAPER")
    print("=" * 70)
    
    # Check for API keys
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_gemini = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    has_claude = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    print("\n📋 AI Providers Status:")
    print(f"   OpenAI:  {'✅ Key found' if has_openai else '❌ Set OPENAI_API_KEY'}")
    print(f"   Gemini:  {'✅ Key found' if has_gemini else '❌ Set GOOGLE_API_KEY (FREE!)'}")
    print(f"   Claude:  {'✅ Key found' if has_claude else '❌ Set ANTHROPIC_API_KEY'}")
    print(f"   Ollama:  🔍 Checking local...")
    
    # Get URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://myshop.pk/laptops-desktops-computers/laptops"
    
    print(f"\n🎯 Target: {url}\n")
    print("-" * 70)
    
    # Create scraper
    scraper = AIEnhancedScraper(provider="auto")
    
    # Scrape
    products = scraper.scrape(url)
    
    print(f"\n{'='*70}")
    print(f"📊 RESULTS: {len(products)} products extracted")
    print("=" * 70)
    
    if products:
        # Show sample
        print("\n📦 Sample products:")
        print("-" * 70)
        
        for i, p in enumerate(products[:5], 1):
            print(f"\n{i}. {p.get('name', 'Unknown')[:60]}")
            if p.get('sku'):
                print(f"   SKU: {p['sku']}")
            if p.get('price'):
                print(f"   Price: {p['price']}")
            if p.get('original_price'):
                print(f"   Was: {p['original_price']}")
            if p.get('description'):
                desc = p['description']
                if isinstance(desc, str):
                    print(f"   Specs: {desc[:80]}...")
            if p.get('brand'):
                print(f"   Brand: {p['brand']}")
            if p.get('rating'):
                print(f"   Rating: {p['rating']}")
        
        if len(products) > 5:
            print(f"\n... and {len(products) - 5} more products")
        
        # Export
        print(f"\n{'='*70}")
        scraper.export("ai_scraped_products.xlsx")
        print("=" * 70)
    else:
        print("\n❌ No products found")
        print("\n💡 Tips:")
        print("   1. Set an API key: set GOOGLE_API_KEY=your_key (Gemini is FREE!)")
        print("   2. Or install Ollama: https://ollama.ai")
        print("   3. Check if the URL is correct")


if __name__ == "__main__":
    main()
