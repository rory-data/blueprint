"""DuckDB Hook for Airflow 2.10+.

This module provides an Airflow hook for DuckDB connections
following Airflow 2.10+ best practices.
"""

import logging
from typing import Any

from airflow.hooks.base import BaseHook

from ...adapters.duckdb_adapter import DuckDBAdapter, DuckDBConfig

logger = logging.getLogger(__name__)


class DuckDBHook(BaseHook):
    """Hook for DuckDB connections in Airflow.
    
    Integrates DuckDBAdapter with Airflow's connection management system.
    """
    
    conn_name_attr = "duckdb_conn_id"
    default_conn_name = "duckdb_default"
    conn_type = "duckdb"
    hook_name = "DuckDB"
    
    def __init__(self, duckdb_conn_id: str = default_conn_name) -> None:
        """Initialize DuckDB hook.
        
        Args:
            duckdb_conn_id: Airflow connection ID for DuckDB
        """
        super().__init__()
        self.duckdb_conn_id = duckdb_conn_id
        self._adapter = None
    
    @property
    def adapter(self) -> DuckDBAdapter:
        """Get DuckDB adapter instance.
        
        Returns:
            Configured DuckDBAdapter instance
        """
        if self._adapter is None:
            conn = self.get_connection(self.duckdb_conn_id)
            
            # Extract configuration from Airflow connection
            config = DuckDBConfig(
                database_path=conn.host or ":memory:",
                read_only=conn.extra_dejson.get("read_only", False),
                config=conn.extra_dejson.get("config", {})
            )
            
            self._adapter = DuckDBAdapter(config)
        
        return self._adapter
    
    def test_connection(self) -> tuple[bool, str]:
        """Test the DuckDB connection.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            with self.adapter.connection() as conn:
                conn.execute("SELECT 1").fetchone()
            return True, "DuckDB connection test successful"
        except Exception as e:
            return False, f"DuckDB connection test failed: {e}"
    
    def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Execute a query using the adapter.
        
        Args:
            query: SQL query to execute
            parameters: Optional query parameters
            
        Returns:
            Query results
        """
        return self.adapter.execute_query(query, parameters)
    
    def execute_query_df(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Execute a query and return results as DataFrame.
        
        Args:
            query: SQL query to execute
            parameters: Optional query parameters
            
        Returns:
            Query results as pandas DataFrame
        """
        return self.adapter.execute_query_df(query, parameters)
    
    def load_data_from_file(self, file_path: str, table_name: str) -> None:
        """Load data from file into DuckDB table.
        
        Args:
            file_path: Path to data file
            table_name: Name of target table
        """
        self.adapter.load_data_from_file(file_path, table_name)
    
    def export_to_file(self, query: str, output_path: str, format: str = "parquet") -> None:
        """Export query results to file.
        
        Args:
            query: SQL query to execute
            output_path: Path to output file
            format: Output format (parquet, csv, json)
        """
        self.adapter.export_to_file(query, output_path, format)