"""
🕷️ Scrapling Pro - Professional Web Scraping Toolkit
=====================================================

A comprehensive, production-ready web scraping framework with:
- 🎯 Smart Templates - Pre-built scrapers for e-commerce, news, jobs, social
- 🔄 Proxy Rotation - Advanced proxy management with health checking
- ⚡ Concurrent Scraping - Thread pools and async support
- 🛡️ Anti-Bot Bypass - Cloudflare, fingerprinting, stealth mode
- 🧬 Adaptive Selectors - Survives website redesigns automatically
- 🧠 Smart Extractors - Intelligent fallback chains for data extraction
- 🎯 Vertical Scrapers - E-commerce, Influencer, Trend Analysis

Quick Start:
    from scraper_pro import quick_scrape, EcommerceScraper
    
    # One-liner scraping
    items = quick_scrape(
        url="https://books.toscrape.com",
        item_selector="article.product_pod",
        fields={"title": "h3 a @title", "price": ".price_color"}
    )
    
    # Template-based scraping
    scraper = EcommerceScraper()
    products = scraper.scrape("https://shop.com/products")

Vertical APIs:
    from scraper_pro import get_verticals
    
    v = get_verticals()
    
    # E-Commerce Intelligence
    product = v.ecommerce.scrape_product(url)
    comparison = v.ecommerce.compare_competitors([url1, url2])
    
    # Influencer Research
    profile = v.influencer.analyze_instagram("username")
    
    # Trend Analysis
    report = v.trends.analyze(["keyword1", "keyword2"])
"""

__version__ = "2.0.0"
__author__ = "Scrapling Pro"

# ============================================================================
# CORE ENGINE
# ============================================================================

from .engine import (
    ScrapingEngine,
    ScrapedItem,
    ProxyConfig,
    ProxyManager,
    Exporter,
    Parsers,
    quick_scrape,
)

# ============================================================================
# TEMPLATES
# ============================================================================

try:
    from .templates import (
        BaseScraper,
        EcommerceScraper,
        AmazonScraper,
        ShopifyScraper,
        NewsScraper,
        JobScraper,
        SocialMediaScraper,
        RealEstateScraper,
        CustomScraper,
    )
except ImportError:
    # Templates may have additional dependencies
    pass

# ============================================================================
# SMART EXTRACTORS (with fallback chains)
# ============================================================================

try:
    from .core import (
        # Fallback utilities
        FallbackChain,
        ToolResult,
        SmartFallback,
        check_tool_availability,
        print_availability,
        
        # Data structures
        ProductData,
        SentimentResult,
        TrendData,
        InfluencerProfile,
        
        # Extractors
        SmartProductExtractor,
        SmartSentimentAnalyzer,
        SmartTrendAnalyzer,
        SmartInfluencerAnalyzer,
        SmartExtractors,
        
        # Convenience functions
        get_extractors,
        extract_product,
        analyze_sentiment,
        analyze_trends,
    )
except ImportError as e:
    # Core extractors need Phase 1 dependencies
    import logging
    logging.debug(f"Smart extractors not available: {e}")

# ============================================================================
# VERTICAL SCRAPERS
# ============================================================================

try:
    from .verticals import (
        # E-Commerce
        EcommerceVertical,
        CompetitorProduct,
        PriceAlert,
        
        # Influencer
        InfluencerVertical,
        InfluencerComparison,
        
        # Trends
        TrendVertical,
        TrendReport,
        
        # Unified API
        ScraplingProVerticals,
        get_verticals,
    )
except ImportError as e:
    # Verticals need smart extractors
    import logging
    logging.debug(f"Vertical scrapers not available: {e}")

# ============================================================================
# INTEGRATIONS (Optional)
# ============================================================================

try:
    from .integrations import (
        ProductSchemaExtractor,
        PriceExtractor,
        TrendAnalyzer,
        ReviewAnalyzer,
        SEOAnalyzer,
        ShopifyIntegration,
        WooCommerceIntegration,
        TaxCalculator,
        check_integrations,
    )
except ImportError:
    # Integrations have many optional dependencies
    pass

# ============================================================================
# ASYNC & CONCURRENT
# ============================================================================

try:
    from .async_scraper import (
        ConcurrentScraper,
        BatchProcessor,
        URLGenerators,
    )
except ImportError:
    pass

# ============================================================================
# PROXY MANAGEMENT
# ============================================================================

try:
    from .proxy_manager import (
        AdvancedProxyManager,
        ProxyProvider,
        FileProxyProvider,
        APIProxyProvider,
    )
except ImportError:
    pass

# ============================================================================
# CLI & DASHBOARD
# ============================================================================

# These are typically run as scripts, not imported
# python cli.py scrape https://example.com
# python web_dashboard.py

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Version
    "__version__",
    
    # Core
    "ScrapingEngine",
    "ScrapedItem",
    "ProxyConfig",
    "ProxyManager",
    "Exporter",
    "Parsers",
    "quick_scrape",
    
    # Templates
    "BaseScraper",
    "EcommerceScraper",
    "AmazonScraper",
    "ShopifyScraper",
    "NewsScraper",
    "JobScraper",
    "SocialMediaScraper",
    "RealEstateScraper",
    "CustomScraper",
    
    # Smart Extractors
    "FallbackChain",
    "SmartProductExtractor",
    "SmartSentimentAnalyzer",
    "SmartTrendAnalyzer",
    "SmartInfluencerAnalyzer",
    "SmartExtractors",
    "get_extractors",
    "extract_product",
    "analyze_sentiment",
    "analyze_trends",
    "print_availability",
    
    # Data structures
    "ProductData",
    "SentimentResult",
    "TrendData",
    "InfluencerProfile",
    
    # Verticals
    "EcommerceVertical",
    "InfluencerVertical",
    "TrendVertical",
    "ScraplingProVerticals",
    "get_verticals",
    
    # Async
    "ConcurrentScraper",
    "BatchProcessor",
    "URLGenerators",
    
    # Proxy
    "AdvancedProxyManager",
]
