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
        from .dag_writer import DAGWriter
        from .utils import get_airflow_dags_folder

        # Determine output file path
        if output_file is None:
            dags_folder = get_airflow_dags_folder()
            output_file = str(dags_folder / f"{dag_id}.py")
        
        # Render the DAG and write to file
        dag = self.render(config)
        
        writer = DAGWriter()
        output_path = Path(output_file)
        writer.write_dag_to_file(dag, output_path)
        
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
