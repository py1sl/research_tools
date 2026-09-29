# PDF Data Extraction Tools

This repository provides a set of tools designed for extracting data from PDF documents. These utilities form part of an ecosystem supporting research assistant agents, facilitating preprocessing steps to build databases or enable Retrieval-Augmented Generation (RAG). The tools may also be directly utilized by the agent itself.

## Overview

- **`extract_meta`**: Focuses on extracting metadata from PDF files.
- **`pdf_data_processing`**: Serves as the main controller and entry point for processing PDF data.
- **`reference_extraction`**: Targets extraction of reference sections from academic papers.

All code is implemented in Python 3.12.

## Reference extraction

`extract_references(pdf_path)` returns a list of dictionaries from a PDF's
References, Bibliography, Works Cited, or Literature Cited section. Each
dictionary contains the normalized citation as `text` and the detected DOI as
`doi` (`None` when no DOI is present). Numbered citations and blank-line
separated citations are supported; PDFs without a recognized section return an
empty list.
