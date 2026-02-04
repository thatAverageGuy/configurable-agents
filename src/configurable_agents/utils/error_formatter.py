"""Error formatting utilities with actionable resolution steps.

Provides structured error contexts with descriptions, resolution steps,
and technical details for common error scenarios.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class ErrorContext:
    """Structured error context with actionable resolution.

    Attributes:
        title: Short error title
        description: Human-readable error description
        resolution_steps: List of steps to resolve the error
        technical_details: Optional technical details (stack traces, file paths)
        error_type: Type of error for categorization
    """

    title: str
    description: str
    resolution_steps: List[str]
    technical_details: Optional[str] = None
    error_type: str = "general"


# Common error patterns with pre-defined resolution steps
COMMON_ERRORS: Dict[str, ErrorContext] = {
    "port_in_use": ErrorContext(
        title="Port Already in Use",
        description="The specified port is already in use by another application.",
        resolution_steps=[
            "Stop the application using this port",
            "Or use a different port via --port flag",
            "On Windows: Run `netstat -ano | findstr :PORT` to find the process",
            "On Linux/macOS: Run `lsof -i :PORT` to find the process",
            "Kill the process with `taskkill /PID <pid> /F` (Windows) or `kill <pid>` (Unix)",
        ],
        error_type="network",
    ),
    "permission_denied": ErrorContext(
        title="Permission Denied",
        description="The application does not have permission to access the specified resource.",
        resolution_steps=[
            "Check file/directory permissions",
            "Ensure the database directory is writable",
            "Try running with elevated privileges if needed",
            "Set AGENTS_DB_PATH to a writable location",
        ],
        error_type="filesystem",
    ),
    "disk_full": ErrorContext(
        title="Disk Full",
        description="No disk space available to write to the database.",
        resolution_steps=[
            "Free up disk space",
            "Clear old workflow runs or logs",
            "Change database location via AGENTS_DB_PATH",
        ],
        error_type="filesystem",
    ),
    "database_locked": ErrorContext(
        title="Database Locked",
        description="The database is locked by another process.",
        resolution_steps=[
            "Ensure only one instance is running",
            "Close any other applications using the database",
            "If the issue persists, restart the application",
        ],
        error_type="database",
    ),
    "module_not_found": ErrorContext(
        title="Missing Dependency",
        description="A required Python module is not installed.",
        resolution_steps=[
            "Install missing dependencies: pip install -e .",
            "Ensure virtual environment is activated",
            "Check requirements.txt for all dependencies",
        ],
        error_type="dependency",
    ),
    "invalid_config": ErrorContext(
        title="Invalid Configuration",
        description="The workflow configuration file is invalid.",
        resolution_steps=[
            "Validate config with: configurable-agents validate <config.yaml>",
            "Check YAML syntax (indentation, colons)",
            "Verify all required fields are present",
            "See docs for config schema reference",
        ],
        error_type="configuration",
    ),
}


def get_error_context(error: Exception) -> ErrorContext:
    """Get ErrorContext for an exception.

    Args:
        error: The exception to format

    Returns:
        ErrorContext with title, description, and resolution steps
    """
    error_str = str(error).lower()

    # Match against common error patterns
    if "port" in error_str and ("use" in error_str or "occupied" in error_str or "already" in error_str):
        return COMMON_ERRORS["port_in_use"]
    elif "permission" in error_str or "denied" in error_str or "access" in error_str:
        return COMMON_ERRORS["permission_denied"]
    elif "disk" in error_str or "space" in error_str or "no space" in error_str:
        return COMMON_ERRORS["disk_full"]
    elif "locked" in error_str or "database is locked" in error_str:
        return COMMON_ERRORS["database_locked"]
    elif "module" in error_str and "not found" in error_str:
        return COMMON_ERRORS["module_not_found"]
    elif "config" in error_str or "validation" in error_str or "invalid" in error_str:
        return COMMON_ERRORS["invalid_config"]

    # Generic error context
    return ErrorContext(
        title=error.__class__.__name__,
        description=str(error) or "An unexpected error occurred.",
        resolution_steps=[
            "Check the error details below",
            "Review logs for more information",
            "Try again with --verbose flag for more details",
        ],
        error_type="general",
    )


def format_error_for_cli(error: Exception, verbose: bool = False) -> str:
    """Format error for CLI output with colors and resolution steps.

    Args:
        error: The exception to format
        verbose: Include technical details if True

    Returns:
        Formatted error string with ANSI colors
    """
    ctx = get_error_context(error)

    lines = [
        f"\033[91m\033[1mError: {ctx.title}\033[0m",  # Red bold title
        f"\033[90m{ctx.description}\033[0m",  # Gray description
        "",
        "\033[93mHow to fix:\033[0m",  # Yellow "How to fix:"
    ]

    for i, step in enumerate(ctx.resolution_steps, 1):
        lines.append(f"  {i}. {step}")

    if verbose and ctx.technical_details:
        lines.extend([
            "",
            "\033[90mTechnical details:\033[0m",
            f"\033[90m{ctx.technical_details}\033[0m",
        ])

    return "\n".join(lines)


def format_error_for_html(error: Exception, verbose: bool = False) -> dict:
    """Format error for HTML rendering.

    Args:
        error: The exception to format
        verbose: Include technical details if True

    Returns:
        Dictionary with error context for template rendering
    """
    ctx = get_error_context(error)

    return {
        "title": ctx.title,
        "description": ctx.description,
        "resolution_steps": ctx.resolution_steps,
        "technical_details": ctx.technical_details if verbose else None,
        "error_type": ctx.error_type,
    }
