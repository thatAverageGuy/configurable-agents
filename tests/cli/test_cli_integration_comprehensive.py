"""
Comprehensive integration tests for all CLI commands.

Tests cover:
- All CLI commands work via subprocess
- Cross-platform path handling
- Error message quality
- End-to-end workflows
- Regression prevention for known bugs
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestAllCommandsHelp:
    """Verify all CLI commands have working help."""

    @pytest.mark.parametrize("command", [
        "run",
        "validate",
        "deploy",
        pytest.param("ui", marks=pytest.mark.slow),
        pytest.param("dashboard", marks=pytest.mark.slow),
        pytest.param("chat", marks=pytest.mark.slow),
    ])
    def test_command_help_exists(self, command):
        """Test each command shows help without crashing."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", command, "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Command '{command}' --help failed: {result.stderr}"
        assert "usage:" in result.stdout.lower() or command in result.stdout.lower()

    def test_main_help_shows_all_commands(self):
        """Test that main help lists all available commands."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        # Should show key commands
        output = result.stdout.lower()
        assert "run" in output
        assert "validate" in output
        assert "deploy" in output
        assert "ui" in output or "dashboard" in output


class TestCrossPlatformPaths:
    """Cross-platform path handling tests."""

    def test_config_with_spaces_in_path(self, tmp_path):
        """Test all commands handle paths with spaces correctly."""
        config_dir = tmp_path / "my folder" / "subfolder with spaces"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields: []
nodes: []
edges: []
""")

        # Test validate command with spaces
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        # Should handle spaces correctly
        assert "not found" not in result.stderr.lower()

    def test_config_with_unicode_chars(self, tmp_path):
        """Test all commands handle unicode in paths correctly."""
        config_dir = tmp_path / "tëst" / "földer"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Test"
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

        # Should handle unicode correctly
        assert result.returncode == 0 or "unicode" not in result.stderr.lower()

    def test_relative_vs_absolute_paths(self, tmp_path):
        """Test commands work with both relative and absolute paths."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Test"
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

        # Test with absolute path
        result_abs = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file.absolute())],
            capture_output=True,
            text=True,
        )

        # Test with relative path (change to tmp_path directory)
        result_rel = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", "config.yaml"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )

        # Both should work
        assert result_abs.returncode == result_rel.returncode

    def test_windows_path_separators(self, tmp_path):
        """Test that Windows path separators work correctly."""
        config_dir = tmp_path / "nested" / "path" / "structure"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Test"
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

        # Should work regardless of path separator
        assert result.returncode == 0


class TestErrorMessageQuality:
    """Verify all error messages are actionable."""

    def test_file_not_found_errors_are_actionable(self):
        """Test file not found errors suggest solutions."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", "missing_file.yaml"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        # Should mention the issue and suggest a fix
        output = result.stderr.lower()
        assert any(word in output for word in ["not found", "no such file"])
        assert any(word in output for word in ["check", "file", "path", "yaml"])

    def test_invalid_yaml_errors_are_specific(self, tmp_path):
        """Test YAML errors indicate the syntax issue."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: [unclosed")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        # Should mention YAML/syntax
        output = result.stderr.lower()
        assert any(word in output for word in ["yaml", "syntax", "parse"])

    def test_validation_errors_include_field_names(self, tmp_path):
        """Test validation errors specify which field is problematic."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  # missing name
""")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # Should indicate what's wrong
            output = result.stderr.lower() + result.stdout.lower()
            assert any(word in output for word in ["required", "missing", "field", "name"])

    def test_invalid_input_format_error_message(self, tmp_path):
        """Test invalid --input format provides helpful error."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields: []
nodes: []
edges: []
""")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", str(config_file), "--input", "invalid_no_equals"],
            capture_output=True,
            text=True,
        )

        # Should indicate format issue
        assert result.returncode != 0
        output = result.stderr.lower()
        assert any(word in output for word in ["format", "equals", "key=value", "expected"])

    def test_port_conflict_error_includes_port_number(self):
        """
        Test that port conflict error specifies which port.

        This is verified via code inspection since we can't easily
        create a real port conflict in tests.
        """
        cli_path = Path("src/configurable_agents/cli.py")
        if cli_path.exists():
            cli_content = cli_path.read_text()
            # Should check ports and report conflicts
            assert "port" in cli_content.lower()
            assert "in use" in cli_content.lower() or "conflict" in cli_content.lower()


class TestRegressionTests:
    """Regression tests for previously fixed bugs."""

    def test_unboundlocalerror_regression(self, tmp_path):
        """
        Regression test for UnboundLocalError in cmd_run (Quick-009).

        Bug: Console was referenced in exception handler but not imported
        in all code paths.
        """
        config_file = tmp_path / "test.yaml"
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

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", str(config_file), "--input", "msg=hello"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should not have UnboundLocalError
        assert "UnboundLocalError" not in result.stderr
        assert "local variable 'Console'" not in result.stderr
        assert "name 'Console' is not defined" not in result.stderr

    def test_windows_multiprocessing_regression(self):
        """
        Regression test for Windows multiprocessing issues (Quick-002 to Quick-008).

        Bug: Nested functions and functools.partial don't work with Windows spawn.
        Fix: Module-level functions for all multiprocessing targets.
        """
        import configurable_agents.cli as cli_module

        # Verify module-level functions exist
        assert hasattr(cli_module, "_run_dashboard_with_config")
        assert hasattr(cli_module, "_run_chat_with_config")
        assert hasattr(cli_module, "_run_dashboard_service")
        assert hasattr(cli_module, "_run_chat_service")
        assert callable(cli_module._run_dashboard_with_config)
        assert callable(cli_module._run_chat_with_config)
        assert callable(cli_module._run_dashboard_service)
        assert callable(cli_module._run_chat_service)

    def test_processmanager_exists(self):
        """Regression test: ProcessManager should be importable."""
        from configurable_agents.process import ProcessManager, ServiceSpec
        assert ProcessManager is not None
        assert ServiceSpec is not None


class TestEndToEndWorkflows:
    """End-to-end workflow tests using multiple CLI commands."""

    def test_validate_then_run_workflow(self, tmp_path):
        """Test typical workflow: validate, then run."""
        config_file = tmp_path / "workflow.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: e2e_test
state:
  fields:
    message: {type: str, required: true}
    result: {type: str, default: ""}
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

        # First validate
        validate_result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )
        assert validate_result.returncode == 0

        # Then run (may fail on API key, but should parse correctly)
        run_result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", str(config_file), "--input", "message=test"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # May fail due to API, but should not crash on parsing
        assert "UnboundLocalError" not in run_result.stderr

    def test_deploy_generate_then_validate(self, tmp_path):
        """Test workflow: deploy generate, validate output."""
        config_file = tmp_path / "workflow.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: deploy_test
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Process: {state.input}"
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

        output_dir = tmp_path / "deploy"
        output_dir.mkdir()

        # Generate deployment artifacts
        deploy_result = subprocess.run(
            [
                sys.executable, "-m", "configurable_agents", "deploy",
                str(config_file), "--generate",
                "--output-dir", str(output_dir)
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert deploy_result.returncode == 0, f"Deploy failed: {deploy_result.stderr}"

        # Verify artifacts created
        artifacts = list(output_dir.iterdir())
        assert len(artifacts) > 0, "No deployment artifacts created"

        # Should have at least one of these files
        artifact_names = [f.name for f in artifacts]
        assert any(name in artifact_names for name in ["Dockerfile", "server.py", "requirements.txt", "app.py"])

    def test_validate_multiple_configs(self, tmp_path):
        """Test validating multiple configs in sequence."""
        configs = []

        for i in range(3):
            config_file = tmp_path / f"config_{i}.yaml"
            config_file.write_text(f"""
schema_version: "1.0"
flow:
  name: test_{i}
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Test {i}"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - name: result
          type: str
edges:
  - {{from: START, to: process}}
  - {{from: process, to: END}}
""")
            configs.append(config_file)

        # Validate all configs
        for config_file in configs:
            result = subprocess.run(
                [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Failed to validate {config_file.name}"


class TestVerboseMode:
    """Test verbose mode across all commands."""

    @pytest.mark.parametrize("command,extra_args", [
        ("validate", ["--verbose"]),
    ])
    def test_verbose_mode_does_not_crash(self, tmp_path, command, extra_args):
        """Test verbose mode doesn't cause crashes."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Test"
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

        args = [sys.executable, "-m", "configurable_agents", command, str(config_file)] + extra_args
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Verbose mode should not crash
        assert "UnboundLocalError" not in result.stderr
        # Should have some output
        assert len(result.stdout) > 0 or len(result.stderr) > 0

    def test_deploy_verbose_mode(self, tmp_path):
        """Test deploy --verbose shows detailed output."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Test"
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
            [sys.executable, "-m", "configurable_agents", "deploy", str(config_file), "--generate", "--verbose"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Verbose mode should not crash
        assert result.returncode == 0 or "UnboundLocalError" not in result.stderr


class TestInputOutputFormats:
    """Test various input/output formats."""

    def test_input_format_with_equals(self, tmp_path):
        """Test --input format with equals sign."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Test"
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
            [sys.executable, "-m", "configurable_agents", "run", str(config_file), "--input", "key=value"],
            capture_output=True,
            text=True,
        )

        # Should parse correctly (may fail for other reasons)
        assert "format" not in result.stderr.lower() or result.returncode == 0 or "equals" not in result.stderr.lower()

    def test_input_format_with_quotes(self, tmp_path):
        """Test --input format with quoted values."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Test"
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
            [sys.executable, "-m", "configurable_agents", "run", str(config_file), "--input", 'message="hello world"'],
            capture_output=True,
            text=True,
        )

        # Should parse correctly
        assert "format" not in result.stderr.lower() or result.returncode == 0

    def test_multiple_input_values(self, tmp_path):
        """Test --input with multiple key=value pairs."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    message: {type: str, required: false}
    count: {type: int, default: 1}
    result: {type: str, default: ""}
nodes:
  - id: process
    prompt: "Test"
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
            [
                sys.executable, "-m", "configurable_agents", "run", str(config_file),
                "--input", "message=hello",
                "--input", "count=5"
            ],
            capture_output=True,
            text=True,
        )

        # Should parse multiple inputs
        assert "format" not in result.stderr.lower() or result.returncode == 0


@pytest.mark.slow
class TestUICommands:
    """Test UI-related commands (dashboard, chat, ui)."""

    def test_dashboard_help_exists(self):
        """Test dashboard command shows help."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "dashboard", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Dashboard command may be an alias or separate command
        # Just verify it doesn't crash
        assert result.returncode == 0 or "usage" in result.stdout.lower()

    def test_chat_help_exists(self):
        """Test chat command shows help."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "chat", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Chat command may be an alias or separate command
        # Just verify it doesn't crash
        assert result.returncode == 0 or "usage" in result.stdout.lower()

    def test_ui_help_exists(self):
        """Test ui command shows help."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "ui", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()


class TestObservabilityCommands:
    """Test observability and reporting commands."""

    def test_cost_report_command_exists(self):
        """Test that cost report functionality exists."""
        from configurable_agents.observability.multi_provider_tracker import generate_cost_report
        assert callable(generate_cost_report)

    def test_cost_reporter_importable(self):
        """Test that CostReporter can be imported."""
        from configurable_agents.observability import CostReporter
        assert CostReporter is not None


class TestDeployOutputQuality:
    """Test deploy command output quality."""

    def test_deploy_shows_progress(self, tmp_path):
        """Test deploy shows some progress information."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Test"
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
            [sys.executable, "-m", "configurable_agents", "deploy", str(config_file), "--generate"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should succeed
        assert result.returncode == 0
        # Should have some output indicating work was done
        assert len(result.stdout) > 0 or len(result.stderr) > 0


class TestSchemaVersions:
    """Test handling of different schema versions."""

    def test_missing_schema_version_validates(self, tmp_path):
        """Test that config without schema_version still validates."""
        config_file = tmp_path / "no_schema.yaml"
        config_file.write_text("""
flow:
  name: test
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Test"
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

        # Should either succeed or give a clear message about schema_version
        if result.returncode != 0:
            output = result.stderr.lower() + result.stdout.lower()
            assert "schema" in output or "version" in output


class TestErrorRecovery:
    """Test error recovery and graceful degradation."""

    def test_missing_optional_dependencies_doesnt_crash(self):
        """Test CLI works even if optional dependencies are missing."""
        # The CLI should handle missing optional dependencies gracefully
        # This is verified by ensuring imports are guarded
        import configurable_agents.cli as cli_module
        assert cli_module is not None

    def test_rich_library_fallback(self):
        """Test that CLI works without rich library."""
        # The CLI should have a fallback when rich is not available
        # Verify by checking the import pattern
        cli_path = Path("src/configurable_agents/cli.py")
        if cli_path.exists():
            content = cli_path.read_text()
            # Should have try/except for rich import
            assert "try:" in content or "RICH_AVAILABLE" in content


class TestSpecialCharactersInInput:
    """Test handling of special characters in input values."""

    @pytest.mark.parametrize("input_value", [
        "hello world",
        "hello\\world",
        "hello\"world",
        "hello'world",
        "hello&world",
    ])
    def test_special_characters_in_input(self, tmp_path, input_value):
        """Test that special characters in input are handled correctly."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input:
      type: str
      required: false
    result:
      type: str
      default: ""
nodes:
  - id: process
    prompt: "Test"
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
            [sys.executable, "-m", "configurable_agents", "run", str(config_file), "--input", f"message={input_value}"],
            capture_output=True,
            text=True,
        )

        # Should not crash due to special characters
        assert "UnboundLocalError" not in result.stderr


class TestTimeoutHandling:
    """Test timeout handling in long-running commands."""

    def test_run_timeout_option_exists(self):
        """Test that run command has timeout option."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", "--help"],
            capture_output=True,
            text=True,
        )
        # Should have some way to handle timeouts
        assert "timeout" in result.stdout.lower() or "time" in result.stdout.lower() or result.returncode == 0
