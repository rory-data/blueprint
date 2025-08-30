"""Example of using the new core-repo architecture.

This example demonstrates how to use the new adapters, custom hooks/operators,
and utilities for modern data engineering workflows.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.utils.dates import days_ago

# Import the new core-repo components
from adapters.duckdb_adapter import DuckDBAdapter, DuckDBConfig
from adapters.s3_adapter import S3Adapter, S3Config
from custom.operators.oracle_to_s3_operator import OracleToS3Operator
from custom.operators.duckdb_operator import DuckDBOperator
from custom.operators.parquet_processing_operator import ParquetProcessingOperator
from utils.file_utils import FileOperations, FileConfig

# Example DAG using the new architecture
dag = DAG(
    dag_id="modern_data_engineering_example",
    description="Example DAG showcasing core-repo architecture",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["core-repo", "example", "data-engineering"],
    default_args={
        "owner": "data-team",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    }
)

# Task 1: Extract data from Oracle to S3
extract_oracle_data = OracleToS3Operator(
    task_id="extract_oracle_data",
    sql="SELECT * FROM sales.transactions WHERE created_date >= '{{ ds }}'",
    s3_bucket="data-lake-raw",
    s3_key="sales/transactions/{{ ds }}/transactions.parquet",
    oracle_conn_id="oracle_sales",
    aws_conn_id="aws_default",
    file_format="parquet",
    dag=dag
)

# Task 2: Process Parquet file (apply transformations)
def clean_transaction_data(df):
    """Clean and transform transaction data."""
    # Remove null values
    df = df.dropna()
    
    # Add calculated columns
    df["total_with_tax"] = df["amount"] * 1.08
    
    # Filter for valid transactions
    df = df[df["amount"] > 0]
    
    return df

process_transactions = ParquetProcessingOperator(
    task_id="process_transactions",
    source_bucket="data-lake-raw",
    source_key="sales/transactions/{{ ds }}/transactions.parquet",
    dest_bucket="data-lake-processed", 
    dest_key="sales/transactions_clean/{{ ds }}/transactions_clean.parquet",
    processing_function=clean_transaction_data,
    aws_conn_id="aws_default",
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
    dag=dag
)

# Task 4: Run analytics queries
run_analytics = DuckDBOperator(
    task_id="run_analytics",
    sql="""
    CREATE OR REPLACE TABLE daily_sales_summary AS
    SELECT 
        DATE(created_date) as sale_date,
        COUNT(*) as transaction_count,
        SUM(total_with_tax) as total_revenue,
        AVG(total_with_tax) as avg_transaction_value
    FROM sales_transactions 
    WHERE DATE(created_date) = '{{ ds }}'
    GROUP BY DATE(created_date)
    """,
    duckdb_conn_id="duckdb_analytics",
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

# Define task dependencies
extract_oracle_data >> process_transactions >> load_to_duckdb >> run_analytics >> export_analytics