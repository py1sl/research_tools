"""Unit tests for markdown_notes.parse_structure."""
import pytest

from markdown_notes.parse_structure import (
    extract_headings,
    extract_inline_tags,
    extract_internal_links,
    parse_frontmatter,
    score_section_relevance,
    split_by_headings,
)


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_extracts_yaml_metadata(self):
        text = "---\ntitle: Hello\ntags: [a, b]\n---\nBody text"
        meta, body = parse_frontmatter(text)
        assert meta["title"] == "Hello"
        assert meta["tags"] == ["a", "b"]
        assert body.strip() == "Body text"

    def test_no_frontmatter_returns_empty_dict(self):
        text = "# Just a heading\nSome text."
        meta, body = parse_frontmatter(text)
        assert meta == {}
        assert "Just a heading" in body

    def test_returns_empty_dict_on_malformed_frontmatter(self):
        # python-frontmatter is lenient, but we ensure no exception propagates
        text = "---\n: bad: yaml: :\n---\nBody"
        meta, body = parse_frontmatter(text)
        assert isinstance(meta, dict)
        assert isinstance(body, str)


# ---------------------------------------------------------------------------
# extract_headings
# ---------------------------------------------------------------------------

class TestExtractHeadings:
    def test_detects_all_levels(self):
        text = "# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6"
        headings = extract_headings(text)
        assert [(h["level"], h["text"]) for h in headings] == [
            (1, "H1"), (2, "H2"), (3, "H3"), (4, "H4"), (5, "H5"), (6, "H6")
        ]

    def test_ignores_non_heading_lines(self):
        text = "Normal line\n#tag not a heading\n## Real heading"
        headings = extract_headings(text)
        assert len(headings) == 1
        assert headings[0]["text"] == "Real heading"

    def test_empty_text_returns_empty_list(self):
        assert extract_headings("") == []

    def test_heading_text_stripped(self):
        text = "##  Spaced heading  "
        headings = extract_headings(text)
        assert headings[0]["text"] == "Spaced heading"


# ---------------------------------------------------------------------------
# split_by_headings
# ---------------------------------------------------------------------------

class TestSplitByHeadings:
    def test_intro_section_stored_under_empty_key(self):
        text = "Intro text\n\n# Section One\nContent"
        sections = split_by_headings(text)
        assert "" in sections
        assert "Intro text" in sections[""]

    def test_sections_keyed_by_heading_text(self):
        text = "# Alpha\nAlpha content\n## Beta\nBeta content"
        sections = split_by_headings(text)
        assert "Alpha" in sections
        assert "Beta" in sections
        assert "Alpha content" in sections["Alpha"]
        assert "Beta content" in sections["Beta"]

    def test_duplicate_headings_suffixed(self):
        text = "## Method\nFirst\n## Method\nSecond"
        sections = split_by_headings(text)
        assert "Method" in sections
        assert "Method_2" in sections

    def test_no_headings_all_content_under_empty_key(self):
        text = "Just some plain text."
        sections = split_by_headings(text)
        assert list(sections.keys()) == [""]
        assert "Just some plain text." in sections[""]


# ---------------------------------------------------------------------------
# extract_internal_links
# ---------------------------------------------------------------------------

class TestExtractInternalLinks:
    def test_detects_relative_md_links(self):
        text = "See [Methods](methods.md) and [Also](../other.md)."
        links = extract_internal_links(text)
        assert len(links) == 2
        assert {"display": "Methods", "target": "methods.md"} in links

    def test_ignores_external_links(self):
        text = "[Web](https://example.com) and [Methods](methods.md)"
        links = extract_internal_links(text)
        assert len(links) == 1
        assert links[0]["target"] == "methods.md"

    def test_ignores_image_links(self):
        text = "![Alt](image.md) [Note](note.md)"
        links = extract_internal_links(text)
        assert len(links) == 1
        assert links[0]["target"] == "note.md"

    def test_deduplicates_identical_links(self):
        text = "[Note](note.md) [Note](note.md)"
        links = extract_internal_links(text)
        assert len(links) == 1

    def test_no_links_returns_empty(self):
        assert extract_internal_links("No links here.") == []


# ---------------------------------------------------------------------------
# extract_inline_tags
# ---------------------------------------------------------------------------

class TestExtractInlineTags:
    def test_finds_inline_tags(self):
        text = "Some text with #python and #research tags."
        tags = extract_inline_tags(text)
        assert "python" in tags
        assert "research" in tags

    def test_ignores_tags_on_heading_lines(self):
        text = "## Heading #not-a-tag\nBody #real-tag"
        tags = extract_inline_tags(text)
        assert "not-a-tag" not in tags
        assert "real-tag" in tags

    def test_deduplicates_tags(self):
        text = "#python code, more #python usage"
        tags = extract_inline_tags(text)
        assert tags.count("python") == 1

    def test_no_tags_returns_empty(self):
        assert extract_inline_tags("No tags here.") == []

    def test_tag_must_start_with_letter(self):
        text = "#123bad #good-tag"
        tags = extract_inline_tags(text)
        assert "123bad" not in tags
        assert "good-tag" in tags


# ---------------------------------------------------------------------------
# score_section_relevance
# ---------------------------------------------------------------------------

class TestScoreSectionRelevance:
    def test_returns_count_of_matching_tokens(self):
        score = score_section_relevance("machine learning models", "machine learning")
        assert score == 2

    def test_case_insensitive(self):
        score = score_section_relevance("Python is great", "python")
        assert score == 1

    def test_zero_score_when_no_match(self):
        assert score_section_relevance("dogs and cats", "quantum physics") == 0

    def test_zero_when_empty_query(self):
        assert score_section_relevance("some text", "") == 0

    def test_zero_when_empty_section(self):
        assert score_section_relevance("", "query") == 0
