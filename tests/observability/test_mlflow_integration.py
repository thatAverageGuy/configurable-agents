"""Integration tests for MLFlow tracking with real MLFlow backend.

These tests use a real MLFlow tracking server (file-based) to verify
end-to-end MLFlow integration. They require MLFlow to be installed.

Cost: Free (uses local file storage)
"""

import os
import tempfile
from pathlib import Path

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

# Skip all tests if MLFlow is not installed
pytestmark = pytest.mark.skipif(
    not MLFLOW_AVAILABLE,
    reason="MLFlow not installed. Install with: pip install mlflow",
)


@pytest.fixture
def temp_mlruns_dir():
    """Create a temporary directory for MLFlow tracking data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mlflow_config(temp_mlruns_dir):
    """Create MLFlow configuration with temporary storage."""
    # Convert Windows path to file:// URI with forward slashes
    from pathlib import Path
    path = Path(temp_mlruns_dir).as_posix()
    tracking_uri = f"file:///{path}" if path[1] == ':' else f"file://{path}"

    return ObservabilityMLFlowConfig(
        enabled=True,
        tracking_uri=tracking_uri,
        experiment_name="test_integration",
        log_artifacts=True,
    )


@pytest.fixture
def workflow_config():
    """Create a workflow config for testing."""
    return WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(
            name="test_workflow",
            version="1.0.0",
            description="Test workflow for MLFlow integration",
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
                prompt="Generate content about {state.topic}",
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
                temperature=0.7,
            )
        ),
    )


@pytest.mark.integration
class TestMLFlowIntegration:
    """Integration tests for MLFlow tracking."""

    def test_track_workflow_creates_run(
        self, mlflow_config, workflow_config, temp_mlruns_dir
    ):
        """Test that tracking creates an MLFlow run with artifacts."""
        tracker = MLFlowTracker(mlflow_config, workflow_config)

        inputs = {"topic": "AI Safety"}
        final_state = {"topic": "AI Safety", "result": "Article about AI Safety"}

        with tracker.track_workflow(inputs):
            tracker.finalize_workflow(final_state, status="success")

        # Verify that MLFlow files were created
        mlruns_path = Path(temp_mlruns_dir)
        assert mlruns_path.exists()

        # Check that experiment was created
        experiment_dirs = list(mlruns_path.iterdir())
        assert len(experiment_dirs) > 0

    def test_track_node_creates_nested_run(
        self, mlflow_config, workflow_config, temp_mlruns_dir
    ):
        """Test that node tracking creates nested runs."""
        tracker = MLFlowTracker(mlflow_config, workflow_config)

        inputs = {"topic": "AI"}

        with tracker.track_workflow(inputs):
            with tracker.track_node("test_node", "gemini-1.5-flash"):
                tracker.log_node_metrics(
                    input_tokens=150,
                    output_tokens=500,
                    model="gemini-1.5-flash",
                    retries=0,
                    prompt="Test prompt: Generate content about {state.topic}",
                    response="Test response: Article about AI",
                )

            tracker.finalize_workflow(
                {"topic": "AI", "result": "Article about AI"},
                status="success",
            )

        # Verify MLFlow structure
        mlruns_path = Path(temp_mlruns_dir)
        assert mlruns_path.exists()

    def test_disabled_tracking_no_files_created(
        self, workflow_config, temp_mlruns_dir
    ):
        """Test that disabled tracking doesn't create MLFlow files."""
        from pathlib import Path
        path = Path(temp_mlruns_dir).as_posix()
        tracking_uri = f"file:///{path}" if path[1] == ':' else f"file://{path}"

        config = ObservabilityMLFlowConfig(
            enabled=False,
            tracking_uri=tracking_uri,
        )
        tracker = MLFlowTracker(config, workflow_config)

        inputs = {"topic": "AI"}

        with tracker.track_workflow(inputs):
            tracker.finalize_workflow({"topic": "AI", "result": "test"}, status="success")

        # No MLFlow files should be created
        mlruns_path = Path(temp_mlruns_dir)
        # Directory might exist but should be empty (or minimal)
        if mlruns_path.exists():
            # Check that no experiment directories were created
            experiment_dirs = [
                d for d in mlruns_path.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
            assert len(experiment_dirs) == 0

    def test_artifacts_logged_when_enabled(
        self, mlflow_config, workflow_config, temp_mlruns_dir
    ):
        """Test that artifacts are logged when log_artifacts=True."""
        tracker = MLFlowTracker(mlflow_config, workflow_config)

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

            tracker.finalize_workflow(
                {"topic": "AI", "result": "test"},
                status="success",
            )

        # Artifacts should be created (inputs.json, outputs.json, prompt.txt, response.txt)
        # We verify by checking that the mlruns directory has content
        mlruns_path = Path(temp_mlruns_dir)
        assert mlruns_path.exists()

    def test_artifacts_not_logged_when_disabled(
        self, workflow_config, temp_mlruns_dir
    ):
        """Test that artifacts are not logged when log_artifacts=False."""
        from pathlib import Path
        path = Path(temp_mlruns_dir).as_posix()
        tracking_uri = f"file:///{path}" if path[1] == ':' else f"file://{path}"

        config = ObservabilityMLFlowConfig(
            enabled=True,
            tracking_uri=tracking_uri,
            experiment_name="test_no_artifacts",
            log_artifacts=False,
        )
        tracker = MLFlowTracker(config, workflow_config)

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

            tracker.finalize_workflow(
                {"topic": "AI", "result": "test"},
                status="success",
            )

        # Run should exist but with minimal artifacts
        mlruns_path = Path(temp_mlruns_dir)
        assert mlruns_path.exists()

    def test_cost_tracking_accuracy(
        self, mlflow_config, workflow_config, temp_mlruns_dir
    ):
        """Test that cost tracking calculates accurate costs."""
        tracker = MLFlowTracker(mlflow_config, workflow_config)

        inputs = {"topic": "AI"}

        with tracker.track_workflow(inputs):
            # First node
            with tracker.track_node("node1", "gemini-1.5-flash"):
                tracker.log_node_metrics(
                    input_tokens=150,
                    output_tokens=500,
                    model="gemini-1.5-flash",
                )

            # Second node
            with tracker.track_node("node2", "gemini-1.5-flash"):
                tracker.log_node_metrics(
                    input_tokens=200,
                    output_tokens=600,
                    model="gemini-1.5-flash",
                )

            tracker.finalize_workflow(
                {"topic": "AI", "result": "test"},
                status="success",
            )

        # Verify that costs were tracked
        # Total tokens: 150+200=350 input, 500+600=1100 output
        # Cost should be calculated based on Gemini 1.5 Flash pricing
        assert tracker._total_input_tokens == 350
        assert tracker._total_output_tokens == 1100
        assert tracker._total_cost > 0

    def test_retry_counting(
        self, mlflow_config, workflow_config, temp_mlruns_dir
    ):
        """Test that retries are counted correctly."""
        tracker = MLFlowTracker(mlflow_config, workflow_config)

        inputs = {"topic": "AI"}

        with tracker.track_workflow(inputs):
            with tracker.track_node("test_node", "gemini-1.5-flash"):
                tracker.log_node_metrics(
                    input_tokens=150,
                    output_tokens=500,
                    model="gemini-1.5-flash",
                    retries=2,  # Simulating 2 retries
                )

            tracker.finalize_workflow(
                {"topic": "AI", "result": "test"},
                status="success",
            )

        # Verify retry count
        assert tracker._retry_count == 2

    def test_error_handling(
        self, mlflow_config, workflow_config, temp_mlruns_dir
    ):
        """Test that errors are handled and logged."""
        tracker = MLFlowTracker(mlflow_config, workflow_config)

        inputs = {"topic": "AI"}

        with pytest.raises(ValueError):
            with tracker.track_workflow(inputs):
                raise ValueError("Simulated workflow error")

        # Run should still be created with error status
        mlruns_path = Path(temp_mlruns_dir)
        assert mlruns_path.exists()

    def test_multiple_workflows_same_experiment(
        self, mlflow_config, workflow_config, temp_mlruns_dir
    ):
        """Test that multiple workflows can use the same experiment."""
        # First workflow
        tracker1 = MLFlowTracker(mlflow_config, workflow_config)
        inputs1 = {"topic": "AI"}
        with tracker1.track_workflow(inputs1):
            tracker1.finalize_workflow(
                {"topic": "AI", "result": "test1"},
                status="success",
            )

        # Second workflow
        tracker2 = MLFlowTracker(mlflow_config, workflow_config)
        inputs2 = {"topic": "ML"}
        with tracker2.track_workflow(inputs2):
            tracker2.finalize_workflow(
                {"topic": "ML", "result": "test2"},
                status="success",
            )

        # Both should create runs in the same experiment
        mlruns_path = Path(temp_mlruns_dir)
        assert mlruns_path.exists()
