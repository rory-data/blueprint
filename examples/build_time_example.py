"""Example of using Blueprint's build-time DAG generation.

This shows how to use Blueprint to generate DAG files at build time using *.py.j2 templates.
"""

from pydantic import BaseModel, Field
from blueprint import Blueprint


class DailyETLConfig(BaseModel):
    """Configuration for daily ETL DAG."""
    
    job_id: str = Field(..., description="Unique identifier for the DAG")
    source_table: str = Field(..., description="Source table name") 
    target_table: str = Field(..., description="Target table name")
    schedule: str = Field(default="@daily", description="DAG schedule")
    retries: int = Field(default=2, description="Number of retries")


class DailyETLBlueprint(Blueprint[DailyETLConfig]):
    """Blueprint for daily ETL operations.
    
    Uses daily_etl.py.j2 template for DAG generation.
    """
    pass  # Template rendering is handled automatically


# Example usage in a build script:
if __name__ == "__main__":
    # Generate a customer ETL DAG
    customer_dag = DailyETLBlueprint.build_template(
        output_file="dags/customer_etl.py",
        lint=True,  # Automatically lint with ruff
        job_id="customer-etl",
        source_table="raw.customers",
        target_table="staging.customers",
        schedule="@hourly",
        retries=3
    )
    
    # Generate a product ETL DAG  
    product_dag = DailyETLBlueprint.build_template(
        output_file="dags/product_etl.py",
        lint=True,
        job_id="product-etl",
        source_table="raw.products",
        target_table="staging.products",
        schedule="@daily",
        retries=2
    )
    
    print("✅ Generated DAG files with automatic linting!")