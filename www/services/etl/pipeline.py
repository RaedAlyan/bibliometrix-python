"""
Pipeline orchestrator — connects Extract → Transform → SR → Validate → Export.

Provides two high-level entry points:
  run_file_pipeline — for manually downloaded bibliographic files
  run_api_pipeline  — for API-based retrieval (OpenAlex / PubMed)

Both return a 3-tuple: (standardized_df, is_valid, errors).

Public API
----------
    from www.services.etl.pipeline import run_file_pipeline, run_api_pipeline

    df, ok, errors = run_file_pipeline("sources/Scopus/Scopus.csv")
    df, ok, errors = run_api_pipeline("machine learning", platform="openalex")
"""

import logging
import pandas as pd

from .extractor import extract_data
from .standardizer import standardize_dataframe
from .sr_generator import generate_sr
from .validator import validate_dataframe
from .exporter import export_to_csv

log = logging.getLogger(__name__)


def run_file_pipeline(
    file_path: str,
    source: str | None = None,
    output_path: str | None = None,
) -> tuple[pd.DataFrame, bool, list[str]]:
    """
    Runs the full ETL pipeline for a manually downloaded bibliographic file.

    Steps:
      1. EXTRACT  — detect source & load raw DataFrame
      2. TRANSFORM — rename columns, enforce types, generate SR
      3. VALIDATE — check schema completeness and type contracts
      4. EXPORT   — write CSV if output_path is given

    Args:
        file_path:   Path to the source file (.csv, .xlsx, .txt, .ciw).
        source:      Optional explicit source override. If None, auto-detected.
        output_path: If provided, write the standardized DataFrame to this CSV.

    Returns:
        (df, is_valid, errors)
        - df:       Standardized pd.DataFrame.
        - is_valid: True if all validation checks passed.
        - errors:   List of validation error strings ([] if is_valid).

    Raises:
        FileNotFoundError: If file_path does not exist.
        ValueError: If the source cannot be determined.
    """
    log.info("run_file_pipeline: starting — file='%s' source=%s", file_path, source)

    # 1. EXTRACT
    raw_df, detected_source = extract_data(file_path, source)
    log.info("run_file_pipeline: extracted %d records, source=%s", len(raw_df), detected_source)

    # 2. TRANSFORM
    df = standardize_dataframe(raw_df, detected_source)
    log.info("run_file_pipeline: standardized — %d rows, %d cols", len(df), len(df.columns))

    # 3. VALIDATE
    is_valid, errors = validate_dataframe(df)
    if is_valid:
        log.info("run_file_pipeline: validation passed")
    else:
        for err in errors:
            log.warning("run_file_pipeline: %s", err)

    # 4. EXPORT (optional)
    if output_path:
        path = export_to_csv(df, output_path)
        log.info("run_file_pipeline: exported to '%s'", path)

    return df, is_valid, errors


def run_api_pipeline(
    query: str,
    platform: str = "openalex",
    output_path: str | None = None,
    max_records: int = 100,
) -> tuple[pd.DataFrame, bool, list[str]]:
    """
    Runs the full ETL pipeline for API-based data retrieval.

    Steps:
      1. RETRIEVE — fetch records from OpenAlex or PubMed API
      2. TRANSFORM — rename columns, enforce types, generate SR
      3. VALIDATE — check schema completeness and type contracts
      4. EXPORT   — write CSV if output_path is given

    Args:
        query:       Search query string (e.g. "machine learning").
        platform:    'openalex' or 'pubmed_api'.
        output_path: If provided, write the standardized DataFrame to this CSV.
        max_records: Maximum number of records to retrieve.

    Returns:
        (df, is_valid, errors)

    Raises:
        ValueError: If platform is not recognised or query is empty.
    """
    if not query.strip():
        raise ValueError("query must not be empty")

    platform = platform.lower()
    if platform not in ("openalex", "pubmed_api"):
        raise ValueError(
            f"Unknown platform '{platform}'. Supported: 'openalex', 'pubmed_api'."
        )

    log.info("run_api_pipeline: starting — platform=%s query='%s' max=%d",
             platform, query, max_records)

    # 1. RETRIEVE
    from .api_retriever import fetch_openalex, fetch_pubmed  # noqa: PLC0415
    if platform == "openalex":
        raw_df = fetch_openalex(query, max_results=max_records)
        detected_source = "OPENALEX"
    else:
        raw_df = fetch_pubmed(query, max_results=max_records)
        detected_source = "PUBMED_API"
    log.info("run_api_pipeline: retrieved %d records", len(raw_df))

    raw_df = raw_df.head(max_records)

    # 2. TRANSFORM
    df = standardize_dataframe(raw_df, detected_source)

    # 3. VALIDATE
    is_valid, errors = validate_dataframe(df)
    if is_valid:
        log.info("run_api_pipeline: validation passed")
    else:
        for err in errors:
            log.warning("run_api_pipeline: %s", err)

    # 4. EXPORT (optional)
    if output_path:
        path = export_to_csv(df, output_path)
        log.info("run_api_pipeline: exported to '%s'", path)

    return df, is_valid, errors
