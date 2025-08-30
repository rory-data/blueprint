"""S3 operations adapter.

This module provides a standardized interface for S3 operations
including reading, writing, and listing objects with proper error handling.
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class S3Config(BaseModel):
    """Configuration for S3 connections."""
    
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
        description="Custom S3 endpoint URL (for S3-compatible services)"
    )


class S3Adapter:
    """Adapter for S3 operations.
    
    Provides a clean interface for S3 operations with proper
    resource management and error handling following SOLID principles.
    """
    
    def __init__(self, config: S3Config) -> None:
        """Initialize S3 adapter with configuration.
        
        Args:
            config: S3 configuration parameters
        """
        self.config = config
    
    @contextmanager
    def client(self) -> Iterator[Any]:
        """Get an S3 client with automatic cleanup.
        
        Yields:
            boto3 S3 client
            
        Raises:
            ImportError: If boto3 package is not installed
            Exception: If client cannot be created
        """
        try:
            import boto3
        except ImportError as e:
            raise ImportError(
                "boto3 package is required for S3 operations. Install with: pip install boto3"
            ) from e
        
        client = None
        try:
            client_kwargs = {
                "service_name": "s3",
                "region_name": self.config.region_name,
            }
            
            if self.config.aws_access_key_id and self.config.aws_secret_access_key:
                client_kwargs.update({
                    "aws_access_key_id": self.config.aws_access_key_id,
                    "aws_secret_access_key": self.config.aws_secret_access_key,
                })
            
            if self.config.endpoint_url:
                client_kwargs["endpoint_url"] = self.config.endpoint_url
            
            client = boto3.client(**client_kwargs)
            logger.info("Created S3 client for region: %s", self.config.region_name)
            yield client
            
        except Exception as e:
            logger.error("Failed to create S3 client: %s", e)
            raise
        finally:
            # boto3 clients don't need explicit cleanup
            if client:
                logger.info("S3 client session ended")
    
    def list_objects(self, bucket: str, prefix: str = "", suffix: str = "") -> list[str]:
        """List objects in S3 bucket with optional filtering.
        
        Args:
            bucket: S3 bucket name
            prefix: Object key prefix filter
            suffix: Object key suffix filter
            
        Returns:
            List of object keys matching the criteria
        """
        with self.client() as s3_client:
            objects = []
            paginator = s3_client.get_paginator("list_objects_v2")
            
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        key = obj["Key"]
                        if not suffix or key.endswith(suffix):
                            objects.append(key)
            
            logger.info("Found %d objects in s3://%s/%s", len(objects), bucket, prefix)
            return objects
    
    def read_object(self, bucket: str, key: str) -> bytes:
        """Read an object from S3.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            
        Returns:
            Object content as bytes
        """
        with self.client() as s3_client:
            try:
                response = s3_client.get_object(Bucket=bucket, Key=key)
                content = response["Body"].read()
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
        with self.client() as s3_client:
            try:
                if isinstance(data, str):
                    data = data.encode("utf-8")
                
                s3_client.put_object(Bucket=bucket, Key=key, Body=data)
                logger.info("Wrote object s3://%s/%s (%d bytes)", bucket, key, len(data))
            except Exception as e:
                logger.error("Failed to write s3://%s/%s: %s", bucket, key, e)
                raise
    
    def delete_object(self, bucket: str, key: str) -> None:
        """Delete an object from S3.
        
        Args:
            bucket: S3 bucket name
            key: Object key
        """
        with self.client() as s3_client:
            try:
                s3_client.delete_object(Bucket=bucket, Key=key)
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
        with self.client() as s3_client:
            try:
                s3_client.head_object(Bucket=bucket, Key=key)
                return True
            except s3_client.exceptions.NoSuchKey:
                return False
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
        with self.client() as s3_client:
            try:
                copy_source = {"Bucket": source_bucket, "Key": source_key}
                s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=dest_bucket,
                    Key=dest_key
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