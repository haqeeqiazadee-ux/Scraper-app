#!/usr/bin/env python3
"""
Standalone runner for video template live tests.

Runs all 20 video templates through our Playwright browser lane and
prints a real-time dashboard. No pytest required — just run directly.

Usage:
    python scripts/run_video_template_tests.py                  # all templates
    python scripts/run_video_template_tests.py --platform youtube  # one platform
    python scripts/run_video_template_tests.py --template youtube-video  # one template
    python scripts/run_video_template_tests.py --headless false    # visible browser
    python scripts/run_video_template_tests.py --parallel 3        # concurrent tabs
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.connectors.browser_worker import PlaywrightBrowserWorker
from packages.core.ai_providers.deterministic import DeterministicProvider
from packages.core.interfaces import FetchRequest
from packages.core.template_registry import get_template, list_templates


# ── Test URLs per template ──────────────────────────────────────────────

TEST_URLS: dict[str, dict] = {
    # YouTube
    "youtube-video": {
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "wait": "#title h1",
    },
    "youtube-channel": {
        "url": "https://www.youtube.com/@YouTube/about",
        "wait": "#channel-name",
    },
    "youtube-comments": {
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "wait": "#title h1",
        "scroll": True,
    },
    "youtube-transcript": {
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "wait": "#title h1",
    },
    "youtube-shorts": {
        "url": "https://www.youtube.com/@MrBeast/shorts",
        "wait": "ytd-rich-grid-renderer",
        "scroll": True,
    },
    "youtube-search": {
        "url": "https://www.youtube.com/results?search_query=python+tutorial",
        "wait": "ytd-video-renderer",
    },
    "youtube-trending": {
        "url": "https://www.youtube.com/feed/trending",
        "wait": "ytd-video-renderer",
    },
    "youtube-downloader": {
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "wait": "#title h1",
    },
    # TikTok
    "tiktok-video": {
        "url": "https://www.tiktok.com/discover",
        "wait": "[data-e2e]",
    },
    "tiktok-profile": {
        "url": "https://www.tiktok.com/@tiktok",
        "wait": "[data-e2e='user-title']",
    },
    "tiktok-comments": {
        "url": "https://www.tiktok.com/discover",
        "wait": "[data-e2e]",
    },
    "tiktok-hashtag": {
        "url": "https://www.tiktok.com/tag/python",
        "wait": "[data-e2e]",
    },
    "tiktok-trending": {
        "url": "https://www.tiktok.com/discover",
        "wait": "[data-e2e]",
    },
    "tiktok-sound": {
        "url": "https://www.tiktok.com/discover",
        "wait": "[data-e2e]",
    },
    # Instagram
    "instagram-reel": {
        "url": "https://www.instagram.com/reels/",
        "wait": "main",
    },
    "instagram-stories": {
        "url": "https://www.instagram.com/instagram/",
        "wait": "main",
    },
    "instagram-video-downloader": {
        "url": "https://www.instagram.com/reels/",
        "wait": "main",
    },
    # Facebook
    "facebook-reels": {
        "url": "https://www.facebook.com/reel/",
        "wait": "[role='main']",
    },
    # Multi-platform
    "multi-platform-transcriber": {
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "wait": "#title h1",
    },
    "multi-platform-downloader": {
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "wait": "#title h1",
    },
}


async def test_single_template(
    worker: PlaywrightBrowserWorker,
    extractor: DeterministicProvider,
    template_id: str,
    config: dict,
    timeout_ms: int = 45000,
) -> dict:
    """Run one template test and return result dict."""
    template = get_template(template_id)
    if not template:
        return {"template_id": template_id, "status": "error", "error": "Template not found"}

    url = config["url"]
    start = time.monotonic()

    try:
        # Fetch page
        request = FetchRequest(url=url, timeout_ms=timeout_ms)
        response = await worker.fetch(request)

        if not response.ok:
            return {
                "template_id": template_id,
                "platform": template.platform,
                "url": url,
                "status": "fail",
                "status_code": response.status_code,
                "error": response.error or f"HTTP {response.status_code}",
                "duration_ms": int((time.monotonic() - start) * 1000),
            }

        # Wait for selector
        if config.get("wait"):
            await worker.wait_for_selector(config["wait"], timeout_ms=10000)

        # Scroll if needed
        if config.get("scroll"):
            await worker.scroll_to_bottom(max_scrolls=3)

        # Get final HTML
        html = await worker.get_page_html() or response.html or response.text
        html_len = len(html) if html else 0

        # Extract
        items = await extractor.extract(html=html, url=url) if html else []

        # Field coverage
        template_fields = {f.name for f in template.config.fields}
        found_fields: set[str] = set()
        for item in items:
            found_fields.update(item.keys())
        matched = found_fields & template_fields
        confidence = len(matched) / len(template_fields) if template_fields else 0

        elapsed = int((time.monotonic() - start) * 1000)

        return {
            "template_id": template_id,
            "template_name": template.name,
            "platform": template.platform,
            "url": url,
            "status": "pass" if html_len > 1000 else "fail",
            "status_code": response.status_code,
            "html_bytes": html_len,
            "items_extracted": len(items),
            "fields_matched": sorted(matched),
            "fields_missing": sorted(template_fields - found_fields),
            "confidence": round(confidence, 3),
            "duration_ms": elapsed,
        }

    except Exception as e:
        return {
            "template_id": template_id,
            "platform": template.platform if template else "?",
            "url": url,
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
            "duration_ms": int((time.monotonic() - start) * 1000),
        }


async def run_all(
    template_filter: str | None = None,
    platform_filter: str | None = None,
    headless: bool = True,
    timeout_ms: int = 45000,
) -> list[dict]:
    """Run tests for all (or filtered) video templates."""

    # Filter test cases
    cases = dict(TEST_URLS)
    if template_filter:
        cases = {k: v for k, v in cases.items() if k == template_filter}
    if platform_filter:
        platform_lower = platform_filter.lower()
        cases = {
            k: v for k, v in cases.items()
            if (get_template(k) and get_template(k).platform.lower() == platform_lower)
        }

    if not cases:
        print(f"No matching templates found.")
        return []

    print(f"\nRunning {len(cases)} video template tests (headless={headless})")
    print("=" * 90)
    print(f"{'#':<4} {'Template':<35} {'Platform':<14} {'Status':<8} "
          f"{'Time':<8} {'HTML':<10} {'Items':<6}")
    print("-" * 90)

    worker = PlaywrightBrowserWorker(headless=headless)
    extractor = DeterministicProvider()
    results: list[dict] = []

    try:
        for i, (tid, config) in enumerate(cases.items(), 1):
            template = get_template(tid)
            platform = template.platform if template else "?"

            # Print progress indicator
            print(f"{i:<4} {tid:<35} {platform:<14} ", end="", flush=True)

            result = await test_single_template(worker, extractor, tid, config, timeout_ms)
            results.append(result)

            # Print result line
            status = result["status"].upper()
            elapsed = result.get("duration_ms", 0)
            html_bytes = result.get("html_bytes", 0)
            items = result.get("items_extracted", 0)
            error = result.get("error", "")

            if status == "PASS":
                print(f"{'OK':<8} {elapsed:>5}ms {html_bytes:>8}B {items:>4}")
            else:
                print(f"{status:<8} {elapsed:>5}ms {html_bytes:>8}B {items:>4}  {error[:30]}")

    finally:
        await worker.close()

    # Summary
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    errors = sum(1 for r in results if r["status"] == "error")
    total_time = sum(r.get("duration_ms", 0) for r in results)

    print("-" * 90)
    print(f"DONE: {len(results)} templates | {passed} passed | "
          f"{failed} failed | {errors} errors | {total_time / 1000:.1f}s total")
    print("=" * 90)

    # Save JSON report
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/video_template_results.json"
    with open(report_path, "w") as f:
        json.dump({"summary": {"passed": passed, "failed": failed, "errors": errors},
                    "results": results}, f, indent=2)
    print(f"\nReport saved: {report_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Test video templates with Playwright")
    parser.add_argument("--template", help="Test a single template ID")
    parser.add_argument("--platform", help="Test all templates for a platform (youtube, tiktok, etc.)")
    parser.add_argument("--headless", default="true", help="Run headless (true/false)")
    parser.add_argument("--timeout", type=int, default=45000, help="Page load timeout in ms")
    args = parser.parse_args()

    headless = args.headless.lower() != "false"

    asyncio.run(run_all(
        template_filter=args.template,
        platform_filter=args.platform,
        headless=headless,
        timeout_ms=args.timeout,
    ))


if __name__ == "__main__":
    main()
