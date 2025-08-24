"""DAG writer for generating standalone DAG files from rendered DAGs."""

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from airflow import DAG
    from airflow.models import BaseOperator


class DAGWriter:
    """Generates standalone DAG files from rendered Airflow DAGs.
    
    This class handles the conversion of a rendered DAG object into complete Python code
    that can be deployed independently without requiring blueprint templates.
    
    Features:
    - Extracts and generates all necessary imports
    - Creates complete DAG definitions with all parameters
    - Generates task definitions with full configuration
    - Handles function definitions for PythonOperator tasks
    - Recreates task dependencies
    """

    def __init__(self):
        """Initialize the DAGWriter."""
        self._operator_handlers: Dict[str, Callable] = {
            "BashOperator": self._handle_bash_operator,
            "PythonOperator": self._handle_python_operator,
            "SQLOperator": self._handle_sql_operator,
            "SqliteOperator": self._handle_sql_operator,
            "PostgresOperator": self._handle_sql_operator,
            "MySqlOperator": self._handle_sql_operator,
        }

    def write_dag_to_file(self, dag: "DAG", output_path: Path) -> None:
        """Write a rendered DAG to a Python file.
        
        Args:
            dag: The rendered Airflow DAG object
            output_path: Path where the DAG file should be written
        """
        dag_code = self._generate_dag_code(dag)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(dag_code)

    def _generate_dag_code(self, dag: "DAG") -> str:
        """Generate the complete Python code for the DAG file."""
        # Generate all code sections
        imports = self._extract_imports(dag)
        dag_definition = self._generate_dag_definition(dag)
        task_definitions = self._generate_task_definitions(dag)
        dependencies = self._generate_dependencies(dag)
        
        # Combine into final code
        code_sections = [
            '"""Auto-generated DAG file from Blueprint."""',
            "",
            imports,
            "",
            dag_definition,
            "",
            task_definitions,
        ]
        
        if dependencies:
            code_sections.extend(["", dependencies])
        
        return "\n".join(code_sections)

    def _extract_imports(self, dag: "DAG") -> str:
        """Extract necessary imports for the DAG and its tasks."""
        imports = set()
        
        # Always include these basic imports
        imports.add("from datetime import datetime, timedelta, timezone")
        imports.add("from airflow import DAG")
        
        # Extract imports based on task types
        for task in dag.tasks:
            task_module = task.__class__.__module__
            task_class = task.__class__.__name__
            imports.add(f"from {task_module} import {task_class}")
        
        return "\n".join(sorted(imports))

    def _generate_dag_definition(self, dag: "DAG") -> str:
        """Generate the complete DAG constructor code."""
        params = []
        
        # Basic DAG parameters
        params.append(f'    dag_id="{dag.dag_id}",')
        
        # Handle default_args
        if hasattr(dag, 'default_args') and dag.default_args:
            default_args_code = self._format_default_args(dag.default_args)
            params.append(f"    default_args={default_args_code},")
        
        # Other DAG parameters
        if hasattr(dag, 'description') and dag.description:
            params.append(f'    description="{dag.description}",')
        
        # Handle schedule (both old and new style)
        schedule = self._get_dag_schedule(dag)
        if schedule is not None:
            if isinstance(schedule, str):
                params.append(f'    schedule="{schedule}",')
            else:
                params.append(f'    schedule={repr(schedule)},')
        
        # Start date
        if hasattr(dag, 'start_date') and dag.start_date:
            start_date_code = self._format_datetime(dag.start_date)
            params.append(f'    start_date={start_date_code},')
        
        # Other boolean/simple parameters
        if hasattr(dag, 'catchup'):
            params.append(f'    catchup={dag.catchup},')
        
        # Tags
        if hasattr(dag, 'tags') and dag.tags:
            tags_str = "[" + ", ".join(f'"{tag}"' for tag in dag.tags) + "]"
            params.append(f'    tags={tags_str},')
        
        params_code = "\n".join(params)
        return f"dag = DAG(\n{params_code}\n)"

    def _format_default_args(self, default_args: Dict[str, Any]) -> str:
        """Format default_args dictionary as Python code."""
        lines = ["{"]
        
        for key, value in default_args.items():
            formatted_value = self._format_value(value)
            lines.append(f'        "{key}": {formatted_value},')
        
        lines.append("    }")
        return "\n    ".join(lines)

    def _format_value(self, value: Any) -> str:
        """Format a value as Python code."""
        if isinstance(value, str):
            return f'"{value}"'
        elif hasattr(value, '__class__') and value.__class__.__name__ == 'timedelta':
            # Handle timedelta objects
            total_seconds = int(value.total_seconds())
            if total_seconds % 3600 == 0:
                return f"timedelta(hours={total_seconds // 3600})"
            elif total_seconds % 60 == 0:
                return f"timedelta(minutes={total_seconds // 60})"
            else:
                return f"timedelta(seconds={total_seconds})"
        else:
            return repr(value)

    def _get_dag_schedule(self, dag: "DAG") -> Any:
        """Get the schedule from a DAG, handling both old and new Airflow versions."""
        # Try new style first (Airflow 2.4+)
        if hasattr(dag, 'schedule') and dag.schedule is not None:
            return dag.schedule
        # Fall back to old style
        elif hasattr(dag, 'schedule_interval') and dag.schedule_interval is not None:
            return dag.schedule_interval
        return None

    def _format_datetime(self, dt) -> str:
        """Format a datetime object as Python code."""
        if dt.tzinfo:
            return f"datetime({dt.year}, {dt.month}, {dt.day}, tzinfo=timezone.utc)"
        else:
            return f"datetime({dt.year}, {dt.month}, {dt.day})"

    def _generate_task_definitions(self, dag: "DAG") -> str:
        """Generate all task definitions."""
        task_definitions = []
        
        for task in dag.tasks:
            task_def = self._generate_single_task_definition(task)
            if task_def:
                task_definitions.append(task_def)
        
        return "\n\n".join(task_definitions)

    def _generate_single_task_definition(self, task: "BaseOperator") -> str:
        """Generate the definition for a single task."""
        task_class = task.__class__.__name__
        
        # Use specific handler if available
        if task_class in self._operator_handlers:
            return self._operator_handlers[task_class](task)
        
        # Fall back to generic handler
        return self._handle_generic_operator(task)

    def _handle_bash_operator(self, task: "BaseOperator") -> str:
        """Handle BashOperator tasks."""
        params = self._get_base_task_params(task)
        
        if hasattr(task, 'bash_command') and task.bash_command:
            bash_cmd = task.bash_command.replace('"', '\\"')
            params.append(f'    bash_command="{bash_cmd}",')
        
        return self._format_task_definition(task, params)

    def _handle_python_operator(self, task: "BaseOperator") -> str:
        """Handle PythonOperator tasks."""
        params = self._get_base_task_params(task)
        
        if hasattr(task, 'python_callable') and task.python_callable:
            func_name = task.python_callable.__name__
            params.append(f'    python_callable={func_name},')
            
            # Include function definition
            func_def = self._extract_function_definition(task.python_callable)
            task_def = self._format_task_definition(task, params)
            
            return f"{func_def}\n\n{task_def}"
        
        return self._format_task_definition(task, params)

    def _handle_sql_operator(self, task: "BaseOperator") -> str:
        """Handle SQL operator tasks."""
        params = self._get_base_task_params(task)
        
        if hasattr(task, 'sql') and task.sql:
            sql_cmd = task.sql.replace('"', '\\"')
            params.append(f'    sql="{sql_cmd}",')
        
        # Add connection_id if present
        if hasattr(task, 'conn_id') and task.conn_id:
            params.append(f'    conn_id="{task.conn_id}",')
        elif hasattr(task, 'connection_id') and task.connection_id:
            params.append(f'    connection_id="{task.connection_id}",')
        
        return self._format_task_definition(task, params)

    def _handle_generic_operator(self, task: "BaseOperator") -> str:
        """Handle generic operators by extracting common parameters."""
        params = self._get_base_task_params(task)
        
        # Try to extract some common operator parameters
        common_params = [
            'sql', 'bash_command', 'command', 'target', 'source',
            'conn_id', 'connection_id', 'database', 'schema'
        ]
        
        for param in common_params:
            if hasattr(task, param):
                value = getattr(task, param)
                if value is not None:
                    if isinstance(value, str):
                        escaped_value = value.replace('"', '\\"')
                        params.append(f'    {param}="{escaped_value}",')
                    else:
                        params.append(f'    {param}={repr(value)},')
        
        return self._format_task_definition(task, params)

    def _get_base_task_params(self, task: "BaseOperator") -> List[str]:
        """Get base parameters common to all tasks."""
        return [
            f'    task_id="{task.task_id}",',
            '    dag=dag,',
        ]

    def _format_task_definition(self, task: "BaseOperator", params: List[str]) -> str:
        """Format a task definition with the given parameters."""
        task_class = task.__class__.__name__
        params_str = "\n".join(params)
        
        return f"{task.task_id} = {task_class}(\n{params_str}\n)"

    def _extract_function_definition(self, func: Callable) -> str:
        """Extract function definition from a callable."""
        try:
            # Get the source code of the function
            source_lines = inspect.getsourcelines(func)[0]
            
            # Remove the base indentation from all lines
            if source_lines:
                base_indent = len(source_lines[0]) - len(source_lines[0].lstrip())
                
                cleaned_lines = []
                for line in source_lines:
                    if line.strip():  # Skip empty lines
                        cleaned_lines.append(line[base_indent:])
                    else:
                        cleaned_lines.append("\n")
                
                return "".join(cleaned_lines).rstrip()
        except (OSError, TypeError, IndexError):
            # If we can't get the source, create a placeholder
            pass
        
        # Fallback placeholder
        return f'''def {func.__name__}(**_):
    """Auto-generated function placeholder."""
    pass'''

    def _generate_dependencies(self, dag: "DAG") -> str:
        """Generate task dependency definitions."""
        dependencies = []
        processed = set()
        
        # Generate dependencies from downstream relationships
        for task in dag.tasks:
            if hasattr(task, 'downstream_task_ids') and task.downstream_task_ids:
                for downstream_id in task.downstream_task_ids:
                    dep_str = f"{task.task_id} >> {downstream_id}"
                    if dep_str not in processed:
                        dependencies.append(dep_str)
                        processed.add(dep_str)
        
        return "\n".join(dependencies)