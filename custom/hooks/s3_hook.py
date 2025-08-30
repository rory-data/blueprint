"""S3 Hook for Airflow 2.10+.

This module provides an Airflow hook for S3 operations
following Airflow 2.10+ best practices.
"""

import logging
from typing import Any

from airflow.hooks.base import BaseHook

from ...adapters.s3_adapter import S3Adapter, S3Config

logger = logging.getLogger(__name__)


class S3Hook(BaseHook):
    """Hook for S3 operations in Airflow.
    
    Integrates S3Adapter with Airflow's connection management system.
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
        self._adapter = None
    
    @property
    def adapter(self) -> S3Adapter:
        """Get S3 adapter instance.
        
        Returns:
            Configured S3Adapter instance
        """
        if self._adapter is None:
            conn = self.get_connection(self.aws_conn_id)
            
            # Extract configuration from Airflow connection
            config = S3Config(
                aws_access_key_id=conn.login,
                aws_secret_access_key=conn.password,
                region_name=conn.extra_dejson.get("region_name", "us-east-1"),
                endpoint_url=conn.extra_dejson.get("endpoint_url")
            )
            
            self._adapter = S3Adapter(config)
        
        return self._adapter
    
    def test_connection(self) -> tuple[bool, str]:
        """Test the S3 connection.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            with self.adapter.client() as s3_client:
                s3_client.list_buckets()
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
        return self.adapter.list_objects(bucket, prefix, suffix)
    
    def read_object(self, bucket: str, key: str) -> bytes:
        """Read an object from S3.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            
        Returns:
            Object content as bytes
        """
        return self.adapter.read_object(bucket, key)
    
    def write_object(self, bucket: str, key: str, data: bytes | str) -> None:
        """Write data to an S3 object.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            data: Data to write
        """
        self.adapter.write_object(bucket, key, data)
    
    def delete_object(self, bucket: str, key: str) -> None:
        """Delete an object from S3.
        
        Args:
            bucket: S3 bucket name
            key: Object key
        """
        self.adapter.delete_object(bucket, key)
    
    def object_exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in S3.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            
        Returns:
            True if object exists, False otherwise
        """
        return self.adapter.object_exists(bucket, key)
    
    def copy_object(self, source_bucket: str, source_key: str,
                   dest_bucket: str, dest_key: str) -> None:
        """Copy an object within S3.
        
        Args:
            source_bucket: Source bucket name
            source_key: Source object key
            dest_bucket: Destination bucket name
            dest_key: Destination object key
        """
        self.adapter.copy_object(source_bucket, source_key, dest_bucket, dest_key)