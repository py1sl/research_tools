from pdf_data_extract.reference_parsing import parse_reference, parse_references


def test_physics_style_with_arxiv():
    r = parse_reference(
        "A. Author, B. Author, and C. Van Der Berg, Phys. Rev. Lett. 99, "
        "123 (2007), arXiv:0705.1234."
    )
    assert r["authors"] == ["A. Author", "B. Author", "C. Van Der Berg"]
    assert (r["journal"], r["volume"], r["pages"], r["year"]) == (
        "Phys. Rev. Lett", "99", "123", 2007,
    )


def test_author_year_style():
    r = parse_reference(
        "Smith, J., Jones, K. (2019). First title. Journal of Things, 4, 1-10."
    )
    assert r == {
        "authors": ["Smith, J.", "Jones, K."],
        "title": "First title",
        "journal": "Journal of Things",
        "volume": "4",
        "pages": "1-10",
        "year": 2019,
    }


def test_title_and_et_al():
    r = parse_reference(
        "J. Doe et al., Some interesting result, Nucl. Phys. B 12, 34-56 (1999)."
    )
    assert r["authors"] == ["J. Doe", "et al."]
    assert r["title"] == "Some interesting result"
    assert r["journal"] == "Nucl. Phys. B"
    assert r["pages"] == "34-56"


def test_quoted_title_and_doi_ignored():
    r = parse_reference(
        'K. Lee and M. Park, "Quoted title," IEEE Trans. Nucl. Sci. 55, 100 '
        "(2008). https://doi.org/10.1109/TNS.2008.1"
    )
    assert r["title"] == "Quoted title"
    assert r["journal"] == "IEEE Trans. Nucl. Sci"
    assert r["year"] == 2008


def test_unparseable_text_gives_none_fields():
    r = parse_reference("")
    assert r["authors"] == [] and r["title"] is None and r["journal"] is None


def test_parse_references_keeps_original_keys():
    out = parse_references(
        [{"text": "A. Author. A paper title. Journal, 2020.", "doi": None,
          "year": 2020, "index": 1}]
    )
    assert out[0]["index"] == 1
    assert out[0]["authors"] == ["A. Author"]
    assert out[0]["title"] == "A paper title"
    assert out[0]["journal"] == "Journal"
