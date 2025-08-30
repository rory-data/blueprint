"""Custom Airflow operators for data processing."""

from .duckdb_operator import DuckDBOperator
from .oracle_to_s3_operator import OracleToS3Operator
from .parquet_processing_operator import ParquetProcessingOperator
from .s3_to_s3_operator import S3ToS3Operator

__all__ = [
    "DuckDBOperator",
    "OracleToS3Operator",
    "ParquetProcessingOperator",
    "S3ToS3Operator",
]