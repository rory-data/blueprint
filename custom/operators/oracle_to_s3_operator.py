"""Oracle to S3 Operator for Airflow 2.10+.

This module provides an Airflow operator for extracting data from Oracle
and storing it in S3 as Parquet files.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any

from airflow.models import BaseOperator
from airflow.utils.context import Context

from ..hooks.oracle_hook import OracleHook
from ..hooks.s3_hook import S3Hook

logger = logging.getLogger(__name__)


class OracleToS3Operator(BaseOperator):
    """Operator for extracting data from Oracle to S3.
    
    Executes Oracle queries and stores results as Parquet files in S3
    following modern Airflow patterns.
    """
    
    def __init__(
        self,
        sql: str,
        s3_bucket: str,
        s3_key: str,
        oracle_conn_id: str = "oracle_default",
        aws_conn_id: str = "aws_default",
        parameters: dict[str, Any] | None = None,
        file_format: str = "parquet",
        chunk_size: int = 10000,
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
            file_format: Output format (parquet, csv)
            chunk_size: Number of rows to process in chunks
            **kwargs: Additional BaseOperator arguments
        """
        super().__init__(**kwargs)
        self.sql = sql
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.oracle_conn_id = oracle_conn_id
        self.aws_conn_id = aws_conn_id
        self.parameters = parameters or {}
        self.file_format = file_format.lower()
        self.chunk_size = chunk_size
        
        if self.file_format not in ["parquet", "csv"]:
            raise ValueError("file_format must be 'parquet' or 'csv'")
    
    def execute(self, context: Context) -> str:
        """Execute the Oracle to S3 operation.
        
        Args:
            context: Airflow execution context
            
        Returns:
            Status message with file location
        """
        oracle_hook = OracleHook(oracle_conn_id=self.oracle_conn_id)
        s3_hook = S3Hook(aws_conn_id=self.aws_conn_id)
        
        logger.info("Executing Oracle query and transferring to S3")
        
        try:
            # Execute query and get DataFrame
            df = oracle_hook.execute_query_df(self.sql, self.parameters)
            logger.info("Oracle query executed, %d rows retrieved", len(df))
            
            # Create temporary file for the data
            with tempfile.NamedTemporaryFile(suffix=f".{self.file_format}", delete=False) as temp_file:
                temp_path = Path(temp_file.name)
                
                # Write data to temporary file
                if self.file_format == "parquet":
                    df.to_parquet(temp_path, index=False)
                elif self.file_format == "csv":
                    df.to_csv(temp_path, index=False)
                
                logger.info("Data written to temporary file: %s", temp_path)
                
                # Upload to S3
                with temp_path.open("rb") as f:
                    data = f.read()
                    s3_hook.write_object(self.s3_bucket, self.s3_key, data)
                
                # Clean up temporary file
                temp_path.unlink()
                
            # Verify upload
            if s3_hook.object_exists(self.s3_bucket, self.s3_key):
                result_msg = f"Successfully transferred {len(df)} rows to s3://{self.s3_bucket}/{self.s3_key}"
                logger.info(result_msg)
                return result_msg
            else:
                raise RuntimeError(f"Failed to verify upload to s3://{self.s3_bucket}/{self.s3_key}")
                
        except Exception as e:
            logger.error("Oracle to S3 transfer failed: %s", e)
            raise