"""Pydantic model utilities and re-exports for Blueprint."""

# Re-export type annotations commonly used with Pydantic
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

__all__ = [
    "Any",
    # Pydantic exports
    "BaseModel",
    "ConfigDict",
    "Field",
    "ValidationError",
    "field_validator",
    "model_validator",
]
