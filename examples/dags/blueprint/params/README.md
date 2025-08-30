# DEPRECATED: Runtime YAML DAG Generation

The files in this directory are examples of runtime YAML DAG generation,
which has been deprecated in favor of build-time DAG generation.

## Migration Guide

Instead of using YAML files to generate DAGs at runtime, use the build-time
generation approach:

### Old approach (DEPRECATED):
```yaml
# customer_etl.dag.yaml
blueprint: daily_etl
job_id: customer-daily-sync
source_table: raw.customers
target_table: analytics.dim_customers
schedule: "@daily"
retries: 3
```

### New approach (RECOMMENDED):
```python
# build_customer_dag.py
from blueprint.templates.daily_etl import DailyETLBlueprint

# Generate DAG file at build time
DailyETLBlueprint.build_template(
    output_file="dags/customer_etl.py",
    lint=True,
    job_id="customer-daily-sync",
    source_table="raw.customers",
    target_table="analytics.dim_customers",
    schedule="@daily",
    retries=3
)
```

This approach provides:
- Better IDE support and type checking
- Faster Airflow startup times
- Easier debugging and testing
- Clear separation between configuration and runtime

For more examples, see `examples/build_time_example.py`.