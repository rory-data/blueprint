"""Blueprint configuration management."""

from typing import Any

from blueprint.utils import get_output_dir as utils_get_output_dir
from blueprint.utils import get_template_path as utils_get_template_path
from blueprint.utils import load_config as utils_load_config


def load_config() -> dict[str, Any]:
    """Load config from blueprint.toml if it exists."""
    return utils_load_config()


def get_template_path(cli_value: str | None = None) -> str:
    """Get template path with precedence: CLI > env > config > default."""
    return utils_get_template_path(cli_value)


def get_output_dir(cli_value: str | None = None) -> str:
    """Get output dir with precedence: CLI > config > default."""
    return utils_get_output_dir(cli_value)
