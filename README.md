# Blueprint

**⚠️ NOTE: This is currently an idea/concept and not yet implemented. The following describes the proposed functionality.**

Build reusable, validated Airflow DAG templates that anyone on your team can discover and use.

## What is Blueprint?

Blueprint helps data platform teams define reusable, parameterized DAG templates for Apache Airflow. These templates can be safely configured by other team members, like data analysts or less-experienced engineers, using simple YAML files.

With Blueprint, you can:

- ✅ Enforce **type-safe parameters** with validation
- 🚫 Get **clear error messages** when configs are invalid
- 🛠️ Use a **CLI** to validate configs before deployment
- 🔍 Automatically **discover available templates** and **generate new DAGs** from them, including directly within Astro IDE

## Why Blueprint?

In most data teams, the same kind of DAG is built over and over with small variations. This usually means lots of copy-pasting and hard-to-maintain code. Blueprint solves this by letting you:

- **Create once, use everywhere** – Write a DAG pattern once as a template
- **Reduce errors** – Validate configurations before deployment
- **Build guardrails** – Enforce your standards and best practices
- **Help non-engineers** – Let others safely define DAGs without touching Python

_Existing templates will be visible and usable by team members through the Astro IDE_
![Modal](https://github.com/user-attachments/assets/1cd09676-7431-4803-8344-81887576fe31)

## Example Workflow

### 1. Create a Blueprint template

Save this in `.astro/templates/etl_blueprints.py`:

```python
from blueprint import Blueprint
from airflow import DAG
from typing import TypedDict
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

class DailyETLConfig(TypedDict):
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

### 2. Create a YAML config

Save this as `dags/configs/customer_etl.dag.yaml`:

```yaml
blueprint: daily_etl  # Auto-generated from class name DailyETL
job_id: customer-daily-sync
source_table: raw.customers
target_table: analytics.dim_customers
schedule: "@hourly"
retries: 4
```

_Blueprint YAML configurations can be created and validated directly in Astro IDE._
![Template](https://github.com/user-attachments/assets/1f0f6aa7-3d9a-49eb-aaec-77b4ecc9c602)

## 3. Validate your config

```bash
$ blueprint lint
  customer_etl.dag.yaml - Valid
```

🎉 **Done!** Blueprint builds your DAG with ID `customer_etl`.

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

[DAG Factory](https://github.com/astronomer/dag-factory) gives full control of Airflow via YAML.

Blueprint hides that complexity behind safe, pre-built templates.

## DAG Factory

```yaml
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

## Blueprint

```yaml
blueprint: daily_etl
job_id: customer-sync
source_table: raw.customers
target_table: analytics.dim_customers
schedule: "@hourly"
```

**Use DAG Factory if:** You need full Airflow flexibility and your users understand Airflow concepts

**Use Blueprint if:** You want standardized, low-code patterns for non-Airflow users

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

Apache 2.0
