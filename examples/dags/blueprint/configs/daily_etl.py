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
    """Daily ETL job that moves data between tables with configurable scheduling.

    This blueprint uses a Jinja2 template (daily_etl.j2) to generate DAGs,
    following DRY principles with a single source of truth for the DAG structure.
    """
    pass
