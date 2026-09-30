"""Extraction of a PDF's document structure: section headings, figure
captions, and table captions.

Text is extracted with PyMuPDF (``pymupdf``) rather than plain string
extraction. PyMuPDF reconstructs text line-by-line from the PDF's layout
(rather than just concatenating characters in content-stream order), which
is noticeably more reliable for multi-column academic layouts, and it
exposes per-line font size/boldness. That extra layout information is used
as a second detection signal alongside the regex heuristics below, so
headings/captions that don't match the hard-coded regex vocabulary (for
example non-standard section names) can still be recognised when they are
visually distinguished (larger and/or bold text relative to the body font).
The regex heuristics remain the primary signal; layout information only
supplements them, so behaviour is unchanged for PDFs/tests without varying
font metadata.
"""
import re
from collections import Counter

import pymupdf

_COMMON_SECTION_NAMES = (
    r"abstract|introduction|background|related work|literature review|"
    r"materials and methods|methods|methodology|experiments?|"
    r"results(?: and discussion)?|discussion|conclusions?|"
    r"acknowledg(?:e)?ments?|references|bibliography|appendix(?:es)?|"
    r"future work|limitations"
)
_NUMBERED_SECTION_HEADING = re.compile(
    r"^\s*(\d+(?:\.\d+)*)[.)]?\s+([A-Za-z][^\n]{0,120}?)\s*$"
)
_CAPTION_SENTENCE_END = re.compile(r'[.!?]["\')\]]?$')
_ABBREVIATIONS = {"dr", "e.g", "eq", "etc", "fig", "i.e", "no", "vs"}
_NAMED_SECTION_HEADING = re.compile(
    rf"^\s*(?:(\d+(?:\.\d+)*)[.)]?\s+)?({_COMMON_SECTION_NAMES})\s*:?\s*$",
    re.IGNORECASE,
)
_FIGURE_CAPTION = re.compile(
    r"^\s*fig(?:ure)?\.?\s*(\d+(?:\.\d+)*)\s*[:.\-]?\s*(.*)$",
    re.IGNORECASE,
)
_TABLE_CAPTION = re.compile(
    r"^\s*table\s*(\d+(?:\.\d+)*)\s*[:.\-]?\s*(.*)$",
    re.IGNORECASE,
)

# PyMuPDF span "flags" is a bitfield; ``pymupdf.TEXT_FONT_BOLD`` (bit 4,
# value 16) marks a bold font. We reference the numeric value directly
# (rather than the ``pymupdf.TEXT_FONT_BOLD`` constant) so this module's
# fake/mocked ``pymupdf`` module in tests doesn't need to replicate it.
_BOLD_FLAG = 1 << 4
# A line's font size must be at least this much larger than the document's
# modal body size to be treated as a heading by font size alone.
_HEADING_SIZE_RATIO = 1.15
# Bold text only counts as a heading signal if it isn't noticeably smaller
# than body text (e.g. bold figure/table caption labels shouldn't count).
_BOLD_HEADING_MIN_RATIO = 0.95


def _span_is_bold(span):
    return bool(span.get("flags", 0) & _BOLD_FLAG) or "bold" in span.get("font", "").lower()


def _page_lines(page):
    """Return a list of ``{"text", "size", "bold"}`` dicts, one per visual
    line on the page, in the order PyMuPDF reconstructs them from the page
    layout."""
    lines = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(span.get("text", "") for span in spans).strip()
            if not text:
                continue
            size = max((span.get("size", 0) for span in spans), default=0)
            bold = any(_span_is_bold(span) for span in spans)
            lines.append({"text": text, "size": size, "bold": bold})
    return lines


def _lines_from_document(document):
    """Return a flat list of line dicts for an already-open PyMuPDF
    document, with a blank separator line between pages so caption/heading
    boundary logic still treats page breaks as breaks."""
    lines = []
    for index, page in enumerate(document):
        if index:
            lines.append({"text": "", "size": 0, "bold": False})
        lines.extend(_page_lines(page))
    return lines


def _get_document_lines(pdf_path):
    """Return a flat list of line dicts for the whole document at
    ``pdf_path``, opening and closing it."""
    try:
        document = pymupdf.open(pdf_path)
    except pymupdf.FileNotFoundError as error:
        raise FileNotFoundError(str(error)) from error

    try:
        return _lines_from_document(document)
    finally:
        document.close()


def _ends_sentence(text):
    text = text.strip()
    if not _CAPTION_SENTENCE_END.search(text):
        return False

    if text.endswith("."):
        final_word = text.rsplit(None, 1)[-1][:-1].lower()
        if final_word in _ABBREVIATIONS:
            return False
    return True


def _looks_like_heading_text(text):
    text = text.strip()
    return bool(
        text
        and len(text.split()) <= 12
        and len(text) <= 100
        and text[0].isupper()
        and not _ends_sentence(text)
    )


def _body_font_size(lines):
    """Return the document's modal font size, weighted by character count,
    as a proxy for the "normal" body-text size."""
    counter = Counter()
    for line in lines:
        if line["text"]:
            counter[round(line["size"], 1)] += len(line["text"])
    return counter.most_common(1)[0][0] if counter else 0


def _is_layout_heading(line, body_size):
    """Whether a line is visually distinguished as a heading, based on font
    size/boldness relative to the document's body text."""
    if body_size <= 0 or not line["text"]:
        return False
    is_larger = line["size"] >= body_size * _HEADING_SIZE_RATIO
    is_bold = line["bold"] and line["size"] >= body_size * _BOLD_HEADING_MIN_RATIO
    return (is_larger or is_bold) and _looks_like_heading_text(line["text"])


def _is_heading_line(line, body_size):
    text = line["text"]
    numbered_match = _NUMBERED_SECTION_HEADING.match(text)
    is_figure_or_table = bool(_FIGURE_CAPTION.match(text) or _TABLE_CAPTION.match(text))
    return bool(
        _NAMED_SECTION_HEADING.match(text)
        or is_figure_or_table
        or (
            numbered_match
            and _looks_like_heading_text(numbered_match.group(2))
            and not is_figure_or_table
        )
        or (not is_figure_or_table and _is_layout_heading(line, body_size))
    )


def _extract_captions(lines, pattern, number_key, text_key, body_size, strict=False):
    captions = []
    current = None

    def save_current():
        if current is not None:
            text = " ".join(" ".join(current["parts"]).split())
            captions.append({number_key: current["number"], text_key: text})

    for line in lines:
        text = line["text"]
        match = pattern.match(text)
        if match:
            save_current()
            current = {"number": match.group(1), "parts": [match.group(2).strip()]}
            if _ends_sentence(match.group(2)):
                save_current()
                current = None
            continue

        if current is not None:
            if not text or _is_heading_line(line, body_size):
                save_current()
                current = None
            elif strict and current["parts"] and text[0].isupper():
                save_current()
                current = None
            else:
                current["parts"].append(text)
                if _ends_sentence(text):
                    save_current()
                    current = None

    save_current()
    return captions


def _numbers_are_sequential(captions, number_key):
    numbers = [caption[number_key].split(".") for caption in captions]
    for previous, current in zip(numbers, numbers[1:]):
        if len(previous) == len(current) and previous[:-1] == current[:-1]:
            if int(current[-1]) == int(previous[-1]) + 1:
                continue
        if (
            len(previous) == len(current)
            and int(current[0]) == int(previous[0]) + 1
            and all(part == "1" for part in current[1:])
        ):
            continue
        return False
    return True


def _extract_validated_captions(lines, pattern, number_key, text_key, body_size):
    captions = _extract_captions(lines, pattern, number_key, text_key, body_size)
    if _numbers_are_sequential(captions, number_key):
        return captions
    return _extract_captions(lines, pattern, number_key, text_key, body_size, strict=True)


def _section_headings_from_lines(lines, body_size):
    headings = []
    seen_layout_headings = set()

    def add(number, heading_text):
        heading_text = heading_text.strip()
        if number is None:
            # Layout-fallback headings (e.g. a running title/footer
            # repeated on every page) are deduplicated by text alone,
            # since they have no number to disambiguate them. Numbered or
            # named headings are never deduplicated this way, so distinct
            # sections that happen to share a title (e.g. "2.1 Overview"
            # and "3.1 Overview") are both kept.
            key = heading_text.lower()
            if key in seen_layout_headings:
                return
            seen_layout_headings.add(key)
        headings.append({"number": number, "heading": heading_text})

    for line in lines:
        text = line["text"]
        if not text:
            continue

        named_match = _NAMED_SECTION_HEADING.match(text)
        if named_match:
            add(named_match.group(1), named_match.group(2))
            continue

        numbered_match = _NUMBERED_SECTION_HEADING.match(text)
        is_figure_or_table = bool(_FIGURE_CAPTION.match(text) or _TABLE_CAPTION.match(text))
        if (
            numbered_match
            and _looks_like_heading_text(numbered_match.group(2))
            and not is_figure_or_table
        ):
            add(numbered_match.group(1), numbered_match.group(2))
            continue

        # Layout fallback: catches headings that don't match the known
        # regex vocabulary (e.g. an unconventional or non-English section
        # name) but are visually distinguished from body text.
        if not is_figure_or_table and _is_layout_heading(line, body_size):
            add(None, text.rstrip(":"))

    return headings


def extract_section_headings(pdf_path):
    """Extract the section headings from a PDF.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        list: A list of dictionaries, each containing the section ``number``
        (``None`` when the heading is not numbered) and the ``heading`` text,
        in the order they appear in the document.
    """
    lines = _get_document_lines(pdf_path)
    return _section_headings_from_lines(lines, _body_font_size(lines))


def extract_figure_captions(pdf_path):
    """Extract figure headings/captions from a PDF.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        list: A list of dictionaries, each containing the figure ``number``
        and its ``caption`` text, in the order they appear in the document.
    """
    lines = _get_document_lines(pdf_path)
    return _extract_validated_captions(
        lines, _FIGURE_CAPTION, "number", "caption", _body_font_size(lines)
    )


def extract_table_captions(pdf_path):
    """Extract table headings/captions from a PDF.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        list: A list of dictionaries, each containing the table ``number``
        and its ``caption`` text, in the order they appear in the document.
    """
    lines = _get_document_lines(pdf_path)
    return _extract_validated_captions(
        lines, _TABLE_CAPTION, "number", "caption", _body_font_size(lines)
    )


def _table_captions_from_document(document):
    """Like :func:`extract_table_captions`, but for an already-open
    PyMuPDF document. Used by ``table_extraction`` so that pairing tables
    with captions only has to parse the PDF once."""
    lines = _lines_from_document(document)
    return _extract_validated_captions(
        lines, _TABLE_CAPTION, "number", "caption", _body_font_size(lines)
    )


def extract_document_structure(pdf_path):
    """Extract the section headings, figure captions, and table captions
    from a PDF.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        dict: A dictionary with the keys ``section_headings``,
        ``figure_captions``, and ``table_captions``.
    """
    lines = _get_document_lines(pdf_path)
    body_size = _body_font_size(lines)

    return {
        "section_headings": _section_headings_from_lines(lines, body_size),
        "figure_captions": _extract_validated_captions(
            lines, _FIGURE_CAPTION, "number", "caption", body_size
        ),
        "table_captions": _extract_validated_captions(
            lines, _TABLE_CAPTION, "number", "caption", body_size
        ),
    }
