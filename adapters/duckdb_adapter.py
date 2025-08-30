"""DuckDB connection and query execution adapter with Ibis integration.

This module provides a standardized interface for connecting to DuckDB
using Ibis as the data spine for efficient operations.
"""

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DuckDBConfig(BaseModel):
    """Configuration for DuckDB connections."""
    
    database_path: str = Field(
        default=":memory:",
        description="Path to DuckDB database file or ':memory:' for in-memory database"
    )
    read_only: bool = Field(
        default=False,
        description="Open database in read-only mode"
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional DuckDB configuration options"
    )


class DuckDBAdapter:
    """Adapter for DuckDB connections and operations with Ibis.
    
    Provides a clean interface for DuckDB operations using Ibis
    as the data spine for efficient analytics operations.
    """
    
    def __init__(self, config: DuckDBConfig) -> None:
        """Initialize DuckDB adapter with configuration.
        
        Args:
            config: DuckDB configuration parameters
        """
        self.config = config
        self._connection = None
    
    @property
    def connection(self) -> Any:
        """Get Ibis DuckDB connection.
        
        Returns:
            Ibis DuckDB backend connection
            
        Raises:
            ImportError: If ibis or duckdb packages are not installed
        """
        if self._connection is None:
            try:
                import ibis
            except ImportError as e:
                raise ImportError(
                    "Ibis package is required. Install with: pip install 'ibis-framework[duckdb]'"
                ) from e
            
            try:
                # Create database directory if needed
                if self.config.database_path != ":memory:":
                    Path(self.config.database_path).parent.mkdir(parents=True, exist_ok=True)
                
                # Connect using Ibis
                self._connection = ibis.duckdb.connect(
                    database=self.config.database_path,
                    read_only=self.config.read_only,
                    config=self.config.config
                )
                
                logger.info("Connected to DuckDB via Ibis: %s", self.config.database_path)
                
            except Exception as e:
                logger.error("Failed to connect to DuckDB: %s", e)
                raise
        
        return self._connection
    
    def execute_query(self, query: str) -> Any:
        """Execute a query and return Ibis expression.
        
        Args:
            query: SQL query to execute
            
        Returns:
            Ibis expression/table
        """
        conn = self.connection
        table = conn.sql(query)
        logger.info("Executed query successfully")
        return table
    
    def execute_query_arrow(self, query: str) -> Any:
        """Execute a query and return results as Arrow table.
        
        Args:
            query: SQL query to execute
            
        Returns:
            Query results as pyarrow Table
        """
        table = self.execute_query(query)
        arrow_table = table.to_pyarrow()
        logger.info("Query executed, returned Arrow table with %d rows", arrow_table.num_rows)
        return arrow_table
    
    def execute_query_polars(self, query: str) -> Any:
        """Execute a query and return results as Polars DataFrame.
        
        Args:
            query: SQL query to execute
            
        Returns:
            Query results as Polars DataFrame
        """
        try:
            import polars as pl
        except ImportError as e:
            raise ImportError(
                "Polars package is required. Install with: pip install polars"
            ) from e
        
        table = self.execute_query(query)
        polars_df = table.to_polars()
        logger.info("Query executed, returned Polars DataFrame with %d rows", len(polars_df))
        return polars_df
    
    def load_data_from_file(self, file_path: str, table_name: str) -> None:
        """Load data from file into DuckDB table using Ibis.
        
        Args:
            file_path: Path to data file (CSV, Parquet, JSON, etc.)
            table_name: Name of target table
        """
        conn = self.connection
        
        # Use Ibis to read the file and create table
        if file_path.endswith('.parquet'):
            table = conn.read_parquet(file_path)
        elif file_path.endswith('.csv'):
            table = conn.read_csv(file_path)
        else:
            # Fallback to raw SQL for other formats
            query = f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM '{file_path}'"
            conn.raw_sql(query)
            logger.info("Loaded data from %s into table %s", file_path, table_name)
            return
        
        # Create the table
        conn.create_table(table_name, table, overwrite=True)
        logger.info("Loaded data from %s into table %s using Ibis", file_path, table_name)
    
    def export_to_file(self, query: str, output_path: str, format: str = "parquet") -> None:
        """Export query results to file using Ibis.
        
        Args:
            query: SQL query to execute
            output_path: Path to output file
            format: Output format (parquet, csv)
        """
        table = self.execute_query(query)
        
        if format.lower() == "parquet":
            table.to_parquet(output_path)
        elif format.lower() == "csv":
            table.to_csv(output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info("Exported query results to %s (%s format)", output_path, format)