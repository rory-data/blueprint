"""Tests for the template loader for build-time DAG generation."""

import pytest

from blueprint.template_loader import load_template, setup_template_path


class TestTemplateLoader:
    """Test template loading functionality."""

    def test_setup_template_path(self):
        """Test template path setup."""
        # This should not raise any exception
        setup_template_path()

    def test_load_template_missing_module(self):
        """Test loading a non-existent template module."""
        with pytest.raises(ImportError, match="Could not import"):
            load_template("nonexistent_module", "NonexistentClass")

    def test_load_template_missing_class(self, tmp_path):
        """Test loading a non-existent class from a module."""
        # Create a simple Python module
        module_file = tmp_path / "test_module.py" 
        module_file.write_text("# Empty module")
        
        # Add the temp path to sys.path for the test
        import sys
        sys.path.insert(0, str(tmp_path))
        
        try:
            with pytest.raises(AttributeError, match="Class .* not found"):
                load_template("test_module", "NonexistentClass")
        finally:
            sys.path.remove(str(tmp_path))