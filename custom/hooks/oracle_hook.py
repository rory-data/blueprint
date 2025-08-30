"""Oracle Hook for Airflow 2.10+.

This module provides an Airflow hook for Oracle database operations
following Airflow 2.10+ best practices.
"""

import logging
from typing import Any

from airflow.hooks.base import BaseHook

from ...adapters.oracle_adapter import OracleAdapter, OracleConfig

logger = logging.getLogger(__name__)


class OracleHook(BaseHook):
    """Hook for Oracle database operations in Airflow.
    
    Integrates OracleAdapter with Airflow's connection management system.
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
        self._adapter = None
    
    @property
    def adapter(self) -> OracleAdapter:
        """Get Oracle adapter instance.
        
        Returns:
            Configured OracleAdapter instance
        """
        if self._adapter is None:
            conn = self.get_connection(self.oracle_conn_id)
            
            # Extract configuration from Airflow connection
            config = OracleConfig(
                host=conn.host,
                port=conn.port or 1521,
                username=conn.login,
                password=conn.password,
                service_name=conn.extra_dejson.get("service_name"),
                sid=conn.extra_dejson.get("sid"),
                encoding=conn.extra_dejson.get("encoding", "UTF-8"),
                nencoding=conn.extra_dejson.get("nencoding", "UTF-8"),
                threaded=conn.extra_dejson.get("threaded", True)
            )
            
            self._adapter = OracleAdapter(config)
        
        return self._adapter
    
    def test_connection(self) -> tuple[bool, str]:
        """Test the Oracle connection.
        
        Returns:
            Tuple of (success, message)
        """
        return self.adapter.test_connection(), "Oracle connection test completed"
    
    def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[tuple]:
        """Execute a query using the adapter.
        
        Args:
            query: SQL query to execute
            parameters: Optional query parameters
            
        Returns:
            Query results as list of tuples
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
    
    def execute_dml(self, query: str, parameters: dict[str, Any] | None = None) -> int:
        """Execute a DML statement.
        
        Args:
            query: DML statement to execute
            parameters: Optional query parameters
            
        Returns:
            Number of rows affected
        """
        return self.adapter.execute_dml(query, parameters)
    
    def execute_many(self, query: str, parameters: list[dict[str, Any]]) -> int:
        """Execute a statement with multiple parameter sets.
        
        Args:
            query: SQL statement to execute
            parameters: List of parameter dictionaries
            
        Returns:
            Total number of rows affected
        """
        return self.adapter.execute_many(query, parameters)