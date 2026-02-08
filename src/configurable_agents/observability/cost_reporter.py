"""Cost reporting and aggregation from MLFlow tracking data.

Provides utilities to query MLFlow experiments and generate cost reports
with various aggregations (by workflow, model, time period, etc.).
"""

import csv
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Optional MLFlow import - fail gracefully if not installed
try:
    import mlflow
    from mlflow.entities import Run
    from mlflow.tracking import MlflowClient

    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MlflowClient = None
    Run = None
    MLFLOW_AVAILABLE = False
    logger.warning(
        "MLFlow not installed. Cost reporting features disabled. "
        "Install with: pip install mlflow"
    )


@dataclass
class CostEntry:
    """Single cost entry from a workflow run."""

    run_id: str
    run_name: str
    workflow_name: str
    start_time: datetime
    duration_seconds: float
    status: str  # "success" or "failure"
    total_cost_usd: float
    input_tokens: int
    output_tokens: int
    node_count: int
    model: Optional[str] = None  # Global model if available


@dataclass
class CostSummary:
    """Aggregated cost summary."""

    total_cost_usd: float
    total_runs: int
    total_tokens: int
    successful_runs: int
    failed_runs: int
    avg_cost_per_run: float
    avg_tokens_per_run: float
    date_range: Tuple[datetime, datetime]  # (start, end)
    breakdown_by_workflow: Dict[str, float]  # workflow_name -> total_cost
    breakdown_by_model: Dict[str, float]  # model -> total_cost


class CostReporter:
    """Query and aggregate cost data from MLFlow experiments.

    Provides methods to generate cost reports with various filters and aggregations.

    Example:
        >>> reporter = CostReporter(tracking_uri="sqlite:///mlflow.db")
        >>> # Get all costs for an experiment
        >>> entries = reporter.get_cost_entries(experiment_name="my_workflows")
        >>> # Generate summary
        >>> summary = reporter.generate_summary(entries)
        >>> print(f"Total cost: ${summary.total_cost_usd:.2f}")
    """

    def __init__(self, tracking_uri: str = "sqlite:///mlflow.db"):
        """Initialize cost reporter.

        Args:
            tracking_uri: MLFlow tracking URI (default: sqlite:///mlflow.db)
        """
        if not MLFLOW_AVAILABLE:
            raise RuntimeError(
                "MLFlow is not installed. Install with: pip install mlflow"
            )

        self.tracking_uri = tracking_uri
        self.client = MlflowClient(tracking_uri=tracking_uri)
        logger.debug(f"Initialized CostReporter with tracking_uri: {tracking_uri}")

    def get_cost_entries(
        self,
        experiment_name: Optional[str] = None,
        workflow_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status_filter: Optional[str] = None,  # "success" or "failure"
    ) -> List[CostEntry]:
        """Query MLFlow for cost entries with optional filters.

        Args:
            experiment_name: Filter by experiment name (default: all experiments)
            workflow_name: Filter by workflow name (default: all workflows)
            start_date: Filter runs starting after this date (default: no filter)
            end_date: Filter runs ending before this date (default: no filter)
            status_filter: Filter by status - "success" or "failure" (default: all)

        Returns:
            List of CostEntry objects matching the filters

        Raises:
            ValueError: If experiment doesn't exist or filters are invalid
        """
        # Get experiment(s)
        if experiment_name:
            try:
                experiment = mlflow.get_experiment_by_name(experiment_name)
                if experiment is None:
                    raise ValueError(f"Experiment not found: {experiment_name}")
                experiment_ids = [experiment.experiment_id]
            except Exception as e:
                raise ValueError(f"Failed to get experiment '{experiment_name}': {e}")
        else:
            # Get all experiments
            experiments = self.client.search_experiments()
            experiment_ids = [exp.experiment_id for exp in experiments]

        # Build filter string for MLFlow
        filter_parts = []

        if start_date:
            start_timestamp = int(start_date.timestamp() * 1000)
            filter_parts.append(f"attributes.start_time >= {start_timestamp}")

        if end_date:
            end_timestamp = int(end_date.timestamp() * 1000)
            filter_parts.append(f"attributes.start_time <= {end_timestamp}")

        if status_filter:
            if status_filter not in ["success", "failure"]:
                raise ValueError(f"Invalid status_filter: {status_filter}")
            # Status is logged as metric: 1 = success, 0 = failure
            status_value = "1" if status_filter == "success" else "0"
            filter_parts.append(f"metrics.status = {status_value}")

        filter_string = " and ".join(filter_parts) if filter_parts else None

        # Query runs across all experiments
        all_runs = []
        for exp_id in experiment_ids:
            try:
                runs = self.client.search_runs(
                    experiment_ids=[exp_id],
                    filter_string=filter_string,
                    order_by=["start_time DESC"],
                )
                all_runs.extend(runs)
            except Exception as e:
                logger.warning(f"Failed to query experiment {exp_id}: {e}")
                continue

        # Convert runs to CostEntry objects
        entries = []
        for run in all_runs:
            try:
                entry = self._run_to_cost_entry(run)

                # Apply workflow_name filter (client-side filtering)
                if workflow_name and entry.workflow_name != workflow_name:
                    continue

                entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to parse run {run.info.run_id}: {e}")
                continue

        logger.info(
            f"Found {len(entries)} cost entries matching filters "
            f"(experiment={experiment_name}, workflow={workflow_name})"
        )

        return entries

    def _run_to_cost_entry(self, run: Any) -> CostEntry:
        """Convert MLFlow run to CostEntry.

        Args:
            run: MLFlow Run object

        Returns:
            CostEntry object

        Raises:
            ValueError: If required metrics/params are missing
        """
        metrics = run.data.metrics
        params = run.data.params

        # Fail fast: Validate required fields exist
        required_metrics = [
            "total_cost_usd",
            "total_input_tokens",
            "total_output_tokens",
            "duration_seconds",
            "node_count",
            "status",
        ]

        missing_metrics = [m for m in required_metrics if m not in metrics]
        if missing_metrics:
            raise ValueError(
                f"Missing required metrics: {', '.join(missing_metrics)}. "
                f"This run may not have been tracked properly."
            )

        # Extract and validate required fields
        try:
            total_cost = float(metrics["total_cost_usd"])
            input_tokens = int(metrics["total_input_tokens"])
            output_tokens = int(metrics["total_output_tokens"])
            duration_seconds = float(metrics["duration_seconds"])
            node_count = int(metrics["node_count"])
            status_metric = float(metrics["status"])
            status = "success" if status_metric == 1.0 else "failure"

            # Workflow name is required
            if "workflow_name" not in params:
                raise ValueError("Missing required parameter: workflow_name")

            workflow_name = params["workflow_name"]
            model = params.get("global_model", None)  # Optional

            # Convert start time from milliseconds to datetime
            start_time_ms = run.info.start_time
            if start_time_ms is None:
                raise ValueError("Missing run start_time")

            start_time = datetime.fromtimestamp(start_time_ms / 1000)

        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid field value: {e}")

        return CostEntry(
            run_id=run.info.run_id,
            run_name=run.info.run_name or "unnamed",
            workflow_name=workflow_name,
            start_time=start_time,
            duration_seconds=duration_seconds,
            status=status,
            total_cost_usd=total_cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            node_count=node_count,
            model=model,
        )

    def generate_summary(self, entries: List[CostEntry]) -> CostSummary:
        """Generate aggregated cost summary from entries.

        Args:
            entries: List of CostEntry objects

        Returns:
            CostSummary with aggregated statistics
        """
        if not entries:
            # Return empty summary
            now = datetime.now()
            return CostSummary(
                total_cost_usd=0.0,
                total_runs=0,
                total_tokens=0,
                successful_runs=0,
                failed_runs=0,
                avg_cost_per_run=0.0,
                avg_tokens_per_run=0.0,
                date_range=(now, now),
                breakdown_by_workflow={},
                breakdown_by_model={},
            )

        # Aggregate totals
        total_cost = sum(e.total_cost_usd for e in entries)
        total_runs = len(entries)
        total_tokens = sum(e.input_tokens + e.output_tokens for e in entries)
        successful_runs = sum(1 for e in entries if e.status == "success")
        failed_runs = total_runs - successful_runs

        # Calculate averages
        avg_cost_per_run = total_cost / total_runs if total_runs > 0 else 0.0
        avg_tokens_per_run = total_tokens / total_runs if total_runs > 0 else 0.0

        # Date range
        start_times = [e.start_time for e in entries]
        date_range = (min(start_times), max(start_times))

        # Breakdown by workflow
        breakdown_by_workflow: Dict[str, float] = {}
        for entry in entries:
            workflow = entry.workflow_name
            breakdown_by_workflow[workflow] = (
                breakdown_by_workflow.get(workflow, 0.0) + entry.total_cost_usd
            )

        # Breakdown by model
        breakdown_by_model: Dict[str, float] = {}
        for entry in entries:
            if entry.model:
                breakdown_by_model[entry.model] = (
                    breakdown_by_model.get(entry.model, 0.0) + entry.total_cost_usd
                )

        return CostSummary(
            total_cost_usd=total_cost,
            total_runs=total_runs,
            total_tokens=total_tokens,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            avg_cost_per_run=avg_cost_per_run,
            avg_tokens_per_run=avg_tokens_per_run,
            date_range=date_range,
            breakdown_by_workflow=breakdown_by_workflow,
            breakdown_by_model=breakdown_by_model,
        )

    def aggregate_by_period(
        self,
        entries: List[CostEntry],
        period: str = "daily",  # "daily", "weekly", "monthly"
    ) -> Dict[str, float]:
        """Aggregate costs by time period.

        Args:
            entries: List of CostEntry objects
            period: Aggregation period - "daily", "weekly", or "monthly"

        Returns:
            Dict mapping period key (YYYY-MM-DD, YYYY-WW, or YYYY-MM) to total cost

        Raises:
            ValueError: If period is invalid
        """
        if period not in ["daily", "weekly", "monthly"]:
            raise ValueError(f"Invalid period: {period}. Use 'daily', 'weekly', or 'monthly'")

        aggregated: Dict[str, float] = {}

        for entry in entries:
            # Generate period key
            if period == "daily":
                key = entry.start_time.strftime("%Y-%m-%d")
            elif period == "weekly":
                # ISO week: YYYY-WW
                year, week, _ = entry.start_time.isocalendar()
                key = f"{year}-W{week:02d}"
            else:  # monthly
                key = entry.start_time.strftime("%Y-%m")

            # Accumulate cost
            aggregated[key] = aggregated.get(key, 0.0) + entry.total_cost_usd

        return aggregated

    def export_to_json(
        self,
        entries: List[CostEntry],
        output_path: str,
        include_summary: bool = True,
    ) -> None:
        """Export cost entries to JSON file.

        Args:
            entries: List of CostEntry objects
            output_path: Path to output JSON file
            include_summary: Whether to include summary statistics (default: True)
        """
        # Convert entries to dicts
        entries_data = [
            {
                "run_id": e.run_id,
                "run_name": e.run_name,
                "workflow_name": e.workflow_name,
                "start_time": e.start_time.isoformat(),
                "duration_seconds": e.duration_seconds,
                "status": e.status,
                "total_cost_usd": e.total_cost_usd,
                "input_tokens": e.input_tokens,
                "output_tokens": e.output_tokens,
                "node_count": e.node_count,
                "model": e.model,
            }
            for e in entries
        ]

        output_data: Dict[str, Any] = {"entries": entries_data}

        # Add summary if requested
        if include_summary:
            summary = self.generate_summary(entries)
            output_data["summary"] = {
                "total_cost_usd": summary.total_cost_usd,
                "total_runs": summary.total_runs,
                "total_tokens": summary.total_tokens,
                "successful_runs": summary.successful_runs,
                "failed_runs": summary.failed_runs,
                "avg_cost_per_run": summary.avg_cost_per_run,
                "avg_tokens_per_run": summary.avg_tokens_per_run,
                "date_range": [
                    summary.date_range[0].isoformat(),
                    summary.date_range[1].isoformat(),
                ],
                "breakdown_by_workflow": summary.breakdown_by_workflow,
                "breakdown_by_model": summary.breakdown_by_model,
            }

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        logger.info(f"Exported {len(entries)} cost entries to {output_path}")

    def export_to_csv(
        self,
        entries: List[CostEntry],
        output_path: str,
    ) -> None:
        """Export cost entries to CSV file.

        Args:
            entries: List of CostEntry objects
            output_path: Path to output CSV file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "run_id",
                    "run_name",
                    "workflow_name",
                    "start_time",
                    "duration_seconds",
                    "status",
                    "total_cost_usd",
                    "input_tokens",
                    "output_tokens",
                    "total_tokens",
                    "node_count",
                    "model",
                ],
            )

            writer.writeheader()

            for entry in entries:
                writer.writerow(
                    {
                        "run_id": entry.run_id,
                        "run_name": entry.run_name,
                        "workflow_name": entry.workflow_name,
                        "start_time": entry.start_time.isoformat(),
                        "duration_seconds": entry.duration_seconds,
                        "status": entry.status,
                        "total_cost_usd": entry.total_cost_usd,
                        "input_tokens": entry.input_tokens,
                        "output_tokens": entry.output_tokens,
                        "total_tokens": entry.input_tokens + entry.output_tokens,
                        "node_count": entry.node_count,
                        "model": entry.model or "",
                    }
                )

        logger.info(f"Exported {len(entries)} cost entries to {output_path}")


def get_date_range_filter(
    period: str,
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Helper to generate date range filters for common periods.

    Args:
        period: Period string - "today", "yesterday", "last_7_days", "last_30_days", "this_month"

    Returns:
        Tuple of (start_date, end_date) for the period

    Raises:
        ValueError: If period is invalid
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "today":
        return (today_start, now)

    elif period == "yesterday":
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start
        return (yesterday_start, yesterday_end)

    elif period == "last_7_days":
        start = today_start - timedelta(days=7)
        return (start, now)

    elif period == "last_30_days":
        start = today_start - timedelta(days=30)
        return (start, now)

    elif period == "this_month":
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return (month_start, now)

    else:
        raise ValueError(
            f"Invalid period: {period}. "
            f"Use 'today', 'yesterday', 'last_7_days', 'last_30_days', or 'this_month'"
        )
