"""Unit tests for cost reporting functionality."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from configurable_agents.observability.cost_reporter import (
    CostEntry,
    CostReporter,
    CostSummary,
    get_date_range_filter,
)


@pytest.fixture
def mock_mlflow():
    """Mock MLFlow module."""
    with patch("configurable_agents.observability.cost_reporter.mlflow") as mock:
        with patch("configurable_agents.observability.cost_reporter.MlflowClient") as mock_client:
            with patch("configurable_agents.observability.cost_reporter.MLFLOW_AVAILABLE", True):
                yield mock, mock_client


def make_mock_run(
    run_id: str = "run_001",
    run_name: str = "test_run",
    workflow_name: str = "test_workflow",
    start_time: Optional[datetime] = None,
    total_cost: float = 0.001,
    input_tokens: int = 150,
    output_tokens: int = 500,
    duration: float = 12.5,
    node_count: int = 3,
    status: str = "success",
    model: Optional[str] = "gemini-1.5-flash",
) -> Mock:
    """Create a mock MLFlow run object."""
    if start_time is None:
        start_time = datetime.now()

    run = Mock()
    run.info = Mock()
    run.info.run_id = run_id
    run.info.run_name = run_name
    run.info.start_time = int(start_time.timestamp() * 1000)  # milliseconds

    run.data = Mock()
    run.data.metrics = {
        "total_cost_usd": total_cost,
        "total_input_tokens": float(input_tokens),
        "total_output_tokens": float(output_tokens),
        "duration_seconds": duration,
        "node_count": float(node_count),
        "status": 1.0 if status == "success" else 0.0,
    }
    run.data.params = {
        "workflow_name": workflow_name,
    }
    if model:
        run.data.params["global_model"] = model

    return run


class TestCostReporter:
    """Tests for CostReporter class."""

    def test_init_success(self, mock_mlflow):
        """Test CostReporter initialization with MLFlow available."""
        mock_mlflow_module, mock_client_class = mock_mlflow

        reporter = CostReporter(tracking_uri="file://./mlruns")

        assert reporter.tracking_uri == "file://./mlruns"
        assert reporter.client is not None
        mock_client_class.assert_called_once_with(tracking_uri="file://./mlruns")

    def test_init_mlflow_unavailable(self):
        """Test CostReporter initialization fails when MLFlow unavailable."""
        with patch("configurable_agents.observability.cost_reporter.MLFLOW_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="MLFlow is not installed"):
                CostReporter()

    def test_run_to_cost_entry_success(self, mock_mlflow):
        """Test conversion of MLFlow run to CostEntry."""
        reporter = CostReporter()
        mock_run = make_mock_run(
            run_id="run_123",
            run_name="my_run",
            workflow_name="article_writer",
            total_cost=0.002,
            input_tokens=200,
            output_tokens=800,
            duration=15.5,
            node_count=4,
            status="success",
            model="gemini-2.5-flash",
        )

        entry = reporter._run_to_cost_entry(mock_run)

        assert entry.run_id == "run_123"
        assert entry.run_name == "my_run"
        assert entry.workflow_name == "article_writer"
        assert entry.total_cost_usd == 0.002
        assert entry.input_tokens == 200
        assert entry.output_tokens == 800
        assert entry.duration_seconds == 15.5
        assert entry.node_count == 4
        assert entry.status == "success"
        assert entry.model == "gemini-2.5-flash"

    def test_run_to_cost_entry_failure_status(self, mock_mlflow):
        """Test CostEntry with failure status."""
        reporter = CostReporter()
        mock_run = make_mock_run(status="failure")

        entry = reporter._run_to_cost_entry(mock_run)

        assert entry.status == "failure"

    def test_run_to_cost_entry_missing_model(self, mock_mlflow):
        """Test CostEntry when global_model is not set."""
        reporter = CostReporter()
        mock_run = make_mock_run(model=None)

        entry = reporter._run_to_cost_entry(mock_run)

        assert entry.model is None

    def test_run_to_cost_entry_missing_required_field(self, mock_mlflow):
        """Test fail-fast when required metrics are missing."""
        reporter = CostReporter()
        mock_run = Mock()
        mock_run.info = Mock()
        mock_run.info.run_id = "run_001"
        mock_run.info.run_name = "test"
        mock_run.info.start_time = int(datetime.now().timestamp() * 1000)
        mock_run.data = Mock()
        mock_run.data.metrics = {}  # Missing metrics - should fail fast
        mock_run.data.params = {}

        with pytest.raises(ValueError, match="Missing required metrics"):
            reporter._run_to_cost_entry(mock_run)

    def test_get_cost_entries_single_experiment(self, mock_mlflow):
        """Test querying cost entries from a single experiment."""
        mock_mlflow_module, mock_client_class = mock_mlflow

        # Mock experiment
        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp_001"
        mock_mlflow_module.get_experiment_by_name.return_value = mock_experiment

        # Mock runs
        mock_runs = [
            make_mock_run(run_id=f"run_{i}", workflow_name="workflow_a")
            for i in range(3)
        ]

        reporter = CostReporter()
        reporter.client.search_runs = Mock(return_value=mock_runs)

        entries = reporter.get_cost_entries(experiment_name="my_experiment")

        assert len(entries) == 3
        assert all(isinstance(e, CostEntry) for e in entries)
        mock_mlflow_module.get_experiment_by_name.assert_called_once_with("my_experiment")
        reporter.client.search_runs.assert_called_once()

    def test_get_cost_entries_nonexistent_experiment(self, mock_mlflow):
        """Test error when experiment doesn't exist."""
        mock_mlflow_module, mock_client_class = mock_mlflow
        mock_mlflow_module.get_experiment_by_name.return_value = None

        reporter = CostReporter()

        with pytest.raises(ValueError, match="Experiment not found"):
            reporter.get_cost_entries(experiment_name="nonexistent")

    def test_get_cost_entries_workflow_filter(self, mock_mlflow):
        """Test filtering by workflow name."""
        mock_mlflow_module, mock_client_class = mock_mlflow

        # Mock runs with different workflows
        mock_runs = [
            make_mock_run(run_id="run_1", workflow_name="workflow_a"),
            make_mock_run(run_id="run_2", workflow_name="workflow_b"),
            make_mock_run(run_id="run_3", workflow_name="workflow_a"),
        ]

        reporter = CostReporter()
        reporter.client.search_experiments = Mock(return_value=[Mock(experiment_id="exp_1")])
        reporter.client.search_runs = Mock(return_value=mock_runs)

        entries = reporter.get_cost_entries(workflow_name="workflow_a")

        assert len(entries) == 2
        assert all(e.workflow_name == "workflow_a" for e in entries)

    def test_get_cost_entries_date_range_filter(self, mock_mlflow):
        """Test filtering by date range."""
        mock_mlflow_module, mock_client_class = mock_mlflow

        reporter = CostReporter()
        reporter.client.search_experiments = Mock(return_value=[Mock(experiment_id="exp_1")])
        reporter.client.search_runs = Mock(return_value=[])

        start_date = datetime(2026, 1, 1)
        end_date = datetime(2026, 1, 31)

        reporter.get_cost_entries(start_date=start_date, end_date=end_date)

        # Verify filter string contains timestamp filters
        call_args = reporter.client.search_runs.call_args
        filter_string = call_args[1].get("filter_string", "")
        assert "attributes.start_time >=" in filter_string
        assert "attributes.start_time <=" in filter_string

    def test_get_cost_entries_status_filter_success(self, mock_mlflow):
        """Test filtering by success status."""
        mock_mlflow_module, mock_client_class = mock_mlflow

        reporter = CostReporter()
        reporter.client.search_experiments = Mock(return_value=[Mock(experiment_id="exp_1")])
        reporter.client.search_runs = Mock(return_value=[])

        reporter.get_cost_entries(status_filter="success")

        call_args = reporter.client.search_runs.call_args
        filter_string = call_args[1].get("filter_string", "")
        assert "metrics.status = 1" in filter_string

    def test_get_cost_entries_status_filter_failure(self, mock_mlflow):
        """Test filtering by failure status."""
        mock_mlflow_module, mock_client_class = mock_mlflow

        reporter = CostReporter()
        reporter.client.search_experiments = Mock(return_value=[Mock(experiment_id="exp_1")])
        reporter.client.search_runs = Mock(return_value=[])

        reporter.get_cost_entries(status_filter="failure")

        call_args = reporter.client.search_runs.call_args
        filter_string = call_args[1].get("filter_string", "")
        assert "metrics.status = 0" in filter_string

    def test_get_cost_entries_invalid_status(self, mock_mlflow):
        """Test error on invalid status filter."""
        reporter = CostReporter()
        reporter.client.search_experiments = Mock(return_value=[Mock(experiment_id="exp_1")])

        with pytest.raises(ValueError, match="Invalid status_filter"):
            reporter.get_cost_entries(status_filter="invalid")


class TestCostSummary:
    """Tests for cost summary generation."""

    def test_generate_summary_empty(self, mock_mlflow):
        """Test summary generation with no entries."""
        reporter = CostReporter()
        summary = reporter.generate_summary([])

        assert summary.total_cost_usd == 0.0
        assert summary.total_runs == 0
        assert summary.total_tokens == 0
        assert summary.successful_runs == 0
        assert summary.failed_runs == 0
        assert summary.avg_cost_per_run == 0.0
        assert summary.avg_tokens_per_run == 0.0
        assert summary.breakdown_by_workflow == {}
        assert summary.breakdown_by_model == {}

    def test_generate_summary_single_entry(self, mock_mlflow):
        """Test summary generation with one entry."""
        reporter = CostReporter()
        entry = CostEntry(
            run_id="run_1",
            run_name="test",
            workflow_name="workflow_a",
            start_time=datetime.now(),
            duration_seconds=10.0,
            status="success",
            total_cost_usd=0.005,
            input_tokens=100,
            output_tokens=400,
            node_count=2,
            model="gemini-1.5-flash",
        )

        summary = reporter.generate_summary([entry])

        assert summary.total_cost_usd == 0.005
        assert summary.total_runs == 1
        assert summary.total_tokens == 500
        assert summary.successful_runs == 1
        assert summary.failed_runs == 0
        assert summary.avg_cost_per_run == 0.005
        assert summary.avg_tokens_per_run == 500.0
        assert summary.breakdown_by_workflow == {"workflow_a": 0.005}
        assert summary.breakdown_by_model == {"gemini-1.5-flash": 0.005}

    def test_generate_summary_multiple_entries(self, mock_mlflow):
        """Test summary generation with multiple entries."""
        reporter = CostReporter()
        now = datetime.now()

        entries = [
            CostEntry(
                run_id=f"run_{i}",
                run_name=f"test_{i}",
                workflow_name="workflow_a" if i < 2 else "workflow_b",
                start_time=now - timedelta(hours=i),
                duration_seconds=10.0,
                status="success" if i != 2 else "failure",
                total_cost_usd=0.001 * (i + 1),
                input_tokens=100,
                output_tokens=400,
                node_count=2,
                model="gemini-1.5-flash",
            )
            for i in range(3)
        ]

        summary = reporter.generate_summary(entries)

        assert summary.total_cost_usd == 0.006  # 0.001 + 0.002 + 0.003
        assert summary.total_runs == 3
        assert summary.total_tokens == 1500  # 500 * 3
        assert summary.successful_runs == 2
        assert summary.failed_runs == 1
        assert summary.avg_cost_per_run == pytest.approx(0.002, rel=1e-6)
        assert summary.avg_tokens_per_run == 500.0
        assert summary.breakdown_by_workflow["workflow_a"] == 0.003  # 0.001 + 0.002
        assert summary.breakdown_by_workflow["workflow_b"] == 0.003


class TestAggregation:
    """Tests for cost aggregation by time period."""

    def test_aggregate_by_daily(self, mock_mlflow):
        """Test aggregation by daily period."""
        reporter = CostReporter()
        base_time = datetime(2026, 1, 15, 10, 0, 0)

        entries = [
            CostEntry(
                run_id=f"run_{i}",
                run_name="test",
                workflow_name="test",
                start_time=base_time + timedelta(days=i),
                duration_seconds=10.0,
                status="success",
                total_cost_usd=0.001,
                input_tokens=100,
                output_tokens=400,
                node_count=2,
            )
            for i in range(3)
        ]

        aggregated = reporter.aggregate_by_period(entries, period="daily")

        assert len(aggregated) == 3
        assert "2026-01-15" in aggregated
        assert "2026-01-16" in aggregated
        assert "2026-01-17" in aggregated
        assert all(cost == 0.001 for cost in aggregated.values())

    def test_aggregate_by_weekly(self, mock_mlflow):
        """Test aggregation by weekly period."""
        reporter = CostReporter()
        base_time = datetime(2026, 1, 15, 10, 0, 0)

        entries = [
            CostEntry(
                run_id=f"run_{i}",
                run_name="test",
                workflow_name="test",
                start_time=base_time + timedelta(days=i),
                duration_seconds=10.0,
                status="success",
                total_cost_usd=0.001,
                input_tokens=100,
                output_tokens=400,
                node_count=2,
            )
            for i in range(10)  # 10 days
        ]

        aggregated = reporter.aggregate_by_period(entries, period="weekly")

        # 10 days starting from Jan 15 should span 2 weeks
        assert len(aggregated) >= 1

    def test_aggregate_by_monthly(self, mock_mlflow):
        """Test aggregation by monthly period."""
        reporter = CostReporter()

        entries = [
            CostEntry(
                run_id="run_1",
                run_name="test",
                workflow_name="test",
                start_time=datetime(2026, 1, 15),
                duration_seconds=10.0,
                status="success",
                total_cost_usd=0.001,
                input_tokens=100,
                output_tokens=400,
                node_count=2,
            ),
            CostEntry(
                run_id="run_2",
                run_name="test",
                workflow_name="test",
                start_time=datetime(2026, 2, 10),
                duration_seconds=10.0,
                status="success",
                total_cost_usd=0.002,
                input_tokens=100,
                output_tokens=400,
                node_count=2,
            ),
        ]

        aggregated = reporter.aggregate_by_period(entries, period="monthly")

        assert len(aggregated) == 2
        assert "2026-01" in aggregated
        assert "2026-02" in aggregated
        assert aggregated["2026-01"] == 0.001
        assert aggregated["2026-02"] == 0.002

    def test_aggregate_invalid_period(self, mock_mlflow):
        """Test error on invalid aggregation period."""
        reporter = CostReporter()

        with pytest.raises(ValueError, match="Invalid period"):
            reporter.aggregate_by_period([], period="invalid")


class TestExport:
    """Tests for export functionality."""

    def test_export_to_json(self, mock_mlflow, tmp_path):
        """Test exporting entries to JSON file."""
        reporter = CostReporter()
        output_file = tmp_path / "costs.json"

        entries = [
            CostEntry(
                run_id="run_1",
                run_name="test",
                workflow_name="workflow_a",
                start_time=datetime(2026, 1, 15, 10, 0, 0),
                duration_seconds=10.0,
                status="success",
                total_cost_usd=0.005,
                input_tokens=100,
                output_tokens=400,
                node_count=2,
                model="gemini-1.5-flash",
            )
        ]

        reporter.export_to_json(entries, str(output_file), include_summary=True)

        assert output_file.exists()

        # Verify JSON structure
        with open(output_file) as f:
            data = json.load(f)

        assert "entries" in data
        assert "summary" in data
        assert len(data["entries"]) == 1
        assert data["entries"][0]["run_id"] == "run_1"
        assert data["summary"]["total_cost_usd"] == 0.005

    def test_export_to_json_no_summary(self, mock_mlflow, tmp_path):
        """Test exporting without summary."""
        reporter = CostReporter()
        output_file = tmp_path / "costs.json"

        entries = [
            CostEntry(
                run_id="run_1",
                run_name="test",
                workflow_name="test",
                start_time=datetime(2026, 1, 15),
                duration_seconds=10.0,
                status="success",
                total_cost_usd=0.001,
                input_tokens=100,
                output_tokens=400,
                node_count=2,
            )
        ]

        reporter.export_to_json(entries, str(output_file), include_summary=False)

        with open(output_file) as f:
            data = json.load(f)

        assert "entries" in data
        assert "summary" not in data

    def test_export_to_csv(self, mock_mlflow, tmp_path):
        """Test exporting entries to CSV file."""
        reporter = CostReporter()
        output_file = tmp_path / "costs.csv"

        entries = [
            CostEntry(
                run_id="run_1",
                run_name="test",
                workflow_name="workflow_a",
                start_time=datetime(2026, 1, 15, 10, 0, 0),
                duration_seconds=10.5,
                status="success",
                total_cost_usd=0.005,
                input_tokens=100,
                output_tokens=400,
                node_count=2,
                model="gemini-1.5-flash",
            )
        ]

        reporter.export_to_csv(entries, str(output_file))

        assert output_file.exists()

        # Verify CSV content
        with open(output_file) as f:
            lines = f.readlines()

        assert len(lines) == 2  # Header + 1 entry
        assert "run_id,run_name,workflow_name" in lines[0]
        assert "run_1,test,workflow_a" in lines[1]


class TestDateRangeFilter:
    """Tests for date range filter helper."""

    def test_get_date_range_today(self):
        """Test 'today' filter."""
        start, end = get_date_range_filter("today")

        assert start.date() == datetime.now().date()
        assert end.date() == datetime.now().date()
        assert start.hour == 0
        assert start.minute == 0

    def test_get_date_range_yesterday(self):
        """Test 'yesterday' filter."""
        start, end = get_date_range_filter("yesterday")

        expected_date = datetime.now().date() - timedelta(days=1)
        assert start.date() == expected_date
        assert end.date() == datetime.now().date()

    def test_get_date_range_last_7_days(self):
        """Test 'last_7_days' filter."""
        start, end = get_date_range_filter("last_7_days")

        expected_start = datetime.now().date() - timedelta(days=7)
        assert start.date() == expected_start
        assert end.date() == datetime.now().date()

    def test_get_date_range_last_30_days(self):
        """Test 'last_30_days' filter."""
        start, end = get_date_range_filter("last_30_days")

        expected_start = datetime.now().date() - timedelta(days=30)
        assert start.date() == expected_start
        assert end.date() == datetime.now().date()

    def test_get_date_range_this_month(self):
        """Test 'this_month' filter."""
        start, end = get_date_range_filter("this_month")

        assert start.day == 1
        assert start.date().month == datetime.now().date().month
        assert end.date() == datetime.now().date()

    def test_get_date_range_invalid(self):
        """Test error on invalid period."""
        with pytest.raises(ValueError, match="Invalid period"):
            get_date_range_filter("invalid")
