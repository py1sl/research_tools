"""Extraction of a PDF's document structure: section headings, figure
captions, and table captions."""
import re

from PyPDF2 import PdfReader

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


def _get_pdf_text(pdf_path):
    reader = PdfReader(pdf_path)
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _ends_sentence(line):
    line = line.strip()
    if not _CAPTION_SENTENCE_END.search(line):
        return False

    if line.endswith("."):
        final_word = line.rsplit(None, 1)[-1][:-1].lower()
        if final_word in _ABBREVIATIONS:
            return False
    return True


def _is_numbered_heading(text):
    text = text.strip()
    return (
        len(text.split()) <= 12
        and len(text) <= 100
        and text[0].isupper()
        and not _ends_sentence(text)
    )


def _is_heading_line(line):
    numbered_match = _NUMBERED_SECTION_HEADING.match(line)
    return bool(
        _NAMED_SECTION_HEADING.match(line)
        or _FIGURE_CAPTION.match(line)
        or _TABLE_CAPTION.match(line)
        or (
            numbered_match
            and _is_numbered_heading(numbered_match.group(2))
            and not (_FIGURE_CAPTION.match(line) or _TABLE_CAPTION.match(line))
        )
    )


def _extract_captions(lines, pattern, number_key, text_key, strict=False):
    captions = []
    current = None

    def save_current():
        if current is not None:
            text = " ".join(" ".join(current["parts"]).split())
            captions.append({number_key: current["number"], text_key: text})

    for line in lines:
        stripped = line.strip()
        match = pattern.match(line)
        if match:
            save_current()
            current = {"number": match.group(1), "parts": [match.group(2).strip()]}
            if _ends_sentence(match.group(2)):
                save_current()
                current = None
            continue

        if current is not None:
            if not stripped or _is_heading_line(line):
                save_current()
                current = None
            elif strict and current["parts"] and stripped[0].isupper():
                save_current()
                current = None
            else:
                current["parts"].append(stripped)
                if _ends_sentence(stripped):
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


def _extract_validated_captions(lines, pattern, number_key, text_key):
    captions = _extract_captions(lines, pattern, number_key, text_key)
    if _numbers_are_sequential(captions, number_key):
        return captions
    return _extract_captions(lines, pattern, number_key, text_key, strict=True)


def _section_headings_from_lines(lines):
    headings = []

    for line in lines:
        named_match = _NAMED_SECTION_HEADING.match(line)
        if named_match:
            headings.append(
                {"number": named_match.group(1), "heading": named_match.group(2).strip()}
            )
            continue

        numbered_match = _NUMBERED_SECTION_HEADING.match(line)
        if (
            numbered_match
            and _is_numbered_heading(numbered_match.group(2))
            and not (_FIGURE_CAPTION.match(line) or _TABLE_CAPTION.match(line))
        ):
            headings.append(
                {
                    "number": numbered_match.group(1),
                    "heading": numbered_match.group(2).strip(),
                }
            )

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
    text = _get_pdf_text(pdf_path)
    return _section_headings_from_lines(text.splitlines())


def extract_figure_captions(pdf_path):
    """Extract figure headings/captions from a PDF.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        list: A list of dictionaries, each containing the figure ``number``
        and its ``caption`` text, in the order they appear in the document.
    """
    text = _get_pdf_text(pdf_path)
    return _extract_validated_captions(
        text.splitlines(), _FIGURE_CAPTION, "number", "caption"
    )


def extract_table_captions(pdf_path):
    """Extract table headings/captions from a PDF.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        list: A list of dictionaries, each containing the table ``number``
        and its ``caption`` text, in the order they appear in the document.
    """
    text = _get_pdf_text(pdf_path)
    return _extract_validated_captions(
        text.splitlines(), _TABLE_CAPTION, "number", "caption"
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
    text = _get_pdf_text(pdf_path)
    lines = text.splitlines()

    return {
        "section_headings": _section_headings_from_lines(lines),
        "figure_captions": _extract_validated_captions(
            lines, _FIGURE_CAPTION, "number", "caption"
        ),
        "table_captions": _extract_validated_captions(
            lines, _TABLE_CAPTION, "number", "caption"
        ),
    }
