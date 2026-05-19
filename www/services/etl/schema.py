"""
Schema definition for the Bibliometrix ETL pipeline.

Defines the target Web-of-Science-like column set, type contracts, and
default fill values. Every module in this package imports from here — one
source of truth for the schema.
"""

# ---------------------------------------------------------------------------
# Target columns (24 WoS-standard tags)
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS: list[str] = [
    "DB", "UT", "DI", "PMID", "TI", "SO", "JI", "PY", "DT", "LA",
    "TC", "AU", "AF", "C1", "RP", "CR", "DE", "ID", "AB",
    "VL", "IS", "BP", "EP", "SR",
]

# Columns whose values must be Python list[str]
MULTI_VALUE_COLUMNS: list[str] = ["AU", "AF", "C1", "CR", "DE", "ID"]

# Columns whose values must be plain str (empty string "" when missing)
SCALAR_COLUMNS: list[str] = [
    c for c in REQUIRED_COLUMNS
    if c not in MULTI_VALUE_COLUMNS and c != "TC"
]

# Integer columns (0 when missing)
INT_COLUMNS: list[str] = ["TC"]

# Default fill values per column
DEFAULT_VALUES: dict = {
    **{col: [] for col in MULTI_VALUE_COLUMNS},
    **{col: "" for col in SCALAR_COLUMNS},
    "TC": 0,
}

# Human-readable descriptions (used by validator messages and notebooks)
COLUMN_DESCRIPTIONS: dict[str, str] = {
    "DB":   "Database source identifier",
    "UT":   "Unique article identifier",
    "DI":   "DOI (Digital Object Identifier)",
    "PMID": "PubMed ID",
    "TI":   "Article title",
    "SO":   "Journal / source title",
    "JI":   "Journal ISO abbreviation",
    "PY":   "Publication year (4-digit string)",
    "DT":   "Document type",
    "LA":   "Language",
    "TC":   "Times cited (integer)",
    "AU":   "Authors — Surname Initials format — list[str]",
    "AF":   "Authors full names — list[str]",
    "C1":   "Author affiliations — list[str]",
    "RP":   "Corresponding author address",
    "CR":   "Cited references — list[str]",
    "DE":   "Author keywords — list[str]",
    "ID":   "Index / MeSH keywords — list[str]",
    "AB":   "Abstract",
    "VL":   "Volume",
    "IS":   "Issue",
    "BP":   "Beginning page",
    "EP":   "Ending page",
    "SR":   "Short reference key (e.g. 'Smith J, 2022, NATURE')",
}

# Valid DB values and what they represent
DB_VALUES: dict[str, str] = {
    "SCOPUS":     "Elsevier Scopus",
    "DIMENSIONS": "Digital Science Dimensions",
    "PUBMED":     "NCBI PubMed",
    "ISI":        "Clarivate Web of Science (and OpenAlex)",
    "OPENALEX":   "OpenAlex open catalogue",
}
