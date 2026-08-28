"""Unit tests for markdown_notes.search (internal helpers + public functions)."""
import os
import textwrap

import pytest

from markdown_notes.search import _extract_snippet, get_note_graph, search_notes


# ---------------------------------------------------------------------------
# _extract_snippet
# ---------------------------------------------------------------------------

class TestExtractSnippet:
    def test_returns_text_around_query_token(self):
        text = "a " * 50 + "target word" + " b" * 50
        snippet = _extract_snippet(text, "target")
        assert "target" in snippet

    def test_falls_back_to_start_when_no_match(self):
        text = "Hello world, this is a test."
        snippet = _extract_snippet(text, "notfound")
        assert snippet.startswith("Hello")

    def test_no_query_returns_start_of_text(self):
        text = "Start of the text " + "x " * 100
        snippet = _extract_snippet(text, None)
        assert snippet.startswith("Start")

    def test_ellipsis_added_for_mid_text_match(self):
        padding = "word " * 40
        text = padding + "target" + padding
        snippet = _extract_snippet(text, "target", window=10)
        assert snippet.startswith("...")


# ---------------------------------------------------------------------------
# search_notes
# ---------------------------------------------------------------------------

class TestSearchNotes:
    def test_raises_for_missing_folder(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            search_notes(str(tmp_path / "nonexistent"))

    def test_returns_all_notes_when_no_filters(self, note_dir):
        results = search_notes(str(note_dir))
        assert len(results) == 2

    def test_result_has_required_keys(self, note_dir):
        results = search_notes(str(note_dir))
        for r in results:
            assert {"file", "title", "tags", "matching_sections", "snippet"} <= r.keys()

    def test_query_filter_returns_matching_notes(self, note_dir):
        results = search_notes(str(note_dir), query="background")
        files = [os.path.basename(r["file"]) for r in results]
        assert "my_note.md" in files

    def test_query_excludes_non_matching_notes(self, note_dir):
        results = search_notes(str(note_dir), query="zzznomatch")
        assert results == []

    def test_tag_filter_returns_matching_notes(self, note_dir):
        results = search_notes(str(note_dir), tags=["python"])
        files = [os.path.basename(r["file"]) for r in results]
        assert "my_note.md" in files
        assert "other_note.md" not in files

    def test_tag_filter_with_hash_prefix(self, note_dir):
        results = search_notes(str(note_dir), tags=["#python"])
        assert any(os.path.basename(r["file"]) == "my_note.md" for r in results)

    def test_heading_filter_returns_matching_notes(self, note_dir):
        results = search_notes(str(note_dir), heading="Methods")
        files = [os.path.basename(r["file"]) for r in results]
        assert "my_note.md" in files
        assert "other_note.md" not in files

    def test_matching_sections_populated_for_query(self, note_dir):
        results = search_notes(str(note_dir), query="background")
        match = next(r for r in results if os.path.basename(r["file"]) == "my_note.md")
        assert "Background" in match["matching_sections"]

    def test_recurses_into_subdirectories(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.md").write_text("# Deep Note\nContent", encoding="utf-8")
        results = search_notes(str(tmp_path))
        assert any(os.path.basename(r["file"]) == "deep.md" for r in results)


# ---------------------------------------------------------------------------
# get_note_graph
# ---------------------------------------------------------------------------

class TestGetNoteGraph:
    def test_raises_for_missing_folder(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            get_note_graph(str(tmp_path / "nonexistent"))

    def test_returns_dict_keyed_by_title(self, note_dir):
        graph = get_note_graph(str(note_dir))
        assert "My Note" in graph
        assert "Other Note" in graph

    def test_links_are_listed_for_each_note(self, note_dir):
        graph = get_note_graph(str(note_dir))
        assert "other_note.md" in graph["My Note"]
        assert "my_note.md" in graph["Other Note"]

    def test_note_without_links_has_empty_list(self, tmp_path):
        (tmp_path / "solo.md").write_text("# Solo\nNo links.", encoding="utf-8")
        graph = get_note_graph(str(tmp_path))
        assert graph["Solo"] == []

    def test_empty_folder_returns_empty_dict(self, tmp_path):
        assert get_note_graph(str(tmp_path)) == {}
