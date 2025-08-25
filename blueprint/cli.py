"""Simplified Blueprint CLI for build-time DAG generation."""

import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from blueprint import discover_blueprints, get_blueprint_info
from blueprint.linting import lint_dag_file, lint_directory
from blueprint.utils import get_template_path

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(package_name="airflow-blueprint")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool):
    """Blueprint - Build-time Airflow DAG generation from *.py.j2 templates.

    Generate DAG files from Jinja2 templates with type-safe configurations.
    """
    if verbose:
        logging.basicConfig(level=logging.INFO)


@cli.command("list")
@click.option("--template-dir", default=None, help="Template directory path")
def list_blueprints(template_dir: Optional[str]):
    """List available blueprint templates."""
    template_dir_path = get_template_path(template_dir)
    blueprints = discover_blueprints(template_dir_path)

    if not blueprints:
        console.print(f"[red]No blueprints found in {template_dir_path}[/red]")
        return

    table = Table(title="Available Blueprint Templates")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="magenta")
    table.add_column("Template File", style="green")

    for blueprint in blueprints:
        template_file = f"{blueprint['name']}.py.j2"
        table.add_row(
            blueprint["name"],
            blueprint.get("description", "No description available"),
            template_file,
        )

    console.print(table)


@cli.command()
@click.argument("blueprint_name")
@click.option("--template-dir", default=None, help="Template directory path")
def describe(blueprint_name: str, template_dir: Optional[str]):
    """Show blueprint configuration schema and documentation."""
    template_dir_path = get_template_path(template_dir)

    try:
        info = get_blueprint_info(blueprint_name, template_dir_path)
    except Exception as e:
        console.print(f"[red]Error loading blueprint '{blueprint_name}': {e}[/red]")
        sys.exit(1)

    console.print(f"[bold cyan]Blueprint: {blueprint_name}[/bold cyan]\n")

    if info.get("description"):
        console.print(f"[bold]Description:[/bold] {info['description']}\n")

    # Show configuration schema
    schema = info.get("schema", {})
    if schema and "properties" in schema:
        table = Table(title="Configuration Parameters")
        table.add_column("Parameter", style="cyan", no_wrap=True)
        table.add_column("Type", style="yellow")
        table.add_column("Required", style="magenta")
        table.add_column("Description", style="green")

        required_fields = set(schema.get("required", []))

        for param_name, param_info in schema["properties"].items():
            param_type = param_info.get("type", "unknown")
            is_required = "Yes" if param_name in required_fields else "No"
            description = param_info.get("description", "No description")

            table.add_row(param_name, param_type, is_required, description)

        console.print(table)

    # Show template file location
    template_file = Path(template_dir_path) / f"{blueprint_name}.py.j2"
    if template_file.exists():
        console.print(f"\n[bold]Template File:[/bold] {template_file}")
    else:
        console.print(f"\n[red]Template file not found: {template_file}[/red]")


@cli.command()
@click.argument("blueprint_name")
@click.argument("output_file")
@click.option("--template-dir", default=None, help="Template directory path")
@click.option("--config", "-c", multiple=True, help="Configuration parameter (key=value)")
@click.option("--lint/--no-lint", default=True, help="Lint generated DAG file")
def generate(
    blueprint_name: str,
    output_file: str,
    template_dir: Optional[str],
    config: List[str],
    lint: bool,
):
    """Generate a DAG file from a blueprint template.

    Example:
        blueprint generate daily_etl customer_etl.py -c job_id=customer-etl -c source_table=raw.customers
    """
    template_dir_path = get_template_path(template_dir)

    try:
        # Load blueprint
        from blueprint import load_blueprint

        blueprint_class = load_blueprint(blueprint_name, template_dir_path)

        # Parse configuration parameters
        config_dict = {}
        for param in config:
            if "=" not in param:
                console.print(f"[red]Invalid config format: {param}. Use key=value[/red]")
                sys.exit(1)
            key, value = param.split("=", 1)
            config_dict[key] = value

        if not config_dict:
            console.print("[red]No configuration provided. Use -c key=value[/red]")
            sys.exit(1)

        # Generate DAG file
        console.print(f"Generating DAG from blueprint '{blueprint_name}'...")
        template_code = blueprint_class.build_template(
            output_file=output_file, lint=lint, **config_dict
        )

        console.print(f"✅ Generated DAG file: {output_file}")

        if lint:
            console.print("✅ DAG file linted and formatted with Ruff")

    except Exception as e:
        console.print(f"[red]Error generating DAG: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("file_or_dir", type=click.Path(exists=True))
@click.option("--fix/--no-fix", default=True, help="Automatically fix linting issues")
@click.option("--format/--no-format", default=True, help="Format code with ruff format")
def lint(file_or_dir: str, fix: bool, format: bool):  # noqa: A002
    """Lint DAG files with Ruff.

    FILE_OR_DIR can be a single Python file or a directory to lint recursively.
    """
    path = Path(file_or_dir)

    if path.is_file():
        console.print(f"Linting file: {path}")
        success = lint_dag_file(path, fix=fix, format_code=format)
        if success:
            console.print("✅ Linting completed successfully")
        else:
            console.print("[red]❌ Linting failed[/red]")
            sys.exit(1)
    elif path.is_dir():
        console.print(f"Linting directory: {path}")
        successful, total = lint_directory(path, fix=fix, format_code=format)
        if successful == total:
            console.print(f"✅ All {total} files linted successfully")
        else:
            console.print(f"[red]❌ {total - successful}/{total} files failed linting[/red]")
            sys.exit(1)
    else:
        console.print(f"[red]Invalid path: {path}[/red]")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()