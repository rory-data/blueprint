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

class DailyETLConfig(TypedDict):
    dag_id: str  # Auto-provided by Blueprint
    job_id: str
    source_table: str
    target_table: str
    schedule: str
    retries: int

class DailyETL(Blueprint[DailyETLConfig]):
    # Name is auto-generated as "daily_etl" from class name
    # Or specify explicitly:
    # name = "daily_etl"
    
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

Blueprint uses TypedDict and generics for full type safety:

```python
from typing import TypedDict, Optional

class MyConfig(TypedDict):
    dag_id: str
    param1: str
    param2: int
    optional_param: Optional[str]

class MyBlueprint(Blueprint[MyConfig]):
    defaults = {
        "param2": 10,
        "optional_param": None
    }
    
    def render(self, config: MyConfig) -> DAG:
        # Full IDE autocomplete and type checking
        ...
```

For parameter descriptions:

```python
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

class AdvancedConfig(TypedDict):
    dag_id: str
    job_id: Annotated[str, "Unique identifier for this job"]
    retries: Annotated[int, "Number of retry attempts"]

class AdvancedBlueprint(Blueprint[AdvancedConfig]):
    defaults = {"retries": 2}
```

## More Examples

### Complex Parameters

Blueprints support nested objects and lists:

```python
from typing import TypedDict, Optional, List

class SourceConfig(TypedDict):
    database: str
    table: str

class NotificationConfig(TypedDict, total=False):
    email: Optional[str]
    slack: Optional[str]

class MultiSourceConfig(TypedDict):
    dag_id: str
    sources: List[SourceConfig]
    notifications: NotificationConfig

class MultiSourceETL(Blueprint[MultiSourceConfig]):
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
    owner: str
    retries: int
    email_on_failure: str

class S3ImportConfig(BaseETLConfig):
    bucket: str
    prefix: str

class BaseETL(Blueprint[BaseETLConfig]):
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
    # Inherits defaults from BaseETL if desired
    
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
 marketing_etl.dag.yaml
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
3. **Provide defaults wisely** - Common values as defaults, critical values as required
4. **Document parameters** - Use the `description` field to explain each parameter
5. **Validate in CI** - Add `blueprint lint` to your CI pipeline

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

Apache 2.0
