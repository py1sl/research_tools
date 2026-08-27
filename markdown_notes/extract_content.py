import re


def extract_plain_text(text):
    """
    Return the markdown body with code fences, front-matter, and inline
    markup stripped, leaving readable plain text.

    Args:
        text (str): Raw markdown text (may include front-matter).

    Returns:
        str: Plain text content.
    """
    # Remove fenced code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`\n]+`', '', text)
    # Remove images
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Remove links but keep display text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove wikilinks but keep display text / target
    text = re.sub(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', lambda m: m.group(2) or m.group(1), text)
    # Remove bold/italic markers
    text = re.sub(r'(\*{1,3}|_{1,3})(.*?)\1', r'\2', text)
    # Remove heading markers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_summary(text):
    """
    Return the first non-empty paragraph from the markdown body.

    Suitable for use as a short abstract or overview of the note.

    Args:
        text (str): Markdown body text (front-matter already stripped).

    Returns:
        str | None: First paragraph text, or None if not found.
    """
    plain = extract_plain_text(text)
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', plain) if p.strip()]
    return paragraphs[0] if paragraphs else None


def extract_code_blocks(text):
    """
    Extract fenced code blocks from markdown text.

    Args:
        text (str): Markdown text.

    Returns:
        list[dict]: Each dict has "language" (str, may be empty) and
                    "content" (str) keys.
    """
    pattern = re.compile(r'```([^\n]*)\n([\s\S]*?)```', re.MULTILINE)
    blocks = []
    for match in pattern.finditer(text):
        blocks.append({
            "language": match.group(1).strip(),
            "content": match.group(2)
        })
    return blocks


def extract_tables(text):
    """
    Extract GFM-style pipe tables from markdown text.

    Returns each table as a list of rows, where each row is a list of
    stripped cell strings.  The separator row (---) is excluded.

    Args:
        text (str): Markdown text.

    Returns:
        list[list[list[str]]]: List of tables; each table is a list of rows.
    """
    tables = []
    current_table = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped[1:-1].split('|')]
            # Skip separator rows (e.g. | --- | --- |)
            if all(re.match(r'^:?-+:?$', c) for c in cells if c):
                continue
            current_table.append(cells)
        else:
            if current_table:
                tables.append(current_table)
                current_table = []

    if current_table:
        tables.append(current_table)

    return tables


def extract_external_links(text):
    """
    Extract external (HTTP/HTTPS) URLs from markdown text.

    Captures both inline links [text](url) and bare URLs.

    Args:
        text (str): Markdown text.

    Returns:
        list[str]: Unique list of external URLs.
    """
    urls = []
    seen = set()

    # Inline links: [text](url)
    for match in re.finditer(r'\[.*?\]\((https?://[^\)]+)\)', text):
        url = match.group(1).strip()
        if url not in seen:
            seen.add(url)
            urls.append(url)

    # Bare URLs not already captured
    for match in re.finditer(r'(?<!\()https?://\S+', text):
        url = match.group(0).rstrip('.,;)')
        if url not in seen:
            seen.add(url)
            urls.append(url)

    return urls
