"""Tests for www.services.etl.extractor."""

import os
import pytest
import pandas as pd
from www.services.etl.extractor import detect_source, extract_data

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sources")
SCOPUS_FILE = os.path.join(SAMPLE_DIR, "Scopus", "Scopus.csv")
DIMENSIONS_FILE = os.path.join(SAMPLE_DIR, "Dimensions", "Dimensions.xlsx")
PUBMED_FILE = os.path.join(SAMPLE_DIR, "PubMed", "pubmed-allergicrh-set.txt")


def _file_exists(path):
    return os.path.isfile(path)


class TestDetectSource:
    @pytest.mark.skipif(not _file_exists(SCOPUS_FILE), reason="Scopus sample not found")
    def test_detect_scopus(self):
        assert detect_source(SCOPUS_FILE) == "SCOPUS"

    @pytest.mark.skipif(not _file_exists(DIMENSIONS_FILE), reason="Dimensions sample not found")
    def test_detect_dimensions(self):
        assert detect_source(DIMENSIONS_FILE) == "DIMENSIONS"

    @pytest.mark.skipif(not _file_exists(PUBMED_FILE), reason="PubMed sample not found")
    def test_detect_pubmed(self):
        assert detect_source(PUBMED_FILE) == "PUBMED"

    def test_unknown_file_raises(self, tmp_path):
        f = tmp_path / "unknown.csv"
        f.write_text("col1,col2\n1,2\n")
        with pytest.raises((ValueError, Exception)):
            detect_source(str(f))

    def test_nonexistent_file_raises(self):
        with pytest.raises((FileNotFoundError, Exception)):
            detect_source("/nonexistent/path/file.csv")


class TestExtractData:
    @pytest.mark.skipif(not _file_exists(SCOPUS_FILE), reason="Scopus sample not found")
    def test_scopus_returns_dataframe(self):
        df, source = extract_data(SCOPUS_FILE)
        assert isinstance(df, pd.DataFrame)
        assert source == "SCOPUS"
        assert len(df) > 0

    @pytest.mark.skipif(not _file_exists(DIMENSIONS_FILE), reason="Dimensions sample not found")
    def test_dimensions_returns_dataframe(self):
        df, source = extract_data(DIMENSIONS_FILE)
        assert isinstance(df, pd.DataFrame)
        assert source == "DIMENSIONS"
        assert len(df) > 0

    @pytest.mark.skipif(not _file_exists(PUBMED_FILE), reason="PubMed sample not found")
    def test_pubmed_returns_dataframe(self):
        df, source = extract_data(PUBMED_FILE)
        assert isinstance(df, pd.DataFrame)
        assert source == "PUBMED"
        assert len(df) > 0

    @pytest.mark.skipif(not _file_exists(SCOPUS_FILE), reason="Scopus sample not found")
    def test_explicit_source_override(self):
        df, source = extract_data(SCOPUS_FILE, source="SCOPUS")
        assert source == "SCOPUS"

    @pytest.mark.skipif(not _file_exists(SCOPUS_FILE), reason="Scopus sample not found")
    def test_scopus_has_expected_raw_columns(self):
        df, _ = extract_data(SCOPUS_FILE)
        assert "Title" in df.columns or "Authors" in df.columns
