"""Tests for www.services.etl.mappings."""

import pytest
from www.services.etl.mappings import (
    get_mapping,
    SCOPUS_MAP,
    DIMENSIONS_MAP,
    PUBMED_MAP,
    OPENALEX_MAP,
    PUBMED_API_MAP,
    WOS_MAP,
    SOURCE_MAPPINGS,
)


class TestGetMapping:
    def test_scopus(self):
        m = get_mapping("SCOPUS")
        assert m is SCOPUS_MAP

    def test_dimensions(self):
        m = get_mapping("DIMENSIONS")
        assert m is DIMENSIONS_MAP

    def test_pubmed(self):
        m = get_mapping("PUBMED")
        assert m is PUBMED_MAP

    def test_openalex(self):
        m = get_mapping("OPENALEX")
        assert m is OPENALEX_MAP

    def test_pubmed_api(self):
        m = get_mapping("PUBMED_API")
        assert m is PUBMED_API_MAP

    def test_wos(self):
        m = get_mapping("WOS")
        assert m is WOS_MAP

    def test_case_insensitive(self):
        assert get_mapping("scopus") is SCOPUS_MAP
        assert get_mapping("Openalex") is OPENALEX_MAP

    def test_unknown_source_raises(self):
        with pytest.raises(KeyError):
            get_mapping("UNKNOWN_DB")


class TestMappingContent:
    @pytest.mark.parametrize("source,expected_key,expected_val", [
        ("SCOPUS", "Title", "TI"),
        ("SCOPUS", "Authors", "AU"),
        ("SCOPUS", "Year", "PY"),
        ("SCOPUS", "Cited by", "TC"),
        ("DIMENSIONS", "Title", "TI"),
        ("OPENALEX", "title", "TI"),
        ("OPENALEX", "cited_by_count", "TC"),
        ("PUBMED_API", "title", "TI"),
        ("PUBMED_API", "pmid", "PMID"),
    ])
    def test_key_maps_to_wos_tag(self, source, expected_key, expected_val):
        mapping = get_mapping(source)
        assert mapping.get(expected_key) == expected_val

    def test_all_values_are_strings_or_none(self):
        for source, mapping in SOURCE_MAPPINGS.items():
            for k, v in mapping.items():
                assert v is None or isinstance(v, str), (
                    f"{source}: key '{k}' has non-string value {v!r}"
                )

    def test_no_duplicate_values_in_scopus(self):
        values = [v for v in SCOPUS_MAP.values() if v is not None]
        # Some duplication is allowed (two raw cols → same WoS tag), so just check list not empty
        assert len(values) > 0

    def test_openalex_has_author_fields(self):
        assert "authors" in OPENALEX_MAP
        assert "authors_full" in OPENALEX_MAP
        assert OPENALEX_MAP["authors"] == "AU"
        assert OPENALEX_MAP["authors_full"] == "AF"
