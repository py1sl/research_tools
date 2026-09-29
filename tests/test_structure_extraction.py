import pytest

from pdf_data_extract import structure_extraction


class FakePage:
    def __init__(self, text):
        self.text = text

    def extract_text(self):
        return self.text


class FakeReader:
    def __init__(self, pages):
        self.pages = [FakePage(text) for text in pages]


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


def _fake_reader(monkeypatch, text):
    monkeypatch.setattr(
        structure_extraction,
        "PdfReader",
        lambda path: FakeReader([text]),
    )


class TestExtractSectionHeadings:
    def test_extracts_numbered_and_named_headings(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_reader(monkeypatch, SAMPLE_TEXT)

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
        _fake_reader(
            monkeypatch,
            "1. Introduction\n"
            "1. This is a numbered sentence, not a section heading.\n"
            "2. This numbered paragraph contains enough words to be ordinary prose "
            "rather than a concise section title.\n",
        )

        assert structure_extraction.extract_section_headings(str(pdf_file)) == [
            {"number": "1", "heading": "Introduction"}
        ]

    def test_raises_for_missing_pdf(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            structure_extraction.extract_section_headings(str(tmp_path / "missing.pdf"))


class TestExtractFigureCaptions:
    def test_extracts_multiline_figure_captions(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_reader(monkeypatch, SAMPLE_TEXT)

        captions = structure_extraction.extract_figure_captions(str(pdf_file))

        assert captions == [
            {"number": "1", "caption": "An example diagram showing the architecture."},
            {"number": "2", "caption": "Another figure caption"},
        ]

    def test_stops_caption_at_sentence_end(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_reader(
            monkeypatch,
            "Figure 1: Caption text on the first line\n"
            "and a wrapped continuation.\n"
            "This is the following body paragraph and should not be included.\n",
        )

        assert structure_extraction.extract_figure_captions(str(pdf_file)) == [
            {"number": "1", "caption": "Caption text on the first line and a wrapped continuation."}
        ]

    def test_raises_for_missing_pdf(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            structure_extraction.extract_figure_captions(str(tmp_path / "missing.pdf"))


class TestExtractTableCaptions:
    def test_extracts_table_captions(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_reader(monkeypatch, SAMPLE_TEXT)

        captions = structure_extraction.extract_table_captions(str(pdf_file))

        assert captions == [
            {"number": "1", "caption": "Summary of results for the experiments."},
        ]

    def test_raises_for_missing_pdf(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            structure_extraction.extract_table_captions(str(tmp_path / "missing.pdf"))


class TestExtractDocumentStructure:
    def test_returns_all_structure_keys(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"pdf")
        _fake_reader(monkeypatch, SAMPLE_TEXT)

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
        _fake_reader(monkeypatch, "Just some plain body text with no structure.")

        structure = structure_extraction.extract_document_structure(str(pdf_file))

        assert structure == {
            "section_headings": [],
            "figure_captions": [],
            "table_captions": [],
        }
