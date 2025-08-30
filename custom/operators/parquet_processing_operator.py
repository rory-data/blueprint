"""Parquet Processing Operator for Airflow 2.10+ with Ibis integration.

This module provides an Airflow operator for processing Parquet files
using Ibis and Arrow for efficient transformations.
"""

import logging
from typing import Any, Callable

from airflow.models import BaseOperator
from airflow.utils.context import Context

from ...utils.file_utils import FileOperations, FileConfig

logger = logging.getLogger(__name__)


class ParquetProcessingOperator(BaseOperator):
    """Operator for processing Parquet files with Ibis and Arrow.
    
    Reads Parquet files from S3, applies transformations using Ibis,
    and writes results back to S3 following modern data engineering patterns.
    """
    
    def __init__(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
        processing_function: Callable[[Any], Any] | None = None,
        aws_conn_id: str = "aws_default",
        backend: str = "polars",
        **kwargs
    ) -> None:
        """Initialize Parquet processing operator.
        
        Args:
            source_bucket: Source S3 bucket name
            source_key: Source Parquet file key
            dest_bucket: Destination S3 bucket name
            dest_key: Destination Parquet file key
            processing_function: Function to apply to the Ibis table
            aws_conn_id: Airflow connection ID for AWS/S3
            backend: Ibis backend to use ('polars' or 'duckdb')
            **kwargs: Additional BaseOperator arguments
        """
        super().__init__(**kwargs)
        self.source_bucket = source_bucket
        self.source_key = source_key
        self.dest_bucket = dest_bucket
        self.dest_key = dest_key
        self.processing_function = processing_function
        self.aws_conn_id = aws_conn_id
        self.backend = backend
        
        if self.backend not in ["polars", "duckdb"]:
            raise ValueError("backend must be 'polars' or 'duckdb'")
    
    def execute(self, context: Context) -> str:
        """Execute the Parquet processing operation using Ibis.
        
        Args:
            context: Airflow execution context
            
        Returns:
            Status message with processed file location
        """
        file_ops = FileOperations(FileConfig(aws_conn_id=self.aws_conn_id))
        
        logger.info(
            "Processing Parquet file from s3://%s/%s to s3://%s/%s using %s backend",
            self.source_bucket, self.source_key,
            self.dest_bucket, self.dest_key, self.backend
        )
        
        try:
            # Read source file as Ibis table
            ibis_table = file_ops.read_parquet_to_ibis(
                self.source_bucket, self.source_key, self.backend
            )
            logger.info("Loaded Parquet file as Ibis table")
            
            # Apply processing function if provided
            if self.processing_function:
                logger.info("Applying processing function with %s backend", self.backend)
                ibis_table = self.processing_function(ibis_table)
                logger.info("Processing completed using Ibis")
            
            # Write processed data back to S3 as Parquet
            file_ops.write_ibis_to_s3_parquet(ibis_table, self.dest_bucket, self.dest_key)
            
            # Verify upload
            if file_ops.s3_hook.check_for_key(key=self.dest_key, bucket_name=self.dest_bucket):
                result_msg = f"Successfully processed and uploaded to s3://{self.dest_bucket}/{self.dest_key}"
                logger.info(result_msg)
                return result_msg
            else:
                raise RuntimeError(f"Failed to verify upload to s3://{self.dest_bucket}/{self.dest_key}")
                
        except Exception as e:
            logger.error("Parquet processing failed: %s", e)
            raise