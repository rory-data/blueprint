from datetime import datetime, timezone

from blueprint import BaseModel, Blueprint, Field


class MultiSourceETLConfig(BaseModel):
    """Configuration for ETL jobs that process multiple sources."""

    job_id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$", description="Unique identifier for this job")
    source_tables: list[str] = Field(description="List of tables to read data from")
    target_table: str = Field(description="Table to write combined data to")
    schedule: str = Field(default="@daily", description="Cron expression or Airflow preset")
    parallel: bool = Field(default=True, description="Whether to process sources in parallel")


class MultiSourceETL(Blueprint[MultiSourceETLConfig]):
    """ETL job that combines data from multiple sources."""

    def render(self, config: MultiSourceETLConfig):
        from airflow import DAG
        from airflow.operators.bash import BashOperator

        dag = DAG(
            dag_id=config.job_id,
            description=f"Combine {len(config.source_tables)} sources into {config.target_table}",
            schedule=config.schedule,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            catchup=False,
            tags=["etl", "blueprint", "multi-source"],
        )
        with dag:
            extract_tasks = []
            for source_table in config.source_tables:
                task = BashOperator(
                    task_id=f"extract_{source_table.replace('.', '_')}",
                    bash_command=f'echo "Extracting from {source_table}..."',
                )
                extract_tasks.append(task)
            combine = BashOperator(
                task_id="combine_sources",
                bash_command='echo "Combining all source data..."',
            )
            load = BashOperator(
                task_id="load_combined_data",
                bash_command=f'echo "Loading into {config.target_table}..."',
            )
            if config.parallel:
                # For parallel, each extract task goes to combine
                for task in extract_tasks:
                    task >> combine >> load
            else:
                for i in range(len(extract_tasks) - 1):
                    extract_tasks[i] >> extract_tasks[i + 1]
                if extract_tasks:
                    extract_tasks[-1] >> combine >> load
        return dag

    def render_template(self, config: MultiSourceETLConfig) -> str:
        """Render the DAG as a Python code template for build-time generation."""
        source_tasks_code = []
        for source_table in config.source_tables:
            task_name = source_table.replace('.', '_')
            source_tasks_code.append(f'''
    extract_{task_name} = BashOperator(
        task_id="extract_{task_name}",
        bash_command='echo "Extracting from {source_table}..."',
    )''')
        
        source_tasks_list = ', '.join([f"extract_{table.replace('.', '_')}" for table in config.source_tables])
        
        if config.parallel:
            task_dependencies = f"[{source_tasks_list}] >> combine_task >> load_task"
        else:
            dependencies = []
            for i in range(len(config.source_tables) - 1):
                task1 = f"extract_{config.source_tables[i].replace('.', '_')}"
                task2 = f"extract_{config.source_tables[i + 1].replace('.', '_')}"
                dependencies.append(f"{task1} >> {task2}")
            if config.source_tables:
                last_task = f"extract_{config.source_tables[-1].replace('.', '_')}"
                dependencies.append(f"{last_task} >> combine_task >> load_task")
            task_dependencies = "\\n    ".join(dependencies)

        template = f'''"""
Multi-Source ETL DAG: {config.job_id}
Generated from Blueprint template

Sources: {', '.join(config.source_tables)}
Target: {config.target_table}
Schedule: {config.schedule}
Parallel: {config.parallel}
"""

from datetime import datetime, timezone
from airflow import DAG
from airflow.operators.bash import BashOperator

dag = DAG(
    dag_id="{config.job_id}",
    description="Combine {len(config.source_tables)} sources into {config.target_table}",
    schedule="{config.schedule}",
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["etl", "blueprint", "multi-source"],
)

with dag:
    # Extract tasks for each source{''.join(source_tasks_code)}
    
    combine_task = BashOperator(
        task_id="combine_sources",
        bash_command='echo "Combining all source data..."',
    )
    
    load_task = BashOperator(
        task_id="load_combined_data",
        bash_command='echo "Loading into {config.target_table}..."',
    )
    
    # Task dependencies
    {task_dependencies}
'''
        return template
