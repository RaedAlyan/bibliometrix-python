"""
SR (Short Reference) generation for the Bibliometrix ETL pipeline.

Strategy
--------
1. Try to import and reuse the existing SR() function from
   www/services/metatagextraction.py — this preserves source-specific
   author-name formatting and duplicate-suffix logic already in the codebase.
2. If that import fails for any reason, fall back to a clean re-implementation
   (fallback_generate_sr) that is documented and tested independently.

Public API
----------
    from www.services.etl.sr_generator import generate_sr
    df = generate_sr(df)
"""

import logging
import re
import pandas as pd

log = logging.getLogger(__name__)

# Set to True when the fallback is active (used in tests and logging)
_USING_FALLBACK: bool = False


def find_existing_sr_function():
    """
    Attempts to import the canonical SR() function from metatagextraction.py.

    Returns:
        The SR callable if found, or None.
    """
    try:
        from ..metatagextraction import SR as _sr  # noqa: PLC0415
        log.debug("find_existing_sr_function: found SR() in metatagextraction")
        return _sr
    except Exception as exc:
        log.warning("find_existing_sr_function: could not import SR() — %s", exc)
        return None


def generate_sr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds the SR (Short Reference) and SR_FULL columns to the DataFrame.

    Tries the canonical SR() from metatagextraction.py first.
    Falls back to fallback_generate_sr() if that raises.

    Args:
        df: DataFrame with WoS-tagged columns, type contracts already enforced.

    Returns:
        DataFrame with 'SR' and 'SR_FULL' columns populated.
    """
    global _USING_FALLBACK

    sr_func = find_existing_sr_function()
    if sr_func is not None:
        try:
            df = sr_func(df)
            _USING_FALLBACK = False
            log.debug("generate_sr: used canonical SR() from metatagextraction")
            return df
        except Exception as exc:
            log.warning("generate_sr: canonical SR() raised '%s' — using fallback", exc)

    _USING_FALLBACK = True
    log.info("generate_sr: using fallback SR implementation")
    return fallback_generate_sr(df)


def fallback_generate_sr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fallback SR generator: builds 'FirstAuthor, PY, JI' from available columns.

    NOTE: This is a fallback implementation used when the canonical SR() from
    metatagextraction.py is unavailable or raises. It does not replicate
    source-specific author-name transformations (e.g. Scopus comma-swap).

    Algorithm:
    - FirstAuthor: first element of AU list, commas replaced with spaces.
    - PY: publication year string.
    - JI: journal abbreviation (falls back to SO if JI is empty).
    - Duplicate SR values are disambiguated with -a, -b, -c suffixes.

    Args:
        df: DataFrame with 'AU', 'PY', 'JI', 'SO' columns.

    Returns:
        DataFrame with 'SR' and 'SR_FULL' columns added.
    """
    df = df.copy()

    def _first_author(au_val) -> str:
        if isinstance(au_val, list) and au_val:
            return str(au_val[0]).replace(",", " ").strip()
        return ""

    def _journal(row) -> str:
        ji = str(row.get("JI", "")).strip()
        if not ji:
            ji = str(row.get("SO", "")).strip()
        return re.sub(r"\.", " ", ji).strip()

    first_authors = (
        df["AU"].apply(_first_author) if "AU" in df.columns
        else pd.Series([""] * len(df), index=df.index)
    )
    py = (
        df["PY"].astype(str) if "PY" in df.columns
        else pd.Series([""] * len(df), index=df.index)
    )
    j9 = df.apply(_journal, axis=1)

    sr_base = (first_authors + ", " + py + ", " + j9).str.replace(r"\s+", " ", regex=True)

    # Deduplicate: identical SR values get -a, -b, -c … suffixes
    seen: dict[str, int] = {}
    sr_list = sr_base.tolist()
    for idx, val in enumerate(sr_list):
        if val in seen:
            seen[val] += 1
            sr_list[idx] = val + "-" + chr(96 + seen[val])
        else:
            seen[val] = 0

    df["SR_FULL"] = sr_base.values
    df["SR"] = sr_list
    return df


def _sr_is_using_fallback() -> bool:
    """Returns True if the last call to generate_sr() used the fallback."""
    return _USING_FALLBACK
