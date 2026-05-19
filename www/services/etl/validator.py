"""
VALIDATE phase — checks the standardized DataFrame against the WoS schema.

All checks are collected before returning — the function never fails on the
first error but reports all issues at once.

Public API
----------
    from www.services.etl.validator import validate_dataframe, ensure_required_columns

    is_valid, errors = validate_dataframe(df)
"""

import logging
import pandas as pd

from .schema import REQUIRED_COLUMNS, MULTI_VALUE_COLUMNS, INT_COLUMNS, SCALAR_COLUMNS

log = logging.getLogger(__name__)


def validate_dataframe(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    Validates the final DataFrame against the mandatory WoS schema.

    Runs all sub-checks and collects every error before returning.

    Args:
        df: The standardized DataFrame to validate.

    Returns:
        (is_valid, errors) — errors is [] when is_valid is True.
    """
    errors: list[str] = []
    errors += validate_required_columns(df)
    errors += validate_no_nulls(df)
    errors += validate_multi_value_columns(df)
    errors += validate_scalar_columns(df)
    errors += validate_numeric_columns(df)
    errors += validate_year_column(df)
    errors += validate_database_column(df)

    is_valid = len(errors) == 0
    if is_valid:
        log.debug("validate_dataframe: all checks passed")
    else:
        log.warning("validate_dataframe: %d issue(s) found", len(errors))
    return is_valid, errors


def validate_required_columns(df: pd.DataFrame) -> list[str]:
    """Checks that all REQUIRED_COLUMNS are present."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return [f"Missing mandatory columns: {missing}"] if missing else []


def validate_no_nulls(df: pd.DataFrame) -> list[str]:
    """Checks that no cell contains NaN or None."""
    errors = []
    for col in df.columns:
        try:
            if df[col].apply(_has_null).any():
                errors.append(f"Column '{col}' contains NaN or None values")
        except Exception:
            pass
    return errors


def validate_multi_value_columns(df: pd.DataFrame) -> list[str]:
    """Checks that MULTI_VALUE_COLUMNS are typed as list[str]."""
    errors = []
    for col in MULTI_VALUE_COLUMNS:
        if col not in df.columns:
            continue
        bad = df[col].apply(lambda x: not isinstance(x, list))
        if bad.any():
            errors.append(
                f"Column '{col}' has {bad.sum()} non-list value(s) (expected list[str])"
            )
    return errors


def validate_scalar_columns(df: pd.DataFrame) -> list[str]:
    """Checks that scalar mandatory columns are str."""
    errors = []
    for col in SCALAR_COLUMNS:
        if col not in df.columns:
            continue
        non_str = df[col].apply(lambda x: not isinstance(x, str))
        if non_str.any():
            errors.append(
                f"Column '{col}' has {non_str.sum()} non-string value(s) (expected str)"
            )
    return errors


def validate_numeric_columns(df: pd.DataFrame) -> list[str]:
    """Checks that TC (and other INT_COLUMNS) have integer dtype."""
    errors = []
    for col in INT_COLUMNS:
        if col not in df.columns:
            continue
        if not pd.api.types.is_integer_dtype(df[col]):
            errors.append(f"Column '{col}' is not integer dtype (got {df[col].dtype})")
    return errors


def validate_year_column(df: pd.DataFrame) -> list[str]:
    """Checks that non-empty PY values match 4-digit year format."""
    if "PY" not in df.columns:
        return []
    bad = df["PY"].apply(
        lambda x: bool(x) and not (isinstance(x, str) and len(x) == 4 and x.isdigit())
    )
    if bad.any():
        sample = df.loc[bad, "PY"].head(3).tolist()
        return [f"Column 'PY' has {bad.sum()} non-4-digit value(s). Sample: {sample}"]
    return []


def validate_database_column(df: pd.DataFrame) -> list[str]:
    """Checks that DB column is present and non-empty."""
    if "DB" not in df.columns:
        return ["Column 'DB' is missing"]
    empty = (df["DB"] == "") | df["DB"].isna()
    if empty.any():
        return [f"Column 'DB' has {empty.sum()} empty/null value(s)"]
    return []


def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Silently adds any missing required columns with safe default values.

    Never raises. list columns → [], TC → 0, others → "".
    """
    from .schema import DEFAULT_VALUES  # noqa: PLC0415
    df = df.copy()
    for col in REQUIRED_COLUMNS:
        if col in df.columns:
            continue
        default = DEFAULT_VALUES.get(col, "")
        if isinstance(default, list):
            df[col] = [list() for _ in range(len(df))]
        else:
            df[col] = default
    return df


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _has_null(x) -> bool:
    if x is None:
        return True
    if isinstance(x, list):
        return False
    try:
        return bool(pd.isna(x))
    except (TypeError, ValueError):
        return False
