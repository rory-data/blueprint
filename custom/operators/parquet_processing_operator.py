"""Parquet Processing Operator for Airflow 2.10+.

This module provides an Airflow operator for processing Parquet files
using pyarrow with S3 integration.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Callable

from airflow.models import BaseOperator
from airflow.utils.context import Context

from ..hooks.s3_hook import S3Hook

logger = logging.getLogger(__name__)


class ParquetProcessingOperator(BaseOperator):
    """Operator for processing Parquet files with pyarrow.
    
    Reads Parquet files from S3, applies transformations, and writes
    results back to S3 following modern Airflow patterns.
    """
    
    def __init__(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
        processing_function: Callable[[Any], Any] | None = None,
        aws_conn_id: str = "aws_default",
        **kwargs
    ) -> None:
        """Initialize Parquet processing operator.
        
        Args:
            source_bucket: Source S3 bucket name
            source_key: Source Parquet file key
            dest_bucket: Destination S3 bucket name
            dest_key: Destination Parquet file key
            processing_function: Function to apply to the DataFrame
            aws_conn_id: Airflow connection ID for AWS/S3
            **kwargs: Additional BaseOperator arguments
        """
        super().__init__(**kwargs)
        self.source_bucket = source_bucket
        self.source_key = source_key
        self.dest_bucket = dest_bucket
        self.dest_key = dest_key
        self.processing_function = processing_function
        self.aws_conn_id = aws_conn_id
    
    def execute(self, context: Context) -> str:
        """Execute the Parquet processing operation.
        
        Args:
            context: Airflow execution context
            
        Returns:
            Status message with processed file location
        """
        try:
            import pandas as pd
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as e:
            raise ImportError(
                "pandas and pyarrow packages are required. "
                "Install with: pip install pandas pyarrow"
            ) from e
        
        s3_hook = S3Hook(aws_conn_id=self.aws_conn_id)
        
        logger.info(
            "Processing Parquet file from s3://%s/%s to s3://%s/%s",
            self.source_bucket, self.source_key,
            self.dest_bucket, self.dest_key
        )
        
        # Create temporary files for processing
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as source_temp:
            source_path = Path(source_temp.name)
            
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as dest_temp:
            dest_path = Path(dest_temp.name)
        
        try:
            # Download source file
            source_data = s3_hook.read_object(self.source_bucket, self.source_key)
            source_path.write_bytes(source_data)
            logger.info("Downloaded source Parquet file")
            
            # Read Parquet file with pyarrow
            table = pq.read_table(source_path)
            df = table.to_pandas()
            logger.info("Loaded Parquet file with %d rows and %d columns", len(df), len(df.columns))
            
            # Apply processing function if provided
            if self.processing_function:
                logger.info("Applying processing function")
                df = self.processing_function(df)
                logger.info("Processing completed, result has %d rows and %d columns", len(df), len(df.columns))
            
            # Write processed data back to Parquet
            df.to_parquet(dest_path, index=False, engine="pyarrow")
            logger.info("Processed data written to temporary file")
            
            # Upload to destination S3
            with dest_path.open("rb") as f:
                processed_data = f.read()
                s3_hook.write_object(self.dest_bucket, self.dest_key, processed_data)
            
            # Verify upload
            if s3_hook.object_exists(self.dest_bucket, self.dest_key):
                result_msg = f"Successfully processed and uploaded to s3://{self.dest_bucket}/{self.dest_key}"
                logger.info(result_msg)
                return result_msg
            else:
                raise RuntimeError(f"Failed to verify upload to s3://{self.dest_bucket}/{self.dest_key}")
                
        finally:
            # Clean up temporary files
            try:
                source_path.unlink(missing_ok=True)
                dest_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning("Failed to clean up temporary files: %s", e)