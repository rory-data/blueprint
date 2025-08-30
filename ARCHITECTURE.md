# Core-Repo: Modern Data Engineering Framework

This repository has been refactored to align with modern data engineering architecture patterns, focusing on build-time DAG generation and modular, reusable components.

## Architecture Overview

The core-repo follows SOLID principles and provides three main module categories:

### 🔌 Adapters (`/adapters`)
Connection adapters for external systems with standardized interfaces:
- **DuckDBAdapter**: DuckDB connections and query execution
- **S3Adapter**: S3 operations (read/write/list)
- **OracleAdapter**: Oracle database connections

### 🛠️ Custom (`/custom`)
Airflow 2.10+ compatible hooks and operators:
- **Hooks**: Custom hooks for external systems integration
- **Operators**: Reusable data processing operators

### 🔧 Utils (`/utils`)
Helper modules for common activities:
- **FileOperations**: pyarrow integration for Parquet files on S3
- **ConfigManager**: Configuration management across environments
- **LoggingUtils**: Centralized logging and monitoring utilities

## Key Principles

- **Build-time DAG generation**: No runtime dynamic generation for better performance
- **SOLID principles**: Clean separation of concerns and dependency injection
- **DRY principle**: Reusable components across different DAGs
- **YAGNI principle**: Simple, focused implementations
- **Type safety**: Full Pydantic validation and Python 3.11+ type hints

## Quick Start

### 1. Install with data engineering dependencies:
```bash
pip install -e .[data-engineering]
```

### 2. Use adapters for external system connections:
```python
from adapters.s3_adapter import S3Adapter, S3Config
from adapters.duckdb_adapter import DuckDBAdapter, DuckDBConfig

# Configure S3 adapter
s3_config = S3Config(region_name="us-west-2")
s3_adapter = S3Adapter(s3_config)

# List files in bucket
files = s3_adapter.list_objects("my-bucket", prefix="data/")
```

### 3. Build DAGs with custom operators:
```python
from custom.operators.oracle_to_s3_operator import OracleToS3Operator

# Extract data from Oracle to S3
extract_task = OracleToS3Operator(
    task_id="extract_sales_data",
    sql="SELECT * FROM sales.transactions",
    s3_bucket="data-lake",
    s3_key="sales/transactions.parquet",
    oracle_conn_id="oracle_default"
)
```

### 4. Process files with utilities:
```python
from utils.file_utils import FileOperations

file_ops = FileOperations()
df = file_ops.read_parquet_to_pandas("my-bucket", "data/file.parquet")
```

## Build-time Generation

The framework focuses on build-time DAG generation for better performance and maintainability:

```python
from blueprint import Blueprint
DailyETLBlueprint.build_template(
    output_file="dags/customer_etl.py",
    **config_params
)
```

## Dependency Groups

Install only what you need:

- **Base**: `pip install core-repo`
- **S3 operations**: `pip install core-repo[s3]`
- **DuckDB**: `pip install core-repo[duckdb]`
- **Oracle**: `pip install core-repo[oracle]`
- **Full data engineering**: `pip install core-repo[data-engineering]`

## Examples

See `examples/modern_data_engineering_example.py` for a complete example of using the new architecture in a real DAG.