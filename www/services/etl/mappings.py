"""
Mapping dictionaries for the Bibliometrix ETL pipeline.

Each dictionary maps the exact raw column names (as they appear in the
source file) to WoS-standard 2–3-letter tags.
- A value of None means "drop this column".
- Keys are case-sensitive and must match the actual file headers.

Public API
----------
    from www.services.etl.mappings import get_mapping, SOURCE_MAPPINGS
"""

import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scopus CSV export (scopus.com → Export → CSV, all fields)
# ---------------------------------------------------------------------------
SCOPUS_MAP: dict[str, str | None] = {
    "Authors":                          "AU",
    "Author full names":                "AF",
    "Author(s) ID":                     "AU_ID",
    "Title":                            "TI",
    "Year":                             "PY",
    "Source title":                     "SO",
    "Volume":                           "VL",
    "Issue":                            "IS",
    "Page start":                       "BP",
    "Page end":                         "EP",
    "Cited by":                         "TC",
    "DOI":                              "DI",
    "Affiliations":                     "C1",
    "Authors with affiliations":        "RP",
    "Abstract":                         "AB",
    "Author Keywords":                  "DE",
    "Index Keywords":                   "ID",
    "References":                       "CR",
    "Correspondence Address":           "RP",
    "Publisher":                        "PU",
    "ISSN":                             "SN",
    "PubMed ID":                        "PMID",
    "Language of Original Document":    "LA",
    "Abbreviated Source Title":         "JI",
    "Document Type":                    "DT",
    "EID":                              "UT",
    "Open Access":                      "OA",
    "Funding Details":                  "FU",
    "Funding Texts":                    "FX",
    # Drop these
    "Publication Stage":                None,
    "Source":                           None,
    "Art. No.":                         None,
    "Page count":                       None,
    "Link":                             None,
    "Molecular Sequence Numbers":       None,
    "Chemicals/CAS":                    None,
    "Tradenames":                       None,
    "Manufacturers":                    None,
    "Editors":                          None,
    "Sponsors":                         None,
    "Conference name":                  None,
    "Conference date":                  None,
    "Conference location":              None,
    "Conference code":                  None,
    "ISBN":                             None,
    "CODEN":                            None,
}

# ---------------------------------------------------------------------------
# Dimensions XLSX export (dimensions.ai → Export → Excel, skiprows=1)
# ---------------------------------------------------------------------------
DIMENSIONS_MAP: dict[str, str | None] = {
    # Derived columns created by the extractor before renaming
    "Authors_AU":                               "AU",
    "DIM_JI":                                   "JI",
    # Core fields
    "Publication ID":                           "UT",
    "Title":                                    "TI",
    "Abstract":                                 "AB",
    "Source title":                             "SO",
    "PubYear":                                  "PY",
    "Volume":                                   "VL",
    "Issue":                                    "IS",
    "Pagination":                               "BP",   # split → BP + EP
    "Authors":                                  "AF",
    "Corresponding Authors":                    "RP",
    "Authors Affiliations":                     "C1",
    "Authors (Raw Affiliation)":               "AU_UN",
    "DOI":                                      "DI",
    "Times cited":                              "TC",
    "Publication Type":                         "DT",
    "MeSH terms":                               "ID",
    "PMID":                                     "PMID",
    "Open Access":                              "OA",
    "Funding":                                  "FU",
    "Fields of Research (ANZSRC 2020)":        "SC",
    # Drop
    "Rank":                                     None,
    "PMCID":                                    None,
    "Acknowledgements":                         None,
    "Anthology title":                          None,
    "Book editors":                             None,
    "Publication date":                         None,
    "Publication date (online)":               None,
    "Publication date (print)":                None,
    "Recent citations":                         None,
    "RCR":                                      None,
    "FCR":                                      None,
    "Source Linkout":                           None,
    "Dimensions URL":                           None,
    "Sustainable Development Goals":            None,
}

# ---------------------------------------------------------------------------
# PubMed TXT export (pubmed.ncbi.nlm.nih.gov → Send to → File → PubMed)
# Keys are the 2–4-letter PubMed tags produced by parse_pubmed_data().
# ---------------------------------------------------------------------------
PUBMED_MAP: dict[str, str | None] = {
    "PMID":     "PMID",
    "TI":       "TI",
    "AB":       "AB",
    "FAU":      "AF",
    "AU":       "AU",
    "JT":       "SO",
    "TA":       "JI",
    "DP":       "PY",       # "2022 Feb 2" → extract first 4-digit year
    "VI":       "VL",
    "IP":       "IS",
    "PG":       "BP",       # "1-9" → split on "-" → BP + EP
    "AID":      "DI",       # filter lines with "[doi]" suffix
    "LA":       "LA",
    "PT":       "DT",
    "AD":       "C1",
    "MH":       "ID",
    "OT":       "DE",
    "IS":       "SN",
    "GR":       "FU",
    "AUID":     "AU_ID",
    # Drop
    "LID":      None,
    "OWN":      None,
    "STAT":     None,
    "DCOM":     None,
    "LR":       None,
    "RN":       None,
    "SB":       None,
    "PMC":      None,
    "EDAT":     None,
    "MHDA":     None,
    "CRDT":     None,
    "PHST":     None,
    "PST":      None,
    "SO":       None,       # PubMed SO is a combined citation string, not journal
    "IR":       None,
    "FIR":      None,
    "CN":       None,
    "EN":       None,
    "EM":       None,
    "COIS":     None,
}

# ---------------------------------------------------------------------------
# OpenAlex API JSON (after flattening by api_retriever._flatten_work)
# ---------------------------------------------------------------------------
OPENALEX_MAP: dict[str, str | None] = {
    "id":                   "UT",
    "doi":                  "DI",
    "title":                "TI",
    "publication_year":     "PY",
    "host_venue_name":      "SO",
    "host_venue_abbrev":    "JI",
    "cited_by_count":       "TC",
    "type":                 "DT",
    "language":             "LA",
    "biblio_volume":        "VL",
    "biblio_issue":         "IS",
    "biblio_first_page":    "BP",
    "biblio_last_page":     "EP",
    "authors":              "AU",
    "authors_full":         "AF",
    "affiliations":         "C1",
    "abstract":             "AB",
    "keywords":             "DE",
    "concepts":             "ID",
    "referenced_works":     "CR",
    "ids_pmid":             "PMID",
    "open_access_is_oa":    "OA",
}

# ---------------------------------------------------------------------------
# PubMed API (EFetch XML parsed to flat dict by api_retriever)
# ---------------------------------------------------------------------------
PUBMED_API_MAP: dict[str, str | None] = {
    "pmid":             "PMID",
    "title":            "TI",
    "abstract":         "AB",
    "journal_title":    "SO",
    "journal_abbrev":   "JI",
    "year":             "PY",
    "volume":           "VL",
    "issue":            "IS",
    "first_page":       "BP",
    "last_page":        "EP",
    "doi":              "DI",
    "language":         "LA",
    "pub_type":         "DT",
    "authors_abbrev":   "AU",
    "authors_full":     "AF",
    "affiliations":     "C1",
    "keywords":         "DE",
    "mesh_terms":       "ID",
    "references":       "CR",
    "grant_list":       "FU",
}

# ---------------------------------------------------------------------------
# WoS files already use WoS tags — no renaming needed
# ---------------------------------------------------------------------------
WOS_MAP: dict[str, str | None] = {}

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
SOURCE_MAPPINGS: dict[str, dict] = {
    "SCOPUS":     SCOPUS_MAP,
    "DIMENSIONS": DIMENSIONS_MAP,
    "PUBMED":     PUBMED_MAP,
    "OPENALEX":   OPENALEX_MAP,
    "PUBMED_API": PUBMED_API_MAP,
    "WOS":        WOS_MAP,
}


def get_mapping(source_name: str) -> dict[str, str | None]:
    """
    Returns the column-mapping dictionary for a given source.

    Args:
        source_name: One of 'SCOPUS', 'DIMENSIONS', 'PUBMED', 'OPENALEX',
                     'PUBMED_API', 'WOS'. Case-insensitive.

    Returns:
        dict mapping raw column names → WoS tags (None = drop).

    Raises:
        KeyError: If source_name is not recognised.
    """
    key = source_name.upper()
    if key not in SOURCE_MAPPINGS:
        raise KeyError(
            f"No mapping found for source '{source_name}'. "
            f"Supported sources: {list(SOURCE_MAPPINGS)}"
        )
    log.debug("get_mapping: returning map for '%s' (%d entries)", key, len(SOURCE_MAPPINGS[key]))
    return SOURCE_MAPPINGS[key]
