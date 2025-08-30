"""S3 Hook for Airflow 2.10+ using Amazon Provider.

This module provides an Airflow hook for S3 operations
using the official Amazon provider with dependency injection.
"""

import logging
from typing import Any

from airflow.hooks.base import BaseHook

logger = logging.getLogger(__name__)


class S3Hook(BaseHook):
    """Hook for S3 operations in Airflow using Amazon Provider.
    
    Extends Airflow's S3Hook with additional convenience methods
    and dependency injection patterns.
    """
    
    conn_name_attr = "aws_conn_id"
    default_conn_name = "aws_default"
    conn_type = "aws"
    hook_name = "S3"
    
    def __init__(self, aws_conn_id: str = default_conn_name) -> None:
        """Initialize S3 hook.
        
        Args:
            aws_conn_id: Airflow connection ID for AWS/S3
        """
        super().__init__()
        self.aws_conn_id = aws_conn_id
        self._s3_hook = None
    
    @property
    def s3_hook(self) -> Any:
        """Get Airflow S3 hook instance.
        
        Returns:
            Airflow S3Hook from Amazon provider
            
        Raises:
            ImportError: If Amazon provider is not installed
        """
        if self._s3_hook is None:
            try:
                from airflow.providers.amazon.aws.hooks.s3 import S3Hook as AmazonS3Hook
            except ImportError as e:
                raise ImportError(
                    "Airflow Amazon provider is required. "
                    "Install with: pip install apache-airflow-providers-amazon"
                ) from e
            
            self._s3_hook = AmazonS3Hook(aws_conn_id=self.aws_conn_id)
            logger.info("Created S3 hook with connection: %s", self.aws_conn_id)
        
        return self._s3_hook
    
    def test_connection(self) -> tuple[bool, str]:
        """Test the S3 connection.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Use Amazon provider's connection test
            self.s3_hook.get_conn().list_buckets()
            return True, "S3 connection test successful"
        except Exception as e:
            return False, f"S3 connection test failed: {e}"
    
    def list_objects(self, bucket: str, prefix: str = "", suffix: str = "") -> list[str]:
        """List objects in S3 bucket.
        
        Args:
            bucket: S3 bucket name
            prefix: Object key prefix filter
            suffix: Object key suffix filter
            
        Returns:
            List of object keys
        """
        keys = self.s3_hook.list_keys(bucket_name=bucket, prefix=prefix)
        if suffix:
            keys = [key for key in keys if key.endswith(suffix)]
        return keys
    
    def read_object(self, bucket: str, key: str) -> bytes:
        """Read an object from S3.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            
        Returns:
            Object content as bytes
        """
        content = self.s3_hook.read_key(key=key, bucket_name=bucket)
        if isinstance(content, str):
            content = content.encode("utf-8")
        return content
    
    def write_object(self, bucket: str, key: str, data: bytes | str) -> None:
        """Write data to an S3 object.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            data: Data to write
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        
        self.s3_hook.load_string(
            string_data=data,
            key=key,
            bucket_name=bucket,
            replace=True
        )
    
    def delete_object(self, bucket: str, key: str) -> None:
        """Delete an object from S3.
        
        Args:
            bucket: S3 bucket name
            key: Object key
        """
        self.s3_hook.delete_objects(bucket=bucket, keys=[key])
    
    def object_exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in S3.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            
        Returns:
            True if object exists, False otherwise
        """
        return self.s3_hook.check_for_key(key=key, bucket_name=bucket)
    
    def copy_object(self, source_bucket: str, source_key: str,
                   dest_bucket: str, dest_key: str) -> None:
        """Copy an object within S3.
        
        Args:
            source_bucket: Source bucket name
            source_key: Source object key
            dest_bucket: Destination bucket name
            dest_key: Destination object key
        """
        self.s3_hook.copy_object(
            source_bucket_key=f"{source_bucket}/{source_key}",
            dest_bucket_key=f"{dest_bucket}/{dest_key}"
        )