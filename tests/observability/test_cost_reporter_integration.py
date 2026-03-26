"""Integration tests for cost reporter with real MLFlow backend.

These tests use actual MLFlow SQLite storage to verify the cost reporter
works correctly with real MLFlow traces (GenAI paradigm, not legacy runs).

NOTE: The CostReporter queries mlflow.search_traces() (not runs), so tests
must create data via mlflow.start_span() context managers. The file:///
backend does not support trace storage; sqlite:/// is required.
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


def _sqlite_uri(tmpdir: str) -> str:
    """Return a sqlite:/// tracking URI for the given temp directory."""
    return f"sqlite:///{Path(tmpdir) / 'mlflow.db'}"


def _make_chat_span(root_span_name: str, model: str, prompt_tokens: int, completion_tokens: int, fail: bool = False):
    """Context manager helper that creates a root + CHAT_MODEL child trace."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        try:
            with mlflow.start_span(root_span_name) as root:
                with mlflow.start_span("llm_call", span_type="CHAT_MODEL") as chat:
                    chat.set_attribute("ai.model.name", model)
                    chat.set_attribute(
                        "mlflow.chat.tokenUsage",
                        {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
                    )
                if fail:
                    raise RuntimeError("simulated workflow failure")
        except RuntimeError:
            pass
        yield

    return _ctx()


@pytest.mark.integration
def test_cost_reporter_with_real_mlflow():
    """Test cost reporter with real MLFlow traces (GenAI paradigm)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_uri = _sqlite_uri(tmpdir)

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("test_cost_reporting")

        # Create 3 traces. Root span names follow the "workflow_{name}" convention
        # used by MLFlowTracker.get_trace_decorator(). CostReporter strips the
        # "workflow_" prefix when extracting workflow_name.
        # Token counts chosen so total tokens = 100+400 + 200+800 + 300+1200 = 3000
        with _make_chat_span("workflow_0", "gemini-1.5-flash", prompt_tokens=100, completion_tokens=400):
            pass
        with _make_chat_span("workflow_1", "gemini-1.5-flash", prompt_tokens=200, completion_tokens=800):
            pass
        with _make_chat_span("workflow_0", "gemini-1.5-flash", prompt_tokens=300, completion_tokens=1200, fail=True):
            pass

        reporter = CostReporter(tracking_uri=tracking_uri)

        # Test 1: Get all entries
        entries = reporter.get_cost_entries(experiment_name="test_cost_reporting")

        assert len(entries) == 3
        # extraction strips "workflow_" prefix → "0" and "1"
        assert all(e.workflow_name in ["0", "1"] for e in entries)
        assert all(e.model == "gemini-1.5-flash" for e in entries)

        # Test 2: Generate summary
        summary = reporter.generate_summary(entries)

        assert summary.total_runs == 3
        assert summary.successful_runs == 2
        assert summary.failed_runs == 1
        assert summary.total_cost_usd > 0        # CostEstimator computes this dynamically
        assert summary.total_tokens == 3000       # (100+400) + (200+800) + (300+1200)
        assert len(summary.breakdown_by_workflow) == 2  # "0" and "1"

        # Test 3: Filter by workflow (extracted name, not raw trace name)
        workflow_0_entries = reporter.get_cost_entries(
            experiment_name="test_cost_reporting", workflow_name="0"
        )
        # traces 0 and 2 are both workflow_0
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
    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_uri = _sqlite_uri(tmpdir)

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("test_export")

        with _make_chat_span("workflow_export_workflow", "gemini-2.5-flash", prompt_tokens=150, completion_tokens=500):
            pass

        reporter = CostReporter(tracking_uri=tracking_uri)
        entries = reporter.get_cost_entries(experiment_name="test_export")

        output_file = tmp_path / "costs.json"
        reporter.export_to_json(entries, str(output_file), include_summary=True)

        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)

        assert "entries" in data
        assert "summary" in data
        assert len(data["entries"]) == 1
        # "workflow_export_workflow" → strips prefix → "export_workflow"
        assert data["entries"][0]["workflow_name"] == "export_workflow"
        assert data["summary"]["total_cost_usd"] > 0


@pytest.mark.integration
def test_cost_reporter_export_csv(tmp_path):
    """Test exporting cost data to CSV file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_uri = _sqlite_uri(tmpdir)

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("test_csv_export")

        with _make_chat_span("workflow_csv_workflow", "gemini-1.5-pro", prompt_tokens=200, completion_tokens=600):
            pass

        reporter = CostReporter(tracking_uri=tracking_uri)
        entries = reporter.get_cost_entries(experiment_name="test_csv_export")

        output_file = tmp_path / "costs.csv"
        reporter.export_to_csv(entries, str(output_file))

        assert output_file.exists()

        with open(output_file) as f:
            lines = f.readlines()

        assert len(lines) == 2  # Header + 1 entry
        assert "run_id,run_name,workflow_name" in lines[0]
        assert "csv_workflow" in lines[1]


@pytest.mark.integration
def test_cost_reporter_aggregate_by_period(tmp_path):
    """Test aggregating costs by time period."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_uri = _sqlite_uri(tmpdir)

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("test_aggregation")

        for i in range(3):
            with _make_chat_span("aggregation_test", "gemini-1.5-flash", prompt_tokens=100, completion_tokens=400):
                pass

        reporter = CostReporter(tracking_uri=tracking_uri)
        entries = reporter.get_cost_entries(experiment_name="test_aggregation")

        daily_agg = reporter.aggregate_by_period(entries, period="daily")

        assert len(daily_agg) >= 1          # at least one day bucket
        assert sum(daily_agg.values()) > 0  # non-zero cost total


@pytest.mark.integration
def test_date_range_filter_helpers():
    """Test date range filter helper functions."""
    today_range = get_date_range_filter("today")
    assert today_range[0] <= today_range[1]
    assert today_range[0].date() == datetime.now().date()

    last_7_days_range = get_date_range_filter("last_7_days")
    assert last_7_days_range[0] <= last_7_days_range[1]
    assert (last_7_days_range[1] - last_7_days_range[0]).days >= 6

    this_month_range = get_date_range_filter("this_month")
    assert this_month_range[0].day == 1
    assert this_month_range[0] <= this_month_range[1]
