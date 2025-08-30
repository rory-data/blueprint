"""Oracle Hook for Airflow 2.10+ using Oracle Provider.

This module provides an Airflow hook for Oracle database operations
using the official Oracle provider with Arrow and Polars integration.
"""

import logging
from typing import Any

from airflow.hooks.base import BaseHook

logger = logging.getLogger(__name__)


class OracleHook(BaseHook):
    """Hook for Oracle database operations using Oracle Provider.
    
    Uses the official Airflow Oracle provider with additional
    convenience methods for Arrow and Polars integration.
    """
    
    conn_name_attr = "oracle_conn_id"
    default_conn_name = "oracle_default"
    conn_type = "oracle"
    hook_name = "Oracle"
    
    def __init__(self, oracle_conn_id: str = default_conn_name) -> None:
        """Initialize Oracle hook.
        
        Args:
            oracle_conn_id: Airflow connection ID for Oracle
        """
        super().__init__()
        self.oracle_conn_id = oracle_conn_id
        self._oracle_hook = None
    
    @property
    def oracle_hook(self) -> Any:
        """Get Airflow Oracle hook instance.
        
        Returns:
            Airflow OracleHook from Oracle provider
            
        Raises:
            ImportError: If Oracle provider is not installed
        """
        if self._oracle_hook is None:
            try:
                from airflow.providers.oracle.hooks.oracle import OracleHook as AirflowOracleHook
            except ImportError as e:
                raise ImportError(
                    "Airflow Oracle provider is required. "
                    "Install with: pip install apache-airflow-providers-oracle"
                ) from e
            
            self._oracle_hook = AirflowOracleHook(oracle_conn_id=self.oracle_conn_id)
            logger.info("Created Oracle hook with connection: %s", self.oracle_conn_id)
        
        return self._oracle_hook
    
    def test_connection(self) -> tuple[bool, str]:
        """Test the Oracle connection.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            self.oracle_hook.test_connection()
            return True, "Oracle connection test successful"
        except Exception as e:
            return False, f"Oracle connection test failed: {e}"
    
    def execute_query_arrow(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Execute a query and return results as Arrow table.
        
        Args:
            query: SQL query to execute
            parameters: Optional query parameters
            
        Returns:
            Query results as pyarrow Table
        """
        try:
            import pyarrow as pa
        except ImportError as e:
            raise ImportError(
                "PyArrow package is required. Install with: pip install pyarrow"
            ) from e
        
        # Get data using Airflow's Oracle hook
        records = self.oracle_hook.get_records(sql=query, parameters=parameters)
        
        if not records:
            logger.info("Query returned no results")
            return pa.table([])
        
        # Get column names from cursor description
        cursor_desc = self.oracle_hook.get_cursor().description
        columns = [desc[0] for desc in cursor_desc] if cursor_desc else []
        
        # Convert to Arrow table
        if columns:
            # Create dictionary for Arrow table
            data_dict = {}
            for i, col_name in enumerate(columns):
                data_dict[col_name] = [row[i] for row in records]
            arrow_table = pa.table(data_dict)
        else:
            # Fallback if no column info available
            arrow_table = pa.table([list(row) for row in records])
        
        logger.info("Query executed, returned Arrow table with %d rows", arrow_table.num_rows)
        return arrow_table
    
    def execute_query_polars(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Execute a query and return results as Polars DataFrame.
        
        Args:
            query: SQL query to execute
            parameters: Optional query parameters
            
        Returns:
            Query results as Polars DataFrame
        """
        try:
            import polars as pl
        except ImportError as e:
            raise ImportError(
                "Polars package is required. Install with: pip install polars"
            ) from e
        
        # Get Arrow table first
        arrow_table = self.execute_query_arrow(query, parameters)
        
        # Convert to Polars
        polars_df = pl.from_arrow(arrow_table)
        logger.info("Query executed, returned Polars DataFrame with %d rows", len(polars_df))
        return polars_df
    
    def execute_dml(self, query: str, parameters: dict[str, Any] | None = None) -> int:
        """Execute a DML statement.
        
        Args:
            query: DML statement to execute
            parameters: Optional query parameters
            
        Returns:
            Number of rows affected
        """
        try:
            self.oracle_hook.run(sql=query, parameters=parameters, autocommit=True)
            # Oracle hook doesn't return row count, so we return 1 for success
            logger.info("DML executed successfully")
            return 1
        except Exception as e:
            logger.error("DML execution failed: %s", e)
            raise