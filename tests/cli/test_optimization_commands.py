"""Tests for CLI optimization commands.

Tests the optimization command group including evaluate, apply-optimized,
and ab-test subcommands.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest
from rich.console import Console

from configurable_agents.cli import (
    cmd_optimization_ab_test,
    cmd_optimization_apply,
    cmd_optimization_evaluate,
    create_parser,
)

# Import for type checking
import configurable_agents.cli as cli_module


class TestOptimizationEvaluate:
    """Tests for the optimization evaluate command."""

    def test_evaluate_parser_creation(self):
        """Verify evaluate subcommand parser is configured correctly."""
        parser = create_parser()
        args = parser.parse_args([
            "optimization", "evaluate",
            "--experiment", "test_experiment",
            "--metric", "cost_usd_avg",
        ])
        assert args.command == "optimization"
        assert args.optimization_command == "evaluate"
        assert args.experiment == "test_experiment"
        assert args.metric == "cost_usd_avg"

    def test_evaluate_requires_experiment(self):
        """Verify experiment argument is required."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["optimization", "evaluate"])

    @patch("configurable_agents.cli.RICH_AVAILABLE", True)
    def test_evaluate_success(self):
        """Test successful evaluation command execution."""
        # Create mock objects
        mock_evaluator = MagicMock()
        mock_comparison = MagicMock()
        mock_comparison.experiment_name = "test_experiment"
        mock_comparison.best_variant = "variant_a"
        mock_evaluator.compare_variants.return_value = mock_comparison

        mock_console = MagicMock()

        # Patch at the import location in cli.py
        with patch("configurable_agents.optimization.ExperimentEvaluator", return_value=mock_evaluator), \
             patch("configurable_agents.optimization.format_comparison_table", return_value="Formatted Table"), \
             patch("rich.console.Console", return_value=mock_console):
            # Create args
            args = Mock(
                experiment="test_experiment",
                metric="cost_usd_avg",
                mlflow_uri=None,
                verbose=False,
            )

            # Execute
            result = cmd_optimization_evaluate(args)

            # Verify
            assert result == 0
            mock_evaluator.compare_variants.assert_called_once_with("test_experiment", "cost_usd_avg")

    @patch("configurable_agents.cli.RICH_AVAILABLE", False)
    def test_evaluate_requires_rich(self):
        """Test evaluate command requires rich library."""
        args = Mock(
            experiment="test_experiment",
            metric="cost_usd_avg",
            mlflow_uri=None,
            verbose=False,
        )
        result = cmd_optimization_evaluate(args)
        assert result == 1

    @patch("configurable_agents.cli.RICH_AVAILABLE", True)
    def test_evaluate_mlflow_not_available(self):
        """Test evaluate command handles MLFlow not available."""
        with patch("configurable_agents.optimization.evaluator.ExperimentEvaluator", side_effect=RuntimeError("MLFlow not installed")):
            args = Mock(
                experiment="test_experiment",
                metric="cost_usd_avg",
                mlflow_uri=None,
                verbose=False,
            )
            result = cmd_optimization_evaluate(args)
            assert result == 1


class TestOptimizationApply:
    """Tests for the optimization apply-optimized command."""

    def test_apply_parser_creation(self):
        """Verify apply-optimized subcommand parser is configured correctly."""
        parser = create_parser()
        args = parser.parse_args([
            "optimization", "apply-optimized",
            "--experiment", "test_experiment",
            "--workflow", "workflow.yaml",
            "--variant", "variant_a",
            "--dry-run",
        ])
        assert args.command == "optimization"
        assert args.optimization_command == "apply-optimized"
        assert args.experiment == "test_experiment"
        assert args.workflow == "workflow.yaml"
        assert args.variant == "variant_a"
        assert args.dry_run is True

    def test_apply_requires_experiment_and_workflow(self):
        """Verify experiment and workflow arguments are required."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["optimization", "apply-optimized"])

    @patch("configurable_agents.optimization.find_best_variant")
    @patch("configurable_agents.optimization.apply_prompt_to_workflow")
    def test_apply_success(self, mock_apply, mock_find_best, tmp_path):
        """Test successful apply command execution."""
        # Create a workflow file so it exists
        workflow_file = tmp_path / "workflow.yaml"
        workflow_file.write_text("flow:\n  name: test\n")

        # Setup mocks
        mock_find_best.return_value = {
            "variant_name": "variant_a",
            "prompt": "Optimized prompt text",
            "cost_usd_avg": 0.001,
        }
        mock_apply.return_value = str(workflow_file) + ".backup"

        args = Mock(
            experiment="test_experiment",
            variant=None,
            workflow=str(workflow_file),
            dry_run=False,
            mlflow_uri=None,
            verbose=False,
        )

        # Execute
        result = cmd_optimization_apply(args)

        # Verify
        assert result == 0

    def test_apply_no_variants_found(self):
        """Test apply command when no variants found."""
        mock_find_best = MagicMock(return_value=None)
        with patch("configurable_agents.optimization.find_best_variant", mock_find_best):
            args = Mock(
                experiment="test_experiment",
                variant=None,
                workflow="workflow.yaml",
                dry_run=False,
                mlflow_uri=None,
                verbose=False,
            )
            result = cmd_optimization_apply(args)
            assert result == 1

    def test_apply_dry_run(self):
        """Test apply command with dry-run flag."""
        mock_find_best = MagicMock(return_value={
            "variant_name": "variant_a",
            "prompt": "Optimized prompt text" * 20,  # Long prompt
            "cost_usd_avg": 0.001,
        })
        with patch("configurable_agents.optimization.find_best_variant", mock_find_best):
            args = Mock(
                experiment="test_experiment",
                variant=None,
                workflow="workflow.yaml",
                dry_run=True,
                mlflow_uri=None,
                verbose=False,
            )
            result = cmd_optimization_apply(args)
            assert result == 0

    @patch("configurable_agents.optimization.find_best_variant")
    @patch("configurable_agents.optimization.ab_test.apply_prompt_to_workflow")
    def test_apply_file_not_found(self, mock_apply, mock_find_best):
        """Test apply command when workflow file not found."""
        mock_find_best.return_value = {
            "variant_name": "variant_a",
            "prompt": "Optimized prompt",
        }
        mock_apply.side_effect = FileNotFoundError("File not found")
        args = Mock(
            experiment="test_experiment",
            variant=None,
            workflow="nonexistent.yaml",
            dry_run=False,
            mlflow_uri=None,
            verbose=False,
        )
        result = cmd_optimization_apply(args)
        assert result == 1

    @patch("configurable_agents.optimization.find_best_variant")
    @patch("configurable_agents.optimization.apply_prompt_to_workflow")
    def test_apply_specific_variant(self, mock_apply, mock_find_best, tmp_path):
        """Test apply command with specific variant selection."""
        # Create a workflow file so it exists
        workflow_file = tmp_path / "workflow.yaml"
        workflow_file.write_text("flow:\n  name: test\n")

        mock_find_best.return_value = {
            "variant_name": "variant_a",
            "prompt": "Variant A prompt",
        }
        mock_apply.return_value = str(workflow_file) + ".backup"

        args = Mock(
            experiment="test_experiment",
            variant="variant_b",
            workflow=str(workflow_file),
            dry_run=False,
            mlflow_uri=None,
            verbose=False,
        )
        result = cmd_optimization_apply(args)
        assert result == 0


class TestOptimizationABTest:
    """Tests for the optimization ab-test command."""

    def test_ab_test_parser_creation(self):
        """Verify ab-test subcommand parser is configured correctly."""
        parser = create_parser()
        args = parser.parse_args([
            "optimization", "ab-test",
            "workflow.yaml",
            "--input", "topic=AI",
        ])
        assert args.command == "optimization"
        assert args.optimization_command == "ab-test"
        assert args.config_file == "workflow.yaml"
        assert args.input == ["topic=AI"]

    def test_ab_test_requires_config_file(self):
        """Verify config file argument is required."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["optimization", "ab-test"])

    @patch("configurable_agents.cli.Path.exists", return_value=False)
    def test_ab_test_config_not_found(self, mock_exists):
        """Test ab-test command when config file not found."""
        args = Mock(
            config_file="nonexistent.yaml",
            input=None,
            verbose=False,
        )
        result = cmd_optimization_ab_test(args)
        assert result == 1

    @patch("configurable_agents.cli.Path.exists", return_value=True)
    @patch("configurable_agents.config.parse_config_file")
    @patch("configurable_agents.config.WorkflowConfig")
    def test_ab_test_not_configured(self, mock_config_class, mock_parse, mock_exists):
        """Test ab-test command when A/B test not configured."""
        from configurable_agents.config.schema import GlobalConfig
        # Create a config without ab_test section
        mock_config = MagicMock(spec=GlobalConfig)
        mock_config.config = None
        mock_config_class.return_value = mock_config
        args = Mock(
            config_file="workflow.yaml",
            input=None,
            verbose=False,
        )
        result = cmd_optimization_ab_test(args)
        assert result == 1

    @patch("configurable_agents.cli.Path.exists", return_value=True)
    @patch("configurable_agents.config.parse_config_file")
    @patch("configurable_agents.config.WorkflowConfig")
    def test_ab_test_disabled(self, mock_config_class, mock_parse, mock_exists):
        """Test ab-test command when A/B test is disabled."""
        from configurable_agents.config.schema import GlobalConfig, ABTestConfig
        mock_ab_config = MagicMock(spec=ABTestConfig)
        mock_ab_config.enabled = False
        mock_config = MagicMock(spec=GlobalConfig)
        mock_config.config = MagicMock()
        mock_config.config.ab_test = mock_ab_config
        mock_config_class.return_value = mock_config
        args = Mock(
            config_file="workflow.yaml",
            input=None,
            verbose=False,
        )
        result = cmd_optimization_ab_test(args)
        assert result == 1

    @patch("configurable_agents.cli.Path.exists", return_value=True)
    @patch("configurable_agents.config.parse_config_file")
    @patch("configurable_agents.config.WorkflowConfig")
    @patch("configurable_agents.optimization.ab_test.ABTestRunner")
    @patch("configurable_agents.optimization.ABTestConfig")
    @patch("configurable_agents.optimization.VariantConfig")
    @pytest.mark.skipif(sys.platform == "win32", reason="MLWin filesystem backend fails on Windows in CI")
    def test_ab_test_successful_run(
        self, mock_variant_config, mock_ab_test_config, mock_runner_class,
        mock_config_class, mock_parse, mock_exists, tmp_path
    ):
        """Test successful A/B test execution."""
        from configurable_agents.config.schema import GlobalConfig, ABTestConfig

        # Create a valid workflow file (outputs must match state fields)
        workflow_file = tmp_path / "workflow.yaml"
        workflow_file.write_text("""
schema_version: "1.0"
flow:
  name: test_workflow
state:
  fields:
    message:
      type: str
      required: false
      default: "test"
    result:
      type: str
      required: false
      default: ""
nodes:
  - id: writer
    prompt: "Write: {state.message}"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - name: result
          type: str
edges:
  - {from: START, to: writer}
  - {from: writer, to: END}
""")

        # Setup mocks
        mock_variant = MagicMock()
        mock_variant.name = "variant_a"
        mock_variant.prompt = "Test prompt"
        mock_variant.config_overrides = None
        mock_variant.node_id = "writer"
        mock_variant_config.return_value = mock_variant

        mock_ab_config = MagicMock(spec=ABTestConfig)
        mock_ab_config.enabled = True
        mock_ab_config.experiment = "test_experiment"
        mock_ab_config.run_count = 3
        mock_ab_config.variants = [mock_variant]

        mock_config = MagicMock(spec=GlobalConfig)
        mock_config.config = MagicMock()
        mock_config.config.ab_test = mock_ab_config
        mock_config_class.return_value = mock_config

        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.summary = "Test Summary"
        mock_result.best_variant = "variant_a"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        args = Mock(
            config_file=str(workflow_file),
            input=None,
            verbose=False,
        )
        result = cmd_optimization_ab_test(args)
        assert result == 0
        mock_runner.run.assert_called_once()


class TestOptimizationCLIIntegration:
    """Integration tests for optimization CLI commands."""

    def test_optimization_command_group_exists(self):
        """Verify optimization command group is registered."""
        parser = create_parser()
        # Parse optimization subcommand
        args = parser.parse_args(["optimization", "evaluate", "--experiment", "test"])
        assert args.command == "optimization"

    def test_optimization_subcommands_registered(self):
        """Verify all optimization subcommands are registered."""
        parser = create_parser()
        subcommands = ["evaluate", "apply-optimized", "ab-test"]

        for subcmd in subcommands:
            if subcmd == "ab-test":
                args = parser.parse_args(["optimization", subcmd, "test.yaml"])
            elif subcmd == "apply-optimized":
                args = parser.parse_args(["optimization", subcmd, "--experiment", "test", "--workflow", "test.yaml"])
            else:  # evaluate
                args = parser.parse_args(["optimization", subcmd, "--experiment", "test"])
            # Just verify parsing works
            assert args.command == "optimization"
            assert args.optimization_command == subcmd

    def test_mlflow_uri_argument_consistency(self):
        """Test mlflow-uri argument is available across commands."""
        parser = create_parser()

        # Test evaluate accepts mlflow-uri
        args = parser.parse_args([
            "optimization", "evaluate",
            "--experiment", "test",
            "--mlflow-uri", "sqlite:///mlflow.db",
        ])
        assert args.mlflow_uri == "sqlite:///mlflow.db"

        # Test apply-optimized accepts mlflow-uri
        args = parser.parse_args([
            "optimization", "apply-optimized",
            "--experiment", "test",
            "--workflow", "test.yaml",
            "--mlflow-uri", "file://./mlruns",
        ])
        assert args.mlflow_uri == "file://./mlruns"

    def test_verbose_flag_available(self):
        """Test verbose flag is available on all commands."""
        parser = create_parser()

        # Test evaluate with verbose
        args = parser.parse_args([
            "optimization", "evaluate",
            "--experiment", "test",
            "-v",
        ])
        assert args.verbose is True

        # Test apply-optimized with verbose
        args = parser.parse_args([
            "optimization", "apply-optimized",
            "--experiment", "test",
            "--workflow", "test.yaml",
            "-v",
        ])
        assert args.verbose is True

        # Test ab-test with verbose
        args = parser.parse_args([
            "optimization", "ab-test",
            "test.yaml",
            "-v",
        ])
        assert args.verbose is True


class TestOptimizationErrorHandling:
    """Tests for error handling in optimization commands."""

    @patch("configurable_agents.cli.RICH_AVAILABLE", True)
    def test_evaluate_handles_generic_exception(self):
        """Test evaluate command handles generic exceptions."""
        with patch("configurable_agents.optimization.evaluator.ExperimentEvaluator", side_effect=Exception("Unexpected error")):
            args = Mock(
                experiment="test_experiment",
                metric="cost_usd_avg",
                mlflow_uri=None,
                verbose=False,
            )
            result = cmd_optimization_evaluate(args)
            assert result == 1

    @patch("configurable_agents.optimization.find_best_variant")
    def test_apply_handles_generic_exception(self, mock_find_best):
        """Test apply command handles generic exceptions."""
        mock_find_best.side_effect = Exception("Unexpected error")
        args = Mock(
            experiment="test_experiment",
            variant=None,
            workflow="workflow.yaml",
            dry_run=False,
            mlflow_uri=None,
            verbose=False,
        )
        result = cmd_optimization_apply(args)
        assert result == 1

    @patch("configurable_agents.cli.Path.exists", return_value=True)
    @patch("configurable_agents.config.parse_config_file")
    @patch("configurable_agents.config.WorkflowConfig")
    def test_ab_test_handles_load_error(self, mock_config_class, mock_parse, mock_exists):
        """Test ab-test command handles config load errors."""
        from configurable_agents.runtime import ConfigLoadError
        mock_parse.side_effect = ConfigLoadError("Invalid YAML")
        args = Mock(
            config_file="invalid.yaml",
            input=None,
            verbose=False,
        )
        result = cmd_optimization_ab_test(args)
        assert result == 1
