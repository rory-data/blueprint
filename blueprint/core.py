"""Core Blueprint base class with magic method generation."""

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Generic, Type, TypeVar

# Handle missing dependencies gracefully
try:
    from pydantic import BaseModel
except ImportError:
    # Define a minimal BaseModel for development
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        @classmethod
        def model_fields(cls):
            return {}
        
        @classmethod
        def model_json_schema(cls):
            return {}
        
        def __dict__(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

try:
    from jinja2 import Environment, FileSystemLoader, Template
except ImportError:
    # Fallback when Jinja2 is not available
    class Template:
        def __init__(self, source):
            self.source = source
        
        def render(self, **kwargs):
            return self.source
    
    class Environment:
        def __init__(self, **kwargs):
            pass
        
        def get_template(self, name):
            return Template(f"# Template {name} not available without Jinja2")
    
    class FileSystemLoader:
        def __init__(self, *args, **kwargs):
            pass

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
        config_type = None
        orig_bases = getattr(cls, "__orig_bases__", ())
        for base in orig_bases:
            if hasattr(base, "__args__") and base.__args__:
                potential_type = base.__args__[0]
                # Verify it's a class that could be a config type
                if isinstance(potential_type, type):
                    try:
                        # Try to check if it has BaseModel-like characteristics
                        if hasattr(potential_type, '__dict__') or hasattr(potential_type, 'model_fields'):
                            config_type = potential_type
                            break
                    except:
                        # If we can't determine, assume it's good
                        config_type = potential_type
                        break
        
        # If we found a config type, set it and generate the build method
        if config_type:
            cls._config_type = config_type
            cls._generate_build_method(config_type)
        else:
            # Fallback: look for a Config class in the same module as the Blueprint
            import inspect
            module = inspect.getmodule(cls)
            if module:
                for name, obj in inspect.getmembers(module):
                    if name.endswith('Config') and inspect.isclass(obj) and name.startswith(cls.__name__.replace('Blueprint', '').replace('ETL', '').replace('Job', '')):
                        cls._config_type = obj
                        cls._generate_build_method(obj)
                        break

    @classmethod
    def _generate_build_method(cls, config_type: Type) -> None:
        """Generate the build method with proper signature from config model."""

        # Create parameters for the build method - simplified for stub compatibility
        params = [inspect.Parameter("cls", inspect.Parameter.POSITIONAL_OR_KEYWORD)]

        # Try to get field definitions from the model if available
        if hasattr(config_type, 'model_fields') and callable(config_type.model_fields):
            try:
                for field_name, field_info in config_type.model_fields().items():
                    # Determine if field has a default - simplified approach
                    try:
                        if hasattr(field_info, 'is_required') and field_info.is_required():
                            default = inspect.Parameter.empty
                        elif hasattr(field_info, 'get_default'):
                            default = field_info.get_default(call_default_factory=True)
                        else:
                            default = None
                    except:
                        default = None

                    # Create parameter with basic annotation
                    param = inspect.Parameter(
                        field_name,
                        inspect.Parameter.KEYWORD_ONLY,
                        default=default,
                        annotation=getattr(field_info, 'annotation', Any),
                    )
                    params.append(param)
            except:
                # If field introspection fails, create a simple **kwargs method
                pass

        # Create the build method
        def build(cls, **kwargs: Any):
            """Build a DAG from the provided configuration.

            This method is dynamically generated with the proper signature
            based on the Blueprint's configuration model.
            """
            # Create the config instance
            config = cls._config_type(**kwargs)

            # Create blueprint instance and render
            instance = cls()
            return instance.render(config)

        # Set the proper signature on the build method
        try:
            build.__signature__ = inspect.Signature(params, return_annotation="DAG")  # type: ignore[assignment]
        except:
            # If signature creation fails, just use the basic method
            pass

        # Bind as classmethod
        cls.build = classmethod(build)

    def render(self, config: T) -> "DAG":
        """Render the DAG with validated configuration.

        This method uses Jinja2 templates when available, or must be implemented 
        by Blueprint subclasses for custom DAG generation logic.

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
                # Uses Jinja2 template automatically, or implement custom logic:
                def render(self, config: MyConfig) -> DAG:
                    return DAG(
                        dag_id=config.dag_id,
                        schedule=config.schedule,
                        start_date=datetime(2024, 1, 1)
                    )
            ```
        """
        # Try to use Jinja2 template first
        try:
            template_code = self._render_jinja_template(config)
            return self._execute_template_code(template_code)
        except FileNotFoundError:
            # No template found, subclass must implement this method
            msg = (
                f"{self.__class__.__name__} must either provide a Jinja2 template "
                f"or implement the render() method"
            )
            raise NotImplementedError(msg)

    def _execute_template_code(self, template_code: str) -> "DAG":
        """Execute the rendered template code to create a DAG object."""
        # Create a local namespace for execution
        local_namespace = {}
        global_namespace = {}
        
        # Execute the template code
        exec(template_code, global_namespace, local_namespace)
        
        # Find the DAG object in the executed code
        dag = local_namespace.get('dag')
        if dag is None:
            msg = "Template code did not create a 'dag' variable"
            raise RuntimeError(msg)
        
        return dag

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

    def _get_template_path(self) -> Path:
        """Get the path to the Jinja2 template for this blueprint."""
        # Get the template name based on the blueprint class name
        class_name = self.__class__.__name__
        if class_name.endswith('Blueprint'):
            class_name = class_name[:-9]  # Remove 'Blueprint' suffix
        
        # Convert CamelCase to snake_case for template naming
        import re
        blueprint_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', class_name).lower()
        
        # Look for template in multiple locations
        possible_paths = [
            # In the same directory as the blueprint class
            Path(inspect.getfile(self.__class__)).parent / "j2" / f"{blueprint_name}.j2",
            # In the blueprint package templates directory
            Path(__file__).parent / "templates" / f"{blueprint_name}.j2",
            # In the examples templates directory (for development)
            Path(__file__).parent.parent / "examples" / ".astro" / "templates" / "j2" / f"{blueprint_name}.j2",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Return the first possible path for error messaging
        return possible_paths[0]

    def _load_template(self) -> Template:
        """Load the Jinja2 template for this blueprint."""
        template_path = self._get_template_path()
        
        if not template_path.exists():
            msg = (
                f"Template file not found: {template_path}. "
                f"Create a Jinja2 template file for {self.__class__.__name__} "
                f"to enable template-based DAG generation."
            )
            raise FileNotFoundError(msg)
        
        # Create Jinja2 environment with the template directory
        env = Environment(
            loader=FileSystemLoader(str(template_path.parent)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        return env.get_template(template_path.name)

    def _render_jinja_template(self, config: T) -> str:
        """Render the Jinja2 template with the given configuration."""
        template = self._load_template()
        return template.render(config=config)

    def render_template(self, config: T) -> str:
        """Render the DAG as a Python code string template.

        This method uses Jinja2 templates to generate DAG code, following DRY principles
        by using the same template structure for both runtime and build-time generation.

        Args:
            config: The validated configuration model instance

        Returns:
            Python code string that defines the DAG

        Example:
            ```python
            class MyBlueprint(Blueprint[MyConfig]):
                # No need to implement render_template - uses Jinja2 template
                pass
            ```
        """
        try:
            return self._render_jinja_template(config)
        except FileNotFoundError:
            # Fallback to the old method if no template is found
            return self._generate_template_from_render(config)

    def _generate_template_from_render(self, config: T) -> str:
        """Generate a template by inspecting the render() method.
        
        This is a fallback implementation that tries to create a template
        from the existing render() method by analyzing its code.
        """
        # For now, return a basic template structure
        # This will be enhanced with actual code analysis
        dag_id = getattr(config, 'dag_id', getattr(config, 'job_id', 'unknown_dag'))
        
        return f'''
"""Auto-generated DAG from Blueprint template."""

from airflow import DAG
from datetime import datetime, timedelta, timezone

# DAG generated from {self.__class__.__name__}
# Configuration: {config.__dict__ if hasattr(config, '__dict__') else 'N/A'}

dag = DAG(
    dag_id="{dag_id}",
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["blueprint", "auto-generated"],
)

# TODO: Add tasks based on Blueprint implementation
# This is a placeholder - implement render_template() in your Blueprint class
# for full template generation support.
'''

    @classmethod
    def build_template(cls, output_file: str = None, **kwargs: Any) -> str:
        """Build a DAG template string from the provided configuration.

        This method generates a Python code string that can be written to a file
        or executed to create the DAG.

        Args:
            output_file: Optional path where the template will be saved
            **kwargs: Configuration parameters for the Blueprint

        Returns:
            Python code string that defines the DAG
        """
        # Get config type - handle both properly initialized classes and manual setup
        if hasattr(cls, '_config_type'):
            config_type = cls._config_type
        else:
            # Try to extract from __orig_bases__ if not already processed
            orig_bases = getattr(cls, "__orig_bases__", ())
            config_type = None
            for base in orig_bases:
                if hasattr(base, "__args__") and base.__args__:
                    potential_type = base.__args__[0]
                    # Check if it's a class that could be a config type
                    if isinstance(potential_type, type):
                        config_type = potential_type
                        cls._config_type = config_type  # Cache it
                        break
            
            if not config_type:
                # Fallback: look for a Config class in the same module
                import inspect
                module = inspect.getmodule(cls)
                if module:
                    for name, obj in inspect.getmembers(module):
                        if name.endswith('Config') and inspect.isclass(obj):
                            config_type = obj
                            cls._config_type = config_type
                            break
                            
            if not config_type:
                raise RuntimeError(f"Could not determine config type for {cls.__name__}")

        # Create the config instance
        config = config_type(**kwargs)

        # Create blueprint instance and render template
        instance = cls()
        template_code = instance.render_template(config)
        
        # Optionally write to file
        if output_file:
            from pathlib import Path
            Path(output_file).write_text(template_code)
        
        return template_code
