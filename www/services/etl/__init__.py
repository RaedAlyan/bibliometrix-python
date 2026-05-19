"""
Bibliometrix-Python ETL Package
================================
Python equivalent of R's bibliometrix::convert2df().

Public API
----------
    from www.services.etl import run_file_pipeline, run_api_pipeline, convert2df

    df = convert2df("sources/Scopus/Scopus.csv")
    df = convert2df(source="openalex", query="machine learning")
"""

from .pipeline import run_file_pipeline, run_api_pipeline
from .standardizer import convert2df
from .schema import REQUIRED_COLUMNS, MULTI_VALUE_COLUMNS, SCALAR_COLUMNS, DEFAULT_VALUES
from .validator import validate_dataframe
from .exporter import export_to_csv

__all__ = [
    "run_file_pipeline",
    "run_api_pipeline",
    "convert2df",
    "REQUIRED_COLUMNS",
    "MULTI_VALUE_COLUMNS",
    "SCALAR_COLUMNS",
    "DEFAULT_VALUES",
    "validate_dataframe",
    "export_to_csv",
]
