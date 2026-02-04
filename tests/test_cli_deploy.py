"""
Unit tests for CLI deploy command.

Tests argument parsing, validation, Docker checks, artifact generation,
port conflicts, environment handling, and build/run operations.
"""

import argparse
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from configurable_agents.cli import (
    cmd_deploy,
    create_parser,
    is_port_in_use,
)
from configurable_agents.runtime import (
    ConfigLoadError,
    ConfigValidationError,
)


# --- Helper Functions ---


def get_test_config_path() -> Path:
    """Get path to test config file."""
    return Path(__file__).parent / "config" / "fixtures" / "valid_config.yaml"


def create_deploy_args(**kwargs) -> argparse.Namespace:
    """
    Create deploy command arguments with defaults.

    Args:
        **kwargs: Override default argument values

    Returns:
        Namespace with deploy arguments
    """
    defaults = {
        "config_file": str(get_test_config_path()),
        "output_dir": "./deploy",
        "api_port": 8000,
        "mlflow_port": 5000,
        "name": None,
        "timeout": 30,
        "generate": False,
        "no_mlflow": False,
        "env_file": ".env",
        "no_env_file": False,
        "verbose": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# --- Tests: Argument Parsing ---


def test_deploy_parser_default_values():
    """Test deploy parser has correct default values."""
    parser = create_parser()
    args = parser.parse_args(["deploy", "workflow.yaml"])

    assert args.command == "deploy"
    assert args.config_file == "workflow.yaml"
    assert args.output_dir == "./deploy"
    assert args.api_port == 8000
    assert args.mlflow_port == 5000
    assert args.name is None
    assert args.timeout == 30
    assert args.generate is False
    assert args.no_mlflow is False
    assert args.env_file == ".env"
    assert args.no_env_file is False
    assert args.verbose is False


def test_deploy_parser_custom_ports():
    """Test deploy parser with custom ports."""
    parser = create_parser()
    args = parser.parse_args([
        "deploy", "workflow.yaml",
        "--api-port", "9000",
        "--mlflow-port", "6000"
    ])

    assert args.api_port == 9000
    assert args.mlflow_port == 6000


def test_deploy_parser_generate_only_mode():
    """Test deploy parser with generate-only flag."""
    parser = create_parser()
    args = parser.parse_args(["deploy", "workflow.yaml", "--generate"])

    assert args.generate is True


def test_deploy_parser_no_mlflow_flag():
    """Test deploy parser with no-mlflow flag."""
    parser = create_parser()
    args = parser.parse_args(["deploy", "workflow.yaml", "--no-mlflow"])

    assert args.no_mlflow is True


def test_deploy_parser_custom_env_file():
    """Test deploy parser with custom env file."""
    parser = create_parser()
    args = parser.parse_args([
        "deploy", "workflow.yaml",
        "--env-file", "custom.env"
    ])

    assert args.env_file == "custom.env"


# --- Tests: Config Validation ---


@patch("configurable_agents.cli.validate_workflow")
def test_deploy_config_file_not_found(mock_validate):
    """Test deploy fails when config file doesn't exist."""
    args = create_deploy_args(config_file="nonexistent.yaml")

    result = cmd_deploy(args)

    assert result == 1
    mock_validate.assert_not_called()


@patch("configurable_agents.cli.Path")
@patch("configurable_agents.cli.validate_workflow")
def test_deploy_config_malformed_yaml(mock_validate, mock_path):
    """Test deploy handles malformed YAML syntax."""
    # Setup: file exists
    mock_path.return_value.exists.return_value = True

    # Setup: validation raises ConfigLoadError
    mock_validate.side_effect = ConfigLoadError("Invalid YAML syntax")

    args = create_deploy_args()
    result = cmd_deploy(args)

    assert result == 1
    mock_validate.assert_called_once()


@patch("configurable_agents.cli.Path")
@patch("configurable_agents.cli.validate_workflow")
def test_deploy_config_validation_failure(mock_validate, mock_path):
    """Test deploy handles semantic validation errors."""
    # Setup: file exists
    mock_path.return_value.exists.return_value = True

    # Setup: validation raises ConfigValidationError
    mock_validate.side_effect = ConfigValidationError("Missing required field: state")

    args = create_deploy_args()
    result = cmd_deploy(args)

    assert result == 1
    mock_validate.assert_called_once()


# --- Tests: Docker Checks ---


@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
@patch("configurable_agents.cli.Path")
def test_deploy_docker_not_installed(mock_path, mock_validate, mock_subprocess):
    """Test deploy fails when Docker is not installed."""
    # Setup: file exists and validation passes
    mock_path.return_value.exists.return_value = True
    mock_validate.return_value = None

    # Setup: Docker command not found
    mock_subprocess.side_effect = FileNotFoundError()

    args = create_deploy_args()
    result = cmd_deploy(args)

    assert result == 1


@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
@patch("configurable_agents.cli.Path")
def test_deploy_docker_not_running(mock_path, mock_validate, mock_subprocess):
    """Test deploy fails when Docker daemon is not running."""
    # Setup: file exists and validation passes
    mock_path.return_value.exists.return_value = True
    mock_validate.return_value = None

    # Setup: Docker version returns non-zero exit code
    mock_subprocess.return_value = Mock(returncode=1)

    args = create_deploy_args()
    result = cmd_deploy(args)

    assert result == 1


@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
@patch("configurable_agents.cli.Path")
def test_deploy_docker_timeout(mock_path, mock_validate, mock_subprocess):
    """Test deploy handles Docker command timeout."""
    # Setup: file exists and validation passes
    mock_path.return_value.exists.return_value = True
    mock_validate.return_value = None

    # Setup: Docker version times out
    mock_subprocess.side_effect = subprocess.TimeoutExpired("docker", 5)

    args = create_deploy_args()
    result = cmd_deploy(args)

    assert result == 1


@patch("configurable_agents.cli.generate_deployment_artifacts")
@patch("configurable_agents.config.parse_config_file")
@patch("configurable_agents.config.WorkflowConfig")
@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
@patch("configurable_agents.cli.Path")
def test_deploy_docker_available(mock_path, mock_validate, mock_subprocess, mock_workflow_config_cls, mock_parse, mock_generate):
    """Test deploy proceeds when Docker is available (build mode, not generate-only)."""
    # Setup: file exists and validation passes
    mock_path_instance = Mock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value = mock_path_instance
    mock_validate.return_value = None

    # Setup: Docker version succeeds
    docker_result = Mock(returncode=0, stdout="", stderr="")
    mock_subprocess.return_value = docker_result

    # Setup: Config parsing
    mock_parse.return_value = {"flow": {"name": "test_workflow"}}
    mock_workflow_config = Mock()
    mock_workflow_config.flow.name = "test_workflow"
    mock_workflow_config_cls.return_value = mock_workflow_config

    # Setup: Artifact generation
    mock_generate.return_value = {"Dockerfile": Path("deploy/Dockerfile")}

    # Use generate=False so Docker check happens
    args = create_deploy_args(generate=False)
    result = cmd_deploy(args)

    assert result == 0
    assert mock_subprocess.call_count >= 1  # At least docker version check


# --- Tests: Artifact Generation ---


@patch("configurable_agents.cli.generate_deployment_artifacts")
@patch("configurable_agents.config.parse_config_file")
@patch("configurable_agents.config.WorkflowConfig")
@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
@patch("configurable_agents.cli.Path")
def test_deploy_generate_only_exits_after_artifacts(
    mock_path, mock_validate, mock_subprocess, mock_workflow_config_cls,
    mock_parse, mock_generate
):
    """Test deploy with --generate exits after artifact generation without Docker check."""
    # Setup: file exists and validation passes
    mock_path_instance = Mock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value = mock_path_instance

    mock_validate.return_value = None

    # Setup: Config parsing
    mock_parse.return_value = {"flow": {"name": "test_workflow"}}
    mock_workflow_config = Mock()
    mock_workflow_config.flow.name = "test_workflow"
    mock_workflow_config_cls.return_value = mock_workflow_config

    # Setup: Artifact generation
    artifacts = {
        "Dockerfile": Path("deploy/Dockerfile"),
        "server.py": Path("deploy/server.py"),
    }
    mock_generate.return_value = artifacts

    args = create_deploy_args(generate=True)
    result = cmd_deploy(args)

    assert result == 0
    mock_generate.assert_called_once()
    # Should NOT call any docker commands in generate-only mode
    assert mock_subprocess.call_count == 0


@patch("configurable_agents.cli.generate_deployment_artifacts")
@patch("configurable_agents.config.parse_config_file")
@patch("configurable_agents.config.WorkflowConfig")
@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
@patch("configurable_agents.cli.Path")
def test_deploy_artifact_generation_error(
    mock_path, mock_validate, mock_subprocess, mock_workflow_config_cls,
    mock_parse, mock_generate
):
    """Test deploy handles artifact generation errors."""
    # Setup: file exists and validation passes
    mock_path_instance = Mock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value = mock_path_instance

    mock_validate.return_value = None

    # Setup: Docker available
    mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

    # Setup: Config parsing
    mock_parse.return_value = {"flow": {"name": "test_workflow"}}
    mock_workflow_config = Mock()
    mock_workflow_config.flow.name = "test_workflow"
    mock_workflow_config_cls.return_value = mock_workflow_config

    # Setup: Artifact generation fails
    mock_generate.side_effect = FileNotFoundError("Template not found")

    args = create_deploy_args()
    result = cmd_deploy(args)

    assert result == 1


# --- Tests: Port Conflicts ---


def test_is_port_in_use_free_port():
    """Test is_port_in_use returns False for free port."""
    # Use a very high port unlikely to be in use
    assert is_port_in_use(65000) is False


def test_is_port_in_use_occupied_port():
    """Test is_port_in_use returns True for occupied port."""
    import socket

    # Create a temporary server on a random port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(('localhost', 0))
        server.listen(1)
        port = server.getsockname()[1]

        # Port should be detected as in use
        assert is_port_in_use(port) is True


@patch("configurable_agents.cli.is_port_in_use")
@patch("configurable_agents.cli.generate_deployment_artifacts")
@patch("configurable_agents.config.parse_config_file")
@patch("configurable_agents.config.WorkflowConfig")
@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
@patch("configurable_agents.cli.Path")
def test_deploy_api_port_conflict(
    mock_path, mock_validate, mock_subprocess, mock_workflow_config_cls,
    mock_parse, mock_generate, mock_is_port_in_use
):
    """Test deploy fails when API port is already in use."""
    # Setup: file exists and validation passes
    mock_path_instance = Mock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value = mock_path_instance

    mock_validate.return_value = None

    # Setup: Docker available
    mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

    # Setup: Config parsing
    mock_parse.return_value = {"flow": {"name": "test_workflow"}}
    mock_workflow_config = Mock()
    mock_workflow_config.flow.name = "test_workflow"
    mock_workflow_config_cls.return_value = mock_workflow_config

    # Setup: Artifact generation
    mock_generate.return_value = {"Dockerfile": Path("deploy/Dockerfile")}

    # Setup: API port in use
    mock_is_port_in_use.return_value = True

    args = create_deploy_args()
    result = cmd_deploy(args)

    assert result == 1


@patch("configurable_agents.cli.is_port_in_use")
@patch("configurable_agents.cli.generate_deployment_artifacts")
@patch("configurable_agents.config.parse_config_file")
@patch("configurable_agents.config.WorkflowConfig")
@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
@patch("configurable_agents.cli.Path")
def test_deploy_mlflow_port_conflict(
    mock_path, mock_validate, mock_subprocess, mock_workflow_config_cls,
    mock_parse, mock_generate, mock_is_port_in_use
):
    """Test deploy fails when MLFlow port is already in use."""
    # Setup: file exists and validation passes
    mock_path_instance = Mock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value = mock_path_instance

    mock_validate.return_value = None

    # Setup: Docker available
    mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

    # Setup: Config parsing
    mock_parse.return_value = {"flow": {"name": "test_workflow"}}
    mock_workflow_config = Mock()
    mock_workflow_config.flow.name = "test_workflow"
    mock_workflow_config_cls.return_value = mock_workflow_config

    # Setup: Artifact generation
    mock_generate.return_value = {"Dockerfile": Path("deploy/Dockerfile")}

    # Setup: API port free, MLFlow port in use
    def port_check(port):
        return port == 5000  # MLFlow port

    mock_is_port_in_use.side_effect = port_check

    args = create_deploy_args()
    result = cmd_deploy(args)

    assert result == 1


# --- Tests: Environment Variables ---


@patch("configurable_agents.cli.is_port_in_use")
@patch("configurable_agents.cli.generate_deployment_artifacts")
@patch("configurable_agents.config.parse_config_file")
@patch("configurable_agents.config.WorkflowConfig")
@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
@patch("configurable_agents.cli.Path")
def test_deploy_with_env_file(
    mock_path, mock_validate, mock_subprocess, mock_workflow_config_cls,
    mock_parse, mock_generate, mock_is_port_in_use, tmp_path
):
    """Test deploy uses environment file when it exists."""
    # Setup: file exists and validation passes
    config_path = tmp_path / "workflow.yaml"
    config_path.write_text("flow:\n  name: test")
    env_path = tmp_path / ".env"
    env_path.write_text("API_KEY=test123\n")

    def path_exists_side_effect(path):
        p = Path(path)
        return p == config_path or p == env_path

    mock_path_instance = Mock()
    mock_path_instance.exists.side_effect = lambda: True
    mock_path.return_value = mock_path_instance

    mock_validate.return_value = None

    # Setup: Docker available
    docker_result = Mock(returncode=0, stdout="abc123\n", stderr="")
    mock_subprocess.return_value = docker_result

    # Setup: Config parsing
    mock_parse.return_value = {"flow": {"name": "test_workflow"}}
    mock_workflow_config = Mock()
    mock_workflow_config.flow.name = "test_workflow"
    mock_workflow_config_cls.return_value = mock_workflow_config

    # Setup: Artifact generation
    mock_generate.return_value = {"Dockerfile": Path("deploy/Dockerfile")}

    # Setup: Ports available
    mock_is_port_in_use.return_value = False

    args = create_deploy_args(
        config_file=str(config_path),
        env_file=str(env_path)
    )

    # We need to also mock Path for the env file check
    with patch("configurable_agents.cli.Path") as mock_path_cls:
        mock_env_file = Mock()
        mock_env_file.exists.return_value = True
        mock_env_file.read_text.return_value = "API_KEY=test123\n"
        mock_path_cls.return_value = mock_env_file

        result = cmd_deploy(args)

    assert result == 0


@patch("configurable_agents.cli.is_port_in_use")
@patch("configurable_agents.cli.generate_deployment_artifacts")
@patch("configurable_agents.config.parse_config_file")
@patch("configurable_agents.config.WorkflowConfig")
@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
def test_deploy_missing_default_env_warning(
    mock_validate, mock_subprocess, mock_workflow_config_cls,
    mock_parse, mock_generate, mock_is_port_in_use, tmp_path
):
    """Test deploy warns when default .env file is missing."""
    # Setup: Create a real config file
    config_path = tmp_path / "workflow.yaml"
    config_path.write_text("flow:\n  name: test")

    mock_validate.return_value = None

    # Setup: Docker available
    mock_subprocess.return_value = Mock(returncode=0, stdout="abc123\n", stderr="")

    # Setup: Config parsing
    mock_parse.return_value = {"flow": {"name": "test_workflow"}}
    mock_workflow_config = Mock()
    mock_workflow_config.flow.name = "test_workflow"
    mock_workflow_config_cls.return_value = mock_workflow_config

    # Setup: Artifact generation
    deploy_dir = tmp_path / "deploy"
    deploy_dir.mkdir()
    mock_generate.return_value = {"Dockerfile": deploy_dir / "Dockerfile"}

    # Setup: Ports available
    mock_is_port_in_use.return_value = False

    args = create_deploy_args(
        config_file=str(config_path),
        output_dir=str(deploy_dir)
    )
    # Note: .env file does NOT exist in tmp_path

    result = cmd_deploy(args)

    # Should succeed with warning
    assert result == 0


# --- Tests: Build & Run ---


@patch("configurable_agents.cli.is_port_in_use")
@patch("configurable_agents.cli.generate_deployment_artifacts")
@patch("configurable_agents.config.parse_config_file")
@patch("configurable_agents.config.WorkflowConfig")
@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
@patch("configurable_agents.cli.Path")
def test_deploy_build_failure(
    mock_path, mock_validate, mock_subprocess, mock_workflow_config_cls,
    mock_parse, mock_generate, mock_is_port_in_use
):
    """Test deploy handles Docker build failure."""
    # Setup: file exists and validation passes
    mock_path_instance = Mock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value = mock_path_instance

    mock_validate.return_value = None

    # Setup: Docker version succeeds, build fails
    def subprocess_side_effect(*args, **kwargs):
        cmd = args[0]
        if cmd[0:2] == ["docker", "version"]:
            return Mock(returncode=0, stdout="", stderr="")
        elif cmd[0:2] == ["docker", "build"]:
            return Mock(returncode=1, stdout="", stderr="Build failed: syntax error")
        return Mock(returncode=0, stdout="", stderr="")

    mock_subprocess.side_effect = subprocess_side_effect

    # Setup: Config parsing
    mock_parse.return_value = {"flow": {"name": "test_workflow"}}
    mock_workflow_config = Mock()
    mock_workflow_config.flow.name = "test_workflow"
    mock_workflow_config_cls.return_value = mock_workflow_config

    # Setup: Artifact generation
    mock_generate.return_value = {"Dockerfile": Path("deploy/Dockerfile")}

    # Setup: Ports available
    mock_is_port_in_use.return_value = False

    # Patch env file check
    with patch("configurable_agents.cli.Path") as mock_path_cls:
        mock_env_path = Mock()
        mock_env_path.exists.return_value = False
        mock_path_cls.return_value = mock_env_path

        args = create_deploy_args()
        result = cmd_deploy(args)

    assert result == 1


@patch("configurable_agents.cli.is_port_in_use")
@patch("configurable_agents.cli.generate_deployment_artifacts")
@patch("configurable_agents.config.parse_config_file")
@patch("configurable_agents.config.WorkflowConfig")
@patch("configurable_agents.cli.subprocess.run")
@patch("configurable_agents.cli.validate_workflow")
@patch("configurable_agents.cli.Path")
def test_deploy_container_conflict(
    mock_path, mock_validate, mock_subprocess, mock_workflow_config_cls,
    mock_parse, mock_generate, mock_is_port_in_use
):
    """Test deploy handles container name conflict."""
    # Setup: file exists and validation passes
    mock_path_instance = Mock()
    mock_path_instance.exists.return_value = True
    mock_path.return_value = mock_path_instance

    mock_validate.return_value = None

    # Setup: Docker version and build succeed, run fails with conflict
    def subprocess_side_effect(*args, **kwargs):
        cmd = args[0]
        if cmd[0:2] == ["docker", "version"]:
            return Mock(returncode=0, stdout="", stderr="")
        elif cmd[0:2] == ["docker", "build"]:
            return Mock(returncode=0, stdout="Successfully built abc123", stderr="")
        elif cmd[0:2] == ["docker", "images"]:
            return Mock(returncode=0, stdout="1.2GB", stderr="")
        elif cmd[0:2] == ["docker", "run"]:
            return Mock(
                returncode=1,
                stdout="",
                stderr="Error: Conflict. The container name '/test_workflow' is already in use"
            )
        return Mock(returncode=0, stdout="", stderr="")

    mock_subprocess.side_effect = subprocess_side_effect

    # Setup: Config parsing
    mock_parse.return_value = {"flow": {"name": "test_workflow"}}
    mock_workflow_config = Mock()
    mock_workflow_config.flow.name = "test_workflow"
    mock_workflow_config_cls.return_value = mock_workflow_config

    # Setup: Artifact generation
    mock_generate.return_value = {"Dockerfile": Path("deploy/Dockerfile")}

    # Setup: Ports available
    mock_is_port_in_use.return_value = False

    # Patch env file check and time
    with patch("configurable_agents.cli.Path") as mock_path_cls:
        mock_env_path = Mock()
        mock_env_path.exists.return_value = False
        mock_path_cls.return_value = mock_env_path

        with patch("configurable_agents.cli.time.time", side_effect=[0, 10]):
            args = create_deploy_args()
            result = cmd_deploy(args)

    assert result == 1
