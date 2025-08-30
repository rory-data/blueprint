"""DuckDB Operator for Airflow 2.10+ with Ibis integration.

This module provides an Airflow operator for executing DuckDB operations
using Ibis as the data spine for efficient analytics operations.
"""

import logging
from typing import Any

from airflow.models import BaseOperator
from airflow.utils.context import Context

from ..hooks.duckdb_hook import DuckDBHook

logger = logging.getLogger(__name__)


class DuckDBOperator(BaseOperator):
    """Operator for executing DuckDB operations with Ibis.
    
    Executes SQL queries, loads data, or exports data using DuckDB
    with Ibis integration for efficient data operations.
    """
    
    def __init__(
        self,
        sql: str | None = None,
        duckdb_conn_id: str = "duckdb_default",
        load_file: str | None = None,
        load_table: str | None = None,
        export_query: str | None = None,
        export_path: str | None = None,
        export_format: str = "parquet",
        return_format: str = "arrow",
        **kwargs
    ) -> None:
        """Initialize DuckDB operator.
        
        Args:
            sql: SQL query to execute
            duckdb_conn_id: Airflow connection ID for DuckDB
            load_file: File path to load data from
            load_table: Table name to load data into
            export_query: Query to export results from
            export_path: Path to export results to
            export_format: Export format (parquet, csv)
            return_format: Format for query results ('arrow', 'polars', 'ibis')
            **kwargs: Additional BaseOperator arguments
        """
        super().__init__(**kwargs)
        self.sql = sql
        self.duckdb_conn_id = duckdb_conn_id
        self.load_file = load_file
        self.load_table = load_table
        self.export_query = export_query
        self.export_path = export_path
        self.export_format = export_format
        self.return_format = return_format
        
        # Validation
        if not any([sql, load_file, export_query]):
            raise ValueError("Must provide either sql, load_file, or export_query")
        
        if load_file and not load_table:
            raise ValueError("load_table is required when load_file is provided")
        
        if export_query and not export_path:
            raise ValueError("export_path is required when export_query is provided")
        
        if return_format not in ["arrow", "polars", "ibis"]:
            raise ValueError("return_format must be 'arrow', 'polars', or 'ibis'")
    
    def execute(self, context: Context) -> Any:
        """Execute the DuckDB operation using Ibis.
        
        Args:
            context: Airflow execution context
            
        Returns:
            Query results in specified format
        """
        hook = DuckDBHook(duckdb_conn_id=self.duckdb_conn_id)
        
        # Load data from file
        if self.load_file and self.load_table:
            logger.info("Loading data from %s into table %s using Ibis", self.load_file, self.load_table)
            hook.load_data_from_file(self.load_file, self.load_table)
            return f"Loaded data into {self.load_table}"
        
        # Export query results
        if self.export_query and self.export_path:
            logger.info("Exporting query results to %s using Ibis", self.export_path)
            hook.export_to_file(self.export_query, self.export_path, self.export_format)
            return f"Exported results to {self.export_path}"
        
        # Execute SQL query
        if self.sql:
            logger.info("Executing DuckDB query with %s return format", self.return_format)
            
            if self.return_format == "arrow":
                results = hook.execute_query_arrow(self.sql)
                logger.info("Query completed, returned Arrow table with %d rows", results.num_rows)
            elif self.return_format == "polars":
                results = hook.execute_query_polars(self.sql)
                logger.info("Query completed, returned Polars DataFrame with %d rows", len(results))
            elif self.return_format == "ibis":
                results = hook.execute_query_ibis(self.sql)
                logger.info("Query completed, returned Ibis table expression")
            
            return results
        
        return None