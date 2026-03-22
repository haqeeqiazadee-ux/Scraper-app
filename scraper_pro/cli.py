#!/usr/bin/env python3
"""
🕷️ SCRAPLING PRO - Command Line Interface
==========================================

Usage:
    python cli.py scrape <url> --template ecommerce --pages 5 --output products.xlsx
    python cli.py templates
    python cli.py test <url>
    python cli.py dashboard
"""

import argparse
import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from core.engine import ScrapingEngine, Exporter, quick_scrape
from core.templates import (
    TEMPLATES, list_templates, EcommerceScraper, NewsScraper,
    JobScraper, CustomScraper
)


def cmd_scrape(args):
    """Run a scraping job"""
    print(f"🕷️ Scraping: {args.url}")
    print(f"   Template: {args.template}")
    print(f"   Mode: {args.mode}")
    print(f"   Pages: {args.pages}")
    print()
    
    # Get template
    template_class = TEMPLATES.get(args.template)
    if not template_class:
        print(f"❌ Unknown template: {args.template}")
        print("   Use 'python cli.py templates' to see available templates")
        return 1
    
    # Create scraper
    engine_kwargs = {
        'mode': args.mode,
        'rate_limit': args.rate_limit,
        'max_retries': args.retries,
    }
    
    if args.proxy:
        engine_kwargs['proxies'] = [args.proxy]
    
    scraper = template_class(**engine_kwargs)
    
    # Scrape
    if args.pages > 1 and args.pagination:
        items = scraper.scrape_paginated(
            args.url,
            url_pattern=args.pagination,
            max_pages=args.pages
        )
    else:
        items = scraper.scrape(args.url)
    
    print(f"\n✅ Scraped {len(items)} items")
    
    # Show preview
    if items and not args.quiet:
        print("\nPreview (first 5 items):")
        for i, item in enumerate(items[:5], 1):
            print(f"  {i}. {item.title[:50]}..." if len(item.title) > 50 else f"  {i}. {item.title}")
    
    # Export
    if args.output:
        output_path = Path(args.output)
        if output_path.suffix == '.json':
            Exporter.to_json(items, args.output)
        elif output_path.suffix == '.xlsx':
            Exporter.to_excel(items, args.output)
        else:
            Exporter.to_csv(items, args.output)
    
    return 0


def cmd_templates(args):
    """List available templates"""
    print("🕷️ Available Scraping Templates")
    print("=" * 50)
    
    for t in list_templates():
        print(f"\n  📦 {t['name']}")
        print(f"     Class: {t['class']}")
        print(f"     {t['description']}")
    
    print("\n" + "=" * 50)
    print("Usage: python cli.py scrape <url> --template <name>")
    return 0


def cmd_test(args):
    """Test a URL"""
    print(f"🔍 Testing: {args.url}")
    
    try:
        from scrapling.fetchers import StealthyFetcher
        
        page = StealthyFetcher.fetch(args.url, timeout=15)
        
        print(f"\n✅ Status: {page.status}")
        
        # Get title
        title_els = page.css('title')
        if title_els:
            print(f"   Title: {title_els[0].text}")
        
        # Count elements
        print(f"\n   Elements found:")
        for selector in ['article', '.product', '.item', 'a', 'img']:
            count = len(page.css(selector))
            if count > 0:
                print(f"     {selector}: {count}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


def cmd_dashboard(args):
    """Start the web dashboard"""
    print("🕷️ Starting Web Dashboard...")
    
    try:
        from web_dashboard import main
        main()
    except ImportError:
        print("❌ Flask not installed. Run: pip install flask")
        return 1
    
    return 0


def cmd_quick(args):
    """Quick scrape with custom selectors"""
    print(f"🕷️ Quick Scrape: {args.url}")
    print(f"   Container: {args.container}")
    print(f"   Fields: {args.fields}")
    
    try:
        fields = json.loads(args.fields)
    except json.JSONDecodeError:
        print("❌ Invalid JSON for fields")
        return 1
    
    items = quick_scrape(
        url=args.url,
        item_selector=args.container,
        fields=fields,
        mode=args.mode,
    )
    
    print(f"\n✅ Scraped {len(items)} items")
    
    for i, item in enumerate(items[:10], 1):
        print(f"  {i}. {item.title}")
    
    if args.output:
        output_path = Path(args.output)
        if output_path.suffix == '.json':
            Exporter.to_json(items, args.output)
        elif output_path.suffix == '.xlsx':
            Exporter.to_excel(items, args.output)
        else:
            Exporter.to_csv(items, args.output)
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="🕷️ Scrapling Pro - Professional Web Scraping CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py scrape https://books.toscrape.com --template ecommerce
  python cli.py scrape https://shop.com --pages 5 --pagination "?page={}" --output products.xlsx
  python cli.py templates
  python cli.py test https://example.com
  python cli.py dashboard
  python cli.py quick https://site.com --container ".item" --fields '{"title": "h2", "price": ".cost"}'
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape a website')
    scrape_parser.add_argument('url', help='URL to scrape')
    scrape_parser.add_argument('-t', '--template', default='ecommerce',
                               choices=list(TEMPLATES.keys()),
                               help='Scraping template to use')
    scrape_parser.add_argument('-m', '--mode', default='stealthy',
                               choices=['stealthy', 'dynamic'],
                               help='Fetcher mode')
    scrape_parser.add_argument('-p', '--pages', type=int, default=1,
                               help='Number of pages to scrape')
    scrape_parser.add_argument('--pagination', default='',
                               help='Pagination URL pattern (use {} for page number)')
    scrape_parser.add_argument('-o', '--output', help='Output file path')
    scrape_parser.add_argument('--proxy', help='Proxy URL')
    scrape_parser.add_argument('--rate-limit', type=float, default=1.0,
                               help='Requests per second')
    scrape_parser.add_argument('--retries', type=int, default=3,
                               help='Max retries per request')
    scrape_parser.add_argument('-q', '--quiet', action='store_true',
                               help='Suppress preview output')
    
    # Templates command
    templates_parser = subparsers.add_parser('templates', help='List available templates')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test a URL')
    test_parser.add_argument('url', help='URL to test')
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Start web dashboard')
    
    # Quick command
    quick_parser = subparsers.add_parser('quick', help='Quick scrape with custom selectors')
    quick_parser.add_argument('url', help='URL to scrape')
    quick_parser.add_argument('-c', '--container', required=True,
                              help='CSS selector for item container')
    quick_parser.add_argument('-f', '--fields', required=True,
                              help='JSON object mapping field names to selectors')
    quick_parser.add_argument('-m', '--mode', default='stealthy',
                              choices=['stealthy', 'dynamic'])
    quick_parser.add_argument('-o', '--output', help='Output file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Route to command
    commands = {
        'scrape': cmd_scrape,
        'templates': cmd_templates,
        'test': cmd_test,
        'dashboard': cmd_dashboard,
        'quick': cmd_quick,
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
