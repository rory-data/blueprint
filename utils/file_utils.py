"""File operations utility library with pyarrow and Ibis integration.

This module provides utilities for reading and writing Parquet files
on S3 using pyarrow and Ibis, following modern data engineering patterns.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FileConfig(BaseModel):
    """Configuration for file operations using Airflow connections."""
    
    aws_conn_id: str = Field(
        default="aws_default",
        description="Airflow connection ID for AWS/S3"
    )


class FileOperations:
    """Utility class for file operations with S3 and pyarrow integration.
    
    Provides convenient methods for reading and writing Parquet files
    on S3 using pyarrow and Ibis, with proper error handling and resource management.
    """
    
    def __init__(self, config: FileConfig | None = None) -> None:
        """Initialize file operations utility.
        
        Args:
            config: File operations configuration
        """
        self.config = config or FileConfig()
        self._s3_hook = None
    
    @property
    def s3_hook(self) -> Any:
        """Get Airflow S3 hook instance.
        
        Returns:
            Airflow S3Hook from Amazon provider
        """
        if self._s3_hook is None:
            try:
                from airflow.providers.amazon.aws.hooks.s3 import S3Hook
            except ImportError as e:
                raise ImportError(
                    "Airflow Amazon provider is required. "
                    "Install with: pip install apache-airflow-providers-amazon"
                ) from e
            
            self._s3_hook = S3Hook(aws_conn_id=self.config.aws_conn_id)
        
        return self._s3_hook
    
    def read_parquet_from_s3(self, bucket: str, key: str, **kwargs) -> Any:
        """Read a Parquet file from S3 using pyarrow.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            **kwargs: Additional arguments for pyarrow.parquet.read_table
            
        Returns:
            pyarrow Table
        """
        try:
            import pyarrow.parquet as pq
        except ImportError as e:
            raise ImportError(
                "pyarrow package is required. Install with: pip install pyarrow"
            ) from e
        
        # Use Airflow S3 hook to get the file
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_path = Path(temp_file.name)
            
            # Download file using Airflow S3 hook
            self.s3_hook.download_file(
                key=key,
                bucket_name=bucket,
                local_path=str(temp_path)
            )
            
            # Read with pyarrow
            table = pq.read_table(temp_path, **kwargs)
            logger.info(
                "Read Parquet file from s3://%s/%s with %d rows and %d columns",
                bucket, key, table.num_rows, table.num_columns
            )
            
            return table
    
    def write_parquet_to_s3(self, table: Any, bucket: str, key: str, **kwargs) -> None:
        """Write a pyarrow Table to S3 as Parquet.
        
        Args:
            table: pyarrow Table to write
            bucket: S3 bucket name
            key: S3 object key
            **kwargs: Additional arguments for pyarrow.parquet.write_table
        """
        try:
            import pyarrow.parquet as pq
        except ImportError as e:
            raise ImportError(
                "pyarrow package is required. Install with: pip install pyarrow"
            ) from e
        
        with tempfile.NamedTemporaryFile(suffix=".parquet") as temp_file:
            temp_path = Path(temp_file.name)
            
            # Write to temporary file
            pq.write_table(table, temp_path, **kwargs)
            
            # Upload using Airflow S3 hook
            self.s3_hook.load_file(
                filename=str(temp_path),
                key=key,
                bucket_name=bucket,
                replace=True
            )
            
            logger.info("Successfully wrote Parquet file to s3://%s/%s with %d rows", bucket, key, table.num_rows)
    
    def read_parquet_to_ibis(self, bucket: str, key: str, backend: str = "polars") -> Any:
        """Read a Parquet file from S3 directly to Ibis expression.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            backend: Ibis backend to use ('polars' or 'duckdb')
            
        Returns:
            Ibis table expression
        """
        try:
            import ibis
        except ImportError as e:
            raise ImportError(
                "Ibis package is required. Install with: pip install 'ibis-framework[polars,duckdb]'"
            ) from e
        
        # Read as Arrow table first
        arrow_table = self.read_parquet_from_s3(bucket, key)
        
        # Convert to Ibis using specified backend
        if backend == "polars":
            try:
                import polars as pl
            except ImportError as e:
                raise ImportError(
                    "Polars package is required. Install with: pip install polars"
                ) from e
            
            polars_df = pl.from_arrow(arrow_table)
            ibis_table = ibis.memtable(polars_df)
        elif backend == "duckdb":
            conn = ibis.duckdb.connect()
            ibis_table = conn.create_table("temp_table", arrow_table, overwrite=True)
        else:
            raise ValueError(f"Unsupported backend: {backend}. Use 'polars' or 'duckdb'")
        
        logger.info("Read Parquet file to Ibis table with %s backend", backend)
        return ibis_table
    
    def write_ibis_to_s3_parquet(self, ibis_table: Any, bucket: str, key: str, **kwargs) -> None:
        """Write an Ibis table to S3 as Parquet.
        
        Args:
            ibis_table: Ibis table expression to write
            bucket: S3 bucket name
            key: S3 object key
            **kwargs: Additional arguments for pyarrow.parquet.write_table
        """
        # Convert Ibis table to Arrow
        arrow_table = ibis_table.to_pyarrow()
        
        # Write using existing method
        self.write_parquet_to_s3(arrow_table, bucket, key, **kwargs)
        logger.info("Successfully wrote Ibis table to S3 as Parquet")
    
    def copy_parquet_with_transformation(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
        transform_func: Any = None,
        backend: str = "polars"
    ) -> None:
        """Copy a Parquet file with optional transformation using Ibis.
        
        Args:
            source_bucket: Source S3 bucket
            source_key: Source S3 key
            dest_bucket: Destination S3 bucket
            dest_key: Destination S3 key
            transform_func: Optional function to transform Ibis table
            backend: Ibis backend to use for transformations
        """
        # Read source file as Ibis table
        ibis_table = self.read_parquet_to_ibis(source_bucket, source_key, backend)
        
        # Apply transformation if provided
        if transform_func:
            logger.info("Applying transformation function using %s backend", backend)
            ibis_table = transform_func(ibis_table)
            logger.info("Transformation applied successfully")
        
        # Write to destination
        self.write_ibis_to_s3_parquet(ibis_table, dest_bucket, dest_key)