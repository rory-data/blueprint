from datetime import UTC, datetime, timedelta, timezone

from airflow.providers.standard.operators import BashOperator
from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import DAG

# DAG configuration
default_args = {
    "owner": "{{ config.owner }}",
    "retries": {{config.retries}},
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

dag = DAG(
    dag_id="{{ config.job_id }}",
    default_args=default_args,
    description="ETL from {{ config.source_table }} to {{ config.target_table }}",
    schedule="{{ config.schedule }}",
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    catchup=False,
    tags={"etl", "blueprint"},
)


# Task definitions
def extract_transform(**context):
    print("Extracting data from {{ config.source_table }}")
    print("Applying transformations...")
    print("Preparing to load into {{ config.target_table }}")
    return {"records_processed": 1000}


with dag:
    check_source_data = BashOperator(
        task_id="check_source_data",
        bash_command='echo "Checking if {{ config.source_table }} has data..."',
    )

    etl_transform = PythonOperator(
        task_id="etl_transform",
        python_callable=extract_transform,
    )

    load_data = BashOperator(
        task_id="load_data",
        bash_command='echo "Loading data into {{ config.target_table }}..."',
    )

    data_quality_check = BashOperator(
        task_id="data_quality_check",
        bash_command='echo "Running quality checks on {{ config.target_table }}..."',
    )

    # Define task dependencies
    check_source_data >> etl_transform >> load_data >> data_quality_check
