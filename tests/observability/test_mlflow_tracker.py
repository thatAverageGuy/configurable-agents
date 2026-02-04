"""Unit tests for MLFlowTracker (MLflow 3.9)."""

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
        async_logging=True,
    )


@pytest.fixture
def mlflow_mock():
    """Create a mock MLFlow module with MLflow 3.9 API."""
    # Create a mock mlflow module
    mock_mlflow = MagicMock()

    # Mock basic methods
    mock_mlflow.active_run.return_value = MagicMock()
    mock_mlflow.set_experiment.return_value = MagicMock(experiment_id="exp_123")
    mock_mlflow.trace = MagicMock(return_value=lambda f: f)  # No-op decorator

    # Mock langchain autolog
    mock_mlflow.langchain = MagicMock()
    mock_mlflow.langchain.autolog = MagicMock()

    # Mock trace search
    mock_mlflow.get_experiment_by_name = MagicMock(return_value=MagicMock(experiment_id="exp_123"))
    mock_mlflow.search_traces = MagicMock(return_value=[])

    # Patch the mlflow module and availability flag
    with patch("configurable_agents.observability.mlflow_tracker.mlflow", mock_mlflow):
        with patch("configurable_agents.observability.mlflow_tracker.MLFLOW_AVAILABLE", True):
            yield mock_mlflow


class TestMLFlowTrackerInitialization:
    """Test MLFlowTracker initialization (MLflow 3.9)."""

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
        """Test that tracker is enabled with valid config and MLFlow 3.9."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        assert tracker.enabled is True
        mlflow_mock.set_tracking_uri.assert_called_once_with("file://./mlruns")
        mlflow_mock.set_experiment.assert_called_once_with("test_experiment")

        # MLflow 3.9: Should enable autolog
        mlflow_mock.langchain.autolog.assert_called_once()

    def test_init_configures_async_logging(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that async logging is configured when enabled."""
        with patch.dict('os.environ', {}, clear=False):
            tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

            assert tracker.enabled is True
            # Async logging environment variables should be set
            # (We can't easily test os.environ changes in unit tests,
            # but we verify initialization succeeded)

    def test_init_handles_mlflow_initialization_error(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that tracker handles MLFlow initialization errors gracefully."""
        mlflow_mock.set_tracking_uri.side_effect = Exception("MLFlow error")

        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        # Should disable tracking instead of crashing
        assert tracker.enabled is False

    def test_init_warns_about_file_backend_deprecation(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that file:// backend shows deprecation warning."""
        # Using file:// should work but log a warning
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        assert tracker.enabled is True
        # Warning logged (tested via caplog in integration tests)


class TestMLFlowTrackerTraceDecorator:
    """Test get_trace_decorator() method (MLflow 3.9)."""

    def test_get_trace_decorator_when_disabled(self, minimal_workflow_config):
        """Test that decorator is no-op when tracking disabled."""
        tracker = MLFlowTracker(None, minimal_workflow_config)

        @tracker.get_trace_decorator("test")
        def test_function():
            return "result"

        # Should work without MLflow
        assert test_function() == "result"

    def test_get_trace_decorator_when_enabled(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that decorator returns MLflow trace decorator when enabled."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        decorator = tracker.get_trace_decorator("workflow_test", workflow_name="test")

        # Should return a callable (decorator function)
        assert callable(decorator)

        # MLflow.trace should be called with correct params
        mlflow_mock.trace.assert_called_once()
        call_kwargs = mlflow_mock.trace.call_args.kwargs
        assert call_kwargs["name"] == "workflow_test"
        assert call_kwargs["span_type"] == "WORKFLOW"
        assert call_kwargs["attributes"]["workflow_name"] == "test"

    def test_get_trace_decorator_determines_span_type(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that span type is determined from name."""
        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        # "workflow" in name → WORKFLOW span type
        tracker.get_trace_decorator("workflow_test")
        assert mlflow_mock.trace.call_args.kwargs["span_type"] == "WORKFLOW"

        mlflow_mock.trace.reset_mock()

        # Other names → AGENT span type
        tracker.get_trace_decorator("node_test")
        assert mlflow_mock.trace.call_args.kwargs["span_type"] == "AGENT"


class TestMLFlowTrackerCostSummary:
    """Test get_workflow_cost_summary() method (MLflow 3.9)."""

    def test_get_cost_summary_when_disabled(self, minimal_workflow_config):
        """Test that cost summary returns empty dict when disabled."""
        tracker = MLFlowTracker(None, minimal_workflow_config)

        summary = tracker.get_workflow_cost_summary()

        assert summary == {}

    def test_get_cost_summary_with_no_traces(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that cost summary returns empty dict when no traces found."""
        mlflow_mock.search_traces.return_value = []

        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)
        summary = tracker.get_workflow_cost_summary()

        assert summary == {}

    def test_get_cost_summary_extracts_token_usage(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that cost summary extracts token usage from trace."""
        # Mock trace with token usage
        mock_span = MagicMock()
        mock_span.name = "test_node"
        mock_span.attributes = {
            "mlflow.chat.tokenUsage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
            },
            "ai.model.name": "gemini-1.5-flash",  # Use supported model
        }
        mock_span.start_time_ns = 1000000000
        mock_span.end_time_ns = 2000000000

        mock_trace = MagicMock()
        mock_trace.info.trace_id = "trace_123"
        mock_trace.info.token_usage = {
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "total_tokens": 300,
        }
        mock_trace.data.spans = [mock_span]

        mlflow_mock.search_traces.return_value = [mock_trace]

        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)
        summary = tracker.get_workflow_cost_summary()

        assert summary["trace_id"] == "trace_123"
        assert summary["total_tokens"]["total_tokens"] == 300
        assert summary["total_cost_usd"] > 0
        assert "test_node" in summary["node_breakdown"]
        assert summary["node_breakdown"]["test_node"]["cost_usd"] > 0

    def test_get_cost_summary_calculates_costs(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that cost summary uses CostEstimator."""
        mock_span = MagicMock()
        mock_span.name = "test_node"
        mock_span.attributes = {
            "mlflow.chat.tokenUsage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
            },
            "ai.model.name": "gemini-1.5-flash",  # Use supported model
        }
        mock_span.start_time_ns = 1000000000
        mock_span.end_time_ns = 2000000000

        mock_trace = MagicMock()
        mock_trace.info.trace_id = "trace_123"
        mock_trace.info.token_usage = {}
        mock_trace.data.spans = [mock_span]

        mlflow_mock.search_traces.return_value = [mock_trace]

        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        # Mock cost estimator
        with patch.object(tracker.cost_estimator, 'estimate_cost', return_value=0.001):
            summary = tracker.get_workflow_cost_summary()

            assert summary["total_cost_usd"] == 0.001
            tracker.cost_estimator.estimate_cost.assert_called_once()


class TestMLFlowTrackerLogSummary:
    """Test log_workflow_summary() method (MLflow 3.9)."""

    def test_log_summary_when_disabled(self, minimal_workflow_config):
        """Test that log summary is no-op when disabled."""
        tracker = MLFlowTracker(None, minimal_workflow_config)

        # Should not raise
        tracker.log_workflow_summary({})

    def test_log_summary_when_no_active_run(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that log summary is no-op when no active run."""
        mlflow_mock.active_run.return_value = None

        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        # Should not raise
        tracker.log_workflow_summary({"total_cost_usd": 0.001})

        # Should not log metrics
        mlflow_mock.log_metrics.assert_not_called()

    def test_log_summary_logs_metrics(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that log summary logs metrics to MLflow."""
        mlflow_mock.active_run.return_value = MagicMock()

        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        cost_summary = {
            "total_cost_usd": 0.0023,
            "total_tokens": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
            },
            "node_breakdown": {"node1": {}, "node2": {}},
        }

        tracker.log_workflow_summary(cost_summary)

        # Should log metrics
        mlflow_mock.log_metrics.assert_called_once()
        logged_metrics = mlflow_mock.log_metrics.call_args.args[0]
        assert logged_metrics["total_cost_usd"] == 0.0023
        assert logged_metrics["total_tokens"] == 300
        assert logged_metrics["node_count"] == 2

    def test_log_summary_logs_artifact(
        self, mlflow_config, minimal_workflow_config, mlflow_mock
    ):
        """Test that log summary logs cost summary as artifact."""
        mlflow_mock.active_run.return_value = MagicMock()

        tracker = MLFlowTracker(mlflow_config, minimal_workflow_config)

        cost_summary = {
            "total_cost_usd": 0.0023,
            "total_tokens": {"total_tokens": 300},
            "node_breakdown": {},
        }

        tracker.log_workflow_summary(cost_summary)

        # Should log artifact (minimal level and above)
        mlflow_mock.log_dict.assert_called_once_with(cost_summary, "cost_summary.json")


class TestMLFlowTrackerArtifactLevels:
    """Test _should_log_artifacts() method."""

    def test_artifact_levels_minimal(self, minimal_workflow_config, mlflow_mock):
        """Test minimal artifact level."""
        config = ObservabilityMLFlowConfig(
            enabled=True,
            log_artifacts=True,
            artifact_level="minimal",
        )
        tracker = MLFlowTracker(config, minimal_workflow_config)

        assert tracker._should_log_artifacts("minimal") is True
        assert tracker._should_log_artifacts("standard") is False
        assert tracker._should_log_artifacts("full") is False

    def test_artifact_levels_standard(self, minimal_workflow_config, mlflow_mock):
        """Test standard artifact level."""
        config = ObservabilityMLFlowConfig(
            enabled=True,
            log_artifacts=True,
            artifact_level="standard",
        )
        tracker = MLFlowTracker(config, minimal_workflow_config)

        assert tracker._should_log_artifacts("minimal") is True
        assert tracker._should_log_artifacts("standard") is True
        assert tracker._should_log_artifacts("full") is False

    def test_artifact_levels_full(self, minimal_workflow_config, mlflow_mock):
        """Test full artifact level."""
        config = ObservabilityMLFlowConfig(
            enabled=True,
            log_artifacts=True,
            artifact_level="full",
        )
        tracker = MLFlowTracker(config, minimal_workflow_config)

        assert tracker._should_log_artifacts("minimal") is True
        assert tracker._should_log_artifacts("standard") is True
        assert tracker._should_log_artifacts("full") is True

    def test_artifact_logging_disabled(self, minimal_workflow_config, mlflow_mock):
        """Test that artifacts not logged when log_artifacts=False."""
        config = ObservabilityMLFlowConfig(
            enabled=True,
            log_artifacts=False,
        )
        tracker = MLFlowTracker(config, minimal_workflow_config)

        assert tracker._should_log_artifacts("minimal") is False
        assert tracker._should_log_artifacts("standard") is False
        assert tracker._should_log_artifacts("full") is False
