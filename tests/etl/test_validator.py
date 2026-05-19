"""Tests for www.services.etl.validator."""

import pytest
import pandas as pd
from www.services.etl.validator import (
    validate_dataframe,
    validate_required_columns,
    validate_no_nulls,
    validate_multi_value_columns,
    validate_scalar_columns,
    validate_numeric_columns,
    validate_year_column,
    validate_database_column,
    ensure_required_columns,
)
from www.services.etl.schema import REQUIRED_COLUMNS, MULTI_VALUE_COLUMNS


def _make_valid_df(n=2) -> pd.DataFrame:
    """Build a minimal DataFrame that passes all validators."""
    rows = []
    for i in range(n):
        rows.append({
            "DB": "ISI",
            "UT": f"W{i}",
            "DI": f"10.1000/{i}",
            "PMID": "",
            "TI": f"Title {i}",
            "SO": "Nature",
            "JI": "Nat",
            "PY": "2022",
            "DT": "article",
            "LA": "en",
            "TC": 5,
            "AU": ["Smith J"],
            "AF": ["John Smith"],
            "C1": ["MIT"],
            "RP": "Smith J",
            "CR": [],
            "DE": ["ML"],
            "ID": ["AI"],
            "AB": "Abstract text.",
            "VL": "1",
            "IS": "2",
            "BP": "10",
            "EP": "20",
            "SR": "Smith J, 2022, Nat",
        })
    return pd.DataFrame(rows)


class TestValidateDataframe:
    def test_valid_df_passes(self):
        df = _make_valid_df()
        is_valid, errors = validate_dataframe(df)
        assert is_valid, f"Errors: {errors}"
        assert errors == []

    def test_returns_tuple(self):
        df = _make_valid_df()
        result = validate_dataframe(df)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestValidateRequiredColumns:
    def test_all_present_no_errors(self):
        df = _make_valid_df()
        errors = validate_required_columns(df)
        assert errors == []

    def test_missing_column_reported(self):
        df = _make_valid_df().drop(columns=["TI"])
        errors = validate_required_columns(df)
        assert any("TI" in e for e in errors)

    def test_multiple_missing(self):
        df = _make_valid_df().drop(columns=["TI", "AB"])
        errors = validate_required_columns(df)
        assert len(errors) == 1
        assert "TI" in errors[0] or "AB" in errors[0]


class TestValidateNoNulls:
    def test_no_nulls_passes(self):
        df = _make_valid_df()
        errors = validate_no_nulls(df)
        assert errors == []

    def test_nan_scalar_reported(self):
        df = _make_valid_df()
        df.loc[0, "TI"] = None
        errors = validate_no_nulls(df)
        assert any("TI" in e for e in errors)


class TestValidateMultiValueColumns:
    def test_lists_pass(self):
        df = _make_valid_df()
        errors = validate_multi_value_columns(df)
        assert errors == []

    def test_non_list_reported(self):
        df = _make_valid_df()
        df["AU"] = "Smith J"  # string instead of list
        errors = validate_multi_value_columns(df)
        assert any("AU" in e for e in errors)


class TestValidateNumericColumns:
    def test_int_tc_passes(self):
        df = _make_valid_df()
        errors = validate_numeric_columns(df)
        assert errors == []

    def test_float_tc_fails(self):
        df = _make_valid_df()
        df["TC"] = df["TC"].astype(float)
        errors = validate_numeric_columns(df)
        assert any("TC" in e for e in errors)


class TestValidateYearColumn:
    def test_valid_years_pass(self):
        df = _make_valid_df()
        errors = validate_year_column(df)
        assert errors == []

    def test_malformed_year_reported(self):
        df = _make_valid_df()
        df.loc[0, "PY"] = "22"
        errors = validate_year_column(df)
        assert errors != []

    def test_empty_year_allowed(self):
        df = _make_valid_df()
        df.loc[0, "PY"] = ""
        errors = validate_year_column(df)
        assert errors == []


class TestValidateDatabaseColumn:
    def test_db_present_passes(self):
        df = _make_valid_df()
        errors = validate_database_column(df)
        assert errors == []

    def test_empty_db_reported(self):
        df = _make_valid_df()
        df.loc[0, "DB"] = ""
        errors = validate_database_column(df)
        assert errors != []

    def test_missing_db_column_reported(self):
        df = _make_valid_df().drop(columns=["DB"])
        errors = validate_database_column(df)
        assert errors != []


class TestEnsureRequiredColumns:
    def test_fills_missing_columns(self):
        df = pd.DataFrame([{"TI": "Hello"}])
        df = ensure_required_columns(df)
        for col in REQUIRED_COLUMNS:
            assert col in df.columns

    def test_list_columns_get_empty_list(self):
        df = pd.DataFrame([{"TI": "Hello"}])
        df = ensure_required_columns(df)
        for col in MULTI_VALUE_COLUMNS:
            assert isinstance(df[col].iloc[0], list)

    def test_tc_defaults_to_zero(self):
        df = pd.DataFrame([{"TI": "Hello"}])
        df = ensure_required_columns(df)
        assert df["TC"].iloc[0] == 0

    def test_existing_columns_untouched(self):
        df = pd.DataFrame([{"TI": "My Title"}])
        df = ensure_required_columns(df)
        assert df["TI"].iloc[0] == "My Title"
