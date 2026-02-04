"""Integration tests for cost reporter with real MLFlow backend.

These tests use actual MLFlow file storage to verify the cost reporter
works correctly with real MLFlow runs.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from configurable_agents.observability import (
    CostEstimator,
    CostReporter,
    MLFlowTracker,
)
from configurable_agents.observability.cost_reporter import get_date_range_filter

# Skip if MLFlow not available
pytest.importorskip("mlflow")

import mlflow


@pytest.mark.integration
def test_cost_reporter_with_real_mlflow():
    """Test cost reporter with real MLFlow runs."""
    # Use temp directory for MLFlow storage
    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_uri = f"file:///{Path(tmpdir).as_posix()}"

        # Configure MLFlow
        mlflow.set_tracking_uri(tracking_uri)
        experiment = mlflow.set_experiment("test_cost_reporting")

        # Create test runs using MLFlow directly
        run_ids = []
        for i in range(3):
            with mlflow.start_run(run_name=f"test_run_{i}"):
                # Log workflow parameters
                mlflow.log_param("workflow_name", f"workflow_{i % 2}")  # 2 workflows
                mlflow.log_param("global_model", "gemini-1.5-flash")

                # Log metrics (as would be done by MLFlowTracker)
                mlflow.log_metric("total_cost_usd", 0.001 * (i + 1))
                mlflow.log_metric("total_input_tokens", 100 * (i + 1))
                mlflow.log_metric("total_output_tokens", 400 * (i + 1))
                mlflow.log_metric("duration_seconds", 10.0 + i)
                mlflow.log_metric("node_count", 2 + i)
                mlflow.log_metric("status", 1.0 if i != 2 else 0.0)  # Last one fails

                run_ids.append(mlflow.active_run().info.run_id)

        # Now query with CostReporter
        reporter = CostReporter(tracking_uri=tracking_uri)

        # Test 1: Get all entries
        entries = reporter.get_cost_entries(experiment_name="test_cost_reporting")

        assert len(entries) == 3
        assert all(e.workflow_name in ["workflow_0", "workflow_1"] for e in entries)
        assert all(e.model == "gemini-1.5-flash" for e in entries)

        # Test 2: Generate summary
        summary = reporter.generate_summary(entries)

        assert summary.total_runs == 3
        assert summary.successful_runs == 2
        assert summary.failed_runs == 1
        assert summary.total_cost_usd == pytest.approx(0.006, rel=1e-6)  # 0.001 + 0.002 + 0.003
        assert summary.total_tokens == 3000  # 500 + 1000 + 1500
        assert len(summary.breakdown_by_workflow) == 2

        # Test 3: Filter by workflow
        workflow_0_entries = reporter.get_cost_entries(
            experiment_name="test_cost_reporting", workflow_name="workflow_0"
        )

        # workflow_0 should have runs at indices 0 and 2
        assert len(workflow_0_entries) == 2

        # Test 4: Filter by status
        success_entries = reporter.get_cost_entries(
            experiment_name="test_cost_reporting", status_filter="success"
        )

        assert len(success_entries) == 2
        assert all(e.status == "success" for e in success_entries)

        failure_entries = reporter.get_cost_entries(
            experiment_name="test_cost_reporting", status_filter="failure"
        )

        assert len(failure_entries) == 1
        assert failure_entries[0].status == "failure"


@pytest.mark.integration
def test_cost_reporter_export_json(tmp_path):
    """Test exporting cost data to JSON file."""
    # Use temp directory for MLFlow storage
    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_uri = f"file:///{Path(tmpdir).as_posix()}"

        # Configure MLFlow
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("test_export")

        # Create a test run
        with mlflow.start_run(run_name="export_test"):
            mlflow.log_param("workflow_name", "export_workflow")
            mlflow.log_param("global_model", "gemini-2.5-flash")
            mlflow.log_metric("total_cost_usd", 0.005)
            mlflow.log_metric("total_input_tokens", 150)
            mlflow.log_metric("total_output_tokens", 500)
            mlflow.log_metric("duration_seconds", 12.5)
            mlflow.log_metric("node_count", 3)
            mlflow.log_metric("status", 1.0)

        # Export with CostReporter
        reporter = CostReporter(tracking_uri=tracking_uri)
        entries = reporter.get_cost_entries(experiment_name="test_export")

        output_file = tmp_path / "costs.json"
        reporter.export_to_json(entries, str(output_file), include_summary=True)

        # Verify file exists and content is valid
        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)

        assert "entries" in data
        assert "summary" in data
        assert len(data["entries"]) == 1
        assert data["entries"][0]["workflow_name"] == "export_workflow"
        assert data["summary"]["total_cost_usd"] == 0.005


@pytest.mark.integration
def test_cost_reporter_export_csv(tmp_path):
    """Test exporting cost data to CSV file."""
    # Use temp directory for MLFlow storage
    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_uri = f"file:///{Path(tmpdir).as_posix()}"

        # Configure MLFlow
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("test_csv_export")

        # Create a test run
        with mlflow.start_run(run_name="csv_test"):
            mlflow.log_param("workflow_name", "csv_workflow")
            mlflow.log_param("global_model", "gemini-1.5-pro")
            mlflow.log_metric("total_cost_usd", 0.003)
            mlflow.log_metric("total_input_tokens", 200)
            mlflow.log_metric("total_output_tokens", 600)
            mlflow.log_metric("duration_seconds", 8.0)
            mlflow.log_metric("node_count", 2)
            mlflow.log_metric("status", 1.0)

        # Export with CostReporter
        reporter = CostReporter(tracking_uri=tracking_uri)
        entries = reporter.get_cost_entries(experiment_name="test_csv_export")

        output_file = tmp_path / "costs.csv"
        reporter.export_to_csv(entries, str(output_file))

        # Verify file exists and has correct format
        assert output_file.exists()

        with open(output_file) as f:
            lines = f.readlines()

        assert len(lines) == 2  # Header + 1 entry
        assert "run_id,run_name,workflow_name" in lines[0]
        assert "csv_workflow" in lines[1]


@pytest.mark.integration
def test_cost_reporter_aggregate_by_period(tmp_path):
    """Test aggregating costs by time period."""
    # Use temp directory for MLFlow storage
    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_uri = f"file:///{Path(tmpdir).as_posix()}"

        # Configure MLFlow
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("test_aggregation")

        # Create runs on different days
        # Note: MLFlow uses start_time from when the run is created,
        # so we'll create runs and then verify aggregation works
        for i in range(3):
            with mlflow.start_run(run_name=f"run_day_{i}"):
                mlflow.log_param("workflow_name", "aggregation_test")
                mlflow.log_metric("total_cost_usd", 0.001)
                mlflow.log_metric("total_input_tokens", 100)
                mlflow.log_metric("total_output_tokens", 400)
                mlflow.log_metric("duration_seconds", 10.0)
                mlflow.log_metric("node_count", 2)
                mlflow.log_metric("status", 1.0)

        # Query and aggregate
        reporter = CostReporter(tracking_uri=tracking_uri)
        entries = reporter.get_cost_entries(experiment_name="test_aggregation")

        # Aggregate by daily (all on same day since created together)
        daily_agg = reporter.aggregate_by_period(entries, period="daily")

        assert len(daily_agg) >= 1  # At least one day
        assert sum(daily_agg.values()) == pytest.approx(0.003, rel=1e-6)


@pytest.mark.integration
def test_date_range_filter_helpers():
    """Test date range filter helper functions."""
    # Test that helpers return valid date ranges
    today_range = get_date_range_filter("today")
    assert today_range[0] <= today_range[1]
    assert today_range[0].date() == datetime.now().date()

    last_7_days_range = get_date_range_filter("last_7_days")
    assert last_7_days_range[0] <= last_7_days_range[1]
    assert (last_7_days_range[1] - last_7_days_range[0]).days >= 6

    this_month_range = get_date_range_filter("this_month")
    assert this_month_range[0].day == 1
    assert this_month_range[0] <= this_month_range[1]
