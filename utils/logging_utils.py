"""Logging and monitoring utilities.

This module provides utilities for setting up logging and monitoring
for data engineering workflows.
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class LoggingConfig(BaseModel):
    """Configuration for logging setup."""
    
    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    file_path: str | None = Field(
        default=None,
        description="Path to log file (logs to console if not provided)"
    )
    max_bytes: int = Field(
        default=10485760,  # 10MB
        description="Maximum log file size in bytes"
    )
    backup_count: int = Field(
        default=5,
        description="Number of backup log files to keep"
    )
    json_format: bool = Field(
        default=False,
        description="Use JSON format for structured logging"
    )


def setup_logging(config: LoggingConfig | None = None) -> None:
    """Set up logging configuration.
    
    Args:
        config: Logging configuration (uses defaults if not provided)
    """
    config = config or LoggingConfig()
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, config.level.upper(), logging.INFO)
    
    if config.json_format:
        # Structured JSON logging
        _setup_json_logging(config, numeric_level)
    else:
        # Standard text logging
        _setup_text_logging(config, numeric_level)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Log the setup
    logger = logging.getLogger(__name__)
    logger.info("Logging configured with level: %s", config.level)


def _setup_text_logging(config: LoggingConfig, level: int) -> None:
    """Set up standard text logging."""
    formatter = logging.Formatter(config.format)
    
    if config.file_path:
        # File logging with rotation
        from logging.handlers import RotatingFileHandler
        
        log_path = Path(config.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        
        # Add file handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        
        # Also add console handler for immediate feedback
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        root_logger.addHandler(console_handler)
    else:
        # Console logging only
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)


def _setup_json_logging(config: LoggingConfig, level: int) -> None:
    """Set up structured JSON logging."""
    try:
        import json_logging
    except ImportError as e:
        raise ImportError(
            "json-logging package is required for JSON logging. "
            "Install with: pip install json-logging"
        ) from e
    
    json_logging.init_non_web(enable_json=True)
    
    # Configure handlers
    handlers = []
    
    if config.file_path:
        from logging.handlers import RotatingFileHandler
        
        log_path = Path(config.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count
        )
        file_handler.setLevel(level)
        handlers.append(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    handlers.append(console_handler)
    
    # Apply configuration
    logging.basicConfig(
        level=level,
        handlers=handlers
    )


def get_logger(name: str, config: LoggingConfig | None = None) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        config: Optional logging configuration
        
    Returns:
        Configured logger instance
    """
    if config:
        setup_logging(config)
    
    return logging.getLogger(name)


def log_function_call(func_name: str, args: dict[str, Any] | None = None) -> None:
    """Log function call with arguments for debugging.
    
    Args:
        func_name: Name of the function being called
        args: Function arguments to log
    """
    logger = logging.getLogger(__name__)
    
    if args:
        sanitized_args = {k: v for k, v in args.items() if "password" not in k.lower()}
        logger.debug("Calling %s with args: %s", func_name, sanitized_args)
    else:
        logger.debug("Calling %s", func_name)


def log_performance(operation: str, duration: float, rows: int | None = None) -> None:
    """Log performance metrics for operations.
    
    Args:
        operation: Name of the operation
        duration: Duration in seconds
        rows: Number of rows processed (if applicable)
    """
    logger = logging.getLogger(__name__)
    
    if rows is not None:
        rows_per_sec = rows / duration if duration > 0 else 0
        logger.info(
            "Performance: %s completed in %.2fs (%d rows, %.0f rows/sec)",
            operation, duration, rows, rows_per_sec
        )
    else:
        logger.info("Performance: %s completed in %.2fs", operation, duration)