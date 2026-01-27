"""
Command-line interface for configurable-agents.

Provides commands for running and validating workflow configurations.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from configurable_agents.runtime import (
    ConfigLoadError,
    ConfigValidationError,
    ExecutionError,
    GraphBuildError,
    StateInitializationError,
    WorkflowExecutionError,
    run_workflow,
    validate_workflow,
)

# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for pretty terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


def supports_unicode() -> bool:
    """Check if terminal supports Unicode output."""
    try:
        # Try encoding a Unicode character
        "\u2713".encode(sys.stdout.encoding or "utf-8")
        return True
    except (UnicodeEncodeError, AttributeError):
        return False


# Use Unicode symbols if supported, otherwise ASCII fallbacks
_UNICODE_SUPPORTED = supports_unicode()
_CHECK = "\u2713" if _UNICODE_SUPPORTED else "+"  # ✓ or +
_CROSS = "\u2717" if _UNICODE_SUPPORTED else "x"  # ✗ or x
_INFO = "\u2139" if _UNICODE_SUPPORTED else "i"  # ℹ or i
_WARNING = "\u26a0" if _UNICODE_SUPPORTED else "!"  # ⚠ or !


def colorize(text: str, color: str) -> str:
    """Add color to text if stdout is a TTY."""
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.RESET}"
    return text


def print_success(message: str) -> None:
    """Print success message in green."""
    print(f"{colorize(_CHECK, Colors.GREEN)} {message}")


def print_error(message: str) -> None:
    """Print error message in red."""
    print(f"{colorize(_CROSS, Colors.RED)} {message}", file=sys.stderr)


def print_info(message: str) -> None:
    """Print info message in blue."""
    print(f"{colorize(_INFO, Colors.BLUE)} {message}")


def print_warning(message: str) -> None:
    """Print warning message in yellow."""
    print(f"{colorize(_WARNING, Colors.YELLOW)} {message}")


def parse_input_args(input_args: list[str]) -> Dict[str, Any]:
    """
    Parse --input arguments in key=value format.

    Args:
        input_args: List of "key=value" strings

    Returns:
        Dictionary of parsed inputs

    Raises:
        ValueError: If input format is invalid

    Example:
        >>> parse_input_args(["topic=AI Safety", "count=5", "enabled=true"])
        {"topic": "AI Safety", "count": 5, "enabled": True}
    """
    inputs = {}

    for arg in input_args:
        if "=" not in arg:
            raise ValueError(
                f"Invalid input format: '{arg}'\n"
                f"Expected format: key=value (e.g., topic='AI Safety')"
            )

        key, value = arg.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Try to parse as JSON to handle types (int, bool, list, dict)
        try:
            # Handle string values (strip quotes if present)
            if (value.startswith("'") and value.endswith("'")) or (
                value.startswith('"') and value.endswith('"')
            ):
                inputs[key] = value[1:-1]
            else:
                # Try JSON parsing for numbers, booleans, lists, dicts
                inputs[key] = json.loads(value)
        except json.JSONDecodeError:
            # If JSON parsing fails, treat as string
            inputs[key] = value

    return inputs


def cmd_run(args: argparse.Namespace) -> int:
    """
    Execute workflow from config file.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    config_path = args.config_file

    # Validate file exists
    if not Path(config_path).exists():
        print_error(f"Config file not found: {config_path}")
        return 1

    # Parse inputs
    try:
        inputs = parse_input_args(args.input) if args.input else {}
    except ValueError as e:
        print_error(f"Invalid input format: {e}")
        return 1

    # Print execution info
    print_info(f"Loading workflow: {colorize(config_path, Colors.CYAN)}")
    if inputs:
        print_info(f"Inputs: {colorize(json.dumps(inputs, indent=2), Colors.GRAY)}")

    # Execute workflow
    try:
        result = run_workflow(config_path, inputs, verbose=args.verbose)

        # Print success
        print_success("Workflow executed successfully!")

        # Print results
        print(f"\n{colorize('Results:', Colors.BOLD)}")
        print(json.dumps(result, indent=2))

        return 0

    except ConfigLoadError as e:
        print_error(f"Failed to load config: {e}")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1

    except ConfigValidationError as e:
        print_error(f"Config validation failed: {e}")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1

    except StateInitializationError as e:
        print_error(f"Invalid inputs: {e}")
        print_warning("Check that all required state fields are provided")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1

    except GraphBuildError as e:
        print_error(f"Failed to build workflow graph: {e}")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1

    except WorkflowExecutionError as e:
        print_error(f"Workflow execution failed: {e}")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1

    except ExecutionError as e:
        print_error(f"Execution error: {e}")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """
    Validate workflow config without executing.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    config_path = args.config_file

    # Validate file exists
    if not Path(config_path).exists():
        print_error(f"Config file not found: {config_path}")
        return 1

    # Print validation info
    print_info(f"Validating workflow: {colorize(config_path, Colors.CYAN)}")

    # Validate config
    try:
        validate_workflow(config_path)

        # Print success
        print_success("Config is valid!")
        return 0

    except ConfigLoadError as e:
        print_error(f"Failed to load config: {e}")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1

    except ConfigValidationError as e:
        print_error(f"Config validation failed: {e}")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """
    Create CLI argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="configurable-agents",
        description="Config-driven LLM agent workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a workflow with inputs
  configurable-agents run workflow.yaml --input topic="AI Safety" --input count=5

  # Validate a config without running
  configurable-agents validate workflow.yaml

  # Run with verbose logging
  configurable-agents run workflow.yaml --input name="Alice" --verbose

For more information, visit: https://github.com/yourusername/configurable-agents
        """,
    )

    parser.add_argument(
        "--version", action="version", version="configurable-agents 0.1.0-dev"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser(
        "run", help="Execute workflow from config file", description="Execute a workflow"
    )
    run_parser.add_argument("config_file", help="Path to workflow config file (YAML/JSON)")
    run_parser.add_argument(
        "-i",
        "--input",
        action="append",
        help="Workflow inputs in key=value format (can be used multiple times)",
    )
    run_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging (DEBUG level)"
    )
    run_parser.set_defaults(func=cmd_run)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate config without executing",
        description="Validate a workflow configuration",
    )
    validate_parser.add_argument(
        "config_file", help="Path to workflow config file (YAML/JSON)"
    )
    validate_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    validate_parser.set_defaults(func=cmd_validate)

    return parser


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Show help if no command provided
    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
