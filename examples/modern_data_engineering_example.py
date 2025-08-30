"""Example of using the new core-repo architecture with Arrow and Ibis.

This example demonstrates how to use the new adapters, custom hooks/operators,
and utilities for modern data engineering workflows with Arrow as data spine.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.utils.dates import days_ago

# Import the new core-repo components
from adapters.duckdb_adapter import DuckDBAdapter, DuckDBConfig
from adapters.s3_adapter import S3Adapter, S3Config
from custom.operators.oracle_to_parquet_operator import OracleToParquetOperator
from custom.operators.duckdb_operator import DuckDBOperator
from custom.operators.parquet_processing_operator import ParquetProcessingOperator
from utils.file_utils import FileOperations, FileConfig

# Example DAG using the new architecture
dag = DAG(
    dag_id="modern_data_engineering_example",
    description="Example DAG showcasing core-repo architecture with Arrow/Ibis",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["core-repo", "example", "data-engineering", "arrow", "ibis"],
    default_args={
        "owner": "data-team",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    }
)

# Task 1: Extract Oracle table to Parquet with schema preservation
extract_oracle_table = OracleToParquetOperator(
    task_id="extract_oracle_table",
    table_name="sales.transactions",
    s3_bucket="data-lake-raw",
    s3_key="sales/transactions/{{ ds }}/transactions.parquet",
    oracle_conn_id="oracle_sales",
    aws_conn_id="aws_default",
    dag=dag
)

# Task 2: Process Parquet file using Ibis transformations
def clean_transaction_data_ibis(ibis_table):
    """Clean and transform transaction data using Ibis."""
    # Remove null values and apply transformations using Ibis
    cleaned = (
        ibis_table
        .dropna()
        .filter(ibis_table.amount > 0)
        .mutate(
            amount_usd=ibis_table.amount * ibis_table.exchange_rate,
            transaction_date=ibis_table.created_date.cast("date")
        )
    )
process_transactions = ParquetProcessingOperator(
    task_id="process_transactions",
    source_bucket="data-lake-raw",
    source_key="sales/transactions/{{ ds }}/transactions.parquet",
    dest_bucket="data-lake-processed", 
    dest_key="sales/transactions_clean/{{ ds }}/transactions_clean.parquet",
    processing_function=clean_transaction_data_ibis,
    aws_conn_id="aws_default",
    backend="polars",  # Use Polars backend for efficient processing
    dag=dag
)

# Task 3: Load processed data into DuckDB for analytics
load_to_duckdb = DuckDBOperator(
    task_id="load_to_duckdb",
    sql="""
    CREATE OR REPLACE TABLE sales_transactions AS 
    SELECT * FROM 's3://data-lake-processed/sales/transactions_clean/{{ ds }}/transactions_clean.parquet'
    """,
    duckdb_conn_id="duckdb_analytics",
    return_format="arrow",  # Use Arrow format for efficiency
    dag=dag
)

# Task 4: Run analytics queries with Ibis
run_analytics = DuckDBOperator(
    task_id="run_analytics",
    sql="""
    CREATE OR REPLACE TABLE daily_sales_summary AS
    SELECT 
        DATE(created_date) as sale_date,
        COUNT(*) as transaction_count,
        SUM(amount_usd) as total_revenue,
        AVG(amount_usd) as avg_transaction_value
    FROM sales_transactions 
    WHERE DATE(created_date) = '{{ ds }}'
    GROUP BY DATE(created_date)
    """,
    duckdb_conn_id="duckdb_analytics",
    return_format="polars",  # Use Polars for analytics
    dag=dag
)

# Task 5: Export analytics results back to S3
export_analytics = DuckDBOperator(
    task_id="export_analytics",
    export_query="SELECT * FROM daily_sales_summary",
    export_path="s3://data-lake-analytics/daily_sales/{{ ds }}/summary.parquet",
    export_format="parquet",
    duckdb_conn_id="duckdb_analytics",
    dag=dag
)

# Define task dependencies - using the new OracleToParquetOperator
extract_oracle_table >> process_transactions >> load_to_duckdb >> run_analytics >> export_analytics