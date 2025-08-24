"""DAG writer for generating standalone DAG files from rendered DAGs."""

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from airflow import DAG
    from airflow.models import BaseOperator

try:
    from airflow.serialization.serialized_objects import SerializedDAG, SerializedBaseOperator, BaseSerialization
    AIRFLOW_SERIALIZATION_AVAILABLE = True
except ImportError:
    AIRFLOW_SERIALIZATION_AVAILABLE = False


class DAGWriter:
    """Generates standalone DAG files from rendered Airflow DAGs.
    
    This class uses Airflow's built-in serialization capabilities to extract DAG information
    and generate complete Python code that can be deployed independently without requiring 
    blueprint templates.
    
    Features:
    - Uses Airflow's SerializedDAG for structured data extraction
    - Leverages BaseSerialization for proper value formatting
    - Generic operator parameter extraction using serialized data
    - Automatic import detection from serialized task metadata
    - Clean dependency recreation from DAG structure
    """

    def __init__(self):
        """Initialize the DAGWriter."""
        if not AIRFLOW_SERIALIZATION_AVAILABLE:
            raise ImportError(
                "Airflow serialization modules not available. "
                "Please ensure Apache Airflow is installed."
            )

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
        """Generate the complete Python code for the DAG file using Airflow serialization."""
        # Serialize the DAG to get structured data
        serialized_data = SerializedDAG.to_dict(dag)
        dag_data = serialized_data["dag"]
        
        # Generate all code sections using serialized data
        imports = self._extract_imports_from_serialized(dag_data)
        dag_definition = self._generate_dag_definition_from_serialized(dag_data)
        task_definitions = self._generate_task_definitions_from_serialized(dag, dag_data)
        dependencies = self._generate_dependencies_from_serialized(dag_data)
        
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

    def _extract_imports_from_serialized(self, dag_data: Dict[str, Any]) -> str:
        """Extract necessary imports using serialized DAG data."""
        imports = set()
        
        # Always include these basic imports
        imports.add("from datetime import datetime, timedelta, timezone")
        imports.add("from airflow import DAG")
        
        # Extract imports from serialized task data
        if "tasks" in dag_data and isinstance(dag_data["tasks"], list):
            for task_data_wrapped in dag_data["tasks"]:
                # Deserialize the task data
                task_obj = BaseSerialization.deserialize(task_data_wrapped)
                # Get the task type and module from the serialized operator
                if hasattr(task_obj, '__class__'):
                    # Use the actual operator class info
                    task_module = task_obj.__class__.__module__.replace('.serialized_objects', '')
                    task_type = task_obj.__class__.__name__.replace('Serialized', '')
                    
                    # For SerializedBaseOperator, get the original operator info
                    if hasattr(task_obj, '_task_type') and hasattr(task_obj, '_task_module'):
                        task_type = getattr(task_obj, '_task_type', task_type)
                        task_module = getattr(task_obj, '_task_module', task_module)
                    
                    if task_module and task_type:
                        imports.add(f"from {task_module} import {task_type}")
        
        return "\n".join(sorted(imports))

    def _generate_dag_definition_from_serialized(self, dag_data: Dict[str, Any]) -> str:
        """Generate DAG constructor using serialized data."""
        params = []
        
        # Basic DAG parameters from serialized data
        if "_dag_id" in dag_data:
            params.append(f'    dag_id="{dag_data["_dag_id"]}",')
        
        # Handle default_args using BaseSerialization
        if "default_args" in dag_data and dag_data["default_args"]:
            default_args = BaseSerialization.deserialize(dag_data["default_args"])
            default_args_code = self._format_default_args(default_args)
            params.append(f"    default_args={default_args_code},")
        
        # Other DAG parameters
        if "_description" in dag_data and dag_data["_description"]:
            params.append(f'    description="{dag_data["_description"]}",')
        
        # Handle schedule
        if "schedule_interval" in dag_data and dag_data["schedule_interval"]:
            schedule = dag_data["schedule_interval"]
            if isinstance(schedule, str):
                params.append(f'    schedule="{schedule}",')
            else:
                params.append(f'    schedule={repr(schedule)},')
        
        # Start date
        if "start_date" in dag_data and dag_data["start_date"]:
            start_date_raw = dag_data["start_date"] 
            # Handle both timestamp floats and datetime objects
            if isinstance(start_date_raw, (int, float)):
                # Convert timestamp to datetime - assume UTC for serialized timestamps
                from datetime import datetime as dt, timezone
                start_date = dt.fromtimestamp(start_date_raw, timezone.utc)
            else:
                # Try to deserialize if it's a complex object
                start_date = BaseSerialization.deserialize(start_date_raw)
            
            start_date_code = self._format_datetime(start_date)
            params.append(f'    start_date={start_date_code},')
        
        # Catchup
        if "catchup" in dag_data:
            params.append(f'    catchup={dag_data["catchup"]},')
        
        # Tags
        if "tags" in dag_data and dag_data["tags"]:
            tags_str = "[" + ", ".join(f'"{tag}"' for tag in dag_data["tags"]) + "]"
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

    def _format_datetime(self, dt) -> str:
        """Format a datetime object as Python code."""
        if hasattr(dt, 'tzinfo') and dt.tzinfo:
            return f"datetime({dt.year}, {dt.month}, {dt.day}, tzinfo=timezone.utc)"
        else:
            return f"datetime({dt.year}, {dt.month}, {dt.day})"

    def _extract_function_definition(self, func) -> str:
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

    def _generate_task_definitions_from_serialized(self, dag: "DAG", dag_data: Dict[str, Any]) -> str:
        """Generate task definitions using serialized data and original DAG for function extraction."""
        task_definitions = []
        
        if "tasks" in dag_data and isinstance(dag_data["tasks"], list):
            for task_data_wrapped in dag_data["tasks"]:
                # Deserialize the task data to get SerializedBaseOperator
                task_obj = BaseSerialization.deserialize(task_data_wrapped)
                
                # Get the original task for function extraction if needed
                task_id = getattr(task_obj, 'task_id', None)
                original_task = next((t for t in dag.tasks if t.task_id == task_id), None)
                
                # Convert SerializedBaseOperator to dict format for processing
                task_data = self._serialize_task_to_dict(task_obj, original_task)
                task_def = self._generate_single_task_from_serialized(task_data, original_task)
                if task_def:
                    task_definitions.append(task_def)
        
        return "\n\n".join(task_definitions)

    def _serialize_task_to_dict(self, task_obj, original_task: Optional["BaseOperator"] = None) -> Dict[str, Any]:
        """Convert SerializedBaseOperator to dict format for processing."""
        if original_task:
            # Use SerializedBaseOperator.serialize_operator for complete data
            from airflow.serialization.serialized_objects import SerializedBaseOperator
            return SerializedBaseOperator.serialize_operator(original_task)
        else:
            # Fallback: extract what we can from SerializedBaseOperator
            return {
                'task_id': getattr(task_obj, 'task_id', ''),
                '_task_type': getattr(task_obj, '_task_type', task_obj.__class__.__name__.replace('Serialized', '')),
                '_task_module': getattr(task_obj, '_task_module', task_obj.__class__.__module__.replace('.serialized_objects', '')),
                'bash_command': getattr(task_obj, 'bash_command', None),
                'python_callable': getattr(task_obj, 'python_callable', None),
            }

    def _generate_single_task_from_serialized(self, task_data: Dict[str, Any], original_task: Optional["BaseOperator"] = None) -> str:
        """Generate a single task definition from serialized data."""
        task_type = task_data.get("_task_type")
        task_id = task_data.get("task_id")
        
        if not task_type or not task_id:
            return ""
        
        # Start with base parameters
        params = [
            f'    task_id="{task_id}",',
            '    dag=dag,',
        ]
        
        # Add operator-specific parameters from serialized data
        self._add_operator_params_from_serialized(params, task_data, task_type, original_task)
        
        # Format the task definition
        params_str = "\n".join(params)
        task_definition = f"{task_id} = {task_type}(\n{params_str}\n)"
        
        # Handle PythonOperator function definitions
        if task_type == "PythonOperator" and original_task and hasattr(original_task, 'python_callable'):
            func_def = self._extract_function_definition(original_task.python_callable)
            return f"{func_def}\n\n{task_definition}"
        
        return task_definition

    def _add_operator_params_from_serialized(self, params: List[str], task_data: Dict[str, Any], 
                                           task_type: str, original_task: Optional["BaseOperator"] = None) -> None:
        """Add operator-specific parameters from serialized data."""
        # Common parameters to skip (internals and already handled)
        skip_params = {
            '_task_type', '_task_module', '_is_empty', '_log_config_logger_name',
            'task_id', 'downstream_task_ids', 'template_fields', 'template_ext',
            'template_fields_renderers', 'ui_color', 'ui_fgcolor', 'weight_rule',
            'is_setup', 'is_teardown', 'on_failure_fail_dagrun', 'pool',
            'start_from_trigger', 'start_trigger_args', '_needs_expansion',
            # Skip parameters that are duplicates of DAG default_args
            'owner', 'retries', 'retry_delay'
        }
        
        # Handle PythonOperator specially
        if task_type == "PythonOperator" and original_task and hasattr(original_task, 'python_callable'):
            func_name = original_task.python_callable.__name__
            params.append(f'    python_callable={func_name},')
        
        for key, value in task_data.items():
            if key not in skip_params and value is not None:
                # Handle special cases for different operators
                formatted_value = self._format_serialized_value(value, key, task_type)
                if formatted_value is not None:
                    params.append(f'    {key}={formatted_value},')

    def _format_serialized_value(self, value: Any, key: str, task_type: str) -> Optional[str]:
        """Format a serialized value for Python code generation."""
        # Skip empty lists and empty tuples for op_args/op_kwargs
        if key in ('op_args', 'op_kwargs') and not value:
            return None
            
        if isinstance(value, str):
            # Escape quotes in string values - prefer double quotes to avoid excessive escaping
            if '"' in value and "'" not in value:
                # Use single quotes if string contains double quotes but no single quotes
                return f"'{value}'"
            else:
                # Use double quotes and escape any internal double quotes
                escaped_value = value.replace('"', '\\"')
                return f'"{escaped_value}"'
        elif isinstance(value, bool):
            return str(value)
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            if all(isinstance(item, str) for item in value):
                return "[" + ", ".join(f'"{item}"' for item in value) + "]"
            else:
                return repr(value)
        elif isinstance(value, dict):
            # For dict values, try to format them nicely
            if key == "op_kwargs" or key == "op_args":
                return self._format_dict_value(value)
        
        # For other types, use repr as fallback
        return repr(value)

    def _format_dict_value(self, value: Dict[str, Any]) -> str:
        """Format a dictionary value for code generation."""
        if not value:
            return "{}"
        
        lines = ["{"]
        for k, v in value.items():
            formatted_v = self._format_value(v)  # Reuse existing method
            lines.append(f'        "{k}": {formatted_v},')
        lines.append("    }")
        return "\n    ".join(lines)

    def _generate_dependencies_from_serialized(self, dag_data: Dict[str, Any]) -> str:
        """Generate task dependencies using serialized data."""
        dependencies = []
        processed = set()
        
        # Extract dependencies from task downstream relationships
        if "tasks" in dag_data and isinstance(dag_data["tasks"], list):
            for task_data_wrapped in dag_data["tasks"]:
                # Deserialize the task data
                task_obj = BaseSerialization.deserialize(task_data_wrapped)
                
                task_id = getattr(task_obj, 'task_id', None)
                downstream_ids = getattr(task_obj, 'downstream_task_ids', [])
                
                if task_id and downstream_ids:
                    for downstream_id in downstream_ids:
                        dep_str = f"{task_id} >> {downstream_id}"
                        if dep_str not in processed:
                            dependencies.append(dep_str)
                            processed.add(dep_str)
        
        return "\n".join(dependencies)

    # Backward compatibility methods for tests
    def _extract_imports(self, dag: "DAG") -> str:
        """Backward compatibility method for tests."""
        serialized_data = SerializedDAG.to_dict(dag)
        return self._extract_imports_from_serialized(serialized_data["dag"])

    def _handle_generic_operator(self, task: "BaseOperator") -> str:
        """Backward compatibility method for tests."""
        from airflow.serialization.serialized_objects import SerializedBaseOperator
        task_data = SerializedBaseOperator.serialize_operator(task)
        return self._generate_single_task_from_serialized(task_data, task)