# Blueprint

Create reusable Airflow DAG templates with validated configurations.

## What is Blueprint?

Blueprint allows data platform engineers to create parameterized DAG templates that data engineers, data analysts and other team members can easily configure through simple YAML files. It provides:

- **Type-safe parameters** with validation
- **Clear error messages** when configurations are invalid
- **Auto-discovery** of DAG configurations
- **CLI tools** for validating configs before deployment

## Why Blueprint?

In many organizations, data platform teams need to support numerous similar DAGs with slight variations. Blueprint solves common problems:

- **Eliminate copy-paste DAGs** - Define patterns once, reuse everywhere
- **Enforce best practices** - Bake standards into your blueprints
- **Reduce errors** - Validate configurations before deployment
- **Empower non-engineers** - YAML configs are easier than Python code

## Quick Example

**1. Define a blueprint** (`.astro/templates/etl_blueprints.py`):

```python
from blueprint import Blueprint
from airflow import DAG
from typing import TypedDict
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

class DailyETLConfig(TypedDict):
    dag_id: str  # Auto-provided by Blueprint
    job_id: Annotated[str, "Unique identifier for this job"]
    source_table: Annotated[str, "Table to read data from"]
    target_table: Annotated[str, "Table to write processed data to"]
    schedule: Annotated[str, "Cron expression or Airflow preset (@daily, @hourly, etc.)"]
    retries: Annotated[int, "Number of retry attempts on task failure"]

class DailyETL(Blueprint[DailyETLConfig]):
    """Daily ETL job that moves data between tables with configurable scheduling."""
    
    # Name is auto-generated as "daily_etl" from class name
    # Or specify explicitly:
    # name = "daily_etl_job"
    
    # Default values defined as class attributes
    defaults = {
        "schedule": "@daily",
        "retries": 2
    }

    def render(self, config: DailyETLConfig) -> DAG:
        from airflow.operators.python import PythonOperator
        from datetime import datetime

        with DAG(
            dag_id=config["dag_id"],
            schedule=config["schedule"],
            start_date=datetime(2024, 1, 1),
            catchup=False,
            default_args={"retries": config["retries"]}
        ) as dag:
            PythonOperator(
                task_id="extract_transform_load",
                python_callable=lambda: print(
                    f"Moving data from {config['source_table']} to {config['target_table']}"
                )
            )
        return dag
```

**2. Configure instances** (`dags/configs/customer_etl.dag.yaml`):

```yaml
blueprint: daily_etl  # Auto-generated from class name DailyETL
job_id: customer-daily-sync
source_table: raw.customers
target_table: analytics.dim_customers
schedule: "@hourly"
retries: 4
```

**3. Validate your config**:

```bash
$ blueprint lint
 customer_etl.dag.yaml - Valid
```

That's it! Blueprint automatically generates a DAG with ID `customer_etl` from your configuration.

## Type Safety

Blueprint uses TypedDict with `Annotated` types for full type safety and self-documenting parameters:

```python
from typing import TypedDict, Optional
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

class MyConfig(TypedDict):
    dag_id: str
    param1: Annotated[str, "Main parameter for the job"]
    param2: Annotated[int, "Secondary parameter with default"]
    optional_param: Annotated[Optional[str], "Optional parameter that can be null"]

class MyBlueprint(Blueprint[MyConfig]):
    """My blueprint that does something useful."""
    
    defaults = {
        "param2": 10,
        "optional_param": None
    }
    
    def render(self, config: MyConfig) -> DAG:
        # Full IDE autocomplete and type checking
        ...
```

These descriptions appear in:
- CLI help: `blueprint describe my_blueprint`
- Interactive prompts: `blueprint new`
- Generated config files as comments

## More Examples

### Complex Parameters

Blueprints support nested objects and lists:

```python
from typing import TypedDict, Optional, List
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

class SourceConfig(TypedDict):
    database: Annotated[str, "Database connection name"]
    table: Annotated[str, "Table to extract data from"]

class NotificationConfig(TypedDict, total=False):
    email: Annotated[Optional[str], "Email address for job notifications"]
    slack: Annotated[Optional[str], "Slack channel for alerts (e.g., #data-alerts)"]

class MultiSourceConfig(TypedDict):
    dag_id: str
    sources: Annotated[List[SourceConfig], "List of data sources to process"]
    notifications: Annotated[NotificationConfig, "Notification settings for job status"]

class MultiSourceETL(Blueprint[MultiSourceConfig]):
    """ETL pipeline that processes multiple data sources in parallel."""
    
    defaults = {
        "notifications": {"email": None, "slack": None}
    }

    def render(self, config: MultiSourceConfig) -> DAG:
        # Access nested data with type safety
        for source in config["sources"]:
            print(f"Processing {source['table']} from {source['database']}")
```

```yaml
blueprint: multi_source_etl
sources:
  - database: postgres
    table: users
  - database: mysql
    table: orders
notifications:
  email: data-team@company.com
  slack: "#data-alerts"
```

### Blueprint Inheritance

Use standard Python inheritance to share common parameters:

```python
class BaseETLConfig(TypedDict):
    dag_id: str
    owner: Annotated[str, "Team or person responsible for the DAG"]
    retries: Annotated[int, "Number of retry attempts on task failure"]
    email_on_failure: Annotated[str, "Email address for failure notifications"]

class S3ImportConfig(BaseETLConfig):
    bucket: Annotated[str, "S3 bucket name to import from"]
    prefix: Annotated[str, "S3 key prefix to filter objects"]

class BaseETL(Blueprint[BaseETLConfig]):
    """Base blueprint with common ETL parameters and error handling."""
    
    defaults = {
        "owner": "data-team",
        "retries": 2,
        "email_on_failure": "alerts@company.com"
    }
    
    def get_default_args(self, config: BaseETLConfig):
        return {
            "owner": config["owner"],
            "retries": config["retries"],
            "email_on_failure": [config["email_on_failure"]]
        }

class S3Import(Blueprint[S3ImportConfig]):
    """Import data from S3 with configurable bucket and prefix."""
    
    # Inherits defaults from BaseETL if desired
    defaults = {
        **BaseETL.defaults,
        # Add S3-specific defaults here
    }
    
    def render(self, config: S3ImportConfig) -> DAG:
        # Has access to all BaseETLConfig fields plus S3-specific ones
        default_args = self.get_default_args(config)
        # ... create DAG with S3 operators
```

## Installation

```bash
pip install astronomer-blueprint
```

## Configuration

Blueprint looks for templates in `.astro/templates/` by default. Override with:

```bash
export BLUEPRINT_TEMPLATES_DIR=/path/to/templates
```

## CLI Commands

```bash
# Validate all configs
blueprint lint

# Validate specific config
blueprint lint dags/configs/my_job.dag.yaml

# List available blueprints
blueprint list

# Show blueprint parameters
blueprint describe daily_etl

# Interactive scaffolding (primary interface)
blueprint new
# Prompts for: DAG name, blueprint selection, parameters

# Direct scaffolding with specific blueprint
blueprint new daily_etl my_new_etl

# Scaffold to specific path
blueprint new dags/configs/prod/my_new_etl.dag.yaml daily_etl

# Quick mode with parameter overrides
blueprint new daily_etl my_new_etl --set job_id=customer-sync --set retries=3
```

## Error Messages

Blueprint provides clear, actionable error messages:

```bash
$ blueprint lint
✗ marketing_etl.dag.yaml
  Line 3: Missing required parameter 'source_table' for blueprint 'daily_etl'

  Your configuration:
    2 | blueprint: daily_etl
    3 | job_id: "marketing-sync"
    4 | target_table: "analytics.marketing_facts"

  Add the missing parameter:
    3 | job_id: "marketing-sync"
  + 4 | source_table: "raw.marketing_events"
    5 | target_table: "analytics.marketing_facts"
```

## Best Practices

1. **Keep blueprints focused** - Each blueprint should represent one type of workflow
2. **Use descriptive parameter names** - `source_table` is clearer than `src`
3. **Always add parameter descriptions** - Use `Annotated[type, "description"]` for all parameters
4. **Document your blueprints** - Add docstrings to blueprint classes explaining their purpose
5. **Provide defaults wisely** - Common values as defaults, critical values as required
6. **Validate in CI** - Add `blueprint lint` to your CI pipeline

## How is this different from DAG Factory?

Blueprint and [DAG Factory](https://github.com/astronomer/dag-factory) solve different problems:

**DAG Factory** is a YAML interface to Airflow that can express the full power of Airflow:
```yaml
# dag-factory approach - exposes all Airflow complexity
my_dag:
  default_args:
    owner: 'data-team'
    retries: 2
    retry_delay_seconds: 300
  start_date: 2024-01-01
  schedule_interval: '@daily'
  tasks:
    extract_data:
      operator: airflow.operators.python.PythonOperator
      python_callable_name: extract_from_api
      python_callable_file: /opt/airflow/dags/etl/extract.py
    transform_data:
      operator: airflow.operators.python.PythonOperator
      dependencies: [extract_data]
      # ... many more Airflow-specific configurations
```

**Blueprint** is a focused abstraction that hides Airflow complexity:
```yaml
# blueprint approach - only business logic exposed
blueprint: daily_etl
job_id: customer-sync
source_table: raw.customers
target_table: analytics.dim_customers
schedule: "@hourly"
```

**When to use each:**
- **Use DAG Factory** when you need full Airflow flexibility and your users understand Airflow concepts
- **Use Blueprint** when you want to hide Airflow complexity and provide domain-specific abstractions

Blueprint is ideal for data platform teams who want to create standardized patterns while empowering analysts and other team members who shouldn't need to understand Airflow internals.

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

Apache 2.0
