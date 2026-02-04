"""Tests for A/B testing runner."""

from unittest.mock import MagicMock, Mock, patch
import pytest
import yaml

from configurable_agents.config import (
    WorkflowConfig,
    FlowMetadata,
    StateSchema,
    StateFieldConfig,
    NodeConfig,
    OutputSchema,
    EdgeConfig,
)
from configurable_agents.optimization.ab_test import (
    VariantConfig,
    ABTestConfig,
    ABTestRunner,
    ABTestResult,
    VariantResult,
    apply_prompt_to_workflow,
    run_ab_test,
    calculate_percentiles,
)


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
                prompt="Test prompt with {topic}",
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
def sample_variants():
    """Create sample variant configs."""
    return [
        VariantConfig(
            name="concise",
            prompt="Be concise and answer: {topic}"
        ),
        VariantConfig(
            name="detailed",
            prompt="Be detailed and thorough in your answer: {topic}"
        ),
    ]


@pytest.fixture
def mlflow_mock():
    """Create a mock MLFlow module."""
    mock_mlflow = MagicMock()

    # Mock experiment methods
    mock_exp = MagicMock()
    mock_exp.experiment_id = "exp_123"
    mock_mlflow.get_experiment_by_name.return_value = mock_exp
    mock_mlflow.create_experiment.return_value = "exp_123"

    # Mock run context
    mock_run = MagicMock()
    mock_run.info.run_id = "run_123"
    mock_mlflow.active_run.return_value = mock_run

    # Mock start_run context manager
    mock_run_context = MagicMock()
    mock_run_context.__enter__ = Mock(return_value=mock_run)
    mock_run_context.__exit__ = Mock(return_value=False)
    mock_mlflow.start_run.return_value = mock_run_context

    # Mock logging methods
    mock_mlflow.log_params = MagicMock()
    mock_mlflow.log_metrics = MagicMock()

    return mock_mlflow


class TestVariantConfig:
    """Test VariantConfig dataclass."""

    def test_variant_config_creation(self):
        """Test creating a variant config."""
        variant = VariantConfig(
            name="test_variant",
            prompt="Test prompt with {input}",
        )

        assert variant.name == "test_variant"
        assert variant.prompt == "Test prompt with {input}"
        assert variant.config_overrides is None
        assert variant.node_id is None

    def test_variant_config_with_overrides(self):
        """Test variant config with config overrides."""
        overrides = {"temperature": 0.5}
        variant = VariantConfig(
            name="test_variant",
            prompt="Test prompt",
            config_overrides=overrides,
        )

        assert variant.config_overrides == overrides

    def test_variant_equality(self):
        """Test variant equality comparison."""
        v1 = VariantConfig(name="test", prompt="Same prompt")
        v2 = VariantConfig(name="test", prompt="Same prompt")
        v3 = VariantConfig(name="test", prompt="Different prompt")

        assert v1 == v2
        assert v1 != v3

    def test_variant_hash(self):
        """Test variant hashing."""
        v1 = VariantConfig(name="test", prompt="Same prompt")
        v2 = VariantConfig(name="test", prompt="Same prompt")

        assert hash(v1) == hash(v2)


class TestABTestConfig:
    """Test ABTestConfig dataclass."""

    def test_ab_test_config_creation(self, sample_variants):
        """Test creating A/B test config."""
        config = ABTestConfig(
            experiment_name="test_experiment",
            variants=sample_variants,
            run_count=5,
        )

        assert config.experiment_name == "test_experiment"
        assert len(config.variants) == 2
        assert config.run_count == 5
        assert config.parallel is True  # Default value

    def test_ab_test_config_defaults(self):
        """Test default values."""
        variant = VariantConfig(name="test", prompt="Test")
        config = ABTestConfig(
            experiment_name="test_exp",
            variants=[variant],
        )

        assert config.run_count == 3  # Default
        assert config.parallel is True
        assert config.inputs == {}


class TestABTestRunner:
    """Test ABTestRunner class."""

    def test_runner_initialization(self):
        """Test runner initialization."""
        runner = ABTestRunner(mlflow_tracking_uri="file:///test_mlruns")

        assert runner.mlflow_tracking_uri == "file:///test_mlruns"

    @patch("configurable_agents.optimization.ab_test.MLFLOW_AVAILABLE", True)
    def test_apply_variant_to_config(self, minimal_workflow_config):
        """Test applying variant prompt to config."""
        variant = VariantConfig(
            name="new_prompt",
            prompt="New prompt with {topic}"
        )

        runner = ABTestRunner()
        modified = runner._apply_variant_to_config(minimal_workflow_config, variant)

        # First node's prompt should be updated
        assert modified.nodes[0].prompt == "New prompt with {topic}"

    @patch("configurable_agents.optimization.ab_test.MLFLOW_AVAILABLE", True)
    def test_apply_variant_to_specific_node(self, minimal_workflow_config):
        """Test applying variant to specific node."""
        # Add a second node
        minimal_workflow_config.nodes.append(
            NodeConfig(
                id="second_node",
                prompt="Second prompt",
                output_schema=OutputSchema(type="str"),
                outputs=["result2"],
            )
        )

        variant = VariantConfig(
            name="variant",
            prompt="Modified prompt",
            node_id="second_node",
        )

        runner = ABTestRunner()
        modified = runner._apply_variant_to_config(minimal_workflow_config, variant)

        # Only second node's prompt should be updated
        assert modified.nodes[0].prompt == "Test prompt with {topic}"
        assert modified.nodes[1].prompt == "Modified prompt"

    @patch("configurable_agents.optimization.ab_test.MLFLOW_AVAILABLE", True)
    def test_apply_variant_with_config_overrides(self, minimal_workflow_config):
        """Test applying variant with config overrides."""
        variant = VariantConfig(
            name="variant",
            prompt="Prompt",
            config_overrides={"config.observability.mlflow.experiment_name": "test_exp"},
        )

        runner = ABTestRunner()
        modified = runner._apply_variant_to_config(minimal_workflow_config, variant)

        # Check that override was applied
        assert modified.config.observability.mlflow.experiment_name == "test_exp"

    def test_aggregate_metrics_empty(self):
        """Test aggregating empty metrics list."""
        runner = ABTestRunner()
        result = runner._aggregate_metrics([])

        assert result["avg_cost_usd"] == 0
        assert result["avg_duration_ms"] == 0
        assert result["success_rate"] == 0

    def test_aggregate_metrics_single(self):
        """Test aggregating single metric."""
        runner = ABTestRunner()
        metrics = [
            {"cost_usd": 0.01, "duration_ms": 1000, "total_tokens": 100, "success": True}
        ]

        result = runner._aggregate_metrics(metrics)

        assert result["avg_cost_usd"] == 0.01
        assert result["avg_duration_ms"] == 1000
        assert result["success_rate"] == 1.0

    def test_aggregate_metrics_multiple(self):
        """Test aggregating multiple metrics."""
        runner = ABTestRunner()
        metrics = [
            {"cost_usd": 0.01, "duration_ms": 1000, "total_tokens": 100, "success": True},
            {"cost_usd": 0.02, "duration_ms": 2000, "total_tokens": 200, "success": True},
            {"cost_usd": 0.015, "duration_ms": 1500, "total_tokens": 150, "success": True},
        ]

        result = runner._aggregate_metrics(metrics)

        assert result["avg_cost_usd"] == pytest.approx(0.015)
        assert result["avg_duration_ms"] == 1500
        assert result["min_cost_usd"] == 0.01
        assert result["max_cost_usd"] == 0.02
        assert result["success_rate"] == 1.0

    def test_aggregate_metrics_with_failures(self):
        """Test aggregating metrics with some failures."""
        runner = ABTestRunner()
        metrics = [
            {"cost_usd": 0.01, "success": True},
            {"cost_usd": 0.02, "success": False},
            {"cost_usd": 0.015, "success": True},
        ]

        result = runner._aggregate_metrics(metrics)

        assert result["success_rate"] == pytest.approx(0.667, rel=0.01)

    def test_find_best_variant_empty(self):
        """Test finding best variant with no results."""
        runner = ABTestRunner()
        best = runner._find_best_variant({})

        assert best is None

    def test_find_best_variant(self):
        """Test finding best variant by cost."""
        runner = ABTestRunner()
        variant_results = {
            "expensive": VariantResult(
                variant_name="expensive",
                run_count=3,
                metrics={"avg_cost_usd": 0.05},
            ),
            "cheap": VariantResult(
                variant_name="cheap",
                run_count=3,
                metrics={"avg_cost_usd": 0.01},
            ),
            "medium": VariantResult(
                variant_name="medium",
                run_count=3,
                metrics={"avg_cost_usd": 0.02},
            ),
        }

        best = runner._find_best_variant(variant_results)

        assert best == "cheap"

    def test_generate_summary(self):
        """Test generating human-readable summary."""
        runner = ABTestRunner()
        variant_results = {
            "variant_a": VariantResult(
                variant_name="variant_a",
                run_count=3,
                metrics={"avg_cost_usd": 0.01},
            ),
            "variant_b": VariantResult(
                variant_name="variant_b",
                run_count=3,
                metrics={"avg_cost_usd": 0.02},
            ),
        }

        summary = runner._generate_summary(variant_results, "variant_a")

        assert "A/B Test Results" in summary
        assert "variant_a" in summary
        assert "variant_b" in summary
        assert "[BEST]" in summary


class TestCalculatePercentiles:
    """Test calculate_percentiles function."""

    def test_empty_list(self):
        """Test with empty list."""
        result = calculate_percentiles([])

        assert result == {"p50": 0, "p95": 0, "p99": 0}

    def test_single_value(self):
        """Test with single value."""
        result = calculate_percentiles([100])

        assert result["p50"] == 100
        assert result["p95"] == 100
        assert result["p99"] == 100

    def test_multiple_values(self):
        """Test with multiple values."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = calculate_percentiles(values)

        # With nearest-rank: ceil(p/100 * n) - 1
        # p50: ceil(0.50 * 10) - 1 = 4, values[4] = 5
        # p95: ceil(0.95 * 10) - 1 = 9, values[9] = 10
        # p99: ceil(0.99 * 10) - 1 = 9, values[9] = 10
        assert result["p50"] == 5
        assert result["p95"] == 10
        assert result["p99"] == 10

    def test_large_dataset(self):
        """Test with larger dataset."""
        values = list(range(1, 101))  # 1 to 100
        result = calculate_percentiles(values)

        # p50: ceil(0.50 * 100) - 1 = 49, values[49] = 50
        # p95: ceil(0.95 * 100) - 1 = 94, values[94] = 95
        # p99: ceil(0.99 * 100) - 1 = 98, values[98] = 99
        assert result["p50"] == 50
        assert result["p95"] == 95
        assert result["p99"] == 99


class TestApplyPromptToWorkflow:
    """Test apply_prompt_to_workflow function."""

    def test_apply_prompt_creates_backup(self, tmp_path):
        """Test that applying prompt creates backup."""
        # Create test workflow file
        workflow_file = tmp_path / "workflow.yaml"
        workflow_content = {
            "schema_version": "1.0",
            "flow": {"name": "test", "version": "1.0"},
            "state": {"fields": {"input": {"type": "str", "required": True}}},
            "nodes": [
                {"id": "node1", "prompt": "Original prompt", "outputs": ["result"], "output_schema": {"type": "str"}}
            ],
            "edges": [{"from": "START", "to": "node1"}, {"from": "node1", "to": "END"}]
        }

        with open(workflow_file, "w") as f:
            yaml.dump(workflow_content, f)

        # Apply new prompt
        backup_path = apply_prompt_to_workflow(
            str(workflow_file),
            "New prompt",
            backup=True
        )

        # Check backup was created
        assert backup_path.endswith(".yaml")
        assert "backup" in backup_path

        # Check original file was updated
        with open(workflow_file) as f:
            updated = yaml.safe_load(f)

        assert updated["nodes"][0]["prompt"] == "New prompt"

    def test_apply_prompt_to_specific_node(self, tmp_path):
        """Test applying prompt to specific node."""
        workflow_file = tmp_path / "workflow.yaml"
        workflow_content = {
            "schema_version": "1.0",
            "flow": {"name": "test"},
            "state": {"fields": {"input": {"type": "str"}}},
            "nodes": [
                {"id": "node1", "prompt": "Prompt 1", "outputs": ["result1"], "output_schema": {"type": "str"}},
                {"id": "node2", "prompt": "Prompt 2", "outputs": ["result2"], "output_schema": {"type": "str"}},
            ],
            "edges": [{"from": "START", "to": "node1"}, {"from": "node1", "to": "node2"}, {"from": "node2", "to": "END"}]
        }

        with open(workflow_file, "w") as f:
            yaml.dump(workflow_content, f)

        # Apply to node2 only
        apply_prompt_to_workflow(
            str(workflow_file),
            "Modified prompt",
            node_id="node2",
            backup=False,
        )

        with open(workflow_file) as f:
            updated = yaml.safe_load(f)

        # Only node2 should be modified
        assert updated["nodes"][0]["prompt"] == "Prompt 1"
        assert updated["nodes"][1]["prompt"] == "Modified prompt"

    def test_apply_prompt_file_not_found(self, tmp_path):
        """Test error when file not found."""
        with pytest.raises(FileNotFoundError):
            apply_prompt_to_workflow(
                str(tmp_path / "nonexistent.yaml"),
                "New prompt"
            )

    def test_apply_prompt_node_not_found(self, tmp_path):
        """Test error when node not found."""
        workflow_file = tmp_path / "workflow.yaml"
        workflow_content = {
            "schema_version": "1.0",
            "flow": {"name": "test"},
            "state": {"fields": {"input": {"type": "str"}}},
            "nodes": [
                {"id": "node1", "prompt": "Prompt", "outputs": ["result"], "output_schema": {"type": "str"}},
            ],
            "edges": [{"from": "START", "to": "node1"}, {"from": "node1", "to": "END"}]
        }

        with open(workflow_file, "w") as f:
            yaml.dump(workflow_content, f)

        with pytest.raises(ValueError, match="Node.*not found"):
            apply_prompt_to_workflow(
                str(workflow_file),
                "New prompt",
                node_id="nonexistent",
                backup=False,
            )


class TestRunABTest:
    """Test run_ab_test convenience function."""

    @patch("configurable_agents.optimization.ab_test.ABTestRunner")
    def test_run_ab_test_convenience(self, mock_runner_class):
        """Test the convenience function."""
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.summary = "Test summary"
        mock_runner.run.return_value = mock_result
        mock_runner_class.return_value = mock_runner

        variants = [
            VariantConfig(name="v1", prompt="Prompt 1"),
            VariantConfig(name="v2", prompt="Prompt 2"),
        ]

        result = run_ab_test(
            experiment_name="test_exp",
            workflow_path="workflow.yaml",
            variants=variants,
            run_count=5,
        )

        # Verify runner was created and run called
        mock_runner_class.assert_called_once()
        mock_runner.run.assert_called_once()
        assert result.summary == "Test summary"
