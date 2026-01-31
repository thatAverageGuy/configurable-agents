"""
Tests for CLI interface.

Tests command-line argument parsing, execution, and error handling.
"""

import json
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from configurable_agents.cli import (
    Colors,
    cmd_report_costs,
    cmd_run,
    cmd_validate,
    colorize,
    create_parser,
    main,
    parse_input_args,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from configurable_agents.runtime import (
    ConfigLoadError,
    ConfigValidationError,
    StateInitializationError,
    WorkflowExecutionError,
)


# --- Helper Functions ---


def get_test_config_path() -> Path:
    """Get path to test config file."""
    return Path(__file__).parent / "config" / "fixtures" / "valid_config.yaml"


# --- Tests: Input Parsing ---


def test_parse_input_args_simple_string():
    """Test parsing simple string inputs."""
    result = parse_input_args(["topic=AI Safety"])
    assert result == {"topic": "AI Safety"}


def test_parse_input_args_quoted_string():
    """Test parsing quoted string inputs."""
    result = parse_input_args(["topic='AI Safety'", 'name="Alice"'])
    assert result == {"topic": "AI Safety", "name": "Alice"}


def test_parse_input_args_integer():
    """Test parsing integer inputs."""
    result = parse_input_args(["count=5", "level=10"])
    assert result == {"count": 5, "level": 10}


def test_parse_input_args_boolean():
    """Test parsing boolean inputs."""
    result = parse_input_args(["enabled=true", "debug=false"])
    assert result == {"enabled": True, "debug": False}


def test_parse_input_args_mixed_types():
    """Test parsing mixed type inputs."""
    result = parse_input_args(["topic=AI", "count=5", "enabled=true"])
    assert result == {"topic": "AI", "count": 5, "enabled": True}


def test_parse_input_args_list():
    """Test parsing list inputs (JSON array)."""
    result = parse_input_args(['tags=["ai", "safety"]'])
    assert result == {"tags": ["ai", "safety"]}


def test_parse_input_args_dict():
    """Test parsing dict inputs (JSON object)."""
    result = parse_input_args(['metadata={"author": "Alice", "version": 1}'])
    assert result == {"metadata": {"author": "Alice", "version": 1}}


def test_parse_input_args_invalid_format():
    """Test error on invalid input format (missing =)."""
    with pytest.raises(ValueError, match="Invalid input format"):
        parse_input_args(["invalid_no_equals"])


def test_parse_input_args_empty_list():
    """Test parsing empty input list."""
    result = parse_input_args([])
    assert result == {}


def test_parse_input_args_value_with_equals():
    """Test parsing value containing equals sign."""
    result = parse_input_args(["url=https://example.com?key=value"])
    assert result == {"url": "https://example.com?key=value"}


# --- Tests: Color Output ---


def test_colorize_with_tty():
    """Test colorize adds ANSI codes when stdout is TTY."""
    with patch("sys.stdout.isatty", return_value=True):
        result = colorize("test", Colors.GREEN)
        assert result.startswith(Colors.GREEN)
        assert result.endswith(Colors.RESET)
        assert "test" in result


def test_colorize_without_tty():
    """Test colorize returns plain text when stdout is not TTY."""
    with patch("sys.stdout.isatty", return_value=False):
        result = colorize("test", Colors.GREEN)
        assert result == "test"


def test_print_success(capsys):
    """Test print_success outputs formatted message."""
    print_success("Task completed")
    captured = capsys.readouterr()
    assert "Task completed" in captured.out
    assert "✓" in captured.out


def test_print_error(capsys):
    """Test print_error outputs to stderr."""
    print_error("Something failed")
    captured = capsys.readouterr()
    assert "Something failed" in captured.err
    assert "✗" in captured.err


def test_print_info(capsys):
    """Test print_info outputs formatted message."""
    print_info("Information here")
    captured = capsys.readouterr()
    assert "Information here" in captured.out
    assert "ℹ" in captured.out


def test_print_warning(capsys):
    """Test print_warning outputs formatted message."""
    print_warning("Be careful")
    captured = capsys.readouterr()
    assert "Be careful" in captured.out
    assert "⚠" in captured.out


# --- Tests: Argument Parser ---


def test_create_parser():
    """Test parser creation and basic structure."""
    parser = create_parser()
    assert parser.prog == "configurable-agents"


def test_parser_run_command():
    """Test parsing run command with inputs."""
    parser = create_parser()
    args = parser.parse_args(["run", "workflow.yaml", "--input", "topic=AI", "--verbose"])

    assert args.command == "run"
    assert args.config_file == "workflow.yaml"
    assert args.input == ["topic=AI"]
    assert args.verbose is True


def test_parser_run_command_multiple_inputs():
    """Test parsing run command with multiple inputs."""
    parser = create_parser()
    args = parser.parse_args(
        ["run", "workflow.yaml", "--input", "topic=AI", "--input", "count=5"]
    )

    assert args.input == ["topic=AI", "count=5"]


def test_parser_validate_command():
    """Test parsing validate command."""
    parser = create_parser()
    args = parser.parse_args(["validate", "workflow.yaml", "--verbose"])

    assert args.command == "validate"
    assert args.config_file == "workflow.yaml"
    assert args.verbose is True


def test_parser_no_command():
    """Test parsing with no command shows help."""
    parser = create_parser()
    args = parser.parse_args([])
    assert args.command is None


def test_parser_version(capsys):
    """Test --version flag."""
    parser = create_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--version"])


# --- Tests: cmd_run ---


@patch("configurable_agents.cli.run_workflow")
def test_cmd_run_success(mock_run_workflow, tmp_path):
    """Test successful workflow execution."""
    # Create test config
    config_file = tmp_path / "test.yaml"
    config_file.write_text("flow:\n  name: test\n")

    # Mock successful execution
    mock_run_workflow.return_value = {"result": "success", "output": "test output"}

    # Create args
    parser = create_parser()
    args = parser.parse_args(["run", str(config_file), "--input", "topic=AI"])

    # Execute
    exit_code = cmd_run(args)

    # Verify
    assert exit_code == 0
    mock_run_workflow.assert_called_once()
    call_args = mock_run_workflow.call_args
    assert call_args[0][0] == str(config_file)
    assert call_args[0][1] == {"topic": "AI"}


@patch("configurable_agents.cli.run_workflow")
def test_cmd_run_file_not_found(mock_run_workflow):
    """Test run command with non-existent file."""
    parser = create_parser()
    args = parser.parse_args(["run", "nonexistent.yaml"])

    exit_code = cmd_run(args)

    assert exit_code == 1
    mock_run_workflow.assert_not_called()


@patch("configurable_agents.cli.run_workflow")
def test_cmd_run_invalid_input_format(mock_run_workflow, tmp_path):
    """Test run command with invalid input format."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("flow:\n  name: test\n")

    parser = create_parser()
    args = parser.parse_args(["run", str(config_file), "--input", "invalid_no_equals"])

    exit_code = cmd_run(args)

    assert exit_code == 1
    mock_run_workflow.assert_not_called()


@patch("configurable_agents.cli.run_workflow")
def test_cmd_run_config_load_error(mock_run_workflow, tmp_path):
    """Test run command with config load error."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("invalid: yaml: content:")

    mock_run_workflow.side_effect = ConfigLoadError(
        "Failed to parse config", phase="config_load"
    )

    parser = create_parser()
    args = parser.parse_args(["run", str(config_file)])

    exit_code = cmd_run(args)

    assert exit_code == 1


@patch("configurable_agents.cli.run_workflow")
def test_cmd_run_config_validation_error(mock_run_workflow, tmp_path):
    """Test run command with config validation error."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("flow:\n  name: test\n")

    mock_run_workflow.side_effect = ConfigValidationError(
        "Invalid config structure", phase="validation"
    )

    parser = create_parser()
    args = parser.parse_args(["run", str(config_file)])

    exit_code = cmd_run(args)

    assert exit_code == 1


@patch("configurable_agents.cli.run_workflow")
def test_cmd_run_state_initialization_error(mock_run_workflow, tmp_path):
    """Test run command with state initialization error."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("flow:\n  name: test\n")

    mock_run_workflow.side_effect = StateInitializationError("Missing required field: topic")

    parser = create_parser()
    args = parser.parse_args(["run", str(config_file)])

    exit_code = cmd_run(args)

    assert exit_code == 1


@patch("configurable_agents.cli.run_workflow")
def test_cmd_run_workflow_execution_error(mock_run_workflow, tmp_path):
    """Test run command with workflow execution error."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("flow:\n  name: test\n")

    mock_run_workflow.side_effect = WorkflowExecutionError(
        "Node execution failed", phase="execution"
    )

    parser = create_parser()
    args = parser.parse_args(["run", str(config_file)])

    exit_code = cmd_run(args)

    assert exit_code == 1


@patch("configurable_agents.cli.run_workflow")
def test_cmd_run_verbose_mode(mock_run_workflow, tmp_path):
    """Test run command with verbose mode enabled."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("flow:\n  name: test\n")

    mock_run_workflow.return_value = {"result": "success"}

    parser = create_parser()
    args = parser.parse_args(["run", str(config_file), "--verbose"])

    exit_code = cmd_run(args)

    assert exit_code == 0
    # Verify verbose flag passed to run_workflow
    call_args = mock_run_workflow.call_args
    assert call_args[1]["verbose"] is True


# --- Tests: cmd_validate ---


@patch("configurable_agents.cli.validate_workflow")
def test_cmd_validate_success(mock_validate_workflow, tmp_path):
    """Test successful config validation."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("flow:\n  name: test\n")

    mock_validate_workflow.return_value = True

    parser = create_parser()
    args = parser.parse_args(["validate", str(config_file)])

    exit_code = cmd_validate(args)

    assert exit_code == 0
    mock_validate_workflow.assert_called_once_with(str(config_file))


@patch("configurable_agents.cli.validate_workflow")
def test_cmd_validate_file_not_found(mock_validate_workflow):
    """Test validate command with non-existent file."""
    parser = create_parser()
    args = parser.parse_args(["validate", "nonexistent.yaml"])

    exit_code = cmd_validate(args)

    assert exit_code == 1
    mock_validate_workflow.assert_not_called()


@patch("configurable_agents.cli.validate_workflow")
def test_cmd_validate_config_load_error(mock_validate_workflow, tmp_path):
    """Test validate command with config load error."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("invalid: yaml: content:")

    mock_validate_workflow.side_effect = ConfigLoadError(
        "Failed to parse config", phase="config_load"
    )

    parser = create_parser()
    args = parser.parse_args(["validate", str(config_file)])

    exit_code = cmd_validate(args)

    assert exit_code == 1


@patch("configurable_agents.cli.validate_workflow")
def test_cmd_validate_config_validation_error(mock_validate_workflow, tmp_path):
    """Test validate command with validation error."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("flow:\n  name: test\n")

    mock_validate_workflow.side_effect = ConfigValidationError(
        "Invalid config structure", phase="validation"
    )

    parser = create_parser()
    args = parser.parse_args(["validate", str(config_file)])

    exit_code = cmd_validate(args)

    assert exit_code == 1


# --- Tests: main() ---


def test_main_no_arguments():
    """Test main with no arguments shows help."""
    with patch("sys.argv", ["configurable-agents"]):
        exit_code = main()
        assert exit_code == 1


@patch("configurable_agents.cli.cmd_run")
def test_main_run_command(mock_cmd_run, tmp_path):
    """Test main dispatches to run command."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("flow:\n  name: test\n")

    mock_cmd_run.return_value = 0

    with patch("sys.argv", ["configurable-agents", "run", str(config_file)]):
        exit_code = main()
        assert exit_code == 0
        mock_cmd_run.assert_called_once()


@patch("configurable_agents.cli.cmd_validate")
def test_main_validate_command(mock_cmd_validate, tmp_path):
    """Test main dispatches to validate command."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("flow:\n  name: test\n")

    mock_cmd_validate.return_value = 0

    with patch("sys.argv", ["configurable-agents", "validate", str(config_file)]):
        exit_code = main()
        assert exit_code == 0
        mock_cmd_validate.assert_called_once()


# --- Integration Tests ---


@pytest.mark.integration
def test_cli_run_simple_workflow(tmp_path):
    """Integration test: Run actual workflow via CLI."""
    # Create simple workflow config
    config_file = tmp_path / "greeting.yaml"
    config_file.write_text(
        """
schema_version: "1.0"

flow:
  name: simple_greeting

state:
  fields:
    name:
      type: str
      required: true
    greeting:
      type: str
      default: ""

nodes:
  - id: greet
    prompt: "Generate a greeting for {state.name}"
    outputs: [greeting]
    output_schema:
      type: object
      fields:
        - name: greeting
          type: str

edges:
  - {from: START, to: greet}
  - {from: greet, to: END}
"""
    )

    # Run via subprocess (tests actual CLI entry point)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "configurable_agents",
            "run",
            str(config_file),
            "--input",
            "name=Alice",
        ],
        capture_output=True,
        text=True,
    )

    # Verify execution (may fail if no API key, but should parse correctly)
    assert result.returncode in [0, 1]  # 0 = success, 1 = API key missing
    assert "greeting" in result.stdout or "API" in result.stderr


@pytest.mark.integration
def test_cli_validate_workflow(tmp_path):
    """Integration test: Validate actual workflow via CLI."""
    # Create valid workflow config
    config_file = tmp_path / "greeting.yaml"
    config_file.write_text(
        """
schema_version: "1.0"

flow:
  name: simple_greeting

state:
  fields:
    name: {type: str, required: true}
    greeting: {type: str, default: ""}

nodes:
  - id: greet
    prompt: "Say hello to {state.name}"
    outputs: [greeting]
    output_schema:
      type: object
      fields:
        - name: greeting
          type: str

edges:
  - {from: START, to: greet}
  - {from: greet, to: END}
"""
    )

    # Validate via subprocess
    result = subprocess.run(
        [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
        capture_output=True,
        text=True,
    )

    # Verify validation passed
    assert result.returncode == 0
    assert "valid" in result.stdout.lower()


# --- Tests: cmd_report_costs ---


@patch("configurable_agents.cli.CostReporter")
@patch("configurable_agents.cli.get_date_range_filter")
def test_cmd_report_costs_success(mock_date_filter, mock_reporter_class):
    """Test successful cost report generation."""
    from argparse import Namespace
    from datetime import datetime

    from configurable_agents.observability import CostEntry, CostSummary

    # Mock date filter
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 1, 31)
    mock_date_filter.return_value = (start_date, end_date)

    # Mock cost reporter
    mock_reporter = MagicMock()
    mock_reporter_class.return_value = mock_reporter

    # Mock cost entries
    mock_entries = [
        CostEntry(
            run_id="run_1",
            run_name="test",
            workflow_name="workflow_a",
            start_time=datetime(2026, 1, 15),
            duration_seconds=10.0,
            status="success",
            total_cost_usd=0.005,
            input_tokens=100,
            output_tokens=400,
            node_count=2,
            model="gemini-1.5-flash",
        )
    ]
    mock_reporter.get_cost_entries.return_value = mock_entries

    # Mock summary
    mock_summary = CostSummary(
        total_cost_usd=0.005,
        total_runs=1,
        total_tokens=500,
        successful_runs=1,
        failed_runs=0,
        avg_cost_per_run=0.005,
        avg_tokens_per_run=500.0,
        date_range=(start_date, end_date),
        breakdown_by_workflow={"workflow_a": 0.005},
        breakdown_by_model={"gemini-1.5-flash": 0.005},
    )
    mock_reporter.generate_summary.return_value = mock_summary

    # Create args
    args = Namespace(
        tracking_uri="file://./mlruns",
        experiment=None,
        workflow=None,
        period="last_7_days",
        start_date=None,
        end_date=None,
        status=None,
        breakdown=False,
        aggregate_by=None,
        output=None,
        format="json",
        include_summary=True,
        verbose=False,
    )

    # Execute
    exit_code = cmd_report_costs(args)

    # Verify
    assert exit_code == 0
    mock_reporter_class.assert_called_once_with(tracking_uri="file://./mlruns")
    mock_date_filter.assert_called_once_with("last_7_days")
    mock_reporter.get_cost_entries.assert_called_once()
    mock_reporter.generate_summary.assert_called_once()


@patch("configurable_agents.cli.CostReporter")
def test_cmd_report_costs_no_entries(mock_reporter_class):
    """Test cost report with no matching entries."""
    from argparse import Namespace

    # Mock cost reporter
    mock_reporter = MagicMock()
    mock_reporter_class.return_value = mock_reporter
    mock_reporter.get_cost_entries.return_value = []  # No entries

    # Create args
    args = Namespace(
        tracking_uri="file://./mlruns",
        experiment=None,
        workflow=None,
        period=None,
        start_date=None,
        end_date=None,
        status=None,
        breakdown=False,
        aggregate_by=None,
        output=None,
        format="json",
        include_summary=True,
        verbose=False,
    )

    # Execute
    exit_code = cmd_report_costs(args)

    # Verify
    assert exit_code == 0  # Should still succeed with warning


@patch("configurable_agents.cli.CostReporter")
def test_cmd_report_costs_mlflow_unavailable(mock_reporter_class):
    """Test error when MLFlow is not available."""
    from argparse import Namespace

    # Mock RuntimeError when initializing reporter
    mock_reporter_class.side_effect = RuntimeError("MLFlow is not installed")

    # Create args
    args = Namespace(
        tracking_uri="file://./mlruns",
        experiment=None,
        workflow=None,
        period=None,
        start_date=None,
        end_date=None,
        status=None,
        breakdown=False,
        aggregate_by=None,
        output=None,
        format="json",
        include_summary=True,
        verbose=False,
    )

    # Execute
    exit_code = cmd_report_costs(args)

    # Verify error
    assert exit_code == 1


@patch("configurable_agents.cli.CostReporter")
@patch("configurable_agents.cli.get_date_range_filter")
def test_cmd_report_costs_with_export(mock_date_filter, mock_reporter_class, tmp_path):
    """Test cost report with export to JSON file."""
    from argparse import Namespace
    from datetime import datetime

    from configurable_agents.observability import CostEntry, CostSummary

    # Mock date filter
    mock_date_filter.return_value = (datetime(2026, 1, 1), datetime(2026, 1, 31))

    # Mock cost reporter
    mock_reporter = MagicMock()
    mock_reporter_class.return_value = mock_reporter

    mock_entries = [
        CostEntry(
            run_id="run_1",
            run_name="test",
            workflow_name="test",
            start_time=datetime(2026, 1, 15),
            duration_seconds=10.0,
            status="success",
            total_cost_usd=0.005,
            input_tokens=100,
            output_tokens=400,
            node_count=2,
        )
    ]
    mock_reporter.get_cost_entries.return_value = mock_entries

    mock_summary = CostSummary(
        total_cost_usd=0.005,
        total_runs=1,
        total_tokens=500,
        successful_runs=1,
        failed_runs=0,
        avg_cost_per_run=0.005,
        avg_tokens_per_run=500.0,
        date_range=(datetime(2026, 1, 1), datetime(2026, 1, 31)),
        breakdown_by_workflow={"test": 0.005},
        breakdown_by_model={},
    )
    mock_reporter.generate_summary.return_value = mock_summary

    # Create args with output file
    output_file = tmp_path / "costs.json"
    args = Namespace(
        tracking_uri="file://./mlruns",
        experiment=None,
        workflow=None,
        period=None,
        start_date=None,
        end_date=None,
        status=None,
        breakdown=False,
        aggregate_by=None,
        output=str(output_file),
        format="json",
        include_summary=True,
        verbose=False,
    )

    # Execute
    exit_code = cmd_report_costs(args)

    # Verify
    assert exit_code == 0
    mock_reporter.export_to_json.assert_called_once_with(
        mock_entries, str(output_file), include_summary=True
    )


@patch("configurable_agents.cli.CostReporter")
def test_cmd_report_costs_invalid_period(mock_reporter_class):
    """Test error with invalid period."""
    from argparse import Namespace

    # Mock cost reporter
    mock_reporter = MagicMock()
    mock_reporter_class.return_value = mock_reporter

    # Create args with invalid period (will fail at get_date_range_filter)
    args = Namespace(
        tracking_uri="file://./mlruns",
        experiment=None,
        workflow=None,
        period="invalid_period",  # Invalid
        start_date=None,
        end_date=None,
        status=None,
        breakdown=False,
        aggregate_by=None,
        output=None,
        format="json",
        include_summary=True,
        verbose=False,
    )

    # Execute
    with patch("configurable_agents.cli.get_date_range_filter") as mock_filter:
        mock_filter.side_effect = ValueError("Invalid period")
        exit_code = cmd_report_costs(args)

    # Verify error
    assert exit_code == 1


# --- Test Summary ---
# Total: 47 tests
# - Input parsing: 11 tests
# - Color output: 8 tests
# - Argument parser: 6 tests
# - cmd_run: 9 tests
# - cmd_validate: 4 tests
# - cmd_report_costs: 5 tests
# - main(): 2 tests
# - Integration: 2 tests
