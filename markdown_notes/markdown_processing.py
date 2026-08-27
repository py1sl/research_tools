import os
from pathlib import Path

from . import extract_content, parse_structure, search as note_search


def read_note(note_path, query=None):
    """
    Read a single markdown note and return a rich structured representation.

    This is the primary entry point for a research agent that needs to
    understand the content of a specific note.  The optional *query*
    parameter causes the returned ``sections`` dict to be filtered so that
    only sections relevant to the query are included, keeping the agent's
    context window tight.

    Args:
        note_path (str): Absolute or relative path to the ``.md`` file.
        query (str | None): Optional free-text query used to filter the
            returned sections by relevance.

    Returns:
        dict: A structured representation of the note with the following keys:

            - ``title`` (str): H1 heading, front-matter title, or filename stem.
            - ``tags`` (list[str]): All tags from front-matter and inline ``#tag``
              notation.
            - ``created`` (str | None): Creation date from front-matter.
            - ``modified`` (str | None): Last-modified date from front-matter.
            - ``summary`` (str | None): First plain-text paragraph of the note.
            - ``section_headings`` (list[str]): Ordered list of all headings.
            - ``sections`` (dict[str, str]): Mapping of heading → section body.
              Filtered by *query* relevance when *query* is provided; if
              no section scores above zero every section is returned.
            - ``internal_links`` (list[dict]): Standard markdown links to other
              ``.md`` files.  Each dict has ``"display"`` (link text) and
              ``"target"`` (path as written) keys.
            - ``external_links`` (list[str]): HTTP/HTTPS URLs found in the note.
            - ``code_blocks`` (list[dict]): Each dict has ``"language"`` and
              ``"content"`` keys.
            - ``tables`` (list[list[list[str]]]): Each table is a list of rows;
              each row is a list of cell strings.
            - ``raw`` (str): The full original markdown text.

    Raises:
        FileNotFoundError: If *note_path* does not exist.
        ValueError: If *note_path* does not end with ``.md``.
    """
    if not os.path.exists(note_path):
        raise FileNotFoundError(f"Note not found: {note_path}")
    if not note_path.endswith('.md'):
        raise ValueError(f"Expected a .md file, got: {note_path}")

    with open(note_path, 'r', encoding='utf-8') as fh:
        raw = fh.read()

    metadata, body = parse_structure.parse_frontmatter(raw)

    # --- title ---
    first_h1 = next(
        (h['text'] for h in parse_structure.extract_headings(body) if h['level'] == 1),
        None
    )
    title = first_h1 or metadata.get('title') or Path(note_path).stem

    # --- tags ---
    fm_tags = metadata.get('tags', [])
    if isinstance(fm_tags, str):
        fm_tags = [fm_tags]
    inline_tags = parse_structure.extract_inline_tags(body)
    all_tags = list({t.lower() for t in list(fm_tags) + inline_tags})

    # --- sections ---
    all_sections = parse_structure.split_by_headings(body)

    if query:
        scored = {
            k: v for k, v in all_sections.items()
            if parse_structure.score_section_relevance(v, query) > 0
        }
        # Fall back to all sections if nothing matched
        sections = scored if scored else all_sections
    else:
        sections = all_sections

    def _str_or_none(val):
        return str(val) if val is not None else None

    return {
        "title": title,
        "tags": all_tags,
        "created": _str_or_none(metadata.get('created') or metadata.get('date')),
        "modified": _str_or_none(metadata.get('modified') or metadata.get('updated')),
        "summary": extract_content.extract_summary(body),
        "section_headings": [h['text'] for h in parse_structure.extract_headings(body)],
        "sections": sections,
        "internal_links": parse_structure.extract_internal_links(body),
        "external_links": extract_content.extract_external_links(body),
        "code_blocks": extract_content.extract_code_blocks(body),
        "tables": extract_content.extract_tables(body),
        "raw": raw
    }


def search_notes(folder_path, query=None, tags=None, heading=None):
    """
    Search all markdown notes in a folder for notes that match the given
    criteria.

    This is the discovery entry point: use it to find *which* notes are
    relevant before reading them in full with :func:`read_note`.

    Args:
        folder_path (str): Path to the root folder (searched recursively).
        query (str | None): Free-text query; notes/sections containing any
            query token are returned.
        tags (list[str] | None): Restrict results to notes carrying ALL
            listed tags.  Tags may be supplied with or without a leading ``#``.
        heading (str | None): Restrict results to notes that contain at least
            one heading whose text contains this string (case-insensitive).

    Returns:
        list[dict]: Lightweight match records, each with:

            - ``"file"`` (str): Absolute path to the note file.
            - ``"title"`` (str): Note title.
            - ``"tags"`` (list[str]): All tags on the note.
            - ``"matching_sections"`` (list[str]): Headings of sections that
              match the query.
            - ``"snippet"`` (str): Short text excerpt around the first match.

    Raises:
        FileNotFoundError: If *folder_path* does not exist.
    """
    return note_search.search_notes(
        folder_path, query=query, tags=tags, heading=heading
    )


def get_note_graph(folder_path):
    """
    Build a link adjacency graph for all notes in a folder.

    Use this to understand how notes are connected without reading every file
    in full.  The graph is keyed by note title and lists the raw link targets
    (paths) of standard markdown links to other ``.md`` files.  To find notes
    that link *to* a specific note, scan the values for that note's filename.

    Args:
        folder_path (str): Path to the root folder (searched recursively).

    Returns:
        dict[str, list[str]]: ``{note_title: [link_targets]}``.

    Raises:
        FileNotFoundError: If *folder_path* does not exist.
    """
    return note_search.get_note_graph(folder_path)
