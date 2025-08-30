"""S3 operations adapter using Airflow Amazon Provider.

This module provides a standardized interface for S3 operations
using the official Airflow Amazon provider with dependency injection.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class S3Config(BaseModel):
    """Configuration for S3 connections using Airflow connections."""
    
    conn_id: str = Field(
        default="aws_default",
        description="Airflow connection ID for AWS/S3"
    )


class S3Adapter:
    """Adapter for S3 operations using Airflow Amazon Provider.
    
    Provides a clean interface for S3 operations using the official
    Airflow Amazon provider, following dependency injection patterns.
    """
    
    def __init__(self, config: S3Config) -> None:
        """Initialize S3 adapter with configuration.
        
        Args:
            config: S3 configuration parameters
        """
        self.config = config
        self._hook = None
    
    @property
    def hook(self) -> Any:
        """Get Airflow S3 hook instance.
        
        Returns:
            Airflow S3Hook from Amazon provider
            
        Raises:
            ImportError: If amazon provider is not installed
        """
        if self._hook is None:
            try:
                from airflow.providers.amazon.aws.hooks.s3 import S3Hook
            except ImportError as e:
                raise ImportError(
                    "Airflow Amazon provider is required. "
                    "Install with: pip install apache-airflow-providers-amazon"
                ) from e
            
            self._hook = S3Hook(aws_conn_id=self.config.conn_id)
            logger.info("Created S3 hook with connection: %s", self.config.conn_id)
        
        return self._hook
    
    def list_objects(self, bucket: str, prefix: str = "", suffix: str = "") -> list[str]:
        """List objects in S3 bucket with optional filtering.
        
        Args:
            bucket: S3 bucket name
            prefix: Object key prefix filter
            suffix: Object key suffix filter
            
        Returns:
            List of object keys matching the criteria
        """
        keys = self.hook.list_keys(bucket_name=bucket, prefix=prefix)
        if suffix:
            keys = [key for key in keys if key.endswith(suffix)]
        
        logger.info("Found %d objects in s3://%s/%s", len(keys), bucket, prefix)
        return keys
    
    def read_object(self, bucket: str, key: str) -> bytes:
        """Read an object from S3.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            
        Returns:
            Object content as bytes
        """
        try:
            content = self.hook.read_key(key=key, bucket_name=bucket)
            if isinstance(content, str):
                content = content.encode("utf-8")
            logger.info("Read object s3://%s/%s (%d bytes)", bucket, key, len(content))
            return content
        except Exception as e:
            logger.error("Failed to read s3://%s/%s: %s", bucket, key, e)
            raise
    
    def write_object(self, bucket: str, key: str, data: bytes | str) -> None:
        """Write data to an S3 object.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            data: Data to write (bytes or string)
        """
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            
            self.hook.load_string(
                string_data=data,
                key=key,
                bucket_name=bucket,
                replace=True
            )
            logger.info("Wrote object s3://%s/%s", bucket, key)
        except Exception as e:
            logger.error("Failed to write s3://%s/%s: %s", bucket, key, e)
            raise
    
    def delete_object(self, bucket: str, key: str) -> None:
        """Delete an object from S3.
        
        Args:
            bucket: S3 bucket name
            key: Object key
        """
        try:
            self.hook.delete_objects(bucket=bucket, keys=[key])
            logger.info("Deleted object s3://%s/%s", bucket, key)
        except Exception as e:
            logger.error("Failed to delete s3://%s/%s: %s", bucket, key, e)
            raise
    
    def object_exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in S3.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            return self.hook.check_for_key(key=key, bucket_name=bucket)
        except Exception as e:
            logger.error("Error checking if s3://%s/%s exists: %s", bucket, key, e)
            raise
    
    def copy_object(self, source_bucket: str, source_key: str, 
                   dest_bucket: str, dest_key: str) -> None:
        """Copy an object within S3.
        
        Args:
            source_bucket: Source bucket name
            source_key: Source object key
            dest_bucket: Destination bucket name
            dest_key: Destination object key
        """
        try:
            self.hook.copy_object(
                source_bucket_key=f"{source_bucket}/{source_key}",
                dest_bucket_key=f"{dest_bucket}/{dest_key}"
            )
            logger.info(
                "Copied s3://%s/%s to s3://%s/%s",
                source_bucket, source_key, dest_bucket, dest_key
            )
        except Exception as e:
            logger.error(
                "Failed to copy s3://%s/%s to s3://%s/%s: %s",
                source_bucket, source_key, dest_bucket, dest_key, e
            )
            raise