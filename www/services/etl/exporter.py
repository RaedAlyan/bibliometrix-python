"""
EXPORT phase — serializes and writes the standardized DataFrame to CSV.

Public API
----------
    from www.services.etl.exporter import export_to_csv, serialize_list_columns

    path = export_to_csv(df, "output/unified.csv")
"""

import os
import logging
import pandas as pd

from .schema import MULTI_VALUE_COLUMNS

log = logging.getLogger(__name__)


def serialize_list_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Joins list[str] columns with ';' to produce flat strings for CSV export.

    Scalar columns are left untouched.

    Args:
        df: DataFrame with list[str] multi-value columns.

    Returns:
        Copy of df with list columns serialized to ';'-delimited strings.
    """
    df = df.copy()
    for col in MULTI_VALUE_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: ";".join(str(e) for e in x) if isinstance(x, list) else str(x)
            )
    log.debug("serialize_list_columns: serialized %d list columns", len(MULTI_VALUE_COLUMNS))
    return df


def export_to_csv(df: pd.DataFrame, output_path: str) -> str:
    """
    Serializes list columns and writes the DataFrame to a CSV file.

    Creates the output directory if it does not exist.

    Args:
        df:          The standardized DataFrame to export.
        output_path: Destination file path (will be created/overwritten).

    Returns:
        The output_path (absolute, resolved).

    Raises:
        OSError: If the directory cannot be created or the file cannot be written.
    """
    output_path = os.path.realpath(output_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    df_export = serialize_list_columns(df)
    df_export.to_csv(output_path, index=False, encoding="utf-8-sig")

    log.info("export_to_csv: wrote %d rows to '%s'", len(df_export), output_path)
    return output_path
