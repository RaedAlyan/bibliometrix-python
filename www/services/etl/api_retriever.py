"""
API RETRIEVE phase — fetches bibliographic records from OpenAlex and PubMed.

Handles pagination, rate limiting, and retries with exponential backoff.
Returns raw (untransformed) pd.DataFrames ready for the standardizer.

Public API
----------
    from www.services.etl.api_retriever import fetch_openalex, fetch_pubmed
"""

import time
import logging
import pandas as pd
import requests
from xml.etree import ElementTree as ET

log = logging.getLogger(__name__)

OPENALEX_BASE  = "https://api.openalex.org/works"
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_TIMEOUT       = 30
_BATCH         = 200


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------

def fetch_openalex(
    query: str,
    max_results: int = 1000,
    retries: int = 3,
    sleep_between_pages: float = 0.5,
) -> pd.DataFrame:
    """
    Fetches works from the OpenAlex REST API using cursor-based pagination.

    Args:
        query:               Free-text search query.
        max_results:         Maximum number of records to retrieve.
        retries:             Retry attempts per page on HTTP 5xx errors.
        sleep_between_pages: Seconds to wait between page requests.

    Returns:
        Raw pd.DataFrame with flattened OpenAlex field names.
    """
    records: list[dict] = []
    cursor = "*"
    per_page = min(200, max_results)

    while len(records) < max_results:
        params = {
            "search": query,
            "per-page": per_page,
            "cursor": cursor,
            "mailto": "bibliometrix@example.com",
        }
        resp = _get_with_retry(OPENALEX_BASE, params, retries)
        if resp is None:
            break

        data = resp.json()
        page_works = data.get("results", [])
        if not page_works:
            break

        for work in page_works:
            records.append(_flatten_work(work))
            if len(records) >= max_results:
                break

        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor:
            break

        time.sleep(sleep_between_pages)

    log.info("fetch_openalex: retrieved %d records for query='%s'", len(records), query)
    return pd.DataFrame(records)


def _flatten_work(work: dict) -> dict:
    """Flattens a single OpenAlex work JSON object into a flat dict."""
    hv    = work.get("primary_location") or work.get("host_venue") or {}
    venue = hv.get("source") or hv.get("journal") or hv if isinstance(hv, dict) else {}
    bib   = work.get("biblio") or {}
    ids   = work.get("ids") or {}

    # Authors
    authorships = work.get("authorships") or []
    authors, authors_full, affiliations = [], [], []
    for a in authorships:
        author = a.get("author") or {}
        display = author.get("display_name") or ""
        parts = display.split(" ", 1)
        if len(parts) == 2:
            abbrev = f"{parts[-1]} {parts[0][0].upper()}"
        else:
            abbrev = display
        authors.append(abbrev)
        authors_full.append(display)
        for inst in (a.get("institutions") or []):
            affiliations.append(inst.get("display_name") or "")

    # Keywords
    keywords = [kw.get("display_name", "") for kw in (work.get("keywords") or [])]
    concepts = [c.get("display_name", "") for c in (work.get("concepts") or [])]

    # Abstract
    inv = work.get("abstract_inverted_index") or {}
    abstract = _reconstruct_abstract(inv)

    pmid = ids.get("pmid") or ""
    if pmid:
        pmid = str(pmid).replace("https://pubmed.ncbi.nlm.nih.gov/", "").strip("/")

    return {
        "id":                 work.get("id", ""),
        "doi":                (work.get("doi") or "").replace("https://doi.org/", ""),
        "title":              work.get("title") or "",
        "publication_year":   str(work.get("publication_year") or ""),
        "host_venue_name":    venue.get("display_name") or "",
        "host_venue_abbrev":  venue.get("abbreviated_title") or "",
        "cited_by_count":     work.get("cited_by_count") or 0,
        "type":               work.get("type") or "",
        "language":           work.get("language") or "",
        "biblio_volume":      bib.get("volume") or "",
        "biblio_issue":       bib.get("issue") or "",
        "biblio_first_page":  bib.get("first_page") or "",
        "biblio_last_page":   bib.get("last_page") or "",
        "authors":            authors,
        "authors_full":       authors_full,
        "affiliations":       affiliations,
        "abstract":           abstract,
        "keywords":           keywords,
        "concepts":           concepts,
        "referenced_works":   work.get("referenced_works") or [],
        "ids_pmid":           pmid,
        "open_access_is_oa":  str((work.get("open_access") or {}).get("is_oa", False)),
    }


def _reconstruct_abstract(inverted_index: dict) -> str:
    """Reconstructs abstract text from OpenAlex inverted-index format."""
    if not inverted_index:
        return ""
    positions: dict[int, str] = {}
    for word, pos_list in inverted_index.items():
        for p in pos_list:
            positions[p] = word
    return " ".join(positions[i] for i in sorted(positions))


# ---------------------------------------------------------------------------
# PubMed (E-utilities)
# ---------------------------------------------------------------------------

def fetch_pubmed(
    query: str,
    max_results: int = 1000,
    retries: int = 3,
) -> pd.DataFrame:
    """
    Fetches articles from PubMed via NCBI E-utilities (ESearch + EFetch XML).

    Phase 1 — ESearch with usehistory=y: stores results on NCBI server.
    Phase 2 — EFetch in batches of 200: parses XML into flat dicts.

    Args:
        query:       Search query string.
        max_results: Maximum number of records to retrieve.
        retries:     Retry attempts per batch.

    Returns:
        Raw pd.DataFrame with PUBMED_API_MAP-compatible field names.
    """
    # Phase 1: ESearch
    search_params = {
        "db": "pubmed", "term": query, "usehistory": "y",
        "retmax": 0, "retmode": "json",
    }
    resp = _get_with_retry(PUBMED_ESEARCH, search_params, retries)
    if resp is None:
        return pd.DataFrame()

    search_data = resp.json().get("esearchresult", {})
    count = int(search_data.get("count", 0))
    web_env = search_data.get("webenv", "")
    query_key = search_data.get("querykey", "")

    if count == 0:
        log.info("fetch_pubmed: no results for query='%s'", query)
        return pd.DataFrame()

    total = min(count, max_results)
    records: list[dict] = []

    # Phase 2: EFetch in batches
    for start in range(0, total, _BATCH):
        batch_size = min(_BATCH, total - start)
        fetch_params = {
            "db": "pubmed", "query_key": query_key, "WebEnv": web_env,
            "retstart": start, "retmax": batch_size,
            "rettype": "xml", "retmode": "xml",
        }
        resp = _get_with_retry(PUBMED_EFETCH, fetch_params, retries)
        if resp is None:
            continue
        records.extend(_parse_efetch_xml(resp.text))
        time.sleep(0.35)

    log.info("fetch_pubmed: retrieved %d records for query='%s'", len(records), query)
    return pd.DataFrame(records)


def _parse_efetch_xml(xml_text: str) -> list[dict]:
    """Parses a PubMed EFetch XML response into a list of flat dicts."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        log.warning("_parse_efetch_xml: XML parse error — %s", exc)
        return []
    return [
        _parse_pubmed_record(citation)
        for citation in root.findall(".//MedlineCitation")
    ]


def _parse_pubmed_record(citation: ET.Element) -> dict:
    """Extracts fields from a single MedlineCitation XML element."""
    def _text(elem, path, default=""):
        node = elem.find(path)
        return node.text.strip() if node is not None and node.text else default

    def _texts(elem, path):
        return [n.text.strip() for n in elem.findall(path) if n.text]

    _found = citation.find("Article")
    article = _found if _found is not None else ET.Element("dummy")
    _found = article.find("Journal")
    journal = _found if _found is not None else ET.Element("dummy")
    _found = journal.find("JournalIssue")
    ji_elem = _found if _found is not None else ET.Element("dummy")

    # Publication year
    year = _text(ji_elem, "PubDate/Year")
    if not year:
        import re
        md = _text(ji_elem, "PubDate/MedlineDate")
        m = re.search(r"\b(\d{4})\b", md)
        year = m.group(1) if m else ""

    # Authors
    authors_abbrev, authors_full, affiliations = [], [], []
    for author in citation.findall(".//Author"):
        last  = _text(author, "LastName")
        fore  = _text(author, "ForeName")
        inits = _text(author, "Initials")
        if last:
            authors_abbrev.append(f"{last} {inits}".strip())
            authors_full.append(f"{last} {fore}".strip() if fore else last)
        for aff in author.findall("AffiliationInfo/Affiliation"):
            if aff.text:
                affiliations.append(aff.text.strip())

    # Keywords
    keywords  = _texts(citation, ".//KeywordList/Keyword")
    mesh      = _texts(citation, ".//MeshHeadingList/MeshHeading/DescriptorName")

    # DOI
    doi = ""
    for loc_id in citation.findall(".//ArticleIdList/ArticleId"):
        if loc_id.get("IdType") == "doi" and loc_id.text:
            doi = loc_id.text.strip()
            break

    # References
    refs = []
    for ref in citation.findall(".//ReferenceList/Reference"):
        cit_text = _text(ref, "Citation")
        if cit_text:
            refs.append(cit_text)

    pmid_node = citation.find("PMID")
    pmid = pmid_node.text.strip() if pmid_node is not None and pmid_node.text else ""

    return {
        "pmid":           pmid,
        "title":          _text(article, "ArticleTitle"),
        "abstract":       " ".join(_texts(article, "Abstract/AbstractText")),
        "journal_title":  _text(journal, "Title"),
        "journal_abbrev": _text(journal, "ISOAbbreviation"),
        "year":           year,
        "volume":         _text(ji_elem, "Volume"),
        "issue":          _text(ji_elem, "Issue"),
        "first_page":     _text(article, "Pagination/MedlinePgn").split("-")[0],
        "last_page":      (
            _text(article, "Pagination/MedlinePgn").split("-")[1]
            if "-" in _text(article, "Pagination/MedlinePgn") else ""
        ),
        "doi":            doi,
        "language":       _text(citation, "Article/Language"),
        "pub_type":       "; ".join(_texts(article, "PublicationTypeList/PublicationType")),
        "authors_abbrev": authors_abbrev,
        "authors_full":   authors_full,
        "affiliations":   affiliations,
        "keywords":       keywords,
        "mesh_terms":     mesh,
        "references":     refs,
        "grant_list":     "; ".join(_texts(citation, ".//GrantList/Grant/GrantID")),
    }


# ---------------------------------------------------------------------------
# Shared HTTP helper
# ---------------------------------------------------------------------------

def _get_with_retry(
    url: str,
    params: dict,
    retries: int,
) -> requests.Response | None:
    """GET with exponential backoff on 429 / 5xx responses."""
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=_TIMEOUT)
            if resp.status_code == 200:
                return resp
            if resp.status_code == 429:
                wait = 2 ** attempt
                log.warning("_get_with_retry: 429 rate-limited — waiting %ds", wait)
                time.sleep(wait)
            elif resp.status_code >= 500:
                wait = 2 ** attempt
                log.warning("_get_with_retry: HTTP %d — retry %d/%d in %ds",
                            resp.status_code, attempt + 1, retries, wait)
                time.sleep(wait)
            else:
                log.error("_get_with_retry: HTTP %d — not retrying", resp.status_code)
                return None
        except requests.RequestException as exc:
            log.warning("_get_with_retry: request failed (%s) — retry %d/%d",
                        exc, attempt + 1, retries)
            time.sleep(2 ** attempt)
    log.error("_get_with_retry: all %d retries exhausted for %s", retries, url)
    return None
