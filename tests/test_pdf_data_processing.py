"""Unit tests for the public API in pdf_data_extract.pdf_data_processing."""
from pdf_data_extract import pdf_extract_data, process_papers_folder, process_pdf_data
from pdf_data_extract import pdf_data_processing

import pytest


class TestPdfExtractData:
    def test_raises_for_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            pdf_extract_data(str(tmp_path / "missing.pdf"))

    def test_returns_expected_placeholder_keys(self, tmp_path):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n")

        result = pdf_extract_data(str(pdf_file))

        assert result == {
            "authors": None,
            "title": None,
            "journal": None,
            "date": None,
            "doi": None,
            "keywords": None,
            "section_headings": None,
            "num_tables": None,
            "num_figures": None,
            "num_equations": None,
        }


class TestProcessPdfData:
    def test_raises_for_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            process_pdf_data(str(tmp_path / "missing.pdf"))

    def test_delegates_to_metadata_and_reference_extractors(self, tmp_path, monkeypatch):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n")
        metadata = {"Title": "Example"}
        calls = []

        def fake_extract_metadata(path):
            calls.append(("metadata", path))
            return metadata

        def fake_extract_references(path):
            calls.append(("references", path))
            return ["ref-1"]

        monkeypatch.setattr(pdf_data_processing.extract_meta, "extract_metadata", fake_extract_metadata)
        monkeypatch.setattr(
            pdf_data_processing.reference_extraction,
            "extract_references",
            fake_extract_references,
        )

        result = process_pdf_data(str(pdf_file))

        assert result == metadata
        assert calls == [
            ("metadata", str(pdf_file)),
            ("references", str(pdf_file)),
        ]


class TestProcessPapersFolder:
    def test_raises_for_missing_folder(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            process_papers_folder(str(tmp_path / "missing"))

    def test_processes_only_pdf_files(self, tmp_path, monkeypatch):
        pdf_a = tmp_path / "a.pdf"
        pdf_b = tmp_path / "b.pdf"
        txt_file = tmp_path / "notes.txt"
        pdf_a.write_bytes(b"%PDF-1.4\n")
        pdf_b.write_bytes(b"%PDF-1.4\n")
        txt_file.write_text("ignore me", encoding="utf-8")

        def fake_process_pdf_data(path):
            return {"path": path}

        monkeypatch.setattr(pdf_data_processing, "process_pdf_data", fake_process_pdf_data)

        results = process_papers_folder(str(tmp_path))

        assert {result["path"] for result in results} == {str(pdf_a), str(pdf_b)}

    def test_returns_empty_list_when_folder_has_no_pdfs(self, tmp_path):
        (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")

        assert process_papers_folder(str(tmp_path)) == []
