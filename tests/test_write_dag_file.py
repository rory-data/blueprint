"""Tests for the write_dag_file method."""

from pathlib import Path
import tempfile
from datetime import datetime, timezone

import pytest
from pydantic import BaseModel, Field

from blueprint import Blueprint


class TestWriteDAGFile:
    """Test the write_dag_file method functionality."""

    def test_write_dag_file_basic(self):
        """Test basic write_dag_file functionality."""
        
        # Define a config model
        class SimpleConfig(BaseModel):
            job_id: str
            schedule: str = "@daily"
            retries: int = 2

        # Define a Blueprint
        class SimpleBlueprint(Blueprint[SimpleConfig]):
            def render(self, config: SimpleConfig):
                from airflow import DAG
                return DAG(
                    dag_id=config.job_id,
                    schedule=config.schedule,
                    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    catchup=False,
                )

        # Create blueprint and config
        blueprint = SimpleBlueprint()
        config = SimpleConfig(job_id="test_dag", schedule="@hourly", retries=3)
        
        # Test with custom output file
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_dag.py"
            
            # Write DAG file
            result_path = blueprint.write_dag_file(config, "test_dag", str(output_file))
            
            # Verify file was created
            assert Path(result_path).exists()
            assert result_path == str(output_file)
            
            # Read and verify content
            content = Path(result_path).read_text()
            
            # Verify basic structure
            assert "from blueprint import load_template" in content
            assert "SimpleBlueprint = load_template(" in content
            assert 'job_id="test_dag"' in content
            assert 'schedule="@hourly"' in content
            assert 'retries=3' in content

    def test_template_name_conversion(self):
        """Test template name conversion from class names."""
        
        class DailyETL(Blueprint):
            pass
        
        class MultiSourceETL(Blueprint):
            pass
        
        class SimpleBlueprint(Blueprint):
            pass
        
        # Test template name generation
        daily_etl = DailyETL()
        assert daily_etl._get_template_name() == "daily_etl"
        
        multi_source = MultiSourceETL()
        assert multi_source._get_template_name() == "multi_source_etl"
        
        simple = SimpleBlueprint()
        assert simple._get_template_name() == "simple_blueprint"

    def test_code_generation_with_different_types(self):
        """Test code generation with different parameter types."""
        
        class ComplexConfig(BaseModel):
            job_id: str
            source_tables: list[str]
            parallel: bool
            retries: int
            threshold: float

        class ComplexBlueprint(Blueprint[ComplexConfig]):
            def render(self, config: ComplexConfig):
                from airflow import DAG
                return DAG(dag_id=config.job_id, start_date=datetime(2024, 1, 1, tzinfo=timezone.utc))

        blueprint = ComplexBlueprint()
        config = ComplexConfig(
            job_id="complex_dag",
            source_tables=["table1", "table2", "table3"],
            parallel=True,
            retries=5,
            threshold=0.95
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "complex_dag.py"
            result_path = blueprint.write_dag_file(config, "complex_dag", str(output_file))
            
            content = Path(result_path).read_text()
            
            # Verify different parameter types are formatted correctly
            assert 'job_id="complex_dag"' in content
            assert 'source_tables=["table1", "table2", "table3"]' in content
            assert 'parallel=True' in content
            assert 'retries=5' in content
            assert 'threshold=0.95' in content

    def test_write_dag_file_uses_dags_folder(self, monkeypatch):
        """Test that write_dag_file uses the correct dags folder when no output file specified."""
        
        class TestConfig(BaseModel):
            job_id: str

        class TestBlueprint(Blueprint[TestConfig]):
            def render(self, config: TestConfig):
                from airflow import DAG
                return DAG(dag_id=config.job_id, start_date=datetime(2024, 1, 1, tzinfo=timezone.utc))

        # Mock get_airflow_dags_folder to return a temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            def mock_get_dags_folder():
                return temp_path
            
            # Monkey patch the function
            import blueprint.utils
            monkeypatch.setattr(blueprint.utils, "get_airflow_dags_folder", mock_get_dags_folder)
            
            blueprint = TestBlueprint()
            config = TestConfig(job_id="test_dag")
            
            # Call without specifying output file
            result_path = blueprint.write_dag_file(config, "test_dag")
            
            # Should create file in the mocked dags folder
            expected_path = temp_path / "test_dag.py"
            assert result_path == str(expected_path)
            assert expected_path.exists()

    def test_write_dag_file_from_config_class_method(self):
        """Test the class method version of write_dag_file."""
        
        class SimpleConfig(BaseModel):
            job_id: str
            schedule: str = "@daily"

        class SimpleBlueprint(Blueprint[SimpleConfig]):
            def render(self, config: SimpleConfig):
                from airflow import DAG
                return DAG(
                    dag_id=config.job_id,
                    schedule=config.schedule,
                    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc)
                )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "class_method_dag.py"
            
            # Use class method
            result_path = SimpleBlueprint.write_dag_file_from_config(
                dag_id="class_method_dag",
                output_file=str(output_file),
                job_id="class_method_dag",
                schedule="@weekly"
            )
            
            # Verify file was created
            assert Path(result_path).exists()
            content = Path(result_path).read_text()
            
            # Verify content
            assert 'job_id="class_method_dag"' in content
            assert 'schedule="@weekly"' in content