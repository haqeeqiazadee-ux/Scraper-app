"""
⏰ SCRAPLING PRO - Scheduler
=============================
Schedule scraping tasks to run automatically.

Features:
- Cron-like scheduling
- One-time delayed execution
- Recurring jobs
- Job persistence
- Email/webhook notifications on completion

Usage:
    from scheduler import Scheduler, Job
    
    scheduler = Scheduler()
    
    # Add a recurring job (every hour)
    scheduler.add_job(
        name="price_monitor",
        func=my_scrape_function,
        schedule="hourly",
        args=["https://shop.com/products"]
    )
    
    # Add a cron job (every day at 9am)
    scheduler.add_job(
        name="daily_report",
        func=generate_report,
        schedule="0 9 * * *"
    )
    
    # Start scheduler
    scheduler.start()
"""

import json
import time
import logging
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Callable, Any, Dict, List, Optional
from pathlib import Path
import re

logger = logging.getLogger("Scheduler")


# ============================================================================
# JOB DEFINITION
# ============================================================================

@dataclass
class Job:
    """Scheduled job definition"""
    name: str
    func: Callable
    schedule: str  # "hourly", "daily", "weekly", or cron expression
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    webhook_url: Optional[str] = None
    email_on_complete: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dict (excluding func)"""
        d = asdict(self)
        del d['func']
        return d


@dataclass
class JobResult:
    """Result of a job execution"""
    job_name: str
    success: bool
    start_time: str
    end_time: str
    duration_seconds: float
    result: Any = None
    error: Optional[str] = None


# ============================================================================
# CRON PARSER
# ============================================================================

class CronParser:
    """
    Simple cron expression parser.
    
    Format: minute hour day_of_month month day_of_week
    
    Examples:
        "0 * * * *"     - Every hour
        "0 9 * * *"     - Every day at 9am
        "0 9 * * 1"     - Every Monday at 9am
        "*/15 * * * *"  - Every 15 minutes
        "0 0 1 * *"     - First day of every month at midnight
    """
    
    @staticmethod
    def parse(expression: str) -> Dict:
        """Parse cron expression"""
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}")
        
        return {
            'minute': CronParser._parse_field(parts[0], 0, 59),
            'hour': CronParser._parse_field(parts[1], 0, 23),
            'day': CronParser._parse_field(parts[2], 1, 31),
            'month': CronParser._parse_field(parts[3], 1, 12),
            'weekday': CronParser._parse_field(parts[4], 0, 6),
        }
    
    @staticmethod
    def _parse_field(field: str, min_val: int, max_val: int) -> List[int]:
        """Parse a single cron field"""
        if field == '*':
            return list(range(min_val, max_val + 1))
        
        if '/' in field:
            # Step values: */15 means every 15
            base, step = field.split('/')
            step = int(step)
            if base == '*':
                return list(range(min_val, max_val + 1, step))
            else:
                start = int(base)
                return list(range(start, max_val + 1, step))
        
        if ',' in field:
            # List: 1,3,5
            return [int(x) for x in field.split(',')]
        
        if '-' in field:
            # Range: 1-5
            start, end = field.split('-')
            return list(range(int(start), int(end) + 1))
        
        return [int(field)]
    
    @staticmethod
    def matches(expression: str, dt: datetime) -> bool:
        """Check if datetime matches cron expression"""
        try:
            parsed = CronParser.parse(expression)
            
            return (
                dt.minute in parsed['minute'] and
                dt.hour in parsed['hour'] and
                dt.day in parsed['day'] and
                dt.month in parsed['month'] and
                dt.weekday() in parsed['weekday']
            )
        except Exception:
            return False
    
    @staticmethod
    def next_run(expression: str, after: datetime = None) -> datetime:
        """Calculate next run time for cron expression"""
        if after is None:
            after = datetime.now()
        
        # Start from next minute
        dt = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
        
        # Search for next matching time (max 1 year ahead)
        for _ in range(525600):  # Minutes in a year
            if CronParser.matches(expression, dt):
                return dt
            dt += timedelta(minutes=1)
        
        raise ValueError(f"Could not find next run time for: {expression}")


# ============================================================================
# SCHEDULER
# ============================================================================

class Scheduler:
    """
    Job scheduler for automated scraping.
    
    Usage:
        scheduler = Scheduler()
        
        scheduler.add_job(
            name="hourly_scrape",
            func=scrape_products,
            schedule="hourly"
        )
        
        scheduler.start()
    """
    
    # Preset schedules
    PRESETS = {
        'minutely': '* * * * *',
        'hourly': '0 * * * *',
        'daily': '0 0 * * *',
        'weekly': '0 0 * * 0',
        'monthly': '0 0 1 * *',
    }
    
    def __init__(self, persistence_file: str = None):
        self.jobs: Dict[str, Job] = {}
        self.results: List[JobResult] = []
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.persistence_file = persistence_file
        
        # Load persisted jobs if file exists
        if persistence_file:
            self._load_jobs()
    
    def add_job(
        self,
        name: str,
        func: Callable,
        schedule: str,
        args: List = None,
        kwargs: Dict = None,
        webhook_url: str = None,
        email_on_complete: str = None,
    ) -> Job:
        """
        Add a scheduled job.
        
        Args:
            name: Unique job name
            func: Function to execute
            schedule: "hourly", "daily", "weekly", or cron expression
            args: Function arguments
            kwargs: Function keyword arguments
            webhook_url: URL to POST results to
            email_on_complete: Email address for notifications
        """
        # Convert preset to cron
        if schedule in self.PRESETS:
            cron_expr = self.PRESETS[schedule]
        else:
            cron_expr = schedule
        
        # Calculate next run
        next_run = CronParser.next_run(cron_expr)
        
        job = Job(
            name=name,
            func=func,
            schedule=cron_expr,
            args=args or [],
            kwargs=kwargs or {},
            next_run=next_run.isoformat(),
            webhook_url=webhook_url,
            email_on_complete=email_on_complete,
        )
        
        with self._lock:
            self.jobs[name] = job
        
        logger.info(f"Job added: {name} (next run: {next_run})")
        self._save_jobs()
        
        return job
    
    def remove_job(self, name: str) -> bool:
        """Remove a job"""
        with self._lock:
            if name in self.jobs:
                del self.jobs[name]
                logger.info(f"Job removed: {name}")
                self._save_jobs()
                return True
        return False
    
    def enable_job(self, name: str) -> bool:
        """Enable a job"""
        with self._lock:
            if name in self.jobs:
                self.jobs[name].enabled = True
                self._save_jobs()
                return True
        return False
    
    def disable_job(self, name: str) -> bool:
        """Disable a job"""
        with self._lock:
            if name in self.jobs:
                self.jobs[name].enabled = False
                self._save_jobs()
                return True
        return False
    
    def run_now(self, name: str) -> Optional[JobResult]:
        """Run a job immediately"""
        if name not in self.jobs:
            logger.error(f"Job not found: {name}")
            return None
        
        return self._execute_job(self.jobs[name])
    
    def _execute_job(self, job: Job) -> JobResult:
        """Execute a job and return result"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Executing job: {job.name}")
            result = job.func(*job.args, **job.kwargs)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            job_result = JobResult(
                job_name=job.name,
                success=True,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                duration_seconds=duration,
                result=result,
            )
            
            # Update job stats
            job.last_run = end_time.isoformat()
            job.run_count += 1
            job.next_run = CronParser.next_run(job.schedule).isoformat()
            
            logger.info(f"Job completed: {job.name} ({duration:.2f}s)")
            
            # Send notifications
            self._notify(job, job_result)
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            job_result = JobResult(
                job_name=job.name,
                success=False,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                duration_seconds=duration,
                error=str(e),
            )
            
            job.last_run = end_time.isoformat()
            job.error_count += 1
            job.last_error = str(e)
            job.next_run = CronParser.next_run(job.schedule).isoformat()
            
            logger.error(f"Job failed: {job.name} - {e}")
        
        self.results.append(job_result)
        self._save_jobs()
        
        return job_result
    
    def _notify(self, job: Job, result: JobResult):
        """Send notifications for job completion"""
        # Webhook notification
        if job.webhook_url:
            try:
                import requests
                requests.post(job.webhook_url, json={
                    'job_name': job.name,
                    'success': result.success,
                    'duration': result.duration_seconds,
                    'timestamp': result.end_time,
                }, timeout=10)
            except Exception as e:
                logger.error(f"Webhook notification failed: {e}")
        
        # Email notification (placeholder - requires email config)
        if job.email_on_complete:
            logger.info(f"Email notification would be sent to: {job.email_on_complete}")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler started")
        
        while self.running:
            now = datetime.now()
            
            with self._lock:
                for job in self.jobs.values():
                    if not job.enabled:
                        continue
                    
                    if job.next_run:
                        next_run = datetime.fromisoformat(job.next_run)
                        if now >= next_run:
                            # Run in separate thread to not block scheduler
                            threading.Thread(
                                target=self._execute_job,
                                args=(job,)
                            ).start()
            
            # Sleep for 30 seconds
            time.sleep(30)
        
        logger.info("Scheduler stopped")
    
    def start(self, blocking: bool = False):
        """
        Start the scheduler.
        
        Args:
            blocking: If True, blocks the current thread. If False, runs in background.
        """
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        
        if blocking:
            self._scheduler_loop()
        else:
            self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self._thread.start()
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def get_status(self) -> Dict:
        """Get scheduler status"""
        return {
            'running': self.running,
            'job_count': len(self.jobs),
            'jobs': {name: job.to_dict() for name, job in self.jobs.items()},
            'recent_results': [asdict(r) for r in self.results[-10:]],
        }
    
    def _save_jobs(self):
        """Save jobs to persistence file"""
        if not self.persistence_file:
            return
        
        try:
            data = {
                'jobs': {name: job.to_dict() for name, job in self.jobs.items()},
                'results': [asdict(r) for r in self.results[-100:]],  # Keep last 100
            }
            
            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save jobs: {e}")
    
    def _load_jobs(self):
        """Load jobs from persistence file"""
        if not self.persistence_file or not Path(self.persistence_file).exists():
            return
        
        try:
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)
            
            # Note: Functions can't be persisted, so jobs need to be re-registered
            logger.info(f"Loaded {len(data.get('jobs', {}))} job definitions")
            
        except Exception as e:
            logger.error(f"Failed to load jobs: {e}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global scheduler instance
_scheduler: Optional[Scheduler] = None


def get_scheduler(persistence_file: str = "scheduler_jobs.json") -> Scheduler:
    """Get or create global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler(persistence_file)
    return _scheduler


def schedule_scrape(
    name: str,
    url: str,
    schedule: str = "hourly",
    template: str = "ecommerce",
    output_file: str = None,
    webhook_url: str = None,
):
    """
    Convenience function to schedule a scraping job.
    
    Example:
        schedule_scrape(
            name="daily_products",
            url="https://shop.com/products",
            schedule="daily",
            template="ecommerce",
            output_file="products_{date}.csv"
        )
    """
    try:
        from engine_v2 import ScrapingEngine, Parsers, Exporter
    except ImportError:
        from engine import ScrapingEngine, Parsers, Exporter
    
    def scrape_job():
        engine = ScrapingEngine(mode="stealthy", timeout=30)
        
        if template == "ecommerce":
            parser = Parsers.ecommerce_products
        else:
            parser = Parsers.ecommerce_products
        
        items = engine.scrape_url(url, parser)
        
        if output_file and items:
            # Replace {date} placeholder
            filepath = output_file.replace(
                "{date}", 
                datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            
            if filepath.endswith('.json'):
                Exporter.to_json(items, filepath)
            elif filepath.endswith('.xlsx'):
                Exporter.to_excel(items, filepath)
            else:
                Exporter.to_csv(items, filepath)
        
        return {
            'url': url,
            'items_count': len(items),
            'output_file': output_file,
        }
    
    scheduler = get_scheduler()
    return scheduler.add_job(
        name=name,
        func=scrape_job,
        schedule=schedule,
        webhook_url=webhook_url,
    )


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("⏰ Scrapling Pro - Scheduler")
    print("=" * 50)
    
    # Example usage
    print("""
Usage:

    from scheduler import Scheduler, schedule_scrape
    
    # Quick way - schedule a scraping job
    schedule_scrape(
        name="hourly_products",
        url="https://books.toscrape.com",
        schedule="hourly",
        output_file="books_{date}.csv"
    )
    
    # Or create custom jobs
    scheduler = Scheduler()
    
    def my_custom_job():
        print("Running custom job!")
        return {"status": "done"}
    
    scheduler.add_job(
        name="my_job",
        func=my_custom_job,
        schedule="*/15 * * * *"  # Every 15 minutes
    )
    
    scheduler.start(blocking=True)
    
Preset Schedules:
    - "minutely"  : Every minute
    - "hourly"    : Every hour
    - "daily"     : Every day at midnight
    - "weekly"    : Every Sunday at midnight
    - "monthly"   : First day of each month
    
Cron Format:
    minute hour day month weekday
    
    Examples:
    - "0 9 * * *"     : Every day at 9am
    - "*/15 * * * *"  : Every 15 minutes
    - "0 0 * * 1"     : Every Monday at midnight
    """)
