#!/usr/bin/env python3
"""
🎯 Scrapling Pro - Vertical Examples
====================================
Ready-to-run examples for each vertical:
1. E-Commerce: Product scraping, price monitoring, competitor analysis
2. Influencer Research: Profile analysis, engagement metrics, authenticity
3. Trend Analysis: Google Trends, seasonal patterns, brand comparison
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================================
# E-COMMERCE EXAMPLES
# ============================================================================

def example_ecommerce_product_scraping():
    """
    Example: Scrape product data from any e-commerce site
    Uses smart fallback: JSON-LD → Microdata → CSS selectors → Regex
    """
    print("\n📦 E-Commerce: Product Scraping")
    print("=" * 50)
    
    from engine import ScrapingEngine
    from core.smart_extractors import SmartProductExtractor
    
    # Initialize
    engine = ScrapingEngine(mode="stealthy")
    extractor = SmartProductExtractor()
    
    # Scrape a product page
    url = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    
    print(f"Scraping: {url}")
    page = engine.fetch(url)
    
    if page:
        product = extractor.extract(page.html, url)
        
        print(f"\n✅ Product extracted via: {product.source}")
        print(f"   Name: {product.name}")
        print(f"   Price: {product.price} {product.currency}")
        print(f"   Availability: {product.availability}")
        print(f"   Confidence: {product.confidence}")
    else:
        print("❌ Failed to fetch page")
    
    return product if page else None


def example_ecommerce_price_monitoring():
    """
    Example: Monitor prices and get alerts on changes
    """
    print("\n💰 E-Commerce: Price Monitoring")
    print("=" * 50)
    
    try:
        from verticals import EcommerceVertical
        
        ecom = EcommerceVertical()
        
        # Add products to watchlist
        products = [
            ("https://example.com/product1", 99.99, "Product 1"),
            ("https://example.com/product2", 149.99, "Product 2"),
        ]
        
        print("Adding products to watchlist...")
        for url, price, name in products:
            ecom.add_to_watchlist(url, price, name)
            print(f"  ✓ {name}: ${price}")
        
        # In production, you'd run this periodically:
        # alerts = ecom.check_prices(threshold_percent=5.0)
        # for alert in alerts:
        #     print(f"🚨 {alert.product_name}: ${alert.old_price} → ${alert.new_price}")
        
        print("\n💡 To check prices, run: ecom.check_prices(threshold_percent=5.0)")
        
    except ImportError as e:
        print(f"⚠️ Verticals not available: {e}")
        print("   Install with: pip install extruct price-parser")


def example_ecommerce_competitor_analysis():
    """
    Example: Compare prices across competitors
    """
    print("\n🏪 E-Commerce: Competitor Analysis")
    print("=" * 50)
    
    try:
        from verticals import EcommerceVertical
        
        ecom = EcommerceVertical()
        
        # In production, use real competitor URLs
        print("Competitor analysis compares prices across multiple sites:")
        print("""
    comparison = ecom.compare_competitors([
        "https://amazon.com/product-xyz",
        "https://walmart.com/product-xyz",
        "https://target.com/product-xyz",
    ])
    
    print(f"Cheapest: {comparison['cheapest']}")
    print(f"Price spread: ${comparison['stats']['price_spread']}")
        """)
        
    except ImportError as e:
        print(f"⚠️ Verticals not available: {e}")


def example_ecommerce_review_sentiment():
    """
    Example: Analyze product review sentiment
    """
    print("\n⭐ E-Commerce: Review Sentiment Analysis")
    print("=" * 50)
    
    try:
        from core.smart_extractors import SmartSentimentAnalyzer
        
        analyzer = SmartSentimentAnalyzer()
        
        reviews = [
            "Absolutely love this product! Best purchase I've made all year.",
            "Terrible quality, broke after one week. Complete waste of money.",
            "It's okay, does what it's supposed to do. Nothing special.",
            "Great value for the price. Fast shipping too!",
            "Disappointed. The description was misleading.",
        ]
        
        print("Analyzing reviews...")
        results = analyzer.analyze_batch(reviews)
        
        print(f"\n📊 Results:")
        print(f"   Total reviews: {results['total']}")
        print(f"   Positive: {results['positive']} ({results['positive_percent']:.1f}%)")
        print(f"   Negative: {results['negative']} ({results['negative_percent']:.1f}%)")
        print(f"   Neutral: {results['neutral']}")
        print(f"   Average score: {results['average_score']:.2f}")
        
        print(f"\n   Tool used: {results['results'][0].source}")
        
    except ImportError as e:
        print(f"⚠️ Sentiment analyzer not available: {e}")
        print("   Install with: pip install vaderSentiment textblob")


# ============================================================================
# INFLUENCER RESEARCH EXAMPLES
# ============================================================================

def example_influencer_profile_analysis():
    """
    Example: Analyze Instagram influencer profile
    """
    print("\n👤 Influencer: Profile Analysis")
    print("=" * 50)
    
    try:
        from verticals import InfluencerVertical
        
        influencer = InfluencerVertical()
        
        print("Analyzing Instagram profile...")
        print("""
    # Analyze a profile
    profile = influencer.analyze_instagram("cristiano")
    
    print(f"Username: @{profile.username}")
    print(f"Followers: {profile.followers:,}")
    print(f"Engagement Rate: {profile.engagement_rate}%")
    print(f"Verified: {profile.verified}")
        """)
        
        print("⚠️ Note: Instagram scraping requires login for most profiles")
        print("   Consider using the official Instagram Basic Display API for production")
        
    except ImportError as e:
        print(f"⚠️ Influencer vertical not available: {e}")
        print("   Install with: pip install instaloader")


def example_influencer_comparison():
    """
    Example: Compare multiple influencers
    """
    print("\n📊 Influencer: Comparison")
    print("=" * 50)
    
    print("""
    from verticals import InfluencerVertical
    
    influencer = InfluencerVertical()
    
    # Compare influencers
    comparison = influencer.compare(
        ["user1", "user2", "user3"],
        platform="instagram"
    )
    
    print(f"Best engagement: @{comparison.best_engagement}")
    print(f"Most followers: @{comparison.most_followers}")
    print(f"Best value (ROI): @{comparison.best_value}")
    print(f"Avg engagement rate: {comparison.avg_engagement_rate}%")
    """)


def example_influencer_authenticity():
    """
    Example: Check for fake followers/engagement
    """
    print("\n🔍 Influencer: Authenticity Check")
    print("=" * 50)
    
    try:
        from verticals import InfluencerVertical
        from core.smart_extractors import InfluencerProfile
        
        influencer = InfluencerVertical()
        
        # Create a sample profile for demo
        sample_profile = InfluencerProfile(
            username="sample_user",
            platform="instagram",
            followers=50000,
            following=200,
            posts=150,
            engagement_rate=2.5,
            verified=False,
        )
        
        print("Checking authenticity...")
        result = influencer.check_authenticity(sample_profile)
        
        print(f"\n📊 Authenticity Report for @{result['username']}:")
        print(f"   Score: {result['authenticity_score']}/100")
        print(f"   Rating: {result['rating']}")
        print(f"   Recommendation: {result['recommendation']}")
        
        if result['red_flags']:
            print(f"   ⚠️ Red flags:")
            for flag in result['red_flags']:
                print(f"      - {flag}")
        else:
            print(f"   ✅ No red flags detected")
        
    except ImportError as e:
        print(f"⚠️ Influencer vertical not available: {e}")


# ============================================================================
# TREND ANALYSIS EXAMPLES
# ============================================================================

def example_trends_keyword_analysis():
    """
    Example: Analyze keyword trends
    """
    print("\n📈 Trends: Keyword Analysis")
    print("=" * 50)
    
    try:
        from core.smart_extractors import SmartTrendAnalyzer
        
        analyzer = SmartTrendAnalyzer()
        
        keywords = ["iPhone", "Samsung Galaxy", "Google Pixel"]
        
        print(f"Analyzing trends for: {keywords}")
        print("(This requires internet access and may take a moment...)\n")
        
        try:
            trends = analyzer.analyze(keywords, timeframe="today 3-m")
            
            for trend in trends:
                print(f"📊 {trend.keyword}:")
                print(f"   Related queries: {trend.related_queries[:3]}")
                if trend.regional_interest:
                    top_region = max(trend.regional_interest.items(), key=lambda x: x[1], default=("N/A", 0))
                    print(f"   Top region: {top_region[0]}")
                print()
                
        except Exception as e:
            print(f"⚠️ Trend analysis failed: {e}")
            print("   pytrends may be rate-limited or blocked")
        
    except ImportError as e:
        print(f"⚠️ Trend analyzer not available: {e}")
        print("   Install with: pip install pytrends")


def example_trends_brand_comparison():
    """
    Example: Compare brand search interest
    """
    print("\n🏢 Trends: Brand Comparison")
    print("=" * 50)
    
    print("""
    from verticals import TrendVertical
    
    trends = TrendVertical()
    
    # Compare brands
    comparison = trends.compare_brands(
        ["Nike", "Adidas", "Puma"],
        timeframe="today 12-m"
    )
    
    print(f"Market leader: {comparison['leader']}")
    print(f"Fastest growing: {comparison['fastest_growing']}")
    print(f"Recommendation: {comparison['recommendation']}")
    
    for brand, data in comparison['brands'].items():
        print(f"  {brand}:")
        print(f"    Market share: {data['market_share']}%")
        print(f"    Trend: {data['trending']}")
    """)


def example_trends_seasonal_patterns():
    """
    Example: Detect seasonal patterns
    """
    print("\n🗓️ Trends: Seasonal Patterns")
    print("=" * 50)
    
    print("""
    from verticals import TrendVertical
    
    trends = TrendVertical()
    
    # Find seasonal patterns
    seasonal = trends.find_seasonal_patterns("swimwear", years=2)
    
    print(f"Peak months: {seasonal['peak_months']}")
    print(f"Low months: {seasonal['low_months']}")
    print(f"Seasonality strength: {seasonal['seasonality_strength']}x")
    print(f"Recommendation: {seasonal['recommendation']}")
    """)


# ============================================================================
# MAIN - RUN ALL EXAMPLES
# ============================================================================

def main():
    print("🕷️ Scrapling Pro - Vertical Examples")
    print("=" * 60)
    print("""
Choose an example to run:

E-COMMERCE:
  1. Product scraping (schema extraction)
  2. Price monitoring setup
  3. Competitor analysis
  4. Review sentiment analysis

INFLUENCER:
  5. Profile analysis
  6. Influencer comparison
  7. Authenticity check

TRENDS:
  8. Keyword analysis
  9. Brand comparison
  10. Seasonal patterns

  0. Run all examples
  q. Quit
    """)
    
    examples = {
        '1': example_ecommerce_product_scraping,
        '2': example_ecommerce_price_monitoring,
        '3': example_ecommerce_competitor_analysis,
        '4': example_ecommerce_review_sentiment,
        '5': example_influencer_profile_analysis,
        '6': example_influencer_comparison,
        '7': example_influencer_authenticity,
        '8': example_trends_keyword_analysis,
        '9': example_trends_brand_comparison,
        '10': example_trends_seasonal_patterns,
    }
    
    while True:
        choice = input("\nEnter choice (0-10, q): ").strip().lower()
        
        if choice == 'q':
            print("Goodbye!")
            break
        elif choice == '0':
            for func in examples.values():
                func()
                print("\n" + "-" * 60)
        elif choice in examples:
            examples[choice]()
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    main()
