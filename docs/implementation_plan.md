# Blueprint Implementation Plan

This document outlines the complete implementation plan for the Blueprint project, breaking down the work into phases with clear milestones and dependencies.

## Project Overview

Blueprint is a system for creating reusable Airflow DAG templates with validated configurations. It allows data platform engineers to create type-safe, parameterized DAG patterns that can be easily configured by analysts and other team members through simple YAML files.

## Architecture Overview

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Blueprint Class   │    │   Discovery System  │    │   Config Parser     │
│                     │    │                     │    │                     │
│ - TypedDict config  │    │ - Scan .astro/      │    │ - YAML validation   │
│ - render() method   │    │ - Load blueprints   │    │ - Type checking     │
│ - defaults dict     │    │ - Registry storage  │    │ - Error messages    │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       │
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   CLI Interface     │    │   DAG Generator     │    │   Error System      │
│                     │    │                     │    │                     │
│ - blueprint lint    │    │ - Auto-discovery    │    │ - Rust-like errors  │
│ - blueprint new     │    │ - Config merging    │    │ - Line numbers      │
│ - blueprint list    │    │ - DAG instantiation │    │ - Suggestions       │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## Phase 1: Core Foundation (Weeks 1-2)

### 1.1 Core Blueprint Base Class
**File:** `src/blueprint/core.py`

```python
from typing import TypedDict, Generic, TypeVar, Dict, Any, Optional
from abc import ABC, abstractmethod

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

T = TypeVar('T', bound=TypedDict)

class Blueprint(Generic[T], ABC):
    """Base class for all blueprints."""
    
    # Optional explicit name override
    name: Optional[str] = None
    
    # Default values for config parameters
    defaults: Dict[str, Any] = {}
    
    # Parameter descriptions (extracted from Annotated types)
    _descriptions: Dict[str, str] = {}
    
    @abstractmethod
    def render(self, config: T) -> 'DAG':
        """Render the blueprint into an Airflow DAG."""
        pass
    
    @classmethod
    def get_name(cls) -> str:
        """Get blueprint name (explicit or auto-generated)."""
        if cls.name:
            return cls.name
        # Convert "DailyETLBlueprint" -> "daily_etl"
        name = cls.__name__
        if name.endswith("Blueprint"):
            name = name[:-9]
        return camel_to_snake(name)
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Extract schema from TypedDict type parameter."""
        # Implementation uses typing introspection
        pass
    
    @classmethod
    def get_required_params(cls) -> List[str]:
        """Get list of required parameters."""
        pass
    
    @classmethod
    def get_param_descriptions(cls) -> Dict[str, str]:
        """Get parameter descriptions from Annotated types."""
        pass
```

**Key Features:**
- Generic base class with TypedDict config type
- Auto-name generation from class name
- Schema introspection from TypedDict
- Default value handling
- Parameter description extraction from `Annotated` types

**Tests:** `tests/test_core.py`
- Test name generation
- Test schema extraction
- Test defaults merging
- Test inheritance patterns

### 1.2 Blueprint Discovery System
**File:** `src/blueprint/discovery.py`

```python
import os
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Type
from .core import Blueprint

class BlueprintRegistry:
    """Registry for discovered blueprints."""
    
    def __init__(self):
        self._blueprints: Dict[str, Type[Blueprint]] = {}
        self._templates_dir = self._get_templates_dir()
    
    def _get_templates_dir(self) -> Path:
        """Get templates directory from env var or default."""
        env_dir = os.getenv('BLUEPRINT_TEMPLATES_DIR')
        if env_dir:
            return Path(env_dir)
        return Path('.astro/templates')
    
    def discover_blueprints(self) -> None:
        """Scan templates directory and load all blueprints."""
        if not self._templates_dir.exists():
            return
        
        for py_file in self._templates_dir.glob('**/*.py'):
            if py_file.name.startswith('_'):
                continue
            self._load_file(py_file)
    
    def _load_file(self, file_path: Path) -> None:
        """Load blueprints from a Python file."""
        spec = importlib.util.spec_from_file_location(
            f"blueprint_module_{file_path.stem}", 
            file_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find all Blueprint subclasses
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, Blueprint) and 
                obj != Blueprint and 
                not inspect.isabstract(obj)):
                blueprint_name = obj.get_name()
                if blueprint_name in self._blueprints:
                    # Handle conflicts - warn and use most recent
                    pass
                self._blueprints[blueprint_name] = obj
    
    def get_blueprint(self, name: str) -> Type[Blueprint]:
        """Get blueprint by name."""
        if name not in self._blueprints:
            raise BlueprintNotFoundError(f"Blueprint '{name}' not found")
        return self._blueprints[name]
    
    def list_blueprints(self) -> List[Dict[str, Any]]:
        """List all available blueprints with metadata."""
        return [
            {
                'name': name,
                'class': cls.__name__,
                'module': cls.__module__,
                'description': cls.__doc__ or '',
                'required_params': cls.get_required_params(),
                'defaults': cls.defaults
            }
            for name, cls in self._blueprints.items()
        ]

# Global registry instance
registry = BlueprintRegistry()
```

**Key Features:**
- Automatic discovery of blueprint classes
- Environment variable override for templates directory
- Conflict detection and resolution
- Lazy loading of blueprint modules
- Registry pattern for blueprint storage

**Tests:** `tests/test_discovery.py`
- Test file discovery
- Test blueprint loading
- Test environment variable override
- Test conflict handling
- Test error cases (malformed files, etc.)

### 1.3 Configuration Parser and Validator
**File:** `src/blueprint/config.py`

```python
import yaml
from pathlib import Path
from typing import Dict, Any, List
from .discovery import registry
from .errors import ValidationError, ConfigError

class ConfigParser:
    """Parse and validate blueprint configurations."""
    
    def __init__(self):
        self.registry = registry
    
    def parse_file(self, config_path: Path) -> Dict[str, Any]:
        """Parse YAML config file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {config_path}: {e}")
        
        return self.validate_config(config, config_path)
    
    def validate_config(self, config: Dict[str, Any], source_path: Path = None) -> Dict[str, Any]:
        """Validate configuration against blueprint schema."""
        if 'blueprint' not in config:
            raise ValidationError("Missing 'blueprint' field", source_path, 1)
        
        blueprint_name = config['blueprint']
        blueprint_cls = self.registry.get_blueprint(blueprint_name)
        
        # Extract DAG ID from filename if not provided
        if 'dag_id' not in config and source_path:
            dag_id = source_path.stem
            if dag_id.endswith('.dag'):
                dag_id = dag_id[:-4]
            config['dag_id'] = dag_id
        
        # Merge with defaults
        final_config = {**blueprint_cls.defaults, **config}
        
        # Validate required parameters
        required_params = blueprint_cls.get_required_params()
        missing_params = []
        for param in required_params:
            if param not in final_config:
                missing_params.append(param)
        
        if missing_params:
            raise ValidationError(
                f"Missing required parameters: {', '.join(missing_params)}",
                source_path,
                self._find_line_number(config, 'blueprint')
            )
        
        # Type validation
        self._validate_types(final_config, blueprint_cls, source_path)
        
        return final_config
    
    def _validate_types(self, config: Dict[str, Any], blueprint_cls, source_path: Path):
        """Validate config values against TypedDict schema."""
        schema = blueprint_cls.get_config_schema()
        # Implementation depends on runtime type checking library
        # Options: typeguard, pydantic, or custom implementation
        pass
    
    def _find_line_number(self, config: Dict[str, Any], key: str) -> int:
        """Find line number of key in original YAML (for error reporting)."""
        # This requires keeping track of line numbers during parsing
        # Implementation would use a custom YAML parser or ruamel.yaml
        return 1
```

**Key Features:**
- YAML parsing with error handling
- Schema validation against TypedDict
- Default value merging
- DAG ID extraction from filename
- Detailed error reporting with line numbers

**Tests:** `tests/test_config.py`
- Test YAML parsing
- Test validation success/failure cases
- Test default merging
- Test type validation
- Test error message quality

## Phase 2: Error Handling & CLI Foundation (Weeks 3-4)

### 2.1 Comprehensive Error System
**File:** `src/blueprint/errors.py`

```python
from typing import Optional, List, Dict, Any
from pathlib import Path

class BlueprintError(Exception):
    """Base exception for all blueprint errors."""
    pass

class ValidationError(BlueprintError):
    """Configuration validation error with rich context."""
    
    def __init__(self, message: str, file_path: Optional[Path] = None, 
                 line_number: Optional[int] = None, suggestions: Optional[List[str]] = None):
        self.message = message
        self.file_path = file_path
        self.line_number = line_number
        self.suggestions = suggestions or []
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format error message with context and suggestions."""
        lines = [f"✗ {self.file_path.name if self.file_path else 'Configuration Error'}"]
        
        if self.line_number:
            lines.append(f"  Line {self.line_number}: {self.message}")
        else:
            lines.append(f"  {self.message}")
        
        # Add file context if available
        if self.file_path and self.line_number:
            lines.extend(self._get_file_context())
        
        # Add suggestions
        if self.suggestions:
            lines.append("")
            lines.append("  Suggestions:")
            for suggestion in self.suggestions:
                lines.append(f"  • {suggestion}")
        
        return "\n".join(lines)
    
    def _get_file_context(self) -> List[str]:
        """Get surrounding lines from file for context."""
        try:
            with open(self.file_path, 'r') as f:
                file_lines = f.readlines()
            
            start = max(0, self.line_number - 3)
            end = min(len(file_lines), self.line_number + 2)
            
            context_lines = ["", "  Your configuration:"]
            for i in range(start, end):
                prefix = "    "
                if i == self.line_number - 1:  # Current line (0-indexed)
                    prefix = "  > "
                context_lines.append(f"{prefix}{i+1:2} | {file_lines[i].rstrip()}")
            
            return context_lines
        except Exception:
            return []

class BlueprintNotFoundError(BlueprintError):
    """Blueprint not found error with suggestions."""
    
    def __init__(self, blueprint_name: str, available_blueprints: List[str]):
        self.blueprint_name = blueprint_name
        self.available_blueprints = available_blueprints
        
        message = f"Blueprint '{blueprint_name}' not found"
        suggestions = []
        
        # Find similar blueprint names
        similar = self._find_similar_names(blueprint_name, available_blueprints)
        if similar:
            suggestions.append(f"Did you mean '{similar[0]}'?")
        
        if available_blueprints:
            suggestions.append(f"Available blueprints: {', '.join(available_blueprints)}")
        else:
            suggestions.extend([
                "No blueprints found in .astro/templates/",
                "Check: Is your blueprint file in .astro/templates/?",
                "Check: Does your class inherit from Blueprint[ConfigType]?"
            ])
        
        super().__init__(f"{message}\n\nSuggestions:\n" + "\n".join(f"• {s}" for s in suggestions))
    
    def _find_similar_names(self, name: str, available: List[str]) -> List[str]:
        """Find similar blueprint names using edit distance."""
        # Simple similarity check - could use more sophisticated algorithms
        similar = []
        for available_name in available:
            if self._edit_distance(name.lower(), available_name.lower()) <= 2:
                similar.append(available_name)
        return similar[:3]  # Top 3 suggestions
    
    def _edit_distance(self, s1: str, s2: str) -> int:
        """Calculate edit distance between two strings."""
        # Simple Levenshtein distance implementation
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
```

**Key Features:**
- Rich error messages with file context
- Line number reporting
- Suggestion system for common mistakes
- Fuzzy matching for blueprint names
- Consistent error formatting

**Tests:** `tests/test_errors.py`
- Test error message formatting
- Test suggestion generation
- Test file context extraction
- Test fuzzy matching accuracy

### 2.2 CLI Foundation
**File:** `src/blueprint/cli.py`

```python
import click
import sys
from pathlib import Path
from typing import List, Optional
from .discovery import registry
from .config import ConfigParser
from .errors import BlueprintError

@click.group()
@click.version_option()
def main():
    """Blueprint - Create reusable Airflow DAG templates."""
    # Initialize registry on CLI startup
    registry.discover_blueprints()

@main.command()
@click.argument('config_files', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option('--exit-code', is_flag=True, help='Exit with non-zero code on validation errors')
def lint(config_files: List[Path], exit_code: bool):
    """Validate blueprint configurations."""
    if not config_files:
        # Default: find all .dag.yaml files
        config_files = list(Path('dags/configs').glob('**/*.dag.yaml'))
        if not config_files:
            click.echo("No .dag.yaml files found in dags/configs/")
            return
    
    parser = ConfigParser()
    errors = []
    
    for config_file in config_files:
        try:
            parser.parse_file(config_file)
            click.echo(f"✓ {config_file.name} - Valid")
        except BlueprintError as e:
            errors.append(e)
            click.echo(str(e), err=True)
    
    if errors:
        click.echo(f"\n{len(errors)} error(s) found", err=True)
        if exit_code:
            sys.exit(1)

@main.command()
def list():
    """List available blueprints."""
    blueprints = registry.list_blueprints()
    
    if not blueprints:
        click.echo("No blueprints found in .astro/templates/")
        click.echo("\nTo get started:")
        click.echo("1. Create .astro/templates/ directory")
        click.echo("2. Add your first blueprint file")
        return
    
    click.echo("Available blueprints:\n")
    for bp in blueprints:
        click.echo(f"  {bp['name']} - {bp['description']}")
        if bp['required_params']:
            click.echo(f"    Required: {', '.join(bp['required_params'])}")

@main.command()
@click.argument('blueprint_name')
def describe(blueprint_name: str):
    """Show detailed information about a blueprint."""
    try:
        blueprint_cls = registry.get_blueprint(blueprint_name)
    except BlueprintError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    
    click.echo(f"Blueprint: {blueprint_name}")
    click.echo(f"Class: {blueprint_cls.__name__}")
    if blueprint_cls.__doc__:
        click.echo(f"Description: {blueprint_cls.__doc__}")
    
    # Show parameters
    schema = blueprint_cls.get_config_schema()
    descriptions = blueprint_cls.get_param_descriptions()
    required = blueprint_cls.get_required_params()
    
    click.echo("\nParameters:")
    for param, param_type in schema.items():
        if param == 'dag_id':
            continue  # Skip auto-provided parameter
        
        req_str = " (required)" if param in required else ""
        default_str = f" (default: {blueprint_cls.defaults.get(param)})" if param in blueprint_cls.defaults else ""
        desc_str = f" - {descriptions.get(param)}" if param in descriptions else ""
        
        click.echo(f"  {param}: {param_type}{req_str}{default_str}{desc_str}")

if __name__ == '__main__':
    main()
```

**Key Features:**
- Click-based CLI with subcommands
- Automatic discovery initialization
- Batch validation with error reporting
- Blueprint listing and description
- Exit codes for CI integration

**Tests:** `tests/test_cli.py`
- Test each CLI command
- Test error handling
- Test output formatting
- Test exit codes

## Phase 3: Advanced CLI Features (Weeks 5-6)

### 3.1 Interactive Blueprint Creation
**File:** `src/blueprint/scaffold.py`

```python
import questionary
from pathlib import Path
from typing import Dict, Any, Optional, List
from .discovery import registry
from .config import ConfigParser

class BlueprintScaffolder:
    """Interactive blueprint configuration scaffolding."""
    
    def __init__(self):
        self.registry = registry
        self.parser = ConfigParser()
    
    def interactive_create(self) -> Optional[Path]:
        """Create blueprint config through interactive prompts."""
        # Step 1: Get DAG name
        dag_name = questionary.text(
            "What should we name your DAG?",
            validate=self._validate_dag_name
        ).ask()
        
        if not dag_name:
            return None
        
        # Step 2: Choose blueprint
        blueprints = self.registry.list_blueprints()
        if not blueprints:
            questionary.print("No blueprints found. Please create blueprints first.", style="fg:red")
            return None
        
        choices = [
            questionary.Choice(
                title=f"{bp['name']} - {bp['description'][:60]}...",
                value=bp['name']
            )
            for bp in blueprints
        ]
        
        blueprint_name = questionary.select(
            "Which blueprint would you like to use?",
            choices=choices
        ).ask()
        
        if not blueprint_name:
            return None
        
        # Step 3: Get parameter values
        blueprint_cls = self.registry.get_blueprint(blueprint_name)
        config = {'blueprint': blueprint_name, 'dag_id': dag_name}
        
        schema = blueprint_cls.get_config_schema()
        descriptions = blueprint_cls.get_param_descriptions()
        required = blueprint_cls.get_required_params()
        defaults = blueprint_cls.defaults
        
        for param, param_type in schema.items():
            if param in ['dag_id', 'blueprint']:
                continue
            
            config[param] = self._prompt_for_parameter(
                param, param_type, descriptions.get(param), 
                param in required, defaults.get(param)
            )
        
        # Step 4: Choose output location
        output_path = self._get_output_path(dag_name)
        
        # Step 5: Generate config file
        self._write_config_file(config, output_path, blueprint_cls)
        
        questionary.print(f"Created: {output_path}", style="fg:green")
        return output_path
    
    def direct_create(self, blueprint_name: str, dag_name: str, 
                     output_path: Optional[Path] = None, 
                     overrides: Optional[Dict[str, Any]] = None) -> Path:
        """Create blueprint config directly with minimal prompts."""
        blueprint_cls = self.registry.get_blueprint(blueprint_name)
        
        config = {
            'blueprint': blueprint_name,
            'dag_id': dag_name,
            **blueprint_cls.defaults,
            **(overrides or {})
        }
        
        # Prompt for missing required parameters
        required = blueprint_cls.get_required_params()
        missing = [p for p in required if p not in config]
        
        if missing:
            questionary.print(f"Missing required parameters: {', '.join(missing)}")
            schema = blueprint_cls.get_config_schema()
            descriptions = blueprint_cls.get_param_descriptions()
            
            for param in missing:
                config[param] = self._prompt_for_parameter(
                    param, schema[param], descriptions.get(param), True, None
                )
        
        if not output_path:
            output_path = self._get_output_path(dag_name)
        
        self._write_config_file(config, output_path, blueprint_cls)
        return output_path
    
    def _prompt_for_parameter(self, param: str, param_type: str, 
                             description: Optional[str], required: bool, 
                             default: Any) -> Any:
        """Prompt user for a single parameter value."""
        prompt_text = f"Enter {param}"
        if description:
            prompt_text += f" ({description})"
        if not required and default is not None:
            prompt_text += f" (default: {default})"
        
        if required:
            return questionary.text(
                prompt_text + ":",
                validate=lambda x: len(x.strip()) > 0 or "This field is required"
            ).ask()
        else:
            result = questionary.text(prompt_text + ":").ask()
            return result if result else default
    
    def _validate_dag_name(self, dag_name: str) -> bool:
        """Validate DAG name follows Airflow conventions."""
        if not dag_name:
            return "DAG name is required"
        if not dag_name.replace('_', '').replace('-', '').isalnum():
            return "DAG name should only contain letters, numbers, underscores, and hyphens"
        return True
    
    def _get_output_path(self, dag_name: str) -> Path:
        """Get output path for config file."""
        default_path = Path(f"dags/configs/{dag_name}.dag.yaml")
        
        use_default = questionary.confirm(
            f"Save to {default_path}?",
            default=True
        ).ask()
        
        if use_default:
            default_path.parent.mkdir(parents=True, exist_ok=True)
            return default_path
        
        custom_path = questionary.path(
            "Enter output path:",
            validate=lambda p: p.endswith('.dag.yaml') or "Path must end with .dag.yaml"
        ).ask()
        
        return Path(custom_path)
    
    def _write_config_file(self, config: Dict[str, Any], output_path: Path, 
                          blueprint_cls) -> None:
        """Write config file with comments."""
        descriptions = blueprint_cls.get_param_descriptions()
        
        lines = [f"blueprint: {config['blueprint']}"]
        
        for key, value in config.items():
            if key == 'blueprint':
                continue
            
            # Add description as comment
            if key in descriptions:
                lines.append(f"# {descriptions[key]}")
            
            # Format value appropriately
            if isinstance(value, str):
                lines.append(f"{key}: \"{value}\"")
            else:
                lines.append(f"{key}: {value}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
```

### 3.2 Enhanced CLI Commands
**File:** Update `src/blueprint/cli.py`

```python
# Add to existing CLI

@main.command()
@click.argument('args', nargs=-1)
@click.option('--set', 'overrides', multiple=True, help='Set parameter values (key=value)')
@click.option('--output', type=click.Path(path_type=Path), help='Output file path')
def new(args, overrides, output):
    """Create a new DAG configuration.
    
    Usage:
        blueprint new                              # Interactive mode
        blueprint new BLUEPRINT DAG_NAME           # Direct mode
        blueprint new PATH BLUEPRINT               # With custom path
    """
    from .scaffold import BlueprintScaffolder
    
    scaffolder = BlueprintScaffolder()
    
    # Parse overrides
    override_dict = {}
    for override in overrides:
        if '=' not in override:
            click.echo(f"Invalid override format: {override}. Use key=value", err=True)
            sys.exit(1)
        key, value = override.split('=', 1)
        override_dict[key] = value
    
    # Determine mode based on arguments
    if not args:
        # Interactive mode
        scaffolder.interactive_create()
    elif len(args) == 2:
        # Direct mode: blueprint new BLUEPRINT DAG_NAME
        blueprint_name, dag_name = args
        try:
            scaffolder.direct_create(blueprint_name, dag_name, output, override_dict)
        except BlueprintError as e:
            click.echo(str(e), err=True)
            sys.exit(1)
    elif len(args) == 2 and args[0].endswith('.dag.yaml'):
        # Path mode: blueprint new PATH BLUEPRINT
        output_path, blueprint_name = Path(args[0]), args[1]
        dag_name = output_path.stem.replace('.dag', '')
        try:
            scaffolder.direct_create(blueprint_name, dag_name, output_path, override_dict)
        except BlueprintError as e:
            click.echo(str(e), err=True)
            sys.exit(1)
    else:
        click.echo("Invalid arguments. Use 'blueprint new --help' for usage.", err=True)
        sys.exit(1)
```

**Key Features:**
- Interactive questionary-based interface
- Flexible argument parsing
- Parameter validation and prompting
- File path handling
- Comment generation in output files

**Tests:** `tests/test_scaffold.py`
- Test interactive flow
- Test direct creation
- Test parameter validation
- Test file generation

## Phase 4: DAG Generation System (Weeks 7-8)

### 4.1 DAG Auto-Discovery and Generation
**File:** `src/blueprint/generator.py`

```python
from pathlib import Path
from typing import Dict, Any, List
import importlib.util
from airflow import DAG
from .discovery import registry
from .config import ConfigParser
from .errors import BlueprintError

class DAGGenerator:
    """Generate DAGs from blueprint configurations."""
    
    def __init__(self):
        self.registry = registry
        self.parser = ConfigParser()
        self._generated_dags: Dict[str, DAG] = {}
    
    def discover_and_generate_dags(self, config_dir: Path = None) -> Dict[str, DAG]:
        """Discover all config files and generate DAGs."""
        if config_dir is None:
            config_dir = Path('dags/configs')
        
        if not config_dir.exists():
            return {}
        
        dag_configs = []
        for config_file in config_dir.glob('**/*.dag.yaml'):
            try:
                config = self.parser.parse_file(config_file)
                dag_configs.append((config_file, config))
            except BlueprintError as e:
                # Log error but continue processing other configs
                print(f"Error processing {config_file}: {e}")
                continue
        
        # Generate DAGs
        for config_file, config in dag_configs:
            try:
                dag = self.generate_dag(config)
                self._generated_dags[dag.dag_id] = dag
            except Exception as e:
                print(f"Error generating DAG from {config_file}: {e}")
                continue
        
        return self._generated_dags
    
    def generate_dag(self, config: Dict[str, Any]) -> DAG:
        """Generate a single DAG from configuration."""
        blueprint_name = config['blueprint']
        blueprint_cls = self.registry.get_blueprint(blueprint_name)
        
        # Create blueprint instance
        blueprint_instance = blueprint_cls()
        
        # Generate DAG
        dag = blueprint_instance.render(config)
        
        # Validate generated DAG
        self._validate_generated_dag(dag, config)
        
        return dag
    
    def _validate_generated_dag(self, dag: DAG, config: Dict[str, Any]) -> None:
        """Validate that generated DAG meets basic requirements."""
        if not dag:
            raise ValueError("Blueprint render() method returned None")
        
        if not isinstance(dag, DAG):
            raise ValueError(f"Blueprint render() method returned {type(dag)}, expected DAG")
        
        if dag.dag_id != config['dag_id']:
            raise ValueError(f"DAG ID mismatch: expected {config['dag_id']}, got {dag.dag_id}")
        
        if not dag.tasks:
            raise ValueError("Generated DAG has no tasks")

# Auto-discovery integration for Airflow
def auto_generate_dags() -> Dict[str, DAG]:
    """Auto-generate all DAGs for Airflow discovery.
    
    This function is called by Airflow when it scans the dags/ directory.
    """
    registry.discover_blueprints()
    generator = DAGGenerator()
    return generator.discover_and_generate_dags()

# Make generated DAGs available to Airflow
_generated_dags = auto_generate_dags()
for dag_id, dag in _generated_dags.items():
    globals()[dag_id] = dag
```

### 4.2 Integration Module
**File:** `src/blueprint/__init__.py`

```python
"""Blueprint - Create reusable Airflow DAG templates."""

from .core import Blueprint
from .discovery import registry
from .config import ConfigParser
from .generator import DAGGenerator, auto_generate_dags
from .errors import BlueprintError, ValidationError, BlueprintNotFoundError

__version__ = "0.1.0"
__all__ = [
    'Blueprint',
    'registry', 
    'ConfigParser',
    'DAGGenerator',
    'auto_generate_dags',
    'BlueprintError',
    'ValidationError', 
    'BlueprintNotFoundError'
]

# Convenience function for DAG generation
def generate_dags():
    """Generate all DAGs from configurations."""
    return auto_generate_dags()
```

### 4.3 Airflow Integration File
**File:** `dags/blueprint_dags.py` (to be included in user projects)

```python
"""
Blueprint DAG Auto-Generator

This file automatically discovers and generates all DAGs from blueprint configurations.
Place this file in your dags/ directory to enable automatic DAG generation.
"""

from blueprint import auto_generate_dags

# Generate all DAGs from configs
_generated_dags = auto_generate_dags()

# Make DAGs available to Airflow
for dag_id, dag in _generated_dags.items():
    globals()[dag_id] = dag
```

**Key Features:**
- Automatic discovery of config files
- DAG generation with error handling
- Validation of generated DAGs
- Integration with Airflow's DAG discovery
- Error isolation (one bad config doesn't break others)

**Tests:** `tests/test_generator.py`
- Test DAG generation
- Test auto-discovery
- Test error handling
- Test Airflow integration

## Phase 5: Advanced Features & Polish (Weeks 9-10)

### 5.1 Type System Enhancement
**File:** `src/blueprint/types.py`

```python
import sys
from typing import get_type_hints, get_origin, get_args, Dict, Any, List
from typing_extensions import get_type_hints as get_type_hints_compat

if sys.version_info >= (3, 9):
    from typing import Annotated, get_type_hints
else:
    from typing_extensions import Annotated, get_type_hints

def extract_schema_from_typeddict(typeddict_class) -> Dict[str, Any]:
    """Extract schema information from a TypedDict class."""
    try:
        if sys.version_info >= (3, 9):
            hints = get_type_hints(typeddict_class, include_extras=True)
        else:
            hints = get_type_hints_compat(typeddict_class, include_extras=True)
    except Exception:
        hints = typeddict_class.__annotations__
    
    schema = {}
    for name, type_hint in hints.items():
        schema[name] = {
            'type': _format_type(type_hint),
            'required': name in getattr(typeddict_class, '__required_keys__', set()),
            'description': _extract_description(type_hint)
        }
    
    return schema

def _format_type(type_hint) -> str:
    """Format type hint for display."""
    if get_origin(type_hint) is Annotated:
        # Extract the actual type from Annotated
        return _format_type(get_args(type_hint)[0])
    
    origin = get_origin(type_hint)
    if origin is None:
        return getattr(type_hint, '__name__', str(type_hint))
    
    args = get_args(type_hint)
    if origin is list:
        return f"List[{_format_type(args[0]) if args else 'Any'}]"
    elif origin is dict:
        return f"Dict[{_format_type(args[0]) if args else 'Any'}, {_format_type(args[1]) if len(args) > 1 else 'Any'}]"
    elif origin is Union:
        return " | ".join(_format_type(arg) for arg in args)
    
    return str(type_hint)

def _extract_description(type_hint) -> str:
    """Extract description from Annotated type."""
    if get_origin(type_hint) is Annotated:
        args = get_args(type_hint)
        if len(args) > 1 and isinstance(args[1], str):
            return args[1]
    return ""
```

### 5.2 Configuration Validation Enhancement
**File:** `src/blueprint/validation.py`

```python
from typing import Any, Dict, List, Union, Type
import re
from datetime import datetime
from .errors import ValidationError

class ConfigValidator:
    """Advanced configuration validation."""
    
    @staticmethod
    def validate_cron_expression(value: str) -> bool:
        """Validate cron expression or Airflow preset."""
        # Airflow presets
        presets = {
            '@once', '@hourly', '@daily', '@weekly', 
            '@monthly', '@yearly', '@none'
        }
        
        if value in presets:
            return True
        
        # Basic cron validation (can be enhanced)
        cron_pattern = r'^(\*|[0-5]?[0-9]|\*/[0-9]+) (\*|[01]?[0-9]|2[0-3]|\*/[0-9]+) (\*|[12]?[0-9]|3[01]|\*/[0-9]+) (\*|[1-9]|1[0-2]|\*/[0-9]+) (\*|[0-6]|\*/[0-9]+)$'
        return bool(re.match(cron_pattern, value))
    
    @staticmethod
    def validate_python_identifier(value: str) -> bool:
        """Validate Python identifier (for DAG IDs, task IDs)."""
        return value.isidentifier()
    
    @staticmethod
    def validate_airflow_connection_id(value: str) -> bool:
        """Validate Airflow connection ID format."""
        # Connection IDs should be valid Python identifiers
        return ConfigValidator.validate_python_identifier(value)
    
    @staticmethod
    def validate_email(value: str) -> bool:
        """Basic email validation."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, value))

def add_validation_rules():
    """Add common validation rules to blueprint parameters."""
    # This could be implemented as decorators or metadata
    pass
```

### 5.3 Plugin System
**File:** `src/blueprint/plugins.py`

```python
from typing import Dict, Any, Callable, List
from .core import Blueprint

class BlueprintPlugin:
    """Base class for blueprint plugins."""
    
    def pre_render(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Modify config before rendering."""
        return config
    
    def post_render(self, dag, config: Dict[str, Any]):
        """Modify DAG after rendering."""
        return dag

class PluginManager:
    """Manage blueprint plugins."""
    
    def __init__(self):
        self._plugins: List[BlueprintPlugin] = []
    
    def register_plugin(self, plugin: BlueprintPlugin):
        """Register a plugin."""
        self._plugins.append(plugin)
    
    def apply_pre_render_plugins(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all pre-render plugins."""
        for plugin in self._plugins:
            config = plugin.pre_render(config)
        return config
    
    def apply_post_render_plugins(self, dag, config: Dict[str, Any]):
        """Apply all post-render plugins."""
        for plugin in self._plugins:
            dag = plugin.post_render(dag, config)
        return dag

# Global plugin manager
plugin_manager = PluginManager()

# Example plugins
class TaggingPlugin(BlueprintPlugin):
    """Add tags to DAGs based on config."""
    
    def post_render(self, dag, config):
        tags = config.get('tags', [])
        tags.append(f"blueprint:{config['blueprint']}")
        dag.tags = list(set(tags))
        return dag

class OwnershipPlugin(BlueprintPlugin):
    """Ensure ownership information is set."""
    
    def pre_render(self, config):
        if 'owner' not in config:
            config['owner'] = 'data-team'
        return config
```

## Phase 6: Testing, Documentation & Release (Weeks 11-12)

### 6.1 Comprehensive Test Suite

**Test Structure:**
```
tests/
├── conftest.py              # Pytest fixtures
├── test_core.py             # Blueprint base class tests
├── test_discovery.py        # Blueprint discovery tests  
├── test_config.py           # Configuration parsing tests
├── test_validation.py       # Validation system tests
├── test_errors.py           # Error handling tests
├── test_cli.py              # CLI command tests
├── test_scaffold.py         # Scaffolding tests
├── test_generator.py        # DAG generation tests
├── test_integration.py      # End-to-end integration tests
├── fixtures/                # Test fixtures
│   ├── blueprints/          # Sample blueprint files
│   ├── configs/             # Sample config files
│   └── dags/                # Expected DAG outputs
└── performance/             # Performance tests
    └── test_large_scale.py   # Large-scale scenario tests
```

**Key Test Categories:**
- Unit tests for all core components
- Integration tests for CLI workflows
- End-to-end tests with real Airflow DAGs
- Performance tests with large numbers of configs
- Error handling and edge case tests

### 6.2 Documentation Completion

**Documentation Structure:**
```
docs/
├── index.md                 # Main documentation homepage
├── quickstart.md            # Getting started guide
├── user-guide/              # User documentation
│   ├── creating-blueprints.md
│   ├── configuring-dags.md
│   ├── cli-reference.md
│   └── troubleshooting.md
├── developer-guide/         # Developer documentation
│   ├── architecture.md
│   ├── contributing.md
│   ├── plugin-development.md
│   └── api-reference.md
├── examples/                # Example blueprints and configs
│   ├── data-pipelines/
│   ├── ml-workflows/
│   └── monitoring/
└── migration/               # Migration guides
    └── from-dag-factory.md
```

### 6.3 Release Preparation

**Packaging and Distribution:**
- Finalize pyproject.toml with all dependencies
- Create GitHub Actions for CI/CD
- Set up PyPI publishing workflow
- Create release documentation
- Tag initial release (v0.1.0)

**Quality Assurance:**
- Code coverage > 90%
- Documentation coverage for all public APIs
- Performance benchmarks
- Security review
- Compatibility testing across Python 3.8-3.11

## Success Metrics

### Technical Metrics
- **Test Coverage:** >90% line coverage
- **Performance:** Handle 1000+ DAG configs in <10 seconds
- **Memory Usage:** <100MB memory overhead per 100 DAGs
- **CLI Response Time:** <2 seconds for interactive commands

### User Experience Metrics
- **Onboarding Time:** New users can create first DAG in <5 minutes
- **Error Resolution:** Clear error messages with actionable suggestions
- **Configuration Complexity:** 80% reduction in lines of code vs. raw Airflow

### Adoption Metrics
- **Blueprint Library:** 10+ community-contributed blueprints within 6 months
- **User Feedback:** >4.5/5 stars on PyPI within first quarter
- **Integration:** Seamless integration with existing Airflow deployments

## Risk Mitigation

### Technical Risks
1. **Airflow Compatibility:** Test against multiple Airflow versions (2.5+)
2. **Performance:** Profile and optimize DAG generation for large scales
3. **Type System:** Ensure compatibility across Python versions

### Adoption Risks
1. **Learning Curve:** Comprehensive documentation and examples
2. **Migration Path:** Clear migration guide from existing solutions
3. **Community Support:** Active community engagement and support

### Maintenance Risks
1. **Dependency Management:** Pin critical dependencies, regular updates
2. **Breaking Changes:** Semantic versioning and deprecation warnings
3. **Support Burden:** Clear contribution guidelines and issue templates

## Post-Release Roadmap

### Short Term (3 months)
- Community feedback integration
- Additional blueprint examples
- Performance optimizations
- Bug fixes and stability improvements

### Medium Term (6 months) 
- Web UI for blueprint management
- Advanced validation rules
- Plugin ecosystem development
- Integration with Airflow UI

### Long Term (12 months)
- Blueprint marketplace/registry
- Advanced templating features
- Multi-environment deployment support
- Enterprise features (RBAC, audit logs)

This implementation plan provides a comprehensive roadmap for building Blueprint from the ground up, with clear phases, deliverables, and success metrics. Each phase builds upon the previous one, ensuring a solid foundation while progressively adding advanced features.