import pytest

from pdf_data_extract import reference_extraction


class FakePage:
    def __init__(self, text):
        self.text = text

    def get_text(self, kind="text", **kwargs):
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
            "arxiv_id": None,
            "url": None,
            "year": 2020,
            "index": 1,
        },
        {
            "text": "B. Author. Another paper. 2021.",
            "doi": None,
            "arxiv_id": None,
            "url": None,
            "year": 2021,
            "index": 2,
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

    refs = reference_extraction.extract_references(str(pdf_file))
    assert [(r["text"], r["year"], r["index"]) for r in refs] == [
        ("A. Author, First title, 2020.", 2020, 1),
        ("B. Author, Second title, 2021.", 2021, 2),
    ]


def test_returns_empty_list_when_no_reference_section(tmp_path, monkeypatch):
    pdf_file = tmp_path / "paper.pdf"
    pdf_file.write_bytes(b"pdf")
    _fake_document(monkeypatch, ["Title\nBody text only."])

    assert reference_extraction.extract_references(str(pdf_file)) == []


def test_raises_for_missing_pdf(tmp_path):
    with pytest.raises(FileNotFoundError):
        reference_extraction.extract_references(str(tmp_path / "missing.pdf"))


def test_uses_last_heading_and_parses_ids_and_hyphenation(tmp_path, monkeypatch):
    pdf_file = tmp_path / "paper.pdf"
    pdf_file.write_bytes(b"pdf")
    _fake_document(
        monkeypatch,
        [
            "Contents\nReferences\n12\nIntro",
            "References\n[1] A. Author, Phys. Rev. Lett. 99, 123 (2007), arXiv:0705.1234.\n"
            "[2] B. Author, Some inter-\nesting result, hep-ph/0123456; "
            "doi:10.1103/PhysRevD.1.2\n3 more. https://example.org/x.",
        ],
    )

    refs = reference_extraction.extract_references(str(pdf_file))

    assert len(refs) == 2
    assert refs[0]["arxiv_id"] == "0705.1234"
    assert refs[0]["year"] == 2007
    assert "interesting result" in refs[1]["text"]
    assert refs[1]["url"] == "https://example.org/x"


def test_splits_unnumbered_author_year_entries(tmp_path, monkeypatch):
    pdf_file = tmp_path / "paper.pdf"
    pdf_file.write_bytes(b"pdf")
    _fake_document(
        monkeypatch,
        [
            "References\nSmith, J., Jones, K. (2019). First title.\n"
            "Journal of Things, 4, 1-10.\n"
            "Brown, L. (2020). Second title. Nature, 5, 2."
        ],
    )

    refs = reference_extraction.extract_references(str(pdf_file))

    assert [r["year"] for r in refs] == [2019, 2020]
    assert refs[0]["text"].endswith("1-10.")


def test_strips_running_headers_and_page_numbers(tmp_path, monkeypatch):
    pdf_file = tmp_path / "paper.pdf"
    pdf_file.write_bytes(b"pdf")
    pages = [
        f"Journal X\nbody\n{i}" for i in range(1, 3)
    ] + [
        "Journal X\nReferences\n[1] A. Author. T. 2020.\n3",
        "Journal X\n[2] B. Author. U. 2021.\n4",
    ]
    _fake_document(monkeypatch, pages)

    refs = reference_extraction.extract_references(str(pdf_file))

    assert [r["text"] for r in refs] == ["A. Author. T. 2020.", "B. Author. U. 2021."]
