"""
🤖 SCRAPLING PRO - AI-POWERED INTELLIGENT SCRAPER v3.0
========================================================
Uses Google Gemini AI (FREE!) to intelligently extract ALL product data.

Features:
- AI analyzes HTML and extracts ALL product information
- Works on ANY e-commerce site - no hardcoded selectors
- Auto-detects category pages vs product pages
- Extracts: name, SKU, price, specs, images, ratings, stock, etc.
- Smart pagination handling
- Excel export with actual URLs

Usage:
    python ai_scraper_v3.py https://example.com/products
    python ai_scraper_v3.py https://example.com/product/item-123

Author: Scrapling Pro
Version: 3.0
"""

import os
import sys
import json
import re
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("AI_Scraper")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Google Gemini API Key (FREE tier - 60 requests/minute)
# Get your own FREE key at: https://aistudio.google.com/apikey
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""

# AI Model Configuration - Multiple models for fallback
GEMINI_MODELS = [
    "gemini-1.5-flash",      # Primary - fast and reliable
    "gemini-1.5-flash-8b",   # Backup - lighter model
    "gemini-2.0-flash",      # Alternative
]
MAX_HTML_LENGTH = 100000  # Max HTML chars to send to AI
AI_TEMPERATURE = 0.1  # Low temperature for consistent extraction
MAX_RETRIES = 3  # Retry on rate limit
RETRY_DELAY = 30  # Seconds to wait between retries


# ============================================================================
# GEMINI AI CLIENT
# ============================================================================

class GeminiAI:
    """
    Google Gemini AI client for intelligent data extraction.
    Uses the FREE tier - 15 requests/minute, 1500 requests/day.
    
    Features:
    - Automatic retry on rate limits
    - Model fallback (tries multiple models)
    - Smart error handling
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.models = GEMINI_MODELS
        self.current_model_idx = 0
        self.client = None
        self.available = False
        
        if not self.api_key:
            logger.error("❌ No Gemini API key provided!")
            logger.error("   Get your FREE key at: https://aistudio.google.com/apikey")
            logger.error("   Then set: GOOGLE_API_KEY=your_key_here")
            return
        
        self._initialize()
    
    @property
    def model(self):
        return self.models[self.current_model_idx]
    
    def _initialize(self):
        """Initialize Gemini client"""
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self.use_new_api = True
            logger.info(f"✅ Gemini AI initialized (model: {self.model})")
            self.available = True
        except ImportError:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai
                self.use_new_api = False
                logger.info(f"✅ Gemini AI initialized [legacy] (model: {self.model})")
                self.available = True
            except ImportError:
                logger.error("❌ Google AI not installed. Run: pip install google-genai")
                self.available = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            self.available = False
    
    def _try_next_model(self):
        """Switch to next model in fallback list"""
        self.current_model_idx = (self.current_model_idx + 1) % len(self.models)
        logger.info(f"🔄 Switching to model: {self.model}")
    
    def extract_products(self, html: str, url: str) -> dict:
        """
        Use AI to extract ALL product information from HTML.
        Includes automatic retry and model fallback.
        """
        if not self.available:
            return {"error": "Gemini AI not available - check API key", "products": []}
        
        # Truncate HTML if too long
        if len(html) > MAX_HTML_LENGTH:
            html = html[:MAX_HTML_LENGTH//2] + "\n...[TRUNCATED]...\n" + html[-MAX_HTML_LENGTH//2:]
        
        prompt = self._build_extraction_prompt(html, url)
        
        # Try with retries
        for attempt in range(MAX_RETRIES):
            try:
                if self.use_new_api:
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=prompt
                    )
                    text = response.text
                else:
                    model = self.client.GenerativeModel(self.model)
                    response = model.generate_content(prompt)
                    text = response.text
                
                # Success! Parse and return
                result = self._parse_json_response(text)
                return result
                
            except Exception as e:
                error_str = str(e)
                
                # Rate limit error - retry after delay
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    if attempt < MAX_RETRIES - 1:
                        # Try different model first
                        self._try_next_model()
                        
                        wait_time = RETRY_DELAY * (attempt + 1)
                        logger.warning(f"⏳ Rate limited. Waiting {wait_time}s before retry {attempt + 2}/{MAX_RETRIES}...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"❌ Rate limit exceeded after {MAX_RETRIES} retries")
                        return {"error": "Rate limit exceeded. Please wait and try again.", "products": []}
                
                # Other error
                logger.error(f"❌ AI extraction error: {e}")
                return {"error": str(e), "products": []}
    
    def _build_extraction_prompt(self, html: str, url: str) -> str:
        """Build the extraction prompt for Gemini"""
        return f"""You are an expert web scraping AI. Analyze this e-commerce HTML and extract ALL product information.

URL: {url}

IMPORTANT INSTRUCTIONS:
1. Identify if this is a CATEGORY page (multiple products) or a PRODUCT page (single product details)
2. Extract EVERY piece of product information you can find
3. For category pages: extract ALL products shown
4. For product pages: extract ALL details including specifications
5. Return ONLY valid JSON, no other text

REQUIRED JSON FORMAT:
{{
    "page_type": "category" or "product",
    "products": [
        {{
            "name": "Full product name/title",
            "sku": "Product SKU, model number, or ID",
            "price": "Current/sale price with currency symbol",
            "original_price": "Original price before discount (if on sale)",
            "discount": "Discount percentage or amount",
            "currency": "Currency code (PKR, USD, etc)",
            "description": "Product description or short specs",
            "full_description": "Complete product description",
            "brand": "Brand/manufacturer name",
            "category": "Product category or breadcrumb path",
            "subcategory": "Subcategory if available",
            "rating": "Rating value (e.g., 4.5)",
            "rating_max": "Maximum rating (e.g., 5)",
            "reviews_count": "Number of reviews",
            "stock_status": "In Stock, Out of Stock, Limited, etc",
            "stock_quantity": "Quantity available if shown",
            "image_url": "Main product image URL (full URL)",
            "additional_images": ["URL1", "URL2"],
            "product_url": "Link to product detail page (full URL)",
            "specifications": {{
                "Processor": "Intel Core i5",
                "RAM": "8GB",
                "Storage": "256GB SSD"
            }},
            "features": ["Feature 1", "Feature 2"],
            "delivery_info": "Delivery/shipping information",
            "warranty": "Warranty information",
            "seller": "Seller name if marketplace",
            "condition": "New, Used, Refurbished",
            "tags": ["tag1", "tag2"],
            "meta": {{
                "any_other_info": "value"
            }}
        }}
    ],
    "pagination": {{
        "current_page": 1,
        "total_pages": null,
        "total_products": null,
        "next_page_url": "URL to next page if available",
        "has_more": true
    }},
    "extraction_notes": "Any notes about the extraction"
}}

RULES:
- Extract ALL products visible on the page
- Include complete URLs (not relative paths)
- Include all specifications found
- If a field is not found, use null
- For prices, include the currency symbol
- Be thorough - extract every detail

HTML CONTENT:
```html
{html}
```

Return ONLY the JSON response, no markdown or explanation:"""

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from AI response"""
        try:
            # Clean up response
            text = text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            
            if text.endswith("```"):
                text = text[:-3]
            
            text = text.strip()
            
            # Parse JSON
            result = json.loads(text)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Response text: {text[:500]}...")
            return {"error": f"JSON parse error: {e}", "products": []}


# ============================================================================
# AI-POWERED SCRAPER
# ============================================================================

class AIScraperV3:
    """
    Ultimate AI-powered web scraper.
    
    Features:
    - Uses Google Gemini AI (FREE!) for intelligent extraction
    - No hardcoded selectors - AI figures out the structure
    - Works on ANY e-commerce website
    - Extracts ALL product information
    - Handles both category pages and product pages
    - Smart pagination support
    """
    
    def __init__(self, timeout: int = 60000):
        self.timeout = timeout
        self.ai = GeminiAI()
        self.products = []
        self.stats = {
            "pages_scraped": 0,
            "products_found": 0,
            "ai_calls": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    def fetch(self, url: str):
        """Fetch page using Scrapling with stealth mode"""
        from scrapling.fetchers import StealthyFetcher
        
        logger.info(f"🌐 Fetching: {url}")
        
        page = StealthyFetcher.fetch(
            url,
            timeout=self.timeout,
            network_idle=True
        )
        
        logger.info(f"✅ Status: {page.status}")
        self.stats["pages_scraped"] += 1
        
        return page
    
    def get_html(self, page) -> str:
        """Extract HTML content from page object"""
        # Try different methods to get HTML
        if hasattr(page, 'html_content') and page.html_content:
            return page.html_content
        
        if hasattr(page, 'body'):
            body = page.body
            if isinstance(body, bytes):
                return body.decode('utf-8', errors='ignore')
            return str(body)
        
        # Try to get from page source
        if hasattr(page, 'page_source'):
            return page.page_source
        
        return str(page)
    
    def scrape(self, url: str, follow_pagination: bool = False, max_pages: int = 10) -> List[dict]:
        """
        Main scraping method.
        
        Args:
            url: URL to scrape
            follow_pagination: Whether to follow pagination links
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of product dictionaries
        """
        self.stats["start_time"] = datetime.now()
        self.products = []
        
        logger.info("=" * 70)
        logger.info("🤖 AI-POWERED SCRAPING STARTED")
        logger.info("=" * 70)
        
        pages_scraped = 0
        current_url = url
        
        while current_url and pages_scraped < max_pages:
            pages_scraped += 1
            logger.info(f"\n📄 Page {pages_scraped}: {current_url}")
            
            try:
                # Fetch page
                page = self.fetch(current_url)
                html = self.get_html(page)
                
                logger.info(f"📊 HTML size: {len(html):,} characters")
                
                products = []
                
                # Try AI extraction first
                if self.ai.available:
                    logger.info("🤖 Analyzing with AI...")
                    self.stats["ai_calls"] += 1
                    
                    result = self.ai.extract_products(html, current_url)
                    
                    if "error" not in result or not result["error"]:
                        page_type = result.get("page_type", "unknown")
                        products = result.get("products", [])
                        
                        logger.info(f"📄 Page type: {page_type}")
                        logger.info(f"📦 Products found by AI: {len(products)}")
                        
                        # Check for pagination
                        if follow_pagination and not products:
                            pagination = result.get("pagination", {})
                            next_url = pagination.get("next_page_url")
                            
                            if next_url and next_url != current_url:
                                current_url = self._make_absolute_url(next_url, current_url)
                                logger.info(f"➡️ Next page: {current_url}")
                                time.sleep(1)
                                continue
                    else:
                        logger.warning(f"⚠️ AI extraction issue: {result.get('error', 'Unknown')}")
                
                # Fallback to heuristic extraction if AI didn't work
                if not products:
                    logger.info("🔧 Using heuristic extraction as fallback...")
                    products = self._heuristic_extract(page, current_url)
                    logger.info(f"📦 Products found by heuristics: {len(products)}")
                
                # Clean and add products
                if products:
                    cleaned = self._clean_products(products, current_url)
                    self.products.extend(cleaned)
                    self.stats["products_found"] += len(cleaned)
                else:
                    self.stats["errors"] += 1
                
                # No more pages
                current_url = None
                
            except Exception as e:
                logger.error(f"❌ Error scraping {current_url}: {e}")
                self.stats["errors"] += 1
                current_url = None
        
        self.stats["end_time"] = datetime.now()
        
        # Log summary
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        logger.info("\n" + "=" * 70)
        logger.info("📊 SCRAPING COMPLETE")
        logger.info("=" * 70)
        logger.info(f"   Pages scraped: {self.stats['pages_scraped']}")
        logger.info(f"   Products found: {self.stats['products_found']}")
        logger.info(f"   AI calls made: {self.stats['ai_calls']}")
        logger.info(f"   Errors: {self.stats['errors']}")
        logger.info(f"   Duration: {duration:.1f} seconds")
        
        return self.products
    
    def _clean_products(self, products: List[dict], base_url: str) -> List[dict]:
        """Clean and normalize product data"""
        cleaned = []
        
        for p in products:
            if not p or not isinstance(p, dict):
                continue
            
            product = {}
            
            # Direct field mappings
            direct_fields = [
                'name', 'sku', 'price', 'original_price', 'discount', 'currency',
                'description', 'full_description', 'brand', 'category', 'subcategory',
                'rating', 'rating_max', 'reviews_count', 'stock_status', 'stock_quantity',
                'image_url', 'product_url', 'delivery_info', 'warranty', 'seller',
                'condition'
            ]
            
            for field in direct_fields:
                if field in p and p[field] is not None:
                    value = p[field]
                    
                    # Make URLs absolute
                    if field in ['image_url', 'product_url'] and value:
                        value = self._make_absolute_url(value, base_url)
                    
                    product[field] = value
            
            # Handle specifications (dict)
            if 'specifications' in p and isinstance(p['specifications'], dict):
                specs = p['specifications']
                # Flatten specs into individual columns
                for key, value in specs.items():
                    if value:
                        clean_key = f"spec_{self._clean_key(key)}"
                        product[clean_key] = str(value)
                # Also keep as JSON
                product['specifications_json'] = json.dumps(specs)
            
            # Handle features (list)
            if 'features' in p and isinstance(p['features'], list):
                product['features'] = ', '.join(str(f) for f in p['features'] if f)
            
            # Handle additional images
            if 'additional_images' in p and isinstance(p['additional_images'], list):
                images = [self._make_absolute_url(img, base_url) for img in p['additional_images'] if img]
                product['additional_images'] = ', '.join(images[:5])  # Max 5 images
            
            # Handle tags
            if 'tags' in p and isinstance(p['tags'], list):
                product['tags'] = ', '.join(str(t) for t in p['tags'] if t)
            
            # Handle meta (additional data)
            if 'meta' in p and isinstance(p['meta'], dict):
                for key, value in p['meta'].items():
                    if value:
                        clean_key = f"meta_{self._clean_key(key)}"
                        product[clean_key] = str(value)
            
            # Only add if we have at least a name or SKU
            if product.get('name') or product.get('sku'):
                # Add extraction metadata
                product['_source_url'] = base_url
                product['_extracted_at'] = datetime.now().isoformat()
                cleaned.append(product)
        
        return cleaned
    
    def _make_absolute_url(self, url: str, base_url: str) -> str:
        """Convert relative URL to absolute"""
        if not url:
            return ""
        if url.startswith(('http://', 'https://')):
            return url
        return urljoin(base_url, url)
    
    def _clean_key(self, key: str) -> str:
        """Clean a key name for use as column header"""
        # Replace spaces and special chars
        key = re.sub(r'[^a-zA-Z0-9]', '_', key.lower())
        # Remove multiple underscores
        key = re.sub(r'_+', '_', key)
        # Remove leading/trailing underscores
        return key.strip('_')
    
    def _heuristic_extract(self, page, url: str) -> List[dict]:
        """
        Fallback heuristic extraction when AI is not available.
        Uses common CSS selectors for e-commerce sites.
        """
        products = []
        
        # Common product container selectors
        container_selectors = [
            '.product', '.product-item', '.product-card', '.product-box',
            '[class*="product"]', '[data-product]',
            '.item', '.card', '.listing-item',
            'article.product_pod',  # books.toscrape.com
            '.grid-item', '.col-product',
        ]
        
        # Try each selector
        for selector in container_selectors:
            try:
                items = page.css(selector)
                if len(items) >= 2:  # Found multiple products
                    logger.info(f"   Found {len(items)} items with selector: {selector}")
                    
                    for item in items[:100]:  # Max 100 products
                        product = self._extract_product_from_element(item, url)
                        if product.get('name'):
                            products.append(product)
                    
                    if products:
                        break
            except Exception as e:
                continue
        
        return products
    
    def _extract_product_from_element(self, element, base_url: str) -> dict:
        """Extract product data from a single element"""
        product = {}
        
        # Name selectors
        name_selectors = ['h2', 'h3', 'h4', '.name', '.title', '.product-name', '.product-title', 'a[title]']
        for sel in name_selectors:
            try:
                els = element.css(sel)
                if els:
                    text = els[0].text.strip() if hasattr(els[0], 'text') else ""
                    if text and len(text) > 2:
                        product['name'] = text[:200]
                        break
            except:
                continue
        
        # Price selectors
        price_selectors = ['.price', '.product-price', '.current-price', '.sale-price', '[class*="price"]']
        for sel in price_selectors:
            try:
                els = element.css(sel)
                if els:
                    text = els[0].text.strip() if hasattr(els[0], 'text') else ""
                    if text and any(c.isdigit() for c in text):
                        product['price'] = text
                        break
            except:
                continue
        
        # Image
        try:
            imgs = element.css('img')
            if imgs:
                src = imgs[0].attrib.get('src') or imgs[0].attrib.get('data-src', '')
                if src:
                    product['image_url'] = self._make_absolute_url(src, base_url)
        except:
            pass
        
        # URL
        try:
            links = element.css('a')
            if links:
                href = links[0].attrib.get('href', '')
                if href and '/product' in href.lower() or '.html' in href:
                    product['product_url'] = self._make_absolute_url(href, base_url)
        except:
            pass
        
        # Rating
        try:
            rating_els = element.css('[class*="rating"], [class*="star"]')
            if rating_els:
                # Try to extract rating from class name (e.g., "star-rating Three")
                classes = rating_els[0].attrib.get('class', '')
                for word in ['One', 'Two', 'Three', 'Four', 'Five']:
                    if word in classes:
                        product['rating'] = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}[word]
                        break
        except:
            pass
        
        return product
    
    def export(self, filename: str = "ai_products.xlsx") -> Optional[str]:
        """Export scraped products to Excel"""
        if not self.products:
            logger.warning("❌ No products to export")
            return None
        
        try:
            from smart_exporter import SmartExcelExporter
            
            exporter = SmartExcelExporter()
            result = exporter.export(
                self.products,
                filename,
                sheet_name="Products",
                add_summary=True,
                highlight_deals=True
            )
            
            if result:
                import os
                size = os.path.getsize(result)
                logger.info(f"✅ Exported {len(self.products)} products to {result} ({size:,} bytes)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Export error: {e}")
            return None
    
    def export_json(self, filename: str = "ai_products.json") -> Optional[str]:
        """Export products to JSON"""
        if not self.products:
            logger.warning("❌ No products to export")
            return None
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.products, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Exported {len(self.products)} products to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ JSON export error: {e}")
            return None


# ============================================================================
# CLI INTERFACE
# ============================================================================

def print_banner():
    """Print ASCII banner"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🤖 SCRAPLING PRO - AI-POWERED INTELLIGENT SCRAPER v3.0            ║
║                                                                      ║
║   Powered by Google Gemini AI (FREE!)                               ║
║   Extract ALL product data from ANY e-commerce site                 ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)


def print_product_sample(products: List[dict], max_show: int = 5):
    """Print sample of extracted products"""
    print("\n📦 SAMPLE PRODUCTS:")
    print("-" * 70)
    
    for i, p in enumerate(products[:max_show], 1):
        print(f"\n{i}. {p.get('name', 'Unknown')[:65]}")
        
        if p.get('sku'):
            print(f"   SKU: {p['sku']}")
        
        if p.get('price'):
            price_str = f"   Price: {p['price']}"
            if p.get('original_price'):
                price_str += f" (was: {p['original_price']})"
            print(price_str)
        
        if p.get('brand'):
            print(f"   Brand: {p['brand']}")
        
        if p.get('description'):
            desc = str(p['description'])[:80]
            print(f"   Desc: {desc}...")
        
        # Show some specs if available
        specs = [k for k in p.keys() if k.startswith('spec_')]
        if specs:
            print(f"   Specs: {', '.join(specs[:3])}...")
        
        if p.get('rating'):
            print(f"   Rating: {p['rating']}")
        
        if p.get('stock_status'):
            print(f"   Stock: {p['stock_status']}")
    
    if len(products) > max_show:
        print(f"\n... and {len(products) - max_show} more products")


def main():
    """Main entry point"""
    print_banner()
    
    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("\n" + "=" * 70)
        print("⚠️  NO API KEY FOUND")
        print("=" * 70)
        print("\nTo use AI-powered extraction, you need a FREE Google API key.")
        print("\n📋 How to get your FREE key (30 seconds):")
        print("   1. Go to: https://aistudio.google.com/apikey")
        print("   2. Sign in with Google")
        print("   3. Click 'Create API Key'")
        print("   4. Copy the key")
        print("\n📋 Then set the key:")
        print("   Windows: set GOOGLE_API_KEY=your_key_here")
        print("   Linux:   export GOOGLE_API_KEY=your_key_here")
        print("\n" + "-" * 70)
        
        # Prompt for key
        try:
            api_key = input("\n🔑 Enter your API key (or press Enter to skip): ").strip()
            if api_key:
                os.environ["GOOGLE_API_KEY"] = api_key
                print("✅ API key set for this session")
            else:
                print("\n⚠️  Continuing without AI. Will use heuristic extraction.")
        except:
            pass
    
    # Get URL from arguments
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default test URL
        url = "https://books.toscrape.com"
        print(f"\nℹ️  No URL provided, using default: {url}")
    
    print(f"\n🎯 Target URL: {url}")
    
    # Check for options
    follow_pagination = "--paginate" in sys.argv or "-p" in sys.argv
    
    if follow_pagination:
        print("📄 Pagination: ENABLED (will follow next page links)")
    
    print("\n" + "=" * 70)
    
    # Create scraper and run
    scraper = AIScraperV3(timeout=60000)
    
    # Check AI availability
    if not scraper.ai.available:
        print("\n⚠️  AI not available. Using heuristic extraction instead.")
        print("   For best results, set up your API key as shown above.")
    
    # Scrape
    products = scraper.scrape(url, follow_pagination=follow_pagination)
    
    # Show results
    if products:
        print_product_sample(products)
        
        # Export
        print("\n" + "=" * 70)
        print("📊 EXPORTING...")
        print("-" * 70)
        
        excel_file = scraper.export("ai_products.xlsx")
        json_file = scraper.export_json("ai_products.json")
        
        print("\n" + "=" * 70)
        print("✅ DONE!")
        print("=" * 70)
        
        if excel_file:
            print(f"   📊 Excel: {excel_file}")
        if json_file:
            print(f"   📄 JSON:  {json_file}")
        
        print(f"\n   Total products extracted: {len(products)}")
        
    else:
        print("\n❌ No products were extracted.")
        print("   This could be because:")
        print("   1. Rate limit exceeded - wait 1 minute and try again")
        print("   2. No API key set - see instructions above")
        print("   3. The page structure is unusual")
        print("   4. The URL is incorrect")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
