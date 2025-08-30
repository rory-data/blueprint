"""Adapters for connections to external systems.

This module provides adapters for connecting to and interacting with external systems
like DuckDB, S3, Oracle, and other data sources in a standardized way.
"""

from .duckdb_adapter import DuckDBAdapter
from .oracle_adapter import OracleAdapter
from .s3_adapter import S3Adapter

__all__ = [
    "DuckDBAdapter",
    "OracleAdapter", 
    "S3Adapter",
]