"""Oracle to S3 Operator for Airflow 2.10+ with Arrow integration.

This module provides an Airflow operator for extracting data from Oracle
and storing it in S3 as Parquet files using Arrow for data spine.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any

from airflow.models import BaseOperator
from airflow.utils.context import Context

from ..hooks.oracle_hook import OracleHook
from ...utils.file_utils import FileOperations, FileConfig

logger = logging.getLogger(__name__)


class OracleToS3Operator(BaseOperator):
    """Operator for extracting data from Oracle to S3 using Arrow.
    
    Executes Oracle queries and stores results as Parquet files in S3
    following modern Airflow patterns with Arrow as data spine.
    """
    
    def __init__(
        self,
        sql: str,
        s3_bucket: str,
        s3_key: str,
        oracle_conn_id: str = "oracle_default",
        aws_conn_id: str = "aws_default",
        parameters: dict[str, Any] | None = None,
        preserve_schema: bool = True,
        **kwargs
    ) -> None:
        """Initialize Oracle to S3 operator.
        
        Args:
            sql: SQL query to execute on Oracle
            s3_bucket: Target S3 bucket name
            s3_key: Target S3 object key
            oracle_conn_id: Airflow connection ID for Oracle
            aws_conn_id: Airflow connection ID for AWS/S3
            parameters: Query parameters
            preserve_schema: Whether to preserve Oracle schema in Parquet
            **kwargs: Additional BaseOperator arguments
        """
        super().__init__(**kwargs)
        self.sql = sql
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.oracle_conn_id = oracle_conn_id
        self.aws_conn_id = aws_conn_id
        self.parameters = parameters or {}
        self.preserve_schema = preserve_schema
    
    def execute(self, context: Context) -> str:
        """Execute the Oracle to S3 operation using Arrow.
        
        Args:
            context: Airflow execution context
            
        Returns:
            Status message with file location
        """
        oracle_hook = OracleHook(oracle_conn_id=self.oracle_conn_id)
        file_ops = FileOperations(FileConfig(aws_conn_id=self.aws_conn_id))
        
        logger.info("Executing Oracle query and transferring to S3 using Arrow")
        
        try:
            # Execute query and get Arrow table (preserves schema)
            arrow_table = oracle_hook.execute_query_arrow(self.sql, self.parameters)
            logger.info("Oracle query executed, %d rows retrieved as Arrow table", arrow_table.num_rows)
            
            # Write Arrow table directly to S3 as Parquet (preserves schema)
            file_ops.write_parquet_to_s3(arrow_table, self.s3_bucket, self.s3_key)
            
            # Verify upload using S3 hook
            s3_hook = file_ops.s3_hook
            if s3_hook.check_for_key(key=self.s3_key, bucket_name=self.s3_bucket):
                result_msg = f"Successfully transferred {arrow_table.num_rows} rows to s3://{self.s3_bucket}/{self.s3_key}"
                if self.preserve_schema:
                    result_msg += " (Oracle schema preserved in Parquet)"
                logger.info(result_msg)
                return result_msg
            else:
                raise RuntimeError(f"Failed to verify upload to s3://{self.s3_bucket}/{self.s3_key}")
                
        except Exception as e:
            logger.error("Oracle to S3 transfer failed: %s", e)
            raise