"""
🧠 Smart Extractors
===================
Unified extraction APIs with intelligent fallback chains.
Each extractor tries primary → secondary → tertiary tools automatically.
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .fallback_chain import FallbackChain, ToolResult, SmartFallback

logger = logging.getLogger("SmartExtractors")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ProductData:
    """Standardized product data structure"""
    name: str = ""
    description: str = ""
    price: float = None
    currency: str = ""
    original_price: float = None
    discount_percent: float = None
    sku: str = ""
    gtin: str = ""
    brand: str = ""
    category: str = ""
    image: str = ""
    images: List[str] = field(default_factory=list)
    availability: str = ""
    condition: str = ""
    rating: float = None
    review_count: int = None
    seller: str = ""
    url: str = ""
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = ""  # Which tool extracted this
    confidence: float = 1.0
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != "" and v != []}


@dataclass 
class SentimentResult:
    """Standardized sentiment analysis result"""
    text: str
    score: float  # -1 to 1
    label: str  # positive, negative, neutral
    confidence: float
    details: Dict = field(default_factory=dict)
    source: str = ""


@dataclass
class TrendData:
    """Standardized trend data structure"""
    keyword: str
    interest_over_time: List[Dict] = field(default_factory=list)
    related_queries: List[str] = field(default_factory=list)
    regional_interest: Dict[str, float] = field(default_factory=dict)
    trending_now: bool = False
    source: str = ""


@dataclass
class InfluencerProfile:
    """Standardized influencer profile data"""
    username: str
    platform: str
    followers: int = 0
    following: int = 0
    posts: int = 0
    engagement_rate: float = 0.0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    bio: str = ""
    verified: bool = False
    business_account: bool = False
    category: str = ""
    profile_url: str = ""
    profile_pic: str = ""
    recent_posts: List[Dict] = field(default_factory=list)
    source: str = ""


# ============================================================================
# PRODUCT EXTRACTION
# ============================================================================

class SmartProductExtractor:
    """
    Extract product data from any e-commerce page.
    
    Fallback chain:
    1. extruct (JSON-LD/microdata) - Most accurate
    2. BeautifulSoup + common selectors
    3. Regex patterns
    
    Usage:
        extractor = SmartProductExtractor()
        product = extractor.extract(html, url)
    """
    
    def __init__(self):
        self._chain = None
        self._init_chain()
    
    def _init_chain(self):
        """Initialize the fallback chain"""
        self._chain = FallbackChain([
            ("extruct", self._extract_with_extruct),
            ("selectors", self._extract_with_selectors),
            ("regex", self._extract_with_regex),
        ], name="ProductExtractor")
    
    def extract(self, html: str, url: str) -> ProductData:
        """
        Extract product data from HTML.
        
        Args:
            html: Page HTML content
            url: Page URL
            
        Returns:
            ProductData with extracted information
        """
        result = self._chain.execute(html, url, cache_key=url)
        
        if result.success:
            data = result.data
            data["source"] = result.tool_name
            return ProductData(**data)
        else:
            logger.warning(f"Product extraction failed for {url}: {result.error}")
            return ProductData(url=url, source="failed")
    
    def _extract_with_extruct(self, html: str, url: str) -> Dict:
        """Primary: Use extruct for schema.org extraction"""
        import extruct
        from w3lib.html import get_base_url
        
        base_url = get_base_url(html, url)
        data = extruct.extract(html, base_url=base_url, syntaxes=['json-ld', 'microdata', 'opengraph'])
        
        product = {}
        
        # JSON-LD (most reliable)
        for item in data.get('json-ld', []):
            if item.get('@type') == 'Product':
                offers = item.get('offers', {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                
                product = {
                    'name': item.get('name'),
                    'description': item.get('description', '')[:500],
                    'sku': item.get('sku'),
                    'gtin': item.get('gtin13') or item.get('gtin') or item.get('gtin12'),
                    'brand': item.get('brand', {}).get('name') if isinstance(item.get('brand'), dict) else item.get('brand'),
                    'category': item.get('category'),
                    'image': item.get('image')[0] if isinstance(item.get('image'), list) else item.get('image'),
                    'images': item.get('image') if isinstance(item.get('image'), list) else [item.get('image')] if item.get('image') else [],
                    'price': self._parse_price(offers.get('price')),
                    'currency': offers.get('priceCurrency'),
                    'availability': offers.get('availability', '').replace('http://schema.org/', '').replace('https://schema.org/', ''),
                    'condition': offers.get('itemCondition', '').replace('http://schema.org/', '').replace('https://schema.org/', ''),
                    'seller': offers.get('seller', {}).get('name') if isinstance(offers.get('seller'), dict) else None,
                    'rating': self._parse_float(item.get('aggregateRating', {}).get('ratingValue')),
                    'review_count': self._parse_int(item.get('aggregateRating', {}).get('reviewCount')),
                    'url': url,
                    'confidence': 0.95,
                }
                break
        
        # Fallback to OpenGraph
        if not product.get('name'):
            for og in data.get('opengraph', []):
                props = dict(og.get('properties', []))
                if props.get('og:type') == 'product' or props.get('og:title'):
                    product = {
                        'name': props.get('og:title'),
                        'description': props.get('og:description', '')[:500],
                        'image': props.get('og:image'),
                        'price': self._parse_price(props.get('product:price:amount')),
                        'currency': props.get('product:price:currency'),
                        'url': url,
                        'confidence': 0.7,
                    }
                    break
        
        if not product.get('name'):
            raise ValueError("No product schema found")
        
        return product
    
    def _extract_with_selectors(self, html: str, url: str) -> Dict:
        """Secondary: Use common CSS selectors"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Common product selectors
        name_selectors = [
            'h1[itemprop="name"]', 'h1.product-title', 'h1.product-name',
            '.product-title h1', '.product_title', 'h1#title', 
            'span#productTitle', 'h1'
        ]
        
        price_selectors = [
            '[itemprop="price"]', '.price', '.product-price', 
            '.sale-price', '.Price', '#priceblock_ourprice',
            '.a-price-whole', '[data-price]'
        ]
        
        image_selectors = [
            'img[itemprop="image"]', '.product-image img', 
            '#main-image', '.gallery-image', 'img.primary'
        ]
        
        name = self._find_first(soup, name_selectors)
        price_text = self._find_first(soup, price_selectors)
        image = self._find_first_attr(soup, image_selectors, 'src')
        
        if not name:
            raise ValueError("Could not find product name")
        
        return {
            'name': name,
            'price': self._parse_price(price_text),
            'image': image,
            'url': url,
            'confidence': 0.6,
        }
    
    def _extract_with_regex(self, html: str, url: str) -> Dict:
        """Tertiary: Use regex patterns"""
        # Try to find title
        title_match = re.search(r'<title>([^<]+)</title>', html, re.I)
        name = title_match.group(1).strip() if title_match else ""
        
        # Try to find price
        price_match = re.search(r'[\$€£¥₹]\s*(\d+[.,]?\d*)', html)
        price = self._parse_price(price_match.group(0)) if price_match else None
        
        # Try to find image
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*product', html, re.I)
        if not img_match:
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+\.(?:jpg|png|webp))["\']', html, re.I)
        image = img_match.group(1) if img_match else ""
        
        if not name:
            raise ValueError("Could not extract product data with regex")
        
        return {
            'name': name,
            'price': price,
            'image': image,
            'url': url,
            'confidence': 0.3,
        }
    
    def _find_first(self, soup, selectors: List[str]) -> str:
        """Find first matching element text"""
        for selector in selectors:
            el = soup.select_one(selector)
            if el and el.get_text(strip=True):
                return el.get_text(strip=True)
        return ""
    
    def _find_first_attr(self, soup, selectors: List[str], attr: str) -> str:
        """Find first matching element attribute"""
        for selector in selectors:
            el = soup.select_one(selector)
            if el and el.get(attr):
                return el.get(attr)
        return ""
    
    def _parse_price(self, value) -> Optional[float]:
        """Parse price from various formats"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        
        # Try price-parser first
        try:
            from price_parser import Price
            p = Price.fromstring(str(value))
            return float(p.amount) if p.amount else None
        except ImportError:
            pass
        
        # Regex fallback
        match = re.search(r'(\d+[.,]?\d*)', str(value).replace(',', ''))
        return float(match.group(1)) if match else None
    
    def _parse_float(self, value) -> Optional[float]:
        """Parse float safely"""
        try:
            return float(value) if value else None
        except (ValueError, TypeError):
            return None
    
    def _parse_int(self, value) -> Optional[int]:
        """Parse int safely"""
        try:
            return int(value) if value else None
        except (ValueError, TypeError):
            return None
    
    def get_stats(self) -> Dict:
        """Get extraction statistics"""
        return self._chain.get_stats()


# ============================================================================
# SENTIMENT ANALYSIS
# ============================================================================

class SmartSentimentAnalyzer:
    """
    Analyze sentiment with automatic fallbacks.
    
    Fallback chain:
    1. VADER - Best for social media/reviews
    2. TextBlob - Good general NLP
    3. Keyword matching - Always works
    
    Usage:
        analyzer = SmartSentimentAnalyzer()
        result = analyzer.analyze("Great product, love it!")
        print(result.label)  # "positive"
    """
    
    def __init__(self):
        self._chain = FallbackChain([
            ("vader", self._analyze_vader),
            ("textblob", self._analyze_textblob),
            ("keywords", self._analyze_keywords),
        ], name="SentimentAnalyzer")
        
        # Keyword lists for fallback
        self._positive_words = {
            'good', 'great', 'excellent', 'amazing', 'awesome', 'fantastic',
            'love', 'best', 'perfect', 'wonderful', 'beautiful', 'happy',
            'recommend', 'quality', 'fast', 'easy', 'helpful', 'nice',
            'satisfied', 'impressed', 'pleased', 'delighted', 'superb'
        }
        self._negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate',
            'poor', 'disappointing', 'waste', 'broken', 'slow', 'difficult',
            'useless', 'frustrating', 'annoying', 'regret', 'never', 'avoid',
            'refund', 'return', 'scam', 'fake', 'cheap', 'defective'
        }
    
    def analyze(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            SentimentResult with score and label
        """
        result = self._chain.execute(text)
        
        if result.success:
            data = result.data
            return SentimentResult(
                text=text[:100],
                score=data['score'],
                label=data['label'],
                confidence=data['confidence'],
                details=data.get('details', {}),
                source=result.tool_name
            )
        else:
            return SentimentResult(
                text=text[:100],
                score=0,
                label="neutral",
                confidence=0,
                source="failed"
            )
    
    def analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """
        Analyze multiple texts and return summary.
        
        Returns:
            Dict with individual results and aggregated stats
        """
        results = [self.analyze(text) for text in texts]
        
        positive = sum(1 for r in results if r.label == "positive")
        negative = sum(1 for r in results if r.label == "negative")
        neutral = sum(1 for r in results if r.label == "neutral")
        
        avg_score = sum(r.score for r in results) / len(results) if results else 0
        
        return {
            'results': results,
            'total': len(results),
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'positive_percent': positive / len(results) * 100 if results else 0,
            'negative_percent': negative / len(results) * 100 if results else 0,
            'average_score': round(avg_score, 3),
        }
    
    def _analyze_vader(self, text: str) -> Dict:
        """Primary: VADER sentiment analysis"""
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        
        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(text)
        
        compound = scores['compound']
        
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"
        
        return {
            'score': compound,
            'label': label,
            'confidence': abs(compound),
            'details': {
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu'],
            }
        }
    
    def _analyze_textblob(self, text: str) -> Dict:
        """Secondary: TextBlob sentiment"""
        from textblob import TextBlob
        
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1
        
        if polarity > 0.1:
            label = "positive"
        elif polarity < -0.1:
            label = "negative"
        else:
            label = "neutral"
        
        return {
            'score': polarity,
            'label': label,
            'confidence': 1 - subjectivity,  # More objective = more confident
            'details': {
                'subjectivity': subjectivity,
            }
        }
    
    def _analyze_keywords(self, text: str) -> Dict:
        """Tertiary: Simple keyword matching"""
        words = set(text.lower().split())
        
        positive_count = len(words & self._positive_words)
        negative_count = len(words & self._negative_words)
        
        total = positive_count + negative_count
        
        if total == 0:
            return {'score': 0, 'label': 'neutral', 'confidence': 0.3}
        
        score = (positive_count - negative_count) / total
        
        if score > 0.2:
            label = "positive"
        elif score < -0.2:
            label = "negative"
        else:
            label = "neutral"
        
        return {
            'score': score,
            'label': label,
            'confidence': min(0.5, total / 10),  # Max 0.5 confidence for keyword method
            'details': {
                'positive_words': positive_count,
                'negative_words': negative_count,
            }
        }
    
    def get_stats(self) -> Dict:
        return self._chain.get_stats()


# ============================================================================
# TREND ANALYSIS
# ============================================================================

class SmartTrendAnalyzer:
    """
    Analyze search trends with fallbacks.
    
    Fallback chain:
    1. pytrends (Google Trends) - Real data
    2. Mock/cached data - For testing
    
    Usage:
        analyzer = SmartTrendAnalyzer()
        trends = analyzer.analyze(["iPhone 16", "Samsung S25"])
    """
    
    def __init__(self):
        self._chain = FallbackChain([
            ("pytrends", self._analyze_pytrends),
            ("cache", self._analyze_cache),
        ], name="TrendAnalyzer")
        
        self._cache: Dict[str, TrendData] = {}
    
    def analyze(
        self, 
        keywords: List[str], 
        timeframe: str = 'today 3-m',
        geo: str = ''
    ) -> List[TrendData]:
        """
        Analyze trends for keywords.
        
        Args:
            keywords: List of keywords to analyze (max 5)
            timeframe: Time range (e.g., 'today 3-m', 'today 12-m')
            geo: Geographic region (e.g., 'US', 'GB', '')
            
        Returns:
            List of TrendData for each keyword
        """
        keywords = keywords[:5]  # Google Trends limit
        
        result = self._chain.execute(
            keywords, timeframe, geo,
            cache_key=f"{'-'.join(keywords)}_{timeframe}_{geo}"
        )
        
        if result.success:
            return result.data
        else:
            logger.warning(f"Trend analysis failed: {result.error}")
            return [TrendData(keyword=k, source="failed") for k in keywords]
    
    def get_trending(self, country: str = 'united_states') -> List[str]:
        """Get currently trending searches"""
        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl='en-US', tz=360)
            df = pytrends.trending_searches(pn=country)
            return df[0].tolist()[:20]
        except Exception as e:
            logger.warning(f"Could not get trending searches: {e}")
            return []
    
    def _analyze_pytrends(
        self, 
        keywords: List[str], 
        timeframe: str, 
        geo: str
    ) -> List[TrendData]:
        """Primary: Use pytrends"""
        from pytrends.request import TrendReq
        
        pytrends = TrendReq(hl='en-US', tz=360)
        pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo)
        
        # Get interest over time
        interest = pytrends.interest_over_time()
        
        # Get related queries
        related = pytrends.related_queries()
        
        # Get regional interest
        regional = pytrends.interest_by_region()
        
        results = []
        for keyword in keywords:
            trend = TrendData(
                keyword=keyword,
                source="pytrends"
            )
            
            # Interest over time
            if not interest.empty and keyword in interest.columns:
                trend.interest_over_time = [
                    {"date": str(idx), "value": int(row[keyword])}
                    for idx, row in interest.iterrows()
                ]
            
            # Related queries
            if keyword in related and related[keyword].get('rising') is not None:
                trend.related_queries = related[keyword]['rising']['query'].tolist()[:10]
            
            # Regional interest
            if not regional.empty and keyword in regional.columns:
                trend.regional_interest = regional[keyword].to_dict()
            
            results.append(trend)
        
        return results
    
    def _analyze_cache(
        self, 
        keywords: List[str], 
        timeframe: str, 
        geo: str
    ) -> List[TrendData]:
        """Fallback: Return cached/mock data"""
        return [
            TrendData(
                keyword=k,
                interest_over_time=[],
                related_queries=[],
                regional_interest={},
                source="cache"
            )
            for k in keywords
        ]


# ============================================================================
# INFLUENCER ANALYSIS
# ============================================================================

class SmartInfluencerAnalyzer:
    """
    Analyze influencer profiles across platforms.
    
    Fallback chain:
    1. Native library (instaloader, snscrape)
    2. Direct scraping
    3. Cached/API data
    
    Usage:
        analyzer = SmartInfluencerAnalyzer()
        profile = analyzer.analyze_instagram("username")
    """
    
    def __init__(self):
        self._instagram_chain = FallbackChain([
            ("instaloader", self._instagram_instaloader),
            ("scraper", self._instagram_scraper),
        ], name="InstagramAnalyzer")
        
        self._twitter_chain = FallbackChain([
            ("snscrape", self._twitter_snscrape),
            ("scraper", self._twitter_scraper),
        ], name="TwitterAnalyzer")
    
    def analyze_instagram(self, username: str) -> InfluencerProfile:
        """Analyze Instagram profile"""
        result = self._instagram_chain.execute(username, cache_key=f"ig_{username}")
        
        if result.success:
            data = result.data
            data['source'] = result.tool_name
            return InfluencerProfile(**data)
        else:
            logger.warning(f"Instagram analysis failed for {username}: {result.error}")
            return InfluencerProfile(username=username, platform="instagram", source="failed")
    
    def analyze_twitter(self, username: str) -> InfluencerProfile:
        """Analyze Twitter/X profile"""
        result = self._twitter_chain.execute(username, cache_key=f"tw_{username}")
        
        if result.success:
            data = result.data
            data['source'] = result.tool_name
            return InfluencerProfile(**data)
        else:
            logger.warning(f"Twitter analysis failed for {username}: {result.error}")
            return InfluencerProfile(username=username, platform="twitter", source="failed")
    
    def _instagram_instaloader(self, username: str) -> Dict:
        """Primary: Use instaloader"""
        from instaloader import Instaloader, Profile
        
        L = Instaloader()
        profile = Profile.from_username(L.context, username)
        
        # Calculate engagement from recent posts
        total_likes = 0
        total_comments = 0
        post_count = 0
        recent_posts = []
        
        for post in profile.get_posts():
            if post_count >= 12:
                break
            total_likes += post.likes
            total_comments += post.comments
            recent_posts.append({
                'shortcode': post.shortcode,
                'likes': post.likes,
                'comments': post.comments,
                'caption': post.caption[:100] if post.caption else "",
                'date': post.date.isoformat()
            })
            post_count += 1
        
        engagement_rate = 0
        avg_likes = 0
        avg_comments = 0
        
        if post_count > 0 and profile.followers > 0:
            avg_likes = total_likes / post_count
            avg_comments = total_comments / post_count
            avg_engagement = (avg_likes + avg_comments) / post_count
            engagement_rate = (avg_engagement / profile.followers) * 100
        
        return {
            'username': profile.username,
            'platform': 'instagram',
            'followers': profile.followers,
            'following': profile.followees,
            'posts': profile.mediacount,
            'engagement_rate': round(engagement_rate, 2),
            'avg_likes': round(avg_likes, 0),
            'avg_comments': round(avg_comments, 0),
            'bio': profile.biography,
            'verified': profile.is_verified,
            'business_account': profile.is_business_account,
            'profile_url': f"https://instagram.com/{username}",
            'profile_pic': profile.profile_pic_url,
            'recent_posts': recent_posts,
        }
    
    def _instagram_scraper(self, username: str) -> Dict:
        """Fallback: Direct scraping (requires Playwright)"""
        # This would use DynamicFetcher from scrapling
        raise NotImplementedError("Instagram scraper fallback not implemented")
    
    def _twitter_snscrape(self, username: str) -> Dict:
        """Primary: Use snscrape for Twitter"""
        import snscrape.modules.twitter as sntwitter
        
        # Get user info
        scraper = sntwitter.TwitterUserScraper(username)
        user = scraper.entity
        
        return {
            'username': user.username,
            'platform': 'twitter',
            'followers': user.followersCount,
            'following': user.friendsCount,
            'posts': user.statusesCount,
            'bio': user.rawDescription,
            'verified': user.verified,
            'profile_url': f"https://twitter.com/{username}",
            'profile_pic': user.profileImageUrl,
        }
    
    def _twitter_scraper(self, username: str) -> Dict:
        """Fallback: Direct scraping"""
        raise NotImplementedError("Twitter scraper fallback not implemented")


# ============================================================================
# UNIFIED API
# ============================================================================

class SmartExtractors:
    """
    Unified API for all smart extractors.
    
    Usage:
        extractors = SmartExtractors()
        
        # Product extraction
        product = extractors.product.extract(html, url)
        
        # Sentiment analysis
        sentiment = extractors.sentiment.analyze("Great product!")
        
        # Trend analysis
        trends = extractors.trends.analyze(["keyword1", "keyword2"])
        
        # Influencer analysis
        profile = extractors.influencer.analyze_instagram("username")
    """
    
    def __init__(self):
        self.product = SmartProductExtractor()
        self.sentiment = SmartSentimentAnalyzer()
        self.trends = SmartTrendAnalyzer()
        self.influencer = SmartInfluencerAnalyzer()
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all extractors"""
        return {
            'product': self.product.get_stats(),
            'sentiment': self.sentiment.get_stats(),
            'trends': self.trends._chain.get_stats(),
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global instance for convenience
_extractors = None

def get_extractors() -> SmartExtractors:
    """Get global SmartExtractors instance"""
    global _extractors
    if _extractors is None:
        _extractors = SmartExtractors()
    return _extractors


def extract_product(html: str, url: str) -> ProductData:
    """Convenience function to extract product data"""
    return get_extractors().product.extract(html, url)


def analyze_sentiment(text: str) -> SentimentResult:
    """Convenience function to analyze sentiment"""
    return get_extractors().sentiment.analyze(text)


def analyze_trends(keywords: List[str]) -> List[TrendData]:
    """Convenience function to analyze trends"""
    return get_extractors().trends.analyze(keywords)


if __name__ == "__main__":
    from .fallback_chain import print_availability
    
    print("\n🧠 Smart Extractors Module")
    print("=" * 50)
    
    # Show tool availability
    print_availability()
    
    # Test sentiment (always works due to keyword fallback)
    print("\n\n📊 Testing Sentiment Analyzer...")
    analyzer = SmartSentimentAnalyzer()
    
    tests = [
        "This product is amazing! Best purchase ever!",
        "Terrible quality, complete waste of money.",
        "It's okay, nothing special.",
    ]
    
    for text in tests:
        result = analyzer.analyze(text)
        print(f"  '{text[:40]}...'")
        print(f"    → {result.label} (score: {result.score:.2f}, via: {result.source})")
