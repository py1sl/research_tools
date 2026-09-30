import pandas as pd
import pymupdf
import pytest

from pdf_data_extract import structure_extraction, table_extraction


def _draw_grid_table(page, rows, *, origin=(72, 100), col_width=100, row_height=20):
    """Draw a simple ruled table (text + grid lines) onto a PyMuPDF page so
    that ``page.find_tables()`` can detect it, mirroring how a real PDF
    table is rendered."""
    x0, y0 = origin
    for row_index, row in enumerate(rows):
        for col_index, value in enumerate(row):
            page.insert_text(
                (x0 + col_index * col_width + 5, y0 + row_index * row_height + 15),
                str(value),
                fontsize=10,
            )

    for row_index in range(len(rows) + 1):
        y = y0 + row_index * row_height
        page.draw_line((x0, y), (x0 + col_width * len(rows[0]), y))
    for col_index in range(len(rows[0]) + 1):
        x = x0 + col_index * col_width
        page.draw_line((x, y0), (x, y0 + row_height * len(rows)))


def _make_pdf_with_tables(path, pages_rows):
    """Create a PDF at ``path`` with one grid table per entry of
    ``pages_rows``; each entry is a list of rows for that page, or an empty
    list for a page with no table."""
    document = pymupdf.open()
    for rows in pages_rows:
        page = document.new_page()
        if rows:
            _draw_grid_table(page, rows)
        else:
            page.insert_text((72, 72), "No table on this page.", fontsize=10)
    document.save(str(path))
    document.close()


TABLE_1 = [
    ["Name", "Score"],
    ["Alice", "95"],
    ["Bob", "88"],
]
TABLE_2 = [
    ["Country", "Capital"],
    ["France", "Paris"],
]


class TestExtractTables:
    def test_extracts_table_as_dataframe(self, tmp_path):
        pdf_file = tmp_path / "paper.pdf"
        _make_pdf_with_tables(pdf_file, [TABLE_1])

        tables = table_extraction.extract_tables(str(pdf_file))

        assert len(tables) == 1
        table = tables[0]
        assert table["page"] == 1
        assert table["index"] == 0
        assert len(table["bbox"]) == 4
        assert isinstance(table["dataframe"], pd.DataFrame)
        assert list(table["dataframe"].columns) == ["Name", "Score"]
        assert table["dataframe"].values.tolist() == [["Alice", "95"], ["Bob", "88"]]

    def test_extracts_multiple_tables_across_pages_in_order(self, tmp_path):
        pdf_file = tmp_path / "paper.pdf"
        _make_pdf_with_tables(pdf_file, [TABLE_1, [], TABLE_2])

        tables = table_extraction.extract_tables(str(pdf_file))

        assert [(t["page"], t["index"]) for t in tables] == [(1, 0), (3, 0)]
        assert list(tables[0]["dataframe"].columns) == ["Name", "Score"]
        assert list(tables[1]["dataframe"].columns) == ["Country", "Capital"]

    def test_returns_empty_list_when_no_tables(self, tmp_path):
        pdf_file = tmp_path / "paper.pdf"
        _make_pdf_with_tables(pdf_file, [[]])

        assert table_extraction.extract_tables(str(pdf_file)) == []

    def test_raises_for_missing_pdf(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            table_extraction.extract_tables(str(tmp_path / "missing.pdf"))


class TestExtractTablesWithCaptions:
    def test_pairs_tables_with_captions_in_order(self, tmp_path):
        pdf_file = tmp_path / "paper.pdf"
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 72), "Table 1: Scores by participant.", fontsize=10)
        _draw_grid_table(page, TABLE_1, origin=(72, 110))
        document.save(str(pdf_file))
        document.close()

        tables = table_extraction.extract_tables_with_captions(str(pdf_file))

        assert len(tables) == 1
        assert tables[0]["matched"] is True
        assert tables[0]["number"] == "1"
        assert tables[0]["caption"] == "Scores by participant."
        assert list(tables[0]["dataframe"].columns) == ["Name", "Score"]

    def test_leaves_number_and_caption_none_when_counts_mismatch(self, tmp_path):
        pdf_file = tmp_path / "paper.pdf"
        # Two tables detected but only one caption in the text layer.
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 72), "Table 1: Only one caption", fontsize=10)
        _draw_grid_table(page, TABLE_1, origin=(72, 110))
        _draw_grid_table(page, TABLE_2, origin=(72, 220))
        document.save(str(pdf_file))
        document.close()

        tables = table_extraction.extract_tables_with_captions(str(pdf_file))

        assert len(tables) == 2
        assert all(
            t["matched"] is False and t["number"] is None and t["caption"] is None
            for t in tables
        )

    def test_raises_for_missing_pdf(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            table_extraction.extract_tables_with_captions(str(tmp_path / "missing.pdf"))
