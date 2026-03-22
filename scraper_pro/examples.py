"""
🕷️ SCRAPLING PRO - Example Scripts
====================================
Ready-to-run examples demonstrating all features.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))


# ============================================================================
# EXAMPLE 1: Quick One-Liner Scraping
# ============================================================================

def example_quick_scrape():
    """
    The simplest way to scrape - one line of code.
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Quick One-Liner Scraping")
    print("="*60)
    
    from core.engine import quick_scrape
    
    items = quick_scrape(
        url="https://books.toscrape.com",
        item_selector="article.product_pod",
        fields={
            "title": "h3 a @title",    # Get title attribute
            "price": ".price_color",    # Get text content
            "rating": ".star-rating @class",  # Get class attribute
        }
    )
    
    print(f"\nScraped {len(items)} items:")
    for item in items[:5]:
        print(f"  📚 {item.title[:40]}: {item.content.get('price')}")
    
    return items


# ============================================================================
# EXAMPLE 2: Using Templates
# ============================================================================

def example_templates():
    """
    Use pre-built templates for common site types.
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Using Templates")
    print("="*60)
    
    from core.templates import EcommerceScraper, list_templates
    
    # List available templates
    print("\nAvailable templates:")
    for t in list_templates():
        print(f"  • {t['name']}: {t['description']}")
    
    # Use e-commerce template
    print("\nUsing EcommerceScraper...")
    scraper = EcommerceScraper(rate_limit=0.5)
    items = scraper.scrape("https://books.toscrape.com")
    
    print(f"\nScraped {len(items)} products:")
    for item in items[:5]:
        print(f"  📦 {item.title[:35]}: {item.content.get('price')}")
    
    return items


# ============================================================================
# EXAMPLE 3: Pagination
# ============================================================================

def example_pagination():
    """
    Scrape multiple pages with automatic pagination.
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Pagination")
    print("="*60)
    
    from core.templates import EcommerceScraper
    
    scraper = EcommerceScraper(rate_limit=0.5)
    
    # Scrape 3 pages
    items = scraper.scrape_paginated(
        start_url="https://books.toscrape.com",
        url_pattern="/catalogue/page-{}.html",
        max_pages=3
    )
    
    print(f"\nScraped {len(items)} products across 3 pages")
    
    return items


# ============================================================================
# EXAMPLE 4: Concurrent Scraping
# ============================================================================

def example_concurrent():
    """
    Scrape multiple URLs in parallel using thread pools.
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Concurrent Scraping")
    print("="*60)
    
    from core.async_scraper import ConcurrentScraper, URLGenerators
    from core.templates import EcommerceScraper
    
    # Generate URLs
    urls = list(URLGenerators.pagination(
        "https://books.toscrape.com",
        "/catalogue/page-{}.html",
        start=1,
        end=3
    ))
    
    print(f"Scraping {len(urls)} URLs concurrently...")
    
    # Create scraper and parser
    template = EcommerceScraper()
    concurrent = ConcurrentScraper(max_workers=3, rate_limit=0.5)
    
    # Scrape with progress
    items = concurrent.scrape_urls(
        urls,
        template.parse,
        progress_callback=lambda p: print(f"\r  Progress: {p}", end="")
    )
    
    print(f"\n\nScraped {len(items)} items total")
    
    return items


# ============================================================================
# EXAMPLE 5: Custom Scraper
# ============================================================================

def example_custom():
    """
    Build a custom scraper with your own selectors.
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: Custom Scraper")
    print("="*60)
    
    from core.templates import CustomScraper
    
    # Define your own selectors
    scraper = CustomScraper(
        container="article.product_pod",
        fields={
            "title": "h3 a @title",
            "price": ".price_color",
            "stock": ".instock",
            "link": "h3 a @href",
        },
        title_field="title"
    )
    
    items = scraper.scrape("https://books.toscrape.com")
    
    print(f"\nScraped {len(items)} items with custom selectors:")
    for item in items[:3]:
        print(f"  📖 {item.title[:35]}")
        print(f"     Price: {item.content.get('price')}")
        print(f"     Link: {item.content.get('link')}")
    
    return items


# ============================================================================
# EXAMPLE 6: Export Data
# ============================================================================

def example_export(items=None):
    """
    Export scraped data to various formats.
    """
    print("\n" + "="*60)
    print("EXAMPLE 6: Export Data")
    print("="*60)
    
    from core.engine import Exporter
    from core.templates import EcommerceScraper
    
    # Get some data if not provided
    if not items:
        scraper = EcommerceScraper(rate_limit=0.5)
        items = scraper.scrape("https://books.toscrape.com")
    
    # Export to different formats
    print(f"\nExporting {len(items)} items...")
    
    Exporter.to_csv(items, "output_example.csv")
    Exporter.to_json(items, "output_example.json")
    
    try:
        Exporter.to_excel(items, "output_example.xlsx")
    except:
        print("  (Excel export requires openpyxl)")
    
    print("\n  Files created:")
    print("    📄 output_example.csv")
    print("    📄 output_example.json")
    print("    📄 output_example.xlsx")


# ============================================================================
# EXAMPLE 7: Adaptive Selectors
# ============================================================================

def example_adaptive():
    """
    Use adaptive selectors that survive website changes.
    """
    print("\n" + "="*60)
    print("EXAMPLE 7: Adaptive Selectors")
    print("="*60)
    
    from scrapling.fetchers import StealthyFetcher
    
    # Enable adaptive mode
    StealthyFetcher.adaptive = True
    
    print("\nAdaptive selectors save element fingerprints and can")
    print("relocate elements even after website redesigns.")
    
    print("\nUsage:")
    print("  # First run - save fingerprints:")
    print("  products = page.css('.product', auto_save=True)")
    print()
    print("  # After site changes - find elements by similarity:")
    print("  products = page.css('.product', adaptive=True)")
    
    # Demo
    page = StealthyFetcher.fetch("https://books.toscrape.com")
    products = page.css("article.product_pod", auto_save=True)
    
    print(f"\n✓ Saved fingerprints for {len(products)} elements")
    print("  These can be relocated even if class names change!")


# ============================================================================
# EXAMPLE 8: JavaScript Rendering
# ============================================================================

def example_dynamic():
    """
    Scrape JavaScript-heavy sites with DynamicFetcher.
    """
    print("\n" + "="*60)
    print("EXAMPLE 8: JavaScript Rendering")
    print("="*60)
    
    try:
        from scrapling.fetchers import DynamicFetcher
        
        print("\nDynamicFetcher uses a real browser (Playwright) for:")
        print("  • JavaScript rendering")
        print("  • Single Page Applications (SPAs)")
        print("  • Infinite scroll")
        print("  • Form filling and clicking")
        
        print("\nFetching with JavaScript rendering...")
        
        page = DynamicFetcher.fetch(
            "https://books.toscrape.com",
            headless=True,
            network_idle=True,
            timeout=30000
        )
        
        products = page.css("article.product_pod")
        print(f"✓ Found {len(products)} products with JS rendering")
        
        print("\nAdvanced options:")
        print("  • wait_selector='#content' - Wait for element")
        print("  • js_code='...' - Execute custom JavaScript")
        print("  • network_idle=True - Wait for network to settle")
        
    except ImportError:
        print("\n⚠️ DynamicFetcher not available")
        print("   Run: scrapling install")


# ============================================================================
# EXAMPLE 9: Proxy Usage
# ============================================================================

def example_proxy():
    """
    Use proxies for scraping.
    """
    print("\n" + "="*60)
    print("EXAMPLE 9: Proxy Usage")
    print("="*60)
    
    print("\nProxy configuration examples:")
    
    print("\n  1. Simple proxy list:")
    print("""
    from core.engine import ScrapingEngine
    
    engine = ScrapingEngine(
        proxies=[
            "http://user:pass@proxy1.com:8080",
            "http://user:pass@proxy2.com:8080",
        ],
        proxy_rotation="weighted"  # or "round_robin", "random"
    )
    """)
    
    print("\n  2. Advanced proxy management:")
    print("""
    from core.proxy_manager import AdvancedProxyManager
    
    manager = AdvancedProxyManager(
        proxies=["http://..."],
        strategy="weighted",
        health_check_interval=300,  # 5 min
    )
    
    proxy = manager.get_proxy(country="US", sticky=True)
    manager.report_success(proxy, response_time=1.2)
    """)
    
    print("\n  Rotation strategies:")
    print("    • round_robin - Cycle through proxies")
    print("    • random - Random selection")
    print("    • weighted - Prefer better performing proxies")
    print("    • least_used - Prefer less used proxies")


# ============================================================================
# EXAMPLE 10: Full Pipeline
# ============================================================================

def example_full_pipeline():
    """
    Complete scraping pipeline with all features.
    """
    print("\n" + "="*60)
    print("EXAMPLE 10: Full Pipeline")
    print("="*60)
    
    from core.engine import ScrapingEngine, Exporter
    from core.templates import EcommerceScraper
    from core.async_scraper import ConcurrentScraper, URLGenerators
    
    print("\nBuilding a complete scraping pipeline...")
    
    # 1. Generate URLs
    print("\n1. Generating URLs...")
    urls = list(URLGenerators.pagination(
        "https://books.toscrape.com",
        "/catalogue/page-{}.html",
        start=1,
        end=2
    ))
    print(f"   Generated {len(urls)} URLs")
    
    # 2. Create scraper with configuration
    print("\n2. Configuring scraper...")
    concurrent = ConcurrentScraper(
        max_workers=2,
        mode="stealthy",
        rate_limit=0.5,
        max_retries=3,
    )
    print("   Mode: stealthy")
    print("   Workers: 2")
    print("   Rate limit: 0.5 req/s")
    
    # 3. Create parser
    template = EcommerceScraper()
    
    # 4. Scrape
    print("\n3. Scraping...")
    items = concurrent.scrape_urls(
        urls,
        template.parse,
        progress_callback=lambda p: print(f"\r   {p}", end="")
    )
    print()
    
    # 5. Export
    print(f"\n4. Exporting {len(items)} items...")
    Exporter.to_json(items, "pipeline_output.json")
    Exporter.to_csv(items, "pipeline_output.csv")
    
    # 6. Summary
    print("\n5. Summary:")
    print(f"   ✓ URLs scraped: {len(urls)}")
    print(f"   ✓ Items extracted: {len(items)}")
    print(f"   ✓ Files created: pipeline_output.json, pipeline_output.csv")
    
    return items


# ============================================================================
# MAIN - Run All Examples
# ============================================================================

def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   🕷️  SCRAPLING PRO - Example Scripts                        ║
    ║                                                               ║
    ║   Demonstrating all features and capabilities                 ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    examples = [
        ("1", "Quick One-Liner", example_quick_scrape),
        ("2", "Using Templates", example_templates),
        ("3", "Pagination", example_pagination),
        ("4", "Concurrent Scraping", example_concurrent),
        ("5", "Custom Scraper", example_custom),
        ("6", "Export Data", example_export),
        ("7", "Adaptive Selectors", example_adaptive),
        ("8", "JavaScript Rendering", example_dynamic),
        ("9", "Proxy Usage", example_proxy),
        ("10", "Full Pipeline", example_full_pipeline),
        ("all", "Run All Examples", None),
    ]
    
    print("Available examples:")
    for num, name, _ in examples:
        print(f"  {num}. {name}")
    
    print()
    choice = input("Enter example number (or 'all'): ").strip()
    
    if choice == "all":
        for num, name, func in examples[:-1]:
            if func:
                try:
                    func()
                except Exception as e:
                    print(f"\n❌ Error in example {num}: {e}")
            input("\nPress Enter for next example...")
    else:
        for num, name, func in examples:
            if num == choice and func:
                try:
                    func()
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                break
        else:
            print(f"Unknown example: {choice}")
    
    print("\n" + "="*60)
    print("Examples complete! 🎉")
    print("="*60)


if __name__ == "__main__":
    main()
