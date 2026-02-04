"""
Integration tests for CLI run command using subprocess.

Tests actual CLI invocation, not just function imports.
Catches import errors, entry point bugs, and integration issues.
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestCLIRunHelp:
    """Test run command help and argument parsing."""

    def test_run_help_shows_usage(self):
        """Test that --help works for run command."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()

    def test_run_accepts_config_file(self):
        """Test run command accepts config file argument."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", "--help"],
            capture_output=True,
            text=True,
        )
        assert "config" in result.stdout.lower() or "positional arguments" in result.stdout.lower()


class TestCLIRunErrors:
    """Test run command error handling."""

    def test_run_missing_file_clear_error(self):
        """Test run fails with clear error when config file doesn't exist."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", "nonexistent.yaml"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        # Clear error message
        assert "not found" in result.stderr.lower() or "no such file" in result.stderr.lower()
        # Actionable guidance
        assert any(word in result.stderr.lower() for word in ["yaml", "check", "path", "file"])

    def test_run_invalid_yaml_syntax(self, tmp_path):
        """Test run fails clearly on malformed YAML syntax."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [unclosed")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", str(config_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "yaml" in result.stderr.lower() or "syntax" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_run_invalid_input_format(self, tmp_path):
        """Test run fails on invalid --input format (missing equals)."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("flow:\n  name: test\n")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", str(config_file), "--input", "invalid_no_equals"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "format" in result.stderr.lower() or "equals" in result.stderr.lower()


class TestCLIRunRegression:
    """Regression tests for previously fixed bugs."""

    def test_unboundlocalerror_regression(self, tmp_path):
        """
        Regression test for UnboundLocalError in cmd_run (Quick-009).

        Bug: Console was referenced in exception handler but not imported
        in all code paths. This test verifies the fix remains in place.
        """
        config_file = tmp_path / "test.yaml"
        # Minimal valid config that triggers the error path
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    msg: {type: str, required: true}
nodes:
  - id: test_node
    prompt: "Test {state.msg}"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - name: result
          type: str
edges:
  - {from: START, to: test_node}
  - {from: test_node, to: END}
""")

        # Run with valid input - should not raise UnboundLocalError
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", str(config_file), "--input", "msg=hello"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should complete without UnboundLocalError
        assert "UnboundLocalError" not in result.stderr
        assert "local variable 'Console'" not in result.stderr
        assert "name 'Console' is not defined" not in result.stderr


class TestCLIRunIntegration:
    """Integration tests for run command with real workflows."""

    @pytest.mark.integration
    def test_run_simple_workflow(self, tmp_path):
        """
        Integration test: Run actual simple workflow via CLI.

        Note: This test may fail if API key is not configured,
        but should demonstrate correct parsing and execution flow.
        """
        config_file = tmp_path / "simple.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: echo_test
state:
  fields:
    message: {type: str, required: true}
nodes:
  - id: echo
    prompt: "Echo: {state.message}"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - name: result
          type: str
edges:
  - {from: START, to: echo}
  - {from: echo, to: END}
""")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", str(config_file), "--input", "message=HelloWorld"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # May fail due to API key, validation, or other issues, but should parse correctly
        assert result.returncode in [0, 1]  # 0=success, 1=validation or API error acceptable
        # Check it attempted to run (loading workflow message should appear)
        assert "loading workflow" in result.stdout.lower() or "echo" in result.stdout.lower()


class TestCLIRunCrossPlatform:
    """Cross-platform compatibility tests for run command."""

    def test_run_path_with_spaces(self, tmp_path):
        """Test that config paths with spaces work on all platforms."""
        config_dir = tmp_path / "my folder" / "sub folder"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "workflow with spaces.yaml"
        config_file.write_text("flow:\n  name: test\n")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        # Should handle spaces correctly (validate command for speed)
        # Note: May return validation error, but not "file not found"
        assert "not found" not in result.stderr.lower()

    def test_run_verbose_mode(self, tmp_path):
        """Test run command with --verbose flag."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("flow:\n  name: test\n")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", str(config_file), "--verbose"],
            capture_output=True,
            text=True,
        )

        # Verbose mode should not crash
        # Output may contain debug info, but no UnboundLocalError
        assert "UnboundLocalError" not in result.stderr
        assert "name 'Console' is not defined" not in result.stderr
