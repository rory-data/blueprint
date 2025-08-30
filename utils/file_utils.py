"""File operations utility library with pyarrow integration.

This module provides utilities for reading and writing Parquet files
on S3 using pyarrow, following modern data engineering patterns.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FileConfig(BaseModel):
    """Configuration for file operations."""
    
    aws_access_key_id: str | None = Field(
        default=None,
        description="AWS access key ID (uses default credentials if not provided)"
    )
    aws_secret_access_key: str | None = Field(
        default=None,
        description="AWS secret access key (uses default credentials if not provided)"
    )
    region_name: str = Field(
        default="us-east-1",
        description="AWS region name"
    )
    endpoint_url: str | None = Field(
        default=None,
        description="Custom S3 endpoint URL"
    )


class FileOperations:
    """Utility class for file operations with S3 and pyarrow integration.
    
    Provides convenient methods for reading and writing Parquet files
    on S3 using pyarrow, with proper error handling and resource management.
    """
    
    def __init__(self, config: FileConfig | None = None) -> None:
        """Initialize file operations utility.
        
        Args:
            config: File operations configuration
        """
        self.config = config or FileConfig()
    
    def _get_s3_filesystem(self) -> Any:
        """Get pyarrow S3 filesystem.
        
        Returns:
            pyarrow S3FileSystem instance
            
        Raises:
            ImportError: If pyarrow is not installed
        """
        try:
            import pyarrow.fs as fs
        except ImportError as e:
            raise ImportError(
                "pyarrow package is required for S3 operations. "
                "Install with: pip install pyarrow"
            ) from e
        
        # Build S3 filesystem options
        fs_options = {
            "region": self.config.region_name,
        }
        
        if self.config.aws_access_key_id and self.config.aws_secret_access_key:
            fs_options.update({
                "access_key": self.config.aws_access_key_id,
                "secret_key": self.config.aws_secret_access_key,
            })
        
        if self.config.endpoint_url:
            fs_options["endpoint_override"] = self.config.endpoint_url
        
        return fs.S3FileSystem(**fs_options)
    
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
        
        s3_path = f"{bucket}/{key}"
        filesystem = self._get_s3_filesystem()
        
        logger.info("Reading Parquet file from s3://%s", s3_path)
        table = pq.read_table(s3_path, filesystem=filesystem, **kwargs)
        logger.info("Read Parquet file with %d rows and %d columns", table.num_rows, table.num_columns)
        
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
        
        s3_path = f"{bucket}/{key}"
        filesystem = self._get_s3_filesystem()
        
        logger.info("Writing Parquet file to s3://%s", s3_path)
        pq.write_table(table, s3_path, filesystem=filesystem, **kwargs)
        logger.info("Successfully wrote Parquet file with %d rows", table.num_rows)
    
    def read_parquet_to_pandas(self, bucket: str, key: str, **kwargs) -> Any:
        """Read a Parquet file from S3 directly to pandas DataFrame.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            **kwargs: Additional arguments for pandas.read_parquet
            
        Returns:
            pandas DataFrame
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "pandas package is required. Install with: pip install pandas"
            ) from e
        
        s3_url = f"s3://{bucket}/{key}"
        
        # Set up storage options if credentials are provided
        storage_options = {}
        if self.config.aws_access_key_id and self.config.aws_secret_access_key:
            storage_options.update({
                "key": self.config.aws_access_key_id,
                "secret": self.config.aws_secret_access_key,
            })
        if self.config.endpoint_url:
            storage_options["client_kwargs"] = {"endpoint_url": self.config.endpoint_url}
        
        logger.info("Reading Parquet file from %s to pandas DataFrame", s3_url)
        df = pd.read_parquet(s3_url, storage_options=storage_options, **kwargs)
        logger.info("Read DataFrame with %d rows and %d columns", len(df), len(df.columns))
        
        return df
    
    def write_pandas_to_s3_parquet(self, df: Any, bucket: str, key: str, **kwargs) -> None:
        """Write a pandas DataFrame to S3 as Parquet.
        
        Args:
            df: pandas DataFrame to write
            bucket: S3 bucket name
            key: S3 object key
            **kwargs: Additional arguments for pandas.to_parquet
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "pandas package is required. Install with: pip install pandas"
            ) from e
        
        s3_url = f"s3://{bucket}/{key}"
        
        # Set up storage options if credentials are provided
        storage_options = {}
        if self.config.aws_access_key_id and self.config.aws_secret_access_key:
            storage_options.update({
                "key": self.config.aws_access_key_id,
                "secret": self.config.aws_secret_access_key,
            })
        if self.config.endpoint_url:
            storage_options["client_kwargs"] = {"endpoint_url": self.config.endpoint_url}
        
        logger.info("Writing DataFrame to %s (%d rows, %d columns)", s3_url, len(df), len(df.columns))
        df.to_parquet(s3_url, storage_options=storage_options, index=False, **kwargs)
        logger.info("Successfully wrote DataFrame to S3 as Parquet")
    
    def copy_parquet_with_transformation(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
        transform_func: Any = None
    ) -> None:
        """Copy a Parquet file with optional transformation.
        
        Args:
            source_bucket: Source S3 bucket
            source_key: Source S3 key
            dest_bucket: Destination S3 bucket
            dest_key: Destination S3 key
            transform_func: Optional function to transform the data
        """
        # Read source file
        table = self.read_parquet_from_s3(source_bucket, source_key)
        
        # Apply transformation if provided
        if transform_func:
            logger.info("Applying transformation function")
            # Convert to pandas for transformation, then back to pyarrow
            df = table.to_pandas()
            df = transform_func(df)
            
            try:
                import pyarrow as pa
            except ImportError as e:
                raise ImportError(
                    "pyarrow package is required. Install with: pip install pyarrow"
                ) from e
            
            table = pa.Table.from_pandas(df)
            logger.info("Transformation applied, result has %d rows", table.num_rows)
        
        # Write to destination
        self.write_parquet_to_s3(table, dest_bucket, dest_key)