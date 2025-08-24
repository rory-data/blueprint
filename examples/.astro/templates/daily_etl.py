from datetime import datetime, timedelta, timezone

from blueprint import BaseModel, Blueprint, Field, field_validator

CRON_EXPRESSION_MIN_SPACES = 4


class DailyETLConfig(BaseModel):
    """Configuration for daily ETL jobs."""

    job_id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$", description="Unique identifier for this job")
    source_table: str = Field(description="Table to read data from")
    target_table: str = Field(description="Table to write processed data to")
    schedule: str = Field(default="@daily", description="Cron expression or Airflow preset")
    retries: int = Field(
        default=2, ge=0, le=5, description="Number of retry attempts on task failure"
    )

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, v):
        valid_presets = ["@once", "@hourly", "@daily", "@weekly", "@monthly", "@yearly"]
        if v not in valid_presets and not (v.count(" ") >= CRON_EXPRESSION_MIN_SPACES):
            msg = f"Schedule must be one of {valid_presets} or a valid cron expression"
            raise ValueError(msg)
        return v

    @field_validator("source_table", "target_table")
    @classmethod
    def validate_table_name(cls, v):
        if "." not in v:
            msg = f"Table name must include schema (e.g., raw.customers): {v}"
            raise ValueError(msg)
        return v


class DailyETL(Blueprint[DailyETLConfig]):
    """Daily ETL job that moves data between tables with configurable scheduling."""

    def render(self, config: DailyETLConfig):
        from airflow import DAG
        from airflow.operators.bash import BashOperator
        from airflow.operators.python import PythonOperator

        default_args = {
            "owner": "data-team",
            "retries": config.retries,
            "retry_delay": timedelta(minutes=5),
            "email_on_failure": False,
        }
        dag = DAG(
            dag_id=config.job_id,
            default_args=default_args,
            description=f"ETL from {config.source_table} to {config.target_table}",
            schedule=config.schedule,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            catchup=False,
            tags=["etl", "blueprint"],
        )
        with dag:
            check_source = BashOperator(
                task_id="check_source_data",
                bash_command=f'echo "Checking if {config.source_table} has data..."',
            )

            def extract_transform(**_):
                print(f"Extracting data from {config.source_table}")
                print("Applying transformations...")
                print(f"Preparing to load into {config.target_table}")
                return {"records_processed": 1000}

            etl_task = PythonOperator(
                task_id="extract_transform",
                python_callable=extract_transform,
            )
            load_data = BashOperator(
                task_id="load_data",
                bash_command=f'echo "Loading data into {config.target_table}..."',
            )
            quality_check = BashOperator(
                task_id="data_quality_check",
                bash_command=f'echo "Running quality checks on {config.target_table}..."',
            )
            check_source >> etl_task >> load_data >> quality_check
        return dag

    def render_template(self, config: DailyETLConfig) -> str:
        """Render the DAG as a Python code template for build-time generation."""
        template = f'''"""
Daily ETL DAG: {config.job_id}
Generated from Blueprint template

Source: {config.source_table}
Target: {config.target_table}
Schedule: {config.schedule}
Retries: {config.retries}
"""

from datetime import datetime, timedelta, timezone
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# DAG configuration
default_args = {{
    "owner": "data-team",
    "retries": {config.retries},
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}}

dag = DAG(
    dag_id="{config.job_id}",
    default_args=default_args,
    description="ETL from {config.source_table} to {config.target_table}",
    schedule="{config.schedule}",
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["etl", "blueprint"],
)

# Task definitions
def extract_transform(**context):
    print("Extracting data from {config.source_table}")
    print("Applying transformations...")
    print("Preparing to load into {config.target_table}")
    return {{"records_processed": 1000}}

with dag:
    check_source = BashOperator(
        task_id="check_source_data",
        bash_command='echo "Checking if {config.source_table} has data..."',
    )

    etl_task = PythonOperator(
        task_id="extract_transform",
        python_callable=extract_transform,
    )
    
    load_data = BashOperator(
        task_id="load_data",
        bash_command='echo "Loading data into {config.target_table}..."',
    )
    
    quality_check = BashOperator(
        task_id="data_quality_check",
        bash_command='echo "Running quality checks on {config.target_table}..."',
    )
    
    check_source >> etl_task >> load_data >> quality_check
'''
        return template
