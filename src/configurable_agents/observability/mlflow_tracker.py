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

    def get_workflow_cost_summary(self, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate cost summary from trace token usage.

        Extracts token usage from MLflow trace metadata and calculates costs
        using the CostEstimator. Provides both total and per-node breakdown.

        Args:
            trace_id: Trace ID (default: get latest from current experiment)

        Returns:
            Cost summary dictionary with:
            - total_tokens: Total tokens used
            - total_cost_usd: Total estimated cost
            - node_breakdown: Per-node cost details
            - trace_id: Trace identifier

        Example:
            >>> cost = tracker.get_workflow_cost_summary()
            >>> print(f"Cost: ${cost['total_cost_usd']:.6f}")
            >>> for node_id, details in cost['node_breakdown'].items():
            ...     print(f"{node_id}: ${details['cost_usd']:.6f}")
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
                    locations=[f"mlflow-experiment:{experiment.experiment_id}"],
                    max_results=1,
                    order_by=["timestamp DESC"],
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

            for span in trace.data.spans:
                # Get token usage from span attributes
                span_attrs = span.attributes or {}
                token_usage = span_attrs.get("mlflow.chat.tokenUsage")

                if token_usage:
                    model = span_attrs.get("ai.model.name", "unknown")
                    prompt_tokens = token_usage.get("prompt_tokens", 0)
                    completion_tokens = token_usage.get("completion_tokens", 0)

                    cost = self.cost_estimator.estimate_cost(
                        model=model,
                        input_tokens=prompt_tokens,
                        output_tokens=completion_tokens,
                    )

                    node_costs[span.name] = {
                        "tokens": token_usage,
                        "cost_usd": cost,
                        "model": model,
                        "duration_ms": (span.end_time_ns - span.start_time_ns) / 1_000_000
                        if span.end_time_ns and span.start_time_ns
                        else 0,
                    }
                    total_cost += cost

            # Get total tokens from trace or sum from nodes
            if not total_tokens:
                total_tokens = {
                    "prompt_tokens": sum(n["tokens"].get("prompt_tokens", 0) for n in node_costs.values()),
                    "completion_tokens": sum(n["tokens"].get("completion_tokens", 0) for n in node_costs.values()),
                    "total_tokens": sum(n["tokens"].get("total_tokens", 0) for n in node_costs.values()),
                }

            return {
                "total_tokens": total_tokens,
                "total_cost_usd": total_cost,
                "node_breakdown": node_costs,
                "trace_id": trace.info.trace_id,
                "workflow_name": self.workflow_config.flow.name,
                "workflow_version": self.workflow_config.flow.version or "unversioned",
            }

        except Exception as e:
            logger.warning(f"Failed to get cost summary: {e}")
            return {}

    def log_workflow_summary(self, cost_summary: Dict[str, Any]) -> None:
        """
        Log workflow summary metrics to MLflow.

        Logs cost and token metrics to the active MLflow run for easy querying
        and dashboard visualization.

        Args:
            cost_summary: Cost summary from get_workflow_cost_summary()

        Example:
            >>> cost_summary = tracker.get_workflow_cost_summary()
            >>> tracker.log_workflow_summary(cost_summary)
        """
        if not self.enabled or not mlflow.active_run():
            return

        try:
            total_tokens = cost_summary.get("total_tokens", {})

            # Log metrics
            mlflow.log_metrics({
                "total_cost_usd": cost_summary.get("total_cost_usd", 0),
                "total_tokens": total_tokens.get("total_tokens", 0),
                "prompt_tokens": total_tokens.get("prompt_tokens", 0),
                "completion_tokens": total_tokens.get("completion_tokens", 0),
                "node_count": len(cost_summary.get("node_breakdown", {})),
            })

            # Log cost summary as artifact (minimal level and above)
            if self._should_log_artifacts("minimal"):
                mlflow.log_dict(cost_summary, "cost_summary.json")

            logger.info(
                f"Workflow summary logged: "
                f"{total_tokens.get('total_tokens', 0)} tokens, "
                f"${cost_summary.get('total_cost_usd', 0):.6f}"
            )

        except Exception as e:
            logger.warning(f"Failed to log workflow summary: {e}")
