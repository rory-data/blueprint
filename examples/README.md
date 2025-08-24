# Blueprint Examples

This directory contains examples of using Blueprint to create Airflow DAGs.

## Quick Start

1. **Start Airflow with Tilt (from root directory):**
   ```bash
   # Install Tilt if you haven't already
   # https://tilt.dev/

   # From the root directory (not examples/)
   tilt up
   ```

2. **Access Airflow UI:**
   - URL: http://localhost:8080
   - Username: `admin`
   - Password: `admin`

3. **View the example DAGs:**
   - `customer-etl-python` - Created using Python API
   - `users_sync`, `products_sync`, `orders_sync` - Dynamically generated DAGs
   - `unified-analytics` - Multi-source ETL example

## Development with Tilt

Tilt provides a great development experience with:
- **Hot Reload**: Changes to Blueprint source code automatically reload in the container
- **Live Sync**: Your local changes sync instantly to the running Airflow instance
- **Build Logs**: Real-time feedback on builds and deployments
- **Resource Dashboard**: Monitor all services in the Tilt UI at http://localhost:10350

### Managing the Environment

```bash
# Start development environment
tilt up

# Stop and clean up
tilt down

# View logs
tilt logs

# Open Tilt UI
tilt ui  # or visit http://localhost:10350
```

## Directory Structure

```
examples/
├── docker-compose.yaml      # Airflow setup (used by Tilt)
├── Dockerfile              # Container definition
├── requirements.txt         # Python dependencies
├── templates/              # Blueprint template definitions
│   └── etl_blueprints.py   # Example ETL blueprints
├── dags/                   # Airflow DAGs directory
│   ├── configs/           # YAML configurations (when YAML loader is implemented)
│   │   ├── customer_etl.dag.yaml
│   │   └── sales_analytics.dag.yaml
│   └── python_api_example.py  # Python API examples
```

## Example Blueprints

### 1. DailyETL

A simple ETL blueprint that moves data from source to target table:

```python
from examples.templates.etl_blueprints import DailyETL

dag = DailyETL.build(
    job_id="my-etl",
    source_table="raw.data",
    target_table="clean.data",
    schedule="@daily"
)
```

### 2. MultiSourceETL

Combines data from multiple sources:

```python
from examples.templates.etl_blueprints import MultiSourceETL

dag = MultiSourceETL.build(
    job_id="combine-sources",
    source_tables=["raw.table1", "raw.table2"],
    target_table="analytics.combined",
    parallel=True
)
```

## Creating Your Own Blueprint

1. Create a new file in `templates/`
2. Define your config model using Pydantic
3. Create a Blueprint class that implements `render()` and optionally `render_template()`
4. Use it for both runtime and build-time DAG generation!

Example:

```python
from blueprint import Blueprint, BaseModel, Field
from airflow import DAG

class MyConfig(BaseModel):
    job_id: str
    schedule: str = "@daily"

class MyBlueprint(Blueprint[MyConfig]):
    def render(self, config: MyConfig) -> DAG:
        """Runtime DAG generation."""
        return DAG(
            dag_id=config.job_id,
            schedule=config.schedule,
            # ... your DAG logic
        )

    def render_template(self, config: MyConfig) -> str:
        """Build-time template generation."""
        return f'''
from airflow import DAG
from datetime import datetime

dag = DAG(
    dag_id="{config.job_id}",
    schedule="{config.schedule}",
    start_date=datetime(2024, 1, 1),
)
# ... your template logic
'''

# Runtime usage (existing functionality)
dag = MyBlueprint.build(job_id="my-job", schedule="@hourly")

# Build-time usage (new functionality)
template_code = MyBlueprint.build_template(job_id="my-job", schedule="@hourly")
```

## Build vs Runtime Generation

Blueprint now supports two modes of operation:

### Runtime Generation (Default)
- DAGs are created dynamically when Airflow loads them
- Use `auto_load_yaml_dags()` in your DAG files
- Flexible but requires Blueprint package in Airflow environment

### Build-time Generation (New)
- DAG files are pre-generated as Python code
- Use `blueprint build` command to generate static DAG files
- Self-contained DAG files that don't require Blueprint at runtime
- Better for production deployments and CI/CD pipelines

```bash
# Generate DAG files from YAML configs
blueprint build --config-dir configs --output-dir dags

# Generate with custom template directory
blueprint build --template-dir my-templates --output-dir generated-dags --force
```
        )

# Use it
dag = MyBlueprint.build(job_id="my-job")
```

## Validation

Blueprint uses Pydantic for validation, so you get helpful error messages:

```python
# This will raise a validation error
dag = DailyETL.build(
    job_id="invalid id!",  # Contains spaces
    source_table="customers",  # Missing schema
    retries=10  # Too many retries
)
```

## Next Steps

- Explore the template definitions in `templates/`
- Try modifying the example DAGs
- Create your own Blueprint templates
- Check out the main README for more documentation
