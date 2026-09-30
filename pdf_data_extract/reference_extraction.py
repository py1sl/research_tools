import re

import pymupdf


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


def _extract_reference_section(text):
    lines = text.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if _REFERENCE_HEADING.match(line)),
        None,
    )
    if start is None:
        return []

    section_lines = []
    for line in lines[start + 1:]:
        if _END_HEADING.match(line):
            break
        section_lines.append(line)

    return _parse_references(section_lines)


def _parse_references(lines):
    references = []
    current = []

    def save_current():
        citation = " ".join(" ".join(current).split())
        if citation:
            doi_match = _DOI.search(citation)
            doi = doi_match.group().rstrip(".,;:") if doi_match else None
            references.append({"text": citation, "doi": doi})
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
            stripped = re.sub(r"^\s*[-•]\s*", "", line)

        if stripped:
            current.append(stripped)

    save_current()
    return references


def extract_references(pdf_path):
    """Extract citation records from a PDF's references or bibliography section.

    Each returned record contains the normalized citation ``text`` and its
    detected ``doi`` (or ``None`` when the citation does not include one).
    Numbered references and references separated by blank lines are supported.
    """
    try:
        document = pymupdf.open(pdf_path)
    except pymupdf.FileNotFoundError as error:
        raise FileNotFoundError(str(error)) from error

    try:
        text = "\n".join(page.get_text("text") for page in document)
    finally:
        document.close()

    return _extract_reference_section(text)
