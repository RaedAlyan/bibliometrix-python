"""Tests for www.services.etl.exporter."""

import os
import pytest
import pandas as pd
from www.services.etl.exporter import serialize_list_columns, export_to_csv
from www.services.etl.schema import MULTI_VALUE_COLUMNS


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame([{
        "TI": "Test Title",
        "AU": ["Smith J", "Jones A"],
        "DE": ["ML", "AI"],
        "TC": 5,
        "PY": "2022",
    }])


class TestSerializeListColumns:
    def test_list_columns_become_strings(self):
        df = _sample_df()
        result = serialize_list_columns(df)
        assert isinstance(result["AU"].iloc[0], str)
        assert ";" in result["AU"].iloc[0] or len(result["AU"].iloc[0]) > 0

    def test_semicolon_delimiter(self):
        df = _sample_df()
        result = serialize_list_columns(df)
        assert result["AU"].iloc[0] == "Smith J;Jones A"

    def test_scalar_columns_unchanged(self):
        df = _sample_df()
        result = serialize_list_columns(df)
        assert result["TI"].iloc[0] == "Test Title"
        assert result["TC"].iloc[0] == 5

    def test_original_df_not_modified(self):
        df = _sample_df()
        _ = serialize_list_columns(df)
        assert isinstance(df["AU"].iloc[0], list)

    def test_empty_list_becomes_empty_string(self):
        df = pd.DataFrame([{"AU": [], "TI": "x"}])
        result = serialize_list_columns(df)
        assert result["AU"].iloc[0] == ""


class TestExportToCsv:
    def test_writes_csv_file(self, tmp_path):
        df = _sample_df()
        out = str(tmp_path / "output.csv")
        path = export_to_csv(df, out)
        assert os.path.isfile(path)

    def test_returns_absolute_path(self, tmp_path):
        df = _sample_df()
        out = str(tmp_path / "out.csv")
        path = export_to_csv(df, out)
        assert os.path.isabs(path)

    def test_csv_content_readable(self, tmp_path):
        df = _sample_df()
        out = str(tmp_path / "data.csv")
        export_to_csv(df, out)
        loaded = pd.read_csv(out)
        assert "TI" in loaded.columns
        assert loaded["TI"].iloc[0] == "Test Title"

    def test_creates_parent_directory(self, tmp_path):
        df = _sample_df()
        out = str(tmp_path / "nested" / "dir" / "out.csv")
        export_to_csv(df, out)
        assert os.path.isfile(out)

    def test_list_columns_serialized_in_csv(self, tmp_path):
        df = _sample_df()
        out = str(tmp_path / "test.csv")
        export_to_csv(df, out)
        loaded = pd.read_csv(out)
        assert "Smith J" in loaded["AU"].iloc[0]
