"""Minimal Airflow stubs for testing."""

from datetime import datetime, timedelta

class DAG:
    """Mock DAG class for testing."""
    def __init__(self, dag_id, **kwargs):
        self.dag_id = dag_id
        self.kwargs = kwargs
    
    def __repr__(self):
        return f"DAG(dag_id='{self.dag_id}')"
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass

class BashOperator:
    """Mock BashOperator for testing."""
    def __init__(self, task_id, bash_command, **kwargs):
        self.task_id = task_id
        self.bash_command = bash_command
    
    def __repr__(self):
        return f"BashOperator(task_id='{self.task_id}')"
    
    def __rshift__(self, other):
        """Mock task dependency operator."""
        return other

class PythonOperator:
    """Mock PythonOperator for testing."""
    def __init__(self, task_id, python_callable, **kwargs):
        self.task_id = task_id
        self.python_callable = python_callable
    
    def __repr__(self):
        return f"PythonOperator(task_id='{self.task_id}')"
        
    def __rshift__(self, other):
        """Mock task dependency operator."""
        return other