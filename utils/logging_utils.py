"""Logging and monitoring utilities.

This module provides utilities for setting up logging and monitoring
for data engineering workflows with performance tracking.
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


class LoggingUtils:
    """Utility class for logging and performance monitoring."""
    
    def __init__(self, config: LoggingConfig | None = None) -> None:
        """Initialize logging utilities.
        
        Args:
            config: Logging configuration
        """
        self.config = config or LoggingConfig()
        self._logger = None
    
    @property
    def logger(self) -> logging.Logger:
        """Get configured logger instance.
        
        Returns:
            Configured logger instance
        """
        if self._logger is None:
            self._logger = logging.getLogger(__name__)
            self.setup_logging()
        return self._logger
    
    def setup_logging(self) -> None:
        """Set up logging configuration."""
        # Convert string level to logging constant
        numeric_level = getattr(logging, self.config.level.upper(), logging.INFO)
        
        if self.config.json_format:
            # Structured JSON logging
            self._setup_json_logging(numeric_level)
        else:
            # Standard text logging
            self._setup_text_logging(numeric_level)
        
        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        self.logger.info("Logging configured with level: %s", self.config.level)
    
    def _setup_text_logging(self, level: int) -> None:
        """Set up standard text logging."""
        formatter = logging.Formatter(self.config.format)
        
        if self.config.file_path:
            # File logging with rotation
            from logging.handlers import RotatingFileHandler
            
            log_path = Path(self.config.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=self.config.max_bytes,
                backupCount=self.config.backup_count
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
    
    def _setup_json_logging(self, level: int) -> None:
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
        
        if self.config.file_path:
            from logging.handlers import RotatingFileHandler
            
            log_path = Path(self.config.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=self.config.max_bytes,
                backupCount=self.config.backup_count
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
    
    def log_function_call(self, func_name: str, args: dict[str, Any] | None = None) -> None:
        """Log function call with arguments for debugging.
        
        Args:
            func_name: Name of the function being called
            args: Function arguments to log
        """
        if args:
            sanitized_args = {k: v for k, v in args.items() if "password" not in k.lower()}
            self.logger.debug("Calling %s with args: %s", func_name, sanitized_args)
        else:
            self.logger.debug("Calling %s", func_name)
    
    def log_performance(self, operation: str, duration: float, rows: int | None = None) -> None:
        """Log performance metrics for operations.
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
            rows: Number of rows processed (if applicable)
        """
        if rows is not None:
            rows_per_sec = rows / duration if duration > 0 else 0
            self.logger.info(
                "Performance: %s completed in %.2fs (%d rows, %.0f rows/sec)",
                operation, duration, rows, rows_per_sec
            )
        else:
            self.logger.info("Performance: %s completed in %.2fs", operation, duration)


# function for logging setup
def setup_logging(config: LoggingConfig | None = None) -> None:
    """Set up logging configuration.
    
    Args:
        config: Logging configuration (uses defaults if not provided)
    """
    utils = LoggingUtils(config)
    utils.setup_logging()