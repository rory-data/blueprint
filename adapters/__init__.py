"""Adapters for connections to external systems using Airflow providers.

This module provides adapters for connecting to and interacting with external systems
using official Airflow providers and modern data engineering patterns with Arrow/Ibis.
"""

from .duckdb_adapter import DuckDBAdapter, DuckDBConfig
from .oracle_adapter import OracleAdapter, OracleConfig
from .s3_adapter import S3Adapter, S3Config

__all__ = [
    "DuckDBAdapter",
    "DuckDBConfig",
    "OracleAdapter",
    "OracleConfig",
    "S3Adapter",
    "S3Config",
]