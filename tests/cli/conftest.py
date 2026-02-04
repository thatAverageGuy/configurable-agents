"""Fixtures for CLI tests."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_workflow_file():
    """Create a temporary workflow YAML file for testing."""
    content = """
schema_version: "1.0"

flow:
  name: test_workflow
  description: Test workflow for CLI commands
  version: "1.0.0"

state:
  fields:
    topic:
      type: str
      required: true
    result:
      type: str
      default: ""

nodes:
  - id: writer
    description: Write about the topic
    prompt: "Write about {state.topic}"
    outputs: [result]

edges:
  - {from: START, to: writer}
  - {from: writer, to: END}

config:
  llm:
    model: "gemini-2.5-flash-lite"
    temperature: 0.7
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_ab_test_workflow_file():
    """Create a temporary A/B test workflow YAML file."""
    content = """
schema_version: "1.0"

flow:
  name: ab_test_workflow
  description: Workflow with A/B testing configuration
  version: "1.0.0"

state:
  fields:
    topic:
      type: str
      required: true
    result:
      type: str
      default: ""

nodes:
  - id: writer
    description: Write about the topic
    prompt: "Default prompt"
    outputs: [result]

edges:
  - {from: START, to: writer}
  - {from: writer, to: END}

config:
  llm:
    model: "gemini-2.5-flash-lite"
    temperature: 0.7

  ab_test:
    enabled: true
    experiment: "test_ab_test"
    run_count: 2
    variants:
      - name: "variant_a"
        prompt: "Write concisely about {state.topic}"
        node_id: "writer"
      - name: "variant_b"
        prompt: "Write in detail about {state.topic}"
        node_id: "writer"
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def mock_mlflow_run():
    """Create a mock MLFlow run for testing."""
    run = MagicMock()
    run.info.run_id = "test_run_id_123"
    run.info.experiment_id = "test_experiment_id"
    run.info.status = "COMPLETED"
    run.data.metrics = {
        "cost_usd": 0.005,
        "duration_ms": 1500,
        "total_tokens": 500,
    }
    run.data.params = {
        "variant_name": "variant_a",
        "prompt": "Test prompt",
    }
    return run


@pytest.fixture
def mock_experiment_evaluator():
    """Create a mock ExperimentEvaluator for testing."""
    evaluator = MagicMock()

    # Mock comparison result
    from configurable_agents.optimization.evaluator import VariantResult, VariantMetrics, ComparisonResult

    mock_metrics = VariantMetrics(
        cost_usd_avg=0.003,
        cost_usd_min=0.002,
        cost_usd_max=0.004,
        cost_usd_p50=0.003,
        duration_ms_avg=1500,
        duration_ms_min=1200,
        duration_ms_max=1800,
        duration_ms_p50=1500,
        total_tokens_avg=500,
        run_count=3,
    )

    mock_variant = VariantResult(
        variant_name="variant_a",
        metrics=mock_metrics,
        run_count=3,
    )

    mock_comparison = ComparisonResult(
        experiment_name="test_experiment",
        metric="cost_usd_avg",
        best_variant="variant_a",
        variants=[mock_variant],
    )

    evaluator.compare_variants.return_value = mock_comparison
    evaluator.find_best_variant.return_value = {
        "variant_name": "variant_a",
        "prompt": "Optimized prompt",
        "cost_usd_avg": 0.003,
    }

    return evaluator


@pytest.fixture
def cli_runner():
    """
    Fixture that provides a function to run CLI commands via subprocess.

    Returns a function that runs commands and returns the result.
    """
    def run_command(args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a CLI command via subprocess."""
        full_args = [sys.executable, "-m", "configurable_agents"] + args
        return subprocess.run(
            full_args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    return run_command


@pytest.fixture
def minimal_config(tmp_path):
    """
    Fixture that provides a minimal valid config file.

    Returns a Path object pointing to the config file.
    """
    config_file = tmp_path / "minimal.yaml"
    config_file.write_text("""
schema_version: "1.0"
flow:
  name: minimal_test
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
    return config_file


@pytest.fixture
def complete_config(tmp_path):
    """
    Fixture that provides a complete valid config file.

    Returns a Path object pointing to the config file.
    """
    config_file = tmp_path / "complete.yaml"
    config_file.write_text("""
schema_version: "1.0"
flow:
  name: complete_test
  description: A complete test workflow
state:
  fields:
    - name: message
      type: str
      required: true
      description: Input message
    - name: count
      type: int
      default: 1
      description: Counter
    - name: result
      type: str
      default: ""
      description: Output result
nodes:
  - id: process
    prompt: "Process: {state.message}"
    outputs: [result]
    output_schema:
      type: object
      fields:
        - name: result
          type: str
          description: The processed result
edges:
  - {from: START, to: process}
  - {from: process, to: END}
""")
    return config_file


@pytest.fixture
def invalid_yaml_config(tmp_path):
    """
    Fixture that provides an invalid YAML config file.

    Returns a Path object pointing to the config file.
    """
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: content: [unclosed")
    return config_file


@pytest.fixture
def deploy_output_dir(tmp_path):
    """
    Fixture that provides a directory for deploy output.

    Creates and returns a Path object for deployment artifacts.
    """
    output_dir = tmp_path / "deploy_output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def requires_api_key():
    """
    Fixture that skips tests if API key is not configured.

    Use this marker for tests that require actual LLM API calls.
    """
    if not any(
        os.environ.get(key)
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    ):
        pytest.skip("No API key configured - set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY")
