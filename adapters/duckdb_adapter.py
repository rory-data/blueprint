"""DuckDB connection and query execution adapter.

This module provides a standardized interface for connecting to DuckDB
and executing queries with proper resource management and error handling.
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

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
    """Adapter for DuckDB connections and operations.
    
    Provides a clean interface for DuckDB operations with proper
    resource management and error handling following SOLID principles.
    """
    
    def __init__(self, config: DuckDBConfig) -> None:
        """Initialize DuckDB adapter with configuration.
        
        Args:
            config: DuckDB configuration parameters
        """
        self.config = config
        self._connection = None
    
    @contextmanager
    def connection(self) -> Iterator[Any]:
        """Get a DuckDB connection with automatic cleanup.
        
        Yields:
            DuckDB connection object
            
        Raises:
            ImportError: If duckdb package is not installed
            Exception: If connection cannot be established
        """
        try:
            import duckdb
        except ImportError as e:
            raise ImportError(
                "DuckDB package is required. Install with: pip install duckdb"
            ) from e
        
        conn = None
        try:
            # Create database directory if needed
            if self.config.database_path != ":memory:":
                Path(self.config.database_path).parent.mkdir(parents=True, exist_ok=True)
            
            conn = duckdb.connect(
                database=self.config.database_path,
                read_only=self.config.read_only,
                config=self.config.config
            )
            
            logger.info("Connected to DuckDB: %s", self.config.database_path)
            yield conn
            
        except Exception as e:
            logger.error("Failed to connect to DuckDB: %s", e)
            raise
        finally:
            if conn:
                conn.close()
                logger.info("Closed DuckDB connection")
    
    def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Execute a query and return results.
        
        Args:
            query: SQL query to execute
            parameters: Optional query parameters
            
        Returns:
            Query results as DuckDB relation
        """
        with self.connection() as conn:
            if parameters:
                return conn.execute(query, parameters).fetchall()
            return conn.execute(query).fetchall()
    
    def execute_query_df(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Execute a query and return results as pandas DataFrame.
        
        Args:
            query: SQL query to execute
            parameters: Optional query parameters
            
        Returns:
            Query results as pandas DataFrame
            
        Raises:
            ImportError: If pandas is not installed
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "Pandas package is required for DataFrame operations. Install with: pip install pandas"
            ) from e
        
        with self.connection() as conn:
            if parameters:
                return conn.execute(query, parameters).df()
            return conn.execute(query).df()
    
    def load_data_from_file(self, file_path: str, table_name: str) -> None:
        """Load data from file into DuckDB table.
        
        Args:
            file_path: Path to data file (CSV, Parquet, JSON, etc.)
            table_name: Name of target table
        """
        with self.connection() as conn:
            # DuckDB auto-detects file format
            query = f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM '{file_path}'"
            conn.execute(query)
            logger.info("Loaded data from %s into table %s", file_path, table_name)
    
    def export_to_file(self, query: str, output_path: str, format: str = "parquet") -> None:
        """Export query results to file.
        
        Args:
            query: SQL query to execute
            output_path: Path to output file
            format: Output format (parquet, csv, json)
        """
        with self.connection() as conn:
            if format.lower() == "parquet":
                export_query = f"COPY ({query}) TO '{output_path}' (FORMAT PARQUET)"
            elif format.lower() == "csv":
                export_query = f"COPY ({query}) TO '{output_path}' (FORMAT CSV, HEADER)"
            elif format.lower() == "json":
                export_query = f"COPY ({query}) TO '{output_path}' (FORMAT JSON)"
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            conn.execute(export_query)
            logger.info("Exported query results to %s (%s format)", output_path, format)