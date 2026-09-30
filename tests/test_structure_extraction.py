import pytest

from pdf_data_extract import structure_extraction

DEFAULT_SIZE = 10.0


class FakePage:
    def __init__(self, lines):
        # lines: list of (text, size, bold) tuples
        self._lines = lines

    def get_text(self, kind="dict"):
        blocks = []
        for text, size, bold in self._lines:
            flags = 16 if bold else 0
            blocks.append(
                {
                    "lines": [
                        {
                            "spans": [
                                {
                                    "text": text,
                                    "size": size,
                                    "flags": flags,
                                    "font": "Bold" if bold else "Regular",
                                }
                            ]
                        }
                    ]
                }
            )
        return {"blocks": blocks}


class FakeDocument:
    def __init__(self, pages):
        self._pages = pages

    def __iter__(self):
        return iter(self._pages)

    def close(self):
        pass


class FakePyMuPDFModule:
    """Stand-in for the ``pymupdf`` module used by structure_extraction."""

    FileNotFoundError = RuntimeError

    def __init__(self, pages):
        self._pages = pages

    def open(self, path):
        return FakeDocument(self._pages)


def _page_from_text(text, size=DEFAULT_SIZE, bold=False):
    return FakePage([(line, size, bold) for line in text.split("\n")])


def _fake_document(monkeypatch, pages_text, *, size=DEFAULT_SIZE, bold=False):
    """Patch ``pymupdf`` so each string in ``pages_text`` becomes a page,
    with every line rendered at a uniform font size/weight (so the new
    layout-based heading detection stays inert and only the regex
    heuristics are exercised, matching the previous plain-text behaviour)."""
    pages = [_page_from_text(text, size=size, bold=bold) for text in pages_text]
    monkeypatch.setattr(structure_extraction, "pymupdf", FakePyMuPDFModule(pages))


SAMPLE_TEXT = (
    "A Paper Title\n"
    "Abstract\n"
    "This paper studies things.\n"
    "1 Introduction\n"
    "This is the introduction text.\n"
    "2 Related Work\n"
    "Prior work is discussed here.\n"
    "Figure 1: An example diagram\n"
    "showing the architecture.\n"
    "Table 1: Summary of results\n"
    "for the experiments.\n"
    "2.1 Background\n"
    "More detail on background.\n"
    "Fig. 2 - Another figure caption\n"
    "3 Conclusion\n"
    "We conclude the paper.\n"
    "References\n"
    "[1] A. Author. A title. 2020."
)


class TestBodyFontSize:
    def test_weights_by_total_character_count_not_line_count(self):
        """The modal body size is weighted by character count, so a
        majority of *characters* at one size should win even if a
        different size has more (but shorter) lines -- e.g. many short
        repeated footer/page-number lines shouldn't outweigh the actual
        body paragraphs just because there are more of them."""
        lines = (
            # Two long paragraphs at size 12: ~95 characters each.
            [
                {"text": "x" * 95, "size": 12.0, "bold": False}
                for _ in range(2)
            ]
            # Five short lines at size 9: 3 characters each (15 total).
            + [
                {"text": "abc", "size": 9.0, "bold": False}
                for _ in range(5)
            ]
        )

        assert structure_extraction._body_font_size(lines) == 12.0

    def test_returns_zero_for_no_lines(self):
        assert structure_extraction._body_font_size([]) == 0


class TestExtractSectionHeadings:
    def test_extracts_numbered_and_named_headings(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_document(monkeypatch, [SAMPLE_TEXT])

        headings = structure_extraction.extract_section_headings(str(pdf_file))

        assert headings == [
            {"number": None, "heading": "Abstract"},
            {"number": "1", "heading": "Introduction"},
            {"number": "2", "heading": "Related Work"},
            {"number": "2.1", "heading": "Background"},
            {"number": "3", "heading": "Conclusion"},
            {"number": None, "heading": "References"},
        ]

    def test_ignores_numbered_prose(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_document(
            monkeypatch,
            [
                "1. Introduction\n"
                "1. This is a numbered sentence, not a section heading.\n"
                "2. This numbered paragraph contains enough words to be ordinary prose "
                "rather than a concise section title.\n"
            ],
        )

        assert structure_extraction.extract_section_headings(str(pdf_file)) == [
            {"number": "1", "heading": "Introduction"}
        ]

    def test_raises_for_missing_pdf(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            structure_extraction.extract_section_headings(str(tmp_path / "missing.pdf"))

    def test_finds_unlisted_heading_by_font_size(self, tmp_path, monkeypatch):
        """A section name outside the hard-coded whitelist (e.g. a
        non-standard or non-English name) is still detected when it is
        visually distinguished by a larger font size."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        page = FakePage(
            [
                ("Zusammenfassung", 16.0, False),
                ("Body text at the normal document font size.", 10.0, False),
                ("Body text at the normal document font size.", 10.0, False),
            ]
        )
        monkeypatch.setattr(
            structure_extraction, "pymupdf", FakePyMuPDFModule([page])
        )

        assert structure_extraction.extract_section_headings(str(pdf_file)) == [
            {"number": None, "heading": "Zusammenfassung"}
        ]

    def test_finds_unlisted_heading_by_bold_text(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        page = FakePage(
            [
                ("Ethical Statement", 10.0, True),
                ("Body text at the normal document font size.", 10.0, False),
                ("Body text at the normal document font size.", 10.0, False),
            ]
        )
        monkeypatch.setattr(
            structure_extraction, "pymupdf", FakePyMuPDFModule([page])
        )

        assert structure_extraction.extract_section_headings(str(pdf_file)) == [
            {"number": None, "heading": "Ethical Statement"}
        ]


class TestExtractFigureCaptions:
    def test_extracts_multiline_figure_captions(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_document(monkeypatch, [SAMPLE_TEXT])

        captions = structure_extraction.extract_figure_captions(str(pdf_file))

        assert captions == [
            {"number": "1", "caption": "An example diagram showing the architecture."},
            {"number": "2", "caption": "Another figure caption"},
        ]

    def test_stops_caption_at_sentence_end(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_document(
            monkeypatch,
            [
                "Figure 1: Caption text on the first line\n"
                "and a wrapped continuation.\n"
                "This is the following body paragraph and should not be included.\n"
            ],
        )

        assert structure_extraction.extract_figure_captions(str(pdf_file)) == [
            {"number": "1", "caption": "Caption text on the first line and a wrapped continuation."}
        ]

    def test_does_not_continue_caption_across_pages(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_document(
            monkeypatch,
            ["Figure 1: A caption without terminal punctuation", "Unrelated page text."],
        )

        assert structure_extraction.extract_figure_captions(str(pdf_file)) == [
            {"number": "1", "caption": "A caption without terminal punctuation"}
        ]

    def test_stops_caption_before_numbered_section_heading(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_document(
            monkeypatch,
            [
                "Figure 1: Caption without a final period\n"
                "2.3 A New Section\n"
                "Section text."
            ],
        )

        assert structure_extraction.extract_figure_captions(str(pdf_file)) == [
            {"number": "1", "caption": "Caption without a final period"}
        ]

    def test_retries_with_stricter_boundaries_when_numbers_skip(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_document(
            monkeypatch,
            [
                "Figure 1: Caption without a final period\n"
                "This body paragraph should not be included.\n"
                "Figure 3: The next figure caption.\n"
            ],
        )

        assert structure_extraction.extract_figure_captions(str(pdf_file)) == [
            {"number": "1", "caption": "Caption without a final period"},
            {"number": "3", "caption": "The next figure caption."},
        ]

    def test_stops_caption_before_unlisted_bold_heading(self, tmp_path, monkeypatch):
        """A caption that doesn't end in a full stop should still be cut
        off by a following visually-distinguished heading, even if that
        heading isn't in the regex whitelist."""
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        page = FakePage(
            [
                ("Figure 1: A caption without terminal punctuation", 10.0, False),
                ("Ethical Statement", 10.0, True),
                ("Some statement text.", 10.0, False),
            ]
        )
        monkeypatch.setattr(
            structure_extraction, "pymupdf", FakePyMuPDFModule([page])
        )

        assert structure_extraction.extract_figure_captions(str(pdf_file)) == [
            {"number": "1", "caption": "A caption without terminal punctuation"}
        ]

    def test_raises_for_missing_pdf(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            structure_extraction.extract_figure_captions(str(tmp_path / "missing.pdf"))


class TestExtractTableCaptions:
    def test_extracts_table_captions(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_document(monkeypatch, [SAMPLE_TEXT])

        captions = structure_extraction.extract_table_captions(str(pdf_file))

        assert captions == [
            {"number": "1", "caption": "Summary of results for the experiments."},
        ]

    def test_retries_with_stricter_boundaries_when_numbers_skip(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_document(
            monkeypatch,
            [
                "Table 1: Caption without a final period\n"
                "This body paragraph should not be included.\n"
                "Table 3: The next table caption.\n"
            ],
        )

        assert structure_extraction.extract_table_captions(str(pdf_file)) == [
            {"number": "1", "caption": "Caption without a final period"},
            {"number": "3", "caption": "The next table caption."},
        ]

    def test_raises_for_missing_pdf(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            structure_extraction.extract_table_captions(str(tmp_path / "missing.pdf"))


class TestExtractDocumentStructure:
    def test_returns_all_structure_keys(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_document(monkeypatch, [SAMPLE_TEXT])

        structure = structure_extraction.extract_document_structure(str(pdf_file))

        assert set(structure.keys()) == {
            "section_headings",
            "figure_captions",
            "table_captions",
        }
        assert structure["section_headings"] == structure_extraction.extract_section_headings(
            str(pdf_file)
        )
        assert structure["figure_captions"] == structure_extraction.extract_figure_captions(
            str(pdf_file)
        )
        assert structure["table_captions"] == structure_extraction.extract_table_captions(
            str(pdf_file)
        )

    def test_returns_empty_lists_when_nothing_found(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_document(monkeypatch, ["Just some plain body text with no structure."])

        structure = structure_extraction.extract_document_structure(str(pdf_file))

        assert structure == {
            "section_headings": [],
            "figure_captions": [],
            "table_captions": [],
        }
