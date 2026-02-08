"""MLFlow 3.9 integration for workflow observability.

Leverages MLflow 3.9 GenAI features for automatic tracing:
- Auto-instrumentation via mlflow.langchain.autolog()
- Automatic token usage tracking
- Span/trace model (not nested runs)
- Enhanced GenAI dashboard

Key differences from previous implementation:
- No manual run management (automatic via @mlflow.trace)
- No context managers (track_workflow, track_node removed)
- No manual token counting (automatic via mlflow.chat.tokenUsage)
- Simplified to ~200 lines (from 484 lines, 60% reduction)

Responsibilities:
1. Initialize MLflow (set URI, experiment, enable autolog)
2. Configure observability settings (artifact levels, overrides)
3. Provide trace decorator helper
4. Post-process traces for cost calculation
5. Graceful degradation (enabled flag, server check)
"""

import json
import logging
import os
import socket
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from configurable_agents.config import ObservabilityMLFlowConfig, WorkflowConfig
from configurable_agents.observability.cost_estimator import CostEstimator
from configurable_agents.observability.multi_provider_tracker import (
    MultiProviderCostTracker,
    _extract_provider,
)

logger = logging.getLogger(__name__)

# Optional MLFlow import - fail gracefully if not installed
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MLFLOW_AVAILABLE = False
    logger.warning(
        "MLFlow not installed. Observability features disabled. "
        "Install with: pip install mlflow>=3.9.0"
    )


class MLFlowTracker:
    """
    MLflow 3.9 integration for workflow observability.

    Uses MLflow 3.9 GenAI features for automatic tracing via mlflow.langchain.autolog().
    Provides configuration management and post-processing helpers.

    Example:
        >>> config = ObservabilityMLFlowConfig(enabled=True)
        >>> tracker = MLFlowTracker(config, workflow_config)
        >>>
        >>> # Get trace decorator for workflow
        >>> @tracker.get_trace_decorator("workflow", workflow_name="article_writer")
        ... def execute_workflow():
        ...     # Workflow automatically traced
        ...     result = graph.invoke(state)
        ...     return result
        >>>
        >>> # Get cost summary after execution
        >>> cost_summary = tracker.get_workflow_cost_summary()
        >>> print(f"Total cost: ${cost_summary['total_cost_usd']:.6f}")
    """

    def __init__(
        self,
        mlflow_config: Optional[ObservabilityMLFlowConfig],
        workflow_config: WorkflowConfig,
    ):
        """
        Initialize MLFlow 3.9 tracker.

        Args:
            mlflow_config: MLFlow configuration (None = disabled)
            workflow_config: Workflow configuration for context
        """
        self.enabled = (
            mlflow_config is not None
            and mlflow_config.enabled
            and MLFLOW_AVAILABLE
        )
        self.mlflow_config = mlflow_config
        self.workflow_config = workflow_config
        self.cost_estimator = CostEstimator()
        self.cost_tracker = MultiProviderCostTracker(mlflow_tracker=self)

        if self.enabled:
            self._initialize_mlflow_39()

    def _check_tracking_server_accessible(self, timeout: float = 3.0) -> bool:
        """
        Check if MLFlow tracking server is accessible (for HTTP/HTTPS URIs).

        Args:
            timeout: Connection timeout in seconds (default: 3.0)

        Returns:
            True if server is accessible or URI is file-based, False otherwise
        """
        tracking_uri = self.mlflow_config.tracking_uri

        # File-based or SQLite URIs don't need server check
        if tracking_uri.startswith(("file://", "sqlite://")) or not tracking_uri.startswith(
            ("http://", "https://")
        ):
            return True

        try:
            # Parse URL to get host and port
            parsed = urlparse(tracking_uri)
            host = parsed.hostname or "localhost"
            port = parsed.port or (443 if parsed.scheme == "https" else 80)

            # Try to connect with timeout
            with socket.create_connection((host, port), timeout=timeout):
                return True

        except (socket.timeout, socket.error, OSError) as e:
            logger.warning(
                f"MLFlow tracking server not accessible at {tracking_uri}: {e}"
            )
            return False
        except Exception as e:
            logger.warning(f"Failed to check MLFlow server accessibility: {e}")
            return False

    def _initialize_mlflow_39(self) -> None:
        """Initialize MLflow 3.9 with auto-instrumentation."""
        if not self.enabled:
            return

        try:
            # Check if tracking server is accessible (for HTTP URIs)
            if not self._check_tracking_server_accessible(timeout=3.0):
                logger.warning(
                    f"MLFlow tracking server not accessible at {self.mlflow_config.tracking_uri}. "
                    "Disabling MLFlow tracking. "
                    "If using http:// URI, ensure MLFlow server is running. "
                    "For local tracking, use: tracking_uri='sqlite:///mlflow.db'"
                )
                self.enabled = False
                return

            # Set tracking URI
            mlflow.set_tracking_uri(self.mlflow_config.tracking_uri)
            logger.debug(f"MLFlow tracking URI: {self.mlflow_config.tracking_uri}")

            # Log deprecation warning for file:// URIs
            if self.mlflow_config.tracking_uri.startswith("file://"):
                logger.warning(
                    "File backend (file://./mlruns) is deprecated in MLflow 3.9. "
                    "Consider migrating to SQLite: sqlite:///mlflow.db "
                    "for better performance. Existing data will continue to work."
                )

            # Configure environment variables
            os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "10")

            # Enable async trace logging (production optimization)
            if self.mlflow_config.async_logging if hasattr(self.mlflow_config, 'async_logging') else True:
                os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = "true"
                os.environ["MLFLOW_ASYNC_TRACE_LOGGING_MAX_WORKERS"] = "20"
                os.environ["MLFLOW_ASYNC_TRACE_LOGGING_MAX_QUEUE_SIZE"] = "2000"
                os.environ["MLFLOW_ASYNC_TRACE_LOGGING_RETRY_TIMEOUT"] = "600"

            # Set or create experiment
            experiment = mlflow.set_experiment(self.mlflow_config.experiment_name)
            logger.debug(
                f"MLFlow experiment: {self.mlflow_config.experiment_name} "
                f"(ID: {experiment.experiment_id})"
            )

            # Enable auto-instrumentation for LangChain/LangGraph
            mlflow.langchain.autolog(
                disable=False,
                silent=False,
                log_traces=True,  # Enable trace logging
                run_tracer_inline=True,  # Proper context propagation for LangGraph async
            )

            logger.info("MLflow 3.9 auto-instrumentation enabled (langchain.autolog)")

        except Exception as e:
            logger.error(f"Failed to initialize MLflow 3.9: {e}")
            logger.warning("Disabling MLFlow tracking for this run")
            self.enabled = False

    def _should_log_artifacts(self, artifact_type: str = "standard") -> bool:
        """
        Check if artifacts should be logged based on artifact_level.

        Args:
            artifact_type: Type of artifact - "minimal", "standard", or "full"

        Returns:
            True if this artifact type should be logged
        """
        if not self.enabled or not self.mlflow_config.log_artifacts:
            return False

        level = self.mlflow_config.artifact_level

        if level == "minimal":
            return artifact_type == "minimal"
        elif level == "standard":
            return artifact_type in ["minimal", "standard"]
        elif level == "full":
            return True  # Log everything

        return False

    def get_trace_decorator(self, name: str, **attributes):
        """
        Get @mlflow.trace decorator configured for this tracker.

        Returns a decorator that traces the wrapped function as an MLflow span.
        If tracking is disabled, returns a no-op decorator.

        Args:
            name: Span name (e.g., "workflow_article_writer")
            **attributes: Additional span attributes to log

        Returns:
            Decorator function

        Example:
            >>> @tracker.get_trace_decorator("workflow", workflow_name="article_writer")
            ... def execute_workflow():
            ...     return graph.invoke(state)
        """
        if not self.enabled:
            # Return no-op decorator if disabled
            def noop_decorator(func):
                return func
            return noop_decorator

        # Determine span type
        span_type = "WORKFLOW" if "workflow" in name.lower() else "AGENT"

        return mlflow.trace(
            name=name,
            span_type=span_type,
            attributes=attributes,
        )

    def track_provider_call(
        self, provider: str, model: str, response: Any
    ) -> Dict[str, Any]:
        """Track an LLM call with provider-aware cost tracking.

        Delegates to MultiProviderCostTracker for token extraction and cost calculation.
        Logs provider/model metrics to MLFlow when active run exists.

        Args:
            provider: Provider name (e.g., "openai", "anthropic", "google", "ollama")
            model: Model name (e.g., "gpt-4o", "claude-3-opus", "gemini-pro")
            response: LLM response object (LiteLLM response or provider response)

        Returns:
            Dict with: input_tokens, output_tokens, total_tokens, cost_usd, provider, model

        Example:
            >>> result = tracker.track_provider_call(
            ...     provider="openai",
            ...     model="gpt-4o",
            ...     response=llm_response
            ... )
            >>> print(f"Cost: ${result['cost_usd']:.6f}")
        """
        # Delegate to cost tracker
        result = self.cost_tracker.track_call(provider, model, response)

        # Log to MLFlow if active run exists
        if self.enabled and mlflow.active_run():
            try:
                # Log provider/model-specific metrics
                mlflow.log_metrics({
                    f"provider_{provider}_cost_usd": result["cost_usd"],
                    f"provider_{provider}_tokens": result["total_tokens"],
                    f"provider_{provider}_input_tokens": result["input_tokens"],
                    f"provider_{provider}_output_tokens": result["output_tokens"],
                })

                # Log params for provider/model context
                mlflow.log_params({
                    f"last_call_provider": provider,
                    f"last_call_model": model,
                })

            except Exception as e:
                logger.warning(f"Failed to log provider call to MLFlow: {e}")

        return result

    def get_workflow_cost_summary(self, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate cost summary from trace token usage.

        Extracts token usage from MLflow trace metadata and calculates costs
        using the CostEstimator. Provides total, per-node, and by_provider breakdown.

        Args:
            trace_id: Trace ID (default: get latest from current experiment)

        Returns:
            Cost summary dictionary with:
            - total_tokens: Total tokens used
            - total_cost_usd: Total estimated cost
            - node_breakdown: Per-node cost details
            - by_provider: Per-provider cost breakdown (provider -> {cost, tokens, calls})
            - trace_id: Trace identifier

        Example:
            >>> cost = tracker.get_workflow_cost_summary()
            >>> print(f"Cost: ${cost['total_cost_usd']:.6f}")
            >>> for provider, data in cost['by_provider'].items():
            ...     print(f"{provider}: ${data['total_cost_usd']:.6f}")
        """
        if not self.enabled:
            return {}

        try:
            # Get trace (from ID or latest run)
            if trace_id:
                trace = mlflow.get_trace(trace_id)
            else:
                # Get latest trace from current experiment
                experiment = mlflow.get_experiment_by_name(
                    self.mlflow_config.experiment_name
                )
                if not experiment:
                    return {}

                traces = mlflow.search_traces(
                    locations=[experiment.experiment_id],
                    max_results=1,
                    order_by=["timestamp DESC"],
                    return_type="list",
                )
                trace = traces[0] if len(traces) > 0 else None

            if not trace:
                return {}

            # Extract token usage from trace metadata
            trace_info = trace.info
            total_tokens = getattr(trace_info, 'token_usage', None) or {}

            # Calculate costs per node (iterate spans)
            node_costs = {}
            total_cost = 0.0

            # Provider aggregation for by_provider breakdown
            provider_costs: Dict[str, Dict[str, Any]] = {}

            for span in trace.data.spans:
                # Get token usage from span attributes
                span_attrs = span.attributes or {}
                token_usage = span_attrs.get("mlflow.chat.tokenUsage")

                if token_usage:
                    model = (
                        span_attrs.get("ai.model.name")
                        or (span_attrs.get("invocation_params") or {}).get("model")
                        or (span_attrs.get("metadata") or {}).get("ls_model_name")
                        or "unknown"
                    )
                    prompt_tokens = token_usage.get("prompt_tokens") or token_usage.get("input_tokens", 0)
                    completion_tokens = token_usage.get("completion_tokens") or token_usage.get("output_tokens", 0)

                    # Extract provider from model name
                    provider = _extract_provider(model)

                    try:
                        cost = self.cost_estimator.estimate_cost(
                            model=model,
                            input_tokens=prompt_tokens,
                            output_tokens=completion_tokens,
                        )
                    except ValueError:
                        cost = 0.0

                    node_costs[span.name] = {
                        "tokens": token_usage,
                        "cost_usd": cost,
                        "model": model,
                        "provider": provider,
                        "duration_ms": (span.end_time_ns - span.start_time_ns) / 1_000_000
                        if span.end_time_ns and span.start_time_ns
                        else 0,
                    }
                    total_cost += cost

                    # Aggregate by provider
                    if provider not in provider_costs:
                        provider_costs[provider] = {
                            "total_cost_usd": 0.0,
                            "total_tokens": 0,
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "calls": 0,
                        }
                    provider_costs[provider]["total_cost_usd"] += cost
                    provider_costs[provider]["total_tokens"] += token_usage.get("total_tokens", 0)
                    provider_costs[provider]["input_tokens"] += prompt_tokens
                    provider_costs[provider]["output_tokens"] += completion_tokens
                    provider_costs[provider]["calls"] += 1

            # Get total tokens from trace or sum from nodes
            if not total_tokens:
                total_tokens = {
                    "prompt_tokens": sum(
                        n["tokens"].get("prompt_tokens") or n["tokens"].get("input_tokens", 0)
                        for n in node_costs.values()
                    ),
                    "completion_tokens": sum(
                        n["tokens"].get("completion_tokens") or n["tokens"].get("output_tokens", 0)
                        for n in node_costs.values()
                    ),
                    "total_tokens": sum(n["tokens"].get("total_tokens", 0) for n in node_costs.values()),
                }

            # Build by_provider breakdown
            by_provider = {}
            for provider, data in provider_costs.items():
                by_provider[provider] = {
                    "total_cost_usd": round(data["total_cost_usd"], 6),
                    "total_tokens": data["total_tokens"],
                    "input_tokens": data["input_tokens"],
                    "output_tokens": data["output_tokens"],
                    "calls": data["calls"],
                }

            return {
                "total_tokens": total_tokens,
                "total_cost_usd": total_cost,
                "node_breakdown": node_costs,
                "by_provider": by_provider,
                "trace_id": trace.info.trace_id,
                "workflow_name": self.workflow_config.flow.name,
                "workflow_version": self.workflow_config.flow.version or "unversioned",
            }

        except Exception as e:
            logger.warning(f"Failed to get cost summary: {e}")
            return {}

    def log_workflow_summary(self, cost_summary: Dict[str, Any]) -> None:
        """
        Log workflow summary as trace-level feedback in MLflow.

        Uses mlflow.log_feedback() to attach cost and token assessments
        directly to the trace, making them visible in the GenAI experiment
        view (Traces tab columns and Overview > Quality charts).

        Args:
            cost_summary: Cost summary from get_workflow_cost_summary()

        Example:
            >>> cost_summary = tracker.get_workflow_cost_summary()
            >>> tracker.log_workflow_summary(cost_summary)
        """
        if not self.enabled:
            return

        trace_id = cost_summary.get("trace_id")
        if not trace_id:
            logger.warning("No trace_id in cost summary, cannot log feedback")
            return

        try:
            from mlflow.entities import AssessmentSource, AssessmentSourceType

            source = AssessmentSource(
                source_type=AssessmentSourceType.CODE,
                source_id="cost_estimator",
            )

            total_tokens = cost_summary.get("total_tokens", {})
            total_cost = cost_summary.get("total_cost_usd", 0)
            by_provider = cost_summary.get("by_provider", {})

            # Log total cost as numeric feedback (shows as column + chart)
            mlflow.log_feedback(
                trace_id=trace_id,
                name="cost_usd",
                value=round(total_cost, 6),
                source=source,
                rationale=(
                    f"{total_tokens.get('total_tokens', 0)} tokens "
                    f"across {len(by_provider)} provider(s)"
                ),
            )

            # Log total tokens as numeric feedback (shows as column + chart)
            mlflow.log_feedback(
                trace_id=trace_id,
                name="total_tokens",
                value=total_tokens.get("total_tokens", 0),
                source=source,
            )

            # Log detailed breakdown as structured feedback (visible in trace detail)
            breakdown = {
                "input_tokens": total_tokens.get("prompt_tokens") or total_tokens.get("input_tokens", 0),
                "output_tokens": total_tokens.get("completion_tokens") or total_tokens.get("output_tokens", 0),
            }
            for provider, data in by_provider.items():
                breakdown[f"{provider}_cost_usd"] = data.get("total_cost_usd", 0)
                breakdown[f"{provider}_tokens"] = data.get("total_tokens", 0)
                breakdown[f"{provider}_calls"] = data.get("calls", 0)

            mlflow.log_feedback(
                trace_id=trace_id,
                name="cost_breakdown",
                value=breakdown,
                source=source,
                rationale=f"Per-provider breakdown for {cost_summary.get('workflow_name', 'unknown')}",
            )

            logger.info(
                f"Workflow summary logged: "
                f"{total_tokens.get('total_tokens', 0)} tokens, "
                f"${total_cost:.6f}, "
                f"{len(by_provider)} providers"
            )

        except Exception as e:
            logger.warning(f"Failed to log workflow summary: {e}")
