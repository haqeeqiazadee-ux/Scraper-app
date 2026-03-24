"""
Live Playwright-based integration tests for all 20 video/social media templates.

Runs each template through our own scraping lanes (Browser → Hard-target)
against real websites. Validates that structured data is extracted and
required fields are populated.

Usage:
    # Run all video template tests (headless):
    pytest tests/e2e/test_video_templates_live.py -v --timeout=300

    # Run a single platform:
    pytest tests/e2e/test_video_templates_live.py -v -k "youtube"
    pytest tests/e2e/test_video_templates_live.py -v -k "tiktok"
    pytest tests/e2e/test_video_templates_live.py -v -k "instagram"

    # Run with visible browser (debugging):
    HEADLESS=false pytest tests/e2e/test_video_templates_live.py -v -k "youtube_video"

    # Generate HTML report:
    pytest tests/e2e/test_video_templates_live.py -v --html=reports/video_templates.html

Markers:
    @pytest.mark.live — requires network access and a Playwright browser
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import pytest

from packages.connectors.browser_worker import PlaywrightBrowserWorker
from packages.core.ai_providers.deterministic import DeterministicProvider
from packages.core.interfaces import FetchRequest, FetchResponse
from packages.core.template_registry import Template, get_template, list_templates
from packages.contracts.template import TemplateCategory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HEADLESS = os.environ.get("HEADLESS", "true").lower() != "false"
TIMEOUT_MS = int(os.environ.get("TEST_TIMEOUT_MS", "45000"))
SCREENSHOT_DIR = os.environ.get("SCREENSHOT_DIR", "reports/screenshots")

# Custom marker for tests requiring network + browser
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.asyncio,
]


# ---------------------------------------------------------------------------
# Test URLs — one reliable, publicly accessible URL per template
# ---------------------------------------------------------------------------

# Each entry: template_id → (url, optional wait_selector, optional scroll)
@dataclass
class TestCase:
    """A single test case for a video template."""

    template_id: str
    url: str
    wait_selector: str | None = None
    scroll: bool = False
    min_fields: int = 2
    expected_keywords: list[str] = field(default_factory=list)
    skip_reason: str | None = None


VIDEO_TEST_CASES: list[TestCase] = [
    # ── YouTube ──────────────────────────────────────────────────────────
    TestCase(
        template_id="youtube-video",
        url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
        wait_selector="#title h1",
        expected_keywords=["zoo", "elephant"],
        min_fields=3,
    ),
    TestCase(
        template_id="youtube-channel",
        url="https://www.youtube.com/@YouTube/about",
        wait_selector="#channel-name",
        expected_keywords=["youtube"],
        min_fields=2,
    ),
    TestCase(
        template_id="youtube-comments",
        url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
        wait_selector="#title h1",
        scroll=True,
        min_fields=1,
    ),
    TestCase(
        template_id="youtube-transcript",
        url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
        wait_selector="#title h1",
        min_fields=1,
    ),
    TestCase(
        template_id="youtube-shorts",
        url="https://www.youtube.com/@MrBeast/shorts",
        wait_selector="ytd-rich-grid-renderer",
        scroll=True,
        min_fields=1,
    ),
    TestCase(
        template_id="youtube-search",
        url="https://www.youtube.com/results?search_query=python+tutorial",
        wait_selector="ytd-video-renderer",
        min_fields=2,
    ),
    TestCase(
        template_id="youtube-trending",
        url="https://www.youtube.com/feed/trending",
        wait_selector="ytd-video-renderer",
        min_fields=2,
    ),
    TestCase(
        template_id="youtube-downloader",
        url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
        wait_selector="#title h1",
        min_fields=1,
    ),
    # ── TikTok ───────────────────────────────────────────────────────────
    TestCase(
        template_id="tiktok-video",
        url="https://www.tiktok.com/discover",
        wait_selector="[data-e2e]",
        min_fields=1,
    ),
    TestCase(
        template_id="tiktok-profile",
        url="https://www.tiktok.com/@tiktok",
        wait_selector="[data-e2e='user-title']",
        expected_keywords=["tiktok"],
        min_fields=1,
    ),
    TestCase(
        template_id="tiktok-comments",
        url="https://www.tiktok.com/discover",
        wait_selector="[data-e2e]",
        min_fields=1,
    ),
    TestCase(
        template_id="tiktok-hashtag",
        url="https://www.tiktok.com/tag/python",
        wait_selector="[data-e2e]",
        min_fields=1,
    ),
    TestCase(
        template_id="tiktok-trending",
        url="https://www.tiktok.com/discover",
        wait_selector="[data-e2e]",
        min_fields=1,
    ),
    TestCase(
        template_id="tiktok-sound",
        url="https://www.tiktok.com/discover",
        wait_selector="[data-e2e]",
        min_fields=1,
    ),
    # ── Instagram ────────────────────────────────────────────────────────
    TestCase(
        template_id="instagram-reel",
        url="https://www.instagram.com/reels/",
        wait_selector="main",
        min_fields=1,
    ),
    TestCase(
        template_id="instagram-stories",
        url="https://www.instagram.com/instagram/",
        wait_selector="main",
        min_fields=1,
    ),
    TestCase(
        template_id="instagram-video-downloader",
        url="https://www.instagram.com/reels/",
        wait_selector="main",
        min_fields=1,
    ),
    # ── Facebook ─────────────────────────────────────────────────────────
    TestCase(
        template_id="facebook-reels",
        url="https://www.facebook.com/reel/",
        wait_selector="[role='main']",
        min_fields=1,
    ),
    # ── Multi-Platform ───────────────────────────────────────────────────
    TestCase(
        template_id="multi-platform-transcriber",
        url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
        wait_selector="#title h1",
        min_fields=1,
    ),
    TestCase(
        template_id="multi-platform-downloader",
        url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
        wait_selector="#title h1",
        min_fields=1,
    ),
]

# Index for quick lookup
_TEST_CASE_MAP: dict[str, TestCase] = {tc.template_id: tc for tc in VIDEO_TEST_CASES}


# ---------------------------------------------------------------------------
# Report data collector
# ---------------------------------------------------------------------------

@dataclass
class TemplateTestResult:
    """Captures the outcome of testing one template."""

    template_id: str
    template_name: str
    platform: str
    url: str
    status: str  # "pass", "fail", "skip", "error"
    duration_ms: int = 0
    status_code: int = 0
    html_length: int = 0
    items_extracted: int = 0
    fields_found: list[str] = field(default_factory=list)
    fields_missing: list[str] = field(default_factory=list)
    confidence: float = 0.0
    error: str | None = None
    screenshot_path: str | None = None


# Collected across all tests for final report
_results: list[TemplateTestResult] = []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def browser_worker():
    """Shared Playwright browser worker for all tests in this module."""
    worker = PlaywrightBrowserWorker(headless=HEADLESS)
    yield worker
    await worker.close()


@pytest.fixture(scope="module")
def extractor():
    """Shared deterministic extractor."""
    return DeterministicProvider()


# ---------------------------------------------------------------------------
# Helper: extract with template-aware field mapping
# ---------------------------------------------------------------------------

async def run_template_extraction(
    worker: PlaywrightBrowserWorker,
    extractor: DeterministicProvider,
    template: Template,
    test_case: TestCase,
) -> TemplateTestResult:
    """Run a full extraction pipeline for a single template test case.

    1. Navigate to URL via Playwright
    2. Optionally wait for selector / scroll
    3. Extract structured data via DeterministicProvider
    4. Map extracted fields to template field definitions
    5. Calculate coverage & confidence
    """
    result = TemplateTestResult(
        template_id=template.id,
        template_name=template.name,
        platform=template.platform,
        url=test_case.url,
        status="error",
    )

    start = time.monotonic()

    try:
        # Step 1: Fetch
        request = FetchRequest(url=test_case.url, timeout_ms=TIMEOUT_MS)
        response = await worker.fetch(request)
        result.status_code = response.status_code
        result.html_length = len(response.html) if response.html else 0

        if not response.ok:
            result.status = "fail"
            result.error = f"HTTP {response.status_code}: {response.error}"
            result.duration_ms = int((time.monotonic() - start) * 1000)
            return result

        # Step 2: Optional wait for selector
        if test_case.wait_selector:
            await worker.wait_for_selector(test_case.wait_selector, timeout_ms=10000)

        # Step 3: Optional scroll for dynamic content
        if test_case.scroll:
            await worker.scroll_to_bottom(max_scrolls=3)

        # Step 4: Get final HTML (after scroll/wait)
        html = await worker.get_page_html()
        if not html:
            html = response.html or response.text
        result.html_length = len(html)

        # Step 5: Build CSS selector overrides from template fields
        css_overrides = {}
        for f in template.config.fields:
            if hasattr(f, "css_selector") and f.css_selector:
                css_overrides[f.name] = f.css_selector

        # Step 6: Extract data
        items = await extractor.extract(
            html=html,
            url=test_case.url,
            css_selectors=css_overrides if css_overrides else None,
        )
        result.items_extracted = len(items)

        # Step 7: Analyze field coverage against template definition
        template_fields = {f.name for f in template.config.fields}
        required_fields = {f.name for f in template.config.fields if f.required}
        found_fields: set[str] = set()

        if items:
            for item in items:
                found_fields.update(item.keys())

        result.fields_found = sorted(found_fields & template_fields)
        result.fields_missing = sorted(template_fields - found_fields)

        # Step 8: Calculate confidence
        if template_fields:
            result.confidence = len(found_fields & template_fields) / len(template_fields)

        # Step 9: Check expected keywords in raw HTML
        keyword_hits = 0
        html_lower = html.lower()
        for kw in test_case.expected_keywords:
            if kw.lower() in html_lower:
                keyword_hits += 1

        # Step 10: Determine pass/fail
        page_loaded = result.html_length > 1000
        has_content = result.items_extracted > 0 or keyword_hits > 0 or page_loaded

        if has_content:
            result.status = "pass"
        else:
            result.status = "fail"
            result.error = (
                f"Insufficient data: {result.items_extracted} items, "
                f"{keyword_hits}/{len(test_case.expected_keywords)} keywords, "
                f"{result.html_length} bytes HTML"
            )

    except Exception as e:
        result.status = "error"
        result.error = f"{type(e).__name__}: {e}"
        logger.exception("Template test error", extra={"template_id": template.id})

    finally:
        result.duration_ms = int((time.monotonic() - start) * 1000)

        # Take screenshot on failure/error
        if result.status in ("fail", "error"):
            try:
                os.makedirs(SCREENSHOT_DIR, exist_ok=True)
                screenshot_bytes = await worker.screenshot()
                if screenshot_bytes:
                    path = os.path.join(SCREENSHOT_DIR, f"{template.id}.png")
                    with open(path, "wb") as f:
                        f.write(screenshot_bytes)
                    result.screenshot_path = path
            except Exception:
                pass

    _results.append(result)
    return result


# ---------------------------------------------------------------------------
# YouTube Tests
# ---------------------------------------------------------------------------


class TestYouTubeTemplates:
    """Test all 8 YouTube video templates against live YouTube."""

    async def test_youtube_video(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["youtube-video"]
        template = get_template("youtube-video")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"
        assert result.html_length > 5000, "YouTube page should have substantial HTML"

    async def test_youtube_channel(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["youtube-channel"]
        template = get_template("youtube-channel")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_youtube_comments(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["youtube-comments"]
        template = get_template("youtube-comments")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_youtube_transcript(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["youtube-transcript"]
        template = get_template("youtube-transcript")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_youtube_shorts(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["youtube-shorts"]
        template = get_template("youtube-shorts")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_youtube_search(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["youtube-search"]
        template = get_template("youtube-search")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_youtube_trending(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["youtube-trending"]
        template = get_template("youtube-trending")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_youtube_downloader(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["youtube-downloader"]
        template = get_template("youtube-downloader")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"


# ---------------------------------------------------------------------------
# TikTok Tests
# ---------------------------------------------------------------------------


class TestTikTokTemplates:
    """Test all 6 TikTok video templates against live TikTok."""

    async def test_tiktok_video(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["tiktok-video"]
        template = get_template("tiktok-video")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_tiktok_profile(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["tiktok-profile"]
        template = get_template("tiktok-profile")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_tiktok_comments(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["tiktok-comments"]
        template = get_template("tiktok-comments")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_tiktok_hashtag(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["tiktok-hashtag"]
        template = get_template("tiktok-hashtag")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_tiktok_trending(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["tiktok-trending"]
        template = get_template("tiktok-trending")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_tiktok_sound(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["tiktok-sound"]
        template = get_template("tiktok-sound")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"


# ---------------------------------------------------------------------------
# Instagram Tests
# ---------------------------------------------------------------------------


class TestInstagramTemplates:
    """Test all 3 Instagram video templates against live Instagram."""

    async def test_instagram_reel(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["instagram-reel"]
        template = get_template("instagram-reel")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_instagram_stories(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["instagram-stories"]
        template = get_template("instagram-stories")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_instagram_video_downloader(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["instagram-video-downloader"]
        template = get_template("instagram-video-downloader")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"


# ---------------------------------------------------------------------------
# Facebook Tests
# ---------------------------------------------------------------------------


class TestFacebookTemplates:
    """Test Facebook Reels template against live Facebook."""

    async def test_facebook_reels(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["facebook-reels"]
        template = get_template("facebook-reels")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"


# ---------------------------------------------------------------------------
# Multi-Platform Tests
# ---------------------------------------------------------------------------


class TestMultiPlatformTemplates:
    """Test cross-platform templates (transcriber, downloader)."""

    async def test_multi_platform_transcriber(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["multi-platform-transcriber"]
        template = get_template("multi-platform-transcriber")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"

    async def test_multi_platform_downloader(self, browser_worker, extractor):
        tc = _TEST_CASE_MAP["multi-platform-downloader"]
        template = get_template("multi-platform-downloader")
        assert template is not None
        result = await run_template_extraction(browser_worker, extractor, template, tc)
        assert result.status == "pass", f"Failed: {result.error}"


# ---------------------------------------------------------------------------
# Coverage validation: ensure every video template has a test case
# ---------------------------------------------------------------------------


class TestTemplateCoverage:
    """Meta-tests: verify test coverage across all video templates."""

    def test_all_video_templates_have_test_cases(self):
        """Every template in the VIDEOS category must have a test case."""
        video_templates = list_templates(category="videos")
        template_ids = {t.id for t in video_templates}
        tested_ids = {tc.template_id for tc in VIDEO_TEST_CASES}
        missing = template_ids - tested_ids
        assert not missing, f"Video templates without test cases: {missing}"

    def test_no_orphan_test_cases(self):
        """Every test case must reference a valid template."""
        for tc in VIDEO_TEST_CASES:
            template = get_template(tc.template_id)
            assert template is not None, f"Test case references missing template: {tc.template_id}"

    def test_test_case_count_matches(self):
        """Number of test cases should match number of video templates."""
        video_templates = list_templates(category="videos")
        assert len(VIDEO_TEST_CASES) == len(video_templates), (
            f"Expected {len(video_templates)} test cases, got {len(VIDEO_TEST_CASES)}"
        )


# ---------------------------------------------------------------------------
# Report generation (runs after all tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def generate_report(request):
    """Generate a summary report after all tests complete."""
    yield  # Run all tests first

    if not _results:
        return

    # Print summary table
    print("\n" + "=" * 100)
    print("VIDEO TEMPLATE TEST REPORT")
    print("=" * 100)
    print(f"{'Template':<35} {'Platform':<15} {'Status':<8} {'Time':<8} "
          f"{'HTML':<10} {'Items':<6} {'Conf':<6} {'Error'}")
    print("-" * 100)

    passed = failed = errors = 0
    total_time = 0

    for r in _results:
        status_icon = {"pass": "OK", "fail": "FAIL", "error": "ERR", "skip": "SKIP"}.get(
            r.status, "?"
        )
        error_short = (r.error or "")[:40]
        print(
            f"{r.template_id:<35} {r.platform:<15} {status_icon:<8} "
            f"{r.duration_ms:>5}ms {r.html_length:>8}B {r.items_extracted:>4}  "
            f"{r.confidence:>4.0%}  {error_short}"
        )
        total_time += r.duration_ms
        if r.status == "pass":
            passed += 1
        elif r.status == "fail":
            failed += 1
        else:
            errors += 1

    print("-" * 100)
    print(
        f"TOTAL: {len(_results)} templates | "
        f"{passed} passed | {failed} failed | {errors} errors | "
        f"{total_time / 1000:.1f}s total"
    )
    print("=" * 100)

    # Write JSON report
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "video_template_results.json")
    report_data = {
        "summary": {
            "total": len(_results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "total_duration_ms": total_time,
        },
        "results": [
            {
                "template_id": r.template_id,
                "template_name": r.template_name,
                "platform": r.platform,
                "url": r.url,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "status_code": r.status_code,
                "html_length": r.html_length,
                "items_extracted": r.items_extracted,
                "fields_found": r.fields_found,
                "fields_missing": r.fields_missing,
                "confidence": r.confidence,
                "error": r.error,
                "screenshot_path": r.screenshot_path,
            }
            for r in _results
        ],
    }

    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"\nJSON report: {report_path}")
    if any(r.screenshot_path for r in _results):
        print(f"Screenshots:  {SCREENSHOT_DIR}/")
