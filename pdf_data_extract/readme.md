# PDF Data Extraction Tools

This repository provides a set of tools designed for extracting data from PDF documents. These utilities form part of an ecosystem supporting research assistant agents, facilitating preprocessing steps to build databases or enable Retrieval-Augmented Generation (RAG). The tools may also be directly utilized by the agent itself.

## Overview

- **`extract_meta`**: Focuses on extracting metadata from PDF files.
- **`pdf_data_processing`**: Serves as the main controller and entry point for processing PDF data.
- **`reference_extraction`**: Targets extraction of reference sections from academic papers.
- **`structure_extraction`**: Extracts section headings, figure captions, and table captions.

All code is implemented in Python 3.12. All PDF parsing across `extract_meta`,
`reference_extraction`, and `structure_extraction` is backed by a single
library, [PyMuPDF](https://pymupdf.readthedocs.io/) (`pymupdf`); `PyPDF2` is
no longer a dependency of this package.

## Metadata extraction

`extract_metadata(pdf_path)` returns a dictionary of the PDF's document-info
metadata (`Title`, `Author`, `Subject`, `Creator`, `Producer`, `CreationDate`,
`ModDate`, `Keywords`, `Trapped`, `NumberOfPages`). `Author` is split into a
list of individual names, and `CreationDate`/`ModDate` are normalized from the
PDF's raw date format to `YYYY-MM-DD HH:MM:SS`. Missing fields are returned as
`None` (or an empty list for `Author`); errors reading the file are logged and
an empty/`None`-filled dictionary is returned rather than raised.

## Reference extraction

`extract_references(pdf_path)` returns a list of dictionaries from a PDF's
References, Bibliography, Works Cited, or Literature Cited section. Each
dictionary contains the normalized citation as `text` and the detected DOI as
`doi` (`None` when no DOI is present). Numbered citations and blank-line
separated citations are supported; PDFs without a recognized section return an
empty list.

## Structure extraction

Text is extracted with [PyMuPDF](https://pymupdf.readthedocs.io/) (`pymupdf`)
rather than plain string extraction. PyMuPDF reconstructs text line-by-line
from the PDF's layout instead of just concatenating characters in
content-stream order, which is notably more reliable for multi-column
academic layouts, and it exposes each line's font size and boldness. That
layout information is used as a second detection signal alongside the regex
heuristics below: a line that doesn't match the known regex vocabulary (for
example a non-standard or non-English section name) is still recognised as a
heading if it is visually distinguished from the body text (larger and/or
bold font). The regex heuristics remain the primary signal, so behaviour for
PDFs where every line shares the same font size/weight is unchanged.

- `extract_section_headings(pdf_path)` returns a list of dictionaries, each
  with a `number` (e.g. `"2.1"`, or `None` when unnumbered) and a `heading`
  string, for numbered headings, common named sections (Abstract,
  Introduction, Methods, Results, Discussion, Conclusion, References, etc.),
  and any other line that stands out from the body text by font size or
  boldness (returned with `number: None`).
- `extract_figure_captions(pdf_path)` returns a list of dictionaries, each
  with a `number` and `caption` string, for lines beginning with `Figure`/`Fig.`.
  Wrapped caption lines are joined; extraction stops at a blank line, a
  sentence ending, a page boundary, or a visually-distinguished heading line.
  If extracted figure numbers are not sequential, extraction retries with
  stricter caption boundaries.
- `extract_table_captions(pdf_path)` returns a list of dictionaries, each with
  a `number` and `caption` string, for lines beginning with `Table`. Captions
  spanning multiple lines are joined using the same boundaries as figure
  captions, including the sequential-number check and stricter retry.
- `extract_document_structure(pdf_path)` combines the three functions above
  into a single dictionary with `section_headings`, `figure_captions`, and
  `table_captions` keys.

PDFs without any recognizable headings or captions return empty lists.

### Considered alternatives

Dedicated scholarly-PDF parsers such as [GROBID](https://github.com/kermitt2/grobid)
or AllenAI's `pdffigures2`/`doc2json` generally produce more accurate results
than any regex-based approach, since they use models trained specifically on
academic papers. They were not adopted here because they require running a
separate Java service (typically via Docker), which adds deployment
complexity beyond a plain `pip install`. PyMuPDF was chosen as a pure-Python,
dependency-light middle ground that still meaningfully improves on plain-text
regex matching by exploiting real layout signals. If extraction accuracy
remains insufficient, GROBID is worth revisiting as a heavier, more accurate
alternative.
