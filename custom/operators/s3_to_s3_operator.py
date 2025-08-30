"""S3 to S3 Operator for Airflow 2.10+.

This module provides an Airflow operator for S3 to S3 operations
like copying, transforming, and moving objects between S3 locations.
"""

import logging
from typing import Any

from airflow.models import BaseOperator
from airflow.utils.context import Context

from ..hooks.s3_hook import S3Hook

logger = logging.getLogger(__name__)


class S3ToS3Operator(BaseOperator):
    """Operator for S3 to S3 operations.
    
    Performs operations like copying, moving, or transforming data
    between S3 locations following modern Airflow patterns.
    """
    
    def __init__(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
        operation: str = "copy",
        aws_conn_id: str = "aws_default",
        verify_dest: bool = True,
        **kwargs
    ) -> None:
        """Initialize S3 to S3 operator.
        
        Args:
            source_bucket: Source S3 bucket name
            source_key: Source object key
            dest_bucket: Destination S3 bucket name
            dest_key: Destination object key
            operation: Operation type ('copy', 'move')
            aws_conn_id: Airflow connection ID for AWS/S3
            verify_dest: Verify destination object after operation
            **kwargs: Additional BaseOperator arguments
        """
        super().__init__(**kwargs)
        self.source_bucket = source_bucket
        self.source_key = source_key
        self.dest_bucket = dest_bucket
        self.dest_key = dest_key
        self.operation = operation.lower()
        self.aws_conn_id = aws_conn_id
        self.verify_dest = verify_dest
        
        if self.operation not in ["copy", "move"]:
            raise ValueError("operation must be 'copy' or 'move'")
    
    def execute(self, context: Context) -> str:
        """Execute the S3 to S3 operation.
        
        Args:
            context: Airflow execution context
            
        Returns:
            Status message
        """
        hook = S3Hook(aws_conn_id=self.aws_conn_id)
        
        # Verify source object exists
        if not hook.object_exists(self.source_bucket, self.source_key):
            raise FileNotFoundError(
                f"Source object does not exist: s3://{self.source_bucket}/{self.source_key}"
            )
        
        # Perform the operation
        if self.operation == "copy":
            logger.info(
                "Copying s3://%s/%s to s3://%s/%s",
                self.source_bucket, self.source_key,
                self.dest_bucket, self.dest_key
            )
            hook.copy_object(
                self.source_bucket, self.source_key,
                self.dest_bucket, self.dest_key
            )
            
        elif self.operation == "move":
            logger.info(
                "Moving s3://%s/%s to s3://%s/%s",
                self.source_bucket, self.source_key,
                self.dest_bucket, self.dest_key
            )
            # Copy then delete for move operation
            hook.copy_object(
                self.source_bucket, self.source_key,
                self.dest_bucket, self.dest_key
            )
            hook.delete_object(self.source_bucket, self.source_key)
        
        # Verify destination if requested
        if self.verify_dest:
            if not hook.object_exists(self.dest_bucket, self.dest_key):
                raise RuntimeError(
                    f"Destination verification failed: s3://{self.dest_bucket}/{self.dest_key}"
                )
            logger.info("Destination object verified successfully")
        
        return f"Successfully {self.operation}d object to s3://{self.dest_bucket}/{self.dest_key}"