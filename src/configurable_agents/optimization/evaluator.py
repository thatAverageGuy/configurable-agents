"""Experiment evaluation and variant comparison.

Queries MLFlow for experiment data, aggregates metrics by variant,
and provides comparison functionality for finding the best performing
prompt variant.

Key features:
- Query MLFlow experiments for all runs
- Aggregate metrics by variant (avg, p95, p99)
- Compare variants by different metrics (cost, latency, tokens)
- Find best performing variant
- Retrieve original prompts from MLFlow
- Format comparison tables for CLI output
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional MLFlow import
try:
    import mlflow
    from mlflow.tracking import MlflowClient
    from mlflow.entities import ViewType
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MlflowClient = None
    ViewType = None
    MLFLOW_AVAILABLE = False


@dataclass
class VariantMetrics:
    """Aggregated metrics for a single variant.

    Attributes:
        variant_name: Name of the variant
        run_count: Number of runs in aggregation
        metrics: Aggregated metric values (avg, p95, p99)
        run_ids: List of MLFlow run IDs
    """

    variant_name: str
    run_count: int
    metrics: Dict[str, Any] = field(default_factory=dict)
    run_ids: List[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Result of variant comparison.

    Attributes:
        experiment_name: Name of the experiment
        metric: Metric used for comparison
        variants: List of VariantMetrics sorted by rank
        best_variant: Name of the best performing variant
    """

    experiment_name: str
    metric: str
    variants: List[VariantMetrics]
    best_variant: Optional[str] = None


class ExperimentEvaluator:
    """Evaluator for MLFlow experiment comparison.

    Queries MLFlow experiments, aggregates metrics by variant,
    and provides comparison functionality.

    Example:
        >>> from configurable_agents.optimization import ExperimentEvaluator
        >>> evaluator = ExperimentEvaluator("sqlite:///mlflow.db")
        >>> comparison = evaluator.compare_variants("prompt_test", metric="cost_usd")
        >>> print(f"Best variant: {comparison.best_variant}")
        >>> table = evaluator.format_comparison_table(comparison)
        >>> print(table)
    """

    def __init__(self, mlflow_tracking_uri: Optional[str] = None):
        """Initialize experiment evaluator.

        Args:
            mlflow_tracking_uri: MLFlow tracking URI (default: from env or sqlite:///mlflow.db)
        """
        if not MLFLOW_AVAILABLE:
            raise RuntimeError(
                "MLFlow is required for experiment evaluation. "
                "Install with: pip install mlflow>=3.9.0"
            )

        self.mlflow_tracking_uri = mlflow_tracking_uri or os.environ.get(
            "MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"
        )
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        self.client = MlflowClient()

        logger.debug(f"ExperimentEvaluator initialized with URI: {self.mlflow_tracking_uri}")

    def get_experiment_runs(
        self,
        experiment_name: str,
        max_results: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get all runs for an experiment.

        Args:
            experiment_name: Name of the experiment
            max_results: Maximum number of runs to return

        Returns:
            List of run dicts with keys: run_id, params, metrics, tags
        """
        # Get experiment
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_name}")

        # Query runs
        runs = self.client.search_runs(
            experiment_ids=[experiment.experiment_id],
            max_results=max_results,
            order_by=["start_time DESC"],
        )

        # Convert to simplified dict format
        result = []
        for run in runs:
            result.append({
                "run_id": run.info.run_id,
                "params": dict(run.data.params) if run.data.params else {},
                "metrics": dict(run.data.metrics) if run.data.metrics else {},
                "tags": dict(run.data.tags) if run.data.tags else {},
                "start_time": datetime.fromtimestamp(run.info.start_time / 1000) if run.info.start_time else None,
                "status": run.info.status,
            })

        logger.debug(f"Retrieved {len(result)} runs from experiment: {experiment_name}")
        return result

    def aggregate_by_variant(self, runs: List[Dict[str, Any]]) -> Dict[str, VariantMetrics]:
        """Aggregate metrics by variant.

        Groups runs by variant_name tag, calculates avg/p95/p99
        for numeric metrics.

        Args:
            runs: List of run dicts

        Returns:
            Mapping of variant name to VariantMetrics
        """
        # Group by variant
        variants: Dict[str, List[Dict[str, Any]]] = {}

        for run in runs:
            variant_name = run["tags"].get("variant_name", "default")
            if variant_name not in variants:
                variants[variant_name] = []
            variants[variant_name].append(run)

        # Aggregate metrics for each variant
        result = {}

        for variant_name, variant_runs in variants.items():
            metrics = self._calculate_variant_metrics(variant_runs)
            run_ids = [r["run_id"] for r in variant_runs]

            result[variant_name] = VariantMetrics(
                variant_name=variant_name,
                run_count=len(variant_runs),
                metrics=metrics,
                run_ids=run_ids,
            )

        return result

    def _calculate_variant_metrics(self, runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aggregated metrics for a variant.

        Args:
            runs: List of run dicts for a single variant

        Returns:
            Aggregated metrics dict with avg, min, max, p95, p99
        """
        # Collect all metric keys across runs
        metric_keys = set()
        for run in runs:
            metric_keys.update(run["metrics"].keys())

        aggregated = {}

        for key in metric_keys:
            values = [run["metrics"].get(key) for run in runs if key in run["metrics"]]

            # Filter out None values
            values = [v for v in values if v is not None]

            if values:
                # Calculate stats
                percentiles = calculate_percentiles(values)
                aggregated[f"{key}_avg"] = sum(values) / len(values)
                aggregated[f"{key}_min"] = min(values)
                aggregated[f"{key}_max"] = max(values)
                aggregated[f"{key}_p50"] = percentiles["p50"]
                aggregated[f"{key}_p95"] = percentiles["p95"]
                aggregated[f"{key}_p99"] = percentiles["p99"]

        return aggregated

    def compare_variants(
        self,
        experiment_name: str,
        metric: str = "cost_usd_avg",
        ascending: bool = True,
    ) -> ComparisonResult:
        """Compare variants in an experiment by a specific metric.

        Args:
            experiment_name: Name of the experiment
            metric: Metric to compare (default: cost_usd_avg)
            ascending: Sort order (True = lower is better, e.g., cost)

        Returns:
            ComparisonResult with variants sorted by rank
        """
        runs = self.get_experiment_runs(experiment_name)
        variant_metrics = self.aggregate_by_variant(runs)

        # Sort variants by metric
        sorted_variants = sorted(
            variant_metrics.values(),
            key=lambda v: v.metrics.get(metric, float("inf" if ascending else float("-inf"))),
            reverse=not ascending,
        )

        # Find best variant (first after sorting)
        best_variant = sorted_variants[0].variant_name if sorted_variants else None

        return ComparisonResult(
            experiment_name=experiment_name,
            metric=metric,
            variants=sorted_variants,
            best_variant=best_variant,
        )

    def find_best_variant(
        self,
        experiment_name: str,
        primary_metric: str = "cost_usd_avg",
        min_runs: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """Find the best performing variant in an experiment.

        Args:
            experiment_name: Name of the experiment
            primary_metric: Metric to optimize (default: cost_usd_avg)
            min_runs: Minimum number of runs required to consider a variant

        Returns:
            Dict with keys: variant_name, metrics, run_id, prompt
        """
        comparison = self.compare_variants(experiment_name, primary_metric)

        # Filter variants with min_runs
        qualified_variants = [
            v for v in comparison.variants
            if v.run_count >= min_runs
        ]

        if not qualified_variants:
            logger.warning(
                f"No variants with >= {min_runs} runs in experiment: {experiment_name}"
            )
            return None

        best = qualified_variants[0]

        # Get prompt from one of the runs
        prompt = None
        run_id = best.run_ids[0] if best.run_ids else None
        if run_id:
            prompt = self.get_prompt_from_run(run_id)

        return {
            "variant_name": best.variant_name,
            "metrics": best.metrics,
            "run_id": run_id,
            "prompt": prompt,
            "run_count": best.run_count,
        }

    def get_prompt_from_run(self, run_id: str) -> Optional[str]:
        """Retrieve original prompt from MLFlow run params.

        Args:
            run_id: MLFlow run ID

        Returns:
            Prompt string or None if not found
        """
        try:
            run = self.client.get_run(run_id)
            return run.data.params.get("prompt")
        except Exception as e:
            logger.warning(f"Failed to retrieve prompt from run {run_id}: {e}")
            return None

    def list_experiments(self) -> List[Dict[str, Any]]:
        """List all available experiments.

        Returns:
            List of experiment dicts with keys: name, id, run_count
        """
        experiments = self.client.search_experiments(view_type=ViewType.ACTIVE_ONLY)

        result = []
        for exp in experiments:
            # Get run count
            runs = self.client.search_runs(
                experiment_ids=[exp.experiment_id],
                max_results=1,
            )
            run_count = len(runs) if runs else 0

            result.append({
                "name": exp.name,
                "id": exp.experiment_id,
                "run_count": run_count,
            })

        return result


def compare_variants(
    experiment_name: str,
    metric: str = "cost_usd_avg",
    mlflow_tracking_uri: Optional[str] = None,
) -> ComparisonResult:
    """Convenience function to compare variants.

    Args:
        experiment_name: Name of the experiment
        metric: Metric to compare (default: cost_usd_avg)
        mlflow_tracking_uri: MLFlow tracking URI

    Returns:
        ComparisonResult with sorted variants

    Example:
        >>> from configurable_agents.optimization import compare_variants
        >>> result = compare_variants("prompt_test", metric="cost_usd_avg")
        >>> print(f"Best: {result.best_variant}")
    """
    evaluator = ExperimentEvaluator(mlflow_tracking_uri=mlflow_tracking_uri)
    return evaluator.compare_variants(experiment_name, metric)


def find_best_variant(
    experiment_name: str,
    primary_metric: str = "cost_usd_avg",
    mlflow_tracking_uri: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Convenience function to find best variant.

    Args:
        experiment_name: Name of the experiment
        primary_metric: Metric to optimize (default: cost_usd_avg)
        mlflow_tracking_uri: MLFlow tracking URI

    Returns:
        Dict with variant info or None

    Example:
        >>> from configurable_agents.optimization import find_best_variant
        >>> best = find_best_variant("prompt_test")
        >>> if best:
        ...     print(f"Best: {best['variant_name']}")
    """
    evaluator = ExperimentEvaluator(mlflow_tracking_uri=mlflow_tracking_uri)
    return evaluator.find_best_variant(experiment_name, primary_metric)


def format_comparison_table(comparison: ComparisonResult) -> str:
    """Format comparison result as CLI table.

    Args:
        comparison: ComparisonResult from compare_variants()

    Returns:
        Formatted table string

    Example:
        >>> from configurable_agents.optimization import compare_variants, format_comparison_table
        >>> result = compare_variants("prompt_test")
        >>> print(format_comparison_table(result))
    """
    lines = [
        f"Experiment: {comparison.experiment_name}",
        f"Metric: {comparison.metric}",
        f"Best variant: {comparison.best_variant or 'N/A'}",
        "=" * 80,
        f"{'Rank':<6} {'Variant':<20} {'Runs':<6} {'Avg':<12} {'Min':<12} {'Max':<12}",
        "-" * 80,
    ]

    for rank, variant in enumerate(comparison.variants, 1):
        name = variant.variant_name
        runs = variant.run_count
        avg = variant.metrics.get(comparison.metric, 0)
        min_val = variant.metrics.get(f"{comparison.metric.replace('_avg', '')}_min", 0)
        max_val = variant.metrics.get(f"{comparison.metric.replace('_avg', '')}_max", 0)

        # Format values
        if isinstance(avg, float) and "cost" in comparison.metric:
            avg_str = f"${avg:.6f}"
            min_str = f"${min_val:.6f}"
            max_str = f"${max_val:.6f}"
        elif isinstance(avg, float):
            avg_str = f"{avg:.2f}"
            min_str = f"{min_val:.2f}"
            max_str = f"{max_val:.2f}"
        else:
            avg_str = str(avg)
            min_str = str(min_val)
            max_str = str(max_val)

        # Mark best variant
        marker = " * " if name == comparison.best_variant else "   "

        lines.append(
            f"{rank:<6} {name:<20} {runs:<6} {avg_str:<12} {min_str:<12} {max_str:<12}{marker}"
        )

    lines.append("=" * 80)
    lines.append("* = Best performing variant")

    return "\n".join(lines)


def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """Calculate percentiles for a list of numeric values.

    Uses nearest-rank method: index = ceil(p/100 * n) - 1

    Args:
        values: List of numeric values

    Returns:
        Dict with p50, p95, p99 percentiles
    """
    if not values:
        return {"p50": 0, "p95": 0, "p99": 0}

    sorted_values = sorted(values)
    n = len(sorted_values)

    def percentile(p: float) -> float:
        """Calculate percentile using nearest-rank method."""
        import math
        # Nearest-rank: ceil(p/100 * n) - 1 gives 0-based index
        idx = math.ceil(p / 100 * n) - 1
        idx = max(0, min(idx, n - 1))  # Clamp to valid range
        return sorted_values[int(idx)]

    return {
        "p50": percentile(50),
        "p95": percentile(95),
        "p99": percentile(99),
    }
