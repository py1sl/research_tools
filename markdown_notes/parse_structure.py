import re
import frontmatter


def parse_frontmatter(text):
    """
    Parse YAML/TOML front-matter from a markdown string.

    Args:
        text (str): Raw markdown text.

    Returns:
        tuple[dict, str]: A (metadata dict, body without front-matter) pair.
    """
    try:
        post = frontmatter.loads(text)
        return dict(post.metadata), post.content
    except Exception:
        return {}, text


def extract_headings(text):
    """
    Extract all ATX-style headings from markdown text.

    Args:
        text (str): Markdown body text (front-matter already stripped).

    Returns:
        list[dict]: Ordered list of {"level": int, "text": str} dicts.
    """
    headings = []
    for line in text.splitlines():
        match = re.match(r'^(#{1,6})\s+(.*)', line)
        if match:
            headings.append({
                "level": len(match.group(1)),
                "text": match.group(2).strip()
            })
    return headings


def split_by_headings(text):
    """
    Split markdown body into sections keyed by heading text.

    Content before the first heading is stored under the key "" (empty string).
    When duplicate heading names exist, later sections are suffixed with an
    incrementing counter (e.g. "Method", "Method_2").

    Args:
        text (str): Markdown body text (front-matter already stripped).

    Returns:
        dict[str, str]: Mapping of heading text → section body.
    """
    sections = {}
    seen_keys = {}
    current_key = ""
    current_lines = []

    for line in text.splitlines(keepends=True):
        match = re.match(r'^(#{1,6})\s+(.*)', line)
        if match:
            sections[current_key] = "".join(current_lines).strip()
            heading_text = match.group(2).strip()
            if heading_text in seen_keys:
                seen_keys[heading_text] += 1
                current_key = f"{heading_text}_{seen_keys[heading_text]}"
            else:
                seen_keys[heading_text] = 1
                current_key = heading_text
            current_lines = []
        else:
            current_lines.append(line)

    sections[current_key] = "".join(current_lines).strip()
    return sections


def extract_internal_links(text):
    """
    Extract internal note links from markdown text.

    An internal link is a standard markdown link whose target is a relative
    path ending in ``.md`` (e.g. ``[Methods](methods.md)`` or
    ``[See also](../other/note.md)``).  Absolute URLs (``http://…``) and
    image links are ignored.

    Args:
        text (str): Markdown text.

    Returns:
        list[dict]: Unique list of dicts with keys:
            - ``"display"`` (str): The link display text.
            - ``"target"`` (str): The raw link target as written in the note.
    """
    pattern = re.compile(r'!\[.*?\]\([^\)]*\)|'   # consume image links first
                         r'\[([^\]]+)\]\(([^\)]+)\)')
    links = []
    seen = set()
    for match in pattern.finditer(text):
        display = match.group(1)
        target = match.group(2)
        # Skip image links (group 1 is None) and external/anchor-only links
        if display is None:
            continue
        target = target.strip()
        if target.startswith(('http://', 'https://', '#', 'mailto:')):
            continue
        # Keep only links that point at markdown files
        path_part = target.split('#')[0]  # strip in-page anchor
        if not path_part.endswith('.md'):
            continue
        key = (display, target)
        if key not in seen:
            seen.add(key)
            links.append({"display": display, "target": target})
    return links


def extract_inline_tags(text):
    """
    Extract inline #tags from markdown text (excludes headings lines).

    Args:
        text (str): Markdown text.

    Returns:
        list[str]: Unique list of tag names (without the leading #).
    """
    tags = []
    seen = set()
    for line in text.splitlines():
        # Skip heading lines
        if re.match(r'^#{1,6}\s', line):
            continue
        for match in re.finditer(r'(?<!\w)#([A-Za-z][A-Za-z0-9_/-]*)', line):
            tag = match.group(1)
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tags


def score_section_relevance(section_text, query):
    """
    Return a simple keyword-overlap relevance score for query-aware filtering.

    Splits both section text and query into lowercase tokens and counts how
    many unique query tokens appear in the section.

    Args:
        section_text (str): Body text of a single section.
        query (str): The query string.

    Returns:
        int: Number of unique query tokens found in the section text.
    """
    if not query or not section_text:
        return 0
    query_tokens = set(re.findall(r'\w+', query.lower()))
    section_lower = section_text.lower()
    return sum(1 for tok in query_tokens if tok in section_lower)
