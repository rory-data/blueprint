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

The generated `.py` file follows this pattern:

```python
"""Auto-generated DAG file from Blueprint."""

from blueprint import load_template

# Load the blueprint template
ETLBlueprint = load_template("etl_blueprint", "ETLBlueprint")

# Create the DAG with validated configuration
dag = ETLBlueprint.build(
    job_id="customer_etl",
    source_table="raw.customers",
    target_table="staging.customers_clean",
    schedule="@hourly",
    retries=2,
)
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

- **Standalone DAGs**: Creates self-contained DAG files that don't require the original blueprint template to be in the dags folder
- **Version Control**: Generated files can be committed to track exactly what DAGs are deployed
- **Deployment**: Simplifies deployment by creating static DAG files
- **Debugging**: Easy to inspect the exact DAG configuration that will be used
- **Airflow Compatibility**: Generated files work with all Airflow deployment patterns

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