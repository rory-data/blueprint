"""Oracle to Parquet Operator for Airflow 2.10+ with Arrow integration.

This module provides an Airflow operator for extracting Oracle tables
and writing them as Parquet files on S3, preserving source schema.
"""

import logging
from typing import Any

from airflow.models import BaseOperator
from airflow.utils.context import Context

from ..hooks.oracle_hook import OracleHook
from ...utils.file_utils import FileOperations, FileConfig

logger = logging.getLogger(__name__)


class OracleToParquetOperator(BaseOperator):
    """Operator for extracting Oracle tables to Parquet with schema preservation.
    
    Extracts Oracle table data using Arrow and writes to Parquet on S3,
    preserving the source schema in the Parquet file.
    """
    
    def __init__(
        self,
        s3_bucket: str,
        s3_key: str,
        table_name: str | None = None,
        sql: str | None = None,
        oracle_conn_id: str = "oracle_default",
        aws_conn_id: str = "aws_default",
        parameters: dict[str, Any] | None = None,
        **kwargs
    ) -> None:
        """Initialize Oracle to Parquet operator.
        
        Args:
            s3_bucket: Target S3 bucket name
            s3_key: Target S3 object key for Parquet file
            table_name: Oracle table name to extract (alternative to sql)
            sql: Custom SQL query to execute (alternative to table_name)
            oracle_conn_id: Airflow connection ID for Oracle
            aws_conn_id: Airflow connection ID for AWS/S3
            parameters: Query parameters (if using sql)
            **kwargs: Additional BaseOperator arguments
        """
        super().__init__(**kwargs)
        
        if not table_name and not sql:
            raise ValueError("Must provide either table_name or sql")
        if table_name and sql:
            raise ValueError("Cannot provide both table_name and sql, choose one")
        
        self.table_name = table_name
        self.sql = sql
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.oracle_conn_id = oracle_conn_id
        self.aws_conn_id = aws_conn_id
        self.parameters = parameters or {}
    
    def execute(self, context: Context) -> str:
        """Execute the Oracle to Parquet operation with schema preservation.
        
        Args:
            context: Airflow execution context
            
        Returns:
            Status message with file location and schema info
        """
        oracle_hook = OracleHook(oracle_conn_id=self.oracle_conn_id)
        file_ops = FileOperations(FileConfig(aws_conn_id=self.aws_conn_id))
        
        # Build SQL query
        if self.table_name:
            query = f"SELECT * FROM {self.table_name}"
            logger.info("Extracting Oracle table: %s", self.table_name)
        else:
            query = self.sql
            logger.info("Executing custom Oracle query")
        
        try:
            # Execute query and get Arrow table (preserves Oracle schema)
            arrow_table = oracle_hook.execute_query_arrow(query, self.parameters)
            logger.info(
                "Oracle data extracted: %d rows, %d columns, schema preserved",
                arrow_table.num_rows, arrow_table.num_columns
            )
            
            # Log schema information
            schema_info = []
            for field in arrow_table.schema:
                schema_info.append(f"{field.name}: {field.type}")
            logger.info("Oracle schema: %s", ", ".join(schema_info))
            
            # Write Arrow table directly to S3 as Parquet (preserves schema)
            file_ops.write_parquet_to_s3(arrow_table, self.s3_bucket, self.s3_key)
            
            # Verify upload
            if file_ops.s3_hook.check_for_key(key=self.s3_key, bucket_name=self.s3_bucket):
                result_msg = (
                    f"Successfully extracted {arrow_table.num_rows} rows "
                    f"from Oracle to s3://{self.s3_bucket}/{self.s3_key} "
                    f"(schema preserved: {arrow_table.num_columns} columns)"
                )
                logger.info(result_msg)
                return result_msg
            else:
                raise RuntimeError(f"Failed to verify upload to s3://{self.s3_bucket}/{self.s3_key}")
                
        except Exception as e:
            logger.error("Oracle to Parquet extraction failed: %s", e)
            raise