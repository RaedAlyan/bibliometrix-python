"""
EXTRACT phase — loads raw bibliographic files into DataFrames.

Every loader returns a raw (untransformed) pd.DataFrame with original column
names intact. No column renaming or type coercion is performed here.

Public API
----------
    from www.services.etl.extractor import extract_data

    raw_df, detected_source = extract_data("sources/Scopus/Scopus.csv")
    raw_df, _               = extract_data("sources/Dimensions/Dimensions.xlsx", source="DIMENSIONS")
"""

import os
import logging
import pandas as pd

log = logging.getLogger(__name__)

# Sentinel values used for source detection
_SCOPUS_SENTINEL     = "EID"
_DIMENSIONS_SENTINEL = "Publication ID"
_WOS_FIRST_LINE      = "FN "
_PUBMED_FIRST_LINE   = "PMID-"


# ---------------------------------------------------------------------------
# Individual loaders
# ---------------------------------------------------------------------------

def load_scopus_csv(file_path: str) -> pd.DataFrame:
    """
    Loads a Scopus CSV export into a raw DataFrame.

    Args:
        file_path: Path to the Scopus .csv file.

    Returns:
        Raw pd.DataFrame with original Scopus column names.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file appears empty.
    """
    _assert_exists(file_path)
    df = pd.read_csv(file_path, low_memory=False)
    _assert_nonempty(df, file_path)
    log.info("load_scopus_csv: %d records from '%s'", len(df), file_path)
    return df


def load_dimensions_excel(file_path: str) -> pd.DataFrame:
    """
    Loads a Dimensions XLSX export into a raw DataFrame.

    Dimensions exports have a title row at row 0; actual headers are at row 1.

    Args:
        file_path: Path to the Dimensions .xlsx or .csv file.

    Returns:
        Raw pd.DataFrame with original Dimensions column names.
    """
    _assert_exists(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".xlsx":
        df = pd.read_excel(file_path, skiprows=1)
    else:
        df = pd.read_csv(file_path, skiprows=1, low_memory=False)
    _assert_nonempty(df, file_path)
    log.info("load_dimensions_excel: %d records from '%s'", len(df), file_path)
    return df


def load_pubmed_txt(file_path: str) -> pd.DataFrame:
    """
    Loads a PubMed TXT export (MEDLINE format) into a raw DataFrame.

    Delegates to the existing parse_pubmed_data() parser already present in
    www/services/parsers.py.

    Args:
        file_path: Path to the PubMed .txt file.

    Returns:
        Raw pd.DataFrame with PubMed 2–4-letter field tags as columns.
    """
    _assert_exists(file_path)
    from ..parsers import parse_pubmed_data  # noqa: PLC0415
    records = parse_pubmed_data(file_path)
    df = pd.DataFrame(records)
    _assert_nonempty(df, file_path)
    log.info("load_pubmed_txt: %d records from '%s'", len(df), file_path)
    return df


def load_wos_txt(file_path: str) -> pd.DataFrame:
    """
    Loads a Web of Science TXT/CIW export into a raw DataFrame.

    Delegates to the existing parse_wos_data() parser.

    Args:
        file_path: Path to the WoS .txt or .ciw file.

    Returns:
        Raw pd.DataFrame with WoS field tags as columns (already WoS-tagged).
    """
    _assert_exists(file_path)
    from ..parsers import parse_wos_data  # noqa: PLC0415
    records = parse_wos_data(file_path)
    df = pd.DataFrame(records)
    _assert_nonempty(df, file_path)
    log.info("load_wos_txt: %d records from '%s'", len(df), file_path)
    return df


def load_generic_csv(file_path: str) -> pd.DataFrame:
    """
    Loads any CSV file. Falls back for unknown CSV sources.

    Args:
        file_path: Path to a CSV file.

    Returns:
        Raw pd.DataFrame.
    """
    _assert_exists(file_path)
    df = pd.read_csv(file_path, low_memory=False)
    _assert_nonempty(df, file_path)
    log.info("load_generic_csv: %d records from '%s'", len(df), file_path)
    return df


def load_generic_excel(file_path: str) -> pd.DataFrame:
    """
    Loads any Excel file. Falls back for unknown Excel sources.

    Args:
        file_path: Path to an Excel file.

    Returns:
        Raw pd.DataFrame.
    """
    _assert_exists(file_path)
    df = pd.read_excel(file_path)
    _assert_nonempty(df, file_path)
    log.info("load_generic_excel: %d records from '%s'", len(df), file_path)
    return df


# ---------------------------------------------------------------------------
# Source detection
# ---------------------------------------------------------------------------

def detect_source(file_path: str) -> str:
    """
    Infers the bibliographic source from file extension and sentinel content.

    Detection strategy:
    1. .xlsx → DIMENSIONS
    2. .csv  → read header; 'EID' → SCOPUS; 'Publication ID' → DIMENSIONS
    3. .txt / .ciw → read first line; 'FN ' → WOS; 'PMID-' → PUBMED

    Args:
        file_path: Path to the file to inspect.

    Returns:
        One of: 'SCOPUS', 'DIMENSIONS', 'PUBMED', 'WOS'.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the source cannot be determined.
    """
    _assert_exists(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".xlsx":
        return "DIMENSIONS"

    if ext == ".bib":
        return "WOS"

    if ext == ".csv":
        try:
            header = pd.read_csv(file_path, nrows=0)
            if _SCOPUS_SENTINEL in header.columns:
                return "SCOPUS"
            if _DIMENSIONS_SENTINEL in header.columns:
                return "DIMENSIONS"
        except Exception as exc:
            log.warning("detect_source: could not read CSV header: %s", exc)
        raise ValueError(
            f"Cannot determine source from CSV '{file_path}'. "
            f"Expected '{_SCOPUS_SENTINEL}' (Scopus) or "
            f"'{_DIMENSIONS_SENTINEL}' (Dimensions) in header."
        )

    if ext in (".txt", ".ciw"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    stripped = line.strip()
                    if stripped:
                        if stripped.startswith(_WOS_FIRST_LINE):
                            return "WOS"
                        if stripped.startswith(_PUBMED_FIRST_LINE):
                            return "PUBMED"
                        break
        except Exception as exc:
            log.warning("detect_source: could not read TXT header: %s", exc)
        raise ValueError(
            f"Cannot determine source from '{file_path}'. "
            f"First line must start with '{_WOS_FIRST_LINE}' (WoS) "
            f"or '{_PUBMED_FIRST_LINE}' (PubMed)."
        )

    raise ValueError(
        f"Unsupported file extension '{ext}'. "
        f"Supported: .csv, .xlsx, .txt, .ciw, .bib"
    )


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

def extract_data(file_path: str, source: str | None = None) -> tuple[pd.DataFrame, str]:
    """
    Detects the source (if not provided) and loads the file into a raw DataFrame.

    Args:
        file_path: Absolute or relative path to the bibliographic file.
        source:    Optional explicit source override ('SCOPUS', 'DIMENSIONS',
                   'PUBMED', 'WOS'). If None, auto-detected.

    Returns:
        (raw_df, source_string) where source_string is the detected/provided source.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the source cannot be determined or is unsupported.
    """
    if source is None:
        source = detect_source(file_path)
    source = source.upper()

    loader_map = {
        "SCOPUS":     load_scopus_csv,
        "DIMENSIONS": load_dimensions_excel,
        "PUBMED":     load_pubmed_txt,
        "WOS":        load_wos_txt,
    }

    if source not in loader_map:
        raise ValueError(
            f"Unsupported source '{source}'. "
            f"Supported: {list(loader_map)}"
        )

    raw_df = loader_map[source](file_path)
    return raw_df, source


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _assert_exists(path: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: '{path}'")


def _assert_nonempty(df: pd.DataFrame, path: str) -> None:
    if df.empty:
        raise ValueError(f"File '{path}' loaded as an empty DataFrame.")
