"""Unit tests for markdown_notes.extract_content."""
import pytest

from markdown_notes.extract_content import (
    extract_code_blocks,
    extract_external_links,
    extract_plain_text,
    extract_summary,
    extract_tables,
)


# ---------------------------------------------------------------------------
# extract_plain_text
# ---------------------------------------------------------------------------

class TestExtractPlainText:
    def test_strips_fenced_code_blocks(self):
        text = "Before\n```python\ncode here\n```\nAfter"
        result = extract_plain_text(text)
        assert "code here" not in result
        assert "Before" in result
        assert "After" in result

    def test_strips_inline_code(self):
        text = "Use `print()` to output."
        result = extract_plain_text(text)
        assert "`" not in result
        assert "Use" in result

    def test_strips_heading_markers(self):
        text = "# Title\n## Section"
        result = extract_plain_text(text)
        assert "#" not in result
        assert "Title" in result
        assert "Section" in result

    def test_replaces_links_with_display_text(self):
        text = "See [my link](https://example.com) for details."
        result = extract_plain_text(text)
        assert "my link" in result
        assert "https://example.com" not in result

    def test_strips_bold_and_italic(self):
        text = "**bold** and *italic* and __under__"
        result = extract_plain_text(text)
        assert "**" not in result
        assert "bold" in result
        assert "italic" in result


# ---------------------------------------------------------------------------
# extract_summary
# ---------------------------------------------------------------------------

class TestExtractSummary:
    def test_returns_first_paragraph(self):
        text = "First paragraph here.\n\nSecond paragraph."
        summary = extract_summary(text)
        assert summary == "First paragraph here."

    def test_returns_none_for_empty_text(self):
        assert extract_summary("") is None

    def test_heading_text_becomes_first_paragraph(self):
        # extract_plain_text removes '#' markers but keeps heading text as a paragraph
        text = "# Heading\n\nReal paragraph."
        summary = extract_summary(text)
        assert summary == "Heading"

    def test_code_blocks_stripped_before_summary(self):
        text = "```python\ncode\n```\n\nReal paragraph."
        summary = extract_summary(text)
        assert summary == "Real paragraph."

    def test_returns_none_when_only_whitespace(self):
        assert extract_summary("   \n\n   ") is None


# ---------------------------------------------------------------------------
# extract_code_blocks
# ---------------------------------------------------------------------------

class TestExtractCodeBlocks:
    def test_extracts_block_with_language(self):
        text = "```python\nprint('hello')\n```"
        blocks = extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"
        assert "print('hello')" in blocks[0]["content"]

    def test_extracts_block_without_language(self):
        text = "```\nplain code\n```"
        blocks = extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["language"] == ""

    def test_extracts_multiple_blocks(self):
        text = "```js\nconsole.log()\n```\nSome text\n```python\npass\n```"
        blocks = extract_code_blocks(text)
        assert len(blocks) == 2
        assert blocks[0]["language"] == "js"
        assert blocks[1]["language"] == "python"

    def test_no_blocks_returns_empty(self):
        assert extract_code_blocks("No code here.") == []


# ---------------------------------------------------------------------------
# extract_tables
# ---------------------------------------------------------------------------

class TestExtractTables:
    def test_extracts_simple_table(self):
        text = "| A | B |\n| - | - |\n| 1 | 2 |"
        tables = extract_tables(text)
        assert len(tables) == 1
        assert tables[0][0] == ["A", "B"]  # header row
        assert tables[0][1] == ["1", "2"]  # data row

    def test_separator_row_excluded(self):
        text = "| H1 | H2 |\n|---|---|\n| v1 | v2 |"
        tables = extract_tables(text)
        for row in tables[0]:
            assert not all(cell.strip("-") == "" for cell in row)

    def test_multiple_tables(self):
        text = (
            "| A | B |\n| - | - |\n| 1 | 2 |\n\n"
            "| C | D |\n| - | - |\n| 3 | 4 |"
        )
        tables = extract_tables(text)
        assert len(tables) == 2

    def test_no_table_returns_empty(self):
        assert extract_tables("No table here.") == []


# ---------------------------------------------------------------------------
# extract_external_links
# ---------------------------------------------------------------------------

class TestExtractExternalLinks:
    def test_extracts_inline_https_link(self):
        text = "Visit [Example](https://example.com) now."
        urls = extract_external_links(text)
        assert "https://example.com" in urls

    def test_extracts_bare_url(self):
        text = "Go to https://bare-url.com for info."
        urls = extract_external_links(text)
        assert "https://bare-url.com" in urls

    def test_deduplicates_urls(self):
        text = "[Link](https://example.com) and https://example.com"
        urls = extract_external_links(text)
        assert urls.count("https://example.com") == 1

    def test_ignores_internal_links(self):
        text = "[Note](other_note.md)"
        urls = extract_external_links(text)
        assert urls == []

    def test_no_links_returns_empty(self):
        assert extract_external_links("Plain text.") == []
