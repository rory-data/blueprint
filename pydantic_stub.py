"""Minimal pydantic stub for development purposes."""

from typing import Any, Dict, Type


class BaseModel:
    """Minimal BaseModel stub."""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def model_json_schema(cls) -> Dict[str, Any]:
        """Return empty schema for now."""
        return {}
    
    @classmethod
    def model_fields(cls):
        """Return empty fields for now."""
        return {}


def Field(**kwargs):
    """Field stub."""
    return kwargs


def field_validator(field_name):
    """field_validator stub."""
    def decorator(func):
        return func
    return decorator


class ValidationError(Exception):
    """ValidationError stub."""
    pass