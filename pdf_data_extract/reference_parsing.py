"""Heuristic parsing of a single citation string into bibliographic fields."""

import re

_DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_ARXIV = re.compile(
    r"\barXiv\s*:\s*\S+|\barxiv\.org/abs/\S+|\b[a-z-]+/\d{7}\b", re.IGNORECASE
)
_URL = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
_PAREN_YEAR = re.compile(r"\(\s*((?:19|20)\d{2})[a-z]?\s*\)")
_ANY_YEAR = re.compile(r"(?<![\d.])((?:19|20)\d{2})[a-z]?(?!\d)")
_PARTICLE = r"(?:(?i:van|von|de|der|den|di|da|la|le|du|del|ter)\s+)*"
_WORD = r"[^\W\d_][\w'\u2019-]*"
_INITIALS = r"(?:[A-Z]\.[ -]?){1,4}"
_INITIAL_FIRST = re.compile(rf"{_INITIALS}\s*{_PARTICLE}{_WORD}(?:\s+(?:Jr|Sr)\.?)?")
_SURNAME_FIRST = re.compile(
    rf"{_PARTICLE}{_WORD}(?:\s+{_WORD})?,\s*{_INITIALS}"
)
_INITIAL_SEP = re.compile(r"\s*(?:,\s*(?:and\s+|&\s*)?|\s+and\s+|\s*&\s*)")
_SURNAME_SEP = re.compile(r"\s*(?:,\s*(?:and\s+|&\s*)?|\s+and\s+|\s*&\s*)")
_ET_AL = re.compile(r"\s*,?\s*et\s+al\.?", re.IGNORECASE)
_VOL_PAGES = re.compile(
    r"(?:vol\.?\s*)?\b(?P<vol>\d{1,4})\s*[,:]\s*"
    r"(?:no\.?\s*\d+\s*,\s*)?(?:pp?\.\s*)?"
    r"(?P<pages>[A-Za-z]?\d+(?:\s*[-\u2013\u2014]+\s*[A-Za-z]?\d+)?)"
)
_SENTENCE_SPLIT = re.compile(r"(?<=[a-z]{4})\.\s+(?=[A-Z\"\u201c])")
_QUOTED = re.compile(r"[\"\u201c](.+?)[,.]?[\"\u201d]")


def _consume_authors(text, name, sep):
    """Greedily match a list of names; return (names, end_position)."""
    names = []
    pos = 0
    while True:
        match = name.match(text, pos)
        if not match:
            break
        names.append(" ".join(match.group().split()))
        pos = match.end()
        et_al = _ET_AL.match(text, pos)
        if et_al:
            names.append("et al.")
            pos = et_al.end()
            break
        separator = sep.match(text, pos)
        if not separator or not name.match(text, separator.end()):
            break
        pos = separator.end()
    return names, pos


def _split_authors(text):
    first = _consume_authors(text, _INITIAL_FIRST, _INITIAL_SEP)
    second = _consume_authors(text, _SURNAME_FIRST, _SURNAME_SEP)
    return second if second[1] > first[1] else first


def _clean(value):
    value = (value or "").strip(" \t.,;:-\u2013")
    return value or None


def parse_reference(text):
    """Parse a citation string into ``authors``, ``title``, ``journal``,
    ``volume``, ``pages`` and ``year``.

    The parser is heuristic and handles common physics/ACS styles
    (``A. Author, Title, Phys. Rev. Lett. 99, 123 (2007)``) and author-year
    styles (``Author, A. (2019). Title. Journal, 4, 1-10.``). Fields that
    cannot be determined are ``None``; ``authors`` is a (possibly empty) list.
    """
    result = {
        "authors": [],
        "title": None,
        "journal": None,
        "volume": None,
        "pages": None,
        "year": None,
    }
    text = " ".join((text or "").split())
    text = _URL.sub(" ", _DOI.sub(" ", text))
    text = re.sub(r"\b(?:doi|arxiv)\s*:?\s*(?=$|[\s,;.])", " ", text, flags=re.I)
    text = _ARXIV.sub(" ", text)
    text = " ".join(text.split())

    authors, end = _split_authors(text)
    result["authors"] = authors
    rest = text[end:].lstrip(" .,;:")

    year_match = _PAREN_YEAR.search(rest)
    if year_match:
        result["year"] = int(year_match.group(1))
        rest = rest[: year_match.start()] + " " + rest[year_match.end():]
    rest = " ".join(rest.split()).strip(" .,;:")

    quoted = _QUOTED.search(rest)
    if quoted:
        result["title"] = _clean(quoted.group(1))
        rest = (rest[: quoted.start()] + " " + rest[quoted.end():]).strip(" .,;:")

    vol = _VOL_PAGES.search(rest)
    if vol:
        result["volume"] = vol.group("vol")
        result["pages"] = re.sub(
            r"\s*[-\u2013\u2014]+\s*", "-", vol.group("pages")
        )
        before = rest[: vol.start()]
        after = rest[vol.end():]
        if result["year"] is None:
            tail = _ANY_YEAR.search(after)
            if tail:
                result["year"] = int(tail.group(1))
        blob = before.strip(" .,;:")
    else:
        if result["year"] is None:
            years = _ANY_YEAR.findall(rest)
            if years:
                result["year"] = int(years[-1])
        blob = _ANY_YEAR.sub("", rest).strip(" .,;:")
        blob = re.sub(r"[,\s]+$", "", blob)

    if result["title"] is None:
        _assign_title_journal(result, blob, bool(vol))
    else:
        result["journal"] = _clean(blob)
    return result


def _assign_title_journal(result, blob, has_volume):
    if not blob:
        return
    parts = _SENTENCE_SPLIT.split(blob, maxsplit=1)
    if len(parts) == 2 and len(parts[0].split()) >= 2:
        result["title"] = _clean(parts[0])
        result["journal"] = _clean(parts[1])
        return
    if "," in blob:
        title, _, journal = blob.rpartition(",")
        result["title"] = _clean(title)
        result["journal"] = _clean(journal)
        return
    if has_volume or len(blob.split()) < 2:
        result["journal"] = _clean(blob)
    else:
        result["title"] = _clean(blob)


def parse_references(references):
    """Add parsed fields to each record from ``extract_references``.

    Returns new dictionaries containing the original keys plus ``authors``,
    ``title``, ``journal``, ``volume`` and ``pages``. An existing ``year`` is
    kept when present.
    """
    parsed = []
    for record in references:
        fields = parse_reference(record["text"])
        merged = dict(record)
        if merged.get("year") is not None:
            fields.pop("year")
        merged.update(fields)
        parsed.append(merged)
    return parsed
