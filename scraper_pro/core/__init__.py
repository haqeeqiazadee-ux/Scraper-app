"""
🕷️ Scrapling Pro - Core Module
==============================
Contains the main engine components and smart extractors.
"""

from .fallback_chain import (
    FallbackChain,
    ToolResult,
    SmartFallback,
    check_tool_availability,
    print_availability,
)

from .smart_extractors import (
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

__all__ = [
    # Fallback chain
    'FallbackChain',
    'ToolResult',
    'SmartFallback',
    'check_tool_availability',
    'print_availability',
    
    # Data structures
    'ProductData',
    'SentimentResult',
    'TrendData',
    'InfluencerProfile',
    
    # Extractors
    'SmartProductExtractor',
    'SmartSentimentAnalyzer',
    'SmartTrendAnalyzer',
    'SmartInfluencerAnalyzer',
    'SmartExtractors',
    
    # Convenience
    'get_extractors',
    'extract_product',
    'analyze_sentiment',
    'analyze_trends',
]
