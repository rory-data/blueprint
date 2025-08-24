"""Core Blueprint base class with magic method generation."""

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Generic, Optional, Type, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from airflow import DAG

T = TypeVar("T", bound=BaseModel)


class Blueprint(Generic[T]):
    """Base class for all Blueprint templates.

    This class uses __init_subclass__ to dynamically generate a `build` method
    with the proper signature based on the Pydantic model used as the type parameter.

    Example:
        class MyConfig(BaseModel):
            job_id: str
            schedule: str = "@daily"

        class MyBlueprint(Blueprint[MyConfig]):
            def render(self, config: MyConfig) -> DAG:
                return DAG(dag_id=config.job_id, schedule=config.schedule)

        # The build method is automatically generated with proper types
        dag = MyBlueprint.build(job_id="my_job", schedule="@hourly")
    """

    _config_type: Type[BaseModel]

    def __init_subclass__(cls, **kwargs):
        """Generate the build method when a Blueprint subclass is defined."""
        super().__init_subclass__(**kwargs)

        # Extract config type from Generic[T] parameter
        orig_bases = getattr(cls, "__orig_bases__", ())
        for base in orig_bases:
            if hasattr(base, "__args__") and base.__args__:
                config_type = base.__args__[0]
                # Verify it's a Pydantic model
                if isinstance(config_type, type) and issubclass(config_type, BaseModel):
                    cls._config_type = config_type
                    cls._generate_build_method(config_type)
                break

    @classmethod
    def _generate_build_method(cls, config_type: Type[BaseModel]) -> None:
        """Generate the build method with proper signature from Pydantic model."""

        # Get model fields from Pydantic

        # Create parameters from Pydantic model fields
        params = [inspect.Parameter("cls", inspect.Parameter.POSITIONAL_OR_KEYWORD)]

        # Get field definitions from the model
        for field_name, field_info in config_type.model_fields.items():
            # Determine if field has a default
            if field_info.is_required():
                default = inspect.Parameter.empty
            else:
                default = field_info.get_default(call_default_factory=True)

            # Create parameter with proper annotation
            param = inspect.Parameter(
                field_name,
                inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=field_info.annotation,
            )
            params.append(param)

        # Create the build method
        def build(cls, **kwargs: Any):
            """Build a DAG from the provided configuration.

            This method is dynamically generated with the proper signature
            based on the Blueprint's configuration model.
            """
            # Create the config instance - Pydantic handles validation
            config = cls._config_type(**kwargs)

            # Create blueprint instance and render
            instance = cls()
            return instance.render(config)

        # Set the proper signature on the build method
        build.__signature__ = inspect.Signature(params, return_annotation="DAG")  # type: ignore[assignment]

        # Bind as classmethod
        cls.build = classmethod(build)

    def render(self, config: T) -> "DAG":
        """Render the DAG with validated configuration.

        This method must be implemented by Blueprint subclasses.

        Args:
            config: The validated configuration model instance

        Returns:
            The rendered Airflow DAG

        Example:
            ```python
            class MyConfig(BaseModel):
                dag_id: str
                schedule: str = "@daily"

            class MyBlueprint(Blueprint[MyConfig]):
                def render(self, config: MyConfig) -> DAG:
                    return DAG(
                        dag_id=config.dag_id,
                        schedule=config.schedule,
                        start_date=datetime(2024, 1, 1)
                    )
            ```
        """
        msg = f"{self.__class__.__name__} must implement the render() method"
        raise NotImplementedError(msg)

    @classmethod
    def get_config_type(cls) -> Type[BaseModel]:
        """Get the configuration type for this Blueprint."""
        if not hasattr(cls, "_config_type"):
            msg = (
                f"{cls.__name__} was not properly initialized. "
                "Make sure it inherits from Blueprint[ConfigType]"
            )
            raise RuntimeError(msg)
        return cls._config_type

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """Get the JSON Schema for this Blueprint's configuration."""
        return cls.get_config_type().model_json_schema()

    def write_dag_file(self, config: T, dag_id: str, output_file: Optional[str] = None) -> str:
        """Write the rendered DAG code to a .py file in the dags folder.

        Args:
            config: The validated configuration model instance
            dag_id: The DAG ID to use in the generated file
            output_file: Optional output file path. If not provided, uses dag_id.py in dags folder

        Returns:
            Path to the created file

        Example:
            ```python
            class MyConfig(BaseModel):
                job_id: str
                schedule: str = "@daily"

            blueprint = MyBlueprint()
            config = MyConfig(job_id="my_job", schedule="@hourly")
            file_path = blueprint.write_dag_file(config, "my_job")
            print(f"DAG file written to: {file_path}")
            ```
        """
        from .utils import get_airflow_dags_folder

        # Determine output file path
        if output_file is None:
            dags_folder = get_airflow_dags_folder()
            output_file = str(dags_folder / f"{dag_id}.py")
        
        # Get the template name and class name for this blueprint
        template_name = self._get_template_name()
        class_name = self.__class__.__name__
        
        # Generate the Python code
        dag_code = self._generate_dag_code(config, template_name, class_name)
        
        # Write the file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(dag_code)
        
        return str(output_path)

    @classmethod
    def write_dag_file_from_config(
        cls, dag_id: str, output_file: Optional[str] = None, **kwargs: Any
    ) -> str:
        """Class method to write DAG file directly from configuration parameters.

        Args:
            dag_id: The DAG ID to use in the generated file
            output_file: Optional output file path. If not provided, uses dag_id.py in dags folder
            **kwargs: Configuration parameters for the blueprint

        Returns:
            Path to the created file

        Example:
            ```python
            file_path = MyBlueprint.write_dag_file_from_config(
                dag_id="my_job",
                job_id="my_job",
                schedule="@hourly",
                retries=3
            )
            print(f"DAG file written to: {file_path}")
            ```
        """
        # Create the config instance - Pydantic handles validation
        config = cls._config_type(**kwargs)
        
        # Create blueprint instance and call instance method
        instance = cls()
        return instance.write_dag_file(config, dag_id, output_file)

    def _get_template_name(self) -> str:
        """Get the template name for this blueprint.
        
        By convention, convert CamelCase class name to snake_case template name.
        E.g., DailyETL -> daily_etl, MultiSourceETL -> multi_source_etl
        """
        class_name = self.__class__.__name__
        
        # Convert CamelCase to snake_case
        # Handle special cases like ETL -> etl
        template_name = ""
        for i, char in enumerate(class_name):
            if char.isupper() and i > 0:
                # Don't add underscore if previous char was also uppercase (handle acronyms)
                if i > 0 and class_name[i-1].islower():
                    template_name += "_"
            template_name += char.lower()
        
        return template_name

    def _generate_dag_code(self, config: T, template_name: str, class_name: str) -> str:
        """Generate the Python code for the DAG file with full rendered DAG content."""
        # Render the DAG to get the actual DAG object
        dag = self.render(config)
        
        # Extract imports needed for the DAG
        imports = self._extract_imports(dag)
        
        # Generate the DAG definition code
        dag_definition = self._generate_dag_definition(dag)
        
        # Generate task definitions
        task_definitions = self._generate_task_definitions(dag)
        
        # Generate task dependencies
        dependencies = self._generate_dependencies(dag)
        
        return f'''"""Auto-generated DAG file from Blueprint."""

{imports}

{dag_definition}

{task_definitions}

{dependencies}
'''

    def _extract_imports(self, dag: "DAG") -> str:
        """Extract the necessary imports for the DAG and its tasks."""
        imports = set()
        
        # Always need these basic imports
        imports.add("from datetime import datetime, timedelta, timezone")
        imports.add("from airflow import DAG")
        
        # Extract imports based on task types
        for task in dag.tasks:
            task_module = task.__class__.__module__
            task_class = task.__class__.__name__
            imports.add(f"from {task_module} import {task_class}")
        
        return "\n".join(sorted(imports))
    
    def _generate_dag_definition(self, dag: "DAG") -> str:
        """Generate the DAG definition code."""
        # Extract DAG parameters
        dag_params = []
        
        dag_params.append(f'    dag_id="{dag.dag_id}",')
        
        if hasattr(dag, 'default_args') and dag.default_args:
            default_args_lines = []
            for key, value in dag.default_args.items():
                if isinstance(value, str):
                    default_args_lines.append(f'    "{key}": "{value}",')
                elif value.__class__.__name__ == 'timedelta':
                    # Handle timedelta objects
                    total_seconds = int(value.total_seconds())
                    if total_seconds % 3600 == 0:
                        default_args_lines.append(f'    "{key}": timedelta(hours={total_seconds // 3600}),')
                    elif total_seconds % 60 == 0:
                        default_args_lines.append(f'    "{key}": timedelta(minutes={total_seconds // 60}),')
                    else:
                        default_args_lines.append(f'    "{key}": timedelta(seconds={total_seconds}),')
                else:
                    default_args_lines.append(f'    "{key}": {repr(value)},')
            
            default_args_str = "{\n" + "\n".join(default_args_lines) + "\n}"
            dag_params.append(f"    default_args={default_args_str},")
        
        if hasattr(dag, 'description') and dag.description:
            dag_params.append(f'    description="{dag.description}",')
        
        if hasattr(dag, 'schedule_interval') and dag.schedule_interval:
            if isinstance(dag.schedule_interval, str):
                dag_params.append(f'    schedule="{dag.schedule_interval}",')
            else:
                dag_params.append(f'    schedule={repr(dag.schedule_interval)},')
        elif hasattr(dag, 'schedule') and dag.schedule:
            if isinstance(dag.schedule, str):
                dag_params.append(f'    schedule="{dag.schedule}",')
            else:
                dag_params.append(f'    schedule={repr(dag.schedule)},')
        
        if hasattr(dag, 'start_date') and dag.start_date:
            # Handle datetime objects
            if dag.start_date.tzinfo:
                dag_params.append(f'    start_date=datetime({dag.start_date.year}, {dag.start_date.month}, {dag.start_date.day}, tzinfo=timezone.utc),')
            else:
                dag_params.append(f'    start_date=datetime({dag.start_date.year}, {dag.start_date.month}, {dag.start_date.day}),')
        
        if hasattr(dag, 'catchup'):
            dag_params.append(f'    catchup={dag.catchup},')
        
        if hasattr(dag, 'tags') and dag.tags:
            tags_str = "[" + ", ".join(f'"{tag}"' for tag in dag.tags) + "]"
            dag_params.append(f'    tags={tags_str},')
        
        dag_params_str = "\n".join(dag_params)
        
        return f"""dag = DAG(
{dag_params_str}
)"""
    
    def _generate_task_definitions(self, dag: "DAG") -> str:
        """Generate task definitions from the DAG."""
        task_definitions = []
        
        for task in dag.tasks:
            task_def = self._generate_single_task_definition(task)
            task_definitions.append(task_def)
        
        return "\n\n".join(task_definitions)
    
    def _generate_single_task_definition(self, task) -> str:
        """Generate the definition for a single task."""
        task_class = task.__class__.__name__
        task_params = []
        
        # Always include task_id and dag
        task_params.append(f'    task_id="{task.task_id}",')
        task_params.append(f'    dag=dag,')
        
        # Handle common task parameters
        if hasattr(task, 'bash_command') and task.bash_command:
            # BashOperator
            bash_cmd = task.bash_command.replace('"', '\\"')
            task_params.append(f'    bash_command="{bash_cmd}",')
        
        if hasattr(task, 'python_callable') and task.python_callable:
            # PythonOperator
            func_name = task.python_callable.__name__
            task_params.append(f'    python_callable={func_name},')
            
            # We need to include the function definition before the task
            if hasattr(task.python_callable, '__code__'):
                func_def = self._extract_function_definition(task.python_callable)
                return f"""{func_def}

{task.task_id} = {task_class}(
{chr(10).join(task_params)}
)"""
        
        if hasattr(task, 'sql') and task.sql:
            # SQL operators
            sql_cmd = task.sql.replace('"', '\\"')
            task_params.append(f'    sql="{sql_cmd}",')
        
        task_params_str = "\n".join(task_params)
        
        return f"""{task.task_id} = {task_class}(
{task_params_str}
)"""
    
    def _extract_function_definition(self, func) -> str:
        """Extract function definition from a callable."""
        import inspect
        try:
            # Get the source code of the function
            source_lines = inspect.getsourcelines(func)[0]
            # Remove the indentation from the first line to get base indentation
            base_indent = len(source_lines[0]) - len(source_lines[0].lstrip())
            
            # Remove base indentation from all lines
            cleaned_lines = []
            for line in source_lines:
                if len(line.strip()) > 0:  # Skip empty lines
                    cleaned_lines.append(line[base_indent:])
                else:
                    cleaned_lines.append(line)
            
            return "".join(cleaned_lines).rstrip()
        except (OSError, TypeError):
            # If we can't get the source, create a placeholder
            return f"""def {func.__name__}(**_):
    \"\"\"Auto-generated function placeholder.\"\"\"
    pass"""
    
    def _generate_dependencies(self, dag: "DAG") -> str:
        """Generate task dependency definitions."""
        dependencies = []
        
        for task in dag.tasks:
            if hasattr(task, 'upstream_task_ids') and task.upstream_task_ids:
                upstream_tasks = list(task.upstream_task_ids)
                if len(upstream_tasks) == 1:
                    dependencies.append(f"{upstream_tasks[0]} >> {task.task_id}")
                elif len(upstream_tasks) > 1:
                    upstream_str = " >> ".join(upstream_tasks)
                    dependencies.append(f"[{upstream_str}] >> {task.task_id}")
        
        # Also check for explicitly set dependencies using >> operator
        # This is a simplified approach - in practice, Airflow stores dependencies
        # in both upstream and downstream relationships
        processed_deps = set()
        for task in dag.tasks:
            if hasattr(task, 'downstream_task_ids') and task.downstream_task_ids:
                for downstream_id in task.downstream_task_ids:
                    dep_str = f"{task.task_id} >> {downstream_id}"
                    if dep_str not in processed_deps:
                        dependencies.append(dep_str)
                        processed_deps.add(dep_str)
        
        return "\n".join(dependencies) if dependencies else ""
