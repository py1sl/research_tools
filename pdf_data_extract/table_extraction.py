"""Extraction of tabular data from a PDF into ``pandas`` DataFrames.

This module is concerned with the table *contents* (rows/columns of cell
values), as opposed to ``structure_extraction``, which only extracts table
*captions* (e.g. "Table 1: ..."). Tables are located and parsed using
PyMuPDF's (``pymupdf``) built-in table-detection, which analyses the page's
vector graphics (ruling lines) and text alignment to reconstruct rows and
columns, rather than the plain-text regex heuristics used elsewhere in this
package.
"""
import logging

import pymupdf

logger = logging.getLogger(__name__)


def _get_document(pdf_path):
    try:
        return pymupdf.open(pdf_path)
    except pymupdf.FileNotFoundError as error:
        raise FileNotFoundError(str(error)) from error


def _find_page_tables(page):
    """Return the ``pymupdf`` ``Table`` objects detected on a page."""
    return page.find_tables().tables


def extract_tables(pdf_path):
    """Extract every detected table from a PDF as a ``pandas`` DataFrame.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        list: A list of dictionaries, one per detected table, in the order
        they appear in the document. Each dictionary contains:

        - ``page``: the 1-indexed page number the table was found on.
        - ``index``: the 0-indexed position of the table within its page
          (``0`` for the first table on a page, ``1`` for the second, etc.).
        - ``bbox``: a ``(x0, y0, x1, y1)`` tuple with the table's bounding
          box on the page, in PDF points.
        - ``dataframe``: a :class:`pandas.DataFrame` with the table's rows
          and columns. The first row is used as the column header when
          PyMuPDF detects one, otherwise columns are labelled positionally.

        PDFs with no detectable tables return an empty list.
    """
    document = _get_document(pdf_path)
    try:
        return _tables_from_document(document)
    finally:
        document.close()


def _tables_from_document(document):
    """Like :func:`extract_tables`, but for an already-open PyMuPDF
    document."""
    tables = []
    for page_number, page in enumerate(document, start=1):
        for index, table in enumerate(_find_page_tables(page)):
            tables.append(
                {
                    "page": page_number,
                    "index": index,
                    "bbox": tuple(table.bbox),
                    "dataframe": table.to_pandas(),
                }
            )
    return tables


def extract_tables_with_captions(pdf_path):
    """Extract tables as DataFrames and pair them with their captions.

    Tables are matched to the captions extracted by
    :func:`pdf_data_extract.structure_extraction.extract_table_captions` in
    document order. This is a best-effort pairing: if the number of detected
    tables doesn't match the number of detected captions (for example a
    caption-less table, or a table split across a page break that is
    detected twice), pairing is considered ambiguous, a warning is logged,
    and every table is returned with ``number``/``caption`` set to ``None``
    and ``matched`` set to ``False``, rather than risking an incorrect
    pairing.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        list: A list of dictionaries, one per detected table, in the order
        they appear in the document. Each dictionary contains the same
        ``page``, ``index``, ``bbox``, and ``dataframe`` keys as
        :func:`extract_tables`, plus:

        - ``number``/``caption``: the paired caption's number/text, or
          ``None`` when no caption could be paired with the table.
        - ``matched``: ``True`` when the number of detected tables and
          captions matched and pairing was performed by document order,
          ``False`` when the counts differed and no pairing could be made.
    """
    # Imported lazily to avoid a hard import-time dependency between the two
    # extraction modules for callers that only need one of them.
    from .structure_extraction import _table_captions_from_document

    document = _get_document(pdf_path)
    try:
        # Both passes share the single open document, rather than each
        # reopening and reparsing the PDF from scratch.
        tables = _tables_from_document(document)
        captions = _table_captions_from_document(document)
    finally:
        document.close()

    matched = len(tables) == len(captions)
    if not matched and tables:
        logger.warning(
            "Detected %d table(s) but %d table caption(s) in %s; "
            "leaving captions unmatched to avoid an incorrect pairing.",
            len(tables),
            len(captions),
            pdf_path,
        )

    for index, table in enumerate(tables):
        caption = captions[index] if matched else None
        table["number"] = caption["number"] if caption else None
        table["caption"] = caption["caption"] if caption else None
        table["matched"] = matched

    return tables
