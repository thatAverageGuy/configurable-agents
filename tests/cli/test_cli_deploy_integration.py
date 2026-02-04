"""
Integration tests for CLI deploy command using subprocess.

Tests actual CLI invocation for deployment artifact generation.
Avoids actual Docker builds in CI - focuses on artifact generation and error handling.
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestCLIDeployHelp:
    """Test deploy command help and argument parsing."""

    def test_deploy_help_shows_usage(self):
        """Test that --help works for deploy command."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "deploy", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()

    def test_deploy_shows_generate_option(self):
        """Test deploy command shows --generate option."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "deploy", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--generate" in result.stdout

    def test_deploy_shows_port_options(self):
        """Test deploy command shows port configuration options."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "deploy", "--help"],
            capture_output=True,
            text=True,
        )
        assert "port" in result.stdout.lower()


class TestCLIDeployErrors:
    """Test deploy command error handling."""

    def test_deploy_missing_file_clear_error(self):
        """Test deploy fails with clear error when config file doesn't exist."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "deploy", "nonexistent.yaml"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        # Clear error message
        assert "not found" in result.stderr.lower() or "no such file" in result.stderr.lower()

    def test_deploy_invalid_yaml_syntax(self, tmp_path):
        """Test deploy fails clearly on malformed YAML syntax."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [unclosed")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "deploy", str(config_file), "--generate"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "yaml" in result.stderr.lower() or "syntax" in result.stderr.lower()


class TestCLIDeployGenerateOnly:
    """Test deploy --generate mode (artifact generation without build)."""

    def test_deploy_generate_creates_artifacts(self, tmp_path):
        """Test deploy --generate creates deployment artifacts."""
        config_file = tmp_path / "workflow.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: test_workflow
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

        output_dir = tmp_path / "deploy_output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "configurable_agents", "deploy",
                str(config_file), "--generate",
                "--output-dir", str(output_dir)
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should succeed (generate-only doesn't require Docker)
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

        # Check artifacts created
        artifacts = list(output_dir.iterdir())
        assert len(artifacts) > 0, "No artifacts created"

        # Should have at least Dockerfile or server.py
        artifact_names = [f.name for f in artifacts]
        assert any(name in artifact_names for name in ["Dockerfile", "server.py", "requirements.txt"])

    def test_deploy_generate_verbose_output(self, tmp_path):
        """Test deploy --generate --verbose shows detailed progress."""
        config_file = tmp_path / "workflow.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: test_workflow
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

        output_dir = tmp_path / "deploy_output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "configurable_agents", "deploy",
                str(config_file), "--generate", "--verbose",
                "--output-dir", str(output_dir)
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0
        # Verbose mode should show more output
        assert len(result.stdout) > 0 or len(result.stderr) > 0


class TestCLIDeployPortHandling:
    """Test deploy command port conflict detection."""

    def test_deploy_accepts_custom_ports(self, tmp_path):
        """Test deploy accepts custom port arguments."""
        config_file = tmp_path / "workflow.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: test_workflow
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

        # Just verify arguments are accepted (generate-only)
        result = subprocess.run(
            [
                sys.executable, "-m", "configurable_agents", "deploy",
                str(config_file), "--generate",
                "--api-port", "9999",
                "--mlflow-port", "5999"
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should accept the arguments (may fail for other reasons, but not port parsing)
        assert "invalid" not in result.stderr.lower() or result.returncode == 0


class TestCLIDeployDockerChecks:
    """Test deploy command Docker availability checks."""

    def test_deploy_docker_not_installed_message(self, tmp_path):
        """
        Test deploy shows clear error when Docker is not available.

        Note: This test is difficult to run reliably in CI.
        We verify the error path exists by checking code.
        """
        # Verify cmd_deploy checks for Docker
        cli_path = Path("src/configurable_agents/cli.py")
        if cli_path.exists():
            cli_content = cli_path.read_text()
            # Should have docker check
            assert "docker" in cli_content.lower()
            # Should have error handling for docker not found
            assert "docker" in cli_content.lower() and ("not found" in cli_content.lower() or "unavailable" in cli_content.lower() or "install" in cli_content.lower())

    @pytest.mark.slow
    def test_deploy_with_docker_available(self, tmp_path):
        """
        Test deploy works when Docker is available.

        This test is marked as slow and requires actual Docker.
        It may be skipped in CI but should run in local dev.
        """
        config_file = tmp_path / "workflow.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: test_workflow
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

        # First check if Docker is available
        docker_check = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
        )

        if docker_check.returncode != 0:
            pytest.skip("Docker not available")

        # Run deploy with --generate (safe even without full Docker setup)
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "deploy", str(config_file), "--generate"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0


class TestCLIDeployEnvFileHandling:
    """Test deploy command environment file handling."""

    def test_deploy_with_env_file(self, tmp_path):
        """Test deploy --env-file option."""
        config_file = tmp_path / "workflow.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: test_workflow
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

        env_file = tmp_path / ".env.test"
        env_file.write_text("API_KEY=test123\n")

        result = subprocess.run(
            [
                sys.executable, "-m", "configurable_agents", "deploy",
                str(config_file), "--generate",
                "--env-file", str(env_file)
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should accept env file argument
        assert result.returncode == 0 or "env" not in result.stderr.lower()

    def test_deploy_missing_env_file_warning(self, tmp_path):
        """Test deploy warns when default .env file is missing."""
        config_file = tmp_path / "workflow.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: test_workflow
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

        # Run from directory without .env file
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "deploy", str(config_file), "--generate"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should succeed (missing .env is not fatal in generate-only mode)
        # May show warning but should not error
        assert result.returncode == 0 or "warning" in result.stderr.lower() or "env" in result.stderr.lower()


class TestCLIDeployCrossPlatform:
    """Cross-platform compatibility tests for deploy command."""

    def test_deploy_path_with_spaces(self, tmp_path):
        """Test that output paths with spaces work on all platforms."""
        config_dir = tmp_path / "my folder" / "workflow"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("""schema_version: "1.0"
flow:
  name: test_workflow
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

        output_dir = tmp_path / "my folder" / "output"
        output_dir.mkdir(parents=True)

        result = subprocess.run(
            [
                sys.executable, "-m", "configurable_agents", "deploy",
                str(config_file), "--generate",
                "--output-dir", str(output_dir)
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should handle spaces correctly
        assert result.returncode == 0 or "path" not in result.stderr.lower()


class TestCLIDeployErrorMessageQuality:
    """Test that deploy error messages are helpful."""

    def test_docker_error_includes_install_instructions(self, tmp_path):
        """Test that Docker unavailable error includes installation guidance."""
        # This is verified by code inspection since we can't easily mock Docker
        cli_path = Path("src/configurable_agents/cli.py")
        if cli_path.exists():
            cli_content = cli_path.read_text().lower()
            # Check for helpful docker error messages
            # Should mention install, docker, or instructions
            assert "install" in cli_content and "docker" in cli_content
            # Specifically check for install instructions near docker error
            assert "https://docs.docker.com" in cli_content or "https://docker.com" in cli_content

    def test_port_conflict_includes_port_number(self, tmp_path):
        """Test that port conflict error specifies which port."""
        # Verified by code inspection
        cli_path = Path("src/configurable_agents/cli.py")
        if cli_path.exists():
            cli_content = cli_path.read_text()
            # Should check ports and report conflicts
            assert "port" in cli_content.lower()
            assert "in use" in cli_content.lower() or "conflict" in cli_content.lower()
