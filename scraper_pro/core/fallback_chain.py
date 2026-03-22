"""
🔄 Fallback Chain Utility
=========================
Provides intelligent fallback chains for all integrations.
Automatically tries primary tool, falls back to secondary/tertiary on failure.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar
from functools import wraps
from dataclasses import dataclass
import time

logger = logging.getLogger("FallbackChain")

T = TypeVar('T')


@dataclass
class ToolResult:
    """Result from a tool execution"""
    success: bool
    data: Any
    tool_name: str
    execution_time: float
    error: Optional[str] = None


class FallbackChain:
    """
    Executes tools in priority order with automatic fallback.
    
    Example:
        chain = FallbackChain([
            ("extruct", extract_with_extruct),
            ("beautifulsoup", extract_with_bs),
            ("regex", extract_with_regex),
        ])
        result = chain.execute(html, url)
    """
    
    def __init__(
        self, 
        tools: List[Tuple[str, Callable]], 
        name: str = "unnamed",
        cache_results: bool = True
    ):
        """
        Args:
            tools: List of (tool_name, callable) in priority order
            name: Name of this chain for logging
            cache_results: Whether to cache successful results
        """
        self.tools = tools
        self.name = name
        self.cache_results = cache_results
        self.stats = {tool[0]: {"success": 0, "fail": 0, "time": 0} for tool in tools}
        self._cache: Dict[str, ToolResult] = {}
    
    def execute(self, *args, cache_key: str = None, **kwargs) -> ToolResult:
        """
        Execute tools in order until one succeeds.
        
        Args:
            *args, **kwargs: Passed to each tool function
            cache_key: Optional key for caching results
            
        Returns:
            ToolResult with data from first successful tool
        """
        # Check cache
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]
        
        errors = []
        
        for tool_name, tool_func in self.tools:
            start = time.time()
            try:
                result = tool_func(*args, **kwargs)
                exec_time = time.time() - start
                
                # Check if result is valid (not None, not empty)
                if result is not None and result != {} and result != []:
                    self.stats[tool_name]["success"] += 1
                    self.stats[tool_name]["time"] += exec_time
                    
                    tool_result = ToolResult(
                        success=True,
                        data=result,
                        tool_name=tool_name,
                        execution_time=exec_time
                    )
                    
                    if cache_key and self.cache_results:
                        self._cache[cache_key] = tool_result
                    
                    logger.debug(f"[{self.name}] {tool_name} succeeded in {exec_time:.3f}s")
                    return tool_result
                else:
                    raise ValueError("Empty result")
                    
            except Exception as e:
                exec_time = time.time() - start
                self.stats[tool_name]["fail"] += 1
                errors.append(f"{tool_name}: {str(e)[:100]}")
                logger.debug(f"[{self.name}] {tool_name} failed: {e}")
                continue
        
        # All tools failed
        return ToolResult(
            success=False,
            data=None,
            tool_name="none",
            execution_time=0,
            error="; ".join(errors)
        )
    
    def get_stats(self) -> Dict[str, Dict]:
        """Get usage statistics for all tools"""
        stats = {}
        for tool_name, data in self.stats.items():
            total = data["success"] + data["fail"]
            stats[tool_name] = {
                "total_calls": total,
                "success_rate": data["success"] / total if total > 0 else 0,
                "avg_time": data["time"] / data["success"] if data["success"] > 0 else 0,
            }
        return stats
    
    def clear_cache(self):
        """Clear the result cache"""
        self._cache.clear()


class SmartFallback:
    """
    Decorator for creating fallback-enabled functions.
    
    Example:
        @SmartFallback.with_fallbacks([
            secondary_implementation,
            tertiary_implementation,
        ])
        def primary_implementation(data):
            return process(data)
    """
    
    @staticmethod
    def with_fallbacks(fallback_funcs: List[Callable]):
        """Decorator that adds fallback functions"""
        def decorator(primary_func: Callable) -> Callable:
            @wraps(primary_func)
            def wrapper(*args, **kwargs):
                # Try primary
                try:
                    result = primary_func(*args, **kwargs)
                    if result is not None and result != {} and result != []:
                        return result
                except Exception as e:
                    logger.debug(f"Primary {primary_func.__name__} failed: {e}")
                
                # Try fallbacks
                for i, fallback in enumerate(fallback_funcs):
                    try:
                        result = fallback(*args, **kwargs)
                        if result is not None and result != {} and result != []:
                            logger.debug(f"Fallback {i+1} succeeded for {primary_func.__name__}")
                            return result
                    except Exception as e:
                        logger.debug(f"Fallback {i+1} failed: {e}")
                        continue
                
                return None
            
            return wrapper
        return decorator


# ============================================================================
# AVAILABILITY CHECKERS
# ============================================================================

def check_tool_availability() -> Dict[str, bool]:
    """Check which tools are available"""
    availability = {}
    
    # Schema extraction
    try:
        import extruct
        availability["extruct"] = True
    except ImportError:
        availability["extruct"] = False
    
    try:
        from pyld import jsonld
        availability["pyld"] = True
    except ImportError:
        availability["pyld"] = False
    
    # Price parsing
    try:
        from price_parser import Price
        availability["price_parser"] = True
    except ImportError:
        availability["price_parser"] = False
    
    # Text cleaning
    try:
        import ftfy
        availability["ftfy"] = True
    except ImportError:
        availability["ftfy"] = False
    
    # Sentiment
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        availability["vader"] = True
    except ImportError:
        availability["vader"] = False
    
    try:
        from textblob import TextBlob
        availability["textblob"] = True
    except ImportError:
        availability["textblob"] = False
    
    # Trends
    try:
        from pytrends.request import TrendReq
        availability["pytrends"] = True
    except ImportError:
        availability["pytrends"] = False
    
    # NLP
    try:
        import spacy
        availability["spacy"] = True
    except ImportError:
        availability["spacy"] = False
    
    # Social
    try:
        import instaloader
        availability["instaloader"] = True
    except ImportError:
        availability["instaloader"] = False
    
    try:
        import snscrape
        availability["snscrape"] = True
    except ImportError:
        availability["snscrape"] = False
    
    # ML
    try:
        import sklearn
        availability["sklearn"] = True
    except ImportError:
        availability["sklearn"] = False
    
    try:
        from pyod.models.iforest import IForest
        availability["pyod"] = True
    except ImportError:
        availability["pyod"] = False
    
    # Commerce
    try:
        import shopify
        availability["shopify"] = True
    except ImportError:
        availability["shopify"] = False
    
    try:
        from woocommerce import API
        availability["woocommerce"] = True
    except ImportError:
        availability["woocommerce"] = False
    
    return availability


def print_availability():
    """Print tool availability status"""
    status = check_tool_availability()
    
    print("\n📦 Tool Availability Status")
    print("=" * 50)
    
    categories = {
        "Schema Extraction": ["extruct", "pyld"],
        "Price Parsing": ["price_parser"],
        "Text Cleaning": ["ftfy"],
        "Sentiment Analysis": ["vader", "textblob"],
        "Trend Analysis": ["pytrends"],
        "NLP": ["spacy"],
        "Social Media": ["instaloader", "snscrape"],
        "Machine Learning": ["sklearn", "pyod"],
        "E-Commerce": ["shopify", "woocommerce"],
    }
    
    for category, tools in categories.items():
        print(f"\n{category}:")
        for tool in tools:
            icon = "✅" if status.get(tool, False) else "❌"
            print(f"  {icon} {tool}")
    
    available = sum(1 for v in status.values() if v)
    total = len(status)
    print(f"\n📊 {available}/{total} tools available ({available/total*100:.0f}%)")
    
    return status


if __name__ == "__main__":
    print_availability()
