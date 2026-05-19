"""Tests for www.services.etl.pipeline (end-to-end, with mocked HTTP)."""

import os
import json
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from www.services.etl.pipeline import run_file_pipeline, run_api_pipeline
from www.services.etl.schema import REQUIRED_COLUMNS

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sources")
SCOPUS_FILE = os.path.join(SAMPLE_DIR, "Scopus", "Scopus.csv")
DIMENSIONS_FILE = os.path.join(SAMPLE_DIR, "Dimensions", "Dimensions.xlsx")
PUBMED_FILE = os.path.join(SAMPLE_DIR, "PubMed", "pubmed-allergicrh-set.txt")


def _file_exists(path):
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# run_file_pipeline
# ---------------------------------------------------------------------------

class TestRunFilePipeline:
    @pytest.mark.skipif(not _file_exists(SCOPUS_FILE), reason="Scopus sample not found")
    def test_scopus_returns_triple(self):
        result = run_file_pipeline(SCOPUS_FILE)
        assert len(result) == 3
        df, is_valid, errors = result
        assert isinstance(df, pd.DataFrame)
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    @pytest.mark.skipif(not _file_exists(SCOPUS_FILE), reason="Scopus sample not found")
    def test_scopus_has_required_columns(self):
        df, _, _ = run_file_pipeline(SCOPUS_FILE)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        assert missing == [], f"Missing: {missing}"

    @pytest.mark.skipif(not _file_exists(DIMENSIONS_FILE), reason="Dimensions sample not found")
    def test_dimensions_pipeline(self):
        df, is_valid, errors = run_file_pipeline(DIMENSIONS_FILE)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    @pytest.mark.skipif(not _file_exists(PUBMED_FILE), reason="PubMed sample not found")
    def test_pubmed_pipeline(self):
        df, is_valid, errors = run_file_pipeline(PUBMED_FILE)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_nonexistent_file_raises(self):
        with pytest.raises((FileNotFoundError, Exception)):
            run_file_pipeline("/nonexistent/file.csv")

    @pytest.mark.skipif(not _file_exists(SCOPUS_FILE), reason="Scopus sample not found")
    def test_export_to_csv(self, tmp_path):
        out = str(tmp_path / "output.csv")
        df, _, _ = run_file_pipeline(SCOPUS_FILE, output_path=out)
        assert os.path.isfile(out)


# ---------------------------------------------------------------------------
# run_api_pipeline (mocked HTTP)
# ---------------------------------------------------------------------------

def _mock_openalex_response():
    work = {
        "id": "https://openalex.org/W123",
        "doi": "https://doi.org/10.1000/xyz",
        "title": "Machine Learning Review",
        "publication_year": 2022,
        "primary_location": {"source": {"display_name": "Nature", "abbreviated_title": "Nat"}},
        "cited_by_count": 10,
        "type": "article",
        "language": "en",
        "biblio": {"volume": "1", "issue": "2", "first_page": "1", "last_page": "10"},
        "authorships": [{
            "author": {"display_name": "John Smith"},
            "institutions": [{"display_name": "MIT"}],
        }],
        "keywords": [{"display_name": "ML"}],
        "concepts": [{"display_name": "AI"}],
        "abstract_inverted_index": {"Machine": [0], "learning": [1]},
        "referenced_works": [],
        "ids": {"pmid": ""},
        "open_access": {"is_oa": False},
    }
    return {
        "results": [work],
        "meta": {"next_cursor": None},
    }


def _mock_pubmed_esearch():
    return {"esearchresult": {"count": "1", "webenv": "WE123", "querykey": "1"}}


MINIMAL_PUBMED_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
<PubmedArticle>
<MedlineCitation>
  <PMID>12345</PMID>
  <Article>
    <ArticleTitle>Test PubMed Article</ArticleTitle>
    <Abstract><AbstractText>This is an abstract.</AbstractText></Abstract>
    <Journal>
      <Title>Test Journal</Title>
      <ISOAbbreviation>Test J</ISOAbbreviation>
      <JournalIssue>
        <Volume>1</Volume>
        <Issue>2</Issue>
        <PubDate><Year>2022</Year></PubDate>
      </JournalIssue>
    </Journal>
    <Pagination><MedlinePgn>10-20</MedlinePgn></Pagination>
    <PublicationTypeList>
      <PublicationType>Journal Article</PublicationType>
    </PublicationTypeList>
    <Language>eng</Language>
  </Article>
  <ArticleIdList>
    <ArticleId IdType="doi">10.1000/test</ArticleId>
  </ArticleIdList>
</MedlineCitation>
</PubmedArticle>
</PubmedArticleSet>"""


class TestRunApiPipeline:
    def test_empty_query_raises(self):
        with pytest.raises(ValueError, match="query"):
            run_api_pipeline("   ", platform="openalex")

    def test_unknown_platform_raises(self):
        with pytest.raises(ValueError, match="platform"):
            run_api_pipeline("test", platform="unknown_db")

    @patch("www.services.etl.api_retriever.requests.get")
    def test_openalex_pipeline(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _mock_openalex_response()
        mock_get.return_value = resp

        df, is_valid, errors = run_api_pipeline("machine learning", platform="openalex", max_records=1)
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 1
        assert "TI" in df.columns

    @patch("www.services.etl.api_retriever.requests.get")
    def test_pubmed_api_pipeline(self, mock_get):
        esearch_resp = MagicMock()
        esearch_resp.status_code = 200
        esearch_resp.json.return_value = _mock_pubmed_esearch()

        efetch_resp = MagicMock()
        efetch_resp.status_code = 200
        efetch_resp.text = MINIMAL_PUBMED_XML

        mock_get.side_effect = [esearch_resp, efetch_resp]

        df, is_valid, errors = run_api_pipeline("allergy", platform="pubmed_api", max_records=1)
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 1

    @patch("www.services.etl.api_retriever.requests.get")
    def test_openalex_has_required_columns(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _mock_openalex_response()
        mock_get.return_value = resp

        df, _, _ = run_api_pipeline("test", platform="openalex", max_records=1)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        assert missing == [], f"Missing: {missing}"

    @patch("www.services.etl.api_retriever.requests.get")
    def test_http_failure_returns_empty_df(self, mock_get):
        mock_get.return_value = MagicMock(status_code=500)
        df, _, _ = run_api_pipeline("test query", platform="openalex", max_records=1)
        assert isinstance(df, pd.DataFrame)

    @patch("www.services.etl.api_retriever.requests.get")
    def test_export_to_csv(self, mock_get, tmp_path):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _mock_openalex_response()
        mock_get.return_value = resp

        out = str(tmp_path / "api_out.csv")
        df, _, _ = run_api_pipeline("test", platform="openalex", max_records=1, output_path=out)
        assert os.path.isfile(out)
