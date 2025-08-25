"""Core Blueprint base class with magic method generation."""

import inspect
import logging
from pathlib import Path
from typing import Any, Generic, TypeVar

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel

logger = logging.getLogger(__name__)

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

    _config_type: type[BaseModel]

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
                        if hasattr(potential_type, "__dict__") or hasattr(
                            potential_type, "model_fields"
                        ):
                            config_type = potential_type
                            break
                    except Exception:
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
                    if (
                        name.endswith("Config")
                        and inspect.isclass(obj)
                        and name.startswith(
                            cls.__name__.replace("Blueprint", "")
                            .replace("ETL", "")
                            .replace("Job", "")
                        )
                    ):
                        cls._config_type = obj
                        cls._generate_build_method(obj)
                        break

    @classmethod
    def _generate_build_method(cls, config_type: type[BaseModel]) -> None:
        """Generate the build method with proper signature from config model."""
        # Create parameters for the build method - simplified for stub compatibility
        params = [inspect.Parameter("cls", inspect.Parameter.POSITIONAL_OR_KEYWORD)]

        # Try to get field definitions from the model if available
        if hasattr(config_type, "model_fields") and callable(config_type.model_fields):
            try:
                for field_name, field_info in config_type.model_fields.items():
                    # Determine if field has a default - simplified approach
                    try:
                        if (
                            hasattr(field_info, "is_required")
                            and field_info.is_required()
                        ):
                            default = inspect.Parameter.empty
                        elif hasattr(field_info, "get_default"):
                            default = field_info.get_default(call_default_factory=True)
                        else:
                            default = None
                    except Exception:
                        default = None

                    # Create parameter with basic annotation
                    param = inspect.Parameter(
                        field_name,
                        inspect.Parameter.KEYWORD_ONLY,
                        default=default,
                        annotation=getattr(field_info, "annotation", Any),
                    )
                    params.append(param)
            except Exception as exc:
                # If field introspection fails, create a simple **kwargs method
                logger.exception(
                    "Field introspection failed for config type %s: %s",
                    config_type.__name__,
                    exc,
                )

        # Note: The build() method has been removed as Blueprint now focuses
        # on build-time DAG generation. Use build_template() instead.

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

    def _get_template_path(self) -> Path:
        """Get the path to the *.py.j2 template for this blueprint."""
        # Get the template name based on the blueprint class name
        class_name = self.__class__.__name__
        class_name = class_name.removesuffix("Blueprint")  # Remove 'Blueprint' suffix

        # Convert CamelCase to snake_case for template naming
        import re

        blueprint_name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", class_name).lower()

        # Look for .py.j2 template files in multiple locations
        possible_paths = [
            # In the same directory as the blueprint class
            Path(inspect.getfile(self.__class__)).parent / f"{blueprint_name}.py.j2",
            # In the blueprint package templates directory
            Path(__file__).parent / "templates" / f"{blueprint_name}.py.j2",
            # In the examples templates directory (for development)
            Path(__file__).parent.parent
            / "examples"
            / "dags"
            / "templates"
            / f"{blueprint_name}.py.j2",
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
                f"Create a *.py.j2 template file for {self.__class__.__name__} "
                f"to enable template-based DAG generation."
            )
            raise FileNotFoundError(msg)

        # Create Jinja2 environment with the template directory
        env = Environment(
            loader=FileSystemLoader(str(template_path.parent)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        return env.get_template(template_path.name)

    def _render_jinja_template(self, config: T) -> str:
        """Render the Jinja2 template with the given configuration."""
        template = self._load_template()
        return template.render(config=config)

    def _generate_template_from_render(self, config: T) -> str:
        """Generate a template by inspecting the render() method.

        This is a fallback implementation that tries to create a template
        from the existing render() method by analyzing its code.
        """
        # For now, return a basic template structure
        # This will be enhanced with actual code analysis
        dag_id = getattr(config, "dag_id", getattr(config, "job_id", "unknown_dag"))

        return f'''
"""Auto-generated DAG from Blueprint template."""

from airflow import DAG
from datetime import datetime, timedelta, timezone

# DAG generated from {self.__class__.__name__}
# Configuration: {config.__dict__ if hasattr(config, "__dict__") else "N/A"}

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
    def build_template(
        cls, output_file: str | None = None, lint: bool = True, **kwargs: Any
    ) -> str:
        """Build a DAG template string from the provided configuration.

        This method generates a Python code string that can be written to a file
        or executed to create the DAG.

        Args:
            output_file: Optional path where the template will be saved
            lint: Whether to automatically lint the generated DAG file with Ruff
            **kwargs: Configuration parameters for the Blueprint

        Returns:
            Python code string that defines the DAG
        """
        # Get config type - handle both properly initialized classes and manual setup
        if hasattr(cls, "_config_type"):
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
                        if name.endswith("Config") and inspect.isclass(obj):
                            config_type = obj
                            cls._config_type = config_type
                            break

            if not config_type:
                raise RuntimeError(
                    f"Could not determine config type for {cls.__name__}"
                )

        # Create the config instance
        config = config_type(**kwargs)

        # Create blueprint instance and render template
        instance = cls()
        template_code = instance.render_template(config)  # type: ignore[arg-type]

        # Optionally write to file and lint
        if output_file:
            from pathlib import Path

            output_path = Path(output_file)
            output_path.write_text(template_code)

            # Lint the generated file
            if lint:
                from .linter import lint_dag_file

                lint_dag_file(output_path, fix=True, format_code=True)

        return template_code
