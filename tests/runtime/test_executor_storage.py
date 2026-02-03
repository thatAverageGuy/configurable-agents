"""Tests for executor-storage integration."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import BaseModel

from configurable_agents.config import (
    EdgeConfig,
    FlowMetadata,
    GlobalConfig,
    NodeConfig,
    OutputSchema,
    OutputSchemaField,
    StateFieldConfig,
    StateSchema,
    StorageConfig,
    WorkflowConfig,
)
from configurable_agents.runtime import run_workflow_from_config


# ============================================
# Test Fixtures
# ============================================


def make_minimal_config(**overrides) -> WorkflowConfig:
    """Create a minimal valid v1.0 config."""
    defaults = {
        "schema_version": "1.0",
        "flow": FlowMetadata(name="test_flow"),
        "state": StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "output": StateFieldConfig(type="str", default=""),
            }
        ),
        "nodes": [
            NodeConfig(
                id="process",
                prompt="Process {state.input}",
                outputs=["output"],
                output_schema=OutputSchema(
                    type="object",
                    fields=[
                        OutputSchemaField(name="output", type="str"),
                    ],
                ),
            )
        ],
        "edges": [
            EdgeConfig(from_="START", to="process"),
            EdgeConfig(from_="process", to="END"),
        ],
    }
    defaults.update(overrides)
    return WorkflowConfig(**defaults)


@pytest.fixture
def minimal_config():
    """Fixture for minimal valid config."""
    return make_minimal_config()


@pytest.fixture
def temp_config_file(tmp_path):
    """Fixture that creates a temporary config file."""

    def _create_config(content: str, extension: str = "yaml") -> Path:
        """Create temp config file with content."""
        file_path = tmp_path / f"config.{extension}"
        file_path.write_text(content)
        return file_path

    return _create_config


# ============================================
# Tests: Executor-Storage Integration
# ============================================


@patch("configurable_agents.runtime.executor.validate_config")
@patch("configurable_agents.runtime.executor.validate_runtime_support")
@patch("configurable_agents.runtime.executor.build_state_model")
@patch("configurable_agents.runtime.executor.build_graph")
def test_run_persisted_before_execution(
    mock_build_graph, mock_state_model, mock_runtime, mock_validate, minimal_config, tmp_path
):
    """Test that WorkflowRunRecord is persisted before execution begins."""
    # Setup mocks
    mock_validate.return_value = None
    mock_runtime.return_value = None

    class MockState(BaseModel):
        input: str
        output: str = ""

    mock_state_model.return_value = MockState

    mock_graph = Mock()
    mock_graph.invoke.return_value = {"input": "test", "output": "result"}
    mock_build_graph.return_value = mock_graph

    # Add storage config with temp database
    db_path = tmp_path / "test_workflow.db"
    storage_config = StorageConfig(backend="sqlite", path=str(db_path))
    config_with_storage = make_minimal_config(
        config=GlobalConfig(storage=storage_config)
    )

    # Execute
    result = run_workflow_from_config(config_with_storage, {"input": "test"})

    # Verify workflow completed
    assert result == {"input": "test", "output": "result"}

    # Verify run record was persisted
    from configurable_agents.storage import create_storage_backend
    from configurable_agents.storage.models import WorkflowRunRecord

    workflow_run_repo, _, _, _, _ = create_storage_backend(storage_config)
    runs = workflow_run_repo.list_by_workflow("test_flow")

    assert len(runs) == 1
    run = runs[0]
    assert run.workflow_name == "test_flow"
    assert run.status == "completed"
    assert run.started_at is not None
    assert run.completed_at is not None
    assert run.duration_seconds > 0


@patch("configurable_agents.runtime.executor.validate_config")
@patch("configurable_agents.runtime.executor.validate_runtime_support")
@patch("configurable_agents.runtime.executor.build_state_model")
@patch("configurable_agents.runtime.executor.build_graph")
def test_run_updated_on_completion(
    mock_build_graph, mock_state_model, mock_runtime, mock_validate, minimal_config, tmp_path
):
    """Test that run record is updated with completion metrics."""
    # Setup mocks
    mock_validate.return_value = None
    mock_runtime.return_value = None

    class MockState(BaseModel):
        input: str
        output: str = ""

    mock_state_model.return_value = MockState

    mock_graph = Mock()
    mock_graph.invoke.return_value = {"input": "test", "output": "result"}
    mock_build_graph.return_value = mock_graph

    # Add storage config
    db_path = tmp_path / "test_completion.db"
    storage_config = StorageConfig(backend="sqlite", path=str(db_path))
    config_with_storage = make_minimal_config(
        config=GlobalConfig(storage=storage_config)
    )

    # Execute
    result = run_workflow_from_config(config_with_storage, {"input": "test"})

    # Verify
    assert result == {"input": "test", "output": "result"}

    # Verify run record has completion metrics
    from configurable_agents.storage import create_storage_backend

    workflow_run_repo, _, _, _, _ = create_storage_backend(storage_config)
    runs = workflow_run_repo.list_by_workflow("test_flow")

    assert len(runs) == 1
    run = runs[0]
    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.duration_seconds > 0
    assert run.outputs is not None
    # Verify outputs contain the result
    import json
    outputs = json.loads(run.outputs)
    assert outputs["output"] == "result"


@patch("configurable_agents.runtime.executor.validate_config")
@patch("configurable_agents.runtime.executor.validate_runtime_support")
@patch("configurable_agents.runtime.executor.build_state_model")
@patch("configurable_agents.runtime.executor.build_graph")
def test_run_updated_on_failure(
    mock_build_graph, mock_state_model, mock_runtime, mock_validate, minimal_config, tmp_path
):
    """Test that run record is updated with 'failed' status on error."""
    # Setup mocks
    mock_validate.return_value = None
    mock_runtime.return_value = None

    class MockState(BaseModel):
        input: str
        output: str = ""

    mock_state_model.return_value = MockState

    # Mock graph that fails
    mock_graph = Mock()
    mock_graph.invoke.side_effect = RuntimeError("Node execution failed")
    mock_build_graph.return_value = mock_graph

    # Add storage config
    db_path = tmp_path / "test_failure.db"
    storage_config = StorageConfig(backend="sqlite", path=str(db_path))
    config_with_storage = make_minimal_config(
        config=GlobalConfig(storage=storage_config)
    )

    # Execute and expect error
    from configurable_agents.runtime import WorkflowExecutionError
    with pytest.raises(WorkflowExecutionError):
        run_workflow_from_config(config_with_storage, {"input": "test"})

    # Verify run record has failed status
    from configurable_agents.storage import create_storage_backend

    workflow_run_repo, _, _, _, _ = create_storage_backend(storage_config)
    runs = workflow_run_repo.list_by_workflow("test_flow")

    assert len(runs) == 1
    run = runs[0]
    assert run.status == "failed"
    assert run.completed_at is not None
    assert run.duration_seconds > 0
    assert run.error_message is not None
    assert "Node execution failed" in run.error_message


@patch("configurable_agents.runtime.executor.validate_config")
@patch("configurable_agents.runtime.executor.validate_runtime_support")
@patch("configurable_agents.runtime.executor.build_state_model")
@patch("configurable_agents.runtime.executor.build_graph")
@patch("configurable_agents.runtime.executor.create_storage_backend")
def test_storage_failure_does_not_block_execution(
    mock_create_storage, mock_build_graph, mock_state_model, mock_runtime, mock_validate, minimal_config
):
    """Test that workflow runs successfully even when storage backend fails."""
    # Setup mocks
    mock_validate.return_value = None
    mock_runtime.return_value = None

    class MockState(BaseModel):
        input: str
        output: str = ""

    mock_state_model.return_value = MockState

    mock_graph = Mock()
    mock_graph.invoke.return_value = {"input": "test", "output": "result"}
    mock_build_graph.return_value = mock_graph

    # Mock storage backend to raise exception
    mock_create_storage.side_effect = Exception("Storage connection failed")

    # Add storage config (will fail to initialize)
    storage_config = StorageConfig(backend="sqlite", path="/invalid/path")
    config_with_storage = make_minimal_config(
        config=GlobalConfig(storage=storage_config)
    )

    # Execute - should succeed despite storage failure
    result = run_workflow_from_config(config_with_storage, {"input": "test"})

    # Verify workflow completed
    assert result == {"input": "test", "output": "result"}


@patch("configurable_agents.runtime.executor.validate_config")
@patch("configurable_agents.runtime.executor.validate_runtime_support")
@patch("configurable_agents.runtime.executor.build_state_model")
@patch("configurable_agents.runtime.executor.build_graph")
def test_no_storage_config_runs_without_persistence(
    mock_build_graph, mock_state_model, mock_runtime, mock_validate, minimal_config
):
    """Test that workflow runs successfully with no storage config."""
    # Setup mocks
    mock_validate.return_value = None
    mock_runtime.return_value = None

    class MockState(BaseModel):
        input: str
        output: str = ""

    mock_state_model.return_value = MockState

    mock_graph = Mock()
    mock_graph.invoke.return_value = {"input": "test", "output": "result"}
    mock_build_graph.return_value = mock_graph

    # Config with no storage
    config_no_storage = make_minimal_config(config=GlobalConfig(storage=None))

    # Execute
    result = run_workflow_from_config(config_no_storage, {"input": "test"})

    # Verify workflow completed
    assert result == {"input": "test", "output": "result"}
