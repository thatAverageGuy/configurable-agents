"""Unit tests for MLFlowTracker with mocked MLFlow."""

from unittest.mock import MagicMock, patch, call
import pytest

from configurable_agents.config import (
    ObservabilityMLFlowConfig,
    WorkflowConfig,
    FlowMetadata,
    StateSchema,
    StateFieldConfig,
    NodeConfig,
    OutputSchema,
    EdgeConfig,
    GlobalConfig,
    LLMConfig,
)
from configurable_agents.observability.mlflow_tracker import MLFlowTracker


@pytest.fixture
def minimal_workflow_config():
    """Create a minimal workflow config for testing."""
    return WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="test_workflow", version="1.0.0"),
        state=StateSchema(
            fields={"topic": StateFieldConfig(type="str", required=True)}
        ),
        nodes=[
            NodeConfig(
                id="test_node",
                prompt="Test prompt",
                output_schema=OutputSchema(type="str"),
                outputs=["result"],
            )
        ],
        edges=[
            EdgeConfig(from_="START", to="test_node"),
            EdgeConfig(from_="test_node", to="END"),
        ],
    )


@pytest.fixture
def mlflow_config():
    """Create MLFlow configuration."""
    return ObservabilityMLFlowConfig(
        enabled=True,
        tracking_uri="file://./mlruns",
        experiment_name="test_experiment",
        log_artifacts=True,
    )


@pytest.fixture
def mlflow_mock():
    """Create a mock MLFlow module."""
    with patch("configurable_agents.observability.mlflow_tracker.mlflow") as mock:
        with patch("configurable_agents.observability.mlflow_tracker.MLFLOW_AVAILABLE", True):
            # Setup common mock behaviors
            mock.active_run.return_value = MagicMock()
            mock.set_experiment.return_value = MagicMock(experiment_id="exp_123")
            yield mock


class TestMLFlowTrackerInitialization:
    """Test MLFlowTracker initialization."""

    def test_init_disabled_when_config_none(self, minimal_workflow_config):
        """Test that tracker is disabled when config is None."""
        tracker = MLFlowTracker(None, minimal_workflow_config)

        assert tracker.enabled is False

    def test_init_disabled_when_enabled_false(self, minimal_workflow_config):
        """Test that tracker is disabled when enabled=False."""
        config = ObservabilityMLFlowConfig(enabled=False)
        tracker = MLFlowTracker(config, minimal_workflow_config)

        assert tracker.enabled is False

    def test_init_enabled_with_valid_config(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that tracker is enabled with valid config and MLFlow available."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        assert tracker.enabled is True
        mlflow_mock.set_tracking_uri.assert_called_once_with("file://./mlruns")
        mlflow_mock.set_experiment.assert_called_once_with("test_experiment")

    def test_init_handles_mlflow_initialization_error(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that tracker handles MLFlow initialization errors gracefully."""
        mlflow_mock.set_tracking_uri.side_effect = Exception("MLFlow error")

        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        # Should disable tracking instead of crashing
        assert tracker.enabled is False


class TestMLFlowTrackerWorkflowTracking:
    """Test workflow-level tracking."""

    def test_track_workflow_disabled(self, minimal_workflow_config):
        """Test that track_workflow is no-op when disabled."""
        tracker = MLFlowTracker(None, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            pass  # Should not raise

    def test_track_workflow_starts_run(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that track_workflow starts an MLFlow run."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            pass

        mlflow_mock.start_run.assert_called_once()
        mlflow_mock.end_run.assert_called_once()

    def test_track_workflow_logs_params(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that track_workflow logs parameters."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            pass

        # Check that workflow params were logged
        assert mlflow_mock.log_param.called
        logged_params = {
            call.args[0]: call.args[1]
            for call in mlflow_mock.log_param.call_args_list
        }
        assert "workflow_name" in logged_params
        assert logged_params["workflow_name"] == "test_workflow"

    def test_track_workflow_logs_inputs_as_artifact(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that track_workflow logs inputs as artifact."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            pass

        # Check that inputs were logged as artifact
        mlflow_mock.log_dict.assert_called()
        calls = mlflow_mock.log_dict.call_args_list
        input_calls = [c for c in calls if c.args[1] == "inputs.json"]
        assert len(input_calls) == 1
        assert input_calls[0].args[0] == inputs

    def test_track_workflow_skips_artifacts_when_disabled(
        self, minimal_workflow_config, mlflow_mock
    ):
        """Test that artifacts are not logged when log_artifacts=False."""
        config = ObservabilityMLFlowConfig(
            enabled=True,
            log_artifacts=False,
        )
        tracker = MLFlowTracker(config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            pass

        # Inputs should not be logged
        mlflow_mock.log_dict.assert_not_called()

    def test_track_workflow_handles_errors(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that track_workflow handles errors and logs them."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with pytest.raises(ValueError):
            with tracker.track_workflow(inputs):
                raise ValueError("Test error")

        # Run should still end
        mlflow_mock.end_run.assert_called_once()

    def test_finalize_workflow_logs_metrics(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that finalize_workflow logs metrics."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        final_state = {"topic": "AI", "result": "article"}

        with tracker.track_workflow(inputs):
            tracker.finalize_workflow(final_state, status="success")

        # Check that metrics were logged
        assert mlflow_mock.log_metric.called
        logged_metrics = {
            call.args[0]: call.args[1]
            for call in mlflow_mock.log_metric.call_args_list
        }
        assert "duration_seconds" in logged_metrics
        assert "status" in logged_metrics
        assert logged_metrics["status"] == 1  # 1 = success


class TestMLFlowTrackerNodeTracking:
    """Test node-level tracking."""

    def test_track_node_disabled(self, minimal_workflow_config):
        """Test that track_node is no-op when disabled."""
        tracker = MLFlowTracker(None, minimal_workflow_config)

        with tracker.track_node("test_node", "gemini-1.5-flash"):
            pass  # Should not raise

    def test_track_node_creates_nested_run(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that track_node creates a nested run."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            with tracker.track_node("test_node", "gemini-1.5-flash"):
                pass

        # Check that nested run was started
        assert mlflow_mock.start_run.call_count >= 2  # Parent + nested

    def test_track_node_logs_params(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that track_node logs parameters."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            with tracker.track_node("test_node", "gemini-1.5-flash", tools=["search"]):
                pass

        # Check that node params were logged
        assert mlflow_mock.log_param.called

    def test_log_node_metrics(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that log_node_metrics logs metrics and updates totals."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            with tracker.track_node("test_node", "gemini-1.5-flash"):
                tracker.log_node_metrics(
                    input_tokens=150,
                    output_tokens=500,
                    model="gemini-1.5-flash",
                    retries=0,
                    prompt="Test prompt",
                    response="Test response",
                )

            tracker.finalize_workflow({}, status="success")

        # Check that node metrics were logged
        logged_metrics = {
            call.args[0]: call.args[1]
            for call in mlflow_mock.log_metric.call_args_list
        }
        assert "input_tokens" in logged_metrics
        assert "output_tokens" in logged_metrics
        assert "node_cost_usd" in logged_metrics

        # Check that totals were updated
        assert "total_input_tokens" in logged_metrics
        assert logged_metrics["total_input_tokens"] == 150
        assert "total_output_tokens" in logged_metrics
        assert logged_metrics["total_output_tokens"] == 500
        assert "total_cost_usd" in logged_metrics

    def test_log_node_metrics_with_artifacts(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that log_node_metrics logs artifacts when enabled."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            with tracker.track_node("test_node", "gemini-1.5-flash"):
                tracker.log_node_metrics(
                    input_tokens=150,
                    output_tokens=500,
                    model="gemini-1.5-flash",
                    prompt="Test prompt",
                    response="Test response",
                )

        # Check that prompt and response were logged
        assert mlflow_mock.log_text.called
        text_calls = mlflow_mock.log_text.call_args_list
        assert any("prompt.txt" in str(c) for c in text_calls)
        assert any("response.txt" in str(c) for c in text_calls)

    def test_log_node_metrics_accumulates_totals(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that multiple node executions accumulate totals."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            # First node
            with tracker.track_node("node1", "gemini-1.5-flash"):
                tracker.log_node_metrics(
                    input_tokens=100,
                    output_tokens=200,
                    model="gemini-1.5-flash",
                )

            # Second node
            with tracker.track_node("node2", "gemini-1.5-flash"):
                tracker.log_node_metrics(
                    input_tokens=150,
                    output_tokens=300,
                    model="gemini-1.5-flash",
                )

            tracker.finalize_workflow({}, status="success")

        # Check totals
        logged_metrics = {
            call.args[0]: call.args[1]
            for call in mlflow_mock.log_metric.call_args_list
        }
        assert logged_metrics["total_input_tokens"] == 250  # 100 + 150
        assert logged_metrics["total_output_tokens"] == 500  # 200 + 300


class TestMLFlowTrackerCostTracking:
    """Test cost tracking functionality."""

    def test_cost_estimation_integration(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that cost estimator is integrated correctly."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            with tracker.track_node("test_node", "gemini-1.5-flash"):
                tracker.log_node_metrics(
                    input_tokens=150,
                    output_tokens=500,
                    model="gemini-1.5-flash",
                )

            tracker.finalize_workflow({}, status="success")

        # Check that cost was calculated and logged
        logged_metrics = {
            call.args[0]: call.args[1]
            for call in mlflow_mock.log_metric.call_args_list
        }
        assert "node_cost_usd" in logged_metrics
        assert logged_metrics["node_cost_usd"] > 0
        assert "total_cost_usd" in logged_metrics
        assert logged_metrics["total_cost_usd"] > 0


class TestMLFlowTrackerGlobalConfig:
    """Test tracking with global config."""

    def test_logs_global_llm_config(self, mlflow_config, minimal_workflow_config, mlflow_mock):
        """Test that global LLM config is logged."""
        # Add global LLM config
        workflow_config = minimal_workflow_config
        workflow_config.config = GlobalConfig(
            llm=LLMConfig(
                provider="google",
                model="gemini-1.5-flash",
                temperature=0.7,
            )
        )

        tracker = MLFlowTracker(mlflow_config, workflow_config)

        inputs = {"topic": "AI"}
        with tracker.track_workflow(inputs):
            pass

        # Check that global config was logged
        logged_params = {
            call.args[0]: call.args[1]
            for call in mlflow_mock.log_param.call_args_list
        }
        assert "global_provider" in logged_params
        assert logged_params["global_provider"] == "google"
        assert "global_model" in logged_params
        assert logged_params["global_model"] == "gemini-1.5-flash"
        assert "global_temperature" in logged_params
        assert logged_params["global_temperature"] == 0.7
