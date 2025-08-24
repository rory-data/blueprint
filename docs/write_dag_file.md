# Blueprint.write_dag_file() Method

The `write_dag_file()` method allows you to write rendered DAG code to a `.py` file in the dags folder, creating a standalone DAG file that can be picked up by Airflow.

## Usage

There are two ways to use this functionality:

### 1. Instance Method

```python
from blueprint import Blueprint, BaseModel

class ETLConfig(BaseModel):
    job_id: str
    source_table: str
    target_table: str
    schedule: str = "@daily"

class ETLBlueprint(Blueprint[ETLConfig]):
    def render(self, config: ETLConfig):
        # Your DAG creation logic here
        pass

# Create blueprint and config
blueprint = ETLBlueprint()
config = ETLConfig(
    job_id="customer_etl",
    source_table="raw.customers", 
    target_table="staging.customers_clean",
    schedule="@hourly"
)

# Write DAG file
file_path = blueprint.write_dag_file(config, "customer_etl")
print(f"DAG file created at: {file_path}")
```

### 2. Class Method (Convenient)

```python
# More convenient - directly from parameters
file_path = ETLBlueprint.write_dag_file_from_config(
    dag_id="customer_etl",
    job_id="customer_etl",
    source_table="raw.customers",
    target_table="staging.customers_clean", 
    schedule="@hourly"
)
```

## Generated File Structure

The generated `.py` file contains the complete rendered DAG code:

```python
"""Auto-generated DAG file from Blueprint."""

from datetime import datetime, timedelta, timezone
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

dag = DAG(
    dag_id="customer_etl",
    default_args={
        "owner": "data-team",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "email_on_failure": False,
    },
    description="ETL from raw.customers to staging.customers_clean",
    schedule="@hourly",
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["etl", "blueprint"],
)

check_source_data = BashOperator(
    task_id="check_source_data",
    dag=dag,
    bash_command="echo \"Checking if raw.customers has data...\"",
)

def extract_transform(**_):
    print("Extracting data from raw.customers")
    print("Applying transformations...")
    print("Preparing to load into staging.customers_clean")
    return {"records_processed": 1000}

etl_task = PythonOperator(
    task_id="extract_transform",
    dag=dag,
    python_callable=extract_transform,
)

load_data = BashOperator(
    task_id="load_data",
    dag=dag,
    bash_command="echo \"Loading data into staging.customers_clean...\"",
)

quality_check = BashOperator(
    task_id="data_quality_check",
    dag=dag,
    bash_command="echo \"Running quality checks on staging.customers_clean...\"",
)

check_source_data >> etl_task >> load_data >> quality_check
```

## Parameters

### `write_dag_file(config, dag_id, output_file=None)`

- **`config`** (T): The validated configuration model instance
- **`dag_id`** (str): The DAG ID to use in the generated file
- **`output_file`** (Optional[str]): Output file path. If not provided, uses `{dag_id}.py` in the Airflow dags folder

### `write_dag_file_from_config(dag_id, output_file=None, **kwargs)`

- **`dag_id`** (str): The DAG ID to use in the generated file  
- **`output_file`** (Optional[str]): Output file path. If not provided, uses `{dag_id}.py` in the Airflow dags folder
- **`**kwargs`**: Configuration parameters for the blueprint (validated by Pydantic)

## Output Location

When `output_file` is not specified, the file is written to:
- `{AIRFLOW_DAGS_FOLDER}/{dag_id}.py`

The dags folder location is determined by:
1. Airflow configuration (`core.dags_folder`)  
2. `$AIRFLOW_HOME/dags` if Airflow config is unavailable
3. `~/airflow/dags` if `AIRFLOW_HOME` is not set

## Benefits

- **Complete DAG Files**: Generates fully rendered DAG code with all tasks, operators, and configuration expanded
- **Standalone Operation**: Created files work independently without requiring blueprint templates or the blueprint package in Airflow
- **Full Visibility**: All DAG structure, tasks, and dependencies are visible in the generated code
- **Easy Debugging**: Complete DAG logic is present in the file for easy inspection and troubleshooting
- **Version Control**: Generated files can be committed to track exactly what DAGs are deployed
- **Deployment Ready**: Files can be deployed directly to any Airflow environment
- **No Runtime Dependencies**: Generated DAGs run using standard Airflow components only

## Template Name Convention

The method automatically converts Blueprint class names to template names:
- `DailyETL` → `daily_etl` 
- `MultiSourceETL` → `multi_source_etl`
- `SimpleBlueprint` → `simple_blueprint`

This follows the existing convention used by `load_template()`.

## Error Handling

The method includes proper error handling:
- Creates parent directories if they don't exist
- Validates configuration using Pydantic before generation
- Returns the full path to the created file for verification