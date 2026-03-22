"""
🕷️ SCRAPLING PRO - Advanced Proxy Management
==============================================
Professional proxy rotation with health checking, geo-targeting, and analytics.

Features:
- Multiple rotation strategies
- Automatic health checking
- Geo-targeting support
- Session stickiness
- Proxy pool management
- Performance analytics
"""

import time
import random
import threading
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger("ScraplingPro.Proxy")


# ============================================================================
# PROXY DATA STRUCTURES
# ============================================================================

@dataclass
class Proxy:
    """Enhanced proxy configuration"""
    host: str
    port: int
    username: str = ""
    password: str = ""
    protocol: str = "http"  # http, https, socks5
    country: str = ""
    city: str = ""
    isp: str = ""
    
    # Performance metrics
    success_count: int = 0
    fail_count: int = 0
    total_response_time: float = 0
    last_used: float = 0
    last_success: float = 0
    last_fail: float = 0
    cooldown_until: float = 0
    
    # Session tracking
    session_id: str = ""
    sticky_until: float = 0
    
    @property
    def url(self) -> str:
        """Get proxy URL string"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.fail_count
        return self.success_count / max(1, total)
    
    @property
    def avg_response_time(self) -> float:
        """Average response time in seconds"""
        return self.total_response_time / max(1, self.success_count)
    
    @property
    def is_available(self) -> bool:
        """Check if proxy is currently available"""
        return time.time() > self.cooldown_until
    
    @property
    def score(self) -> float:
        """Calculate proxy quality score (0-1)"""
        # Weighted score based on success rate and response time
        success_weight = 0.7
        speed_weight = 0.3
        
        # Normalize response time (faster = higher score)
        # Assume good response time is < 2s, bad is > 10s
        speed_score = max(0, 1 - (self.avg_response_time / 10))
        
        return (self.success_rate * success_weight) + (speed_score * speed_weight)
    
    def to_dict(self) -> Dict:
        """Convert to dict for fetcher kwargs"""
        return {
            "server": f"{self.protocol}://{self.host}:{self.port}",
            "username": self.username,
            "password": self.password,
        }
    
    @classmethod
    def from_url(cls, url: str, **kwargs) -> "Proxy":
        """Parse proxy from URL string"""
        # Pattern: protocol://user:pass@host:port or protocol://host:port
        pattern = r'^(https?|socks5)?:?/?/?(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$'
        match = re.match(pattern, url.strip())
        
        if match:
            protocol, username, password, host, port = match.groups()
            return cls(
                host=host,
                port=int(port),
                username=username or "",
                password=password or "",
                protocol=protocol or "http",
                **kwargs
            )
        else:
            raise ValueError(f"Invalid proxy URL: {url}")


# ============================================================================
# PROXY PROVIDERS
# ============================================================================

class ProxyProvider:
    """Base class for proxy providers"""
    
    name: str = "Base"
    
    def get_proxies(self) -> List[Proxy]:
        raise NotImplementedError
    
    def refresh(self):
        """Refresh proxy list"""
        pass


class FileProxyProvider(ProxyProvider):
    """Load proxies from a file"""
    
    name = "File"
    
    def __init__(self, filepath: str, format: str = "url"):
        """
        Args:
            filepath: Path to proxy file
            format: "url" (one proxy URL per line) or "json"
        """
        self.filepath = filepath
        self.format = format
    
    def get_proxies(self) -> List[Proxy]:
        proxies = []
        
        with open(self.filepath, 'r') as f:
            if self.format == "json":
                data = json.load(f)
                for item in data:
                    if isinstance(item, str):
                        proxies.append(Proxy.from_url(item))
                    else:
                        proxies.append(Proxy(**item))
            else:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            proxies.append(Proxy.from_url(line))
                        except ValueError:
                            logger.warning(f"Invalid proxy: {line}")
        
        return proxies


class ListProxyProvider(ProxyProvider):
    """Proxy provider from a list of URLs"""
    
    name = "List"
    
    def __init__(self, proxy_urls: List[str]):
        self.proxy_urls = proxy_urls
    
    def get_proxies(self) -> List[Proxy]:
        return [Proxy.from_url(url) for url in self.proxy_urls]


class RotatingProxyProvider(ProxyProvider):
    """
    Provider for rotating proxy services like BrightData, SmartProxy, etc.
    
    These services use a single endpoint that automatically rotates IPs.
    """
    
    name = "Rotating"
    
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        protocol: str = "http",
        session_prefix: str = "session",
        num_sessions: int = 10
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.protocol = protocol
        self.session_prefix = session_prefix
        self.num_sessions = num_sessions
    
    def get_proxies(self) -> List[Proxy]:
        """Generate session-based proxy entries"""
        proxies = []
        
        for i in range(self.num_sessions):
            # Create session-based username (format varies by provider)
            session_user = f"{self.username}-{self.session_prefix}-{i}"
            
            proxies.append(Proxy(
                host=self.host,
                port=self.port,
                username=session_user,
                password=self.password,
                protocol=self.protocol,
                session_id=f"session_{i}"
            ))
        
        return proxies


# ============================================================================
# ADVANCED PROXY MANAGER
# ============================================================================

class AdvancedProxyManager:
    """
    Advanced proxy management with multiple strategies and features.
    
    Strategies:
    - round_robin: Cycle through proxies in order
    - random: Random selection
    - weighted: Prefer better performing proxies
    - geo: Select by country/region
    - sticky: Maintain session with same proxy
    - least_used: Prefer less frequently used proxies
    
    Example:
        manager = AdvancedProxyManager(
            providers=[FileProxyProvider("proxies.txt")],
            strategy="weighted",
            health_check_interval=300
        )
        
        proxy = manager.get_proxy()
        # ... use proxy ...
        manager.report_success(proxy, response_time=1.2)
    """
    
    def __init__(
        self,
        providers: List[ProxyProvider] = None,
        proxies: List[str] = None,
        strategy: str = "weighted",
        health_check_interval: int = 300,
        max_fails_before_cooldown: int = 3,
        cooldown_seconds: int = 300,
        min_success_rate: float = 0.2,
        sticky_session_duration: int = 600,
    ):
        self.strategy = strategy
        self.health_check_interval = health_check_interval
        self.max_fails_before_cooldown = max_fails_before_cooldown
        self.cooldown_seconds = cooldown_seconds
        self.min_success_rate = min_success_rate
        self.sticky_session_duration = sticky_session_duration
        
        self.proxies: Dict[str, Proxy] = {}
        self.providers = providers or []
        
        # Index for round-robin
        self._rr_index = 0
        self._lock = threading.Lock()
        
        # Domain -> proxy mapping for sticky sessions
        self._sticky_sessions: Dict[str, str] = {}
        
        # Analytics
        self._requests_per_proxy = defaultdict(int)
        self._errors_per_proxy = defaultdict(list)
        
        # Load initial proxies
        if proxies:
            self.providers.append(ListProxyProvider(proxies))
        
        self.refresh_proxies()
        
        # Start health checker
        self._health_thread = None
        if health_check_interval > 0:
            self._start_health_checker()
    
    def refresh_proxies(self):
        """Load/reload proxies from all providers"""
        with self._lock:
            for provider in self.providers:
                for proxy in provider.get_proxies():
                    key = f"{proxy.host}:{proxy.port}"
                    if key not in self.proxies:
                        self.proxies[key] = proxy
                    else:
                        # Preserve stats for existing proxies
                        existing = self.proxies[key]
                        proxy.success_count = existing.success_count
                        proxy.fail_count = existing.fail_count
                        proxy.total_response_time = existing.total_response_time
                        self.proxies[key] = proxy
        
        logger.info(f"Loaded {len(self.proxies)} proxies")
    
    def _get_available_proxies(
        self,
        country: str = None,
        exclude: Set[str] = None
    ) -> List[Proxy]:
        """Get list of currently available proxies"""
        now = time.time()
        available = []
        
        for key, proxy in self.proxies.items():
            # Check cooldown
            if proxy.cooldown_until > now:
                continue
            
            # Check minimum success rate (if enough requests)
            if proxy.success_count + proxy.fail_count >= 10:
                if proxy.success_rate < self.min_success_rate:
                    continue
            
            # Check country filter
            if country and proxy.country and proxy.country.lower() != country.lower():
                continue
            
            # Check exclusions
            if exclude and key in exclude:
                continue
            
            available.append(proxy)
        
        return available
    
    def get_proxy(
        self,
        domain: str = None,
        country: str = None,
        exclude: Set[str] = None,
        sticky: bool = False
    ) -> Optional[Proxy]:
        """
        Get a proxy based on the configured strategy.
        
        Args:
            domain: Target domain (for sticky sessions)
            country: Filter by country code
            exclude: Set of proxy keys to exclude
            sticky: Enable sticky session for this domain
        """
        with self._lock:
            # Check for sticky session
            if sticky and domain:
                sticky_key = self._sticky_sessions.get(domain)
                if sticky_key and sticky_key in self.proxies:
                    proxy = self.proxies[sticky_key]
                    if proxy.is_available and proxy.sticky_until > time.time():
                        return proxy
            
            available = self._get_available_proxies(country, exclude)
            
            if not available:
                logger.warning("No available proxies")
                return None
            
            # Select based on strategy
            if self.strategy == "round_robin":
                proxy = available[self._rr_index % len(available)]
                self._rr_index += 1
            
            elif self.strategy == "random":
                proxy = random.choice(available)
            
            elif self.strategy == "weighted":
                # Weight by score
                weights = [p.score for p in available]
                # Add small base weight to give all proxies a chance
                weights = [w + 0.1 for w in weights]
                proxy = random.choices(available, weights=weights, k=1)[0]
            
            elif self.strategy == "least_used":
                # Sort by usage count
                available.sort(key=lambda p: p.success_count + p.fail_count)
                proxy = available[0]
            
            else:
                proxy = available[0]
            
            # Update tracking
            proxy.last_used = time.time()
            self._requests_per_proxy[f"{proxy.host}:{proxy.port}"] += 1
            
            # Set up sticky session
            if sticky and domain:
                proxy.sticky_until = time.time() + self.sticky_session_duration
                self._sticky_sessions[domain] = f"{proxy.host}:{proxy.port}"
            
            return proxy
    
    def report_success(self, proxy: Proxy, response_time: float = 0):
        """Report successful request"""
        with self._lock:
            key = f"{proxy.host}:{proxy.port}"
            if key in self.proxies:
                p = self.proxies[key]
                p.success_count += 1
                p.last_success = time.time()
                if response_time > 0:
                    p.total_response_time += response_time
    
    def report_failure(self, proxy: Proxy, error: str = ""):
        """Report failed request"""
        with self._lock:
            key = f"{proxy.host}:{proxy.port}"
            if key in self.proxies:
                p = self.proxies[key]
                p.fail_count += 1
                p.last_fail = time.time()
                
                # Track error
                self._errors_per_proxy[key].append({
                    "time": datetime.now().isoformat(),
                    "error": error
                })
                
                # Check for cooldown
                recent_fails = sum(
                    1 for e in self._errors_per_proxy[key][-10:]
                    if datetime.fromisoformat(e["time"]) > datetime.now() - timedelta(minutes=5)
                )
                
                if recent_fails >= self.max_fails_before_cooldown:
                    p.cooldown_until = time.time() + self.cooldown_seconds
                    logger.warning(f"Proxy {key} put on cooldown for {self.cooldown_seconds}s")
    
    def _start_health_checker(self):
        """Start background health check thread"""
        def health_check_loop():
            while True:
                time.sleep(self.health_check_interval)
                self._run_health_checks()
        
        self._health_thread = threading.Thread(target=health_check_loop, daemon=True)
        self._health_thread.start()
    
    def _run_health_checks(self):
        """Run health checks on all proxies"""
        from scrapling.fetchers import StealthyFetcher
        
        test_url = "https://httpbin.org/ip"
        
        for key, proxy in list(self.proxies.items()):
            try:
                start = time.time()
                page = StealthyFetcher.fetch(
                    test_url,
                    proxy=proxy.url,
                    timeout=10
                )
                
                if page.status == 200:
                    self.report_success(proxy, time.time() - start)
                else:
                    self.report_failure(proxy, f"Status {page.status}")
                    
            except Exception as e:
                self.report_failure(proxy, str(e))
    
    def get_stats(self) -> Dict:
        """Get comprehensive proxy statistics"""
        with self._lock:
            stats = {
                "total_proxies": len(self.proxies),
                "available_proxies": len(self._get_available_proxies()),
                "strategy": self.strategy,
                "proxies": {}
            }
            
            for key, proxy in self.proxies.items():
                stats["proxies"][key] = {
                    "success_rate": proxy.success_rate,
                    "avg_response_time": proxy.avg_response_time,
                    "total_requests": proxy.success_count + proxy.fail_count,
                    "score": proxy.score,
                    "is_available": proxy.is_available,
                    "country": proxy.country,
                }
            
            # Overall stats
            total_success = sum(p.success_count for p in self.proxies.values())
            total_fail = sum(p.fail_count for p in self.proxies.values())
            
            stats["overall"] = {
                "total_requests": total_success + total_fail,
                "success_rate": total_success / max(1, total_success + total_fail),
                "avg_response_time": sum(p.total_response_time for p in self.proxies.values()) / max(1, total_success),
            }
            
            return stats
    
    def get_best_proxies(self, n: int = 10) -> List[Proxy]:
        """Get the top N performing proxies"""
        with self._lock:
            available = self._get_available_proxies()
            # Sort by score
            available.sort(key=lambda p: p.score, reverse=True)
            return available[:n]
    
    def remove_proxy(self, proxy: Proxy):
        """Remove a proxy from the pool"""
        with self._lock:
            key = f"{proxy.host}:{proxy.port}"
            if key in self.proxies:
                del self.proxies[key]
                logger.info(f"Removed proxy {key}")
    
    def add_proxy(self, proxy: Proxy):
        """Add a new proxy to the pool"""
        with self._lock:
            key = f"{proxy.host}:{proxy.port}"
            self.proxies[key] = proxy


# ============================================================================
# GEO-TARGETING HELPER
# ============================================================================

class GeoProxySelector:
    """
    Select proxies based on geographic requirements.
    
    Example:
        selector = GeoProxySelector(manager)
        proxy = selector.get_proxy_for_region("US", ["CA", "NY"])
    """
    
    def __init__(self, manager: AdvancedProxyManager):
        self.manager = manager
    
    def get_proxy_for_country(self, country: str) -> Optional[Proxy]:
        """Get a proxy from a specific country"""
        return self.manager.get_proxy(country=country)
    
    def get_proxy_for_region(
        self,
        country: str,
        regions: List[str] = None
    ) -> Optional[Proxy]:
        """Get a proxy from a specific country/region"""
        proxy = self.manager.get_proxy(country=country)
        
        if proxy and regions and proxy.city:
            # Check if proxy is in desired region
            if proxy.city not in regions:
                # Try to find one in the right region
                for _ in range(10):  # Try up to 10 times
                    p = self.manager.get_proxy(country=country)
                    if p and p.city in regions:
                        return p
        
        return proxy


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    print("🕷️ Scrapling Pro - Advanced Proxy Management")
    print("=" * 50)
    
    # Demo with sample proxies
    sample_proxies = [
        "http://user:pass@proxy1.example.com:8080",
        "http://user:pass@proxy2.example.com:8080",
        "http://user:pass@proxy3.example.com:8080",
    ]
    
    # Note: These are example URLs and won't actually work
    print("\nDemo with sample proxy configuration:")
    print("  Strategy: weighted")
    print("  Health check: every 5 minutes")
    print("  Cooldown: 5 minutes after 3 failures")
    
    print("\n  Usage:")
    print("""
    manager = AdvancedProxyManager(
        proxies=["http://user:pass@proxy:8080"],
        strategy="weighted"
    )
    
    proxy = manager.get_proxy(domain="example.com", sticky=True)
    
    try:
        # Use proxy
        page = StealthyFetcher.fetch(url, proxy=proxy.url)
        manager.report_success(proxy, response_time=1.2)
    except Exception as e:
        manager.report_failure(proxy, str(e))
    """)
