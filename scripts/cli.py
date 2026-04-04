#!/usr/bin/env python3
"""
Scraper Platform CLI — command-line interface for the AI scraping platform.

Usage:
    python -m scripts.cli scrape https://example.com
    python -m scripts.cli crawl https://example.com --depth 2
    python -m scripts.cli search "best gaming laptops"
    python -m scripts.cli route https://amazon.com/dp/B09V3KXJPB
"""

import asyncio
import json
import sys
import click

@click.group()
@click.version_option("1.0.0", prog_name="scraper-cli")
def cli():
    """AI Scraping Platform — the most advanced scraper on Earth."""
    pass

@cli.command()
@click.argument("url")
@click.option("--format", "output_format", default="json", type=click.Choice(["json", "markdown", "html", "raw"]))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--pretty/--no-pretty", default=True, help="Pretty-print JSON output")
def scrape(url, output_format, output, pretty):
    """Scrape data from a single URL."""
    async def _run():
        from services.worker_http.worker import HttpWorker
        worker = HttpWorker()
        result = await worker.process_task({
            "url": url,
            "output_format": output_format,
            "tenant_id": "cli",
        })
        return result

    result = asyncio.run(_run())
    _output_result(result, output, pretty)

@cli.command()
@click.argument("url")
@click.option("--depth", default=3, help="Maximum crawl depth")
@click.option("--max-pages", default=100, help="Maximum pages to crawl")
@click.option("--format", "output_format", default="json", type=click.Choice(["json", "markdown"]))
@click.option("--output", "-o", type=click.Path())
@click.option("--delay", default=1.0, help="Crawl delay in seconds")
def crawl(url, depth, max_pages, output_format, output, delay):
    """Recursively crawl a website."""
    async def _run():
        from packages.core.crawl_manager import CrawlManager, CrawlConfig
        manager = CrawlManager()
        config = CrawlConfig(
            seed_urls=[url],
            max_depth=depth,
            max_pages=max_pages,
            output_format=output_format,
            crawl_delay=delay,
        )
        crawl_id = await manager.start_crawl(config)

        # Wait for crawl to complete with progress
        import time
        while True:
            job = await manager.get_crawl(crawl_id)
            if job and job.state in ("completed", "failed", "stopped"):
                break
            if job:
                click.echo(f"\rCrawling... {job.stats.pages_crawled} pages, {job.stats.items_extracted} items", nl=False)
            time.sleep(1)

        click.echo()  # newline after progress
        results = await manager.get_results(crawl_id)
        return {"crawl_id": crawl_id, "stats": job.stats.__dict__ if job else {}, "results": results}

    result = asyncio.run(_run())
    _output_result(result, output, True)

@cli.command()
@click.argument("query")
@click.option("--max-results", default=5)
@click.option("--format", "output_format", default="json")
@click.option("--output", "-o", type=click.Path())
def search(query, max_results, output_format, output):
    """Search the web and scrape results."""
    # Use the search endpoint logic
    click.echo(json.dumps({"query": query, "status": "search requires BRAVE_SEARCH_API_KEY"}, indent=2))

@cli.command()
@click.argument("url")
def route(url):
    """Show which execution lane would handle this URL (dry run)."""
    from packages.core.router import ExecutionRouter
    from packages.contracts.task import Task
    router = ExecutionRouter()
    task = Task(url=url, tenant_id="cli")
    decision = router.route(task)
    click.echo(json.dumps({
        "url": url,
        "lane": decision.lane.value,
        "reason": decision.reason,
        "fallback_lanes": [l.value for l in decision.fallback_lanes],
        "confidence": decision.confidence,
        "estimated_cost": getattr(decision, 'estimated_cost', 0),
    }, indent=2))

def _output_result(result, output_path, pretty):
    """Output result to file or stdout."""
    text = json.dumps(result, indent=2 if pretty else None, default=str)
    if output_path:
        with open(output_path, "w") as f:
            f.write(text)
        click.echo(f"Output written to {output_path}")
    else:
        click.echo(text)

if __name__ == "__main__":
    cli()
