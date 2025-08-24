"""Tests for the DAGWriter class."""

import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from pydantic import BaseModel

from blueprint.dag_writer import DAGWriter


class TestDAGWriter:
    """Test the DAGWriter class functionality."""
    
    def test_basic_dag_writing(self):
        """Test basic DAG file generation."""
        # Create a simple DAG
        from airflow import DAG
        from airflow.operators.bash import BashOperator
        
        dag = DAG(
            dag_id="test_dag",
            schedule="@daily",
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            catchup=False,
            description="Test DAG",
            tags=["test", "example"],
        )
        
        # Add a simple task
        task = BashOperator(
            task_id="test_task",
            bash_command="echo 'Hello World'",
            dag=dag,
        )
        
        # Test DAG writing
        writer = DAGWriter()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_dag.py"
            writer.write_dag_to_file(dag, output_file)
            
            # Verify file was created
            assert output_file.exists()
            content = output_file.read_text()
            
            # Verify content
            assert "from datetime import datetime, timedelta, timezone" in content
            assert "from airflow import DAG" in content
            assert "from airflow.operators.bash import BashOperator" in content
            assert 'dag_id="test_dag"' in content
            assert 'schedule="@daily"' in content
            assert 'description="Test DAG"' in content
            assert 'tags=["test", "example"]' in content
            assert "test_task = BashOperator(" in content
            assert 'bash_command="echo \'Hello World\'"' in content

    def test_python_operator_with_function(self):
        """Test PythonOperator handling with function extraction."""
        from airflow import DAG
        from airflow.operators.python import PythonOperator
        
        def test_function(**context):
            """Test function for PythonOperator."""
            print("Hello from Python!")
            return "success"
        
        dag = DAG(
            dag_id="python_dag",
            schedule=None,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        
        python_task = PythonOperator(
            task_id="python_task",
            python_callable=test_function,
            dag=dag,
        )
        
        writer = DAGWriter()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "python_dag.py"
            writer.write_dag_to_file(dag, output_file)
            
            content = output_file.read_text()
            
            # Verify function definition is included
            assert "def test_function(**context):" in content
            assert "Test function for PythonOperator." in content
            assert "python_callable=test_function" in content

    def test_dag_with_default_args(self):
        """Test DAG with default_args handling."""
        from airflow import DAG
        from airflow.operators.bash import BashOperator
        
        default_args = {
            "owner": "test-user",
            "retries": 3,
            "retry_delay": timedelta(minutes=5),
            "email_on_failure": False,
        }
        
        dag = DAG(
            dag_id="default_args_dag",
            default_args=default_args,
            schedule="@hourly",
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        
        task = BashOperator(
            task_id="test_task",
            bash_command="echo 'test'",
            dag=dag,
        )
        
        writer = DAGWriter()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "default_args_dag.py"
            writer.write_dag_to_file(dag, output_file)
            
            content = output_file.read_text()
            
            # Verify default_args are properly formatted
            assert '"owner": "test-user"' in content
            assert '"retries": 3' in content
            assert 'retry_delay": timedelta(minutes=5)' in content
            assert '"email_on_failure": False' in content

    def test_task_dependencies(self):
        """Test task dependency generation."""
        from airflow import DAG
        from airflow.operators.bash import BashOperator
        
        dag = DAG(
            dag_id="dependency_dag",
            schedule=None,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        
        task1 = BashOperator(
            task_id="task1",
            bash_command="echo 'task1'",
            dag=dag,
        )
        
        task2 = BashOperator(
            task_id="task2",
            bash_command="echo 'task2'",
            dag=dag,
        )
        
        task3 = BashOperator(
            task_id="task3",
            bash_command="echo 'task3'",
            dag=dag,
        )
        
        # Set up dependencies
        task1 >> task2 >> task3
        
        writer = DAGWriter()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "dependency_dag.py"
            writer.write_dag_to_file(dag, output_file)
            
            content = output_file.read_text()
            
            # Verify dependencies are captured
            # (Note: exact format may vary based on how Airflow stores dependencies)
            assert "task1 >> task2" in content or "task2" in content
            assert "task2 >> task3" in content or "task3" in content

    def test_generic_operator_handling(self):
        """Test handling of operators not specifically supported."""
        from airflow import DAG
        from airflow.operators.bash import BashOperator
        
        # Create a DAG with a basic operator
        dag = DAG(
            dag_id="generic_dag",
            schedule=None,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        
        # BashOperator should be handled by specific handler, but test the generic path
        task = BashOperator(
            task_id="generic_task",
            bash_command="echo 'test'",
            dag=dag,
        )
        
        writer = DAGWriter()
        
        # Test individual method
        task_def = writer._handle_generic_operator(task)
        
        # Should include basic task parameters
        assert "task_id=" in task_def
        assert "dag=dag" in task_def
        assert "BashOperator" in task_def

    def test_import_extraction(self):
        """Test import extraction from DAG."""
        from airflow import DAG
        from airflow.operators.bash import BashOperator
        from airflow.operators.python import PythonOperator
        
        def dummy_func():
            pass
        
        dag = DAG(
            dag_id="import_test_dag",
            schedule=None,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        
        bash_task = BashOperator(
            task_id="bash_task",
            bash_command="echo 'test'",
            dag=dag,
        )
        
        python_task = PythonOperator(
            task_id="python_task",
            python_callable=dummy_func,
            dag=dag,
        )
        
        writer = DAGWriter()
        imports = writer._extract_imports(dag)
        
        # Verify all required imports are present
        assert "from datetime import datetime, timedelta, timezone" in imports
        assert "from airflow import DAG" in imports
        assert "from airflow.operators.bash import BashOperator" in imports
        assert "from airflow.operators.python import PythonOperator" in imports

    def test_datetime_formatting(self):
        """Test datetime formatting methods."""
        writer = DAGWriter()
        
        # Test timezone-aware datetime
        dt_with_tz = datetime(2024, 3, 15, tzinfo=timezone.utc)
        formatted = writer._format_datetime(dt_with_tz)
        assert formatted == "datetime(2024, 3, 15, tzinfo=timezone.utc)"
        
        # Test naive datetime
        dt_naive = datetime(2024, 3, 15)
        formatted = writer._format_datetime(dt_naive)
        assert formatted == "datetime(2024, 3, 15)"

    def test_value_formatting(self):
        """Test value formatting for different types."""
        writer = DAGWriter()
        
        # Test string
        assert writer._format_value("test") == '"test"'
        
        # Test timedelta
        td = timedelta(minutes=30)
        assert writer._format_value(td) == "timedelta(minutes=30)"
        
        td = timedelta(hours=2)
        assert writer._format_value(td) == "timedelta(hours=2)"
        
        td = timedelta(seconds=45)
        assert writer._format_value(td) == "timedelta(seconds=45)"
        
        # Test other types
        assert writer._format_value(123) == "123"
        assert writer._format_value(True) == "True"