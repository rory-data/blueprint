"""Tests for the linting functionality."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from blueprint.linting import lint_dag_file, lint_directory


class TestLinting:
    """Test linting functionality."""

    def test_lint_dag_file_missing_file(self):
        """Test linting a non-existent file."""
        result = lint_dag_file("/nonexistent/file.py")
        assert result is False

    @patch("subprocess.run")
    def test_lint_dag_file_success(self, mock_run, tmp_path):
        """Test successful linting."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        
        # Mock successful ruff runs
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        result = lint_dag_file(test_file, fix=True, format_code=True)
        
        assert result is True
        assert mock_run.call_count == 2  # One for check, one for format

    @patch("subprocess.run")
    def test_lint_dag_file_ruff_not_found(self, mock_run, tmp_path):
        """Test handling when ruff is not installed."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        
        mock_run.side_effect = FileNotFoundError("ruff not found")
        
        result = lint_dag_file(test_file)
        assert result is False

    @patch("subprocess.run") 
    def test_lint_dag_file_with_issues(self, mock_run, tmp_path):
        """Test linting with issues found."""
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\n")  # Unused import
        
        # Mock ruff finding issues but fixing them
        mock_run.return_value = Mock(returncode=1, stdout="Fixed issues", stderr="")
        
        result = lint_dag_file(test_file, fix=True)
        assert result is True  # Should succeed with fix=True

    def test_lint_directory_missing(self):
        """Test linting a non-existent directory."""
        result = lint_directory("/nonexistent/directory")
        assert result == (0, 0)

    @patch("blueprint.linting.lint_dag_file")
    def test_lint_directory_success(self, mock_lint_file, tmp_path):
        """Test successful directory linting."""
        # Create test files
        (tmp_path / "dag1.py").write_text("print('hello')")
        (tmp_path / "dag2.py").write_text("print('world')")
        
        # Mock successful linting
        mock_lint_file.return_value = True
        
        successful, total = lint_directory(tmp_path)
        
        assert successful == 2
        assert total == 2
        assert mock_lint_file.call_count == 2

    @patch("blueprint.linting.lint_dag_file")
    def test_lint_directory_partial_failure(self, mock_lint_file, tmp_path):
        """Test directory linting with some failures."""
        # Create test files
        (tmp_path / "dag1.py").write_text("print('hello')")
        (tmp_path / "dag2.py").write_text("print('world')")
        
        # Mock one success, one failure
        mock_lint_file.side_effect = [True, False]
        
        successful, total = lint_directory(tmp_path)
        
        assert successful == 1
        assert total == 2