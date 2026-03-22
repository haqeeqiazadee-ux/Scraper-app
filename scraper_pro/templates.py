"""
🕷️ SCRAPLING PRO - Scraping Templates
=======================================
Ready-to-use templates for common scraping scenarios.
"""

from typing import List, Dict, Callable, Any, Optional
from dataclasses import dataclass
import json
import re

# Import from core
try:
    from .engine import ScrapingEngine, ScrapedItem, Exporter, Parsers, logger
except ImportError:
    from engine import ScrapingEngine, ScrapedItem, Exporter, Parsers
    import logging
    logger = logging.getLogger("ScraplingPro")


# ============================================================================
# BASE TEMPLATE
# ============================================================================

class ScraperTemplate:
    """Base class for scraper templates"""
    
    name: str = "Base Template"
    description: str = "Override this"
    
    def __init__(self, **engine_kwargs):
        self.engine = ScrapingEngine(**engine_kwargs)
        self.items: List[ScrapedItem] = []
    
    def parse(self, page) -> List[ScrapedItem]:
        """Override this method"""
        raise NotImplementedError
    
    def scrape(self, url: str, **kwargs) -> List[ScrapedItem]:
        """Scrape a single URL"""
        self.items = self.engine.scrape_url(url, self.parse, **kwargs)
        return self.items
    
    def scrape_many(self, urls: List[str], concurrent: bool = True) -> List[ScrapedItem]:
        """Scrape multiple URLs"""
        self.items = self.engine.scrape_urls(urls, self.parse, concurrent=concurrent)
        return self.items
    
    def scrape_paginated(
        self, 
        start_url: str, 
        url_pattern: str = "?page={}",
        max_pages: int = 10,
        **kwargs
    ) -> List[ScrapedItem]:
        """Scrape with pagination"""
        self.items = self.engine.scrape_with_pagination(
            start_url, self.parse, "url", url_pattern, max_pages=max_pages, **kwargs
        )
        return self.items
    
    def export(self, filepath: str, format: str = "auto"):
        """Export results"""
        if format == "auto":
            if filepath.endswith(".json"):
                format = "json"
            elif filepath.endswith(".xlsx"):
                format = "excel"
            else:
                format = "csv"
        
        if format == "json":
            Exporter.to_json(self.items, filepath)
        elif format == "excel":
            Exporter.to_excel(self.items, filepath)
        else:
            Exporter.to_csv(self.items, filepath)


# ============================================================================
# E-COMMERCE TEMPLATES
# ============================================================================

class EcommerceScraper(ScraperTemplate):
    """
    E-Commerce Product Scraper
    --------------------------
    Scrapes product listings from online stores.
    
    Works with: Amazon-style, Shopify, WooCommerce, custom stores
    
    Example:
        scraper = EcommerceScraper()
        items = scraper.scrape("https://shop.example.com/products")
        scraper.export("products.xlsx")
    """
    
    name = "E-Commerce Scraper"
    description = "Scrape products, prices, images, ratings"
    
    # Customize these selectors for your target site
    SELECTORS = {
        "container": [
            "article.product_pod", ".product-card", ".product-item",
            ".product", "[data-product]", ".item", ".listing"
        ],
        "title": ["h2", "h3", ".title", ".name", ".product-name", "h3 a"],
        "price": [".price", ".price_color", ".cost", ".amount", "[data-price]"],
        "image": ["img"],
        "rating": [".rating", ".star-rating", ".stars", "[class*='star']"],
        "description": [".description", ".desc", ".summary", "p"],
        "link": ["a"],
    }
    
    def parse(self, page) -> List[ScrapedItem]:
        items = []
        
        # Find product container
        products = []
        for selector in self.SELECTORS["container"]:
            products = page.css(selector)
            if products:
                break
        
        for product in products:
            item_data = {"url": str(page.url) if hasattr(page, 'url') else ""}
            
            # Extract title
            title = ""
            for sel in self.SELECTORS["title"]:
                els = product.css(sel)
                if els:
                    title = els[0].attrib.get("title") or els[0].text or ""
                    title = title.strip()
                    if title:
                        break
            
            # Extract other fields
            content = {}
            
            for sel in self.SELECTORS["price"]:
                els = product.css(sel)
                if els:
                    content["price"] = els[0].text.strip()
                    break
            
            for sel in self.SELECTORS["image"]:
                els = product.css(sel)
                if els:
                    content["image"] = els[0].attrib.get("src") or els[0].attrib.get("data-src", "")
                    break
            
            for sel in self.SELECTORS["rating"]:
                els = product.css(sel)
                if els:
                    # Try to extract rating from class or text
                    rating_class = els[0].attrib.get("class", "")
                    content["rating"] = rating_class.split()[-1] if rating_class else els[0].text
                    break
            
            for sel in self.SELECTORS["link"]:
                els = product.css(sel)
                if els:
                    content["product_url"] = els[0].attrib.get("href", "")
                    break
            
            items.append(ScrapedItem(
                url=item_data["url"],
                title=title,
                content=content
            ))
        
        return items


class AmazonScraper(EcommerceScraper):
    """Amazon-specific scraper"""
    
    name = "Amazon Scraper"
    description = "Scrape Amazon product listings"
    
    SELECTORS = {
        "container": ["[data-component-type='s-search-result']", ".s-result-item"],
        "title": ["h2 a span", ".a-text-normal"],
        "price": [".a-price .a-offscreen", ".a-price-whole"],
        "image": [".s-image"],
        "rating": [".a-icon-star-small span", ".a-icon-alt"],
        "link": ["h2 a"],
        "reviews": [".a-size-small .a-link-normal"],
    }


class ShopifyScraper(EcommerceScraper):
    """Shopify store scraper"""
    
    name = "Shopify Scraper"
    description = "Scrape Shopify-based stores"
    
    SELECTORS = {
        "container": [".product-card", ".grid-product", ".product-item"],
        "title": [".product-card__title", ".grid-product__title", "h3"],
        "price": [".product-card__price", ".grid-product__price", ".price"],
        "image": [".product-card__image img", ".grid-product__image img", "img"],
        "link": ["a.product-card", "a.grid-product__link", "a"],
    }


# ============================================================================
# NEWS & ARTICLES
# ============================================================================

class NewsScraper(ScraperTemplate):
    """
    News Article Scraper
    --------------------
    Scrapes news headlines and article metadata.
    
    Example:
        scraper = NewsScraper()
        items = scraper.scrape("https://news.example.com")
    """
    
    name = "News Scraper"
    description = "Scrape news headlines, summaries, dates"
    
    SELECTORS = {
        "container": ["article", ".article", ".post", ".story", ".news-item", ".entry"],
        "title": ["h1", "h2", "h3", ".title", ".headline"],
        "summary": ["p", ".summary", ".excerpt", ".description", ".lead"],
        "author": [".author", ".byline", "[rel='author']", ".writer"],
        "date": ["time", ".date", ".published", ".timestamp", "[datetime]"],
        "link": ["a"],
        "category": [".category", ".tag", ".section"],
    }
    
    def parse(self, page) -> List[ScrapedItem]:
        items = []
        
        # Find articles
        articles = []
        for selector in self.SELECTORS["container"]:
            articles = page.css(selector)
            if articles:
                break
        
        for article in articles:
            # Extract title
            title = ""
            for sel in self.SELECTORS["title"]:
                els = article.css(sel)
                if els:
                    title = els[0].text.strip() if els[0].text else ""
                    if title:
                        break
            
            content = {}
            
            # Summary
            for sel in self.SELECTORS["summary"]:
                els = article.css(sel)
                if els:
                    text = els[0].text.strip() if els[0].text else ""
                    if text and len(text) > 20:  # Avoid short snippets
                        content["summary"] = text[:300]
                        break
            
            # Author
            for sel in self.SELECTORS["author"]:
                els = article.css(sel)
                if els:
                    content["author"] = els[0].text.strip() if els[0].text else ""
                    break
            
            # Date
            for sel in self.SELECTORS["date"]:
                els = article.css(sel)
                if els:
                    content["date"] = els[0].attrib.get("datetime") or (els[0].text.strip() if els[0].text else "")
                    break
            
            # Link
            for sel in self.SELECTORS["link"]:
                els = article.css(sel)
                if els:
                    content["link"] = els[0].attrib.get("href", "")
                    break
            
            if title:  # Only add if we found a title
                items.append(ScrapedItem(
                    url=str(page.url) if hasattr(page, 'url') else "",
                    title=title,
                    content=content
                ))
        
        return items


# ============================================================================
# JOB LISTINGS
# ============================================================================

class JobScraper(ScraperTemplate):
    """
    Job Listing Scraper
    -------------------
    Scrapes job postings from career sites.
    
    Example:
        scraper = JobScraper()
        items = scraper.scrape_paginated(
            "https://jobs.example.com/search",
            url_pattern="&page={}",
            max_pages=5
        )
    """
    
    name = "Job Scraper"
    description = "Scrape job titles, companies, salaries"
    
    SELECTORS = {
        "container": [
            ".job-card", ".job-listing", ".job", ".position",
            "[data-job]", ".search-result", ".job-result"
        ],
        "title": ["h2", "h3", ".title", ".job-title", ".position-title"],
        "company": [".company", ".employer", ".organization", ".company-name"],
        "location": [".location", ".job-location", ".city"],
        "salary": [".salary", ".compensation", ".pay", ".wage"],
        "job_type": [".job-type", ".employment-type", ".type"],
        "posted": [".posted", ".date", "time", ".posted-date"],
        "link": ["a"],
    }
    
    def parse(self, page) -> List[ScrapedItem]:
        items = []
        
        jobs = []
        for selector in self.SELECTORS["container"]:
            jobs = page.css(selector)
            if jobs:
                break
        
        for job in jobs:
            title = ""
            for sel in self.SELECTORS["title"]:
                els = job.css(sel)
                if els:
                    title = els[0].text.strip() if els[0].text else ""
                    if title:
                        break
            
            content = {}
            
            for field in ["company", "location", "salary", "job_type", "posted"]:
                for sel in self.SELECTORS.get(field, []):
                    els = job.css(sel)
                    if els:
                        content[field] = els[0].text.strip() if els[0].text else ""
                        break
            
            for sel in self.SELECTORS["link"]:
                els = job.css(sel)
                if els:
                    content["job_url"] = els[0].attrib.get("href", "")
                    break
            
            if title:
                items.append(ScrapedItem(
                    url=str(page.url) if hasattr(page, 'url') else "",
                    title=title,
                    content=content
                ))
        
        return items


# ============================================================================
# SOCIAL MEDIA
# ============================================================================

class SocialMediaScraper(ScraperTemplate):
    """
    Social Media Post Scraper
    -------------------------
    Scrapes posts from social platforms (public pages only).
    Requires DynamicFetcher for most sites.
    
    Example:
        scraper = SocialMediaScraper(mode="dynamic")
        items = scraper.scrape("https://twitter.com/username")
    """
    
    name = "Social Media Scraper"
    description = "Scrape posts, likes, timestamps"
    
    def __init__(self, **kwargs):
        kwargs.setdefault("mode", "dynamic")
        super().__init__(**kwargs)
    
    SELECTORS = {
        "container": [
            ".tweet", ".post", ".status", "[data-testid='tweet']",
            "article", ".feed-item", ".timeline-item"
        ],
        "author": [".author", ".username", ".user", "[data-testid='User-Name']"],
        "content": [".text", ".content", ".post-text", "[data-testid='tweetText']"],
        "timestamp": ["time", ".timestamp", ".date", "[datetime]"],
        "likes": [".likes", ".like-count", "[data-testid='like']"],
        "shares": [".shares", ".retweet-count", ".share-count"],
        "comments": [".comments", ".reply-count", ".comment-count"],
    }
    
    def parse(self, page) -> List[ScrapedItem]:
        items = []
        
        posts = []
        for selector in self.SELECTORS["container"]:
            posts = page.css(selector)
            if posts:
                break
        
        for post in posts:
            content_text = ""
            for sel in self.SELECTORS["content"]:
                els = post.css(sel)
                if els:
                    content_text = els[0].text.strip() if els[0].text else ""
                    if content_text:
                        break
            
            data = {}
            
            for field in ["author", "timestamp", "likes", "shares", "comments"]:
                for sel in self.SELECTORS.get(field, []):
                    els = post.css(sel)
                    if els:
                        if field == "timestamp":
                            data[field] = els[0].attrib.get("datetime") or (els[0].text.strip() if els[0].text else "")
                        else:
                            data[field] = els[0].text.strip() if els[0].text else ""
                        break
            
            if content_text:
                items.append(ScrapedItem(
                    url=str(page.url) if hasattr(page, 'url') else "",
                    title=data.get("author", "Unknown"),
                    content={"text": content_text, **data}
                ))
        
        return items


# ============================================================================
# REAL ESTATE
# ============================================================================

class RealEstateScraper(ScraperTemplate):
    """
    Real Estate Listing Scraper
    ---------------------------
    Scrapes property listings.
    
    Example:
        scraper = RealEstateScraper()
        items = scraper.scrape("https://zillow.com/homes/")
    """
    
    name = "Real Estate Scraper"
    description = "Scrape properties, prices, features"
    
    SELECTORS = {
        "container": [
            ".property-card", ".listing", ".property", ".home-card",
            "[data-test='property-card']", ".search-result"
        ],
        "address": [".address", ".property-address", ".location"],
        "price": [".price", ".list-price", ".property-price", "[data-test='property-card-price']"],
        "beds": [".beds", ".bedrooms", "[data-test='property-card-beds']"],
        "baths": [".baths", ".bathrooms", "[data-test='property-card-baths']"],
        "sqft": [".sqft", ".square-feet", ".area", "[data-test='property-card-sqft']"],
        "property_type": [".type", ".property-type"],
        "image": ["img"],
        "link": ["a"],
    }
    
    def parse(self, page) -> List[ScrapedItem]:
        items = []
        
        listings = []
        for selector in self.SELECTORS["container"]:
            listings = page.css(selector)
            if listings:
                break
        
        for listing in listings:
            address = ""
            for sel in self.SELECTORS["address"]:
                els = listing.css(sel)
                if els:
                    address = els[0].text.strip() if els[0].text else ""
                    if address:
                        break
            
            content = {}
            
            for field in ["price", "beds", "baths", "sqft", "property_type"]:
                for sel in self.SELECTORS.get(field, []):
                    els = listing.css(sel)
                    if els:
                        content[field] = els[0].text.strip() if els[0].text else ""
                        break
            
            for sel in self.SELECTORS["image"]:
                els = listing.css(sel)
                if els:
                    content["image"] = els[0].attrib.get("src") or els[0].attrib.get("data-src", "")
                    break
            
            for sel in self.SELECTORS["link"]:
                els = listing.css(sel)
                if els:
                    content["listing_url"] = els[0].attrib.get("href", "")
                    break
            
            if address:
                items.append(ScrapedItem(
                    url=str(page.url) if hasattr(page, 'url') else "",
                    title=address,
                    content=content
                ))
        
        return items


# ============================================================================
# CUSTOM TEMPLATE BUILDER
# ============================================================================

class CustomScraper(ScraperTemplate):
    """
    Custom Scraper Builder
    ----------------------
    Build a scraper by defining selectors.
    
    Example:
        scraper = CustomScraper(
            container=".product",
            fields={
                "title": "h2",
                "price": ".cost",
                "image": "img @src",  # @attr for attributes
            }
        )
        items = scraper.scrape("https://example.com")
    """
    
    name = "Custom Scraper"
    description = "User-defined selectors"
    
    def __init__(
        self,
        container: str,
        fields: Dict[str, str],
        title_field: str = "title",
        **engine_kwargs
    ):
        super().__init__(**engine_kwargs)
        self.container = container
        self.fields = fields
        self.title_field = title_field
    
    def parse(self, page) -> List[ScrapedItem]:
        items = []
        
        for element in page.css(self.container):
            content = {}
            title = ""
            
            for field_name, selector in self.fields.items():
                # Check for attribute extraction (e.g., "img @src")
                if " @" in selector:
                    sel, attr = selector.rsplit(" @", 1)
                    els = element.css(sel)
                    value = els[0].attrib.get(attr, "") if els else ""
                else:
                    els = element.css(selector)
                    value = els[0].text.strip() if els and els[0].text else ""
                
                if field_name == self.title_field:
                    title = value
                else:
                    content[field_name] = value
            
            items.append(ScrapedItem(
                url=str(page.url) if hasattr(page, 'url') else "",
                title=title,
                content=content
            ))
        
        return items


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

TEMPLATES = {
    "ecommerce": EcommerceScraper,
    "amazon": AmazonScraper,
    "shopify": ShopifyScraper,
    "news": NewsScraper,
    "jobs": JobScraper,
    "social": SocialMediaScraper,
    "realestate": RealEstateScraper,
    "custom": CustomScraper,
}


def get_template(name: str) -> type:
    """Get a template class by name"""
    return TEMPLATES.get(name.lower(), CustomScraper)


def list_templates() -> List[Dict]:
    """List all available templates"""
    return [
        {"name": name, "class": cls.name, "description": cls.description}
        for name, cls in TEMPLATES.items()
    ]


# ============================================================================
# MAIN - DEMO
# ============================================================================

if __name__ == "__main__":
    print("🕷️ Scrapling Pro - Templates")
    print("=" * 50)
    
    print("\nAvailable templates:")
    for t in list_templates():
        print(f"  • {t['name']}: {t['description']}")
    
    print("\n" + "=" * 50)
    print("Demo: E-Commerce Scraper")
    print("=" * 50)
    
    scraper = EcommerceScraper()
    items = scraper.scrape("https://books.toscrape.com")
    
    print(f"\nScraped {len(items)} products:")
    for item in items[:5]:
        print(f"  📦 {item.title[:40]}... - {item.content.get('price', 'N/A')}")
    
    scraper.export("products_demo.json")
