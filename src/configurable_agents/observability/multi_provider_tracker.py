"""Multi-provider cost tracking for unified LLM cost reporting.

Tracks and aggregates costs across multiple LLM providers (OpenAI, Anthropic, Google, Ollama).
Provides provider-aware cost summaries with automatic provider detection from model names.
Integrates with MLFlowTracker for workflow-level cost reporting.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from configurable_agents.observability.cost_estimator import CostEstimator

logger = logging.getLogger(__name__)

# Optional MLFlow import for generate_cost_report function
try:
    import mlflow
    from mlflow.tracking import MlflowClient

    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MlflowClient = None
    MLFLOW_AVAILABLE = False
    logger.warning(
        "MLFlow not installed. generate_cost_report() requires MLFlow. "
        "Install with: pip install mlflow>=3.9.0"
    )


@dataclass
class ProviderCostEntry:
    """Single cost entry for a provider call."""

    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ProviderCostSummary:
    """Aggregated cost summary by provider."""

    total_cost_usd: float
    total_tokens: int
    by_provider: Dict[str, Dict[str, Any]]  # provider -> {total_cost, total_tokens, calls}
    total_calls: int


def _extract_provider(model_name: str) -> str:
    """Extract provider from model name.

    Supports both LiteLLM-style provider prefixes ("openai/gpt-4o")
    and bare model names ("gpt-4o", "claude-3-opus").

    Args:
        model_name: Model name with optional provider prefix

    Returns:
        Provider name: "openai", "anthropic", "google", "ollama", or "unknown"

    Examples:
        >>> _extract_provider("openai/gpt-4o")
        'openai'
        >>> _extract_provider("anthropic/claude-3-opus")
        'anthropic'
        >>> _extract_provider("gemini-pro")
        'google'
        >>> _extract_provider("ollama/llama2")
        'ollama'
    """
    model_lower = model_name.lower()

    # Check for LiteLLM-style provider prefix (provider/model)
    if "/" in model_lower:
        provider_prefix = model_lower.split("/", 1)[0]
        provider_map = {
            "openai": "openai",
            "anthropic": "anthropic",
            "google": "google",
            "gemini": "google",  # Some use "gemini/model-name"
            "ollama": "ollama",
            "ollama_chat": "ollama",
        }
        if provider_prefix in provider_map:
            return provider_map[provider_prefix]

    # Auto-detect from bare model name
    # OpenAI: models starting with "gpt-"
    if model_lower.startswith("gpt-") or "openai" in model_lower:
        return "openai"

    # Anthropic: models starting with "claude-"
    if model_lower.startswith("claude-") or "anthropic" in model_lower:
        return "anthropic"

    # Google: models starting with "gemini-" or containing "gemini"
    if "gemini" in model_lower or "google" in model_lower:
        return "google"

    # Ollama: common local model names
    if any(
        x in model_lower
        for x in ["llama", "mistral", "qwen", "phi", "gemma", "deepseek"]
    ):
        return "ollama"

    return "unknown"


def _is_ollama_model(provider: str) -> bool:
    """Check if provider is Ollama (local models, zero cost).

    Args:
        provider: Provider name from _extract_provider()

    Returns:
        True if Ollama (local, free), False otherwise
    """
    return provider == "ollama"


class MultiProviderCostTracker:
    """Unified cost tracking across multiple LLM providers.

    Tracks token usage and costs for LLM calls across OpenAI, Anthropic, Google, and Ollama.
    Provides provider-aware cost summaries with automatic provider detection.

    Example:
        >>> tracker = MultiProviderCostTracker()
        >>> # Track a call
        >>> result = tracker.track_call(
        ...     provider="openai",
        ...     model="gpt-4o",
        ...     response=llm_response
        ... )
        >>> print(f"Cost: ${result['cost_usd']:.6f}")
        >>> # Get summary
        >>> summary = tracker.get_cost_summary()
        >>> print(f"Total: ${summary['total_cost_usd']:.6f}")
    """

    def __init__(self, mlflow_tracker: Optional[Any] = None):
        """Initialize multi-provider cost tracker.

        Args:
            mlflow_tracker: Optional MLFlowTracker instance for integration
        """
        self.mlflow_tracker = mlflow_tracker
        self.cost_estimator = CostEstimator()
        self._call_history: List[ProviderCostEntry] = []

    def track_call(
        self, provider: str, model: str, response: Any
    ) -> Dict[str, Any]:
        """Track a single LLM call and extract cost metrics.

        Extracts token usage from LLM response formats (LiteLLM or direct provider).
        Calculates cost using CostEstimator. Stores entry in internal history.

        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            model: Model name (e.g., "gpt-4o", "claude-3-opus")
            response: LLM response object (LiteLLM response or provider response)

        Returns:
            Dict with: input_tokens, output_tokens, total_tokens, cost_usd, provider, model

        Example:
            >>> tracker = MultiProviderCostTracker()
            >>> result = tracker.track_call("openai", "gpt-4o", litellm_response)
            >>> print(result)
            {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150,
             'cost_usd': 0.00015, 'provider': 'openai', 'model': 'gpt-4o'}
        """
        # Extract token usage from response
        tokens = self._extract_tokens(response)

        input_tokens = tokens.get("input_tokens", 0)
        output_tokens = tokens.get("output_tokens", 0)
        total_tokens = tokens.get("total_tokens", input_tokens + output_tokens)

        # Calculate cost (zero for Ollama/local models)
        if _is_ollama_model(provider):
            cost_usd = 0.0
        else:
            try:
                cost_usd = self.cost_estimator.estimate_cost(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    provider=provider,
                )
            except Exception as e:
                logger.warning(f"Failed to estimate cost for {provider}/{model}: {e}")
                cost_usd = 0.0

        # Create result dict
        result = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "provider": provider,
            "model": model,
        }

        # Store in history
        entry = ProviderCostEntry(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
        )
        self._call_history.append(entry)

        logger.debug(
            f"Tracked call: {provider}/{model} - "
            f"{total_tokens} tokens, ${cost_usd:.6f}"
        )

        return result

    def _extract_tokens(self, response: Any) -> Dict[str, int]:
        """Extract token usage from various LLM response formats.

        Handles:
        - LiteLLM response format (response.usage)
        - OpenAI response format
        - Anthropic response format
        - Dict-like responses

        Args:
            response: LLM response object

        Returns:
            Dict with input_tokens, output_tokens, total_tokens
        """
        tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        if response is None:
            return tokens

        # Try LiteLLM/OpenAI format (response.usage)
        if hasattr(response, "usage"):
            usage = response.usage
            if hasattr(usage, "prompt_tokens"):
                tokens["input_tokens"] = usage.prompt_tokens or 0
            if hasattr(usage, "completion_tokens"):
                tokens["output_tokens"] = usage.completion_tokens or 0
            if hasattr(usage, "total_tokens"):
                tokens["total_tokens"] = usage.total_tokens or 0

        # Try dict-like response
        elif isinstance(response, dict):
            if "usage" in response:
                usage = response["usage"]
                tokens["input_tokens"] = usage.get("prompt_tokens", 0)
                tokens["output_tokens"] = usage.get("completion_tokens", 0)
                tokens["total_tokens"] = usage.get("total_tokens", 0)

        # Calculate total if not provided
        if tokens["total_tokens"] == 0:
            tokens["total_tokens"] = tokens["input_tokens"] + tokens["output_tokens"]

        return tokens

    def get_cost_summary(self, runs: Optional[List[Any]] = None) -> ProviderCostSummary:
        """Generate aggregated cost summary by provider.

        Aggregates costs from internal call history or optional MLFlow runs.

        Args:
            runs: Optional list of MLFlow runs to include in summary

        Returns:
            ProviderCostSummary with totals and by_provider breakdown

        Example:
            >>> summary = tracker.get_cost_summary()
            >>> print(f"Total cost: ${summary.total_cost_usd:.6f}")
            >>> for provider, data in summary.by_provider.items():
            ...     print(f"{provider}: ${data['total_cost_usd']:.6f} ({data['calls']} calls)")
        """
        # Aggregate from internal history
        provider_data: Dict[str, Dict[str, Any]] = {}
        total_cost = 0.0
        total_tokens = 0
        total_calls = 0

        for entry in self._call_history:
            if entry.provider not in provider_data:
                provider_data[entry.provider] = {
                    "total_cost_usd": 0.0,
                    "total_tokens": 0,
                    "calls": 0,
                    "models": {},
                }

            provider_data[entry.provider]["total_cost_usd"] += entry.cost_usd
            provider_data[entry.provider]["total_tokens"] += entry.total_tokens
            provider_data[entry.provider]["calls"] += 1

            # Track by model within provider
            if entry.model not in provider_data[entry.provider]["models"]:
                provider_data[entry.provider]["models"][entry.model] = {
                    "cost_usd": 0.0,
                    "tokens": 0,
                    "calls": 0,
                }
            provider_data[entry.provider]["models"][entry.model]["cost_usd"] += (
                entry.cost_usd
            )
            provider_data[entry.provider]["models"][entry.model]["tokens"] += (
                entry.total_tokens
            )
            provider_data[entry.provider]["models"][entry.model]["calls"] += 1

            total_cost += entry.cost_usd
            total_tokens += entry.total_tokens
            total_calls += 1

        # Clean up internal structure (remove models from top level)
        by_provider = {}
        for provider, data in provider_data.items():
            by_provider[provider] = {
                "total_cost_usd": data["total_cost_usd"],
                "total_tokens": data["total_tokens"],
                "calls": data["calls"],
                "models": data["models"],
            }

        return ProviderCostSummary(
            total_cost_usd=round(total_cost, 6),
            total_tokens=total_tokens,
            by_provider=by_provider,
            total_calls=total_calls,
        )

    def generate_report(
        self, experiment_name: str, mlflow_client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Generate cost report from MLFlow experiment data.

        Queries MLFlow for all runs in the experiment and aggregates costs by provider.

        Args:
            experiment_name: MLFlow experiment name
            mlflow_client: Optional MLFlow client (uses default if not provided)

        Returns:
            Dict with: experiment, total_cost_usd, total_tokens, by_provider breakdown

        Raises:
            RuntimeError: If MLFlow is not installed
            ValueError: If experiment doesn't exist
        """
        if not MLFLOW_AVAILABLE:
            raise RuntimeError(
                "MLFlow is not installed. Cannot generate report. "
                "Install with: pip install mlflow>=3.9.0"
            )

        client = mlflow_client or MlflowClient()

        # Get experiment
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            raise ValueError(f"Experiment not found: {experiment_name}")

        # Query runs
        runs = client.search_runs(experiment_ids=[experiment.experiment_id])

        # Aggregate costs from runs
        provider_data: Dict[str, Dict[str, Any]] = {}
        total_cost = 0.0
        total_tokens = 0

        for run in runs:
            # Extract provider/model from run params
            params = run.data.params
            metrics = run.data.metrics

            provider = params.get("provider", "unknown")
            model = params.get("model", "unknown")

            # Auto-detect provider if not specified
            if provider == "unknown":
                provider = _extract_provider(model)

            key = f"{provider}/{model}"
            if key not in provider_data:
                provider_data[key] = {
                    "provider": provider,
                    "model": model,
                    "total_cost_usd": 0.0,
                    "total_tokens": 0,
                    "run_count": 0,
                }

            provider_data[key]["total_cost_usd"] += metrics.get("total_cost_usd", 0.0)
            provider_data[key]["total_tokens"] += metrics.get("total_tokens", 0)
            provider_data[key]["run_count"] += 1

            total_cost += metrics.get("total_cost_usd", 0.0)
            total_tokens += metrics.get("total_tokens", 0)

        # Aggregate by provider
        by_provider: Dict[str, Dict[str, Any]] = {}
        for key, data in provider_data.items():
            provider = data["provider"]
            if provider not in by_provider:
                by_provider[provider] = {
                    "total_cost_usd": 0.0,
                    "total_tokens": 0,
                    "run_count": 0,
                    "models": {},
                }

            by_provider[provider]["total_cost_usd"] += data["total_cost_usd"]
            by_provider[provider]["total_tokens"] += data["total_tokens"]
            by_provider[provider]["run_count"] += data["run_count"]

            # Track individual models
            model = data["model"]
            by_provider[provider]["models"][model] = {
                "total_cost_usd": data["total_cost_usd"],
                "total_tokens": data["total_tokens"],
                "run_count": data["run_count"],
            }

        return {
            "experiment": experiment_name,
            "experiment_id": experiment.experiment_id,
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "by_provider": by_provider,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def clear_history(self) -> None:
        """Clear internal call history.

        Useful for starting fresh tracking in a new workflow session.
        """
        self._call_history.clear()

    def get_history(self) -> List[ProviderCostEntry]:
        """Get internal call history.

        Returns:
            List of all tracked calls

        Example:
            >>> history = tracker.get_history()
            >>> for entry in history:
            ...     print(f"{entry.provider}/{entry.model}: ${entry.cost_usd:.6f}")
        """
        return list(self._call_history)


def generate_cost_report(
    experiment_name: str,
    mlflow_uri: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate unified cost report for an MLFlow experiment.

    Standalone function for CLI usage. Creates MLFlow client, queries experiment,
    and generates provider-aware cost summary.

    Args:
        experiment_name: MLFlow experiment name
        mlflow_uri: Optional MLFlow tracking URI (uses default if not specified)

    Returns:
        Dict with: experiment, total_cost_usd, total_tokens, by_provider breakdown

    Raises:
        RuntimeError: If MLFlow is not installed
        ValueError: If experiment doesn't exist

    Example:
        >>> report = generate_cost_report("my_workflows")
        >>> print(f"Total cost: ${report['total_cost_usd']:.2f}")
        >>> for provider, data in report['by_provider'].items():
        ...     print(f"{provider}: ${data['total_cost_usd']:.2f}")
    """
    if not MLFLOW_AVAILABLE:
        raise RuntimeError(
            "MLFlow is not installed. Cannot generate cost report. "
            "Install with: pip install mlflow>=3.9.0"
        )

    # Set tracking URI if provided
    if mlflow_uri:
        mlflow.set_tracking_uri(mlflow_uri)

    # Create client
    client = MlflowClient()

    # Use tracker to generate report
    tracker = MultiProviderCostTracker()
    return tracker.generate_report(experiment_name, mlflow_client=client)
