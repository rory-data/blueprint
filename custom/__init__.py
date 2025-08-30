"""Custom Airflow hooks and operators.

This module provides custom hooks and operators for Airflow 2.10+
following best practices for modern data engineering workflows.
"""

from .hooks import (
    DuckDBHook,
    S3Hook,
    OracleHook,
)
from .operators import (
    DuckDBOperator,
    S3ToS3Operator,
    OracleToS3Operator,
    ParquetProcessingOperator,
)

__all__ = [
    # Hooks
    "DuckDBHook",
    "S3Hook", 
    "OracleHook",
    # Operators
    "DuckDBOperator",
    "S3ToS3Operator",
    "OracleToS3Operator", 
    "ParquetProcessingOperator",
]