import os
import re
from pathlib import Path

from . import extract_content, parse_structure


def _iter_markdown_files(folder_path):
    """Yield absolute paths for all .md files under folder_path."""
    for root, _, files in os.walk(folder_path):
        for fname in files:
            if fname.endswith('.md'):
                yield os.path.join(root, fname)


def _read_file(path):
    """Read a file and return its text, or None on error."""
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def _extract_snippet(text, query, window=150):
    """
    Return a short excerpt from text around the first occurrence of any
    query token.  Falls back to the start of the text if nothing matches.

    Args:
        text (str): Plain text to search.
        query (str): Query string.
        window (int): Number of characters either side of the match.

    Returns:
        str: Snippet with leading/trailing whitespace stripped.
    """
    if not query:
        return text[:window * 2].strip()
    tokens = re.findall(r'\w+', query.lower())
    for token in tokens:
        match = re.search(re.escape(token), text, re.IGNORECASE)
        if match:
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            snippet = text[start:end].strip()
            return f"...{snippet}..." if start > 0 else snippet
    return text[:window * 2].strip()


def search_notes(folder_path, query=None, tags=None, heading=None):
    """
    Search all markdown notes in a folder for notes matching the given criteria.

    At least one of query, tags, or heading should be supplied; if none are
    supplied every note is returned with a minimal summary.

    Args:
        folder_path (str): Path to the root folder containing .md files.
        query (str | None): Free-text query; notes/sections containing any of
            the query tokens are returned.
        tags (list[str] | None): Only return notes that carry ALL listed tags.
        heading (str | None): Only return notes that contain a heading whose
            text matches (case-insensitive substring).

    Returns:
        list[dict]: Each dict has:
            - "file" (str): Absolute file path.
            - "title" (str): Note title (H1 or filename).
            - "tags" (list[str]): All tags on the note.
            - "matching_sections" (list[str]): Headings of sections that
              contain the query.
            - "snippet" (str): Short excerpt around the first query match.

    Raises:
        FileNotFoundError: If folder_path does not exist.
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    tags_filter = [t.lstrip('#').lower() for t in tags] if tags else []
    results = []

    for filepath in sorted(_iter_markdown_files(folder_path)):
        raw = _read_file(filepath)
        if raw is None:
            continue

        metadata, body = parse_structure.parse_frontmatter(raw)

        # --- collect tags ---
        fm_tags = metadata.get('tags', [])
        if isinstance(fm_tags, str):
            fm_tags = [fm_tags]
        inline_tags = parse_structure.extract_inline_tags(body)
        all_tags = list({t.lower() for t in fm_tags + inline_tags})

        # --- tags filter ---
        if tags_filter and not all(t in all_tags for t in tags_filter):
            continue

        # --- heading filter ---
        headings_in_note = [h['text'] for h in parse_structure.extract_headings(body)]
        if heading:
            if not any(heading.lower() in h.lower() for h in headings_in_note):
                continue

        # --- title ---
        first_h1 = next((h['text'] for h in parse_structure.extract_headings(body)
                         if h['level'] == 1), None)
        title = first_h1 or metadata.get('title') or Path(filepath).stem

        # --- query matching ---
        sections = parse_structure.split_by_headings(body)
        matching_sections = []
        plain_full = extract_content.extract_plain_text(body)

        if query:
            for sec_heading, sec_body in sections.items():
                if parse_structure.score_section_relevance(sec_body, query) > 0:
                    matching_sections.append(sec_heading or "(intro)")
            if not matching_sections:
                # No section match — check full text
                if parse_structure.score_section_relevance(plain_full, query) == 0:
                    continue
        
        snippet = _extract_snippet(plain_full, query)

        results.append({
            "file": filepath,
            "title": title,
            "tags": all_tags,
            "matching_sections": matching_sections,
            "snippet": snippet
        })

    return results


def get_note_graph(folder_path):
    """
    Build a link adjacency graph for all notes in a folder.

    Each note is represented by its title (H1 heading or filename stem).
    The graph maps each note title to the list of link targets (as written
    in the note) that point to other ``.md`` files via standard markdown
    links (e.g. ``[text](other_note.md)``).

    Args:
        folder_path (str): Path to the root folder containing .md files.

    Returns:
        dict[str, list[str]]: Adjacency dict {note_title: [link_targets]}.
            Link targets are the raw path strings from the markdown source.

    Raises:
        FileNotFoundError: If folder_path does not exist.
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    graph = {}
    for filepath in sorted(_iter_markdown_files(folder_path)):
        raw = _read_file(filepath)
        if raw is None:
            continue

        metadata, body = parse_structure.parse_frontmatter(raw)
        first_h1 = next(
            (h['text'] for h in parse_structure.extract_headings(body) if h['level'] == 1),
            None
        )
        title = first_h1 or metadata.get('title') or Path(filepath).stem
        links = [lnk['target'] for lnk in parse_structure.extract_internal_links(body)]
        graph[title] = links

    return graph
