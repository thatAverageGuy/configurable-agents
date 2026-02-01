"""
Integration tests for CLI deploy command.

Tests full end-to-end deployment workflow with real Docker.

These tests require Docker to be installed and running.
They are marked as slow and integration tests.
"""

import shutil
import subprocess
import time
from pathlib import Path

import pytest
import requests


@pytest.mark.integration
@pytest.mark.slow
def test_deploy_full_workflow(tmp_path):
    """
    Test full end-to-end deployment workflow.

    Creates a simple workflow, deploys it as Docker container,
    verifies it's running, tests the API, and cleans up.

    Requires Docker to be installed and running.
    """
    # Skip if Docker is not available
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            pytest.skip("Docker daemon is not running")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker is not installed or not responding")

    # Create a simple workflow config
    config_content = """
flow:
  name: test_integration_workflow
  description: Integration test workflow
  version: 1.0.0

state:
  fields:
    message:
      type: str
      required: true
      description: Input message

steps:
  - name: echo_step
    agent: echo_agent
    prompt: "Echo: {message}"

agents:
  - name: echo_agent
    llm:
      provider: anthropic
      model: claude-3-5-haiku-20241022
      temperature: 0.7
      max_tokens: 100
"""

    config_path = tmp_path / "workflow.yaml"
    config_path.write_text(config_content)

    # Deploy directory
    deploy_dir = tmp_path / "deploy"
    container_name = "test-integration-workflow"
    api_port = 58000  # Use high port to avoid conflicts
    mlflow_port = 58001

    try:
        # Run deploy command
        result = subprocess.run(
            [
                "configurable-agents", "deploy",
                str(config_path),
                "--output-dir", str(deploy_dir),
                "--api-port", str(api_port),
                "--mlflow-port", str(mlflow_port),
                "--name", container_name,
                "--no-env-file",  # Skip env file requirement
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes for build
        )

        # Check deploy succeeded
        assert result.returncode == 0, f"Deploy failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

        # Verify artifacts were generated
        assert (deploy_dir / "Dockerfile").exists()
        assert (deploy_dir / "server.py").exists()
        assert (deploy_dir / "requirements.txt").exists()
        assert (deploy_dir / "workflow.yaml").exists()

        # Verify container is running
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert container_name in result.stdout

        # Wait for container to be ready (health check)
        max_wait = 30  # seconds
        start_time = time.time()
        health_url = f"http://localhost:{api_port}/health"
        ready = False

        while time.time() - start_time < max_wait:
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    ready = True
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)

        assert ready, f"Container did not become healthy within {max_wait}s"

        # Test health endpoint
        response = requests.get(health_url)
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert health_data["workflow_name"] == "test_integration_workflow"

        # Test API docs endpoint
        docs_url = f"http://localhost:{api_port}/docs"
        response = requests.get(docs_url)
        assert response.status_code == 200

        # Test MLFlow UI endpoint
        mlflow_url = f"http://localhost:{mlflow_port}"
        response = requests.get(mlflow_url, timeout=5)
        assert response.status_code == 200

    finally:
        # Cleanup: stop and remove container
        subprocess.run(
            ["docker", "stop", container_name],
            capture_output=True,
            timeout=30
        )
        subprocess.run(
            ["docker", "rm", container_name],
            capture_output=True,
            timeout=30
        )

        # Remove image
        subprocess.run(
            ["docker", "rmi", f"{container_name}:latest"],
            capture_output=True,
            timeout=30
        )

        # Clean up deploy directory
        if deploy_dir.exists():
            shutil.rmtree(deploy_dir)
