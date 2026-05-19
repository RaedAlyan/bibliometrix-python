"""Tests for www.services.etl.standardizer."""

import os
import pytest
import pandas as pd
from www.services.etl.standardizer import (
    standardize_dataframe,
    normalize_year,
    normalize_int,
    split_multi_value,
    rename_columns,
    ensure_required_columns,
)
from www.services.etl.schema import REQUIRED_COLUMNS, MULTI_VALUE_COLUMNS, INT_COLUMNS

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sources")
SCOPUS_FILE = os.path.join(SAMPLE_DIR, "Scopus", "Scopus.csv")
DIMENSIONS_FILE = os.path.join(SAMPLE_DIR, "Dimensions", "Dimensions.xlsx")
PUBMED_FILE = os.path.join(SAMPLE_DIR, "PubMed", "pubmed-allergicrh-set.txt")


def _file_exists(path):
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# Unit-level helpers
# ---------------------------------------------------------------------------

class TestNormalizeYear:
    @pytest.mark.parametrize("raw,expected", [
        ("2022", "2022"),
        ("2022 Feb 2", "2022"),
        (2024, "2024"),
        ("", ""),
        (None, ""),
        (float("nan"), ""),
        ("abc", ""),
    ])
    def test_year_extraction(self, raw, expected):
        assert normalize_year(raw) == expected


class TestNormalizeInt:
    def test_numeric_series(self):
        s = pd.Series([1, 2, 3])
        result = normalize_int(s)
        assert result.dtype == int
        assert list(result) == [1, 2, 3]

    def test_non_numeric_becomes_zero(self):
        s = pd.Series(["abc", None, "", "5"])
        result = normalize_int(s)
        assert result.dtype == int
        assert result[0] == 0
        assert result[3] == 5

    def test_float_truncated(self):
        s = pd.Series([1.9, 2.1])
        result = normalize_int(s)
        assert list(result) == [1, 2]


class TestSplitMultiValue:
    def test_already_list_passthrough(self):
        assert split_multi_value(["a", "b"], "AU") == ["a", "b"]

    def test_semicolon_delimiter(self):
        result = split_multi_value("Smith J; Jones A", "AU")
        assert result == ["Smith J", "Jones A"]

    def test_nan_returns_empty(self):
        assert split_multi_value(float("nan"), "AU") == []

    def test_none_returns_empty(self):
        assert split_multi_value(None, "AU") == []

    def test_empty_string_returns_empty(self):
        assert split_multi_value("", "AU") == []

    def test_single_value_returns_single_item(self):
        assert split_multi_value("Smith J", "AU") == ["Smith J"]

    def test_strips_whitespace(self):
        result = split_multi_value("  Smith J ; Jones A  ", "AU")
        assert result == ["Smith J", "Jones A"]


# ---------------------------------------------------------------------------
# Integration-level standardization
# ---------------------------------------------------------------------------

class TestStandardizeDataframe:
    @pytest.fixture
    def minimal_openalex_df(self):
        return pd.DataFrame([{
            "id": "W123",
            "doi": "10.1000/xyz",
            "title": "Test Title",
            "publication_year": "2022",
            "host_venue_name": "Nature",
            "host_venue_abbrev": "Nat",
            "cited_by_count": 5,
            "type": "article",
            "language": "en",
            "biblio_volume": "1",
            "biblio_issue": "2",
            "biblio_first_page": "10",
            "biblio_last_page": "20",
            "authors": ["Smith J", "Jones A"],
            "authors_full": ["John Smith", "Alice Jones"],
            "affiliations": ["MIT"],
            "abstract": "Test abstract.",
            "keywords": ["ML", "AI"],
            "concepts": ["Computer Science"],
            "referenced_works": [],
            "ids_pmid": "12345",
            "open_access_is_oa": "False",
        }])

    def test_all_required_columns_present(self, minimal_openalex_df):
        df = standardize_dataframe(minimal_openalex_df, "OPENALEX")
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        assert missing == [], f"Missing columns: {missing}"

    def test_no_nan_in_output(self, minimal_openalex_df):
        df = standardize_dataframe(minimal_openalex_df, "OPENALEX")
        for col in df.columns:
            for val in df[col]:
                if not isinstance(val, list):
                    assert val is not None
                    try:
                        assert not pd.isna(val)
                    except (TypeError, ValueError):
                        pass

    def test_multi_value_columns_are_lists(self, minimal_openalex_df):
        df = standardize_dataframe(minimal_openalex_df, "OPENALEX")
        for col in MULTI_VALUE_COLUMNS:
            if col in df.columns:
                for val in df[col]:
                    assert isinstance(val, list), f"{col} value {val!r} is not a list"

    def test_tc_is_integer(self, minimal_openalex_df):
        df = standardize_dataframe(minimal_openalex_df, "OPENALEX")
        assert pd.api.types.is_integer_dtype(df["TC"])

    def test_py_is_4_digit_string(self, minimal_openalex_df):
        df = standardize_dataframe(minimal_openalex_df, "OPENALEX")
        assert df["PY"].iloc[0] == "2022"

    def test_db_set_correctly_for_openalex(self, minimal_openalex_df):
        df = standardize_dataframe(minimal_openalex_df, "OPENALEX")
        assert df["DB"].iloc[0] == "ISI"

    def test_sr_field_present_and_nonempty(self, minimal_openalex_df):
        df = standardize_dataframe(minimal_openalex_df, "OPENALEX")
        assert "SR" in df.columns
        assert df["SR"].iloc[0] != ""

    @pytest.mark.skipif(not _file_exists(SCOPUS_FILE), reason="Scopus sample not found")
    def test_scopus_standardization(self):
        from www.services.etl.extractor import extract_data
        raw_df, source = extract_data(SCOPUS_FILE)
        df = standardize_dataframe(raw_df, source)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        assert missing == [], f"Missing: {missing}"
        assert df["DB"].iloc[0] == "SCOPUS"

    @pytest.mark.skipif(not _file_exists(DIMENSIONS_FILE), reason="Dimensions sample not found")
    def test_dimensions_standardization(self):
        from www.services.etl.extractor import extract_data
        raw_df, source = extract_data(DIMENSIONS_FILE)
        df = standardize_dataframe(raw_df, source)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        assert missing == [], f"Missing: {missing}"
        assert df["DB"].iloc[0] == "DIMENSIONS"

    @pytest.mark.skipif(not _file_exists(PUBMED_FILE), reason="PubMed sample not found")
    def test_pubmed_standardization(self):
        from www.services.etl.extractor import extract_data
        raw_df, source = extract_data(PUBMED_FILE)
        df = standardize_dataframe(raw_df, source)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        assert missing == [], f"Missing: {missing}"
        assert df["DB"].iloc[0] == "PUBMED"
