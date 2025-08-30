"""Configuration management utilities.

This module provides utilities for managing configuration
across different environments and deployment scenarios.
"""

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EnvironmentConfig(BaseModel):
    """Configuration for different environments."""
    
    environment: str = Field(
        default="development",
        description="Environment name (development, staging, production)"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    config_file_path: str | None = Field(
        default=None,
        description="Path to additional configuration file"
    )


class ConfigManager:
    """Manager for application configuration.
    
    Provides centralized configuration management with environment-specific
    overrides and validation following SOLID principles.
    """
    
    def __init__(self, config: EnvironmentConfig | None = None) -> None:
        """Initialize configuration manager.
        
        Args:
            config: Environment configuration
        """
        self.config = config or EnvironmentConfig()
        self._loaded_config: dict[str, Any] = {}
    
    def load_config_from_file(self, config_path: str | Path) -> dict[str, Any]:
        """Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Loaded configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file format is not supported
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        suffix = config_path.suffix.lower()
        
        if suffix == ".yaml" or suffix == ".yml":
            return self._load_yaml_config(config_path)
        elif suffix == ".toml":
            return self._load_toml_config(config_path)
        elif suffix == ".json":
            return self._load_json_config(config_path)
        else:
            raise ValueError(f"Unsupported configuration file format: {suffix}")
    
    def _load_yaml_config(self, config_path: Path) -> dict[str, Any]:
        """Load YAML configuration file."""
        try:
            import yaml
        except ImportError as e:
            raise ImportError(
                "PyYAML package is required for YAML configs. Install with: pip install pyyaml"
            ) from e
        
        with config_path.open() as f:
            config = yaml.safe_load(f)
        
        logger.info("Loaded YAML configuration from %s", config_path)
        return config or {}
    
    def _load_toml_config(self, config_path: Path) -> dict[str, Any]:
        """Load TOML configuration file."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError as e:
                raise ImportError(
                    "tomli package is required for TOML configs on Python <3.11. "
                    "Install with: pip install tomli"
                ) from e
        
        with config_path.open("rb") as f:
            config = tomllib.load(f)
        
        logger.info("Loaded TOML configuration from %s", config_path)
        return config
    
    def _load_json_config(self, config_path: Path) -> dict[str, Any]:
        """Load JSON configuration file."""
        import json
        
        with config_path.open() as f:
            config = json.load(f)
        
        logger.info("Loaded JSON configuration from %s", config_path)
        return config
    
    def get_environment_config(self) -> dict[str, Any]:
        """Get configuration with environment variable overrides.
        
        Returns:
            Configuration dictionary with environment overrides
        """
        config = self._loaded_config.copy()
        
        # Apply environment variable overrides
        env_prefix = "CORE_REPO_"
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                config_key = key[len(env_prefix):].lower()
                config[config_key] = value
                logger.debug("Applied environment override: %s = %s", config_key, value)
        
        return config
    
    def validate_config(self, config: dict[str, Any], schema: type[BaseModel]) -> BaseModel:
        """Validate configuration against a Pydantic schema.
        
        Args:
            config: Configuration dictionary to validate
            schema: Pydantic model class for validation
            
        Returns:
            Validated configuration instance
        """
        try:
            validated = schema(**config)
            logger.info("Configuration validation successful")
            return validated
        except Exception as e:
            logger.error("Configuration validation failed: %s", e)
            raise
    
    def save_config(self, config: dict[str, Any], output_path: str | Path, format: str = "yaml") -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration dictionary to save
            output_path: Path to save configuration
            format: Output format (yaml, toml, json)
        """
        output_path = Path(output_path)
        format = format.lower()
        
        if format == "yaml":
            self._save_yaml_config(config, output_path)
        elif format == "toml":
            self._save_toml_config(config, output_path)
        elif format == "json":
            self._save_json_config(config, output_path)
        else:
            raise ValueError(f"Unsupported output format: {format}")
    
    def _save_yaml_config(self, config: dict[str, Any], output_path: Path) -> None:
        """Save configuration as YAML."""
        try:
            import yaml
        except ImportError as e:
            raise ImportError(
                "PyYAML package is required. Install with: pip install pyyaml"
            ) from e
        
        with output_path.open("w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.info("Saved YAML configuration to %s", output_path)
    
    def _save_toml_config(self, config: dict[str, Any], output_path: Path) -> None:
        """Save configuration as TOML."""
        try:
            import tomli_w
        except ImportError as e:
            raise ImportError(
                "tomli-w package is required for writing TOML. Install with: pip install tomli-w"
            ) from e
        
        with output_path.open("wb") as f:
            tomli_w.dump(config, f)
        
        logger.info("Saved TOML configuration to %s", output_path)
    
    def _save_json_config(self, config: dict[str, Any], output_path: Path) -> None:
        """Save configuration as JSON."""
        import json
        
        with output_path.open("w") as f:
            json.dump(config, f, indent=2, sort_keys=False)
        
        logger.info("Saved JSON configuration to %s", output_path)