"""Tests for runtime executor."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import BaseModel, ValidationError as PydanticValidationError

from configurable_agents.config import (
    EdgeConfig,
    FlowMetadata,
    GlobalConfig,
    NodeConfig,
    OutputSchema,
    OutputSchemaField,
    Route,
    StateFieldConfig,
    StateSchema,
    ValidationError,
    WorkflowConfig,
)
from configurable_agents.runtime import (
    ConfigLoadError,
    ConfigValidationError,
    ExecutionError,
    GraphBuildError,
    StateInitializationError,
    WorkflowExecutionError,
    run_workflow,
    run_workflow_from_config,
    validate_workflow,
)
from configurable_agents.runtime.feature_gate import UnsupportedFeatureError


# ============================================
# Test Fixtures
# ============================================


def make_minimal_config(**overrides) -> WorkflowConfig:
    """Create a minimal valid v0.1 config."""
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
# Tests: run_workflow_from_config (core logic)
# ============================================


def test_run_workflow_from_config_success(minimal_config):
    """Test successful workflow execution from config."""
    # Mock all the components
    with (
        patch("configurable_agents.runtime.executor.validate_config") as mock_validate,
        patch(
            "configurable_agents.runtime.executor.validate_runtime_support"
        ) as mock_runtime,
        patch(
            "configurable_agents.runtime.executor.build_state_model"
        ) as mock_state_model,
        patch("configurable_agents.runtime.executor.build_graph") as mock_build_graph,
    ):
        # Setup mocks
        mock_validate.return_value = None
        mock_runtime.return_value = None

        # Mock state model
        class MockState(BaseModel):
            input: str
            output: str = ""

        mock_state_model.return_value = MockState

        # Mock graph
        mock_graph = Mock()
        mock_graph.invoke.return_value = {"input": "test", "output": "result"}
        mock_build_graph.return_value = mock_graph

        # Execute
        result = run_workflow_from_config(minimal_config, {"input": "test"})

        # Verify
        assert result == {"input": "test", "output": "result"}
        mock_validate.assert_called_once_with(minimal_config)
        mock_runtime.assert_called_once_with(minimal_config)
        mock_state_model.assert_called_once()
        mock_build_graph.assert_called_once()
        mock_graph.invoke.assert_called_once()


def test_run_workflow_from_config_verbose_logging(minimal_config):
    """Test verbose logging is enabled."""
    with (
        patch("configurable_agents.runtime.executor.validate_config"),
        patch("configurable_agents.runtime.executor.validate_runtime_support"),
        patch("configurable_agents.runtime.executor.build_state_model") as mock_state,
        patch("configurable_agents.runtime.executor.build_graph") as mock_graph,
        patch("configurable_agents.runtime.executor.logging") as mock_logging,
    ):
        # Setup mocks
        class MockState(BaseModel):
            input: str
            output: str = ""

        mock_state.return_value = MockState
        mock_graph_instance = Mock()
        mock_graph_instance.invoke.return_value = {"input": "test", "output": "result"}
        mock_graph.return_value = mock_graph_instance

        # Execute with verbose=True
        run_workflow_from_config(minimal_config, {"input": "test"}, verbose=True)

        # Verify logging level was set
        mock_logging.getLogger.assert_called()


def test_run_workflow_from_config_config_validation_error(minimal_config):
    """Test error when config validation fails."""
    with patch(
        "configurable_agents.runtime.executor.validate_config"
    ) as mock_validate:
        # Setup mock to raise ValidationError
        mock_validate.side_effect = ValidationError("Invalid config")

        # Execute and verify error
        with pytest.raises(ConfigValidationError) as exc_info:
            run_workflow_from_config(minimal_config, {"input": "test"})

        assert "Config validation failed" in str(exc_info.value)
        assert exc_info.value.phase == "config_validation"


def test_run_workflow_from_config_unsupported_feature_error(minimal_config):
    """Test error when unsupported features detected."""
    with (
        patch("configurable_agents.runtime.executor.validate_config"),
        patch(
            "configurable_agents.runtime.executor.validate_runtime_support"
        ) as mock_runtime,
    ):
        # Setup mock to raise UnsupportedFeatureError
        mock_runtime.side_effect = UnsupportedFeatureError(
            "Conditional routing",
            "v0.2",
            "8-12 weeks",
            "Use linear edges",
        )

        # Execute and verify error
        with pytest.raises(ConfigValidationError) as exc_info:
            run_workflow_from_config(minimal_config, {"input": "test"})

        assert "Unsupported features detected" in str(exc_info.value)
        assert exc_info.value.phase == "feature_gating"


def test_run_workflow_from_config_state_model_build_error(minimal_config):
    """Test error when state model building fails."""
    with (
        patch("configurable_agents.runtime.executor.validate_config"),
        patch("configurable_agents.runtime.executor.validate_runtime_support"),
        patch(
            "configurable_agents.runtime.executor.build_state_model"
        ) as mock_state_model,
    ):
        # Setup mock to raise error
        mock_state_model.side_effect = ValueError("Invalid state schema")

        # Execute and verify error
        with pytest.raises(GraphBuildError) as exc_info:
            run_workflow_from_config(minimal_config, {"input": "test"})

        assert "Failed to build state model" in str(exc_info.value)
        assert exc_info.value.phase == "state_model_build"


def test_run_workflow_from_config_state_initialization_error(minimal_config):
    """Test error when state initialization fails."""
    with (
        patch("configurable_agents.runtime.executor.validate_config"),
        patch("configurable_agents.runtime.executor.validate_runtime_support"),
        patch(
            "configurable_agents.runtime.executor.build_state_model"
        ) as mock_state_model,
    ):
        # Mock state model that will fail validation
        class MockState(BaseModel):
            input: str
            output: str
            required_field: int  # Missing in inputs

        mock_state_model.return_value = MockState

        # Execute and verify error
        with pytest.raises(StateInitializationError) as exc_info:
            run_workflow_from_config(minimal_config, {"input": "test"})

        assert "Failed to initialize state" in str(exc_info.value)
        assert exc_info.value.phase == "state_initialization"


def test_run_workflow_from_config_graph_build_error(minimal_config):
    """Test error when graph building fails."""
    with (
        patch("configurable_agents.runtime.executor.validate_config"),
        patch("configurable_agents.runtime.executor.validate_runtime_support"),
        patch(
            "configurable_agents.runtime.executor.build_state_model"
        ) as mock_state_model,
        patch("configurable_agents.runtime.executor.build_graph") as mock_build_graph,
    ):
        # Setup mocks
        class MockState(BaseModel):
            input: str
            output: str = ""

        mock_state_model.return_value = MockState
        mock_build_graph.side_effect = ValueError("Invalid graph structure")

        # Execute and verify error
        with pytest.raises(GraphBuildError) as exc_info:
            run_workflow_from_config(minimal_config, {"input": "test"})

        assert "Failed to build execution graph" in str(exc_info.value)
        assert exc_info.value.phase == "graph_build"


def test_run_workflow_from_config_workflow_execution_error(minimal_config):
    """Test error during workflow execution."""
    with (
        patch("configurable_agents.runtime.executor.validate_config"),
        patch("configurable_agents.runtime.executor.validate_runtime_support"),
        patch(
            "configurable_agents.runtime.executor.build_state_model"
        ) as mock_state_model,
        patch("configurable_agents.runtime.executor.build_graph") as mock_build_graph,
    ):
        # Setup mocks
        class MockState(BaseModel):
            input: str
            output: str = ""

        mock_state_model.return_value = MockState

        # Mock graph that fails on invoke
        mock_graph = Mock()
        mock_graph.invoke.side_effect = RuntimeError("Node execution failed")
        mock_build_graph.return_value = mock_graph

        # Execute and verify error
        with pytest.raises(WorkflowExecutionError) as exc_info:
            run_workflow_from_config(minimal_config, {"input": "test"})

        assert "Workflow execution failed" in str(exc_info.value)
        assert exc_info.value.phase == "workflow_execution"


# ============================================
# Tests: run_workflow (file loading)
# ============================================


def test_run_workflow_success(temp_config_file):
    """Test successful workflow execution from file."""
    # Create valid config file
    config_yaml = """
schema_version: "1.0"
flow:
  name: test_workflow
state:
  fields:
    input: {type: str, required: true}
    output: {type: str, default: ""}
nodes:
  - id: process
    prompt: "Process {state.input}"
    outputs: [output]
    output_schema:
      type: object
      fields:
        - name: output
          type: str
edges:
  - {from: START, to: process}
  - {from: process, to: END}
"""
    config_path = temp_config_file(config_yaml, "yaml")

    # Mock execution
    with patch(
        "configurable_agents.runtime.executor.run_workflow_from_config"
    ) as mock_run:
        mock_run.return_value = {"input": "test", "output": "result"}

        # Execute
        result = run_workflow(str(config_path), {"input": "test"})

        # Verify
        assert result == {"input": "test", "output": "result"}
        mock_run.assert_called_once()


def test_run_workflow_file_not_found():
    """Test error when config file not found."""
    with pytest.raises(ConfigLoadError) as exc_info:
        run_workflow("nonexistent.yaml", {"input": "test"})

    assert "Config file not found" in str(exc_info.value)
    assert exc_info.value.phase == "config_load"


def test_run_workflow_invalid_yaml(temp_config_file):
    """Test error with invalid YAML syntax."""
    config_path = temp_config_file("invalid: yaml: syntax:", "yaml")

    with pytest.raises(ConfigLoadError) as exc_info:
        run_workflow(str(config_path), {"input": "test"})

    assert "Failed to parse config file" in str(exc_info.value)
    assert exc_info.value.phase == "config_parse"


def test_run_workflow_invalid_schema(temp_config_file):
    """Test error with invalid config schema."""
    config_yaml = """
schema_version: "1.0"
flow:
  name: test
# Missing required fields: state, nodes, edges
"""
    config_path = temp_config_file(config_yaml, "yaml")

    with pytest.raises(ConfigValidationError) as exc_info:
        run_workflow(str(config_path), {"input": "test"})

    assert "Config schema validation failed" in str(exc_info.value)
    assert exc_info.value.phase == "schema_validation"


def test_run_workflow_json_format(temp_config_file):
    """Test workflow execution with JSON config."""
    config_json = """{
  "schema_version": "1.0",
  "flow": {"name": "test_workflow"},
  "state": {
    "fields": {
      "input": {"type": "str", "required": true},
      "output": {"type": "str", "default": ""}
    }
  },
  "nodes": [{
    "id": "process",
    "prompt": "Process {state.input}",
    "outputs": ["output"],
    "output_schema": {
      "type": "object",
      "fields": [{"name": "output", "type": "str"}]
    }
  }],
  "edges": [
    {"from": "START", "to": "process"},
    {"from": "process", "to": "END"}
  ]
}"""
    config_path = temp_config_file(config_json, "json")

    # Mock execution
    with patch(
        "configurable_agents.runtime.executor.run_workflow_from_config"
    ) as mock_run:
        mock_run.return_value = {"input": "test", "output": "result"}

        # Execute
        result = run_workflow(str(config_path), {"input": "test"})

        # Verify
        assert result == {"input": "test", "output": "result"}


def test_run_workflow_verbose_flag(temp_config_file):
    """Test verbose flag is passed through."""
    config_yaml = """
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input: {type: str, required: true}
    output: {type: str, default: ""}
nodes:
  - id: process
    prompt: "Process"
    outputs: [output]
    output_schema:
      type: object
      fields:
        - name: output
          type: str
edges:
  - {from: START, to: process}
  - {from: process, to: END}
"""
    config_path = temp_config_file(config_yaml, "yaml")

    with patch(
        "configurable_agents.runtime.executor.run_workflow_from_config"
    ) as mock_run:
        mock_run.return_value = {"input": "test", "output": "result"}

        # Execute with verbose=True
        run_workflow(str(config_path), {"input": "test"}, verbose=True)

        # Verify verbose was passed
        assert mock_run.call_args[1]["verbose"] is True


# ============================================
# Tests: validate_workflow
# ============================================


def test_validate_workflow_success(temp_config_file):
    """Test successful validation."""
    config_yaml = """
schema_version: "1.0"
flow:
  name: test_workflow
state:
  fields:
    input: {type: str, required: true}
    output: {type: str, default: ""}
nodes:
  - id: process
    prompt: "Process {state.input}"
    outputs: [output]
    output_schema:
      type: object
      fields:
        - name: output
          type: str
edges:
  - {from: START, to: process}
  - {from: process, to: END}
"""
    config_path = temp_config_file(config_yaml, "yaml")

    with (
        patch("configurable_agents.runtime.executor.validate_config"),
        patch("configurable_agents.runtime.executor.validate_runtime_support"),
    ):
        # Execute
        result = validate_workflow(str(config_path))

        # Verify
        assert result is True


def test_validate_workflow_file_not_found():
    """Test validation error when file not found."""
    with pytest.raises(ConfigLoadError) as exc_info:
        validate_workflow("nonexistent.yaml")

    assert "Config file not found" in str(exc_info.value)


def test_validate_workflow_invalid_yaml(temp_config_file):
    """Test validation error with invalid YAML."""
    config_path = temp_config_file("invalid: yaml: syntax:", "yaml")

    with pytest.raises(ConfigLoadError) as exc_info:
        validate_workflow(str(config_path))

    assert "Failed to parse config file" in str(exc_info.value)


def test_validate_workflow_invalid_schema(temp_config_file):
    """Test validation error with invalid schema."""
    config_yaml = """
schema_version: "1.0"
flow:
  name: test
# Missing required fields
"""
    config_path = temp_config_file(config_yaml, "yaml")

    with pytest.raises(ConfigValidationError) as exc_info:
        validate_workflow(str(config_path))

    assert "Config schema validation failed" in str(exc_info.value)


def test_validate_workflow_validation_error(temp_config_file):
    """Test validation error from validator."""
    config_yaml = """
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input: {type: str, required: true}
nodes:
  - id: process
    prompt: "Process"
    outputs: [missing_field]
    output_schema:
      type: object
      fields:
        - name: output
          type: str
edges:
  - {from: START, to: process}
  - {from: process, to: END}
"""
    config_path = temp_config_file(config_yaml, "yaml")

    with (
        patch("configurable_agents.runtime.executor.validate_config") as mock_validate,
    ):
        mock_validate.side_effect = ValidationError("Output field not found in state")

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_workflow(str(config_path))

        assert "Config validation failed" in str(exc_info.value)


def test_validate_workflow_unsupported_features(temp_config_file):
    """Test validation error with unsupported features."""
    config_yaml = """
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    input: {type: str, required: true}
    output: {type: str, default: ""}
nodes:
  - id: process
    prompt: "Process"
    outputs: [output]
    output_schema:
      type: object
      fields:
        - name: output
          type: str
edges:
  - from: START
    routes:
      - condition:
          logic: "{state.input} == 'test'"
        to: process
"""
    config_path = temp_config_file(config_yaml, "yaml")

    with (
        patch("configurable_agents.runtime.executor.validate_config"),
        patch(
            "configurable_agents.runtime.executor.validate_runtime_support"
        ) as mock_runtime,
    ):
        mock_runtime.side_effect = UnsupportedFeatureError(
            "Conditional routing", "v0.2", "8-12 weeks", "Use linear edges"
        )

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_workflow(str(config_path))

        assert "Unsupported features detected" in str(exc_info.value)


# ============================================
# Tests: Error Hierarchy
# ============================================


def test_execution_error_base_class():
    """Test ExecutionError base class."""
    error = ExecutionError("Test error", phase="test_phase")
    assert str(error) == "Test error"
    assert error.phase == "test_phase"
    assert error.original_error is None


def test_execution_error_with_original():
    """Test ExecutionError with original exception."""
    original = ValueError("Original error")
    error = ExecutionError("Wrapped error", phase="test", original_error=original)
    assert error.original_error == original


def test_all_error_types_inherit_from_execution_error():
    """Test error class hierarchy."""
    assert issubclass(ConfigLoadError, ExecutionError)
    assert issubclass(ConfigValidationError, ExecutionError)
    assert issubclass(StateInitializationError, ExecutionError)
    assert issubclass(GraphBuildError, ExecutionError)
    assert issubclass(WorkflowExecutionError, ExecutionError)
