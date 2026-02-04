"""Tests for CLI observability commands.

Tests for:
- cost-report command
- profile-report command
- observability command group (status, cost-report, profile-report)
- --enable-profiling flag on run command
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from io import StringIO

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
class TestCostReportCommand:
    """Test cost-report CLI command."""

    def test_cost_report_command_exists(self):
        """Verify cost-report command is registered in CLI parser."""
        from configurable_agents.cli import create_parser

        parser = create_parser()

        # Test that cost-report is a valid subcommand
        with patch("sys.argv", ["configurable-agents", "cost-report", "--help"]):
            # Should not raise SystemExit for valid command
            try:
                args = parser.parse_args(["cost-report", "--experiment", "test"])
                assert args.command == "cost-report"
                assert args.experiment == "test"
            except SystemExit:
                pytest.fail("cost-report command not found in parser")

    def test_cost_report_requires_experiment(self):
        """Verify --experiment is required for cost-report."""
        from configurable_agents.cli import create_parser
        from argparse import ArgumentParser

        parser = create_parser()

        # Should fail without --experiment
        with pytest.raises(SystemExit):
            parser.parse_args(["cost-report"])

    def test_cost_report_with_mock_mlflow(self):
        """Test cost-report with mocked MLFlow data."""
        from configurable_agents.cli import cmd_cost_report
        from argparse import Namespace

        # Mock generate_cost_report function
        mock_report = {
            "experiment": "test_experiment",
            "experiment_id": "1",
            "total_cost_usd": 0.50,
            "total_tokens": 10000,
            "by_provider": {
                "openai": {
                    "total_cost_usd": 0.30,
                    "total_tokens": 6000,
                    "run_count": 5,
                    "models": {
                        "gpt-4o": {
                            "total_cost_usd": 0.30,
                            "total_tokens": 6000,
                            "run_count": 5,
                        }
                    }
                },
                "anthropic": {
                    "total_cost_usd": 0.20,
                    "total_tokens": 4000,
                    "run_count": 3,
                    "models": {
                        "claude-3-opus": {
                            "total_cost_usd": 0.20,
                            "total_tokens": 4000,
                            "run_count": 3,
                        }
                    }
                }
            },
            "generated_at": "2025-01-01T00:00:00Z"
        }

        with patch("configurable_agents.cli.generate_cost_report", return_value=mock_report):
            args = Namespace(
                experiment="test_experiment",
                mlflow_uri=None,
                verbose=False
            )

            # Should execute without error
            result = cmd_cost_report(args)
            assert result == 0

    def test_cost_report_highlights_most_expensive(self):
        """Verify most expensive provider is highlighted in output."""
        from configurable_agents.cli import cmd_cost_report
        from argparse import Namespace
        from rich.console import Console
        from io import StringIO

        # Mock report with clear cost difference
        mock_report = {
            "experiment": "test",
            "experiment_id": "1",
            "total_cost_usd": 1.00,
            "total_tokens": 10000,
            "by_provider": {
                "expensive_provider": {
                    "total_cost_usd": 0.80,
                    "total_tokens": 8000,
                    "run_count": 10,
                    "models": {"model-a": {"total_cost_usd": 0.80, "total_tokens": 8000, "run_count": 10}}
                },
                "cheap_provider": {
                    "total_cost_usd": 0.20,
                    "total_tokens": 2000,
                    "run_count": 2,
                    "models": {"model-b": {"total_cost_usd": 0.20, "total_tokens": 2000, "run_count": 2}}
                }
            }
        }

        with patch("configurable_agents.cli.generate_cost_report", return_value=mock_report):
            # Capture console output
            console = Console(file=StringIO(), force_terminal=True)
            with patch("configurable_agents.cli.Console", return_value=console):
                args = Namespace(experiment="test", mlflow_uri=None, verbose=False)
                result = cmd_cost_report(args)
                assert result == 0

    def test_cost_report_shows_totals(self):
        """Verify totals row is displayed in cost report."""
        from configurable_agents.cli import cmd_cost_report
        from argparse import Namespace

        mock_report = {
            "experiment": "test",
            "experiment_id": "1",
            "total_cost_usd": 0.50,
            "total_tokens": 10000,
            "by_provider": {
                "openai": {
                    "total_cost_usd": 0.50,
                    "total_tokens": 10000,
                    "run_count": 5,
                    "models": {"gpt-4o": {"total_cost_usd": 0.50, "total_tokens": 10000, "run_count": 5}}
                }
            }
        }

        with patch("configurable_agents.cli.generate_cost_report", return_value=mock_report):
            args = Namespace(experiment="test", mlflow_uri=None, verbose=False)
            result = cmd_cost_report(args)
            assert result == 0

    def test_cost_report_handles_mlflow_error(self):
        """Verify error handling when MLFlow is not available."""
        from configurable_agents.cli import cmd_cost_report
        from argparse import Namespace

        with patch("configurable_agents.cli.generate_cost_report", side_effect=RuntimeError("MLFlow not installed")):
            args = Namespace(experiment="test", mlflow_uri=None, verbose=False)
            result = cmd_cost_report(args)
            assert result == 1


@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
class TestProfileReportCommand:
    """Test profile-report CLI command."""

    def test_profile_report_command_exists(self):
        """Verify profile-report command is registered in CLI parser."""
        from configurable_agents.cli import create_parser

        parser = create_parser()

        args = parser.parse_args(["profile-report"])
        assert args.command == "profile-report"
        assert args.run_id is None  # Default value
        assert args.mlflow_uri is None

    def test_profile_report_defaults_to_latest_run(self):
        """Verify profile-report defaults to latest run when --run-id not provided."""
        from configurable_agents.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["profile-report"])

        assert args.run_id is None  # Will use latest run

    def test_profile_report_accepts_run_id(self):
        """Verify profile-report accepts --run-id argument."""
        from configurable_agents.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["profile-report", "--run-id", "abc123"])

        assert args.run_id == "abc123"

    def test_profile_report_with_mock_mlflow(self):
        """Test profile-report with mocked MLFlow data."""
        from configurable_agents.cli import cmd_profile_report
        from argparse import Namespace

        # Mock MLFlow run with timing metrics
        mock_run = MagicMock()
        mock_run.info.run_id = "test-run-id"
        mock_run.data.metrics = {
            "node_research_duration_ms": 150.0,
            "node_research_cost_usd": 0.05,
            "node_write_duration_ms": 50.0,
            "node_write_cost_usd": 0.01,
        }

        # Mock MLFlow client
        mock_client = MagicMock()
        mock_client.get_run.return_value = mock_run

        # Mock mlflow module
        mock_mlflow = MagicMock()
        mock_mlflow.get_tracking_uri.return_value = "file://./mlruns"
        mock_mlflow.set_tracking_uri = MagicMock()

        # Mock mlflow.tracking module
        mock_mlflow_tracking = MagicMock()
        mock_mlflow_tracking.MlflowClient = MagicMock(return_value=mock_client)

        # Patch sys.modules to inject mock mlflow at import time
        with patch.dict("sys.modules", {
            "mlflow": mock_mlflow,
            "mlflow.tracking": mock_mlflow_tracking,
            "mlflow.entities": MagicMock()
        }):
            args = Namespace(
                run_id="test-run-id",
                mlflow_uri=None,
                verbose=False
            )

            result = cmd_profile_report(args)
            assert result == 0

    def test_profile_report_highlights_slowest_node(self):
        """Verify slowest node is highlighted in output."""
        from configurable_agents.cli import cmd_profile_report
        from argparse import Namespace

        # Mock run with clear timing difference
        mock_run = MagicMock()
        mock_run.info.run_id = "test-run-id"
        mock_run.data.metrics = {
            "node_slow_node_duration_ms": 500.0,
            "node_slow_node_cost_usd": 0.10,
            "node_fast_node_duration_ms": 50.0,
            "node_fast_node_cost_usd": 0.01,
        }

        mock_client = MagicMock()
        mock_client.get_run.return_value = mock_run

        mock_mlflow = MagicMock()
        mock_mlflow.get_tracking_uri.return_value = "file://./mlruns"

        mock_mlflow_tracking = MagicMock()
        mock_mlflow_tracking.MlflowClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {
            "mlflow": mock_mlflow,
            "mlflow.tracking": mock_mlflow_tracking,
            "mlflow.entities": MagicMock()
        }):
            args = Namespace(run_id="test-run-id", mlflow_uri=None, verbose=False)
            result = cmd_profile_report(args)
            assert result == 0

    def test_profile_report_shows_bottlenecks(self):
        """Verify bottleneck section is displayed for nodes >50%."""
        from configurable_agents.cli import cmd_profile_report
        from argparse import Namespace

        # Mock run with bottleneck (>50% of total time)
        # Total = 600ms, slow_node = 500ms = 83.3%
        mock_run = MagicMock()
        mock_run.info.run_id = "test-run-id"
        mock_run.data.metrics = {
            "node_bottleneck_duration_ms": 500.0,
            "node_bottleneck_cost_usd": 0.10,
            "node_other_duration_ms": 100.0,
            "node_other_cost_usd": 0.02,
        }

        mock_client = MagicMock()
        mock_client.get_run.return_value = mock_run

        mock_mlflow = MagicMock()
        mock_mlflow.get_tracking_uri.return_value = "file://./mlruns"

        mock_mlflow_tracking = MagicMock()
        mock_mlflow_tracking.MlflowClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {
            "mlflow": mock_mlflow,
            "mlflow.tracking": mock_mlflow_tracking,
            "mlflow.entities": MagicMock()
        }):
            args = Namespace(run_id="test-run-id", mlflow_uri=None, verbose=False)
            result = cmd_profile_report(args)
            assert result == 0

    def test_profile_report_handles_no_profiling_data(self):
        """Verify graceful handling when no profiling data exists."""
        from configurable_agents.cli import cmd_profile_report
        from argparse import Namespace

        # Mock run without timing metrics
        mock_run = MagicMock()
        mock_run.info.run_id = "test-run-id"
        mock_run.data.metrics = {
            "total_cost_usd": 0.10,
            "total_tokens": 1000,
        }

        mock_client = MagicMock()
        mock_client.get_run.return_value = mock_run

        mock_mlflow = MagicMock()
        mock_mlflow.get_tracking_uri.return_value = "file://./mlruns"

        mock_mlflow_tracking = MagicMock()
        mock_mlflow_tracking.MlflowClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {
            "mlflow": mock_mlflow,
            "mlflow.tracking": mock_mlflow_tracking,
            "mlflow.entities": MagicMock()
        }):
            args = Namespace(run_id="test-run-id", mlflow_uri=None, verbose=False)
            result = cmd_profile_report(args)
            assert result == 0  # Should succeed, not fail


@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
class TestObservabilityStatusCommand:
    """Test observability status CLI command."""

    def test_observability_status_command_exists(self):
        """Verify observability status command is registered."""
        from configurable_agents.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["observability", "status"])

        assert args.command == "observability"
        assert args.observability_command == "status"

    def test_observability_status_shows_mlflow_connection(self):
        """Verify status shows MLFlow connection state."""
        from configurable_agents.cli import cmd_observability_status
        from argparse import Namespace

        # Mock MLFlow with successful connection
        mock_experiment = MagicMock()
        mock_experiment.name = "Default"
        mock_experiment.experiment_id = "0"

        mock_client = MagicMock()
        mock_client.search_experiments.return_value = [mock_experiment]
        mock_client.search_runs.return_value = []

        mock_mlflow = MagicMock()
        mock_mlflow.get_tracking_uri.return_value = "file://./mlruns"
        mock_mlflow.set_tracking_uri = MagicMock()

        mock_mlflow_tracking = MagicMock()
        mock_mlflow_tracking.MlflowClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {
            "mlflow": mock_mlflow,
            "mlflow.tracking": mock_mlflow_tracking,
            "mlflow.entities": MagicMock()
        }):
            args = Namespace(mlflow_uri=None, verbose=False)
            result = cmd_observability_status(args)
            assert result == 0

    def test_observability_status_shows_recent_runs(self):
        """Verify status shows recent run count."""
        from configurable_agents.cli import cmd_observability_status
        from argparse import Namespace
        from datetime import datetime

        # Mock experiment with recent runs
        mock_experiment = MagicMock()
        mock_experiment.name = "Default"
        mock_experiment.experiment_id = "0"

        mock_run = MagicMock()

        mock_client = MagicMock()
        mock_client.search_experiments.return_value = [mock_experiment]
        mock_client.search_runs.return_value = [mock_run]

        mock_mlflow = MagicMock()
        mock_mlflow.get_tracking_uri.return_value = "file://./mlruns"

        mock_mlflow_tracking = MagicMock()
        mock_mlflow_tracking.MlflowClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {
            "mlflow": mock_mlflow,
            "mlflow.tracking": mock_mlflow_tracking,
            "mlflow.entities": MagicMock()
        }):
            args = Namespace(mlflow_uri=None, verbose=False)
            result = cmd_observability_status(args)
            assert result == 0

    def test_observability_status_handles_disconnected(self):
        """Verify status handles disconnected MLFlow gracefully."""
        from configurable_agents.cli import cmd_observability_status
        from argparse import Namespace

        # Mock MLFlow with connection error
        mock_client = MagicMock()
        mock_client.search_experiments.side_effect = Exception("Connection refused")

        mock_mlflow = MagicMock()
        mock_mlflow.get_tracking_uri.return_value = "http://invalid:5000"

        mock_mlflow_tracking = MagicMock()
        mock_mlflow_tracking.MlflowClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {
            "mlflow": mock_mlflow,
            "mlflow.tracking": mock_mlflow_tracking,
            "mlflow.entities": MagicMock()
        }):
            args = Namespace(mlflow_uri="http://invalid:5000", verbose=False)
            result = cmd_observability_status(args)
            # Should still return 0 (graceful degradation)
            assert result == 0


@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
class TestObservabilityAliases:
    """Test observability subcommands as aliases to main commands."""

    def test_observability_cost_report_alias(self):
        """Verify observability cost-report is an alias to main command."""
        from configurable_agents.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["observability", "cost-report", "--experiment", "test"])

        assert args.command == "observability"
        assert args.observability_command == "cost-report"
        assert args.experiment == "test"

    def test_observability_profile_report_alias(self):
        """Verify observability profile-report is an alias to main command."""
        from configurable_agents.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["observability", "profile-report", "--run-id", "abc123"])

        assert args.command == "observability"
        assert args.observability_command == "profile-report"
        assert args.run_id == "abc123"


class TestEnableProfilingFlag:
    """Test --enable-profiling flag on run command."""

    def test_enable_profiling_flag_exists(self):
        """Verify --enable-profiling flag is available on run command."""
        from configurable_agents.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "workflow.yaml", "--enable-profiling"])

        assert args.command == "run"
        assert args.enable_profiling is True

    def test_enable_profiling_flag_default_false(self):
        """Verify --enable-profiling defaults to False."""
        from configurable_agents.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "workflow.yaml"])

        assert args.enable_profiling is False

    def test_enable_profiling_sets_environment_variable(self):
        """Verify --enable-profiling sets environment variable."""
        from configurable_agents.cli import cmd_run
        from argparse import Namespace
        from pathlib import Path
        import os

        # Create a dummy workflow file
        mock_config = {
            "flow": {
                "name": "test",
                "nodes": [
                    {"id": "test_node", "type": "llm", "model": "gpt-4o", "prompt": "test"}
                ]
            }
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("configurable_agents.cli.run_workflow", return_value={"result": "success"}):
                # Clean environment before test
                if "CONFIGURABLE_AGENTS_PROFILING" in os.environ:
                    del os.environ["CONFIGURABLE_AGENTS_PROFILING"]

                args = Namespace(
                    config_file="test.yaml",
                    input=None,
                    enable_profiling=True,
                    verbose=False
                )

                cmd_run(args)

                # Verify environment variable was set
                assert os.environ.get("CONFIGURABLE_AGENTS_PROFILING") == "1"

                # Clean up
                if "CONFIGURABLE_AGENTS_PROFILING" in os.environ:
                    del os.environ["CONFIGURABLE_AGENTS_PROFILING"]


@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich library not available")
class TestCLIIntegration:
    """Integration tests for CLI observability commands."""

    def test_full_cost_report_workflow(self):
        """Test full cost report generation workflow."""
        from configurable_agents.cli import cmd_cost_report
        from argparse import Namespace

        mock_report = {
            "experiment": "integration_test",
            "experiment_id": "1",
            "total_cost_usd": 1.50,
            "total_tokens": 30000,
            "by_provider": {
                "openai": {
                    "total_cost_usd": 0.75,
                    "total_tokens": 15000,
                    "run_count": 10,
                    "models": {
                        "gpt-4o": {"total_cost_usd": 0.50, "total_tokens": 10000, "run_count": 7},
                        "gpt-3.5-turbo": {"total_cost_usd": 0.25, "total_tokens": 5000, "run_count": 3}
                    }
                },
                "anthropic": {
                    "total_cost_usd": 0.75,
                    "total_tokens": 15000,
                    "run_count": 8,
                    "models": {
                        "claude-3-opus": {"total_cost_usd": 0.75, "total_tokens": 15000, "run_count": 8}
                    }
                }
            }
        }

        with patch("configurable_agents.cli.generate_cost_report", return_value=mock_report):
            args = Namespace(experiment="integration_test", mlflow_uri=None, verbose=False)
            result = cmd_cost_report(args)
            assert result == 0

    def test_full_profile_report_workflow(self):
        """Test full profile report generation workflow."""
        from configurable_agents.cli import cmd_profile_report
        from argparse import Namespace

        mock_run = MagicMock()
        mock_run.info.run_id = "integration-run-123"
        mock_run.data.metrics = {
            "node_agent_research_duration_ms": 300.0,
            "node_agent_research_cost_usd": 0.08,
            "node_agent_write_duration_ms": 200.0,
            "node_agent_write_cost_usd": 0.05,
            "node_summarize_duration_ms": 50.0,
            "node_summarize_cost_usd": 0.01,
        }

        mock_client = MagicMock()
        mock_client.get_run.return_value = mock_run

        mock_mlflow = MagicMock()
        mock_mlflow.get_tracking_uri.return_value = "file://./mlruns"

        mock_mlflow_tracking = MagicMock()
        mock_mlflow_tracking.MlflowClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {
            "mlflow": mock_mlflow,
            "mlflow.tracking": mock_mlflow_tracking,
            "mlflow.entities": MagicMock()
        }):
            args = Namespace(run_id="integration-run-123", mlflow_uri=None, verbose=False)
            result = cmd_profile_report(args)
            assert result == 0
