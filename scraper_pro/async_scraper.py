"""
🕷️ SCRAPLING PRO - Async & Concurrent Scraping
================================================
High-performance scraping with asyncio and threading.

Features:
- Async scraping with asyncio
- Thread pool for concurrent requests
- Worker queues for job management
- Progress tracking
- Batch processing
"""

import asyncio
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger("ScraplingPro.Async")

# Import core components
try:
    from .engine import ScrapingEngine, ScrapedItem, RateLimiter
except ImportError:
    from engine import ScrapingEngine, ScrapedItem, RateLimiter


# ============================================================================
# PROGRESS TRACKER
# ============================================================================

@dataclass
class Progress:
    """Track scraping progress"""
    total: int = 0
    completed: int = 0
    successful: int = 0
    failed: int = 0
    start_time: datetime = None
    items_scraped: int = 0
    
    def start(self, total: int):
        self.total = total
        self.completed = 0
        self.successful = 0
        self.failed = 0
        self.start_time = datetime.now()
        self.items_scraped = 0
    
    def update(self, success: bool, items: int = 0):
        self.completed += 1
        if success:
            self.successful += 1
        else:
            self.failed += 1
        self.items_scraped += items
    
    @property
    def percent(self) -> float:
        return (self.completed / max(1, self.total)) * 100
    
    @property
    def elapsed(self) -> float:
        if not self.start_time:
            return 0
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def rate(self) -> float:
        """Requests per second"""
        return self.completed / max(1, self.elapsed)
    
    @property
    def eta(self) -> float:
        """Estimated time remaining in seconds"""
        if self.completed == 0:
            return 0
        return (self.total - self.completed) / self.rate
    
    def __str__(self):
        return (
            f"[{self.completed}/{self.total}] {self.percent:.1f}% | "
            f"✓{self.successful} ✗{self.failed} | "
            f"{self.items_scraped} items | "
            f"{self.rate:.2f} req/s | "
            f"ETA: {self.eta:.0f}s"
        )


# ============================================================================
# CONCURRENT SCRAPER
# ============================================================================

class ConcurrentScraper:
    """
    High-performance concurrent scraper using thread pools.
    
    Example:
        scraper = ConcurrentScraper(max_workers=10, rate_limit=2.0)
        
        results = scraper.scrape_urls(
            urls=["https://site.com/page/1", "https://site.com/page/2", ...],
            parser=my_parser_function,
            progress_callback=lambda p: print(p)
        )
    """
    
    def __init__(
        self,
        max_workers: int = 5,
        mode: str = "stealthy",
        rate_limit: float = 1.0,
        max_retries: int = 3,
        timeout: int = 30,
        proxies: List[str] = None,
    ):
        self.max_workers = max_workers
        self.engine = ScrapingEngine(
            mode=mode,
            rate_limit=rate_limit,
            max_retries=max_retries,
            timeout=timeout,
            proxies=proxies,
        )
        self.progress = Progress()
        self.results: List[ScrapedItem] = []
        self._lock = threading.Lock()
    
    def _scrape_one(
        self, 
        url: str, 
        parser: Callable,
        **kwargs
    ) -> List[ScrapedItem]:
        """Scrape a single URL (thread-safe)"""
        try:
            page = self.engine.fetch(url, **kwargs)
            if page:
                items = parser(page)
                with self._lock:
                    self.progress.update(True, len(items))
                return items
            else:
                with self._lock:
                    self.progress.update(False)
                return [ScrapedItem(url=url, success=False, error="Failed to fetch")]
        except Exception as e:
            with self._lock:
                self.progress.update(False)
            logger.error(f"Error scraping {url}: {e}")
            return [ScrapedItem(url=url, success=False, error=str(e))]
    
    def scrape_urls(
        self,
        urls: List[str],
        parser: Callable,
        progress_callback: Callable[[Progress], None] = None,
        **kwargs
    ) -> List[ScrapedItem]:
        """
        Scrape multiple URLs concurrently.
        
        Args:
            urls: List of URLs to scrape
            parser: Function(page) -> List[ScrapedItem]
            progress_callback: Optional callback for progress updates
            **kwargs: Additional kwargs for the fetcher
        
        Returns:
            List of all scraped items
        """
        self.results = []
        self.progress.start(len(urls))
        
        logger.info(f"Starting concurrent scrape of {len(urls)} URLs with {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            futures = {
                executor.submit(self._scrape_one, url, parser, **kwargs): url
                for url in urls
            }
            
            # Process as they complete
            for future in as_completed(futures):
                url = futures[future]
                try:
                    items = future.result()
                    with self._lock:
                        self.results.extend(items)
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(self.progress)
                    
                except Exception as e:
                    logger.error(f"Future error for {url}: {e}")
        
        logger.info(f"Completed: {self.progress}")
        return self.results
    
    def scrape_with_generator(
        self,
        url_generator: Callable[[], str],
        parser: Callable,
        max_urls: int = 100,
        stop_on_empty: bool = True,
        **kwargs
    ) -> List[ScrapedItem]:
        """
        Scrape URLs from a generator (useful for dynamic pagination).
        
        Args:
            url_generator: Function that yields URLs
            parser: Parser function
            max_urls: Maximum URLs to scrape
            stop_on_empty: Stop if parser returns no items
        """
        self.results = []
        urls_scraped = 0
        
        while urls_scraped < max_urls:
            try:
                url = url_generator()
                if not url:
                    break
                
                items = self._scrape_one(url, parser, **kwargs)
                
                with self._lock:
                    self.results.extend(items)
                
                urls_scraped += 1
                
                # Check if we should stop
                if stop_on_empty and not any(item.success for item in items):
                    logger.info("No successful items, stopping")
                    break
                    
            except StopIteration:
                break
        
        return self.results


# ============================================================================
# BATCH PROCESSOR
# ============================================================================

@dataclass
class BatchJob:
    """A batch scraping job"""
    id: str
    urls: List[str]
    template: str
    status: str = "pending"  # pending, running, completed, failed
    progress: Progress = field(default_factory=Progress)
    results: List[ScrapedItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = None
    error: str = ""


class BatchProcessor:
    """
    Process multiple scraping jobs in batches.
    
    Example:
        processor = BatchProcessor()
        
        # Add jobs
        job1 = processor.add_job(urls=urls1, template="ecommerce")
        job2 = processor.add_job(urls=urls2, template="news")
        
        # Process all
        processor.process_all()
        
        # Get results
        results = processor.get_job_results(job1.id)
    """
    
    def __init__(self, max_concurrent_jobs: int = 2, **engine_kwargs):
        self.jobs: Dict[str, BatchJob] = {}
        self.job_queue = queue.Queue()
        self.max_concurrent_jobs = max_concurrent_jobs
        self.engine_kwargs = engine_kwargs
        self._running = False
        self._workers = []
    
    def add_job(
        self,
        urls: List[str],
        template: str = "ecommerce",
        job_id: str = None
    ) -> BatchJob:
        """Add a new batch job"""
        if not job_id:
            job_id = f"job_{len(self.jobs) + 1}_{int(time.time())}"
        
        job = BatchJob(id=job_id, urls=urls, template=template)
        self.jobs[job_id] = job
        self.job_queue.put(job_id)
        
        logger.info(f"Added job {job_id} with {len(urls)} URLs")
        return job
    
    def _process_job(self, job: BatchJob):
        """Process a single job"""
        from .templates import TEMPLATES, EcommerceScraper
        
        job.status = "running"
        job.progress.start(len(job.urls))
        
        try:
            # Get template
            template_class = TEMPLATES.get(job.template, EcommerceScraper)
            scraper = template_class(**self.engine_kwargs)
            
            # Scrape with progress
            def update_progress(success, items_count):
                job.progress.update(success, items_count)
            
            # Use concurrent scraper
            concurrent = ConcurrentScraper(**self.engine_kwargs)
            job.results = concurrent.scrape_urls(
                job.urls,
                scraper.parse,
                progress_callback=lambda p: None  # Already tracking
            )
            
            job.status = "completed"
            job.completed_at = datetime.now()
            logger.info(f"Job {job.id} completed: {len(job.results)} items")
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.now()
            logger.error(f"Job {job.id} failed: {e}")
    
    def process_all(self, blocking: bool = True):
        """Process all queued jobs"""
        if blocking:
            while not self.job_queue.empty():
                job_id = self.job_queue.get()
                job = self.jobs.get(job_id)
                if job:
                    self._process_job(job)
        else:
            # Start background workers
            self._running = True
            for i in range(self.max_concurrent_jobs):
                worker = threading.Thread(target=self._worker_loop, daemon=True)
                worker.start()
                self._workers.append(worker)
    
    def _worker_loop(self):
        """Background worker loop"""
        while self._running:
            try:
                job_id = self.job_queue.get(timeout=1)
                job = self.jobs.get(job_id)
                if job:
                    self._process_job(job)
            except queue.Empty:
                continue
    
    def stop(self):
        """Stop background processing"""
        self._running = False
        for worker in self._workers:
            worker.join(timeout=5)
    
    def get_job_status(self, job_id: str) -> Dict:
        """Get status of a job"""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        
        return {
            "id": job.id,
            "status": job.status,
            "progress": str(job.progress),
            "results_count": len(job.results),
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
        }
    
    def get_job_results(self, job_id: str) -> List[ScrapedItem]:
        """Get results of a completed job"""
        job = self.jobs.get(job_id)
        return job.results if job else []
    
    def get_all_jobs(self) -> List[Dict]:
        """Get status of all jobs"""
        return [self.get_job_status(job_id) for job_id in self.jobs]


# ============================================================================
# URL GENERATORS
# ============================================================================

class URLGenerators:
    """Common URL generator patterns"""
    
    @staticmethod
    def pagination(base_url: str, pattern: str, start: int = 1, end: int = 10):
        """
        Generate paginated URLs.
        
        Example:
            gen = URLGenerators.pagination(
                "https://site.com/products",
                "?page={}",
                start=1,
                end=50
            )
            for url in gen:
                print(url)
        """
        for page in range(start, end + 1):
            yield base_url + pattern.format(page)
    
    @staticmethod
    def sitemap(sitemap_url: str, filter_pattern: str = None):
        """
        Generate URLs from a sitemap.
        
        Example:
            gen = URLGenerators.sitemap(
                "https://site.com/sitemap.xml",
                filter_pattern="/products/"
            )
        """
        import re
        from scrapling.fetchers import StealthyFetcher
        
        try:
            page = StealthyFetcher.fetch(sitemap_url)
            
            # Extract URLs from sitemap
            urls = re.findall(r'<loc>(.*?)</loc>', page.html_content)
            
            for url in urls:
                if filter_pattern is None or filter_pattern in url:
                    yield url
                    
        except Exception as e:
            logger.error(f"Error parsing sitemap: {e}")
    
    @staticmethod
    def from_file(filepath: str):
        """
        Generate URLs from a file (one per line).
        
        Example:
            gen = URLGenerators.from_file("urls.txt")
        """
        with open(filepath, 'r') as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith('#'):
                    yield url
    
    @staticmethod
    def from_list(urls: List[str]):
        """Generate URLs from a list"""
        for url in urls:
            yield url
    
    @staticmethod
    def search_results(
        search_url: str,
        query: str,
        page_param: str = "page",
        query_param: str = "q",
        max_pages: int = 10
    ):
        """
        Generate search result URLs.
        
        Example:
            gen = URLGenerators.search_results(
                "https://site.com/search",
                query="python",
                max_pages=5
            )
        """
        from urllib.parse import urlencode
        
        for page in range(1, max_pages + 1):
            params = {query_param: query, page_param: page}
            yield f"{search_url}?{urlencode(params)}"


# ============================================================================
# ASYNC SCRAPER (for asyncio environments)
# ============================================================================

class AsyncScraper:
    """
    Async scraper for asyncio environments.
    
    Note: Scrapling's fetchers are sync, so this uses run_in_executor.
    For true async, you'd need an async HTTP library.
    
    Example:
        async def main():
            scraper = AsyncScraper()
            results = await scraper.scrape_urls(urls, parser)
    """
    
    def __init__(
        self,
        max_concurrent: int = 5,
        mode: str = "stealthy",
        **engine_kwargs
    ):
        self.max_concurrent = max_concurrent
        self.engine = ScrapingEngine(mode=mode, **engine_kwargs)
        self.semaphore = None
    
    async def _fetch_one(
        self,
        url: str,
        parser: Callable,
        loop: asyncio.AbstractEventLoop
    ) -> List[ScrapedItem]:
        """Fetch a single URL asynchronously"""
        async with self.semaphore:
            try:
                # Run sync fetch in executor
                page = await loop.run_in_executor(
                    None,
                    lambda: self.engine.fetch(url)
                )
                
                if page:
                    items = parser(page)
                    return items
                else:
                    return [ScrapedItem(url=url, success=False, error="Failed to fetch")]
                    
            except Exception as e:
                return [ScrapedItem(url=url, success=False, error=str(e))]
    
    async def scrape_urls(
        self,
        urls: List[str],
        parser: Callable
    ) -> List[ScrapedItem]:
        """Scrape multiple URLs asynchronously"""
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        loop = asyncio.get_event_loop()
        
        tasks = [
            self._fetch_one(url, parser, loop)
            for url in urls
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Flatten results
        all_items = []
        for items in results:
            all_items.extend(items)
        
        return all_items


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    print("🕷️ Scrapling Pro - Async & Concurrent Scraping")
    print("=" * 50)
    
    # Demo: Concurrent scraping
    from templates import EcommerceScraper
    
    scraper = ConcurrentScraper(max_workers=3, rate_limit=0.5)
    
    # Generate URLs
    urls = list(URLGenerators.pagination(
        "https://books.toscrape.com",
        "/catalogue/page-{}.html",
        start=1,
        end=3
    ))
    
    print(f"\nScraping {len(urls)} URLs concurrently...")
    
    # Create parser
    template = EcommerceScraper()
    
    results = scraper.scrape_urls(
        urls,
        template.parse,
        progress_callback=lambda p: print(f"\r{p}", end="")
    )
    
    print(f"\n\n✅ Scraped {len(results)} items total")
    
    # Show sample
    for item in results[:5]:
        print(f"  📦 {item.title[:40]}...")
