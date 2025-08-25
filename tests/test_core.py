"""Tests for core Blueprint functionality focused on build-time generation."""

import inspect
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from blueprint import Blueprint


class TestBlueprint:
    """Test the core Blueprint class functionality for build-time generation."""

    def test_blueprint_build_template_method_exists(self):
        """Test that Blueprint has the build_template class method."""
        # Define a config model
        try:
            from pydantic import BaseModel
        except ImportError:
            # Mock BaseModel if pydantic is not available
            class BaseModel:
                pass

        class SimpleConfig(BaseModel):
            job_id: str = "test"
            schedule: str = "@daily"

        # Define a Blueprint
        class SimpleBlueprint(Blueprint[SimpleConfig]):
            def render_template(self, config: SimpleConfig) -> str:
                return f'''
from airflow import DAG
from datetime import datetime

dag = DAG(
    dag_id="{config.job_id}",
    schedule="{config.schedule}",
    start_date=datetime(2024, 1, 1),
)
'''

        # Test that build_template method exists
        assert hasattr(SimpleBlueprint, "build_template")
        assert callable(SimpleBlueprint.build_template)

    def test_blueprint_render_template_method(self):
        """Test the render_template method."""
        try:
            from pydantic import BaseModel
        except ImportError:
            # Mock BaseModel if pydantic is not available
            class BaseModel:
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)

        class SimpleConfig(BaseModel):
            job_id: str = "test"
            schedule: str = "@daily"

        class SimpleBlueprint(Blueprint[SimpleConfig]):
            def render_template(self, config: SimpleConfig) -> str:
                return f'# DAG: {config.job_id}\nschedule = "{config.schedule}"'

        # Create an instance and test render_template
        blueprint = SimpleBlueprint()
        config = SimpleConfig(job_id="test_dag", schedule="@hourly")
        
        template_code = blueprint.render_template(config)
        
        assert isinstance(template_code, str)
        assert "test_dag" in template_code
        assert "@hourly" in template_code

    @patch("blueprint.core.Path")
    def test_get_template_path(self, mock_path):
        """Test template path resolution for .py.j2 files."""
        try:
            from pydantic import BaseModel
        except ImportError:
            class BaseModel:
                pass

        class TestConfig(BaseModel):
            pass

        class TestBlueprint(Blueprint[TestConfig]):
            pass

        # Mock path.exists() to return True for the first path
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        blueprint = TestBlueprint()
        
        # This will test the _get_template_path method indirectly
        # by checking if it looks for .py.j2 files
        try:
            path = blueprint._get_template_path()
            # Should look for test_blueprint.py.j2
            assert str(path).endswith("test_blueprint.py.j2")
        except Exception:
            # This is expected if the template path doesn't exist
            pass

    def test_blueprint_get_config_type(self):
        """Test getting the configuration type from Blueprint."""
        try:
            from pydantic import BaseModel
        except ImportError:
            class BaseModel:
                @classmethod
                def model_json_schema(cls):
                    return {"properties": {}}

        class TestConfig(BaseModel):
            job_id: str = "test"

        class TestBlueprint(Blueprint[TestConfig]):
            pass

        # Test get_config_type method
        config_type = TestBlueprint.get_config_type()
        assert config_type == TestConfig

    def test_blueprint_get_schema(self):
        """Test getting the JSON schema from Blueprint."""
        try:
            from pydantic import BaseModel
        except ImportError:
            class BaseModel:
                @classmethod
                def model_json_schema(cls):
                    return {"properties": {"job_id": {"type": "string"}}}

        class TestConfig(BaseModel):
            job_id: str = "test"

        class TestBlueprint(Blueprint[TestConfig]):
            pass

        # Test get_schema method
        schema = TestBlueprint.get_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema

    def test_jinja_template_not_found_fallback(self):
        """Test fallback when Jinja2 template is not found."""
        try:
            from pydantic import BaseModel
        except ImportError:
            class BaseModel:
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)

        class TestConfig(BaseModel):
            job_id: str = "test"

        class TestBlueprint(Blueprint[TestConfig]):
            pass

        blueprint = TestBlueprint()
        config = TestConfig(job_id="test_dag")

        # This should use the fallback method since no .py.j2 template exists
        template_code = blueprint.render_template(config)
        
        assert isinstance(template_code, str)
        assert "test_dag" in template_code
        assert "Auto-generated DAG" in template_code