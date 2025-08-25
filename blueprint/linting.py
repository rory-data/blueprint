"""Linting utilities for Blueprint-generated DAG files."""

import logging
import subprocess
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def lint_dag_file(file_path: Union[str, Path], fix: bool = True, format_code: bool = True) -> bool:
    """Lint a DAG file using Ruff.
    
    Args:
        file_path: Path to the DAG file to lint
        fix: Whether to automatically fix linting issues
        format_code: Whether to format the code using ruff format
        
    Returns:
        True if linting passed (no issues or all issues fixed), False otherwise
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.error("DAG file does not exist: %s", file_path)
        return False
    
    success = True
    
    try:
        # Run ruff check
        check_cmd = ["ruff", "check", str(file_path)]
        if fix:
            check_cmd.append("--fix")
            
        logger.info("Running: %s", " ".join(check_cmd))
        result = subprocess.run(
            check_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode != 0:
            logger.warning("Ruff check issues found for %s:\n%s", file_path, result.stdout)
            if not fix:
                success = False
        else:
            logger.info("✅ Ruff check passed for %s", file_path)
            
        # Run ruff format if requested
        if format_code:
            format_cmd = ["ruff", "format", str(file_path)]
            logger.info("Running: %s", " ".join(format_cmd))
            
            result = subprocess.run(
                format_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                logger.error("Ruff format failed for %s:\n%s", file_path, result.stderr)
                success = False
            else:
                logger.info("✅ Ruff format completed for %s", file_path)
                
    except subprocess.TimeoutExpired:
        logger.error("Timeout running ruff on %s", file_path)
        success = False
    except FileNotFoundError:
        logger.error("Ruff not found. Please install ruff: pip install ruff")
        success = False
    except Exception as e:
        logger.error("Error running ruff on %s: %s", file_path, e)
        success = False
        
    return success


def lint_directory(directory: Union[str, Path], pattern: str = "*.py", 
                  fix: bool = True, format_code: bool = True) -> tuple[int, int]:
    """Lint all Python files in a directory.
    
    Args:
        directory: Directory to search for Python files
        pattern: File pattern to match (default: "*.py")
        fix: Whether to automatically fix linting issues
        format_code: Whether to format the code using ruff format
        
    Returns:
        Tuple of (successful_files, total_files)
    """
    directory = Path(directory)
    
    if not directory.exists() or not directory.is_dir():
        logger.error("Directory does not exist: %s", directory)
        return 0, 0
        
    python_files = list(directory.rglob(pattern))
    if not python_files:
        logger.warning("No Python files found in %s", directory)
        return 0, 0
        
    successful_files = 0
    
    for file_path in python_files:
        logger.info("Linting %s", file_path)
        if lint_dag_file(file_path, fix=fix, format_code=format_code):
            successful_files += 1
            
    logger.info("Linted %d/%d files successfully", successful_files, len(python_files))
    return successful_files, len(python_files)