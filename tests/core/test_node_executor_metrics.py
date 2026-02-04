"""Tests for node executor metrics collection and state persistence."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import BaseModel

from configurable_agents.config.schema import (
    GlobalConfig,
    LLMConfig,
    NodeConfig,
    OutputSchema,
    OutputSchemaField,
)
from configurable_agents.core import execute_node
from configurable_agents.core.node_executor import NodeExecutionError
from configurable_agents.llm import LLMUsageMetadata


# ============================================
# Test Helpers
# ============================================


def make_usage(input_tokens=100, output_tokens=50):
    """Create mock LLM usage metadata."""
    return LLMUsageMetadata(input_tokens=input_tokens, output_tokens=output_tokens)


class SimpleState(BaseModel):
    """Simple state for testing."""

    topic: str
    research: str = ""
    score: int = 0


class SimpleOutput(BaseModel):
    """Simple output model."""

    result: str


# ============================================
# Tests: Per-node metrics collection
# ============================================


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_node_saves_execution_state(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Test that node saves execution state with metrics to storage."""
    # Setup state
    state = SimpleState(topic="AI Safety", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Research {topic}",
        output_schema=OutputSchema(type="str", description="Research findings"),
        outputs=["research"],
    )

    # Mock output model
    mock_build_output.return_value = SimpleOutput

    # Mock LLM result
    mock_result = SimpleOutput(result="AI safety research findings...")
    mock_call_llm.return_value = (mock_result, make_usage(150, 75))

    # Create mock tracker with storage repos
    tracker = Mock()
    execution_state_repo = Mock()
    tracker.execution_state_repo = execution_state_repo
    tracker.run_id = "test-run-123"

    # Execute node
    updated_state = execute_node(node_config, state, tracker=tracker)

    # Verify state updated
    assert updated_state.research == "AI safety research findings..."

    # Verify save_state was called
    execution_state_repo.save_state.assert_called_once()
    call_args = execution_state_repo.save_state.call_args

    # Verify arguments
    assert call_args[1]["run_id"] == "test-run-123"
    assert call_args[1]["node_id"] == "test_node"

    # Verify state_data contains metrics
    state_data = call_args[1]["state_data"]
    assert state_data["node_id"] == "test_node"
    assert state_data["status"] == "completed"
    # Note: duration may be 0 with mocked instant LLM calls
    assert state_data["duration_seconds"] >= 0
    assert state_data["input_tokens"] == 150
    assert state_data["output_tokens"] == 75
    assert state_data["total_tokens"] == 225
    assert "model" in state_data
    assert "cost_usd" in state_data


@patch("configurable_agents.observability.cost_estimator.CostEstimator")
@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_node_saves_cost_metrics(
    mock_build_output, mock_create_llm, mock_call_llm, MockCostEstimator
):
    """Test that node saves cost metrics using CostEstimator."""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config with specific model
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
        llm=LLMConfig(model="gemini-1.5-flash"),
    )

    # Mock output model
    mock_build_output.return_value = SimpleOutput

    # Mock LLM result
    mock_result = SimpleOutput(result="Processed")
    mock_call_llm.return_value = (mock_result, make_usage(200, 100))

    # Mock cost estimator
    mock_estimator = Mock()
    mock_estimator.estimate_cost.return_value = 0.00015
    MockCostEstimator.return_value = mock_estimator

    # Create mock tracker with storage repos
    tracker = Mock()
    execution_state_repo = Mock()
    tracker.execution_state_repo = execution_state_repo
    tracker.run_id = "test-run-456"

    # Execute node
    updated_state = execute_node(node_config, state, tracker=tracker)

    # Verify cost estimator was called
    mock_estimator.estimate_cost.assert_called_once_with(
        model="gemini-1.5-flash",
        input_tokens=200,
        output_tokens=100,
    )

    # Verify state_data contains cost
    state_data = execution_state_repo.save_state.call_args[1]["state_data"]
    assert state_data["cost_usd"] == 0.00015


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_node_saves_output_values(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Test that node saves output values in state snapshot."""
    # Setup state
    state = SimpleState(topic="Robotics", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Research {topic}",
        output_schema=OutputSchema(type="str", description="Output"),
        outputs=["research"],
    )

    # Mock output model
    mock_build_output.return_value = SimpleOutput

    # Mock LLM result with specific output
    mock_result = SimpleOutput(result="Robotics research results...")
    mock_call_llm.return_value = (mock_result, make_usage())

    # Create mock tracker with storage repos
    tracker = Mock()
    execution_state_repo = Mock()
    tracker.execution_state_repo = execution_state_repo
    tracker.run_id = "test-run-789"

    # Execute node
    updated_state = execute_node(node_config, state, tracker=tracker)

    # Verify state_data contains output values
    state_data = execution_state_repo.save_state.call_args[1]["state_data"]
    assert "outputs" in state_data
    assert state_data["outputs"]["research"] == "Robotics research results..."


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_node_saves_state_on_failure(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Test that node saves failed state when LLM call fails."""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock output model
    mock_build_output.return_value = SimpleOutput

    # Mock LLM to raise error
    from configurable_agents.llm import LLMAPIError
    mock_call_llm.side_effect = LLMAPIError("API timeout")

    # Create mock tracker with storage repos
    tracker = Mock()
    execution_state_repo = Mock()
    tracker.execution_state_repo = execution_state_repo
    tracker.run_id = "test-run-fail"

    # Execute node - should raise error
    with pytest.raises(NodeExecutionError):
        execute_node(node_config, state, tracker=tracker)

    # Verify save_state was called with failed status
    execution_state_repo.save_state.assert_called_once()
    call_args = execution_state_repo.save_state.call_args

    # Verify failed state data
    state_data = call_args[1]["state_data"]
    assert state_data["node_id"] == "test_node"
    assert state_data["status"] == "failed"
    assert "error" in state_data
    assert "API timeout" in state_data["error"]
    assert state_data["duration_seconds"] >= 0


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_storage_failure_does_not_break_node(
    mock_build_output, mock_create_llm, mock_call_llm, caplog
):
    """Test that storage failure doesn't break node execution."""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock output model
    mock_build_output.return_value = SimpleOutput

    # Mock LLM result
    mock_result = SimpleOutput(result="Result")
    mock_call_llm.return_value = (mock_result, make_usage())

    # Create mock tracker with storage repo that fails
    tracker = Mock()
    execution_state_repo = Mock()
    execution_state_repo.save_state.side_effect = Exception("Storage failed")
    tracker.execution_state_repo = execution_state_repo
    tracker.run_id = "test-run-error"

    # Execute node - should succeed despite storage failure
    updated_state = execute_node(node_config, state, tracker=tracker)

    # Verify node completed
    assert updated_state.research == "Result"


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_no_storage_runs_normally(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Test that node executes normally when tracker has no storage repo."""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock output model
    mock_build_output.return_value = SimpleOutput

    # Mock LLM result
    mock_result = SimpleOutput(result="Result without storage")
    mock_call_llm.return_value = (mock_result, make_usage())

    # Create tracker without storage repos
    tracker = Mock()
    execution_state_repo = Mock()
    tracker.execution_state_repo = None
    tracker.run_id = None

    # Execute node - should work fine
    updated_state = execute_node(node_config, state, tracker=tracker)

    # Verify node completed
    assert updated_state.research == "Result without storage"

    # Verify save_state was NOT called (no repo attached)
    execution_state_repo.save_state.assert_not_called()


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_node_saves_state_with_no_tracker(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Test that node executes normally when no tracker is provided."""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock output model
    mock_build_output.return_value = SimpleOutput

    # Mock LLM result
    mock_result = SimpleOutput(result="Result no tracker")
    mock_call_llm.return_value = (mock_result, make_usage())

    # Execute node without tracker
    updated_state = execute_node(node_config, state)

    # Verify node completed
    assert updated_state.research == "Result no tracker"


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_output_values_are_truncated(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Test that large output values are truncated for storage efficiency."""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock output model
    mock_build_output.return_value = SimpleOutput

    # Create a long output (> 500 chars)
    long_output = "x" * 1000
    mock_result = SimpleOutput(result=long_output)
    mock_call_llm.return_value = (mock_result, make_usage())

    # Create mock tracker with storage repos
    tracker = Mock()
    execution_state_repo = Mock()
    tracker.execution_state_repo = execution_state_repo
    tracker.run_id = "test-run-truncate"

    # Execute node
    updated_state = execute_node(node_config, state, tracker=tracker)

    # Verify state was saved with truncated output
    state_data = execution_state_repo.save_state.call_args[1]["state_data"]
    saved_output = state_data["outputs"]["research"]
    assert len(saved_output) == 500  # Truncated to 500 chars
    assert saved_output == "x" * 500
