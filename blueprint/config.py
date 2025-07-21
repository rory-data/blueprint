"""Blueprint configuration management."""

import sys
from typing import Any, Dict, Optional

from blueprint.utils import get_output_dir as utils_get_output_dir
from blueprint.utils import get_template_path as utils_get_template_path
from blueprint.utils import load_config as utils_load_config

# Handle different Python versions for tomllib
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[import-not-found]
    except ImportError:
        tomllib = None


def load_config() -> Dict[str, Any]:
    """Load config from blueprint.toml if it exists."""
    return utils_load_config()


def get_template_path(cli_value: Optional[str] = None) -> str:
    """Get template path with precedence: CLI > env > config > default."""
    return utils_get_template_path(cli_value)


def get_output_dir(cli_value: Optional[str] = None) -> str:
    """Get output dir with precedence: CLI > config > default."""
    return utils_get_output_dir(cli_value)
