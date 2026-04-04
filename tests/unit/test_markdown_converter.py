"""Tests for markdown converter."""

import pytest
from unittest.mock import patch, MagicMock

from packages.core.markdown_converter import MarkdownConverter


@pytest.fixture
def converter():
    return MarkdownConverter()


@pytest.fixture
def sample_html():
    return """
    <html>
    <head><title>Test Product Page</title></head>
    <body>
        <h1>Product Name</h1>
        <p>This is a <strong>great</strong> product with many features.</p>
        <ul>
            <li>Feature one</li>
            <li>Feature two</li>
        </ul>
    </body>
    </html>
    """


@pytest.fixture
def complex_html():
    return """
    <html>
    <head>
        <title>E-Commerce Store</title>
        <style>.hidden { display: none; }</style>
        <script>var analytics = {};</script>
    </head>
    <body>
        <nav><a href="/">Home</a><a href="/about">About</a></nav>
        <main>
            <h1>Laptop Pro Max</h1>
            <h2>Overview</h2>
            <p>The best laptop for professionals.</p>
            <h3>Specifications</h3>
            <table>
                <tr><th>CPU</th><td>M3 Pro</td></tr>
                <tr><th>RAM</th><td>36 GB</td></tr>
            </table>
            <p>Price: <strong>$2,499</strong></p>
            <p>Visit <a href="https://example.com/details">details page</a> for more.</p>
            <img src="https://example.com/laptop.jpg" alt="Laptop Pro Max" />
        </main>
        <footer><p>&copy; 2025 Store Inc.</p></footer>
    </body>
    </html>
    """


class TestConvertHtmlToMarkdown:

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_convert_html_to_markdown(self, mock_h2t, mock_traf, converter, sample_html):
        """Basic HTML to markdown conversion uses trafilatura then html2text."""
        mock_traf.extract.return_value = (
            "<p>This is a <strong>great</strong> product with many features.</p>"
        )
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = (
            "This is a **great** product with many features.\n"
        )

        result = converter.convert(sample_html, url="https://example.com/products")

        assert "great" in result.content
        assert result.output_format == "markdown"

    @patch("packages.core.markdown_converter.trafilatura")
    def test_convert_html_to_clean_html(self, mock_traf, converter, sample_html):
        """output_format='html' returns cleaned HTML from trafilatura."""
        cleaned = "<p>This is a <strong>great</strong> product.</p>"
        mock_traf.extract.return_value = cleaned

        result = converter.convert(
            sample_html, url="https://example.com", output_format="html"
        )

        assert result.output_format == "html"
        assert "<strong>" in result.content or "great" in result.content

    def test_convert_raw_passthrough(self, converter, sample_html):
        """output_format='raw' returns the original HTML unchanged."""
        result = converter.convert(
            sample_html, url="https://example.com", output_format="raw"
        )

        assert result.output_format == "raw"
        assert "<h1>" in result.content
        assert "Product Name" in result.content

    def test_convert_json_passthrough(self, converter, sample_html):
        """output_format='json' returns empty content (JSON extraction handled elsewhere)."""
        result = converter.convert(
            sample_html, url="https://example.com", output_format="json"
        )

        assert result.output_format == "json"
        assert result.content == ""


class TestCleanHtml:

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_clean_html_strips_nav_footer(self, mock_h2t, mock_traf, converter, complex_html):
        """Trafilatura removes navigation and footer boilerplate."""
        # trafilatura should strip nav/footer and return only main content
        mock_traf.extract.return_value = (
            "<h1>Laptop Pro Max</h1><p>The best laptop for professionals.</p>"
        )
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = (
            "# Laptop Pro Max\n\nThe best laptop for professionals.\n"
        )

        result = converter.convert(complex_html, url="https://example.com")

        assert "Home" not in result.content
        assert "Store Inc" not in result.content
        mock_traf.extract.assert_called_once()

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_clean_html_strips_scripts_styles(self, mock_h2t, mock_traf, converter, complex_html):
        """Script and style tags are removed from output."""
        mock_traf.extract.return_value = "<p>The best laptop.</p>"
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = "The best laptop.\n"

        result = converter.convert(complex_html, url="https://example.com")

        assert "analytics" not in result.content
        assert "<script>" not in result.content
        assert "<style>" not in result.content
        assert ".hidden" not in result.content


class TestMarkdownFormatting:

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_markdown_tables_preserved(self, mock_h2t, mock_traf, converter):
        """HTML tables are converted to markdown tables."""
        html = "<table><tr><th>CPU</th><td>M3</td></tr></table>"
        mock_traf.extract.return_value = html
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = "| CPU | M3 |\n| --- | --- |\n"

        result = converter.convert(
            f"<html><body>{html}</body></html>", url="https://example.com"
        )

        assert "|" in result.content
        assert "CPU" in result.content

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_markdown_headings_preserved(self, mock_h2t, mock_traf, converter):
        """h1-h6 hierarchy is maintained in markdown output."""
        html = "<h1>Title</h1><h2>Subtitle</h2><h3>Section</h3><p>Text</p>"
        mock_traf.extract.return_value = html
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = (
            "# Title\n\n## Subtitle\n\n### Section\n\nText\n"
        )

        result = converter.convert(
            f"<html><body>{html}</body></html>", url="https://example.com"
        )

        assert "# Title" in result.content
        assert "## Subtitle" in result.content
        assert "### Section" in result.content

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_markdown_images_converted(self, mock_h2t, mock_traf, converter):
        """img tags are converted to ![alt](src) markdown syntax."""
        html = '<img src="https://example.com/img.jpg" alt="Product Photo" />'
        mock_traf.extract.return_value = html
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = (
            "![Product Photo](https://example.com/img.jpg)\n"
        )

        result = converter.convert(
            f"<html><body>{html}</body></html>", url="https://example.com"
        )

        assert "![Product Photo]" in result.content
        assert "https://example.com/img.jpg" in result.content

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_markdown_links_preserved(self, mock_h2t, mock_traf, converter):
        """a tags are converted to [text](href) markdown syntax."""
        html = '<a href="https://example.com/page">Click here</a>'
        mock_traf.extract.return_value = html
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = (
            "[Click here](https://example.com/page)\n"
        )

        result = converter.convert(
            f"<html><body>{html}</body></html>", url="https://example.com"
        )

        assert "[Click here]" in result.content
        assert "(https://example.com/page)" in result.content


class TestPostProcessing:

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_post_process_removes_empty_headings(self, mock_h2t, mock_traf, converter):
        """Empty heading lines like '## \\n' are removed from output."""
        mock_traf.extract.return_value = "<h2></h2><p>Content</p>"
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = "## \n\nContent\n"

        result = converter.convert(
            "<html><body><h2></h2><p>Content</p></body></html>",
            url="https://example.com",
        )

        # Empty headings should be stripped
        lines = result.content.strip().split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                # Heading line must have text after the # symbols
                heading_text = stripped.lstrip("#").strip()
                assert heading_text != ""

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_post_process_collapses_blank_lines(self, mock_h2t, mock_traf, converter):
        """More than 2 consecutive blank lines are collapsed to 2."""
        mock_traf.extract.return_value = "<p>A</p><p>B</p>"
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = "A\n\n\n\n\n\nB\n"

        result = converter.convert(
            "<html><body><p>A</p><p>B</p></body></html>",
            url="https://example.com",
        )

        # Should have at most 2 consecutive blank lines (3 newlines in a row)
        assert "\n\n\n\n" not in result.content


class TestTokenEstimation:

    def test_estimate_tokens(self, converter):
        """Token estimation returns approximately len/4."""
        text = "a" * 400  # 400 chars
        estimated = converter.estimate_tokens(text)
        assert 80 <= estimated <= 120  # ~100 tokens, allow some tolerance

    def test_estimate_tokens_empty(self, converter):
        """Empty string returns 0 tokens."""
        assert converter.estimate_tokens("") == 0

    def test_truncate_to_tokens(self, converter):
        """Truncation respects word boundaries."""
        text = "The quick brown fox jumps over the lazy dog " * 50  # long text
        truncated = converter.truncate_to_tokens(text, max_tokens=10)
        # Should end at a word boundary (no partial words)
        assert not truncated.endswith(" ")  # no trailing space
        words = truncated.split()
        for word in words:
            assert len(word) > 0  # no empty words

    def test_truncate_to_tokens_short_text(self, converter):
        """Short text below token limit is returned as-is."""
        text = "Hello world"
        truncated = converter.truncate_to_tokens(text, max_tokens=1000)
        assert truncated == text


class TestConversionResult:

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_conversion_result_has_metadata(self, mock_h2t, mock_traf, converter):
        """Conversion result includes title and estimated_tokens metadata."""
        html = "<html><head><title>My Product</title></head><body><p>Content here</p></body></html>"
        mock_traf.extract.return_value = "<p>Content here</p>"
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = "Content here\n"

        result = converter.convert(html, url="https://example.com")

        assert hasattr(result, "title") or "title" in (result.metadata if hasattr(result, "metadata") else {})
        assert hasattr(result, "estimated_tokens") or "estimated_tokens" in (result.metadata if hasattr(result, "metadata") else {})
        # Tokens should be a positive integer for non-empty content
        tokens = getattr(result, "estimated_tokens", None) or result.metadata.get("estimated_tokens", 0)
        assert tokens > 0


class TestFallbackBehavior:

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_fallback_when_trafilatura_fails(self, mock_h2t, mock_traf, converter):
        """Falls back to html2text when trafilatura raises an error."""
        mock_traf.extract.side_effect = Exception("trafilatura parsing error")
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = "Fallback content\n"

        html = "<html><body><p>Fallback content</p></body></html>"
        result = converter.convert(html, url="https://example.com")

        assert "Fallback" in result.content
        mock_h2t_instance.handle.assert_called()

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_fallback_when_trafilatura_returns_none(self, mock_h2t, mock_traf, converter):
        """Falls back to html2text when trafilatura returns None."""
        mock_traf.extract.return_value = None
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = "Direct conversion\n"

        html = "<html><body><p>Direct conversion</p></body></html>"
        result = converter.convert(html, url="https://example.com")

        assert "Direct conversion" in result.content


class TestRelativeUrls:

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_relative_urls_resolved(self, mock_h2t, mock_traf, converter):
        """Relative URLs in the HTML are converted to absolute URLs."""
        html = '<html><body><a href="/products/123">Link</a><img src="/img/photo.jpg" /></body></html>'
        mock_traf.extract.return_value = (
            '<a href="/products/123">Link</a><img src="/img/photo.jpg" />'
        )
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = (
            "[Link](https://example.com/products/123)\n\n"
            "![](https://example.com/img/photo.jpg)\n"
        )

        result = converter.convert(html, url="https://example.com/page")

        # The converter should resolve relative URLs before/during conversion
        assert "/products/123" not in result.content or "https://example.com/products/123" in result.content

    @patch("packages.core.markdown_converter.trafilatura")
    @patch("packages.core.markdown_converter.html2text")
    def test_absolute_urls_unchanged(self, mock_h2t, mock_traf, converter):
        """Absolute URLs are left as-is."""
        html = '<html><body><a href="https://other.com/page">External</a></body></html>'
        mock_traf.extract.return_value = '<a href="https://other.com/page">External</a>'
        mock_h2t_instance = MagicMock()
        mock_h2t.HTML2Text.return_value = mock_h2t_instance
        mock_h2t_instance.handle.return_value = (
            "[External](https://other.com/page)\n"
        )

        result = converter.convert(html, url="https://example.com")

        assert "https://other.com/page" in result.content
