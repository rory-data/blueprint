# Blueprint Workflows

This guide covers common workflows when using Blueprint.

## Creating Your First Blueprint

### 1. Set up the templates directory

```bash
mkdir -p .astro/templates
```

### 2. Create a blueprint file

```python
# .astro/templates/etl_blueprints.py
from blueprint import Blueprint
from airflow import DAG
from typing import TypedDict

class SimpleETLConfig(TypedDict):
    dag_id: str  # Auto-provided by Blueprint
    source: str  # Source data location
    destination: str  # Destination for processed data

class SimpleETL(Blueprint[SimpleETLConfig]):
    # Name auto-generated as "simple_etl" from class name
    
    def render(self, config: SimpleETLConfig) -> DAG:
        from airflow.operators.python import PythonOperator
        from datetime import datetime
        
        with DAG(
            dag_id=config["dag_id"],
            start_date=datetime(2024, 1, 1),
            schedule="@daily",
            catchup=False
        ) as dag:
            PythonOperator(
                task_id="process_data",
                python_callable=lambda: print(f"ETL: {config['source']} → {config['destination']}")
            )
        return dag
```

### 3. Create a configuration

The easiest way is to use the interactive scaffolding:

```bash
$ blueprint new
? What should we name your DAG? my_first_etl
? Which blueprint would you like to use? 
  ❯ simple_etl - Simple ETL pipeline
    daily_etl - Daily batch ETL job
    streaming_pipeline - Real-time data pipeline
? Enter source (Source data location): s3://raw-data/events
? Enter destination (Destination for processed data): s3://processed-data/events

Created: dags/configs/my_first_etl.dag.yaml
```

Or create it directly if you know the blueprint:

```bash
# Direct creation
$ blueprint new simple_etl my_first_etl
```

Or create it manually:

```yaml
# dags/configs/my_first_etl.dag.yaml
blueprint: simple_etl
source: s3://raw-data/events
destination: s3://processed-data/events
```

### 4. Validate the configuration

```bash
$ blueprint lint dags/configs/my_first_etl.dag.yaml
✓ my_first_etl.dag.yaml - Valid
```

## Managing Complex Blueprints

### Using Nested Parameters

For blueprints that need structured configuration:

```python
from typing import TypedDict, Optional, List

class SourceConfig(TypedDict):
    type: str
    location: str
    table: Optional[str]
    auth_method: Optional[str]

class TransformationConfig(TypedDict):
    deduplication: bool
    aggregation_window: str
    filters: List[dict]

class DataPipelineConfig(TypedDict):
    dag_id: str
    sources: List[SourceConfig]
    transformations: TransformationConfig
    destinations: List[str]

class DataPipeline(Blueprint[DataPipelineConfig]):
    def render(self, config: DataPipelineConfig) -> DAG:
        # Type-safe access to nested structure
        for source in config["sources"]:
            # IDE autocomplete works here!
            print(f"Processing {source['type']} from {source['location']}")
```

Configuration:
```yaml
blueprint: data_pipeline
sources:
  - type: database
    location: postgres://prod/users
    table: user_events
  - type: api
    location: https://api.example.com/events
    auth_method: oauth2
transformations:
  deduplication: true
  aggregation_window: 1h
  filters:
    - field: event_type
      operator: in
      values: [click, purchase]
destinations:
  - s3://analytics/processed/
  - bigquery://project.dataset.table
```

### Blueprint Inheritance Pattern

Share common configuration across multiple blueprints:

```python
from datetime import timedelta

# Base config with common parameters
class BaseScheduledJobConfig(TypedDict):
    dag_id: str
    schedule: str
    retries: int
    retry_delay: int  # Seconds between retries
    email_on_failure: str
    owner: str

# Specific config inheriting from base
class DatabaseExportConfig(BaseScheduledJobConfig):
    connection_id: str  # Airflow connection ID
    query: str  # SQL query to execute
    output_format: str  # Output format

class BaseScheduledJob(Blueprint[BaseScheduledJobConfig]):
    defaults = {
        "schedule": "@daily",
        "retries": 2,
        "retry_delay": 300,
        "email_on_failure": "data-alerts@company.com",
        "owner": "data-team"
    }
    
    def get_default_args(self, config: BaseScheduledJobConfig):
        return {
            "owner": config["owner"],
            "retries": config["retries"],
            "retry_delay": timedelta(seconds=config["retry_delay"]),
            "email_on_failure": [config["email_on_failure"]]
        }

class DatabaseExport(Blueprint[DatabaseExportConfig]):
    defaults = {
        **BaseScheduledJob.defaults,
        "output_format": "parquet"
    }
    
    def render(self, config: DatabaseExportConfig) -> DAG:
        from airflow import DAG
        from airflow.providers.postgres.operators.postgres import PostgresOperator
        
        with DAG(
            dag_id=config["dag_id"],
            schedule=config["schedule"],
            default_args=self.get_default_args(config),
            start_date=datetime(2024, 1, 1)
        ) as dag:
            PostgresOperator(
                task_id="export_data",
                postgres_conn_id=config["connection_id"],
                sql=config["query"]
            )
        return dag
```

## Development Workflow

### 1. Blueprint Development Cycle

```bash
# Edit your blueprint
vim .astro/templates/my_blueprint.py

# Test with a sample config
cat > test_config.dag.yaml << EOF
blueprint: my_blueprint
param1: value1
param2: value2
EOF

# Validate
blueprint lint test_config.dag.yaml

# Check what parameters are available
blueprint describe my_blueprint
```

### 2. Debugging Blueprint Errors

When you encounter an error:

```bash
$ blueprint lint
✗ broken_config.dag.yaml
  Line 5: Type error for parameter 'retries'
  
  Expected: int
  Got: str ("two")
  
  Your configuration:
    4 | schedule: "@hourly"
    5 | retries: "two"
    6 | email_on_failure: "alerts@company.com"
```

Fix by updating the configuration:
```yaml
retries: 2  # Changed from "two" to 2
```

### 3. Testing Blueprints Locally

Create a test script to validate blueprint rendering:

```python
# test_blueprint.py
from blueprint import load_blueprint, load_config

# Load blueprint and config
bp = load_blueprint("my_blueprint")
config = load_config("test_config.dag.yaml")

# Test rendering
dag = bp.render(config)
print(f"Successfully created DAG: {dag.dag_id}")
print(f"Tasks: {[task.task_id for task in dag.tasks]}")
```

## Scaffolding New DAGs

### Interactive Scaffolding (Primary Interface)

The main way to create new DAGs is with the interactive interface:

```bash
$ blueprint new
? What should we name your DAG? customer_sync
? Which blueprint would you like to use?
  ❯ daily_etl - Daily batch ETL job
    hourly_sync - Hourly data synchronization  
    ml_training - Machine learning training pipeline
? Enter job_id (Unique identifier for this job): customer-daily-sync
? Enter source_table (Table to read from): raw.customers
? Enter target_table (Table to write to): analytics.dim_customers  
? Enter schedule (default: @daily): @hourly
? Enter retries (default: 2): 3

Created: dags/configs/customer_sync.dag.yaml
```

The generated file includes all parameters with comments:

```yaml
# dags/configs/customer_sync.dag.yaml
blueprint: daily_etl
# Unique identifier for this job
job_id: customer-daily-sync
# Table to read from  
source_table: raw.customers
# Table to write to
target_table: analytics.dim_customers
# Schedule interval
schedule: "@hourly" 
# Number of retries
retries: 3
```

### Direct Scaffolding

If you know exactly what you want:

```bash
# Create with blueprint and DAG name
$ blueprint new daily_etl customer_sync

# Create at specific path
$ blueprint new dags/configs/prod/customer_sync.dag.yaml daily_etl

# Create with parameter overrides
$ blueprint new daily_etl customer_sync \
    --set job_id=customer-sync \
    --set source_table=raw.customers \
    --set target_table=analytics.dim_customers
```

### Batch Scaffolding

Create multiple similar configs:

```bash
# Create configs for multiple tables
for table in users orders products; do
  blueprint new daily_etl ${table}_etl \
    --set job_id="${table}-sync" \
    --set source_table="raw.${table}" \
    --set target_table="analytics.dim_${table}"
done
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/validate-dags.yml
name: Validate DAG Configurations

on:
  pull_request:
    paths:
      - 'dags/configs/*.dag.yaml'
      - '.astro/templates/**'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install Blueprint
        run: pip install astronomer-blueprint
      
      - name: Validate configurations
        run: blueprint lint --exit-code
      
      - name: List available blueprints
        run: blueprint list
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: blueprint-lint
        name: Validate Blueprint Configs
        entry: blueprint lint
        language: system
        files: \.dag\.yaml$
        pass_filenames: true
```

## Migration Strategies

### Migrating from Copy-Paste DAGs

1. **Identify patterns** in your existing DAGs:
```bash
# Find similar DAGs
grep -r "PostgresOperator" dags/ | cut -d: -f1 | sort | uniq -c | sort -nr
```

2. **Extract common patterns** into a blueprint:
```python
class LegacyPostgresConfig(TypedDict):
    dag_id: str
    query_file: str  # Path to SQL file
    connection_id: str  # Airflow connection ID
    pool: str  # Airflow pool name

class LegacyPostgres(Blueprint[LegacyPostgresConfig]):
    defaults = {
        "connection_id": "postgres_default",
        "pool": "default_pool"
    }
```

3. **Create configs** for each existing DAG:
```yaml
# dags/configs/daily_revenue_report.dag.yaml
blueprint: legacy_postgres
query_file: sql/revenue_report.sql
connection_id: analytics_db
```

4. **Validate all migrations**:
```bash
# Validate all at once
blueprint lint

# Or validate specific ones during migration
for config in dags/configs/*.dag.yaml; do
    echo "Checking $config..."
    blueprint lint "$config"
done
```

### Handling Breaking Changes

When you need to update a blueprint but can't update all consumers:

1. **Create a new blueprint** instead of modifying the existing one:
```python
# Instead of modifying 'etl_job', create 'etl_job_v2'
class ETLJobV2Config(TypedDict):
    dag_id: str
    sources: List[dict]  # Changed from single source

class ETLJobV2(Blueprint[ETLJobV2Config]):
    pass
```

2. **Document the migration path**:
```python
class ETLJobConfig(TypedDict):
    dag_id: str
    source: str  # Old single source structure

class ETLJob(Blueprint[ETLJobConfig]):
    # Keep old structure for backward compatibility
    # Add deprecation warning in docstring
    """
    DEPRECATED: Use ETLJobV2 instead.
    This blueprint will be removed in v2.0.
    """
```

3. **Provide migration tooling**:
```bash
# migration_script.py
import yaml

def migrate_etl_config(old_config_path):
    with open(old_config_path) as f:
        config = yaml.safe_load(f)
    
    if config.get('blueprint') == 'etl_job':
        # Convert single source to list
        config['blueprint'] = 'etl_job_v2'
        config['sources'] = [{'location': config.pop('source')}]
    
    return config
```

## Best Practices

### 1. Parameter Design

- **Be explicit**: `database_connection_id` over `conn_id`
- **Group related parameters**: Use nested dicts for related settings
- **Provide sensible defaults**: But don't hide critical parameters
- **Document thoroughly**: Every parameter should have a description

### 2. Blueprint Organization

```
.astro/templates/
├── __init__.py
├── common/
│   ├── __init__.py
│   └── base_blueprints.py    # Shared base classes
├── etl/
│   ├── __init__.py
│   ├── batch_processing.py
│   └── streaming.py
└── ml/
    ├── __init__.py
    ├── training.py
    └── inference.py
```

### 3. Configuration Management

```
dags/configs/
├── prod/
│   ├── critical_etl.dag.yaml
│   └── revenue_report.dag.yaml
├── staging/
│   ├── test_pipeline.dag.yaml
│   └── experimental_ml.dag.yaml
└── README.md  # Document what each config does
```

### 4. Validation Beyond Schema

Add custom validation in your blueprints:

```python
def render(self, config):
    # Validate business logic
    if config["schedule"] == "@hourly" and config["retries"] > 3:
        raise ValueError("Hourly jobs shouldn't retry more than 3 times")
    
    # Validate dependencies exist
    if config.get("upstream_dag"):
        # Check that upstream DAG exists in Airflow
        pass
```

## Troubleshooting

### Common Issues

1. **Blueprint not found**
```bash
$ blueprint lint
✗ Error: Blueprint 'my_blueprint' not found

Available blueprints:
  - daily_etl
  - streaming_pipeline
  
Check: Is your blueprint file in .astro/templates/?
Check: Does your class inherit from Blueprint[ConfigType]?
```

2. **Import errors in blueprint**
```bash
$ blueprint lint
✗ Error loading blueprint 'data_pipeline': No module named 'pandas'

Blueprint files are loaded at validation time.
Ensure all imports are available or use lazy imports:

def render(self, config):
    import pandas as pd  # Import inside method
```

3. **Conflicting blueprint names**
```bash
$ blueprint list
⚠ Warning: Multiple blueprints named 'etl_job' found:
  - .astro/templates/etl.py:15
  - .astro/templates/legacy/old_etl.py:8
  
The most recently loaded blueprint will be used.
```

### Debug Mode

Run with verbose output for debugging:

```bash
# See what Blueprint is doing
BLUEPRINT_DEBUG=1 blueprint lint

# Check which templates directory is being used
blueprint info

# Test blueprint loading
python -c "from blueprint import list_blueprints; print(list_blueprints())"
```