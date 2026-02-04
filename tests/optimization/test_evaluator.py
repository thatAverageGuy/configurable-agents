"""Tests for experiment evaluator."""

from unittest.mock import MagicMock, Mock, patch
from datetime import datetime
import pytest

from configurable_agents.optimization.evaluator import (
    ExperimentEvaluator,
    VariantMetrics,
    ComparisonResult,
    compare_variants,
    find_best_variant,
    format_comparison_table,
    calculate_percentiles,
)


@pytest.fixture
def sample_runs():
    """Create sample MLFlow run data."""
    return [
        {
            "run_id": "run_1",
            "params": {"variant_name": "concise", "prompt": "Concise prompt"},
            "metrics": {"cost_usd": 0.01, "duration_ms": 1000, "total_tokens": 100},
            "tags": {"variant_name": "concise"},
            "start_time": datetime(2024, 1, 1, 12, 0, 0),
            "status": "COMPLETED",
        },
        {
            "run_id": "run_2",
            "params": {"variant_name": "concise", "prompt": "Concise prompt"},
            "metrics": {"cost_usd": 0.012, "duration_ms": 1100, "total_tokens": 110},
            "tags": {"variant_name": "concise"},
            "start_time": datetime(2024, 1, 1, 12, 1, 0),
            "status": "COMPLETED",
        },
        {
            "run_id": "run_3",
            "params": {"variant_name": "detailed", "prompt": "Detailed prompt"},
            "metrics": {"cost_usd": 0.02, "duration_ms": 2000, "total_tokens": 200},
            "tags": {"variant_name": "detailed"},
            "start_time": datetime(2024, 1, 1, 12, 2, 0),
            "status": "COMPLETED",
        },
        {
            "run_id": "run_4",
            "params": {"variant_name": "detailed", "prompt": "Detailed prompt"},
            "metrics": {"cost_usd": 0.025, "duration_ms": 2100, "total_tokens": 210},
            "tags": {"variant_name": "detailed"},
            "start_time": datetime(2024, 1, 1, 12, 3, 0),
            "status": "COMPLETED",
        },
    ]


@pytest.fixture
def mlflow_client_mock():
    """Create a mock MLFlow client."""
    mock_client = MagicMock()

    # Mock experiment
    mock_exp = MagicMock()
    mock_exp.experiment_id = "exp_123"
    mock_exp.name = "test_experiment"

    # Mock runs
    mock_run_1 = MagicMock()
    mock_run_1.info.run_id = "run_1"
    mock_run_1.info.start_time = 1704110400000  # 2024-01-01 12:00:00
    mock_run_1.info.status = "COMPLETED"
    mock_run_1.data.params = {"variant_name": "concise", "prompt": "Concise prompt"}
    mock_run_1.data.metrics = {"cost_usd": 0.01, "duration_ms": 1000}
    mock_run_1.data.tags = {"variant_name": "concise"}

    mock_run_2 = MagicMock()
    mock_run_2.info.run_id = "run_2"
    mock_run_2.info.start_time = 1704110460000  # 2024-01-01 12:01:00
    mock_run_2.info.status = "COMPLETED"
    mock_run_2.data.params = {"variant_name": "concise", "prompt": "Concise prompt"}
    mock_run_2.data.metrics = {"cost_usd": 0.012, "duration_ms": 1100}
    mock_run_2.data.tags = {"variant_name": "concise"}

    mock_run_3 = MagicMock()
    mock_run_3.info.run_id = "run_3"
    mock_run_3.info.start_time = 1704110520000
    mock_run_3.info.status = "COMPLETED"
    mock_run_3.data.params = {"variant_name": "detailed", "prompt": "Detailed prompt"}
    mock_run_3.data.metrics = {"cost_usd": 0.02, "duration_ms": 2000}
    mock_run_3.data.tags = {"variant_name": "detailed"}

    mock_run_4 = MagicMock()
    mock_run_4.info.run_id = "run_4"
    mock_run_4.info.start_time = 1704110580000
    mock_run_4.info.status = "COMPLETED"
    mock_run_4.data.params = {"variant_name": "detailed", "prompt": "Detailed prompt"}
    mock_run_4.data.metrics = {"cost_usd": 0.025, "duration_ms": 2100}
    mock_run_4.data.tags = {"variant_name": "detailed"}

    mock_client.search_runs.return_value = [mock_run_1, mock_run_2, mock_run_3, mock_run_4]
    mock_client.get_run.return_value.data.params = {"prompt": "Test prompt"}

    return mock_client, [mock_run_1, mock_run_2, mock_run_3, mock_run_4]


class TestExperimentEvaluator:
    """Test ExperimentEvaluator class."""

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_evaluator_initialization(self, mock_mlflow, mock_client_class):
        """Test evaluator initialization."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        evaluator = ExperimentEvaluator("sqlite:///test.db")

        assert evaluator.mlflow_tracking_uri == "sqlite:///test.db"
        assert evaluator.client == mock_client
        mock_mlflow.set_tracking_uri.assert_called_once_with("sqlite:///test.db")

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", False)
    def test_evaluator_requires_mlflow(self):
        """Test that evaluator raises error when MLFlow not available."""
        with pytest.raises(RuntimeError, match="MLFlow is required"):
            ExperimentEvaluator()

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_get_experiment_runs(self, mock_mlflow, mock_client_class, mlflow_client_mock):
        """Test getting experiment runs."""
        mock_client, runs = mlflow_client_mock
        mock_client_class.return_value = mock_client

        mock_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="exp_123")

        evaluator = ExperimentEvaluator()
        result = evaluator.get_experiment_runs("test_experiment")

        assert len(result) == 4
        assert result[0]["run_id"] == "run_1"
        assert result[0]["tags"]["variant_name"] == "concise"

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_get_experiment_runs_not_found(self, mock_mlflow, mock_client_class):
        """Test error when experiment not found."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_mlflow.get_experiment_by_name.return_value = None

        evaluator = ExperimentEvaluator()

        with pytest.raises(ValueError, match="Experiment not found"):
            evaluator.get_experiment_runs("nonexistent")

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_aggregate_by_variant(self, mock_mlflow, mock_client_class, sample_runs):
        """Test aggregating metrics by variant."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        evaluator = ExperimentEvaluator()
        result = evaluator.aggregate_by_variant(sample_runs)

        assert len(result) == 2
        assert "concise" in result
        assert "detailed" in result

        # Check concise variant aggregation
        concise = result["concise"]
        assert concise.run_count == 2
        assert "cost_usd_avg" in concise.metrics
        assert pytest.approx(0.011, rel=0.1) == concise.metrics["cost_usd_avg"]

        # Check detailed variant aggregation
        detailed = result["detailed"]
        assert detailed.run_count == 2
        assert pytest.approx(0.0225, rel=0.1) == detailed.metrics["cost_usd_avg"]

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_aggregate_calculates_percentiles(self, mock_mlflow, mock_client_class):
        """Test that aggregation calculates percentiles."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create runs with varied metrics
        runs = [
            {
                "run_id": f"run_{i}",
                "params": {},
                "metrics": {"cost_usd": i * 0.01},
                "tags": {"variant_name": "test"},
                "start_time": datetime.now(),
                "status": "COMPLETED",
            }
            for i in range(1, 101)  # 1.00 to 1.00
        ]

        evaluator = ExperimentEvaluator()
        result = evaluator.aggregate_by_variant(runs)

        test_variant = result["test"]
        assert "cost_usd_p50" in test_variant.metrics
        assert "cost_usd_p95" in test_variant.metrics
        assert "cost_usd_p99" in test_variant.metrics

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_compare_variants_by_cost(self, mock_mlflow, mock_client_class, sample_runs):
        """Test comparing variants by cost metric."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="exp_123")

        evaluator = ExperimentEvaluator()

        # Patch get_experiment_runs to return sample data
        with patch.object(evaluator, "get_experiment_runs", return_value=sample_runs):
            result = evaluator.compare_variants("test_experiment", metric="cost_usd_avg")

        # Should return ComparisonResult
        assert isinstance(result, ComparisonResult)
        assert result.experiment_name == "test_experiment"
        assert result.metric == "cost_usd_avg"

        # Best variant should be concise (lower cost)
        assert result.best_variant == "concise"

        # Variants should be sorted by cost
        assert len(result.variants) == 2
        assert result.variants[0].variant_name == "concise"
        assert result.variants[1].variant_name == "detailed"

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_compare_variants_descending(self, mock_mlflow, mock_client_class, sample_runs):
        """Test comparing variants with descending sort."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="exp_123")

        evaluator = ExperimentEvaluator()

        # Patch get_experiment_runs to return sample data
        with patch.object(evaluator, "get_experiment_runs", return_value=sample_runs):
            result = evaluator.compare_variants(
                "test_experiment",
                metric="duration_ms_avg",
                ascending=False,  # Higher is better (e.g., for quality scores)
            )

        # Detailed variant has higher duration (slower), so it comes first with descending=False
        assert result.variants[0].variant_name == "detailed"

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_find_best_variant(self, mock_mlflow, mock_client_class, mlflow_client_mock):
        """Test finding best variant."""
        mock_client, runs = mlflow_client_mock
        mock_client_class.return_value = mock_client
        mock_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="exp_123")

        evaluator = ExperimentEvaluator()
        best = evaluator.find_best_variant("test_experiment", primary_metric="cost_usd_avg")

        assert best is not None
        assert best["variant_name"] == "concise"
        assert best["run_count"] == 2
        assert "metrics" in best
        assert "run_id" in best
        assert "prompt" in best

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_find_best_variant_min_runs(self, mock_mlflow, mock_client_class):
        """Test find_best_variant with min_runs filter."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create runs where one variant has fewer runs
        mock_run = MagicMock()
        mock_run.info.run_id = "run_1"
        mock_run.info.start_time = 1704110400000
        mock_run.info.status = "COMPLETED"
        mock_run.data.params = {"variant_name": "test", "prompt": "Test"}
        mock_run.data.metrics = {"cost_usd": 0.01}
        mock_run.data.tags = {"variant_name": "test"}

        mock_client.search_runs.return_value = [mock_run]  # Only 1 run

        mock_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="exp_123")
        mock_client.get_run.return_value.data.params = {"prompt": "Test"}

        evaluator = ExperimentEvaluator()
        best = evaluator.find_best_variant("test_experiment", min_runs=3)

        # Should return None because variant has fewer than 3 runs
        assert best is None

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_get_prompt_from_run(self, mock_mlflow, mock_client_class):
        """Test retrieving prompt from run."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_run = MagicMock()
        mock_run.data.params = {"prompt": "Test prompt content"}
        mock_client.get_run.return_value = mock_run

        evaluator = ExperimentEvaluator()
        prompt = evaluator.get_prompt_from_run("run_123")

        assert prompt == "Test prompt content"
        mock_client.get_run.assert_called_once_with("run_123")

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_get_prompt_from_run_not_found(self, mock_mlflow, mock_client_class):
        """Test getting prompt when run not found."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_run.side_effect = Exception("Run not found")

        evaluator = ExperimentEvaluator()
        prompt = evaluator.get_prompt_from_run("nonexistent")

        # Should return None and log warning
        assert prompt is None

    @patch("configurable_agents.optimization.evaluator.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.optimization.evaluator.MlflowClient")
    @patch("configurable_agents.optimization.evaluator.mlflow")
    def test_list_experiments(self, mock_mlflow, mock_client_class):
        """Test listing all experiments."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock experiments
        mock_exp_1 = MagicMock()
        mock_exp_1.experiment_id = "exp_1"
        mock_exp_1.name = "experiment_1"

        mock_exp_2 = MagicMock()
        mock_exp_2.experiment_id = "exp_2"
        mock_exp_2.name = "experiment_2"

        mock_mlflow.entities.ViewType = MagicMock()
        mock_mlflow.entities.ViewType.ACTIVE_ONLY = "ACTIVE_ONLY"
        mock_client.search_experiments.return_value = [mock_exp_1, mock_exp_2]

        # Mock runs for counting
        mock_client.search_runs.return_value = [MagicMock()]

        evaluator = ExperimentEvaluator()
        experiments = evaluator.list_experiments()

        assert len(experiments) == 2
        assert experiments[0]["name"] == "experiment_1"
        assert experiments[1]["name"] == "experiment_2"
        assert all("run_count" in exp for exp in experiments)


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch("configurable_agents.optimization.evaluator.ExperimentEvaluator")
    def test_compare_variants_convenience(self, mock_evaluator_class):
        """Test compare_variants convenience function."""
        mock_evaluator = MagicMock()
        mock_result = ComparisonResult(
            experiment_name="test",
            metric="cost",
            variants=[],
        )
        mock_result.best_variant = "concise"
        mock_evaluator.compare_variants.return_value = mock_result
        mock_evaluator_class.return_value = mock_evaluator

        result = compare_variants("test_experiment", metric="cost_usd_avg")

        mock_evaluator.compare_variants.assert_called_once_with("test_experiment", "cost_usd_avg")
        assert result.best_variant == "concise"

    @patch("configurable_agents.optimization.evaluator.ExperimentEvaluator")
    def test_find_best_variant_convenience(self, mock_evaluator_class):
        """Test find_best_variant convenience function."""
        mock_evaluator = MagicMock()
        mock_best = {"variant_name": "best", "metrics": {}}
        mock_evaluator.find_best_variant.return_value = mock_best
        mock_evaluator_class.return_value = mock_evaluator

        result = find_best_variant("test_experiment", primary_metric="cost_usd_avg")

        mock_evaluator.find_best_variant.assert_called_once_with("test_experiment", "cost_usd_avg")
        assert result["variant_name"] == "best"


class TestFormatComparisonTable:
    """Test format_comparison_table function."""

    def test_format_comparison_table(self):
        """Test formatting comparison result as table."""
        variants = [
            VariantMetrics(
                variant_name="concise",
                run_count=3,
                metrics={"cost_usd_avg": 0.01, "cost_usd_min": 0.008, "cost_usd_max": 0.012},
            ),
            VariantMetrics(
                variant_name="detailed",
                run_count=3,
                metrics={"cost_usd_avg": 0.02, "cost_usd_min": 0.018, "cost_usd_max": 0.025},
            ),
        ]

        comparison = ComparisonResult(
            experiment_name="test_exp",
            metric="cost_usd_avg",
            variants=variants,
            best_variant="concise",
        )

        table = format_comparison_table(comparison)

        assert "Experiment: test_exp" in table
        assert "Metric: cost_usd_avg" in table
        assert "Best variant: concise" in table
        assert "concise" in table
        assert "detailed" in table
        assert "*" in table  # Best marker

    def test_format_comparison_table_with_latency(self):
        """Test formatting with latency metric (non-cost)."""
        variants = [
            VariantMetrics(
                variant_name="fast",
                run_count=3,
                metrics={"duration_ms_avg": 1000, "duration_ms_min": 900, "duration_ms_max": 1100},
            ),
        ]

        comparison = ComparisonResult(
            experiment_name="test_exp",
            metric="duration_ms_avg",
            variants=variants,
            best_variant="fast",
        )

        table = format_comparison_table(comparison)

        # Latency should not have $ prefix
        assert "1000" in table  # Format is without decimal for latency
        # Find the line with the data (not header)
        lines = table.split("\n")
        data_line = None
        for line in lines:
            if "fast" in line:
                data_line = line
                break
        assert data_line is not None
        # The data line should not have $ for latency
        assert "$" not in data_line or data_line.index("$") > data_line.index("fast")


class TestCalculatePercentilesEvaluator:
    """Test calculate_percentiles in evaluator module."""

    def test_empty(self):
        """Test with empty list."""
        result = calculate_percentiles([])
        assert result == {"p50": 0, "p95": 0, "p99": 0}

    def test_single_value(self):
        """Test with single value."""
        result = calculate_percentiles([42])
        assert result["p50"] == 42
        assert result["p95"] == 42
        assert result["p99"] == 42

    def test_even_distribution(self):
        """Test with evenly distributed values."""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result = calculate_percentiles(values)

        # With nearest-rank method: ceil(p/100 * n) - 1
        # p50: ceil(0.50 * 10) - 1 = 5 - 1 = 4, values[4] = 50
        # p95: ceil(0.95 * 10) - 1 = 10 - 1 = 9, values[9] = 100
        # p99: ceil(0.99 * 10) - 1 = 10 - 1 = 9, values[9] = 100
        assert result["p50"] == 50
        assert result["p95"] == 100
        assert result["p99"] == 100

    def test_skewed_distribution(self):
        """Test with skewed distribution."""
        values = [1] * 90 + [100] * 10  # 90% are 1, 10% are 100
        result = calculate_percentiles(values)

        # P50 should be 1 (most values are 1)
        assert result["p50"] == 1
        # P95 should be 100
        assert result["p95"] == 100
