"""Core-repo - Modern data engineering framework for Airflow 2.10+.

This package provides adapters, hooks, operators, and utilities
for enterprise data workflows with dependency injection patterns.
"""

__version__ = "0.0.1a2"

# Core Blueprint functionality
from .blueprint import Blueprint
from .blueprint.errors import (
    BlueprintError,
    BlueprintNotFoundError,
    ConfigurationError,
    DuplicateBlueprintError,
    DuplicateDAGIdError,
    YAMLParseError,
)
from .blueprint.errors import (
    ValidationError as BlueprintValidationError,
)
from .blueprint.loaders import (
    discover_blueprints,
    get_blueprint_info,
    load_blueprint,
)
from .blueprint.models import (
    Any,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from .blueprint.registry import registry
from .blueprint.template_loader import (
    load_template,
    setup_template_path,
)

# Adapters for external systems
from .adapters.duckdb_adapter import DuckDBAdapter, DuckDBConfig
from .adapters.oracle_adapter import OracleAdapter, OracleConfig
from .adapters.s3_adapter import S3Adapter, S3Config

# Custom Airflow components
from .custom.hooks.duckdb_hook import DuckDBHook
from .custom.hooks.oracle_hook import OracleHook
from .custom.hooks.s3_hook import S3Hook
from .custom.operators.duckdb_operator import DuckDBOperator
from .custom.operators.oracle_to_parquet_operator import OracleToParquetOperator
from .custom.operators.oracle_to_s3_operator import OracleToS3Operator
from .custom.operators.parquet_processing_operator import ParquetProcessingOperator
from .custom.operators.s3_to_s3_operator import S3ToS3Operator

# Utilities
from .utils.config_manager import ConfigManager
from .utils.file_utils import FileOperations, FileConfig
from .utils.logging_utils import LoggingUtils

__all__ = [
    # Core Blueprint
    "Any",
    "BaseModel",
    "Blueprint",
    "BlueprintError",
    "BlueprintNotFoundError",
    "BlueprintValidationError",
    "ConfigDict",
    "ConfigurationError",
    "DuplicateBlueprintError",
    "DuplicateDAGIdError",
    "Field",
    "ValidationError",
    "YAMLParseError",
    "discover_blueprints",
    "field_validator",
    "get_blueprint_info",
    "load_blueprint",
    "load_template",
    "model_validator",
    "registry",
    "setup_template_path",
    # Adapters
    "DuckDBAdapter",
    "DuckDBConfig",
    "OracleAdapter",
    "OracleConfig", 
    "S3Adapter",
    "S3Config",
    # Hooks
    "DuckDBHook",
    "OracleHook",
    "S3Hook",
    # Operators
    "DuckDBOperator",
    "OracleToParquetOperator",
    "OracleToS3Operator",
    "ParquetProcessingOperator",
    "S3ToS3Operator",
    # Utils
    "ConfigManager",
    "FileOperations",
    "FileConfig",
    "LoggingUtils",
]