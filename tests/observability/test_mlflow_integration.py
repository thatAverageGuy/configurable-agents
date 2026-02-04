"""Integration tests for MLFlow 3.9 tracking with real MLFlow backend."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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
from configurable_agents.observability.mlflow_tracker import (
    MLFlowTracker,
    MLFLOW_AVAILABLE,
)

pytestmark = pytest.mark.skipif(
    not MLFLOW_AVAILABLE,
    reason="MLFlow not installed. Install with: pip install mlflow>=3.9.0",
)


@pytest.fixture
def temp_mlruns_dir():
    """Create a temporary directory for MLFlow tracking data."""
    import mlflow
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    # Close MLflow connections before cleanup
    try:
        mlflow.end_run()
    except:
        pass
    # Give Windows time to release file handles
    import time
    time.sleep(0.1)
    import shutil
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except:
        pass


@pytest.fixture
def mlflow_config(temp_mlruns_dir):
    """Create MLFlow configuration with SQLite backend."""
    db_path = Path(temp_mlruns_dir) / "mlflow.db"
    tracking_uri = f"sqlite:///{db_path.as_posix()}"

    return ObservabilityMLFlowConfig(
        enabled=True,
        tracking_uri=tracking_uri,
        experiment_name="test_integration",
        log_artifacts=True,
        async_logging=False,  # Disable async for tests
    )


@pytest.fixture
def workflow_config():
    """Create a workflow config for testing."""
    return WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(
            name="test_workflow",
            version="1.0.0",
        ),
        state=StateSchema(
            fields={
                "topic": StateFieldConfig(type="str", required=True),
                "result": StateFieldConfig(type="str", required=False),
            }
        ),
        nodes=[
            NodeConfig(
                id="test_node",
                prompt="Generate content about {topic}",
                output_schema=OutputSchema(type="str"),
                outputs=["result"],
            )
        ],
        edges=[
            EdgeConfig(from_="START", to="test_node"),
            EdgeConfig(from_="test_node", to="END"),
        ],
        config=GlobalConfig(
            llm=LLMConfig(
                provider="google",
                model="gemini-1.5-flash",
            )
        ),
    )


@pytest.mark.integration
class TestMLFlowIntegration:
    """Integration tests for MLFlow 3.9 tracking."""

    def test_initialization_creates_experiment(
        self, mlflow_config, workflow_config
    ):
        """Test that tracker initialization creates experiment."""
        tracker = MLFlowTracker(mlflow_config, workflow_config)

        assert tracker.enabled is True
        # Verify experiment was created (integration with real MLflow)
        import mlflow
        experiment = mlflow.get_experiment_by_name("test_integration")
        assert experiment is not None

    def test_disabled_tracking_no_initialization(
        self, workflow_config, temp_mlruns_dir
    ):
        """Test that disabled tracking doesn't initialize MLflow."""
        config = ObservabilityMLFlowConfig(enabled=False)
        tracker = MLFlowTracker(config, workflow_config)

        assert tracker.enabled is False

    def test_trace_decorator_returns_callable(
        self, mlflow_config, workflow_config
    ):
        """Test that get_trace_decorator returns working decorator."""
        tracker = MLFlowTracker(mlflow_config, workflow_config)

        decorator = tracker.get_trace_decorator(
            "workflow_test",
            workflow_name="test_workflow"
        )

        @decorator
        def test_func():
            return "result"

        # Should execute without error
        result = test_func()
        assert result == "result"

    def test_cost_summary_with_mock_trace(
        self, mlflow_config, workflow_config
    ):
        """Test cost summary extraction from trace."""
        tracker = MLFlowTracker(mlflow_config, workflow_config)

        # Mock a trace with token usage
        mock_span = MagicMock()
        mock_span.name = "test_node"
        mock_span.attributes = {
            "mlflow.chat.tokenUsage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
            },
            "ai.model.name": "gemini-1.5-flash",
        }
        mock_span.start_time_ns = 1000000000
        mock_span.end_time_ns = 2000000000

        mock_trace = MagicMock()
        mock_trace.info.trace_id = "test_trace"
        mock_trace.info.token_usage = {}
        mock_trace.data.spans = [mock_span]

        with patch("mlflow.search_traces", return_value=[mock_trace]):
            with patch("mlflow.get_experiment_by_name", return_value=MagicMock(experiment_id="1")):
                summary = tracker.get_workflow_cost_summary()

        assert summary["trace_id"] == "test_trace"
        assert summary["total_cost_usd"] > 0
        assert "test_node" in summary["node_breakdown"]

    def test_log_summary_creates_metrics(
        self, mlflow_config, workflow_config
    ):
        """Test that log_workflow_summary logs metrics."""
        tracker = MLFlowTracker(mlflow_config, workflow_config)

        cost_summary = {
            "total_cost_usd": 0.001,
            "total_tokens": {"total_tokens": 300, "prompt_tokens": 100, "completion_tokens": 200},
            "node_breakdown": {"node1": {}},
        }

        with patch("mlflow.active_run", return_value=MagicMock()):
            with patch("mlflow.log_metrics") as mock_log:
                with patch("mlflow.log_dict"):
                    tracker.log_workflow_summary(cost_summary)

                mock_log.assert_called_once()
                logged = mock_log.call_args.args[0]
                assert logged["total_cost_usd"] == 0.001
                assert logged["total_tokens"] == 300

    def test_artifact_levels(self, workflow_config, temp_mlruns_dir):
        """Test artifact level configuration."""
        db_path = Path(temp_mlruns_dir) / "mlflow.db"

        # Test minimal level
        config = ObservabilityMLFlowConfig(
            enabled=True,
            tracking_uri=f"sqlite:///{db_path.as_posix()}",
            log_artifacts=True,
            artifact_level="minimal",
        )
        tracker = MLFlowTracker(config, workflow_config)

        assert tracker._should_log_artifacts("minimal") is True
        assert tracker._should_log_artifacts("standard") is False
        assert tracker._should_log_artifacts("full") is False

    def test_graceful_degradation_on_error(self, workflow_config, temp_mlruns_dir):
        """Test that tracker degrades gracefully on MLflow errors."""
        db_path = Path(temp_mlruns_dir) / "mlflow.db"
        config = ObservabilityMLFlowConfig(
            enabled=True,
            tracking_uri=f"sqlite:///{db_path.as_posix()}",
        )

        # Mock MLflow to raise error during initialization
        with patch("mlflow.set_tracking_uri", side_effect=Exception("MLflow error")):
            tracker = MLFlowTracker(config, workflow_config)

            # Should disable tracking instead of crashing
            assert tracker.enabled is False
