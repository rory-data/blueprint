"""Custom Airflow hooks for external systems."""

from .duckdb_hook import DuckDBHook
from .oracle_hook import OracleHook
from .s3_hook import S3Hook

__all__ = [
    "DuckDBHook",
    "OracleHook",
    "S3Hook",
]