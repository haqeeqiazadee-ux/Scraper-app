"""
Scrapling Pro Integrations Module
=================================
Ready-to-use integrations with open-source tools and free APIs
for ecommerce, trend analysis, influencer research, and more.

Install dependencies:
    pip install extruct pyld price-parser vaderSentiment textblob 
    pip install pytrends instaloader snscrape scikit-learn
    pip install ShopifyAPI woocommerce taxjar karrio
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import re

# ============================================================================
# PRODUCT DATA EXTRACTION (Schema.org / JSON-LD)
# ============================================================================

try:
    import extruct
    from w3lib.html import get_base_url
    EXTRUCT_AVAILABLE = True
except ImportError:
    EXTRUCT_AVAILABLE = False
    print("Install extruct: pip install extruct w3lib")


class ProductSchemaExtractor:
    """
    Extract structured product data from any ecommerce page using schema.org markup.
    Works with Amazon, Shopify, WooCommerce, Magento, and most ecommerce sites.
    """
    
    @staticmethod
    def extract(html: str, url: str) -> Dict[str, Any]:
        """Extract Product schema from HTML"""
        if not EXTRUCT_AVAILABLE:
            raise ImportError("extruct not installed")
        
        base_url = get_base_url(html, url)
        data = extruct.extract(html, base_url=base_url, syntaxes=['json-ld', 'microdata', 'opengraph'])
        
        product = {}
        
        # Priority 1: JSON-LD (most reliable)
        for item in data.get('json-ld', []):
            if item.get('@type') == 'Product':
                offers = item.get('offers', {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                
                product = {
                    'source': 'json-ld',
                    'name': item.get('name'),
                    'description': item.get('description'),
                    'sku': item.get('sku'),
                    'gtin': item.get('gtin13') or item.get('gtin') or item.get('gtin12'),
                    'mpn': item.get('mpn'),
                    'brand': item.get('brand', {}).get('name') if isinstance(item.get('brand'), dict) else item.get('brand'),
                    'category': item.get('category'),
                    'image': item.get('image'),
                    'price': offers.get('price'),
                    'currency': offers.get('priceCurrency'),
                    'availability': offers.get('availability', '').replace('http://schema.org/', ''),
                    'condition': offers.get('itemCondition', '').replace('http://schema.org/', ''),
                    'seller': offers.get('seller', {}).get('name') if isinstance(offers.get('seller'), dict) else None,
                    'rating': item.get('aggregateRating', {}).get('ratingValue'),
                    'review_count': item.get('aggregateRating', {}).get('reviewCount'),
                    'url': url
                }
                break
        
        # Priority 2: Microdata
        if not product:
            for item in data.get('microdata', []):
                if 'Product' in str(item.get('type', '')):
                    props = item.get('properties', {})
                    offers = props.get('offers', {})
                    if isinstance(offers, dict):
                        offers = offers.get('properties', {})
                    
                    product = {
                        'source': 'microdata',
                        'name': props.get('name'),
                        'description': props.get('description'),
                        'sku': props.get('sku'),
                        'brand': props.get('brand'),
                        'image': props.get('image'),
                        'price': offers.get('price') if isinstance(offers, dict) else None,
                        'url': url
                    }
                    break
        
        # Priority 3: OpenGraph (fallback)
        if not product.get('name'):
            for og in data.get('opengraph', []):
                props = dict(og.get('properties', []))
                if props.get('og:type') == 'product' or not product.get('name'):
                    product.update({
                        'source': product.get('source', 'opengraph'),
                        'name': product.get('name') or props.get('og:title'),
                        'description': product.get('description') or props.get('og:description'),
                        'image': product.get('image') or props.get('og:image'),
                        'price': product.get('price') or props.get('product:price:amount'),
                        'currency': product.get('currency') or props.get('product:price:currency'),
                    })
        
        return product
    
    @staticmethod
    def extract_all_products(html: str, url: str) -> List[Dict]:
        """Extract all products from a page (category pages, search results)"""
        if not EXTRUCT_AVAILABLE:
            raise ImportError("extruct not installed")
        
        base_url = get_base_url(html, url)
        data = extruct.extract(html, base_url=base_url, syntaxes=['json-ld', 'microdata'])
        
        products = []
        
        for item in data.get('json-ld', []):
            if item.get('@type') == 'Product':
                products.append(ProductSchemaExtractor._parse_product(item))
            elif item.get('@type') == 'ItemList':
                for elem in item.get('itemListElement', []):
                    if elem.get('item', {}).get('@type') == 'Product':
                        products.append(ProductSchemaExtractor._parse_product(elem['item']))
        
        return products
    
    @staticmethod
    def _parse_product(item: Dict) -> Dict:
        offers = item.get('offers', {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        
        return {
            'name': item.get('name'),
            'sku': item.get('sku'),
            'price': offers.get('price'),
            'currency': offers.get('priceCurrency'),
            'image': item.get('image'),
            'url': item.get('url')
        }


# ============================================================================
# PRICE EXTRACTION
# ============================================================================

try:
    from price_parser import Price
    PRICE_PARSER_AVAILABLE = True
except ImportError:
    PRICE_PARSER_AVAILABLE = False


class PriceExtractor:
    """Extract and normalize prices from any format"""
    
    @staticmethod
    def parse(price_string: str) -> Dict[str, Any]:
        """Parse price string into structured data"""
        if not PRICE_PARSER_AVAILABLE:
            # Fallback regex parsing
            match = re.search(r'[\$€£¥₹]?\s*(\d+[.,]?\d*)', price_string)
            if match:
                return {
                    'amount': float(match.group(1).replace(',', '')),
                    'currency': None,
                    'original': price_string
                }
            return {'amount': None, 'currency': None, 'original': price_string}
        
        price = Price.fromstring(price_string)
        return {
            'amount': float(price.amount) if price.amount else None,
            'currency': price.currency,
            'original': price_string
        }
    
    @staticmethod
    def compare_prices(prices: List[str]) -> Dict[str, Any]:
        """Compare multiple prices and find best deal"""
        parsed = [PriceExtractor.parse(p) for p in prices]
        valid = [p for p in parsed if p['amount'] is not None]
        
        if not valid:
            return {'min': None, 'max': None, 'avg': None}
        
        amounts = [p['amount'] for p in valid]
        return {
            'min': min(amounts),
            'max': max(amounts),
            'avg': sum(amounts) / len(amounts),
            'count': len(valid),
            'savings': max(amounts) - min(amounts)
        }


# ============================================================================
# TREND ANALYSIS (Google Trends)
# ============================================================================

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False


class TrendAnalyzer:
    """Analyze search trends using Google Trends"""
    
    def __init__(self, hl: str = 'en-US', tz: int = 360):
        if not PYTRENDS_AVAILABLE:
            raise ImportError("pytrends not installed: pip install pytrends")
        self.pytrends = TrendReq(hl=hl, tz=tz)
    
    def analyze_keywords(self, keywords: List[str], timeframe: str = 'today 3-m', geo: str = '') -> Dict:
        """Analyze interest for keywords over time"""
        self.pytrends.build_payload(keywords[:5], timeframe=timeframe, geo=geo)  # Max 5 keywords
        
        interest_df = self.pytrends.interest_over_time()
        
        result = {
            'keywords': keywords[:5],
            'timeframe': timeframe,
            'geo': geo or 'worldwide',
            'data': {}
        }
        
        if not interest_df.empty:
            for kw in keywords[:5]:
                if kw in interest_df.columns:
                    series = interest_df[kw]
                    result['data'][kw] = {
                        'current': int(series.iloc[-1]) if len(series) > 0 else 0,
                        'average': round(series.mean(), 2),
                        'max': int(series.max()),
                        'min': int(series.min()),
                        'trend': 'rising' if len(series) > 1 and series.iloc[-1] > series.iloc[0] else 'falling'
                    }
        
        return result
    
    def get_related_queries(self, keyword: str) -> Dict:
        """Get related search queries"""
        self.pytrends.build_payload([keyword])
        related = self.pytrends.related_queries()
        
        result = {'keyword': keyword, 'top': [], 'rising': []}
        
        if keyword in related:
            if related[keyword]['top'] is not None:
                result['top'] = related[keyword]['top'].to_dict('records')[:10]
            if related[keyword]['rising'] is not None:
                result['rising'] = related[keyword]['rising'].to_dict('records')[:10]
        
        return result
    
    def get_trending_now(self, country: str = 'united_states') -> List[str]:
        """Get currently trending searches"""
        df = self.pytrends.trending_searches(pn=country)
        return df[0].tolist()[:20]
    
    def compare_products(self, products: List[str]) -> Dict:
        """Compare search interest between products"""
        return self.analyze_keywords(products, timeframe='today 12-m')


# ============================================================================
# SENTIMENT ANALYSIS (Reviews & UGC)
# ============================================================================

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False


@dataclass
class SentimentResult:
    text: str
    compound: float
    positive: float
    negative: float
    neutral: float
    classification: str
    subjectivity: float = 0.0


class ReviewAnalyzer:
    """Analyze sentiment of product reviews and UGC"""
    
    def __init__(self):
        if VADER_AVAILABLE:
            self.vader = SentimentIntensityAnalyzer()
        else:
            self.vader = None
    
    def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment of a single text"""
        if self.vader:
            scores = self.vader.polarity_scores(text)
            compound = scores['compound']
        else:
            # Fallback to TextBlob
            if TEXTBLOB_AVAILABLE:
                blob = TextBlob(text)
                compound = blob.sentiment.polarity
                scores = {
                    'pos': max(0, compound),
                    'neg': abs(min(0, compound)),
                    'neu': 1 - abs(compound)
                }
            else:
                raise ImportError("Install vaderSentiment or textblob")
        
        # Classification
        if compound >= 0.05:
            classification = 'positive'
        elif compound <= -0.05:
            classification = 'negative'
        else:
            classification = 'neutral'
        
        # Subjectivity
        subjectivity = 0.0
        if TEXTBLOB_AVAILABLE:
            subjectivity = TextBlob(text).sentiment.subjectivity
        
        return SentimentResult(
            text=text[:100] + '...' if len(text) > 100 else text,
            compound=round(compound, 3),
            positive=round(scores.get('pos', 0), 3),
            negative=round(scores.get('neg', 0), 3),
            neutral=round(scores.get('neu', 0), 3),
            classification=classification,
            subjectivity=round(subjectivity, 3)
        )
    
    def analyze_batch(self, reviews: List[str]) -> Dict:
        """Analyze multiple reviews and aggregate results"""
        results = [self.analyze(r) for r in reviews]
        
        positive = sum(1 for r in results if r.classification == 'positive')
        negative = sum(1 for r in results if r.classification == 'negative')
        neutral = sum(1 for r in results if r.classification == 'neutral')
        
        avg_compound = sum(r.compound for r in results) / len(results) if results else 0
        
        return {
            'total_reviews': len(reviews),
            'positive_count': positive,
            'negative_count': negative,
            'neutral_count': neutral,
            'positive_percentage': round(positive / len(reviews) * 100, 1) if reviews else 0,
            'negative_percentage': round(negative / len(reviews) * 100, 1) if reviews else 0,
            'average_sentiment': round(avg_compound, 3),
            'sentiment_label': 'positive' if avg_compound >= 0.05 else 'negative' if avg_compound <= -0.05 else 'neutral',
            'reviews': [vars(r) for r in results[:10]]  # First 10 detailed
        }
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract key phrases from review text"""
        if TEXTBLOB_AVAILABLE:
            blob = TextBlob(text)
            return list(blob.noun_phrases)[:10]
        return []


# ============================================================================
# SEO / SCHEMA ANALYSIS
# ============================================================================

class SEOAnalyzer:
    """Analyze SEO signals including schema markup for AEO/GEO"""
    
    @staticmethod
    def analyze_schema(html: str, url: str) -> Dict:
        """Analyze schema.org markup for SEO"""
        if not EXTRUCT_AVAILABLE:
            raise ImportError("extruct not installed")
        
        data = extruct.extract(html, url)
        
        schema_types = []
        for item in data.get('json-ld', []):
            if '@type' in item:
                schema_types.append(item['@type'])
        
        # AEO signals (Answer Engine Optimization)
        aeo_signals = {
            'has_faq': any('FAQ' in str(t) for t in schema_types),
            'has_howto': any('HowTo' in str(t) for t in schema_types),
            'has_qa': any('Question' in str(t) or 'Answer' in str(t) for t in schema_types),
            'has_article': any('Article' in str(t) for t in schema_types),
            'has_product': any('Product' in str(t) for t in schema_types),
            'has_review': any('Review' in str(t) for t in schema_types),
            'has_organization': any('Organization' in str(t) for t in schema_types),
            'has_breadcrumb': any('Breadcrumb' in str(t) for t in schema_types),
        }
        
        # Score
        aeo_score = sum(aeo_signals.values()) / len(aeo_signals) * 100
        
        return {
            'url': url,
            'json_ld_count': len(data.get('json-ld', [])),
            'microdata_count': len(data.get('microdata', [])),
            'opengraph_found': len(data.get('opengraph', [])) > 0,
            'schema_types': schema_types,
            'aeo_signals': aeo_signals,
            'aeo_score': round(aeo_score, 1),
            'recommendations': SEOAnalyzer._get_recommendations(aeo_signals)
        }
    
    @staticmethod
    def _get_recommendations(signals: Dict) -> List[str]:
        recommendations = []
        if not signals['has_faq']:
            recommendations.append('Add FAQPage schema for featured snippets')
        if not signals['has_product'] and not signals['has_article']:
            recommendations.append('Add Product or Article schema for rich results')
        if not signals['has_breadcrumb']:
            recommendations.append('Add BreadcrumbList for navigation visibility')
        if not signals['has_organization']:
            recommendations.append('Add Organization schema for brand visibility')
        return recommendations


# ============================================================================
# INFLUENCER ANALYTICS
# ============================================================================

try:
    from instaloader import Instaloader, Profile
    INSTALOADER_AVAILABLE = True
except ImportError:
    INSTALOADER_AVAILABLE = False


class InfluencerAnalyzer:
    """Analyze social media influencer metrics"""
    
    def __init__(self):
        if INSTALOADER_AVAILABLE:
            self.loader = Instaloader()
        else:
            self.loader = None
    
    def analyze_instagram(self, username: str) -> Dict:
        """Get Instagram influencer metrics"""
        if not INSTALOADER_AVAILABLE:
            raise ImportError("instaloader not installed: pip install instaloader")
        
        try:
            profile = Profile.from_username(self.loader.context, username)
            
            # Calculate engagement from recent posts
            total_likes = 0
            total_comments = 0
            post_count = 0
            
            for post in profile.get_posts():
                if post_count >= 12:
                    break
                total_likes += post.likes
                total_comments += post.comments
                post_count += 1
            
            engagement_rate = 0
            if post_count > 0 and profile.followers > 0:
                avg_engagement = (total_likes + total_comments) / post_count
                engagement_rate = (avg_engagement / profile.followers) * 100
            
            return {
                'platform': 'instagram',
                'username': profile.username,
                'full_name': profile.full_name,
                'followers': profile.followers,
                'following': profile.followees,
                'posts': profile.mediacount,
                'engagement_rate': round(engagement_rate, 2),
                'bio': profile.biography,
                'verified': profile.is_verified,
                'business': profile.is_business_account,
                'category': profile.business_category_name if profile.is_business_account else None,
                'external_url': profile.external_url,
                'analyzed_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e), 'username': username}


# ============================================================================
# FRAUD DETECTION (ML-based)
# ============================================================================

try:
    from sklearn.ensemble import IsolationForest
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class FraudDetector:
    """Basic fraud detection using anomaly detection"""
    
    def __init__(self, contamination: float = 0.01):
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn not installed: pip install scikit-learn")
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.trained = False
    
    def train(self, transactions: List[Dict]):
        """Train on historical transaction data"""
        features = self._extract_features(transactions)
        self.model.fit(features)
        self.trained = True
    
    def score(self, transaction: Dict) -> Dict:
        """Score a single transaction for fraud risk"""
        if not self.trained:
            return {'error': 'Model not trained'}
        
        features = self._extract_features([transaction])
        prediction = self.model.predict(features)[0]
        score = self.model.decision_function(features)[0]
        
        return {
            'is_anomaly': prediction == -1,
            'risk_score': round((1 - score) * 50 + 50, 2),  # Normalize to 0-100
            'classification': 'high_risk' if prediction == -1 else 'normal'
        }
    
    def _extract_features(self, transactions: List[Dict]) -> np.ndarray:
        features = []
        for t in transactions:
            features.append([
                t.get('amount', 0),
                t.get('frequency', 0),
                t.get('velocity_24h', 0),
                1 if t.get('new_device') else 0,
                1 if t.get('new_location') else 0,
                t.get('hour_of_day', 12),
            ])
        return np.array(features)


# ============================================================================
# ECOMMERCE PLATFORM INTEGRATIONS
# ============================================================================

class ShopifyIntegration:
    """Integration with Shopify API"""
    
    def __init__(self, shop_url: str, access_token: str):
        try:
            import shopify
            self.shopify = shopify
        except ImportError:
            raise ImportError("ShopifyAPI not installed: pip install ShopifyAPI")
        
        self.shop_url = shop_url
        self.access_token = access_token
        self._setup_session()
    
    def _setup_session(self):
        session = self.shopify.Session(self.shop_url, '2024-01', self.access_token)
        self.shopify.ShopifyResource.activate_session(session)
    
    def get_products(self, limit: int = 50) -> List[Dict]:
        """Get products from Shopify store"""
        products = self.shopify.Product.find(limit=limit)
        return [self._format_product(p) for p in products]
    
    def _format_product(self, product) -> Dict:
        return {
            'id': product.id,
            'title': product.title,
            'handle': product.handle,
            'vendor': product.vendor,
            'product_type': product.product_type,
            'created_at': product.created_at,
            'variants': len(product.variants),
            'images': len(product.images)
        }


class WooCommerceIntegration:
    """Integration with WooCommerce API"""
    
    def __init__(self, url: str, consumer_key: str, consumer_secret: str):
        try:
            from woocommerce import API
            self.wcapi = API(
                url=url,
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                version="wc/v3"
            )
        except ImportError:
            raise ImportError("woocommerce not installed: pip install woocommerce")
    
    def get_products(self, per_page: int = 50) -> List[Dict]:
        """Get products from WooCommerce store"""
        response = self.wcapi.get("products", params={"per_page": per_page})
        return response.json()
    
    def get_orders(self, per_page: int = 50) -> List[Dict]:
        """Get orders from WooCommerce store"""
        response = self.wcapi.get("orders", params={"per_page": per_page})
        return response.json()


# ============================================================================
# TAX CALCULATION
# ============================================================================

class TaxCalculator:
    """Tax calculation using TaxJar API"""
    
    def __init__(self, api_key: str):
        try:
            import taxjar
            self.client = taxjar.Client(api_key=api_key)
        except ImportError:
            raise ImportError("taxjar not installed: pip install taxjar")
    
    def calculate(self, from_address: Dict, to_address: Dict, 
                  amount: float, shipping: float = 0) -> Dict:
        """Calculate tax for an order"""
        result = self.client.tax_for_order({
            'from_country': from_address.get('country', 'US'),
            'from_zip': from_address.get('zip'),
            'from_state': from_address.get('state'),
            'to_country': to_address.get('country', 'US'),
            'to_zip': to_address.get('zip'),
            'to_state': to_address.get('state'),
            'amount': amount,
            'shipping': shipping
        })
        
        return {
            'taxable_amount': result.taxable_amount,
            'amount_to_collect': result.amount_to_collect,
            'rate': result.rate,
            'has_nexus': result.has_nexus,
            'freight_taxable': result.freight_taxable
        }
    
    def validate_vat(self, vat_number: str) -> Dict:
        """Validate EU VAT number"""
        result = self.client.validate({'vat': vat_number})
        return {
            'valid': result.valid,
            'exists': result.exists,
            'company_name': result.vies_response.name if result.vies_response else None,
            'company_address': result.vies_response.address if result.vies_response else None
        }


# ============================================================================
# UTILITY: INTEGRATION CHECKER
# ============================================================================

def check_integrations() -> Dict[str, bool]:
    """Check which integrations are available"""
    return {
        'extruct (schema extraction)': EXTRUCT_AVAILABLE,
        'price_parser': PRICE_PARSER_AVAILABLE,
        'pytrends (Google Trends)': PYTRENDS_AVAILABLE,
        'vader (sentiment)': VADER_AVAILABLE,
        'textblob (NLP)': TEXTBLOB_AVAILABLE,
        'instaloader (Instagram)': INSTALOADER_AVAILABLE,
        'scikit-learn (ML/fraud)': SKLEARN_AVAILABLE,
    }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("Scrapling Pro Integrations Module")
    print("=" * 50)
    print("\nAvailable integrations:")
    
    status = check_integrations()
    for name, available in status.items():
        icon = "✅" if available else "❌"
        print(f"  {icon} {name}")
    
    print("\n" + "=" * 50)
    print("Example usage:")
    print("""
    # Extract product data from any ecommerce page
    from scrapling.fetchers import StealthyFetcher
    from integrations import ProductSchemaExtractor
    
    page = StealthyFetcher.fetch("https://example.com/product")
    product = ProductSchemaExtractor.extract(page.html, page.url)
    print(product)
    
    # Analyze review sentiment
    from integrations import ReviewAnalyzer
    
    analyzer = ReviewAnalyzer()
    result = analyzer.analyze_batch([
        "Great product, love it!",
        "Terrible quality, waste of money",
        "It's okay, nothing special"
    ])
    print(f"Positive: {result['positive_percentage']}%")
    
    # Track trends
    from integrations import TrendAnalyzer
    
    trends = TrendAnalyzer()
    data = trends.analyze_keywords(["iPhone 16", "Galaxy S25", "Pixel 9"])
    print(data)
    """)
