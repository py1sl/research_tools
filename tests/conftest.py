"""Shared pytest fixtures for markdown_notes tests."""
import os
import textwrap

import pytest


SIMPLE_NOTE = textwrap.dedent("""\
    ---
    title: My Note
    tags: [python, research]
    created: 2024-01-15
    modified: 2024-06-01
    ---
    # My Note

    This is the introduction paragraph.

    ## Background

    Some background text about #inline-tag and more words.

    ## Methods

    Details of the method. Visit https://example.com for more info.

    ```python
    def hello():
        return "world"
    ```

    | Header A | Header B |
    | -------- | -------- |
    | cell 1   | cell 2   |

    See also [Other Note](other_note.md) and [External](https://link.com).
""")

LINKED_NOTE = textwrap.dedent("""\
    # Other Note

    This note links back to [My Note](my_note.md).
""")


@pytest.fixture()
def note_dir(tmp_path):
    """Return a temporary directory pre-populated with two linked notes."""
    (tmp_path / "my_note.md").write_text(SIMPLE_NOTE, encoding="utf-8")
    (tmp_path / "other_note.md").write_text(LINKED_NOTE, encoding="utf-8")
    return tmp_path


@pytest.fixture()
def note_file(note_dir):
    """Return the path to the primary test note file."""
    return str(note_dir / "my_note.md")
