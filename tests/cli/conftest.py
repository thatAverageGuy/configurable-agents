"""Fixtures for CLI tests."""

import tempfile
from pathlib import Path
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
