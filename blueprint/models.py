"""Pydantic model utilities and re-exports for Blueprint."""

# Re-export type annotations commonly used with Pydantic
from typing import Any, Dict, List, Optional, Union

# Handle missing pydantic gracefully
try:
    from pydantic import (
        BaseModel,
        ConfigDict,
        Field,
        ValidationError,
        field_validator,
        model_validator,
    )
except ImportError:
    # Define minimal stubs for development
    class BaseModel:
        def __init__(self, **kwargs):
            # Handle field validation and default values 
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        @classmethod
        def model_fields(cls):
            # Return empty dict for stub, real pydantic would inspect class annotations
            return {}
        
        @classmethod 
        def model_json_schema(cls):
            return {}
        
        def __dict__(self):
            return {k: v for k, v in vars(self).items() if not k.startswith('_')}
    
    def Field(**kwargs):
        return kwargs
    
    def field_validator(*field_names):
        def decorator(func):
            return func
        return decorator
    
    def model_validator(mode):
        def decorator(func):
            return func
        return decorator
    
    class ValidationError(Exception):
        pass
    
    class ConfigDict:
        pass

__all__ = [
    "Any",
    # Pydantic exports
    "BaseModel", 
    "ConfigDict",
    "Dict",
    "Field",
    "List",
    # Type exports
    "Optional",
    "Union",
    "ValidationError",
    "field_validator",
    "model_validator",
]
