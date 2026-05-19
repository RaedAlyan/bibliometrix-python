# ETL Pipeline — Project Report

**Course:** Data Science 2025/2026  
**Professor:** Prof. Moscato  
**Student:** Raed Eleyan  
**Project:** bibliometrix-python — Source-Agnostic ETL Pipeline  

---

## Executive Summary

This project implements a complete Extract → Transform → Load (ETL) pipeline for the
`bibliometrix-python` Shiny dashboard, replicating the functionality of R's
`bibliometrix::convert2df()` function. The pipeline ingests bibliographic data from five
distinct sources and produces a unified Web of Science (WoS)-tagged DataFrame that all
downstream analytical functions can consume without modification.

---

## 1. Problem Statement

The existing `bibliometrix-python` dashboard operated reliably only with Web of Science
exports. Loading Scopus, Dimensions, or PubMed data required manual column renaming and
frequently crashed analytical functions due to type mismatches (strings where lists were
expected, missing columns, None values in numeric fields). The dashboard also provided no
mechanism for live API retrieval.

**Goal:** Make the dashboard fully source-agnostic by building a modular ETL layer that:
1. Accepts any of the five supported sources
2. Produces an identical schema regardless of source
3. Exposes a clean public API (`convert2df`, `run_file_pipeline`, `run_api_pipeline`)
4. Integrates transparently with the existing Shiny UI

---

## 2. Architecture

### 2.1 Package Structure

```
www/services/etl/
├── __init__.py       Public API re-exports
├── schema.py         WoS tag schema, type contracts, default values
├── mappings.py       Per-source column-name → WoS-tag dictionaries
├── extractor.py      File loading and source auto-detection
├── api_retriever.py  OpenAlex REST + NCBI E-utilities fetchers
├── standardizer.py   Rename → normalize → type-enforce pipeline
├── sr_generator.py   Short Reference (SR) field computation
├── validator.py      Schema completeness and type-contract checks
├── exporter.py       CSV serialization for list-valued columns
└── pipeline.py       High-level orchestrators (file + API)
```

### 2.2 Data Flow

```
Source File / API
       │
       ▼
  [extractor.py]          detect_source() + load_*(file_path)
       │  raw pd.DataFrame with original column names
       ▼
  [api_retriever.py]      fetch_openalex() / fetch_pubmed()  ← (API path only)
       │  raw flattened pd.DataFrame
       ▼
  [standardizer.py]
    ├─ rename_columns()         source-specific → WoS tags
    ├─ ensure_required_columns() fill missing with safe defaults
    ├─ normalize_scalar_fields() NaN → "", strip whitespace
    ├─ normalize_multi_value_fields() str → list[str]
    ├─ normalize_int / normalize_year  type enforcement
    ├─ sr_generator.generate_sr()     SR field
    └─ DB = source label
       │  standardized pd.DataFrame
       ▼
  [validator.py]          validate_dataframe() → (bool, list[str])
       │
       ▼
  [exporter.py]           export_to_csv() — list → ";" for CSV compat
```

### 2.3 Unified Schema

All 24 required columns use WoS 2–3 letter tags:

| Tag | Description | Type |
|-----|-------------|------|
| `DB` | Database source label | `str` |
| `UT` | Unique document ID | `str` |
| `DI` | DOI | `str` |
| `PMID` | PubMed ID | `str` |
| `TI` | Title | `str` |
| `SO` | Journal / Source title | `str` |
| `JI` | Abbreviated source title | `str` |
| `PY` | Publication year (4-digit) | `str` |
| `DT` | Document type | `str` |
| `LA` | Language | `str` |
| `TC` | Times cited | `int` |
| `AU` | Authors (abbreviated) | `list[str]` |
| `AF` | Authors (full name) | `list[str]` |
| `C1` | Author affiliations | `list[str]` |
| `RP` | Reprint / correspondence address | `str` |
| `CR` | Cited references | `list[str]` |
| `DE` | Author keywords | `list[str]` |
| `ID` | Index / MeSH keywords | `list[str]` |
| `AB` | Abstract | `str` |
| `VL` | Volume | `str` |
| `IS` | Issue | `str` |
| `BP` | Begin page | `str` |
| `EP` | End page | `str` |
| `SR` | Short reference key | `str` |

---

## 3. Implementation Details

### 3.1 Source Detection (`extractor.py`)

Detection is hierarchical and avoids reading entire files:

1. `.xlsx` extension → `DIMENSIONS`
2. `.csv` with `EID` column → `SCOPUS`; with `Publication ID` → `DIMENSIONS`
3. `.txt` first line starts with `FN ` → `WOS`; `PMID-` pattern → `PUBMED`
4. Raises `ValueError` with diagnostic message for unrecognized formats

### 3.2 Mapping Dictionaries (`mappings.py`)

Five dedicated dictionaries translate raw column names to WoS tags:

- **SCOPUS_MAP** (25 entries) — derived from actual `Scopus.csv` headers
- **DIMENSIONS_MAP** (22 entries) — derived from `Dimensions.xlsx` with custom preprocessing for `Pagination` split and abbreviated-author generation
- **PUBMED_MAP** (17 entries) — for MEDLINE-tagged `.txt` files; handles `DP` (date → year), `AID` (DOI extraction), `PG` (page range split)
- **OPENALEX_MAP** (21 entries) — for flattened JSON from the `/works` endpoint
- **PUBMED_API_MAP** (16 entries) — for EFetch XML parsed to flat dicts

### 3.3 Standardization (`standardizer.py`)

**Source-specific preprocessing** runs before generic renaming:
- `_preprocess_dimensions()` — generates abbreviated author strings, splits `Pagination` into `BP`/`EP`, creates `DIM_JI` proxy
- `_preprocess_pubmed()` — extracts 4-digit year from `DP`, extracts DOI from `AID`, splits `PG` for pages

**Normalization** then proceeds generically:
- `normalize_scalar_fields()` — converts all scalar cells to `str`, replacing `NaN`/`None` with `""`
- `normalize_multi_value_fields()` — parses delimited strings into `list[str]`; already-list cells are stripped/filtered
- `normalize_int()` — `pd.to_numeric(..., errors="coerce").fillna(0).astype(int)`
- `normalize_year()` — regex `\b(\d{4})\b` extraction

### 3.4 API Retrieval (`api_retriever.py`)

**OpenAlex** uses cursor-based pagination (`cursor=*` → `next_cursor`):
- Flattens nested JSON: `authorships[*].author.display_name` → `authors` list
- Reconstructs abstract from inverted index format
- Exponential backoff on HTTP 429 and 5xx responses

**PubMed** uses NCBI E-utilities in two phases:
- Phase 1: `ESearch` with `usehistory=y` stores result set on NCBI server
- Phase 2: `EFetch` in batches of 200, parses XML `MedlineCitation` elements
- Rate-limited to ~3 requests/second (0.35s sleep between batches)

### 3.5 Validation (`validator.py`)

Seven independent checks, all errors collected before returning:
1. All 24 required columns present
2. No `NaN` or `None` in any cell
3. Multi-value columns typed as `list` (not `str`)
4. Scalar mandatory columns typed as `str`
5. `TC` has integer dtype
6. `PY` matches `\d{4}` (when non-empty)
7. `DB` present and non-empty

### 3.6 SR Field (`sr_generator.py`)

Tries the existing `metatagextraction.SR()` function first (preserving compatibility with
the existing dashboard). Falls back to manual generation:
`"{FirstAuthor}, {PY}, {JI}"` with deduplication suffix `_a`, `_b`, `_c` for collisions.

---

## 4. App Integration

### Modified Files

| File | Change |
|------|--------|
| `app.py` | Added "1D" option to the data-source select; added API inputs (query, source, max_records); fixed `mostra()` to handle 1D directly without waiting for `input.Dataset`; changed `show_table()` to pure reactive with null guard |
| `functions/get_database.py` | Added `elif input.select() == "1D":` branch |
| `functions/get_data.py` | Added 1D block before `file is None` check; calls `run_api_pipeline()` |
| `functions/get_table.py` | Added null guard: `if data is None or data.empty: return early` |

---

## 5. Testing

### Test Suite (`tests/etl/`)

| File | Tests | Coverage |
|------|-------|----------|
| `test_mappings.py` | 12 | Source detection, key→value contracts, case-insensitivity, unknown-source error |
| `test_extractor.py` | 10 | Source auto-detection, file loading for all 3 file formats, null handling |
| `test_standardizer.py` | 13 | Year/int normalization, split_multi_value, full integration for each source |
| `test_validator.py` | 18 | Each validator function isolated; valid/invalid DataFrame cases |
| `test_exporter.py` | 10 | List serialization, CSV roundtrip, directory creation |
| `test_pipeline.py` | 12 | End-to-end file pipeline, API pipeline with mocked HTTP, error paths |
| **Total** | **75** | — |

### Running Tests

```bash
# With pytest installed in the project environment:
pytest tests/etl/ -v

# Syntax check only (no environment dependencies):
python3 -m py_compile www/services/etl/*.py tests/etl/*.py
```

---

## 6. CLI (`run_etl.py`)

```
# File mode
python run_etl.py --mode file --input sources/Scopus/Scopus.csv --output out/unified.csv
python run_etl.py --mode file --source DIMENSIONS --input sources/Dimensions/Dimensions.xlsx

# API mode  
python run_etl.py --mode api --platform openalex --query "machine learning" --max-records 200
python run_etl.py --mode api --platform pubmed_api --query "CRISPR therapy" --output out/crispr.csv
```

Exit codes: `0` = valid, `1` = input error, `2` = validation warnings.

---

## 7. Design Decisions

### Why WoS tags as the unified schema?
All existing analytical functions (`cocMatrix`, `metaTagExtraction`, `histNetwork`, etc.)
were written for WoS data and hard-code WoS tag names. Using WoS tags as the target schema
means zero changes to analytical code.

### Why keep `process_single_file()` intact?
The existing WoS/Scopus/PubMed file upload path in the dashboard uses `biblio_json()` and
`process_single_file()` and has been tested by users. The new ETL pipeline is an _additional_
entry point, not a replacement. The "1D" (API) path calls the new pipeline; the "1A" (file)
path preserves the original path.

### Why cursor-based pagination for OpenAlex?
OpenAlex deprecated offset-based pagination for large result sets. Cursor-based pagination
is the recommended approach and handles result sets of any size without deduplication issues.

### Why `usehistory=y` for PubMed?
Large result sets (>10k PMIDs) exceed URL length limits for direct PMID fetching.
The WebEnv/query_key approach stores results server-side and allows batched retrieval.

### Why does `DB = "ISI"` for OpenAlex?
The existing `metatagextraction.py` checks `M["DB"].iloc[0] in ["ISI", "OPENALEX"]` for
C3 field processing. Using `"ISI"` ensures OpenAlex data follows the WoS code path, which
is the most complete analytical path in the existing code.

---

## 8. Known Limitations

1. **Lens.org and Cochrane Library** are listed in the UI but not yet implemented (no sample files available to derive mappings).
2. **WoS file format** uses the existing `parse_wos_data()` parser which has its own column naming — the ETL pipeline preserves WoS column names as-is (identity mapping).
3. **Abstract reconstruction** from OpenAlex inverted index is exact but slow for large corpora (O(n·w) where w = words per abstract).
4. **Rate limiting** for OpenAlex and PubMed is handled with fixed sleeps; adaptive backoff based on `X-RateLimit-*` headers would be more robust.

---

## 9. File Manifest

```
www/services/etl/
├── __init__.py
├── schema.py
├── mappings.py
├── extractor.py
├── api_retriever.py
├── standardizer.py
├── sr_generator.py
├── validator.py
├── exporter.py
└── pipeline.py

tests/
├── __init__.py
└── etl/
    ├── __init__.py
    ├── test_mappings.py
    ├── test_extractor.py
    ├── test_standardizer.py
    ├── test_validator.py
    ├── test_exporter.py
    └── test_pipeline.py

notebooks/
└── etl_demo.ipynb

docs/
└── etl_project_report.md   ← this file

run_etl.py                   CLI entry point
```
