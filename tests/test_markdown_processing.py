"""Unit tests for the public API in markdown_notes.markdown_processing."""
import os

import pytest

from markdown_notes import get_note_graph, read_note, search_notes


# ---------------------------------------------------------------------------
# read_note
# ---------------------------------------------------------------------------

class TestReadNote:
    def test_raises_for_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_note(str(tmp_path / "missing.md"))

    def test_raises_for_non_md_extension(self, tmp_path):
        f = tmp_path / "note.txt"
        f.write_text("content", encoding="utf-8")
        with pytest.raises(ValueError):
            read_note(str(f))

    def test_returns_expected_keys(self, note_file):
        result = read_note(note_file)
        expected_keys = {
            "title", "tags", "created", "modified", "summary",
            "section_headings", "sections", "internal_links",
            "external_links", "code_blocks", "tables", "raw",
        }
        assert expected_keys <= result.keys()

    def test_title_from_h1(self, note_file):
        result = read_note(note_file)
        assert result["title"] == "My Note"

    def test_frontmatter_tags_included(self, note_file):
        result = read_note(note_file)
        assert "python" in result["tags"]
        assert "research" in result["tags"]

    def test_inline_tags_included(self, note_file):
        result = read_note(note_file)
        assert "inline-tag" in result["tags"]

    def test_created_and_modified_dates(self, note_file):
        result = read_note(note_file)
        assert result["created"] == "2024-01-15"
        assert result["modified"] == "2024-06-01"

    def test_summary_is_first_paragraph(self, note_file):
        # extract_summary returns the first plain-text paragraph;
        # heading text counts as a paragraph after '#' markers are stripped
        result = read_note(note_file)
        assert result["summary"] == "My Note"

    def test_section_headings_ordered(self, note_file):
        result = read_note(note_file)
        assert result["section_headings"] == ["My Note", "Background", "Methods"]

    def test_sections_keyed_by_heading(self, note_file):
        result = read_note(note_file)
        assert "Background" in result["sections"]
        assert "Methods" in result["sections"]

    def test_query_filters_sections(self, note_file):
        result = read_note(note_file, query="background")
        assert "Background" in result["sections"]
        # "Methods" section should not be returned (no match), unless fallback applies
        # The fallback kicks in only if NOTHING matches — here Background does match
        assert "Methods" not in result["sections"]

    def test_query_fallback_all_sections_when_no_match(self, note_file):
        result = read_note(note_file, query="zzznomatch")
        # Fallback: all sections returned
        assert "Background" in result["sections"]
        assert "Methods" in result["sections"]

    def test_internal_links_extracted(self, note_file):
        result = read_note(note_file)
        targets = [lnk["target"] for lnk in result["internal_links"]]
        assert "other_note.md" in targets

    def test_external_links_extracted(self, note_file):
        result = read_note(note_file)
        assert any("example.com" in url for url in result["external_links"])

    def test_code_blocks_extracted(self, note_file):
        result = read_note(note_file)
        assert len(result["code_blocks"]) == 1
        assert result["code_blocks"][0]["language"] == "python"

    def test_tables_extracted(self, note_file):
        result = read_note(note_file)
        assert len(result["tables"]) == 1
        assert result["tables"][0][0] == ["Header A", "Header B"]

    def test_raw_contains_full_text(self, note_file):
        result = read_note(note_file)
        with open(note_file, encoding="utf-8") as fh:
            assert result["raw"] == fh.read()

    def test_title_falls_back_to_frontmatter_title(self, tmp_path):
        note = tmp_path / "noheading.md"
        note.write_text("---\ntitle: FM Title\n---\nJust body text.", encoding="utf-8")
        result = read_note(str(note))
        assert result["title"] == "FM Title"

    def test_title_falls_back_to_filename_stem(self, tmp_path):
        note = tmp_path / "my_file.md"
        note.write_text("Just body text with no heading.", encoding="utf-8")
        result = read_note(str(note))
        assert result["title"] == "my_file"


# ---------------------------------------------------------------------------
# search_notes (public API delegation)
# ---------------------------------------------------------------------------

class TestSearchNotesPublicAPI:
    def test_delegates_to_search_module(self, note_dir):
        results = search_notes(str(note_dir), query="background")
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_raises_for_nonexistent_folder(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            search_notes(str(tmp_path / "missing"))


# ---------------------------------------------------------------------------
# get_note_graph (public API delegation)
# ---------------------------------------------------------------------------

class TestGetNoteGraphPublicAPI:
    def test_returns_adjacency_dict(self, note_dir):
        graph = get_note_graph(str(note_dir))
        assert isinstance(graph, dict)
        assert "My Note" in graph

    def test_raises_for_nonexistent_folder(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            get_note_graph(str(tmp_path / "missing"))
