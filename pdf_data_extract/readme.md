# PDF Data Extraction Tools

This repository provides a set of tools designed for extracting data from PDF documents. These utilities form part of an ecosystem supporting research assistant agents, facilitating preprocessing steps to build databases or enable Retrieval-Augmented Generation (RAG). The tools may also be directly utilized by the agent itself.

## Overview

- **`extract_meta`**: Focuses on extracting metadata from PDF files.
- **`pdf_data_processing`**: Serves as the main controller and entry point for processing PDF data.
- **`reference_extraction`**: Targets extraction of reference sections from academic papers.
- **`structure_extraction`**: Extracts section headings, figure captions, and table captions.

All code is implemented in Python 3.12.

## Reference extraction

`extract_references(pdf_path)` returns a list of dictionaries from a PDF's
References, Bibliography, Works Cited, or Literature Cited section. Each
dictionary contains the normalized citation as `text` and the detected DOI as
`doi` (`None` when no DOI is present). Numbered citations and blank-line
separated citations are supported; PDFs without a recognized section return an
empty list.

## Structure extraction

- `extract_section_headings(pdf_path)` returns a list of dictionaries, each
  with a `number` (e.g. `"2.1"`, or `None` when unnumbered) and a `heading`
  string, for both numbered headings and common named sections (Abstract,
  Introduction, Methods, Results, Discussion, Conclusion, References, etc.).
- `extract_figure_captions(pdf_path)` returns a list of dictionaries, each
  with a `number` and `caption` string, for lines beginning with `Figure`/`Fig.`.
  Wrapped caption lines are joined; extraction stops at a blank line, a
  sentence ending, or a page boundary. If extracted figure numbers are not
  sequential, extraction retries with stricter caption boundaries.
- `extract_table_captions(pdf_path)` returns a list of dictionaries, each with
  a `number` and `caption` string, for lines beginning with `Table`. Captions
  spanning multiple lines are joined using the same boundaries as figure
  captions, including the sequential-number check and stricter retry.
- `extract_document_structure(pdf_path)` combines the three functions above
  into a single dictionary with `section_headings`, `figure_captions`, and
  `table_captions` keys.

PDFs without any recognizable headings or captions return empty lists.
