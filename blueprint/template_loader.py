"""Blueprint template loader utility.

This module handles the configuration and loading of Blueprint templates
for build-time DAG generation using *.py.j2 templates.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from blueprint.utils import get_template_path as utils_get_template_path

# Default template path relative to AIRFLOW_HOME
DEFAULT_TEMPLATE_PATH = ".astro/templates"

# Create logger for this module
logger = logging.getLogger(__name__)


def get_template_path() -> str:
    """Get the template path from environment or default."""
    return utils_get_template_path()


def setup_template_path() -> None:
    """Add the template path to sys.path if not already present."""
    template_path = get_template_path()

    # Convert to absolute path
    template_path = Path(template_path).resolve()

    # Only add to sys.path if the directory exists and not already there
    if template_path.exists() and str(template_path) not in sys.path:
        sys.path.insert(0, str(template_path))
    # If it doesn't exist, that's okay - we'll handle this gracefully elsewhere


def load_template(module_name: str, class_name: str) -> Any:
    """Dynamically load a template class from a module.

    Args:
        module_name: Name of the module (e.g., 'daily_etl')
        class_name: Name of the class to import (e.g., 'DailyETL')

    Returns:
        The imported class
    """
    setup_template_path()

    try:
        module = __import__(module_name)
        return getattr(module, class_name)
    except ImportError as e:
        template_path = get_template_path()
        error_msg = f"Could not import {class_name} from {module_name}: {e}"
        if not Path(template_path).exists():
            error_msg += f"\nTemplate directory does not exist: {template_path}"
        raise ImportError(error_msg) from e
    except AttributeError as e:
        error_msg = f"Class {class_name} not found in {module_name}: {e}"
        raise AttributeError(error_msg) from e


# Auto-setup when module is imported
setup_template_path()
