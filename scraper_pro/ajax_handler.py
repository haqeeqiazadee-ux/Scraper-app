"""
🔄 SCRAPLING PRO - Advanced AJAX & Dynamic Content Handler
==========================================================
Handles all types of dynamically loaded content:
- Infinite scroll
- Load more buttons  
- AJAX pagination
- Lazy-loaded images
- Tab/accordion content
- Auto-updating content
- Single Page Applications (SPAs)

Usage:
    from ajax_handler import AjaxHandler
    
    handler = AjaxHandler()
    
    # Infinite scroll
    items = handler.scroll_until_end(page, ".product-card", max_items=100)
    
    # Load more button
    items = handler.click_load_more(page, ".load-more-btn", ".product-card")
    
    # Wait for AJAX content
    handler.wait_for_content(page, ".results-container")
"""

import time
import logging
import re
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("AjaxHandler")


# ============================================================================
# AJAX HANDLER
# ============================================================================

class AjaxHandler:
    """
    Comprehensive handler for AJAX and dynamically loaded content.
    
    Works with PlayWrightFetcher/DynamicFetcher from scrapling.
    """
    
    def __init__(
        self,
        scroll_pause: float = 1.5,
        click_pause: float = 1.0,
        load_timeout: float = 10.0,
        max_retries: int = 3,
    ):
        """
        Args:
            scroll_pause: Seconds to wait after each scroll
            click_pause: Seconds to wait after each click
            load_timeout: Max seconds to wait for content to load
            max_retries: Retries for failed operations
        """
        self.scroll_pause = scroll_pause
        self.click_pause = click_pause
        self.load_timeout = load_timeout
        self.max_retries = max_retries
    
    # ========================================================================
    # INFINITE SCROLL
    # ========================================================================
    
    def scroll_until_end(
        self,
        page,
        item_selector: str,
        max_items: int = None,
        max_scrolls: int = 50,
        no_new_items_limit: int = 3,
    ) -> List[Any]:
        """
        Scroll page until no more content loads.
        
        Args:
            page: PlayWright page object
            item_selector: CSS selector for items to collect
            max_items: Stop after collecting this many items
            max_scrolls: Maximum number of scroll operations
            no_new_items_limit: Stop after this many scrolls with no new items
            
        Returns:
            List of collected elements
        """
        collected = []
        seen_hashes = set()
        no_new_count = 0
        
        logger.info(f"Starting infinite scroll for: {item_selector}")
        
        for scroll_num in range(max_scrolls):
            # Get current items
            items = self._safe_css(page, item_selector)
            new_items = 0
            
            for item in items:
                item_hash = self._hash_element(item)
                if item_hash not in seen_hashes:
                    seen_hashes.add(item_hash)
                    collected.append(item)
                    new_items += 1
                    
                    if max_items and len(collected) >= max_items:
                        logger.info(f"Reached max items: {max_items}")
                        return collected
            
            if new_items == 0:
                no_new_count += 1
                if no_new_count >= no_new_items_limit:
                    logger.info(f"No new items after {no_new_items_limit} scrolls, stopping")
                    break
            else:
                no_new_count = 0
                logger.debug(f"Scroll {scroll_num + 1}: Found {new_items} new items (total: {len(collected)})")
            
            # Scroll down
            self._scroll_down(page)
            time.sleep(self.scroll_pause)
            
            # Check if at bottom
            if self._is_at_bottom(page):
                logger.info("Reached bottom of page")
                break
        
        logger.info(f"Scroll complete: collected {len(collected)} items")
        return collected
    
    def scroll_with_callback(
        self,
        page,
        item_selector: str,
        callback: Callable[[Any], Dict],
        max_items: int = None,
        max_scrolls: int = 50,
    ) -> List[Dict]:
        """
        Scroll and process items with a callback function.
        
        Args:
            page: Page object
            item_selector: CSS selector for items
            callback: Function to process each item, returns dict
            max_items: Maximum items to collect
            max_scrolls: Maximum scrolls
            
        Returns:
            List of processed item dicts
        """
        results = []
        seen_hashes = set()
        
        for scroll_num in range(max_scrolls):
            items = self._safe_css(page, item_selector)
            
            for item in items:
                item_hash = self._hash_element(item)
                if item_hash not in seen_hashes:
                    seen_hashes.add(item_hash)
                    
                    try:
                        result = callback(item)
                        if result:
                            results.append(result)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                    
                    if max_items and len(results) >= max_items:
                        return results
            
            self._scroll_down(page)
            time.sleep(self.scroll_pause)
            
            if self._is_at_bottom(page):
                break
        
        return results
    
    # ========================================================================
    # LOAD MORE BUTTON
    # ========================================================================
    
    def click_load_more(
        self,
        page,
        button_selector: str,
        item_selector: str,
        max_clicks: int = 20,
        max_items: int = None,
    ) -> List[Any]:
        """
        Click "Load More" button repeatedly to load all content.
        
        Args:
            page: Page object
            button_selector: CSS selector for load more button
            item_selector: CSS selector for items
            max_clicks: Maximum button clicks
            max_items: Stop after this many items
            
        Returns:
            List of collected elements
        """
        collected = []
        seen_hashes = set()
        
        logger.info(f"Starting load more clicks: {button_selector}")
        
        for click_num in range(max_clicks):
            # Collect current items
            items = self._safe_css(page, item_selector)
            
            for item in items:
                item_hash = self._hash_element(item)
                if item_hash not in seen_hashes:
                    seen_hashes.add(item_hash)
                    collected.append(item)
                    
                    if max_items and len(collected) >= max_items:
                        return collected
            
            # Try to click load more button
            button = self._safe_css_first(page, button_selector)
            
            if not button:
                logger.info("Load more button not found, stopping")
                break
            
            # Check if button is visible/enabled
            if not self._is_clickable(button):
                logger.info("Load more button not clickable, stopping")
                break
            
            # Click the button
            try:
                self._click_element(page, button_selector)
                logger.debug(f"Click {click_num + 1}: Loaded more items")
                time.sleep(self.click_pause)
                
                # Wait for new content
                self._wait_for_network_idle(page)
                
            except Exception as e:
                logger.warning(f"Click failed: {e}")
                break
        
        # Final collection
        items = self._safe_css(page, item_selector)
        for item in items:
            item_hash = self._hash_element(item)
            if item_hash not in seen_hashes:
                seen_hashes.add(item_hash)
                collected.append(item)
        
        logger.info(f"Load more complete: collected {len(collected)} items")
        return collected
    
    # ========================================================================
    # AJAX PAGINATION
    # ========================================================================
    
    def paginate_ajax(
        self,
        page,
        next_selector: str,
        item_selector: str,
        max_pages: int = 20,
        wait_selector: str = None,
    ) -> List[Any]:
        """
        Handle AJAX-based pagination (next button changes content without URL change).
        
        Args:
            page: Page object
            next_selector: CSS selector for next page button
            item_selector: CSS selector for items
            max_pages: Maximum pages to scrape
            wait_selector: Selector to wait for after clicking (confirms load)
            
        Returns:
            List of all collected elements
        """
        all_items = []
        
        for page_num in range(max_pages):
            # Collect items on current page
            items = self._safe_css(page, item_selector)
            all_items.extend(items)
            
            logger.info(f"Page {page_num + 1}: Found {len(items)} items")
            
            # Find and click next button
            next_btn = self._safe_css_first(page, next_selector)
            
            if not next_btn or not self._is_clickable(next_btn):
                logger.info("No more pages (next button not found/clickable)")
                break
            
            # Get current content hash to detect change
            content_before = self._get_content_hash(page, item_selector)
            
            # Click next
            try:
                self._click_element(page, next_selector)
                time.sleep(self.click_pause)
                
                # Wait for content to change
                if wait_selector:
                    self._wait_for_selector(page, wait_selector)
                else:
                    self._wait_for_content_change(page, item_selector, content_before)
                
            except Exception as e:
                logger.warning(f"Pagination failed: {e}")
                break
        
        logger.info(f"Pagination complete: {len(all_items)} total items")
        return all_items
    
    # ========================================================================
    # WAIT FOR CONTENT
    # ========================================================================
    
    def wait_for_content(
        self,
        page,
        selector: str,
        timeout: float = None,
    ) -> bool:
        """
        Wait for specific content to appear on page.
        
        Args:
            page: Page object
            selector: CSS selector to wait for
            timeout: Max seconds to wait
            
        Returns:
            True if content found, False if timeout
        """
        timeout = timeout or self.load_timeout
        start = time.time()
        
        while time.time() - start < timeout:
            elements = self._safe_css(page, selector)
            if elements:
                return True
            time.sleep(0.5)
        
        logger.warning(f"Timeout waiting for: {selector}")
        return False
    
    def wait_for_network_idle(
        self,
        page,
        idle_time: float = 0.5,
        timeout: float = None,
    ) -> bool:
        """
        Wait until no network requests are in progress.
        
        Useful for waiting for AJAX requests to complete.
        """
        timeout = timeout or self.load_timeout
        
        try:
            # If page has playwright's wait method
            if hasattr(page, 'wait_for_load_state'):
                page.wait_for_load_state('networkidle', timeout=timeout * 1000)
                return True
        except Exception:
            pass
        
        # Fallback: just wait
        time.sleep(idle_time)
        return True
    
    def wait_for_element_count(
        self,
        page,
        selector: str,
        min_count: int,
        timeout: float = None,
    ) -> bool:
        """
        Wait until at least min_count elements are present.
        """
        timeout = timeout or self.load_timeout
        start = time.time()
        
        while time.time() - start < timeout:
            elements = self._safe_css(page, selector)
            if len(elements) >= min_count:
                return True
            time.sleep(0.5)
        
        return False
    
    # ========================================================================
    # LAZY LOADING
    # ========================================================================
    
    def load_lazy_images(
        self,
        page,
        image_selector: str = "img[data-src], img[data-lazy], img.lazy",
    ) -> int:
        """
        Trigger loading of lazy-loaded images by scrolling them into view.
        
        Returns:
            Number of images loaded
        """
        images = self._safe_css(page, image_selector)
        loaded = 0
        
        for img in images:
            try:
                # Scroll image into view
                self._scroll_to_element(page, img)
                time.sleep(0.2)
                loaded += 1
            except Exception:
                pass
        
        logger.info(f"Loaded {loaded} lazy images")
        return loaded
    
    # ========================================================================
    # TAB/ACCORDION CONTENT
    # ========================================================================
    
    def click_all_tabs(
        self,
        page,
        tab_selector: str,
        content_selector: str = None,
    ) -> Dict[str, Any]:
        """
        Click each tab and collect content.
        
        Args:
            page: Page object
            tab_selector: CSS selector for tab buttons
            content_selector: CSS selector for content (optional)
            
        Returns:
            Dict mapping tab text to content
        """
        results = {}
        tabs = self._safe_css(page, tab_selector)
        
        for i, tab in enumerate(tabs):
            tab_text = self._get_text(tab) or f"tab_{i}"
            
            try:
                # Click tab
                self._click_element_direct(tab)
                time.sleep(self.click_pause)
                
                # Get content
                if content_selector:
                    content = self._safe_css(page, content_selector)
                    results[tab_text] = [self._get_html(c) for c in content]
                else:
                    results[tab_text] = True
                    
            except Exception as e:
                logger.warning(f"Tab click failed: {e}")
                results[tab_text] = None
        
        return results
    
    def expand_all_accordions(
        self,
        page,
        accordion_selector: str,
    ) -> int:
        """
        Click all accordion headers to expand content.
        
        Returns:
            Number of accordions expanded
        """
        accordions = self._safe_css(page, accordion_selector)
        expanded = 0
        
        for acc in accordions:
            try:
                self._click_element_direct(acc)
                time.sleep(0.3)
                expanded += 1
            except Exception:
                pass
        
        logger.info(f"Expanded {expanded} accordions")
        return expanded
    
    # ========================================================================
    # SPA NAVIGATION
    # ========================================================================
    
    def navigate_spa(
        self,
        page,
        link_selector: str,
        wait_selector: str,
    ) -> bool:
        """
        Navigate within a Single Page Application.
        
        Args:
            page: Page object
            link_selector: CSS selector for link to click
            wait_selector: Selector to wait for after navigation
            
        Returns:
            True if navigation successful
        """
        try:
            self._click_element(page, link_selector)
            time.sleep(0.5)
            
            return self.wait_for_content(page, wait_selector)
            
        except Exception as e:
            logger.error(f"SPA navigation failed: {e}")
            return False
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _safe_css(self, page, selector: str) -> List:
        """Safely get elements by CSS selector"""
        try:
            if hasattr(page, 'css'):
                return page.css(selector) or []
            elif hasattr(page, 'query_selector_all'):
                return page.query_selector_all(selector) or []
            return []
        except Exception:
            return []
    
    def _safe_css_first(self, page, selector: str):
        """Safely get first element by CSS selector"""
        elements = self._safe_css(page, selector)
        return elements[0] if elements else None
    
    def _hash_element(self, element) -> str:
        """Create hash of element for deduplication"""
        try:
            if hasattr(element, 'html'):
                return str(hash(element.html))
            elif hasattr(element, 'inner_html'):
                return str(hash(element.inner_html()))
            else:
                return str(hash(str(element)))
        except Exception:
            return str(id(element))
    
    def _scroll_down(self, page, pixels: int = 800):
        """Scroll page down"""
        try:
            if hasattr(page, 'execute_script'):
                page.execute_script(f"window.scrollBy(0, {pixels})")
            elif hasattr(page, 'evaluate'):
                page.evaluate(f"window.scrollBy(0, {pixels})")
        except Exception as e:
            logger.debug(f"Scroll failed: {e}")
    
    def _scroll_to_element(self, page, element):
        """Scroll element into view"""
        try:
            if hasattr(element, 'scroll_into_view'):
                element.scroll_into_view()
            elif hasattr(page, 'evaluate'):
                page.evaluate("el => el.scrollIntoView()", element)
        except Exception:
            pass
    
    def _is_at_bottom(self, page) -> bool:
        """Check if scrolled to bottom of page"""
        try:
            if hasattr(page, 'execute_script'):
                return page.execute_script(
                    "return (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 100"
                )
            elif hasattr(page, 'evaluate'):
                return page.evaluate(
                    "() => (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 100"
                )
        except Exception:
            return False
        return False
    
    def _is_clickable(self, element) -> bool:
        """Check if element is visible and clickable"""
        try:
            if hasattr(element, 'is_visible'):
                return element.is_visible()
            if hasattr(element, 'is_displayed'):
                return element.is_displayed()
            return True  # Assume clickable if can't check
        except Exception:
            return True
    
    def _click_element(self, page, selector: str):
        """Click element by selector"""
        try:
            if hasattr(page, 'click'):
                page.click(selector)
            elif hasattr(page, 'execute_script'):
                page.execute_script(f"document.querySelector('{selector}').click()")
            elif hasattr(page, 'evaluate'):
                page.evaluate(f"document.querySelector('{selector}').click()")
        except Exception as e:
            raise RuntimeError(f"Click failed: {e}")
    
    def _click_element_direct(self, element):
        """Click element directly"""
        try:
            if hasattr(element, 'click'):
                element.click()
        except Exception as e:
            raise RuntimeError(f"Direct click failed: {e}")
    
    def _wait_for_network_idle(self, page):
        """Wait for network to be idle"""
        try:
            if hasattr(page, 'wait_for_load_state'):
                page.wait_for_load_state('networkidle', timeout=self.load_timeout * 1000)
        except Exception:
            time.sleep(1)  # Fallback
    
    def _wait_for_selector(self, page, selector: str):
        """Wait for selector to appear"""
        try:
            if hasattr(page, 'wait_for_selector'):
                page.wait_for_selector(selector, timeout=self.load_timeout * 1000)
        except Exception:
            self.wait_for_content(page, selector)
    
    def _wait_for_content_change(self, page, selector: str, old_hash: str):
        """Wait for content to change"""
        start = time.time()
        while time.time() - start < self.load_timeout:
            new_hash = self._get_content_hash(page, selector)
            if new_hash != old_hash:
                return True
            time.sleep(0.3)
        return False
    
    def _get_content_hash(self, page, selector: str) -> str:
        """Get hash of content matching selector"""
        elements = self._safe_css(page, selector)
        content = "".join(self._hash_element(e) for e in elements)
        return str(hash(content))
    
    def _get_text(self, element) -> str:
        """Get text content of element"""
        try:
            if hasattr(element, 'text'):
                return element.text.strip()
            elif hasattr(element, 'inner_text'):
                return element.inner_text().strip()
            elif hasattr(element, 'text_content'):
                return element.text_content().strip()
            return ""
        except Exception:
            return ""
    
    def _get_html(self, element) -> str:
        """Get HTML content of element"""
        try:
            if hasattr(element, 'html'):
                return element.html
            elif hasattr(element, 'inner_html'):
                return element.inner_html()
            return str(element)
        except Exception:
            return ""


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def scrape_infinite_scroll(
    url: str,
    item_selector: str,
    parse_func: Callable,
    max_items: int = 100,
    mode: str = "dynamic",
) -> List[Dict]:
    """
    Convenience function to scrape infinite scroll pages.
    
    Args:
        url: Page URL
        item_selector: CSS selector for items
        parse_func: Function to parse each item element
        max_items: Maximum items to collect
        mode: Fetcher mode ("dynamic" required for JS)
        
    Returns:
        List of parsed items
    """
    try:
        from engine_v2 import ScrapingEngine
    except ImportError:
        from engine import ScrapingEngine
    
    engine = ScrapingEngine(mode=mode, timeout=60)
    page = engine.fetch(url)
    
    if not page:
        return []
    
    handler = AjaxHandler()
    elements = handler.scroll_until_end(page, item_selector, max_items=max_items)
    
    results = []
    for el in elements:
        try:
            result = parse_func(el)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Parse error: {e}")
    
    return results


def scrape_load_more(
    url: str,
    button_selector: str,
    item_selector: str,
    parse_func: Callable,
    max_items: int = 100,
) -> List[Dict]:
    """
    Convenience function to scrape pages with Load More button.
    """
    try:
        from engine_v2 import ScrapingEngine
    except ImportError:
        from engine import ScrapingEngine
    
    engine = ScrapingEngine(mode="dynamic", timeout=60)
    page = engine.fetch(url)
    
    if not page:
        return []
    
    handler = AjaxHandler()
    elements = handler.click_load_more(page, button_selector, item_selector, max_items=max_items)
    
    results = []
    for el in elements:
        try:
            result = parse_func(el)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Parse error: {e}")
    
    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🔄 Scrapling Pro - AJAX Handler")
    print("=" * 50)
    print("""
Features:
  ✅ Infinite scroll handling
  ✅ Load more button clicking
  ✅ AJAX pagination
  ✅ Lazy image loading
  ✅ Tab/accordion expansion
  ✅ SPA navigation
  ✅ Network idle detection
  ✅ Content change detection

Usage:

    from ajax_handler import AjaxHandler, scrape_infinite_scroll
    
    # Method 1: Use convenience function
    items = scrape_infinite_scroll(
        url="https://example.com/products",
        item_selector=".product-card",
        parse_func=lambda el: {
            "title": el.css(".title")[0].text,
            "price": el.css(".price")[0].text,
        },
        max_items=100
    )
    
    # Method 2: Use handler directly
    handler = AjaxHandler()
    
    # With a page object from engine
    elements = handler.scroll_until_end(page, ".product-card", max_items=100)
    elements = handler.click_load_more(page, ".load-more", ".product-card")
    elements = handler.paginate_ajax(page, ".next-btn", ".product-card")
    
    # Wait for AJAX content
    handler.wait_for_content(page, ".results-loaded")
    handler.wait_for_network_idle(page)
    
    # Load lazy images
    handler.load_lazy_images(page)
    
    # Expand tabs/accordions
    handler.click_all_tabs(page, ".tab-btn", ".tab-content")
    handler.expand_all_accordions(page, ".accordion-header")
    """)
