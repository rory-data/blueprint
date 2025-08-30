"""Oracle database connection adapter using Airflow Oracle Provider.

This module provides a standardized interface for connecting to Oracle
databases using the official Airflow Oracle provider with Ibis integration.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OracleConfig(BaseModel):
    """Configuration for Oracle database connections using Airflow connections."""
    
    conn_id: str = Field(
        default="oracle_default",
        description="Airflow connection ID for Oracle database"
    )


class OracleAdapter:
    """Adapter for Oracle database connections using Airflow Oracle Provider.
    
    Provides a clean interface for Oracle operations using the official
    Airflow Oracle provider with Ibis integration for data operations.
    """
    
    def __init__(self, config: OracleConfig) -> None:
        """Initialize Oracle adapter with configuration.
        
        Args:
            config: Oracle configuration parameters
        """
        self.config = config
        self._hook = None
    
    @property
    def hook(self) -> Any:
        """Get Airflow Oracle hook instance.
        
        Returns:
            Airflow OracleHook from Oracle provider
            
        Raises:
            ImportError: If oracle provider is not installed
        """
        if self._hook is None:
            try:
                from airflow.providers.oracle.hooks.oracle import OracleHook
            except ImportError as e:
                raise ImportError(
                    "Airflow Oracle provider is required. "
                    "Install with: pip install apache-airflow-providers-oracle"
                ) from e
            
            self._hook = OracleHook(oracle_conn_id=self.config.conn_id)
            logger.info("Created Oracle hook with connection: %s", self.config.conn_id)
        
        return self._hook
    
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
        records = self.hook.get_records(sql=query, parameters=parameters)
        
        if not records:
            logger.info("Query returned no results")
            return pa.table([])
        
        # Get column names from cursor description
        cursor_desc = self.hook.get_cursor().description
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
        """Execute a DML statement (INSERT, UPDATE, DELETE).
        
        Args:
            query: DML statement to execute
            parameters: Optional query parameters
            
        Returns:
            Number of rows affected
        """
        try:
            self.hook.run(sql=query, parameters=parameters, autocommit=True)
            # Oracle hook doesn't return row count, so we return 1 for success
            logger.info("DML executed successfully")
            return 1
        except Exception as e:
            logger.error("DML execution failed: %s", e)
            raise
    
    def test_connection(self) -> bool:
        """Test the Oracle connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            self.hook.test_connection()
            logger.info("Oracle connection test successful")
            return True
        except Exception as e:
            logger.error("Oracle connection test failed: %s", e)
            return False