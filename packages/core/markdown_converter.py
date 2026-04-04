"""
HTML-to-Markdown Converter — clean HTML extraction and markdown conversion.

Provides LLM-ready markdown output from raw HTML using trafilatura for
boilerplate removal and html2text for markdown conversion. Supports
multiple output formats: markdown, cleaned HTML, raw HTML, and JSON.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

__all__ = [
    "MarkdownConverter",
    "ConversionResult",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Average characters per token for rough LLM token estimation
_CHARS_PER_TOKEN = 4

# Regex patterns for post-processing
_CONSECUTIVE_BLANK_LINES = re.compile(r"\n{3,}")
_EMPTY_HEADING = re.compile(r"^#{1,6}\s*$", re.MULTILINE)
_BROKEN_RELATIVE_LINK = re.compile(
    r"\[([^\]]*)\]\((/[^\)]*)\)",
)
_EMPTY_LINK = re.compile(r"\[([^\]]*)\]\(\s*\)")
_TRAILING_WHITESPACE = re.compile(r"[ \t]+$", re.MULTILINE)


# ---------------------------------------------------------------------------
# ConversionResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class ConversionResult:
    """Result of an HTML-to-markdown (or other format) conversion."""

    content: str
    format: str  # "markdown", "html", "raw", "json"
    title: str = ""
    estimated_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# MarkdownConverter
# ---------------------------------------------------------------------------

class MarkdownConverter:
    """Converts raw HTML to clean, LLM-ready markdown.

    Pipeline:
      1. Clean HTML with trafilatura (strip nav, footer, ads, chrome)
      2. Convert cleaned HTML to markdown with html2text
      3. Post-process markdown (fix broken links, remove empty sections)

    Graceful fallback: if trafilatura fails, falls back to html2text
    directly on the raw HTML.
    """

    def __init__(self) -> None:
        self._h2t = self._create_html2text()

    # -- public API ---------------------------------------------------------

    def convert(
        self,
        html: str,
        url: str = "",
        output_format: str = "markdown",
    ) -> ConversionResult:
        """Convert HTML to the requested output format.

        Parameters
        ----------
        html:
            Raw HTML string.
        url:
            Source URL, used for resolving relative links and metadata.
        output_format:
            One of ``"markdown"``, ``"html"``, ``"raw"``, ``"json"``.

        Returns
        -------
        ConversionResult
            Converted content with metadata.
        """
        if not html or not html.strip():
            return ConversionResult(
                content="",
                format=output_format,
                title="",
                estimated_tokens=0,
                metadata={},
            )

        if output_format == "raw":
            return ConversionResult(
                content=html,
                format="raw",
                title=self._extract_title_from_html(html),
                estimated_tokens=self.estimate_tokens(html),
                metadata={},
            )

        # Step 1: clean HTML with trafilatura
        cleaned_html, traf_metadata = self._trafilatura_extract(html, url)

        title = traf_metadata.get("title", "") or self._extract_title_from_html(html)
        metadata = {
            k: v
            for k, v in traf_metadata.items()
            if k != "title" and v
        }

        if output_format == "html":
            content = cleaned_html if cleaned_html else html
            return ConversionResult(
                content=content,
                format="html",
                title=title,
                estimated_tokens=self.estimate_tokens(content),
                metadata=metadata,
            )

        # Step 2: convert to markdown
        source_html = cleaned_html if cleaned_html else html
        markdown = self.html_to_markdown(source_html)

        # Step 3: post-process
        markdown = self.post_process(markdown, base_url=url)

        if output_format == "json":
            # Return markdown content but tagged as json format for
            # downstream JSON envelope wrapping
            return ConversionResult(
                content=markdown,
                format="json",
                title=title,
                estimated_tokens=self.estimate_tokens(markdown),
                metadata=metadata,
            )

        return ConversionResult(
            content=markdown,
            format="markdown",
            title=title,
            estimated_tokens=self.estimate_tokens(markdown),
            metadata=metadata,
        )

    def clean_html(self, html: str, url: str = "") -> str:
        """Use trafilatura to extract main content as cleaned HTML.

        Falls back to the raw HTML if trafilatura returns nothing.
        """
        cleaned, _ = self._trafilatura_extract(html, url)
        return cleaned if cleaned else html

    def html_to_markdown(self, html: str) -> str:
        """Convert HTML to markdown using html2text."""
        try:
            import html2text as _h2t_mod  # noqa: F811
        except ImportError:
            logger.error(
                "html2text is not installed — returning stripped text"
            )
            return self._fallback_strip_tags(html)

        h2t = self._create_html2text()
        return h2t.handle(html)

    def post_process(self, markdown: str, base_url: str = "") -> str:
        """Post-process markdown output.

        - Fix relative URLs using base_url
        - Remove empty headings
        - Remove empty links
        - Collapse consecutive blank lines
        - Strip trailing whitespace
        """
        if not markdown:
            return markdown

        # Fix relative URLs
        if base_url:
            markdown = self._fix_relative_urls(markdown, base_url)

        # Remove empty links like [text]()
        markdown = _EMPTY_LINK.sub(r"\1", markdown)

        # Remove empty headings (### with no text)
        markdown = _EMPTY_HEADING.sub("", markdown)

        # Collapse 3+ consecutive newlines to 2
        markdown = _CONSECUTIVE_BLANK_LINES.sub("\n\n", markdown)

        # Strip trailing whitespace per line
        markdown = _TRAILING_WHITESPACE.sub("", markdown)

        return markdown.strip()

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (~4 characters per token)."""
        if not text:
            return 0
        return max(1, len(text) // _CHARS_PER_TOKEN)

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximately *max_tokens* tokens.

        Respects word boundaries so words are not split mid-way.
        """
        if not text:
            return text
        max_chars = max_tokens * _CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text

        # Cut at max_chars then back up to the last word boundary
        truncated = text[:max_chars]
        last_space = truncated.rfind(" ")
        if last_space > max_chars * 0.5:
            truncated = truncated[:last_space]

        return truncated.rstrip() + "..."

    # -- private helpers ----------------------------------------------------

    @staticmethod
    def _create_html2text():
        """Create and configure an html2text converter instance."""
        try:
            import html2text
        except ImportError:
            logger.error("html2text is not installed")
            return None

        h = html2text.HTML2Text()
        h.body_width = 0  # no line wrapping
        h.unicode_snob = True  # use unicode instead of ascii
        h.protect_links = True  # don't break long URLs
        h.wrap_links = False
        h.wrap_list_items = False
        h.skip_internal_links = False
        h.ignore_images = False  # preserve images as ![alt](url)
        h.ignore_links = False
        h.ignore_emphasis = False
        h.mark_code = True
        h.decode_errors = "replace"
        return h

    def _trafilatura_extract(
        self, html: str, url: str = ""
    ) -> tuple[str, dict[str, Any]]:
        """Extract main content and metadata via trafilatura.

        Returns (cleaned_html, metadata_dict). On failure returns
        ("", {}) so callers can fall back gracefully.
        """
        metadata: dict[str, Any] = {}

        try:
            import trafilatura
            from trafilatura.metadata import extract_metadata
        except ImportError:
            logger.warning(
                "trafilatura is not installed — skipping HTML cleaning"
            )
            return "", metadata

        try:
            # Extract metadata first
            meta_obj = extract_metadata(html, default_url=url or None)
            if meta_obj:
                metadata = {
                    "title": meta_obj.title or "",
                    "author": meta_obj.author or "",
                    "date": meta_obj.date or "",
                    "sitename": meta_obj.sitename or "",
                }

            # Extract cleaned HTML content
            cleaned = trafilatura.extract(
                html,
                url=url or None,
                output_format="html",
                include_tables=True,
                include_links=True,
                include_images=True,
            )

            if cleaned:
                return cleaned, metadata

            logger.debug("trafilatura returned empty result, will fall back")
            return "", metadata

        except Exception:
            logger.warning("trafilatura extraction failed", exc_info=True)
            return "", metadata

    @staticmethod
    def _extract_title_from_html(html: str) -> str:
        """Quick regex-based title extraction as a fallback."""
        match = re.search(
            r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL
        )
        if match:
            import html as html_lib

            return html_lib.unescape(match.group(1)).strip()
        return ""

    @staticmethod
    def _fix_relative_urls(markdown: str, base_url: str) -> str:
        """Resolve relative URLs in markdown links and images."""
        if not base_url:
            return markdown

        parsed_base = urlparse(base_url)
        if not parsed_base.scheme:
            return markdown

        def _resolve(match: re.Match) -> str:
            text = match.group(1)
            path = match.group(2)
            absolute = urljoin(base_url, path)
            return f"[{text}]({absolute})"

        return _BROKEN_RELATIVE_LINK.sub(_resolve, markdown)

    @staticmethod
    def _fallback_strip_tags(html: str) -> str:
        """Last-resort fallback: strip HTML tags and return plain text."""
        import html as html_lib

        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html_lib.unescape(text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
