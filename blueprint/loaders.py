"""YAML loading and blueprint discovery functionality."""

from pathlib import Path
from typing import Any

import yaml

from blueprint.core import Blueprint
from blueprint.errors import ConfigurationError, YAMLParseError
from blueprint.registry import BlueprintRegistry, registry


def load_blueprint(
    blueprint_name: str, template_dir: str | None = None
) -> type[Blueprint]:
    """Load a blueprint class by name.

    Args:
        blueprint_name: Name of the blueprint (e.g., 'daily_etl')
        template_dir: Directory containing blueprint templates

    Returns:
        The Blueprint class

    Raises:
        BlueprintNotFoundError: If blueprint not found
        DuplicateBlueprintError: If multiple blueprints with same name
    """
    if template_dir:
        # Create a temporary registry for the specific template directory
        temp_registry = BlueprintRegistry()

        # Override the get_template_dirs method to use the provided directory
        temp_registry.get_template_dirs = lambda: [Path(template_dir)]  # type: ignore[method-assign]

        # Discover blueprints in the specified directory
        temp_registry.discover_blueprints(force=True)

        return temp_registry.get_blueprint(blueprint_name)
    # Use the global registry
    registry.discover_blueprints()
    return registry.get_blueprint(blueprint_name)


def discover_blueprints(template_dir: str | None = None) -> list[dict[str, Any]]:
    """Discover all available blueprints.

    Args:
        template_dir: Directory containing blueprint templates

    Returns:
        List of blueprint information dictionaries
    """
    if template_dir:
        # Create a temporary registry for the specific template directory
        temp_registry = BlueprintRegistry()

        # Override the get_template_dirs method to use the provided directory
        temp_registry.get_template_dirs = lambda: [Path(template_dir)]  # type: ignore[method-assign]

        # Discover blueprints in the specified directory
        temp_registry.discover_blueprints(force=True)

        return temp_registry.list_blueprints()
    # Use the global registry
    registry.discover_blueprints()
    return registry.list_blueprints()


def get_blueprint_info(
    blueprint_name: str, template_dir: str | None = None
) -> dict[str, Any]:
    """Get detailed information about a specific blueprint.

    Args:
        blueprint_name: Name of the blueprint
        template_dir: Directory containing blueprint templates

    Returns:
        Dictionary with blueprint information including schema
    """
    if template_dir:
        # Create a temporary registry for the specific template directory
        temp_registry = BlueprintRegistry()

        # Override the get_template_dirs method to use the provided directory
        temp_registry.get_template_dirs = lambda: [Path(template_dir)]  # type: ignore[method-assign]

        # Discover blueprints in the specified directory
        temp_registry.discover_blueprints(force=True)

        return temp_registry.get_blueprint_info(blueprint_name)
    # Use the global registry
    registry.discover_blueprints()
    return registry.get_blueprint_info(blueprint_name)
