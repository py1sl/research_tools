import pytest

from pdf_data_extract import reference_extraction


class FakePage:
    def __init__(self, text):
        self.text = text

    def get_text(self, kind="text"):
        return self.text


class FakeDocument:
    def __init__(self, pages):
        self._pages = [FakePage(text) for text in pages]

    def __iter__(self):
        return iter(self._pages)

    def close(self):
        pass


class FakePyMuPDFModule:
    FileNotFoundError = RuntimeError

    def __init__(self, pages):
        self._pages = pages

    def open(self, path):
        return FakeDocument(self._pages)


def _fake_document(monkeypatch, pages):
    monkeypatch.setattr(
        reference_extraction, "pymupdf", FakePyMuPDFModule(pages)
    )


def test_extracts_numbered_references_and_dois(tmp_path, monkeypatch):
    pdf_file = tmp_path / "paper.pdf"
    pdf_file.write_bytes(b"pdf")
    _fake_document(
        monkeypatch,
        [
            "Introduction\nCitations appear here.\nREFERENCES\n"
            "[1] A. Author. A paper title. Journal, 2020.\n"
            "https://doi.org/10.1234/example.\n"
            "[2] B. Author. Another paper. 2021."
        ],
    )

    references = reference_extraction.extract_references(str(pdf_file))

    assert references == [
        {
            "text": "A. Author. A paper title. Journal, 2020. "
            "https://doi.org/10.1234/example.",
            "doi": "10.1234/example",
        },
        {
            "text": "B. Author. Another paper. 2021.",
            "doi": None,
        },
    ]


def test_extracts_blank_line_separated_bibliography_and_stops_at_next_section(
    tmp_path, monkeypatch
):
    pdf_file = tmp_path / "paper.pdf"
    pdf_file.write_bytes(b"pdf")
    _fake_document(
        monkeypatch,
        [
            "Bibliography\nA. Author, First title, 2020.\n\n"
            "B. Author, Second title, 2021.\nAppendix\n"
            "This is not a reference."
        ],
    )

    assert reference_extraction.extract_references(str(pdf_file)) == [
        {"text": "A. Author, First title, 2020.", "doi": None},
        {"text": "B. Author, Second title, 2021.", "doi": None},
    ]


def test_returns_empty_list_when_no_reference_section(tmp_path, monkeypatch):
    pdf_file = tmp_path / "paper.pdf"
    pdf_file.write_bytes(b"pdf")
    _fake_document(monkeypatch, ["Title\nBody text only."])

    assert reference_extraction.extract_references(str(pdf_file)) == []


def test_raises_for_missing_pdf(tmp_path):
    with pytest.raises(FileNotFoundError):
        reference_extraction.extract_references(str(tmp_path / "missing.pdf"))
