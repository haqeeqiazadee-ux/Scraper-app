#!/usr/bin/env python3
"""
Quick Test Script - Verify your scraper setup works
Run: python test_setup.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Test that all required packages are installed"""
    print("Testing imports...")
    
    # Core scrapling
    try:
        from scrapling.fetchers import Fetcher, StealthyFetcher
        print("  ✓ Scrapling core imported successfully")
    except ImportError as e:
        print(f"  ✗ Scrapling import failed: {e}")
        print("    Run: pip install scrapling[all]")
        return False
    
    # Dynamic/Browser mode
    try:
        from scrapling.fetchers import DynamicFetcher
        print("  ✓ DynamicFetcher imported (browser mode available)")
    except ImportError as e:
        print(f"  ⚠ DynamicFetcher not available: {e}")
        print("    Run: scrapling install")
        print("    (basic and stealthy modes still work)")
    
    # Excel support
    try:
        import openpyxl
        print("  ✓ openpyxl imported (Excel support available)")
    except ImportError:
        print("  ⚠ openpyxl not found (Excel export disabled, CSV still works)")
        print("    Optional: pip install openpyxl")
    
    return True


def test_integration_tools():
    """Test optional integration tools"""
    print("\nTesting integration tools (optional)...")
    
    tools = {
        'extruct': "Schema extraction (JSON-LD, microdata)",
        'price_parser': "Price parsing from any format",
        'vaderSentiment': "Sentiment analysis",
        'textblob': "NLP sentiment fallback",
        'pytrends': "Google Trends data",
        'instaloader': "Instagram scraping",
        'sklearn': "Machine learning (fraud detection)",
    }
    
    available = 0
    for module, description in tools.items():
        try:
            __import__(module.replace('_', ''))
            print(f"  ✓ {module}: {description}")
            available += 1
        except ImportError:
            # Try alternate import
            try:
                if module == 'sklearn':
                    import sklearn
                    print(f"  ✓ {module}: {description}")
                    available += 1
                    continue
            except ImportError:
                pass
            print(f"  ○ {module}: Not installed (optional)")
    
    print(f"\n  {available}/{len(tools)} integration tools available")
    
    if available < 3:
        print("\n  💡 To install all integrations:")
        print("     pip install extruct price-parser vaderSentiment textblob pytrends")
    
    return True  # Optional tools don't fail the test


def test_basic_fetch():
    """Test a simple fetch using StealthyFetcher (recommended)"""
    print("\nTesting basic fetch...")
    
    from scrapling.fetchers import StealthyFetcher
    
    try:
        page = StealthyFetcher.fetch("https://httpbin.org/html")
        
        if page.status == 200:
            print("  ✓ Basic fetch works!")
            # Try parsing - css() returns a list in scrapling
            try:
                h1_elements = page.css("h1")
                if h1_elements:
                    text = h1_elements[0].text if hasattr(h1_elements[0], 'text') else str(h1_elements[0])
                    print(f"  ✓ Parsing works! Found: {text[:50]}")
            except Exception as e:
                print(f"  ⚠ Parsing issue (fetch still works): {e}")
            return True
        else:
            print(f"  ✗ Fetch returned status {page.status}")
            return False
    except Exception as e:
        print(f"  ✗ Fetch failed: {e}")
        return False


def test_stealthy_fetch():
    """Test stealthy fetcher"""
    print("\nTesting stealthy fetch...")
    
    from scrapling.fetchers import StealthyFetcher
    
    try:
        page = StealthyFetcher.fetch("https://httpbin.org/headers")
        
        if page.status == 200:
            print("  ✓ Stealthy fetch works!")
            return True
        else:
            print(f"  ✗ Stealthy fetch returned status {page.status}")
            return False
    except Exception as e:
        print(f"  ✗ Stealthy fetch failed: {e}")
        return False


def test_dynamic_fetch():
    """Test Dynamic fetcher (browser mode)"""
    print("\nTesting dynamic fetch (browser mode)...")
    
    try:
        from scrapling.fetchers import DynamicFetcher
    except ImportError:
        print("  ⚠ DynamicFetcher not available (browser not installed)")
        print("    To enable: scrapling install")
        return None  # Neither pass nor fail
    
    try:
        page = DynamicFetcher.fetch("https://httpbin.org/html", headless=True)
        
        if page.status == 200:
            print("  ✓ Dynamic fetch works!")
            return True
        else:
            print(f"  ✗ Dynamic fetch returned status {page.status}")
            return False
    except Exception as e:
        print(f"  ⚠ Dynamic fetch unavailable: {e}")
        print("    To enable: scrapling install")
        return None


def test_export():
    """Test CSV export"""
    print("\nTesting export...")
    
    import os
    import tempfile
    
    try:
        from engine import ScrapedItem, Exporter
        
        test_items = [
            ScrapedItem(url="https://test.com", title="Test Item 1", content={"price": "$10"}),
            ScrapedItem(url="https://test.com", title="Test Item 2", content={"price": "$20"}),
        ]
        
        test_file = os.path.join(tempfile.gettempdir(), "test_export.csv")
        Exporter.to_csv(test_items, test_file)
        
        if os.path.exists(test_file):
            print(f"  ✓ CSV export works!")
            os.remove(test_file)
            return True
        else:
            print("  ✗ Export failed - file not created")
            return False
    except ImportError as e:
        print(f"  ⚠ Export test skipped (import issue): {e}")
        return None
    except Exception as e:
        print(f"  ✗ Export failed: {e}")
        return False


def main():
    print("=" * 60)
    print("SCRAPLING PRO - SETUP VERIFICATION")
    print("=" * 60)
    
    if not test_imports():
        print("\n❌ Import test failed. Please install missing packages.")
        sys.exit(1)
    
    # Test integration tools
    test_integration_tools()
    
    results = []
    results.append(("Basic Fetch", test_basic_fetch()))
    results.append(("Stealthy Fetch", test_stealthy_fetch()))
    results.append(("Dynamic Fetch", test_dynamic_fetch()))
    results.append(("Export", test_export()))
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        if passed is None:
            status = "⚠ SKIP (optional)"
        elif passed:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
            all_passed = False
        print(f"  {name}: {status}")
    
    if all_passed:
        print("\n✅ All tests passed! Your scraper is ready to use.")
        print("\nNext steps:")
        print("  1. Look at examples.py for usage patterns")
        print("  2. Run: python -c \"from core import print_availability; print_availability()\"")
        print("  3. Customize the selectors for your target site")
        print("  4. Run your scraper!")
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
