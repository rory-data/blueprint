"""Oracle database connection adapter.

This module provides a standardized interface for connecting to Oracle
databases and executing queries with proper connection pooling and error handling.
"""

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OracleConfig(BaseModel):
    """Configuration for Oracle database connections."""
    
    host: str = Field(description="Oracle database host")
    port: int = Field(default=1521, description="Oracle database port")
    service_name: str | None = Field(
        default=None,
        description="Oracle service name (use either service_name or sid)"
    )
    sid: str | None = Field(
        default=None,
        description="Oracle SID (use either service_name or sid)"
    )
    username: str = Field(description="Database username")
    password: str = Field(description="Database password")
    encoding: str = Field(default="UTF-8", description="Character encoding")
    nencoding: str = Field(default="UTF-8", description="National character encoding")
    threaded: bool = Field(default=True, description="Enable threaded mode")


class OracleAdapter:
    """Adapter for Oracle database connections and operations.
    
    Provides a clean interface for Oracle operations with proper
    resource management and error handling following SOLID principles.
    """
    
    def __init__(self, config: OracleConfig) -> None:
        """Initialize Oracle adapter with configuration.
        
        Args:
            config: Oracle configuration parameters
        """
        self.config = config
    
    def _get_dsn(self) -> str:
        """Build Oracle DSN from configuration.
        
        Returns:
            Oracle DSN string
            
        Raises:
            ValueError: If neither service_name nor sid is provided
        """
        if self.config.service_name:
            return f"{self.config.host}:{self.config.port}/{self.config.service_name}"
        elif self.config.sid:
            return f"{self.config.host}:{self.config.port}:{self.config.sid}"
        else:
            raise ValueError("Either service_name or sid must be provided")
    
    @contextmanager
    def connection(self) -> Iterator[Any]:
        """Get an Oracle connection with automatic cleanup.
        
        Yields:
            Oracle connection object
            
        Raises:
            ImportError: If oracledb package is not installed
            Exception: If connection cannot be established
        """
        try:
            import oracledb
        except ImportError as e:
            raise ImportError(
                "oracledb package is required. Install with: pip install oracledb"
            ) from e
        
        conn = None
        try:
            dsn = self._get_dsn()
            conn = oracledb.connect(
                user=self.config.username,
                password=self.config.password,
                dsn=dsn,
                encoding=self.config.encoding,
                nencoding=self.config.nencoding,
                threaded=self.config.threaded
            )
            
            logger.info("Connected to Oracle: %s", dsn)
            yield conn
            
        except Exception as e:
            logger.error("Failed to connect to Oracle: %s", e)
            raise
        finally:
            if conn:
                conn.close()
                logger.info("Closed Oracle connection")
    
    def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[tuple]:
        """Execute a query and return results.
        
        Args:
            query: SQL query to execute
            parameters: Optional query parameters
            
        Returns:
            Query results as list of tuples
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            try:
                if parameters:
                    cursor.execute(query, parameters)
                else:
                    cursor.execute(query)
                
                results = cursor.fetchall()
                logger.info("Query executed successfully, %d rows returned", len(results))
                return results
            finally:
                cursor.close()
    
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
                df = pd.read_sql(query, conn, params=parameters)
            else:
                df = pd.read_sql(query, conn)
            
            logger.info("Query executed successfully, DataFrame shape: %s", df.shape)
            return df
    
    def execute_dml(self, query: str, parameters: dict[str, Any] | None = None) -> int:
        """Execute a DML statement (INSERT, UPDATE, DELETE).
        
        Args:
            query: DML statement to execute
            parameters: Optional query parameters
            
        Returns:
            Number of rows affected
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            try:
                if parameters:
                    cursor.execute(query, parameters)
                else:
                    cursor.execute(query)
                
                row_count = cursor.rowcount
                conn.commit()
                logger.info("DML executed successfully, %d rows affected", row_count)
                return row_count
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def execute_many(self, query: str, parameters: list[dict[str, Any]]) -> int:
        """Execute a statement with multiple parameter sets.
        
        Args:
            query: SQL statement to execute
            parameters: List of parameter dictionaries
            
        Returns:
            Total number of rows affected
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, parameters)
                row_count = cursor.rowcount
                conn.commit()
                logger.info(
                    "Batch execution completed, %d rows affected across %d statements",
                    row_count, len(parameters)
                )
                return row_count
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def test_connection(self) -> bool:
        """Test the Oracle connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM DUAL")
                cursor.close()
            logger.info("Oracle connection test successful")
            return True
        except Exception as e:
            logger.error("Oracle connection test failed: %s", e)
            return False