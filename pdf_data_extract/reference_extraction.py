import re

import pymupdf

from .reference_parsing import parse_references


_REFERENCE_HEADING = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s+)?"
    r"(?:references|bibliography|works cited|literature cited)"
    r"(?:\s*\([^)]*\))?\s*:?\s*$",
    re.IGNORECASE,
)
_END_HEADING = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s+)?"
    r"(?:appendix(?:es)?|acknowledg(?:e)?ments?|author contributions|"
    r"funding|conflicts? of interest|declarations|data availability|"
    r"supplementary (?:material|information)|footnotes)"
    r"\s*:?\s*$",
    re.IGNORECASE,
)
_NUMBERED_REFERENCE = re.compile(r"^\s*(?:\[(\d+)\]|(\d+)[.)])\s+")
_DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_ARXIV = re.compile(
    r"\barXiv\s*:\s*((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)"
    r"|\barxiv\.org/abs/((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)",
    re.IGNORECASE,
)
_URL = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
_YEAR = re.compile(r"(?<![\d.])((?:19|20)\d{2})[a-z]?(?![\d])")
_NEW_ENTRY = re.compile(
    r"^\s*(?:[A-Z][\w'\u2019-]+(?:\s[\w'\u2019-]+)?,\s+(?:[A-Z]\.|[A-Z][a-z]+\b)"
    r"|[A-Z]\.(?:\s?[A-Z]\.)*\s+[A-Z][\w'\u2019-]+,)"
)
_ENTRY_END = re.compile(r"[.)\]\d]$")
_SPLIT_DOI_TAIL = re.compile(r"(?:doi\.org/|doi:|\b10\.\d{4,9}/?)$", re.IGNORECASE)


def _extract_reference_section(text):
    lines = text.splitlines()
    headings = [
        index for index, line in enumerate(lines) if _REFERENCE_HEADING.match(line)
    ]
    if not headings:
        return []
    # Prefer the last heading: earlier matches are usually a table of contents.
    start = headings[-1]

    section_lines = []
    for line in lines[start + 1:]:
        if _END_HEADING.match(line):
            break
        section_lines.append(line)

    return _parse_references(section_lines)


def _join(current, piece):
    """Append a line to an entry, repairing hyphenation and split DOIs."""
    if not current:
        current.append(piece)
        return current
    last = current[-1]
    if re.search(r"[A-Za-z]{2}-$", last) and piece[:1].islower():
        current[-1] = last[:-1] + piece
    elif _SPLIT_DOI_TAIL.search(last) or re.match(r"^[-._;/:]", piece):
        current[-1] = last + piece
    else:
        current.append(piece)
    return current


def _build_record(text):
    doi_match = _DOI.search(text)
    doi = doi_match.group().rstrip(".,;:)") if doi_match else None
    arxiv_match = _ARXIV.search(text)
    arxiv_id = (
        (arxiv_match.group(1) or arxiv_match.group(2)) if arxiv_match else None
    )
    url_match = next(
        (m for m in _URL.finditer(text) if "doi.org" not in m.group().lower()
         and "arxiv.org" not in m.group().lower()),
        None,
    )
    url = url_match.group().rstrip(".,;:)") if url_match else None
    # Ignore digits belonging to the DOI/arXiv identifiers when finding the year.
    stripped = _URL.sub(" ", _DOI.sub(" ", text))
    stripped = _ARXIV.sub(" ", stripped)
    year_match = _YEAR.search(stripped)
    return {
        "text": text,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "url": url,
        "year": int(year_match.group(1)) if year_match else None,
    }


def _parse_references(lines):
    numbered = any(_NUMBERED_REFERENCE.match(line) for line in lines)
    entries = []
    current = []

    def save_current():
        citation = " ".join(" ".join(current).split())
        if citation:
            record = _build_record(citation)
            record["index"] = len(entries) + 1
            entries.append(record)
        current.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                save_current()
            continue

        numbered_start = _NUMBERED_REFERENCE.match(line)
        if numbered_start:
            save_current()
            stripped = line[numbered_start.end():].strip()
        elif not current:
            stripped = re.sub(r"^\s*[-•]\s*", "", line).strip()
        elif (
            not numbered
            and _NEW_ENTRY.match(stripped)
            and _ENTRY_END.search(current[-1])
        ):
            save_current()

        if stripped:
            _join(current, stripped)

    save_current()
    return entries


def _strip_page_furniture(pages):
    """Remove running headers/footers and bare page numbers from page texts."""
    split = [page.splitlines() for page in pages]

    def key(line):
        return re.sub(r"\d+", "#", line.strip())

    counts = {}
    for lines in split:
        edge = [l for l in lines[:2] + lines[-2:] if l.strip()]
        for k in {key(l) for l in edge}:
            counts[k] = counts.get(k, 0) + 1
    threshold = max(3, len(pages) // 2)

    cleaned = []
    for lines in split:
        keep = []
        last = len(lines) - 1
        for i, line in enumerate(lines):
            on_edge = i < 2 or i > last - 2
            if on_edge and line.strip():
                if re.fullmatch(r"\s*(?:page\s+)?\d{1,4}\s*", line, re.IGNORECASE):
                    continue
                if counts.get(key(line), 0) >= threshold and len(pages) >= 3:
                    continue
            keep.append(line)
        cleaned.append("\n".join(keep))
    return cleaned


def extract_references(pdf_path, parse_fields=False):
    """Extract citation records from a PDF's references or bibliography section.

    Each returned record contains the normalized citation ``text`` and its
    1-based ``index``, and any detected ``doi``, ``arxiv_id``, ``url`` and
    ``year`` (``None`` when absent). Numbered, blank-line separated and
    unnumbered author-first references are supported; page text is read in
    reading order, running headers/footers are removed and hyphenated line
    breaks are repaired. With ``parse_fields=True`` each record also gets
    ``authors``, ``title``, ``journal``, ``volume`` and ``pages`` (see
    :func:`pdf_data_extract.reference_parsing.parse_reference`).
    """
    try:
        document = pymupdf.open(pdf_path)
    except pymupdf.FileNotFoundError as error:
        raise FileNotFoundError(str(error)) from error

    try:
        pages = [page.get_text("text", sort=True) for page in document]
    finally:
        document.close()

    references = _extract_reference_section(
        "\n".join(_strip_page_furniture(pages))
    )
    return parse_references(references) if parse_fields else references
