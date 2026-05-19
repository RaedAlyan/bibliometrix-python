"""
TRANSFORM phase — renames, cleans, and type-enforces bibliographic DataFrames.

This module applies the full transformation pipeline to a raw DataFrame:
  1. rename_columns        — map raw source names → WoS tags
  2. ensure_required_columns — fill any missing mandatory columns
  3. normalize_scalar_fields — clean strings (strip, NaN → "")
  4. normalize_multi_value_fields — parse delimited strings into list[str]
  5. Type enforcement: TC → int, PY → 4-digit str, DB → source string

Also exposes convert2df() as the single public entry point that orchestrates
the entire pipeline (Extract → Transform → SR → Validate → Return).

Public API
----------
    from www.services.etl.standardizer import convert2df, standardize_dataframe

    df = convert2df("sources/Scopus/Scopus.csv")
    df = convert2df(source="openalex", query="machine learning")
"""

import re
import logging
import warnings
import pandas as pd

from .schema import (
    REQUIRED_COLUMNS, MULTI_VALUE_COLUMNS, SCALAR_COLUMNS,
    INT_COLUMNS, DEFAULT_VALUES,
)
from .mappings import get_mapping

log = logging.getLogger(__name__)

# Delimiter candidates per multi-value field (tried in order)
_DELIMITERS: dict[str, list[str]] = {
    "AU":  [";", "|", " and "],
    "AF":  [";", "|"],
    "C1":  [";", "|"],
    "CR":  [";", "|", "\n"],
    "DE":  [";", "|"],
    "ID":  [";", "|"],
}

# DB values set per source
_SOURCE_TO_DB: dict[str, str] = {
    "SCOPUS":     "SCOPUS",
    "DIMENSIONS": "DIMENSIONS",
    "PUBMED":     "PUBMED",
    "PUBMED_API": "PUBMED",
    "OPENALEX":   "ISI",
    "WOS":        "ISI",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def convert2df(
    source: str,
    query: str | None = None,
    serialize_lists: bool = False,
) -> pd.DataFrame:
    """
    Main ETL entry point — Python equivalent of R's bibliometrix::convert2df().

    Orchestrates: EXTRACT → RENAME → NORMALIZE → TYPE → SR → VALIDATE → RETURN.

    Args:
        source:          File path for file-based sources, OR one of
                         'openalex' / 'pubmed_api' for API sources.
        query:           Search query string (API sources only).
        serialize_lists: If True, list columns are joined with ';' before
                         returning (for CSV export compatibility).

    Returns:
        Standardized pd.DataFrame.

    Raises:
        FileNotFoundError: source is a path and the file does not exist.
        ValueError: source cannot be identified.
    """
    src_lower = source.lower() if isinstance(source, str) else ""

    # ── EXTRACT ──────────────────────────────────────────────────────────────
    if src_lower in ("openalex", "pubmed_api"):
        if not query:
            raise ValueError(f"A 'query' string is required for API source '{source}'.")
        raw_df, detected = _extract_api(src_lower, query)
    else:
        from .extractor import extract_data  # noqa: PLC0415
        raw_df, detected = extract_data(source)

    log.info("convert2df: extracted %d rows, source=%s", len(raw_df), detected)

    # ── TRANSFORM ────────────────────────────────────────────────────────────
    df = standardize_dataframe(raw_df, detected)

    # ── VALIDATE ─────────────────────────────────────────────────────────────
    from .validator import validate_dataframe  # noqa: PLC0415
    is_valid, errors = validate_dataframe(df)
    if not is_valid:
        for err in errors:
            log.warning("convert2df validation: %s", err)
        warnings.warn(
            f"ETL validation found {len(errors)} issue(s). DataFrame returned anyway.",
            stacklevel=2,
        )

    # ── SERIALIZE (optional) ─────────────────────────────────────────────────
    if serialize_lists:
        from .exporter import serialize_list_columns  # noqa: PLC0415
        df = serialize_list_columns(df)

    return df


def standardize_dataframe(raw_df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Applies the full transformation pipeline to a raw DataFrame.

    Steps: rename → source-specific preprocessing → ensure columns →
           normalize scalars → normalize multi-value → type-enforce → SR → DB.

    Args:
        raw_df: Raw DataFrame with original source column names.
        source: Detected source string ('SCOPUS', 'DIMENSIONS', etc.).

    Returns:
        Fully standardized DataFrame.
    """
    df = raw_df.copy()

    # Source-specific pre-processing before generic renaming
    if source == "DIMENSIONS":
        df = _preprocess_dimensions(df)
    elif source == "PUBMED":
        df = _preprocess_pubmed(df)

    df = rename_columns(df, source)
    df = ensure_required_columns(df)
    df = normalize_scalar_fields(df)
    df = normalize_multi_value_fields(df)

    # Type enforcement
    for col in INT_COLUMNS:
        if col in df.columns:
            df[col] = normalize_int(df[col])
    if "PY" in df.columns:
        df["PY"] = df["PY"].apply(normalize_year)

    # DB field
    df["DB"] = _SOURCE_TO_DB.get(source, source)

    # SR field
    from .sr_generator import generate_sr  # noqa: PLC0415
    df = generate_sr(df)

    # Final fill
    df = ensure_required_columns(df)
    df = df.reset_index(drop=True)

    log.info("standardize_dataframe: done — %d rows, %d cols", len(df), len(df.columns))
    return df


# ---------------------------------------------------------------------------
# Step functions
# ---------------------------------------------------------------------------

def rename_columns(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Renames raw source columns to WoS tags using the appropriate mapping dict.

    Drops columns whose mapping value is None or that have no mapping entry.
    Deduplicates columns where two source cols map to the same WoS tag
    by coalescing (first non-null value wins).

    Args:
        df:     Raw DataFrame with original source column names.
        source: Source identifier (used to look up the mapping dict).

    Returns:
        DataFrame with WoS-tagged column names.
    """
    mapping = get_mapping(source)
    df = df.copy()

    cols_to_drop = [c for c, t in mapping.items() if t is None and c in df.columns]
    df = df.drop(columns=cols_to_drop, errors="ignore")

    rename_dict = {c: t for c, t in mapping.items() if t is not None and c in df.columns}
    df = df.rename(columns=rename_dict)

    # Keep only columns that appear as values in the mapping (+ EP added by preprocessing)
    keep = set(v for v in mapping.values() if v is not None) | {"EP"}
    df = df[[c for c in df.columns if c in keep]]

    # Coalesce duplicate columns (e.g. two Scopus cols → "RP")
    if df.columns.duplicated().any():
        dedup: dict[str, pd.Series] = {}
        seen: set[str] = set()
        for col in df.columns:
            if col not in seen:
                seen.add(col)
                group = df.loc[:, df.columns == col]
                if group.shape[1] > 1:
                    dedup[col] = group.apply(
                        lambda row: next((v for v in row if pd.notna(v) and v != ""), row.iloc[0]),
                        axis=1,
                    )
                else:
                    dedup[col] = group.iloc[:, 0]
        df = pd.DataFrame(dedup)

    df = df.reset_index(drop=True)
    return df


def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds any missing required columns with safe default values.

    Defaults: list columns → [], TC → 0, all others → "".

    Args:
        df: DataFrame to fill.

    Returns:
        DataFrame with all REQUIRED_COLUMNS present.
    """
    df = df.copy()
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            default = DEFAULT_VALUES.get(col, "")
            if isinstance(default, list):
                df[col] = [list() for _ in range(len(df))]
            else:
                df[col] = default
    return df


def normalize_scalar_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts all scalar (non-list, non-int) columns to clean strings.

    Replaces NaN / None / float-nan with "".

    Args:
        df: DataFrame after renaming.

    Returns:
        DataFrame with string scalars and no NaN in scalar columns.
    """
    df = df.copy()
    for col in SCALAR_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(_to_str)
    return df


def normalize_multi_value_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts delimited-string columns to list[str].

    Already-list cells are stripped and filtered; NaN/None → [].

    Args:
        df: DataFrame after scalar normalization.

    Returns:
        DataFrame with list[str] in all MULTI_VALUE_COLUMNS that are present.
    """
    df = df.copy()
    for col in MULTI_VALUE_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: split_multi_value(x, col))
    return df


def split_multi_value(value, column_name: str | None = None) -> list[str]:
    """
    Parses a raw cell value into list[str].

    - Already a list → strip each element, filter empty.
    - NaN / None / empty string → [].
    - Otherwise try delimiters in _DELIMITERS[column_name] order.

    Args:
        value:       Raw cell value.
        column_name: WoS tag used to select delimiters (optional).

    Returns:
        list[str]
    """
    if isinstance(value, list):
        return [str(e).strip() for e in value if str(e).strip()]

    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass

    if value is None:
        return []

    s = str(value).strip()
    if not s or s.lower() in ("nan", "none"):
        return []

    delimiters = _DELIMITERS.get(column_name or "", [";"])
    for d in delimiters:
        parts = s.split(d)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]

    return [s]


def normalize_year(value) -> str:
    """
    Extracts a 4-digit year from a date/year value.

    Examples:
        "2022 Feb 2" → "2022"
        2024         → "2024"
        ""           → ""

    Args:
        value: Raw year/date value.

    Returns:
        4-digit year string or "".
    """
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    m = re.search(r"\b(\d{4})\b", s)
    return m.group(1) if m else (s if s else "")


def normalize_int(series: pd.Series) -> pd.Series:
    """
    Casts a Series to int, replacing non-numeric values with 0.

    Args:
        series: Raw numeric series.

    Returns:
        pd.Series of dtype int.
    """
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


# ---------------------------------------------------------------------------
# Source-specific pre-processing
# ---------------------------------------------------------------------------

def _preprocess_dimensions(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-processes a raw Dimensions DataFrame before generic renaming."""
    df = df.copy()

    # Abbreviated AU from "Authors" ("Surname, Name; ..." → "Surname Initials")
    if "Authors" in df.columns:
        def _abbrev(val):
            if pd.isna(val) or not str(val).strip():
                return ""
            names = []
            for person in str(val).split("; "):
                person = person.strip()
                if not person:
                    continue
                parts = person.split(", ", 1)
                if len(parts) == 2:
                    initials = "".join(p[0].upper() for p in parts[1].split() if p)
                    names.append(f"{parts[0].strip()} {initials}")
                elif parts[0]:
                    names.append(parts[0])
            return "; ".join(names)

        df["Authors_AU"] = df["Authors"].apply(_abbrev)

    # JI proxy from "Source title" (Dimensions has no abbreviation column)
    if "Source title" in df.columns:
        df["DIM_JI"] = df["Source title"].astype(str).str.upper().str.strip()

    # Split "Pagination" ("1-9") → BP + EP
    if "Pagination" in df.columns:
        def _split_pages(val):
            s = str(val).strip() if pd.notna(val) else ""
            parts = s.split("-", 1)
            return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")

        split = df["Pagination"].apply(_split_pages)
        df["Pagination"] = split.apply(lambda t: t[0])
        df["EP"] = split.apply(lambda t: t[1])

    return df


def _preprocess_pubmed(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-processes a raw PubMed DataFrame before generic renaming."""
    df = df.copy()

    if "DP" in df.columns:
        df["DP"] = df["DP"].apply(normalize_year)

    if "AID" in df.columns:
        df["AID"] = df["AID"].apply(_extract_doi_from_aid)

    if "PG" in df.columns:
        def _split_pg(val):
            s = str(val).strip() if pd.notna(val) else ""
            parts = s.split("-", 1)
            return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")

        split = df["PG"].apply(_split_pg)
        df["PG"] = split.apply(lambda t: t[0])
        df["EP"] = split.apply(lambda t: t[1])

    if "PMID" in df.columns:
        df["PMID"] = df["PMID"].astype(str).str.strip()

    return df


def _extract_doi_from_aid(val) -> str:
    """Extracts DOI from a PubMed AID field (looks for [doi] suffix)."""
    if pd.isna(val) or val is None:
        return ""
    for part in str(val).split(";"):
        part = part.strip()
        if part.lower().endswith("[doi]"):
            return part[:-len("[doi]")].strip()
    return ""


def _extract_api(source_key: str, query: str) -> tuple[pd.DataFrame, str]:
    """Routes to the appropriate API retriever."""
    from .api_retriever import fetch_openalex, fetch_pubmed  # noqa: PLC0415
    if source_key == "openalex":
        return fetch_openalex(query), "OPENALEX"
    elif source_key == "pubmed_api":
        return fetch_pubmed(query), "PUBMED_API"
    else:
        raise ValueError(f"Unknown API source: '{source_key}'")


def _to_str(x) -> str:
    """Converts any value to a clean string; NaN/None → ''."""
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(x).strip()
    return "" if s.lower() in ("nan", "none") else s
