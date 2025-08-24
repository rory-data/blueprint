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
    """ETL job that combines data from multiple sources.

    This blueprint uses a Jinja2 template (multi_source_etl.j2) to generate DAGs,
    following DRY principles with a single source of truth for the DAG structure.
    """
    pass
