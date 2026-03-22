"""
🔐 SCRAPLING PRO - Authenticated Scraping
==========================================
Scrape websites that require login by:
1. Opening a browser for manual login
2. Saving session cookies/state
3. Using saved session for automated scraping

Features:
- Manual login with visual browser
- Session persistence (cookies saved to file)
- Automatic session reuse
- Session refresh detection
- Multi-site session management

Usage:
    from auth_scraper import AuthenticatedScraper
    
    # First time: Login manually
    scraper = AuthenticatedScraper(name="amazon")
    scraper.login_manual("https://amazon.com/login")  # Browser opens, you login
    
    # Now scrape authenticated pages
    page = scraper.fetch("https://amazon.com/your-orders")
    
    # Next time: Session is reused automatically
    scraper = AuthenticatedScraper(name="amazon")
    scraper.load_session()  # Loads saved cookies
    page = scraper.fetch("https://amazon.com/your-orders")  # Works without login!
"""

import json
import time
import pickle
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("AuthScraper")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SessionData:
    """Stored session information"""
    name: str
    domain: str
    cookies: List[Dict]
    local_storage: Dict = field(default_factory=dict)
    session_storage: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None


# ============================================================================
# AUTHENTICATED SCRAPER
# ============================================================================

class AuthenticatedScraper:
    """
    Scraper that handles authenticated sessions.
    
    Workflow:
    1. Call login_manual() - opens browser for you to login
    2. After login, cookies are saved automatically
    3. Use fetch() to scrape authenticated pages
    4. Session persists across script restarts
    
    Usage:
        # First time setup
        scraper = AuthenticatedScraper(name="mysite")
        scraper.login_manual("https://mysite.com/login")
        # Browser opens - login manually
        # Press Enter in terminal when done
        
        # Scrape authenticated content
        page = scraper.fetch("https://mysite.com/dashboard")
        products = page.css(".product")
        
        # Next time - session is restored automatically
        scraper = AuthenticatedScraper(name="mysite")
        if scraper.load_session():
            page = scraper.fetch("https://mysite.com/dashboard")  # No login needed!
    """
    
    def __init__(
        self,
        name: str,
        sessions_dir: str = "sessions",
        timeout: int = 60,
        headless: bool = False,  # Usually False for login
    ):
        """
        Args:
            name: Unique name for this site/account (e.g., "amazon", "linkedin")
            sessions_dir: Directory to store session files
            timeout: Page load timeout in seconds
            headless: Run browser in headless mode (False recommended for login)
        """
        self.name = name
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.timeout = timeout
        self.headless = headless
        
        self.session_file = self.sessions_dir / f"{name}_session.json"
        self.cookies_file = self.sessions_dir / f"{name}_cookies.pkl"
        
        self.session: Optional[SessionData] = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Try to load existing session
        self._try_load_session()
    
    def login_manual(
        self,
        login_url: str,
        success_indicator: str = None,
        wait_for_user: bool = True,
    ) -> bool:
        """
        Open browser for manual login.
        
        Args:
            login_url: URL of the login page
            success_indicator: CSS selector that appears after successful login
                              (e.g., ".user-menu", "#dashboard")
            wait_for_user: If True, waits for user to press Enter after login
            
        Returns:
            True if login successful and session saved
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install")
            return False
        
        print(f"\n{'='*60}")
        print(f"🔐 MANUAL LOGIN REQUIRED: {self.name}")
        print(f"{'='*60}")
        print(f"\n1. A browser window will open to: {login_url}")
        print(f"2. Please login with your credentials")
        print(f"3. After successful login, come back here and press ENTER")
        print(f"\n{'='*60}\n")
        
        try:
            with sync_playwright() as p:
                # Launch visible browser
                browser = p.chromium.launch(
                    headless=False,  # Always visible for login
                    args=['--start-maximized']
                )
                
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = context.new_page()
                
                # Go to login page
                page.goto(login_url, timeout=self.timeout * 1000)
                
                if wait_for_user:
                    # Wait for user to login
                    input("\n✋ Press ENTER after you have logged in successfully...")
                elif success_indicator:
                    # Wait for success indicator
                    print(f"Waiting for login success indicator: {success_indicator}")
                    page.wait_for_selector(success_indicator, timeout=300000)  # 5 min timeout
                
                # Check if login was successful
                current_url = page.url
                
                # Save session
                self._save_session_from_context(context, current_url)
                
                print(f"\n✅ Session saved successfully!")
                print(f"   Cookies: {len(self.session.cookies)}")
                print(f"   Domain: {self.session.domain}")
                
                browser.close()
                return True
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            print(f"\n❌ Login failed: {e}")
            return False
    
    def login_automated(
        self,
        login_url: str,
        username_selector: str,
        password_selector: str,
        submit_selector: str,
        username: str,
        password: str,
        success_indicator: str = None,
        pre_login_actions: List[Dict] = None,
    ) -> bool:
        """
        Automated login (use with caution - may trigger anti-bot).
        
        Args:
            login_url: Login page URL
            username_selector: CSS selector for username input
            password_selector: CSS selector for password input
            submit_selector: CSS selector for submit button
            username: Your username
            password: Your password
            success_indicator: CSS selector indicating successful login
            pre_login_actions: List of actions before login (e.g., click cookie banner)
                              [{"action": "click", "selector": ".accept-cookies"}]
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed")
            return False
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # Go to login page
                page.goto(login_url, timeout=self.timeout * 1000)
                time.sleep(2)  # Wait for page to settle
                
                # Pre-login actions (e.g., dismiss popups)
                if pre_login_actions:
                    for action in pre_login_actions:
                        if action.get('action') == 'click':
                            try:
                                page.click(action['selector'], timeout=5000)
                                time.sleep(0.5)
                            except:
                                pass
                
                # Fill credentials
                page.fill(username_selector, username)
                time.sleep(0.5)
                page.fill(password_selector, password)
                time.sleep(0.5)
                
                # Submit
                page.click(submit_selector)
                
                # Wait for login to complete
                if success_indicator:
                    page.wait_for_selector(success_indicator, timeout=30000)
                else:
                    time.sleep(5)  # Wait for redirect
                
                # Save session
                self._save_session_from_context(context, page.url)
                
                browser.close()
                return True
                
        except Exception as e:
            logger.error(f"Automated login failed: {e}")
            return False
    
    def load_session(self) -> bool:
        """
        Load saved session from file.
        
        Returns:
            True if session loaded successfully
        """
        return self._try_load_session()
    
    def fetch(
        self,
        url: str,
        wait_for: str = None,
        wait_time: float = 2.0,
    ) -> Any:
        """
        Fetch a page using the authenticated session.
        
        Args:
            url: URL to fetch
            wait_for: CSS selector to wait for before returning
            wait_time: Additional wait time in seconds
            
        Returns:
            Page object with .css(), .html, etc.
        """
        if not self.session or not self.session.cookies:
            logger.error("No session available. Call login_manual() first.")
            return None
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            # Fallback to requests with cookies
            return self._fetch_with_requests(url)
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                # Add saved cookies
                context.add_cookies(self.session.cookies)
                
                page = context.new_page()
                page.goto(url, timeout=self.timeout * 1000)
                
                if wait_for:
                    try:
                        page.wait_for_selector(wait_for, timeout=10000)
                    except:
                        pass
                
                if wait_time:
                    time.sleep(wait_time)
                
                # Get page content
                html = page.content()
                current_url = page.url
                
                # Update session cookies (they may have been refreshed)
                new_cookies = context.cookies()
                if new_cookies:
                    self.session.cookies = new_cookies
                    self.session.last_used = datetime.now().isoformat()
                    self._save_session()
                
                browser.close()
                
                # Return a page-like object
                return self._create_page_object(html, current_url)
                
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            return None
    
    def fetch_multiple(
        self,
        urls: List[str],
        wait_for: str = None,
        wait_time: float = 1.0,
    ) -> List[Any]:
        """
        Fetch multiple pages efficiently (reuses browser context).
        """
        if not self.session:
            logger.error("No session available")
            return []
        
        results = []
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                context.add_cookies(self.session.cookies)
                
                page = context.new_page()
                
                for url in urls:
                    try:
                        page.goto(url, timeout=self.timeout * 1000)
                        
                        if wait_for:
                            try:
                                page.wait_for_selector(wait_for, timeout=5000)
                            except:
                                pass
                        
                        time.sleep(wait_time)
                        
                        html = page.content()
                        results.append(self._create_page_object(html, url))
                        
                    except Exception as e:
                        logger.error(f"Failed to fetch {url}: {e}")
                        results.append(None)
                
                # Update cookies
                self.session.cookies = context.cookies()
                self._save_session()
                
                browser.close()
                
        except ImportError:
            # Fallback to sequential requests
            for url in urls:
                results.append(self._fetch_with_requests(url))
        
        return results
    
    def is_session_valid(self) -> bool:
        """Check if current session appears valid"""
        if not self.session:
            return False
        
        if not self.session.cookies:
            return False
        
        # Check if cookies have expired
        now = datetime.now()
        for cookie in self.session.cookies:
            if 'expires' in cookie:
                try:
                    expires = datetime.fromtimestamp(cookie['expires'])
                    if expires > now:
                        return True  # At least one cookie is still valid
                except:
                    pass
        
        # If no expiry info, assume valid if created recently
        try:
            created = datetime.fromisoformat(self.session.created_at)
            if now - created < timedelta(days=7):
                return True
        except:
            pass
        
        return False
    
    def clear_session(self):
        """Clear saved session"""
        self.session = None
        
        if self.session_file.exists():
            self.session_file.unlink()
        
        if self.cookies_file.exists():
            self.cookies_file.unlink()
        
        logger.info(f"Session cleared: {self.name}")
    
    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================
    
    def _try_load_session(self) -> bool:
        """Try to load session from file"""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self.session = SessionData(**data)
                    logger.info(f"Session loaded: {self.name} ({len(self.session.cookies)} cookies)")
                    return True
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")
        
        return False
    
    def _save_session(self):
        """Save current session to file"""
        if not self.session:
            return
        
        try:
            with open(self.session_file, 'w') as f:
                json.dump({
                    'name': self.session.name,
                    'domain': self.session.domain,
                    'cookies': self.session.cookies,
                    'local_storage': self.session.local_storage,
                    'session_storage': self.session.session_storage,
                    'created_at': self.session.created_at,
                    'last_used': self.session.last_used,
                    'expires_at': self.session.expires_at,
                }, f, indent=2)
            
            logger.debug(f"Session saved: {self.name}")
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def _save_session_from_context(self, context, current_url: str):
        """Extract and save session from browser context"""
        from urllib.parse import urlparse
        
        domain = urlparse(current_url).netloc
        cookies = context.cookies()
        
        self.session = SessionData(
            name=self.name,
            domain=domain,
            cookies=cookies,
        )
        
        self._save_session()
    
    def _fetch_with_requests(self, url: str):
        """Fallback: fetch using requests library"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Convert playwright cookies to requests format
            session = requests.Session()
            for cookie in self.session.cookies:
                session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie.get('domain', ''),
                    path=cookie.get('path', '/')
                )
            
            response = session.get(url, timeout=self.timeout)
            
            return self._create_page_object(response.text, url, response.status_code)
            
        except Exception as e:
            logger.error(f"Requests fallback failed: {e}")
            return None
    
    def _create_page_object(self, html: str, url: str, status: int = 200):
        """Create a page-like object from HTML"""
        try:
            from bs4 import BeautifulSoup
            
            class PageObject:
                def __init__(self, html, url, status):
                    self.html = html
                    self.url = url
                    self.status = status
                    self._soup = BeautifulSoup(html, 'html.parser')
                
                def css(self, selector: str):
                    return self._soup.select(selector)
                
                def css_first(self, selector: str):
                    result = self._soup.select_one(selector)
                    return result
                
                def text(self):
                    return self._soup.get_text()
            
            return PageObject(html, url, status)
            
        except ImportError:
            # Return raw HTML if BeautifulSoup not available
            class RawPage:
                def __init__(self, html, url, status):
                    self.html = html
                    self.url = url
                    self.status = status
            
            return RawPage(html, url, status)


# ============================================================================
# SESSION MANAGER
# ============================================================================

class SessionManager:
    """
    Manage multiple authenticated sessions.
    
    Usage:
        manager = SessionManager()
        
        # List all sessions
        sessions = manager.list_sessions()
        
        # Get scraper for specific site
        amazon = manager.get_scraper("amazon")
        linkedin = manager.get_scraper("linkedin")
    """
    
    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self._scrapers: Dict[str, AuthenticatedScraper] = {}
    
    def list_sessions(self) -> List[Dict]:
        """List all saved sessions"""
        sessions = []
        
        for file in self.sessions_dir.glob("*_session.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    sessions.append({
                        'name': data.get('name'),
                        'domain': data.get('domain'),
                        'created_at': data.get('created_at'),
                        'last_used': data.get('last_used'),
                        'cookies_count': len(data.get('cookies', [])),
                    })
            except:
                pass
        
        return sessions
    
    def get_scraper(self, name: str) -> AuthenticatedScraper:
        """Get or create scraper for a site"""
        if name not in self._scrapers:
            self._scrapers[name] = AuthenticatedScraper(
                name=name,
                sessions_dir=str(self.sessions_dir)
            )
        return self._scrapers[name]
    
    def delete_session(self, name: str) -> bool:
        """Delete a saved session"""
        session_file = self.sessions_dir / f"{name}_session.json"
        
        if session_file.exists():
            session_file.unlink()
            if name in self._scrapers:
                del self._scrapers[name]
            return True
        
        return False


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🔐 Scrapling Pro - Authenticated Scraping")
    print("=" * 50)
    print("""
Usage:

    from auth_scraper import AuthenticatedScraper, SessionManager
    
    # === FIRST TIME: Manual Login ===
    scraper = AuthenticatedScraper(name="amazon")
    
    # Opens browser - you login manually
    scraper.login_manual("https://amazon.com/ap/signin")
    
    # Now scrape authenticated pages
    page = scraper.fetch("https://amazon.com/gp/css/order-history")
    orders = page.css(".order-card")
    
    
    # === NEXT TIME: Session Restored ===
    scraper = AuthenticatedScraper(name="amazon")
    
    if scraper.is_session_valid():
        # No login needed!
        page = scraper.fetch("https://amazon.com/gp/css/order-history")
    else:
        # Session expired, login again
        scraper.login_manual("https://amazon.com/ap/signin")
    
    
    # === MANAGE MULTIPLE SITES ===
    manager = SessionManager()
    
    # List all saved sessions
    print(manager.list_sessions())
    
    # Get scrapers for different sites
    amazon = manager.get_scraper("amazon")
    linkedin = manager.get_scraper("linkedin")
    shopify = manager.get_scraper("shopify_admin")
    
    
    # === AUTOMATED LOGIN (use carefully) ===
    scraper.login_automated(
        login_url="https://site.com/login",
        username_selector="#email",
        password_selector="#password",
        submit_selector="#login-btn",
        username="your@email.com",
        password="your_password",
        success_indicator=".dashboard"
    )
    """)
