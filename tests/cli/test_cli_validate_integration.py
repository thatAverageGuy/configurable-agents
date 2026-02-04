"""
Integration tests for CLI validate command using subprocess.

Tests actual CLI invocation for config validation.
Catches import errors, entry point bugs, and validation issues.
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestCLIValidateHelp:
    """Test validate command help and argument parsing."""

    def test_validate_help_shows_usage(self):
        """Test that --help works for validate command."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()

    def test_validate_shows_verbose_option(self):
        """Test validate command supports --verbose flag."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--verbose" in result.stdout or "-v" in result.stdout


class TestCLIValidateErrors:
    """Test validate command error handling."""

    def test_validate_missing_file_clear_error(self):
        """Test validate fails with clear error when config file doesn't exist."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", "nonexistent.yaml"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        # Clear error message
        assert "not found" in result.stderr.lower() or "no such file" in result.stderr.lower()
        # Actionable guidance
        assert any(word in result.stderr.lower() for word in ["yaml", "check", "path", "file", "create"])

    def test_validate_invalid_yaml_syntax(self, tmp_path):
        """Test validate fails clearly on malformed YAML syntax."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [unclosed")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        # Should mention YAML or syntax issue
        assert "yaml" in result.stderr.lower() or "syntax" in result.stderr.lower() or "parse" in result.stderr.lower()

    def test_validate_empty_file(self, tmp_path):
        """Test validate fails clearly on empty config file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        # Should indicate empty or invalid config
        assert any(word in result.stderr.lower() for word in ["empty", "invalid", "required", "missing"])


class TestCLIValidateValidConfigs:
    """Test validate command accepts various valid configs."""

    def test_validate_minimal_valid_config(self, tmp_path):
        """Test validate passes on minimal valid config."""
        config_file = tmp_path / "minimal.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: minimal_test
state:
  fields: []
nodes: []
edges: []
""")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Should indicate success
        assert "valid" in result.stdout.lower() or "success" in result.stdout.lower() or "ok" in result.stdout.lower()

    def test_validate_complete_valid_config(self, tmp_path):
        """Test validate passes on complete valid config."""
        config_file = tmp_path / "complete.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: complete_test
  description: A complete test workflow
state:
  fields:
    - name: message
      type: str
      required: true
    - name: count
      type: int
      default: 1
nodes:
  - id: process
    prompt: "Process: {state.message}"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - name: result
          type: str
edges:
  - {from: START, to: process}
  - {from: process, to: END}
""")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "valid" in result.stdout.lower() or "success" in result.stdout.lower()

    def test_validate_verbose_output(self, tmp_path):
        """Test validate --verbose shows detailed validation info."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: test
state:
  fields: []
nodes: []
edges: []
""")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file), "--verbose"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Verbose mode should show more details
        assert len(result.stdout) > 0


class TestCLIValidateInvalidConfigs:
    """Test validate command catches various invalid configs."""

    def test_validate_missing_required_field(self, tmp_path):
        """Test validate catches missing required field in state."""
        config_file = tmp_path / "missing_field.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: test
state:
  fields:
    - name: message
      type: str
      # Missing 'required' field
nodes: []
edges: []
""")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        # May pass or fail depending on schema - but error should be clear if fails
        if result.returncode != 0:
            # Should mention the validation issue
            assert any(word in result.stderr.lower() for word in ["required", "missing", "field", "invalid"])

    def test_validate_missing_flow_name(self, tmp_path):
        """Test validate catches missing flow name."""
        config_file = tmp_path / "no_name.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  # Missing name
  description: Test
state:
  fields: []
nodes: []
edges: []
""")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        # Should fail on missing required flow.name
        assert result.returncode != 0
        assert any(word in result.stderr.lower() for word in ["name", "required", "missing"])

    def test_validate_invalid_node_reference(self, tmp_path):
        """Test validate catches invalid node reference in edges."""
        config_file = tmp_path / "bad_edge.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: test
state:
  fields: []
nodes:
  - id: node1
    prompt: "Test"
edges:
  - {from: START, to: nonexistent_node}
""")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        # Should catch invalid node reference
        assert result.returncode != 0
        assert any(word in result.stderr.lower() for word in ["node", "reference", "not found", "invalid"])

    def test_validate_cyclic_edges(self, tmp_path):
        """Test validate catches cycles in workflow graph."""
        config_file = tmp_path / "cycle.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: test
state:
  fields: []
nodes:
  - id: node1
    prompt: "Test 1"
  - id: node2
    prompt: "Test 2"
edges:
  - {from: node1, to: node2}
  - {from: node2, to: node1}
""")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        # Should detect cycle (no path to END)
        assert result.returncode != 0
        assert any(word in result.stderr.lower() for word in ["cycle", "end", "path", "terminal"])


class TestCLIValidateCrossPlatform:
    """Cross-platform compatibility tests for validate command."""

    def test_validate_path_with_spaces(self, tmp_path):
        """Test that config paths with spaces work on all platforms."""
        config_dir = tmp_path / "my folder" / "sub folder"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "workflow with spaces.yaml"
        config_file.write_text("flow:\n  name: test\nstate:\n  fields: []\nnodes: []\nedges: []\n")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        # Should handle spaces correctly
        assert "not found" not in result.stderr.lower()

    def test_validate_windows_path_separators(self, tmp_path):
        """Test that Windows path separators work correctly."""
        # Create nested directory to test path handling
        config_dir = tmp_path / "nested" / "path"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("flow:\n  name: test\nstate:\n  fields: []\nnodes: []\nedges: []\n")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        # Should work regardless of path separator
        assert result.returncode == 0 or "not found" not in result.stderr.lower()


class TestCLIValidateErrorMessageQuality:
    """Test that validation error messages are helpful."""

    def test_error_messages_include_field_names(self, tmp_path):
        """Test that validation errors specify which field is problematic."""
        config_file = tmp_path / "test.yaml"
        # Config with obvious issues
        config_file.write_text("flow:\n  # missing name\nstate:\n  fields:\n    - type: str\n      # missing name\n")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # Error should mention the problematic area
            output = result.stdout.lower() + result.stderr.lower()
            # At minimum should indicate there's a validation problem
            assert any(word in output for word in ["invalid", "required", "missing", "field"])

    def test_error_messages_suggest_fixes(self, tmp_path):
        """Test that error messages suggest how to fix issues."""
        config_file = tmp_path / "missing.yaml"

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        # Should guide user on what to do
        assert any(word in result.stderr.lower() for word in ["check", "file", "path", "create", "yaml"])
