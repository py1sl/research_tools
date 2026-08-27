# Markdown Notes Tools

A set of Python tools for reading and searching personal research notes written
in Markdown (compatible with Obsidian-style vaults).  Part of the
`research_tools` ecosystem supporting a research assistant agent.

## Overview

| Module | Role |
|---|---|
| `markdown_processing.py` | **Main entry point** — exposes the three public tool functions |
| `parse_structure.py` | Front-matter, headings, sections, wikilinks, tags |
| `extract_content.py` | Plain text, summaries, code blocks, tables, external links |
| `search.py` | Cross-file search and note-graph construction |

All code targets Python 3.12.

## Public API

### `read_note(note_path, query=None)`

Read a single `.md` file and return a rich structured dict:

```python
{
  "title": str,
  "tags": list[str],
  "created": str | None,
  "modified": str | None,
  "summary": str | None,
  "section_headings": list[str],
  "sections": dict[str, str],   # filtered by query when query is given
  "wikilinks": list[str],
  "external_links": list[str],
  "code_blocks": list[dict],    # {"language": str, "content": str}
  "tables": list[list[list]],
  "raw": str
}
```

### `search_notes(folder_path, query=None, tags=None, heading=None)`

Search all `.md` files under `folder_path` (recursive).  Returns a list of
lightweight match dicts useful for narrowing down which notes to read in full.

### `get_note_graph(folder_path)`

Returns a wikilink adjacency dict `{note_title: [linked_note_titles]}` for the
entire vault — useful for understanding note relationships.

## Dependencies

- `python-frontmatter` — YAML/TOML front-matter parsing
- `markdown-it-py` — available in the environment (used indirectly)
- Standard library: `os`, `re`, `pathlib`
