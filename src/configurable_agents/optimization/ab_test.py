"""A/B testing runner for prompt variant experiments.

Enables systematic prompt experimentation by running workflow variants
and tracking metrics to MLFlow for comparison.

Key features:
- Define prompt variants in config or programmatically
- Run each variant multiple times for statistical significance
- Track metrics (cost, latency, tokens, success rate) to MLFlow
- Tag runs for easy filtering and comparison
- Apply winning prompt back to workflow config
"""

import copy
import hashlib
import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from configurable_agents.config import WorkflowConfig, parse_config_file, validate_config
from configurable_agents.runtime import run_workflow_from_config

logger = logging.getLogger(__name__)

# Optional MLFlow import
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MLFLOW_AVAILABLE = False
    logger.warning(
        "MLFlow not installed. A/B test features disabled. "
        "Install with: pip install mlflow>=3.9.0"
    )


@dataclass
class VariantConfig:
    """Configuration for a single prompt variant.

    Attributes:
        name: Human-readable variant name (e.g., "concise", "detailed")
        prompt: The prompt template to test
        config_overrides: Optional config overrides (for non-prompt changes)
        node_id: Optional specific node to apply prompt to (default: first node)
    """

    name: str
    prompt: str
    config_overrides: Optional[Dict[str, Any]] = None
    node_id: Optional[str] = None

    def __hash__(self) -> int:
        """Hash variant config for deduplication."""
        return hash((self.name, self.prompt))

    def __eq__(self, other) -> bool:
        """Compare variant configs."""
        if not isinstance(other, VariantConfig):
            return False
        return self.name == other.name and self.prompt == other.prompt


@dataclass
class ABTestConfig:
    """Configuration for A/B test execution.

    Attributes:
        experiment_name: MLFlow experiment name for grouping results
        variants: List of prompt variants to test
        run_count: Number of times to run each variant (default: 3)
        parallel: Run variants concurrently (default: True)
        inputs: Inputs to pass to each workflow run
    """

    experiment_name: str
    variants: List[VariantConfig]
    run_count: int = 3
    parallel: bool = True
    inputs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VariantResult:
    """Results for a single variant execution.

    Attributes:
        variant_name: Name of the variant
        run_count: Number of successful runs completed
        metrics: Aggregated metrics across all runs
        run_ids: List of MLFlow run IDs for this variant
        errors: List of errors encountered during runs
    """

    variant_name: str
    run_count: int
    metrics: Dict[str, Any]
    run_ids: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class ABTestResult:
    """Complete A/B test results.

    Attributes:
        experiment_name: Name of the experiment
        variants: Mapping of variant name to VariantResult
        best_variant: Name of the best performing variant
        summary: Human-readable summary
    """

    experiment_name: str
    variants: Dict[str, VariantResult]
    best_variant: Optional[str] = None
    summary: str = ""


class ABTestRunner:
    """Runner for A/B testing prompt variants.

    Executes workflow variants, tracks metrics to MLFlow, and provides
    comparison results.

    Example:
        >>> from configurable_agents.optimization import ABTestRunner, VariantConfig, ABTestConfig
        >>> variants = [
        ...     VariantConfig(name="concise", prompt="Be concise: {topic}"),
        ...     VariantConfig(name="detailed", prompt="Be detailed: {topic}"),
        ... ]
        >>> config = ABTestConfig(experiment_name="prompt_test", variants=variants, run_count=3)
        >>> runner = ABTestRunner()
        >>> result = runner.run(config, "workflow.yaml", {"topic": "AI"})
        >>> print(f"Best variant: {result.best_variant}")
    """

    def __init__(self, mlflow_tracking_uri: Optional[str] = None):
        """Initialize A/B test runner.

        Args:
            mlflow_tracking_uri: MLFlow tracking URI (default: from env or sqlite:///mlflow.db)
        """
        self.mlflow_tracking_uri = mlflow_tracking_uri or os.environ.get(
            "MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"
        )

        if MLFLOW_AVAILABLE:
            try:
                mlflow.set_tracking_uri(self.mlflow_tracking_uri)
                logger.debug(f"MLFlow tracking URI: {self.mlflow_tracking_uri}")
            except Exception as e:
                logger.warning(f"Failed to set MLFlow tracking URI: {e}")

    def run(
        self,
        config: ABTestConfig,
        workflow_path: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> ABTestResult:
        """Run A/B test across all variants.

        Args:
            config: A/B test configuration
            workflow_path: Path to workflow YAML file
            inputs: Optional inputs override (uses config.inputs if not provided)

        Returns:
            ABTestResult with aggregated results across all variants

        Raises:
            ValueError: If workflow config is invalid
            RuntimeError: If MLFlow is not available
        """
        if not MLFLOW_AVAILABLE:
            raise RuntimeError("MLFlow is required for A/B testing. Install with: pip install mlflow")

        if not config.variants:
            raise ValueError("At least one variant must be specified")

        # Merge inputs
        run_inputs = {**config.inputs, **(inputs or {})}

        # Load base workflow config
        workflow_config = self._load_workflow_config(workflow_path)

        # Create/get MLFlow experiment
        experiment_id = self._get_or_create_experiment(config.experiment_name)
        logger.info(f"Running A/B test in experiment: {config.experiment_name} (ID: {experiment_id})")

        # Run each variant
        variant_results: Dict[str, VariantResult] = {}

        for variant in config.variants:
            logger.info(f"Running variant '{variant.name}' ({config.run_count} runs)")
            result = self._run_variant(
                variant=variant,
                workflow_config=workflow_config,
                workflow_path=workflow_path,
                inputs=run_inputs,
                run_count=config.run_count,
                experiment_name=config.experiment_name,
            )
            variant_results[variant.name] = result
            logger.info(
                f"Variant '{variant.name}' completed: "
                f"{result.run_count}/{config.run_count} successful runs, "
                f"avg cost: ${result.metrics.get('avg_cost_usd', 0):.6f}"
            )

        # Determine best variant (by cost, lower is better)
        best_variant = self._find_best_variant(variant_results)

        # Generate summary
        summary = self._generate_summary(variant_results, best_variant)

        return ABTestResult(
            experiment_name=config.experiment_name,
            variants=variant_results,
            best_variant=best_variant,
            summary=summary,
        )

    def _run_variant(
        self,
        variant: VariantConfig,
        workflow_config: WorkflowConfig,
        workflow_path: str,
        inputs: Dict[str, Any],
        run_count: int,
        experiment_name: str,
    ) -> VariantResult:
        """Run a single variant multiple times.

        Args:
            variant: Variant configuration
            workflow_config: Base workflow config
            workflow_path: Path to workflow file (for prompt application)
            inputs: Workflow inputs
            run_count: Number of runs
            experiment_name: MLFlow experiment name

        Returns:
            VariantResult with aggregated metrics
        """
        metrics_history = []
        errors = []
        run_ids = []
        successful_runs = 0

        # Calculate prompt hash for tagging
        prompt_hash = hashlib.sha256(variant.prompt.encode()).hexdigest()[:16]

        for run_idx in range(run_count):
            run_name = f"{variant.name}_run{run_idx + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            try:
                # Create modified config with variant prompt
                modified_config = self._apply_variant_to_config(
                    workflow_config, variant
                )

                # Start MLFlow run
                with mlflow.start_run(
                    experiment_id=mlflow.get_experiment_by_name(experiment_name).experiment_id,
                    run_name=run_name,
                    tags={
                        "variant_name": variant.name,
                        "prompt_hash": prompt_hash,
                        "ab_test": "true",
                    },
                ):
                    run_id = mlflow.active_run().info.run_id
                    run_ids.append(run_id)

                    # Log variant parameters
                    mlflow.log_params({
                        "variant_name": variant.name,
                        "prompt": variant.prompt,
                        "prompt_hash": prompt_hash,
                    })

                    # Run workflow
                    start_time = datetime.now()
                    result_state = run_workflow_from_config(modified_config, inputs, verbose=False)
                    end_time = datetime.now()

                    # Calculate metrics
                    duration_ms = (end_time - start_time).total_seconds() * 1000

                    # Extract metrics from state (if profiler tracked them)
                    cost_usd = 0.0
                    total_tokens = 0

                    # Check for execution metadata in state
                    for key in dir(result_state):
                        if key.startswith("_cost_usd_"):
                            cost_usd += getattr(result_state, key, 0)
                        if key.startswith("_execution_time_ms_"):
                            duration_ms += getattr(result_state, key, 0)

                    # Log metrics
                    mlflow.log_metrics({
                        "duration_ms": duration_ms,
                        "cost_usd": cost_usd,
                        "total_tokens": total_tokens,
                        "success": 1,
                    })

                    metrics_history.append({
                        "duration_ms": duration_ms,
                        "cost_usd": cost_usd,
                        "total_tokens": total_tokens,
                        "success": True,
                    })
                    successful_runs += 1

            except Exception as e:
                logger.error(f"Run {run_idx + 1} for variant '{variant.name}' failed: {e}")
                errors.append(str(e))

                # Log failed run
                try:
                    with mlflow.start_run(
                        experiment_id=mlflow.get_experiment_by_name(experiment_name).experiment_id,
                        run_name=f"{variant.name}_run{run_idx + 1}_failed",
                        tags={
                            "variant_name": variant.name,
                            "prompt_hash": prompt_hash,
                            "ab_test": "true",
                        },
                    ):
                        mlflow.log_metrics({"success": 0})
                        run_ids.append(mlflow.active_run().info.run_id)
                except Exception:
                    pass  # Best effort logging

        # Aggregate metrics
        aggregated = self._aggregate_metrics(metrics_history)

        return VariantResult(
            variant_name=variant.name,
            run_count=successful_runs,
            metrics=aggregated,
            run_ids=run_ids,
            errors=errors,
        )

    def _apply_variant_to_config(
        self,
        base_config: WorkflowConfig,
        variant: VariantConfig,
    ) -> WorkflowConfig:
        """Apply variant prompt to workflow config.

        Args:
            base_config: Base workflow configuration
            variant: Variant with prompt to apply

        Returns:
            New WorkflowConfig with variant prompt applied
        """
        # Deep copy to avoid mutating original
        config_dict = copy.deepcopy(base_config.model_dump())

        # Find target node
        if variant.node_id:
            # Apply to specific node
            node_found = False
            for node in config_dict.get("nodes", []):
                if node["id"] == variant.node_id:
                    node["prompt"] = variant.prompt
                    node_found = True
                    break
            if not node_found:
                raise ValueError(f"Node '{variant.node_id}' not found in workflow")
        else:
            # Apply to first node (default behavior)
            nodes = config_dict.get("nodes", [])
            if not nodes:
                raise ValueError("Workflow has no nodes")
            nodes[0]["prompt"] = variant.prompt

        # Apply any config overrides
        if variant.config_overrides:
            self._apply_config_overrides(config_dict, variant.config_overrides)

        # Reconstruct WorkflowConfig
        return WorkflowConfig(**config_dict)

    def _apply_config_overrides(self, config_dict: Dict[str, Any], overrides: Dict[str, Any]) -> None:
        """Apply config overrides to config dict.

        Args:
            config_dict: Config dict to modify in place
            overrides: Override values
        """
        for key, value in overrides.items():
            if "." in key:
                # Nested key (e.g., "config.observability.mlflow.experiment_name")
                parts = key.split(".")
                current = config_dict
                for part in parts[:-1]:
                    if part not in current or current[part] is None:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                config_dict[key] = value

    def _aggregate_metrics(self, metrics_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate metrics across multiple runs.

        Calculates avg, min, max, p95, p99 for numeric metrics.

        Args:
            metrics_history: List of metric dicts from individual runs

        Returns:
            Aggregated metrics dict
        """
        if not metrics_history:
            return {
                "avg_cost_usd": 0,
                "avg_duration_ms": 0,
                "avg_tokens": 0,
                "success_rate": 0,
            }

        numeric_keys = ["cost_usd", "duration_ms", "total_tokens"]
        aggregated = {}

        for key in numeric_keys:
            values = [m.get(key, 0) for m in metrics_history if key in m]
            if values:
                percentiles = calculate_percentiles(values)
                aggregated[f"avg_{key}"] = sum(values) / len(values)
                aggregated[f"min_{key}"] = min(values)
                aggregated[f"max_{key}"] = max(values)
                aggregated[f"p95_{key}"] = percentiles.get("p95", 0)
                aggregated[f"p99_{key}"] = percentiles.get("p99", 0)
            else:
                aggregated[f"avg_{key}"] = 0

        # Success rate
        successful = sum(1 for m in metrics_history if m.get("success", False))
        aggregated["success_rate"] = successful / len(metrics_history) if metrics_history else 0

        return aggregated

    def _find_best_variant(self, variant_results: Dict[str, VariantResult]) -> Optional[str]:
        """Find best variant based on average cost.

        Args:
            variant_results: Mapping of variant name to results

        Returns:
            Name of best variant (lowest avg cost) or None
        """
        if not variant_results:
            return None

        best_name = None
        best_cost = float("inf")

        for name, result in variant_results.items():
            if result.run_count > 0:  # Only consider variants with successful runs
                cost = result.metrics.get("avg_cost_usd", float("inf"))
                if cost < best_cost:
                    best_cost = cost
                    best_name = name

        return best_name

    def _generate_summary(
        self,
        variant_results: Dict[str, VariantResult],
        best_variant: Optional[str],
    ) -> str:
        """Generate human-readable summary.

        Args:
            variant_results: Mapping of variant name to results
            best_variant: Name of best variant

        Returns:
            Summary string
        """
        lines = [
            "A/B Test Results",
            "=" * 50,
        ]

        for name, result in sorted(variant_results.items()):
            best_marker = " [BEST]" if name == best_variant else ""
            lines.append(
                f"{name}{best_marker}: {result.run_count} runs, "
                f"${result.metrics.get('avg_cost_usd', 0):.6f} avg cost, "
                f"{result.metrics.get('success_rate', 0):.1%} success rate"
            )

            if result.errors:
                lines.append(f"  Errors: {len(result.errors)}")

        return "\n".join(lines)

    def _load_workflow_config(self, workflow_path: str) -> WorkflowConfig:
        """Load workflow config from file.

        Args:
            workflow_path: Path to workflow YAML file

        Returns:
            Validated WorkflowConfig
        """
        config_dict = parse_config_file(workflow_path)
        config = WorkflowConfig(**config_dict)
        validate_config(config)
        return config

    def _get_or_create_experiment(self, experiment_name: str) -> str:
        """Get or create MLFlow experiment.

        Args:
            experiment_name: Name of experiment

        Returns:
            Experiment ID
        """
        if not MLFLOW_AVAILABLE:
            raise RuntimeError("MLFlow is required")

        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment:
                return experiment.experiment_id
        except Exception:
            pass

        # Create new experiment
        experiment = mlflow.create_experiment(experiment_name)
        return experiment.experiment_id


def run_ab_test(
    experiment_name: str,
    workflow_path: str,
    variants: List[VariantConfig],
    run_count: int = 3,
    inputs: Optional[Dict[str, Any]] = None,
    mlflow_tracking_uri: Optional[str] = None,
) -> ABTestResult:
    """Convenience function to run A/B test.

    Args:
        experiment_name: MLFlow experiment name
        workflow_path: Path to workflow YAML file
        variants: List of variant configs
        run_count: Number of runs per variant
        inputs: Optional workflow inputs
        mlflow_tracking_uri: MLFlow tracking URI

    Returns:
        ABTestResult with aggregated results

    Example:
        >>> from configurable_agents.optimization import run_ab_test, VariantConfig
        >>> variants = [
        ...     VariantConfig(name="v1", prompt="Prompt 1: {input}"),
        ...     VariantConfig(name="v2", prompt="Prompt 2: {input}"),
        ... ]
        >>> result = run_ab_test("test_exp", "workflow.yaml", variants, run_count=3)
        >>> print(result.summary)
    """
    config = ABTestConfig(
        experiment_name=experiment_name,
        variants=variants,
        run_count=run_count,
        inputs=inputs or {},
    )

    runner = ABTestRunner(mlflow_tracking_uri=mlflow_tracking_uri)
    return runner.run(config, workflow_path)


def apply_prompt_to_workflow(
    workflow_path: str,
    prompt: str,
    node_id: Optional[str] = None,
    backup: bool = True,
) -> str:
    """Apply optimized prompt to workflow config.

    Updates the workflow YAML file with a new prompt, optionally
    creating a backup of the original.

    Args:
        workflow_path: Path to workflow YAML file
        prompt: New prompt to apply
        node_id: Optional node ID (default: first node)
        backup: Create backup of original file

    Returns:
        Path to the modified file (or backup path if backup=True)

    Raises:
        FileNotFoundError: If workflow file doesn't exist
        ValueError: If node_id not found
    """
    workflow_path = Path(workflow_path)

    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    # Load config
    with open(workflow_path) as f:
        config_dict = yaml.safe_load(f)

    # Create backup
    if backup:
        backup_path = workflow_path.with_suffix(
            f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        )
        shutil.copy2(workflow_path, backup_path)
        logger.info(f"Created backup: {backup_path}")

    # Find and update prompt
    nodes = config_dict.get("nodes", [])
    if node_id:
        node_found = False
        for node in nodes:
            if node["id"] == node_id:
                node["prompt"] = prompt
                node_found = True
                break
        if not node_found:
            raise ValueError(f"Node '{node_id}' not found in workflow")
    else:
        if not nodes:
            raise ValueError("Workflow has no nodes")
        nodes[0]["prompt"] = prompt

    # Write updated config
    with open(workflow_path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Updated prompt in workflow: {workflow_path}")

    return str(backup_path) if backup else str(workflow_path)


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
