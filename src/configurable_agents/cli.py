"""
Command-line interface for configurable-agents.

Provides commands for running and validating workflow configurations.
Also provides observability commands for cost and profiling reports.
"""

import argparse
import json
import logging
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from configurable_agents.deploy import generate_deployment_artifacts
from configurable_agents.observability import (
    CostReporter,
    get_date_range_filter,
)
from configurable_agents.observability.multi_provider_tracker import (
    generate_cost_report,
)
from configurable_agents.registry import AgentRegistryServer
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
from configurable_agents.ui.dashboard import create_dashboard_app

# Rich library for formatted tables
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Table = None
    Panel = None

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
_BULLET = "\u2022" if _UNICODE_SUPPORTED else "*"  # • or *


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


def is_port_in_use(port: int) -> bool:
    """
    Check if TCP port is already in use on localhost.

    Args:
        port: Port number to check

    Returns:
        True if port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


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

    # Set profiling flag via environment variable
    if args.enable_profiling:
        os.environ["CONFIGURABLE_AGENTS_PROFILING"] = "1"
        print_info(f"Profiling enabled for this run")

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


def cmd_deploy(args: argparse.Namespace) -> int:
    """
    Deploy workflow as Docker container.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    config_path = args.config_file

    # Step 1: Validate config file exists and is valid
    if not Path(config_path).exists():
        print_error(f"Config file not found: {config_path}")
        return 1

    print_info(f"Validating workflow config: {colorize(config_path, Colors.CYAN)}")

    try:
        validate_workflow(config_path)
        print_success("Config validation passed")
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

    # Step 2: Check Docker installed and running
    print_info("Checking Docker availability...")
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print_error("Docker daemon is not running")
            print_info("Please start Docker Desktop or the Docker daemon")
            return 1
        print_success("Docker is available")
    except FileNotFoundError:
        print_error("Docker is not installed")
        print_info("Install Docker from: https://docs.docker.com/get-docker/")
        return 1
    except subprocess.TimeoutExpired:
        print_error("Docker command timed out")
        print_info("Please check if Docker is responding")
        return 1

    # Step 3: Generate deployment artifacts
    output_dir = Path(args.output_dir)
    print_info(f"Generating deployment artifacts in: {colorize(str(output_dir), Colors.CYAN)}")

    # Load config to get workflow name if --name not provided
    from configurable_agents.config import parse_config_file, WorkflowConfig
    try:
        config_dict = parse_config_file(config_path)
        workflow_config = WorkflowConfig(**config_dict)
        workflow_name = workflow_config.flow.name
    except Exception as e:
        print_error(f"Failed to load workflow config: {e}")
        if args.verbose:
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
        return 1

    # Sanitize container name
    container_name = args.name or workflow_name
    # Convert to lowercase and replace invalid characters with dash
    container_name = "".join(
        c if c.isalnum() or c in ("-", "_") else "-"
        for c in container_name.lower()
    )

    # Determine MLFlow settings
    mlflow_port = 0 if args.no_mlflow else args.mlflow_port
    enable_mlflow = not args.no_mlflow

    try:
        artifacts = generate_deployment_artifacts(
            config_path=config_path,
            output_dir=output_dir,
            api_port=args.api_port,
            mlflow_port=mlflow_port,
            sync_timeout=args.timeout,
            enable_mlflow=enable_mlflow,
            container_name=container_name,
        )

        print_success(f"Generated {len(artifacts)} deployment artifacts:")
        for artifact_name, artifact_path in artifacts.items():
            print(f"  {colorize(artifact_name, Colors.GRAY)}: {artifact_path}")

    except Exception as e:
        print_error(f"Failed to generate artifacts: {e}")
        if args.verbose:
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
        return 1

    # Step 4: Exit early if --generate flag
    if args.generate:
        print_info("Artifacts generated. Skipping Docker build and run.")
        print_info(f"To build manually, run: docker build -t {container_name}:latest {output_dir}")
        return 0

    # Step 5: Check port availability
    print_info("Checking port availability...")

    if is_port_in_use(args.api_port):
        print_error(f"Port {args.api_port} is already in use")
        print_info(f"Try a different port with: --api-port <port>")
        return 1

    if enable_mlflow and mlflow_port > 0 and is_port_in_use(mlflow_port):
        print_error(f"Port {mlflow_port} is already in use")
        print_info(f"Try a different port with: --mlflow-port <port> or disable with --no-mlflow")
        return 1

    print_success("Ports are available")

    # Step 6: Handle environment file
    env_file_path = Path(args.env_file)
    env_file_args = []

    if args.no_env_file:
        print_warning("Environment file disabled. Configure environment manually if needed.")
    else:
        if not env_file_path.exists():
            if args.env_file == ".env":
                # Default .env doesn't exist - just warn
                print_warning(f"Default .env file not found. Container will use environment defaults.")
                env_example = Path(output_dir) / '.env.example'
                print_info(f"Copy {env_example} to .env to customize environment")
            else:
                # Custom env file specified but doesn't exist - fail
                print_error(f"Environment file not found: {env_file_path}")
                return 1
        else:
            # Env file exists - validate format and use it
            try:
                # Basic validation: check for suspicious content
                content = env_file_path.read_text()
                if not content.strip():
                    print_warning(f"Environment file {env_file_path} is empty")
                else:
                    # Check for basic format issues
                    for line_num, line in enumerate(content.split('\n'), 1):
                        line = line.strip()
                        if line and not line.startswith('#') and '=' not in line:
                            print_warning(f"Line {line_num} in {env_file_path} may be malformed: {line}")

                env_file_args = ["--env-file", str(env_file_path)]
                print_success(f"Using environment file: {env_file_path}")
            except Exception as e:
                print_warning(f"Could not validate environment file: {e}")
                # Still use it - Docker will validate
                env_file_args = ["--env-file", str(env_file_path)]

    # Step 7: Build Docker image
    print_info(f"Building Docker image: {colorize(f'{container_name}:latest', Colors.CYAN)}")

    build_start = time.time()
    try:
        result = subprocess.run(
            ["docker", "build", "-t", f"{container_name}:latest", str(output_dir)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )

        if result.returncode != 0:
            print_error("Docker build failed")
            print(result.stderr, file=sys.stderr)
            return 1

        build_time = time.time() - build_start
        print_success(f"Image built successfully in {build_time:.1f}s")

        # Get image size
        try:
            size_result = subprocess.run(
                ["docker", "images", container_name, "--format", "{{.Size}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if size_result.returncode == 0:
                image_size = size_result.stdout.strip()
                print_info(f"Image size: {colorize(image_size, Colors.GRAY)}")
        except Exception:
            pass  # Size check is optional

    except subprocess.TimeoutExpired:
        print_error("Docker build timed out after 5 minutes")
        return 1
    except Exception as e:
        print_error(f"Build failed: {e}")
        if args.verbose:
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
        return 1

    # Step 8: Run container (detached)
    print_info(f"Starting container: {colorize(container_name, Colors.CYAN)}")

    # Build docker run command
    port_args = ["-p", f"{args.api_port}:8000"]
    if enable_mlflow and mlflow_port > 0:
        port_args.extend(["-p", f"{mlflow_port}:5000"])

    docker_run_cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        *port_args,
        *env_file_args,
        f"{container_name}:latest"
    ]

    try:
        result = subprocess.run(
            docker_run_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            stderr = result.stderr.lower()
            if "conflict" in stderr or "already in use" in stderr:
                print_error(f"Container '{container_name}' already exists")
                print_info(f"Remove it with: docker rm -f {container_name}")
                return 1
            else:
                print_error("Failed to start container")
                print(result.stderr, file=sys.stderr)
                return 1

        container_id = result.stdout.strip()[:12]  # Short ID
        print_success(f"Container started: {colorize(container_id, Colors.GRAY)}")

    except subprocess.TimeoutExpired:
        print_error("Container start timed out")
        return 1
    except Exception as e:
        print_error(f"Failed to start container: {e}")
        if args.verbose:
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
        return 1

    # Step 9: Print success message with URLs and examples
    print()
    print(f"{colorize('=' * 60, Colors.GREEN)}")
    print(f"{colorize('Deployment successful!', Colors.BOLD + Colors.GREEN)}")
    print(f"{colorize('=' * 60, Colors.GREEN)}")
    print()
    print(f"{colorize('Endpoints:', Colors.BOLD)}")
    print(f"  API:          http://localhost:{args.api_port}/execute")
    print(f"  Docs:         http://localhost:{args.api_port}/docs")
    print(f"  Health:       http://localhost:{args.api_port}/health")
    if enable_mlflow and mlflow_port > 0:
        print(f"  MLFlow UI:    http://localhost:{mlflow_port}")
    print()
    print(f"{colorize('Example Usage:', Colors.BOLD)}")
    print(f"  curl -X POST http://localhost:{args.api_port}/execute \\")
    print(f"    -H 'Content-Type: application/json' \\")
    print(f"    -d '{{}}'")
    print()
    print(f"{colorize('Container Management:', Colors.BOLD)}")
    print(f"  View logs:    docker logs {container_name}")
    print(f"  Stop:         docker stop {container_name}")
    print(f"  Restart:      docker restart {container_name}")
    print(f"  Remove:       docker rm -f {container_name}")
    print()

    return 0


def cmd_report_costs(args: argparse.Namespace) -> int:
    """
    Generate cost reports from MLFlow tracking data.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Initialize cost reporter
        tracking_uri = args.tracking_uri
        reporter = CostReporter(tracking_uri=tracking_uri)

        print_info(f"Querying MLFlow: {colorize(tracking_uri, Colors.CYAN)}")

        # Parse date range
        start_date = None
        end_date = None

        if args.period:
            try:
                start_date, end_date = get_date_range_filter(args.period)
                print_info(
                    f"Period: {colorize(args.period, Colors.CYAN)} "
                    f"({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
                )
            except ValueError as e:
                print_error(f"Invalid period: {e}")
                return 1
        elif args.start_date or args.end_date:
            if args.start_date:
                from datetime import datetime

                start_date = datetime.fromisoformat(args.start_date)
            if args.end_date:
                from datetime import datetime

                end_date = datetime.fromisoformat(args.end_date)

        # Query cost entries
        entries = reporter.get_cost_entries(
            experiment_name=args.experiment,
            workflow_name=args.workflow,
            start_date=start_date,
            end_date=end_date,
            status_filter=args.status,
        )

        if not entries:
            print_warning("No cost entries found matching the filters")
            return 0

        print_success(f"Found {len(entries)} workflow runs")

        # Generate summary
        summary = reporter.generate_summary(entries)

        # Display summary
        print(f"\n{colorize('Cost Summary:', Colors.BOLD)}")
        print(f"  Total Cost:        ${summary.total_cost_usd:.6f}")
        print(f"  Total Runs:        {summary.total_runs}")
        print(f"  Successful:        {summary.successful_runs}")
        print(f"  Failed:            {summary.failed_runs}")
        print(f"  Total Tokens:      {summary.total_tokens:,}")
        print(f"  Avg Cost/Run:      ${summary.avg_cost_per_run:.6f}")
        print(f"  Avg Tokens/Run:    {summary.avg_tokens_per_run:.0f}")

        # Display breakdowns if requested
        if args.breakdown:
            if summary.breakdown_by_workflow:
                print(f"\n{colorize('Cost by Workflow:', Colors.BOLD)}")
                for workflow, cost in sorted(
                    summary.breakdown_by_workflow.items(), key=lambda x: x[1], reverse=True
                ):
                    print(f"  {workflow:<30} ${cost:.6f}")

            if summary.breakdown_by_model:
                print(f"\n{colorize('Cost by Model:', Colors.BOLD)}")
                for model, cost in sorted(
                    summary.breakdown_by_model.items(), key=lambda x: x[1], reverse=True
                ):
                    print(f"  {model:<30} ${cost:.6f}")

        # Aggregate by period if requested
        if args.aggregate_by:
            print(f"\n{colorize(f'Cost by {args.aggregate_by.capitalize()}:', Colors.BOLD)}")
            aggregated = reporter.aggregate_by_period(entries, period=args.aggregate_by)
            for period_key, cost in sorted(aggregated.items()):
                print(f"  {period_key:<15} ${cost:.6f}")

        # Export to file if requested
        if args.output:
            output_format = args.format.lower()
            if output_format == "json":
                reporter.export_to_json(
                    entries, args.output, include_summary=args.include_summary
                )
            elif output_format == "csv":
                reporter.export_to_csv(entries, args.output)
            else:
                print_error(f"Invalid format: {output_format}")
                return 1

            print_success(f"Exported to {args.output}")

        return 0

    except RuntimeError as e:
        print_error(f"MLFlow not available: {e}")
        print_info("Install MLFlow with: pip install mlflow")
        return 1

    except ValueError as e:
        print_error(f"Invalid input: {e}")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
        return 1


def cmd_cost_report(args: argparse.Namespace) -> int:
    """
    Generate unified cost report from MLFlow experiment data.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not RICH_AVAILABLE:
        print_error("Rich library is required for cost-report command")
        print_info("Install with: pip install rich>=13.0.0")
        return 1

    try:
        experiment_name = args.experiment
        mlflow_uri = args.mlflow_uri

        if not experiment_name:
            print_error("--experiment is required for cost-report")
            return 1

        # Generate cost report
        report = generate_cost_report(experiment_name, mlflow_uri=mlflow_uri)

        console = Console()

        # Display title
        console.print()
        title = Text(f"Cost Report: {experiment_name}", style="bold cyan")
        console.print(Panel(title, expand=False))
        console.print()

        # Create table for provider breakdown
        table = Table(title=None)
        table.add_column("Provider/Model", style="cyan", no_wrap=False)
        table.add_column("Tokens", justify="right", style="green")
        table.add_column("Cost USD", justify="right", style="yellow")
        table.add_column("Calls", justify="right", style="blue")

        # Find most expensive provider for highlighting
        most_expensive_key = None
        most_expensive_cost = 0.0
        provider_rows = []

        for provider, data in report.get("by_provider", {}).items():
            provider_cost = data.get("total_cost_usd", 0.0)
            provider_tokens = data.get("total_tokens", 0)
            provider_calls = data.get("run_count", 0)
            provider_models = data.get("models", {})

            # Track most expensive provider
            if provider_cost > most_expensive_cost:
                most_expensive_cost = provider_cost
                most_expensive_key = provider

            provider_rows.append((provider, provider_cost, provider_tokens, provider_calls, provider_models))

        # Sort by cost descending
        provider_rows.sort(key=lambda x: x[1], reverse=True)

        # Add rows to table
        for provider, cost, tokens, calls, models in provider_rows:
            # Show individual models if more than one
            if len(models) > 1:
                # Provider header row
                style = "bold yellow" if provider == most_expensive_key else ""
                table.add_row(
                    f"{provider}/",
                    f"{tokens:,}",
                    f"${cost:.6f}",
                    f"{calls}",
                    style=style
                )
                # Model sub-rows
                for model_name, model_data in models.items():
                    model_style = "dim" if provider != most_expensive_key else "yellow"
                    table.add_row(
                        f"  {model_name}",
                        f"{model_data['total_tokens']:,}",
                        f"${model_data['total_cost_usd']:.6f}",
                        f"{model_data['run_count']}",
                        style=model_style
                    )
            else:
                # Single model - show directly
                model_name = list(models.keys())[0] if models else "unknown"
                style = "bold yellow" if provider == most_expensive_key else ""
                table.add_row(
                    f"{provider}/{model_name}",
                    f"{tokens:,}",
                    f"${cost:.6f}",
                    f"{calls}",
                    style=style
                )

        # Add totals row
        total_cost = report.get("total_cost_usd", 0.0)
        total_tokens = report.get("total_tokens", 0)
        total_calls = sum(r[3] for r in provider_rows)

        table.add_row()
        table.add_row(
            "TOTAL",
            f"{total_tokens:,}",
            f"${total_cost:.6f}",
            f"{total_calls}",
            style="bold"
        )

        console.print(table)
        console.print()

        # Highlight most expensive provider
        if most_expensive_key:
            print_info(f"Most expensive provider: {colorize(most_expensive_key, Colors.BOLD + Colors.YELLOW)} (${most_expensive_cost:.6f})")

        return 0

    except RuntimeError as e:
        print_error(f"MLFlow not available: {e}")
        print_info("Install MLFlow with: pip install mlflow>=3.9.0")
        return 1

    except ValueError as e:
        print_error(f"Invalid input: {e}")
        if args.verbose:
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
        return 1

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
        return 1


def cmd_profile_report(args: argparse.Namespace) -> int:
    """
    Generate profiling report with bottleneck analysis.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not RICH_AVAILABLE:
        print_error("Rich library is required for profile-report command")
        print_info("Install with: pip install rich>=13.0.0")
        return 1

    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        mlflow_uri = args.mlflow_uri
        run_id = args.run_id

        # Set tracking URI if provided
        if mlflow_uri:
            mlflow.set_tracking_uri(mlflow_uri)

        client = MlflowClient()

        # Get the run
        if run_id:
            run = client.get_run(run_id)
        else:
            # Get latest run from default experiment
            from mlflow.entities import ViewType
            experiments = client.search_experiments(view_type=ViewType.ACTIVE_ONLY)
            if not experiments:
                print_error("No MLFlow experiments found")
                return 1

            # Use first experiment (usually Default)
            experiment_id = experiments[0].experiment_id
            runs = client.search_runs(
                experiment_ids=[experiment_id],
                order_by=["start_time DESC"],
                max_results=1
            )
            if not runs:
                print_error(f"No runs found in experiment: {experiments[0].name}")
                return 1

            run = runs[0]
            run_id = run.info.run_id

        console = Console()

        # Display title
        console.print()
        title = Text(f"Profile Report: {run_id[:8]}", style="bold cyan")
        console.print(Panel(title, expand=False))
        console.print()

        # Extract node timing metrics
        metrics = run.data.metrics
        node_timings = {}

        for metric_name, metric_value in metrics.items():
            if metric_name.startswith("node_") and metric_name.endswith("_duration_ms"):
                # Extract node_id from metric name
                # Format: node_{node_id}_duration_ms
                parts = metric_name.split("_")
                if len(parts) >= 3:
                    node_id = "_".join(parts[1:-2])  # Handle node_ids with underscores
                    if node_id not in node_timings:
                        node_timings[node_id] = {"duration_ms": 0.0, "cost_usd": 0.0, "calls": 0}
                    node_timings[node_id]["duration_ms"] = metric_value
                    node_timings[node_id]["calls"] = 1

            elif metric_name.startswith("node_") and metric_name.endswith("_cost_usd"):
                parts = metric_name.split("_")
                if len(parts) >= 3:
                    node_id = "_".join(parts[1:-2])
                    if node_id not in node_timings:
                        node_timings[node_id] = {"duration_ms": 0.0, "cost_usd": 0.0, "calls": 0}
                    node_timings[node_id]["cost_usd"] = metric_value

        if not node_timings:
            print_warning("No profiling data found for this run")
            print_info("Run with --enable-profiling flag to capture profiling data")
            return 0

        # Calculate totals
        total_duration = sum(t["duration_ms"] for t in node_timings.values())
        total_cost = sum(t["cost_usd"] for t in node_timings.values())
        total_calls = sum(t["calls"] for t in node_timings.values())

        # Find slowest node
        slowest_node = max(node_timings.items(), key=lambda x: x[1]["duration_ms"])
        slowest_node_id, slowest_data = slowest_node

        # Create table
        table = Table(title=None)
        table.add_column("Node ID", style="cyan", no_wrap=False)
        table.add_column("Avg Duration (ms)", justify="right", style="green")
        table.add_column("Total Duration (ms)", justify="right", style="green")
        table.add_column("Calls", justify="right", style="blue")
        table.add_column("% of Total", justify="right", style="yellow")
        table.add_column("Cost USD", justify="right", style="magenta")

        # Add rows sorted by total duration
        for node_id, timing_data in sorted(node_timings.items(), key=lambda x: x[1]["duration_ms"], reverse=True):
            duration_ms = timing_data["duration_ms"]
            cost_usd = timing_data["cost_usd"]
            calls = timing_data["calls"]
            avg_duration = duration_ms / calls if calls > 0 else 0
            percent_of_total = (duration_ms / total_duration * 100) if total_duration > 0 else 0

            # Highlight slowest node in bold red
            style = "bold red" if node_id == slowest_node_id else ""
            # Highlight bottlenecks (>50%) in yellow
            if percent_of_total > 50 and node_id != slowest_node_id:
                style = "bold yellow"

            table.add_row(
                node_id,
                f"{avg_duration:.1f}",
                f"{duration_ms:.1f}",
                f"{calls}",
                f"{percent_of_total:.1f}%",
                f"${cost_usd:.6f}" if cost_usd > 0 else "-",
                style=style
            )

        # Add totals row
        table.add_row()
        table.add_row(
            "TOTAL",
            "-",
            f"{total_duration:.1f}",
            f"{total_calls}",
            "100.0%",
            f"${total_cost:.6f}",
            style="bold"
        )

        console.print(table)
        console.print()

        # Highlight slowest node
        print_warning(f"Slowest node: {colorize(slowest_node_id, Colors.BOLD + Colors.RED)} ({slowest_data['duration_ms']:.1f}ms avg)")

        # Highlight bottlenecks
        bottlenecks = []
        for node_id, timing_data in node_timings.items():
            percent = (timing_data["duration_ms"] / total_duration * 100) if total_duration > 0 else 0
            if percent > 50:
                bottlenecks.append((node_id, percent))

        if bottlenecks:
            print()
            print_warning("Bottlenecks (>50% of total time):")
            for node_id, percent in sorted(bottlenecks, key=lambda x: x[1], reverse=True):
                print(f"  {colorize(_BULLET, Colors.YELLOW)} {node_id}: {percent:.1f}%")

        console.print()
        return 0

    except ImportError:
        print_error("MLFlow not available")
        print_info("Install MLFlow with: pip install mlflow>=3.9.0")
        return 1

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
        return 1


def cmd_observability_status(args: argparse.Namespace) -> int:
    """
    Show MLFlow observability status.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not RICH_AVAILABLE:
        print_error("Rich library is required for observability status command")
        print_info("Install with: pip install rich>=13.0.0")
        return 1

    try:
        import mlflow
        from mlflow.tracking import MlflowClient
        from mlflow.entities import ViewType
        from datetime import timedelta

        mlflow_uri = args.mlflow_uri

        # Set tracking URI if provided
        if mlflow_uri:
            mlflow.set_tracking_uri(mlflow_uri)

        client = MlflowClient()
        console = Console()

        # Get tracking URI
        tracking_uri = mlflow.get_tracking_uri()

        # Test connection
        connected = True
        connection_status = colorize("Connected", Colors.GREEN)
        try:
            experiments = client.search_experiments(view_type=ViewType.ACTIVE_ONLY)
        except Exception as e:
            connected = False
            connection_status = colorize(f"Disconnected: {e}", Colors.RED)
            experiments = []

        console.print()
        title = Text("Observability Status", style="bold cyan")
        console.print(Panel(title, expand=False))
        console.print()

        # Display status
        status_table = Table(title=None, show_header=False)
        status_table.add_column("Property", style="cyan")
        status_table.add_column("Value", style="green")

        status_table.add_row("MLFlow Connection", connection_status)
        status_table.add_row("MLFlow URI", tracking_uri)

        console.print(status_table)
        console.print()

        if connected and experiments:
            # Show experiment count
            print_success(f"Found {len(experiments)} experiment(s)")

            # Show recent runs (last 24 hours)
            console.print()
            console.print(colorize("Recent Activity (Last 24 Hours):", Colors.BOLD))

            recent_cutoff = datetime.now() - timedelta(hours=24)
            total_recent_runs = 0

            for exp in experiments[:5]:  # Limit to first 5 experiments
                try:
                    runs = client.search_runs(
                        experiment_ids=[exp.experiment_id],
                        filter_string="attributes.start_time > '{}'".format(recent_cutoff.isoformat()),
                        max_results=1000
                    )
                    total_recent_runs += len(runs)

                    if runs:
                        console.print(f"  {colorize(exp.name, Colors.CYAN)}: {len(runs)} run(s)")

                except Exception:
                    # Skip experiments with query errors
                    pass

            if total_recent_runs == 0:
                print_info("No runs in the last 24 hours")
            else:
                print_success(f"Total recent runs: {total_recent_runs}")

        console.print()
        return 0

    except ImportError:
        print_error("MLFlow not available")
        print_info("Install MLFlow with: pip install mlflow>=3.9.0")
        return 1

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
        return 1


def cmd_agent_registry_start(args: argparse.Namespace) -> int:
    """
    Start the agent registry server.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    db_url = args.db_url

    print_info(f"Starting agent registry server on {colorize(f'{args.host}:{args.port}', Colors.CYAN)}")
    print_info(f"Database: {colorize(db_url, Colors.GRAY)}")

    try:
        # Create registry server
        server = AgentRegistryServer(registry_url=db_url)
        app = server.create_app()

        # Import uvicorn for running the server
        try:
            import uvicorn
        except ImportError:
            print_error("uvicorn is required to run the registry server")
            print_info("Install with: pip install uvicorn[standard]")
            return 1

        # Run server
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info" if args.verbose else "warning",
        )

        return 0

    except Exception as e:
        print_error(f"Failed to start registry server: {e}")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1


def cmd_agent_registry_list(args: argparse.Namespace) -> int:
    """
    List registered agents from the registry database.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    db_url = args.db_url

    # Parse URL to create storage config
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        from configurable_agents.config.schema import StorageConfig
        from configurable_agents.storage.factory import create_storage_backend

        config = StorageConfig(backend="sqlite", path=db_path)
        _, _, repo = create_storage_backend(config)
    else:
        print_error(f"Unsupported database URL: {db_url}")
        return 1

    # Query agents
    agents = repo.list_all(include_dead=args.include_dead)

    if not agents:
        print_warning("No agents found in registry")
        return 0

    print_success(f"Found {len(agents)} agent(s)")

    # Display agents
    if RICH_AVAILABLE:
        console = Console()
        table = Table(title=None)
        table.add_column("Agent ID", style="cyan", no_wrap=False)
        table.add_column("Name", style="green", no_wrap=False)
        table.add_column("Host:Port", style="blue", no_wrap=False)
        table.add_column("Last Heartbeat", style="magenta")
        table.add_column("Status", style="yellow")

        for agent in agents:
            status = colorize("Alive", Colors.GREEN) if agent.is_alive() else colorize("Dead", Colors.RED)
            heartbeat_str = agent.last_heartbeat.strftime("%Y-%m-%d %H:%M:%S") if agent.last_heartbeat else "N/A"
            table.add_row(
                agent.agent_id,
                agent.agent_name,
                f"{agent.host}:{agent.port}",
                heartbeat_str,
                status,
            )

        console.print(table)
        console.print()
    else:
        # Fallback to plain text
        print(f"\n{'Agent ID':<30} {'Name':<25} {'Host:Port':<20} {'Last Heartbeat':<20} {'Status'}")
        print("-" * 110)
        for agent in agents:
            status = "Alive" if agent.is_alive() else "Dead"
            heartbeat_str = agent.last_heartbeat.strftime("%Y-%m-%d %H:%M:%S") if agent.last_heartbeat else "N/A"
            print(f"{agent.agent_id:<30} {agent.agent_name:<25} {agent.host}:{agent.port:<14} {heartbeat_str:<20} {status}")

    return 0


def cmd_agent_registry_cleanup(args: argparse.Namespace) -> int:
    """
    Manually trigger cleanup of expired agents.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    db_url = args.db_url

    # Parse URL to create storage config
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        from configurable_agents.config.schema import StorageConfig
        from configurable_agents.storage.factory import create_storage_backend

        config = StorageConfig(backend="sqlite", path=db_path)
        _, _, repo = create_storage_backend(config)
    else:
        print_error(f"Unsupported database URL: {db_url}")
        return 1

    print_info("Cleaning up expired agents...")

    # Delete expired agents
    deleted_count = repo.delete_expired()

    if deleted_count > 0:
        print_success(f"Deleted {colorize(str(deleted_count), Colors.BOLD)} expired agent(s)")
    else:
        print_info("No expired agents found")

    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    """
    Launch the orchestration dashboard server.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    db_url = args.db_url
    mlflow_uri = args.mlflow_uri

    print_info(f"Starting dashboard server on {colorize(f'{args.host}:{args.port}', Colors.CYAN)}")
    print_info(f"Database: {colorize(db_url, Colors.GRAY)}")

    if mlflow_uri:
        print_info(f"MLFlow UI: {colorize(mlflow_uri, Colors.GRAY)}")

    # Import uvicorn for running the server
    try:
        import uvicorn
    except ImportError:
        print_error("uvicorn is required to run the dashboard server")
        print_info("Install with: pip install uvicorn[standard]")
        return 1

    # Create dashboard app
    try:
        dashboard = create_dashboard_app(
            db_url=db_url,
            mlflow_tracking_uri=mlflow_uri,
        )
        app = dashboard.get_app()
    except Exception as e:
        print_error(f"Failed to create dashboard app: {e}")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1

    # Print server URLs
    print()
    print(f"{colorize('=' * 60, Colors.GREEN)}")
    print(f"{colorize('Dashboard server started!', Colors.BOLD + Colors.GREEN)}")
    print(f"{colorize('=' * 60, Colors.GREEN)}")
    print()
    print(f"{colorize('Endpoints:', Colors.BOLD)}")
    print(f"  Dashboard:    http://localhost:{args.port}/")
    print(f"  Workflows:    http://localhost:{args.port}/workflows")
    print(f"  Agents:       http://localhost:{args.port}/agents")
    if mlflow_uri:
        print(f"  MLFlow UI:    http://localhost:{args.port}/mlflow")
    print()

    # Run server
    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info" if args.verbose else "warning",
        )
    except KeyboardInterrupt:
        print_info("\nDashboard server stopped")
        return 0
    except Exception as e:
        print_error(f"Server error: {e}")
        if args.verbose:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        return 1

    return 0


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

  # Deploy workflow as Docker container
  configurable-agents deploy workflow.yaml --api-port 8000

  # Generate deployment artifacts only (no Docker build)
  configurable-agents deploy workflow.yaml --generate --output-dir ./my_deploy

  # Generate cost report for last 7 days
  configurable-agents report costs --period last_7_days --breakdown

  # Export cost data to CSV
  configurable-agents report costs --output costs.csv --format csv

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
    run_parser.add_argument(
        "--enable-profiling",
        action="store_true",
        help="Enable performance profiling for this run (captures node timing data)",
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

    # Deploy command
    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Deploy workflow as Docker container",
        description="Generate deployment artifacts and run workflow in Docker container"
    )
    deploy_parser.add_argument("config_file", help="Path to workflow config (YAML/JSON)")
    deploy_parser.add_argument(
        "--output-dir",
        default="./deploy",
        help="Artifacts output directory (default: ./deploy)"
    )
    deploy_parser.add_argument(
        "--api-port",
        type=int,
        default=8000,
        help="FastAPI server port (default: 8000)"
    )
    deploy_parser.add_argument(
        "--mlflow-port",
        type=int,
        default=5000,
        help="MLFlow UI port (default: 5000)"
    )
    deploy_parser.add_argument(
        "--name",
        help="Container name (default: workflow name from config)"
    )
    deploy_parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Sync/async threshold in seconds (default: 30)"
    )
    deploy_parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate artifacts only, skip Docker build and run"
    )
    deploy_parser.add_argument(
        "--no-mlflow",
        action="store_true",
        help="Disable MLFlow UI in container"
    )
    deploy_parser.add_argument(
        "--env-file",
        default=".env",
        help="Environment variables file (default: .env)"
    )
    deploy_parser.add_argument(
        "--no-env-file",
        action="store_true",
        help="Skip environment file (configure manually)"
    )
    deploy_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    deploy_parser.set_defaults(func=cmd_deploy)

    # Report command (with subcommands)
    report_parser = subparsers.add_parser(
        "report",
        help="Generate reports from MLFlow data",
        description="Generate cost and usage reports",
    )
    report_subparsers = report_parser.add_subparsers(
        dest="report_command", help="Report type"
    )

    # Report costs subcommand
    costs_parser = report_subparsers.add_parser(
        "costs",
        help="Generate cost reports",
        description="Query MLFlow for cost data and generate reports",
    )
    costs_parser.add_argument(
        "--tracking-uri",
        default="file://./mlruns",
        help="MLFlow tracking URI (default: file://./mlruns)",
    )
    costs_parser.add_argument(
        "--experiment",
        help="Filter by experiment name",
    )
    costs_parser.add_argument(
        "--workflow",
        help="Filter by workflow name",
    )
    costs_parser.add_argument(
        "--period",
        choices=["today", "yesterday", "last_7_days", "last_30_days", "this_month"],
        help="Filter by predefined time period",
    )
    costs_parser.add_argument(
        "--start-date",
        help="Filter runs after this date (ISO format: YYYY-MM-DD)",
    )
    costs_parser.add_argument(
        "--end-date",
        help="Filter runs before this date (ISO format: YYYY-MM-DD)",
    )
    costs_parser.add_argument(
        "--status",
        choices=["success", "failure"],
        help="Filter by run status",
    )
    costs_parser.add_argument(
        "--breakdown",
        action="store_true",
        help="Show cost breakdown by workflow and model",
    )
    costs_parser.add_argument(
        "--aggregate-by",
        choices=["daily", "weekly", "monthly"],
        help="Aggregate costs by time period",
    )
    costs_parser.add_argument(
        "-o", "--output",
        help="Export results to file (JSON or CSV based on --format)",
    )
    costs_parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)",
    )
    costs_parser.add_argument(
        "--include-summary",
        action="store_true",
        default=True,
        help="Include summary in JSON export (default: True)",
    )
    costs_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    costs_parser.set_defaults(func=cmd_report_costs)

    # Cost-report command (unified multi-provider cost reporting)
    cost_report_parser = subparsers.add_parser(
        "cost-report",
        help="Generate unified cost report by provider",
        description="Generate cost breakdown by provider from MLFlow experiment data",
    )
    cost_report_parser.add_argument(
        "--experiment",
        required=True,
        help="MLFlow experiment name (required)",
    )
    cost_report_parser.add_argument(
        "--mlflow-uri",
        default=None,
        help="MLFlow tracking URI (default: from config or file://./mlruns)",
    )
    cost_report_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    cost_report_parser.set_defaults(func=cmd_cost_report)

    # Profile-report command (bottleneck analysis)
    profile_report_parser = subparsers.add_parser(
        "profile-report",
        help="Generate profiling report with bottleneck analysis",
        description="Analyze workflow execution times and identify bottlenecks",
    )
    profile_report_parser.add_argument(
        "--run-id",
        default=None,
        help="MLFlow run ID (default: latest run)",
    )
    profile_report_parser.add_argument(
        "--mlflow-uri",
        default=None,
        help="MLFlow tracking URI (default: from config or file://./mlruns)",
    )
    profile_report_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    profile_report_parser.set_defaults(func=cmd_profile_report)

    # Observability command group
    observability_parser = subparsers.add_parser(
        "observability",
        help="Observability commands for MLFlow integration",
        description="Manage and inspect MLFlow observability data",
    )
    observability_subparsers = observability_parser.add_subparsers(
        dest="observability_command", help="Observability subcommands"
    )

    # Observability status subcommand
    obs_status_parser = observability_subparsers.add_parser(
        "status",
        help="Show MLFlow connection and status",
        description="Display MLFlow connection status and recent run information",
    )
    obs_status_parser.add_argument(
        "--mlflow-uri",
        default=None,
        help="MLFlow tracking URI (default: from config or file://./mlruns)",
    )
    obs_status_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    obs_status_parser.set_defaults(func=cmd_observability_status)

    # Observability cost-report subcommand (alias to main command)
    obs_cost_parser = observability_subparsers.add_parser(
        "cost-report",
        help="Generate unified cost report (alias)",
        description="Alias for cost-report command",
    )
    obs_cost_parser.add_argument(
        "--experiment",
        required=True,
        help="MLFlow experiment name (required)",
    )
    obs_cost_parser.add_argument(
        "--mlflow-uri",
        default=None,
        help="MLFlow tracking URI (default: from config or file://./mlruns)",
    )
    obs_cost_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    obs_cost_parser.set_defaults(func=cmd_cost_report)

    # Observability profile-report subcommand (alias to main command)
    obs_profile_parser = observability_subparsers.add_parser(
        "profile-report",
        help="Generate profiling report (alias)",
        description="Alias for profile-report command",
    )
    obs_profile_parser.add_argument(
        "--run-id",
        default=None,
        help="MLFlow run ID (default: latest run)",
    )
    obs_profile_parser.add_argument(
        "--mlflow-uri",
        default=None,
        help="MLFlow tracking URI (default: from config or file://./mlruns)",
    )
    obs_profile_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    obs_profile_parser.set_defaults(func=cmd_profile_report)

    # Agent registry command group
    registry_parser = subparsers.add_parser(
        "agent-registry",
        help="Agent registry management commands",
        description="Manage the agent registry server for distributed agent coordination",
    )
    registry_subparsers = registry_parser.add_subparsers(
        dest="registry_command", help="Registry subcommands"
    )

    # Registry start subcommand
    registry_start_parser = registry_subparsers.add_parser(
        "start",
        help="Start the agent registry server",
        description="Start the agent registry server using uvicorn",
    )
    registry_start_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    registry_start_parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="Port to listen on (default: 9000)",
    )
    registry_start_parser.add_argument(
        "--db-url",
        default="sqlite:///agent_registry.db",
        help="Database URL for registry storage (default: sqlite:///agent_registry.db)",
    )
    registry_start_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    registry_start_parser.set_defaults(func=cmd_agent_registry_start)

    # Registry list subcommand
    registry_list_parser = registry_subparsers.add_parser(
        "list",
        help="List registered agents",
        description="List all agents in the registry database",
    )
    registry_list_parser.add_argument(
        "--db-url",
        default="sqlite:///agent_registry.db",
        help="Database URL for registry storage (default: sqlite:///agent_registry.db)",
    )
    registry_list_parser.add_argument(
        "--include-dead",
        action="store_true",
        help="Include expired/dead agents in the list",
    )
    registry_list_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    registry_list_parser.set_defaults(func=cmd_agent_registry_list)

    # Registry cleanup subcommand
    registry_cleanup_parser = registry_subparsers.add_parser(
        "cleanup",
        help="Clean up expired agents",
        description="Manually trigger cleanup of expired agents from the registry",
    )
    registry_cleanup_parser.add_argument(
        "--db-url",
        default="sqlite:///agent_registry.db",
        help="Database URL for registry storage (default: sqlite:///agent_registry.db)",
    )
    registry_cleanup_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    registry_cleanup_parser.set_defaults(func=cmd_agent_registry_cleanup)

    # Dashboard command
    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Launch the orchestration dashboard",
        description="Launch the web-based orchestration dashboard for monitoring workflows and agents",
    )
    dashboard_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    dashboard_parser.add_argument(
        "--port",
        type=int,
        default=7861,
        help="Port to listen on (default: 7861)",
    )
    dashboard_parser.add_argument(
        "--db-url",
        default="sqlite:///configurable_agents.db",
        help="Database URL for storage (default: sqlite:///configurable_agents.db)",
    )
    dashboard_parser.add_argument(
        "--mlflow-uri",
        default=None,
        help="MLFlow tracking URI for embedded UI (default: None)",
    )
    dashboard_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    dashboard_parser.set_defaults(func=cmd_dashboard)

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
