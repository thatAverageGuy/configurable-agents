"""MLFlow integration for workflow tracking and observability.

Provides MLFlow-based tracking of workflow executions, including:
- Workflow-level metrics (duration, tokens, cost, status)
- Node-level nested runs (per-node execution details)
- Artifacts (inputs, outputs, prompts, responses)
- Graceful degradation when MLFlow is disabled
"""

import json
import logging
import os
import time
import urllib.request
import socket
from contextlib import contextmanager
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
    mlflow = None  # Set to None so it exists at module level for mocking
    MLFLOW_AVAILABLE = False
    logger.warning(
        "MLFlow not installed. Observability features disabled. "
        "Install with: pip install mlflow"
    )


class MLFlowTracker:
    """MLFlow tracker for workflow execution observability.

    Handles MLFlow initialization, run management, and metric/artifact logging.
    Supports graceful degradation when MLFlow is disabled or unavailable.

    Example:
        >>> config = ObservabilityMLFlowConfig(enabled=True)
        >>> tracker = MLFlowTracker(config, workflow_config)
        >>> with tracker.track_workflow(inputs={"topic": "AI"}):
        ...     # Execute workflow
        ...     with tracker.track_node("write_node", model="gemini-1.5-flash"):
        ...         # Execute node
        ...         tracker.log_node_metrics(input_tokens=150, output_tokens=500)
    """

    def __init__(
        self,
        mlflow_config: Optional[ObservabilityMLFlowConfig],
        workflow_config: WorkflowConfig,
    ):
        """Initialize MLFlow tracker.

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

        # Tracking state
        self._workflow_start_time: Optional[float] = None
        self._node_start_time: Optional[float] = None
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_cost = 0.0
        self._node_count = 0
        self._retry_count = 0
        self._current_node_config: Optional[Any] = None  # For node-level overrides

        if self.enabled:
            self._initialize_mlflow()

    def _should_log_artifacts(self, artifact_type: str = "standard") -> bool:
        """Check if artifacts should be logged based on artifact_level.

        Args:
            artifact_type: Type of artifact - "minimal", "standard", or "full"

        Returns:
            True if this artifact type should be logged
        """
        if not self.enabled or not self.mlflow_config.log_artifacts:
            return False

        # Check node-level override
        if self._current_node_config and hasattr(self._current_node_config, 'log_artifacts'):
            if self._current_node_config.log_artifacts is not None:
                return self._current_node_config.log_artifacts

        level = self.mlflow_config.artifact_level

        if level == "minimal":
            return artifact_type == "minimal"
        elif level == "standard":
            return artifact_type in ["minimal", "standard"]
        elif level == "full":
            return True  # Log everything

        return False

    def _should_log_prompts(self) -> bool:
        """Check if prompts should be logged in UI.

        Returns:
            True if prompts should be shown in MLFlow UI
        """
        if not self.enabled:
            return False

        # Check node-level override
        if self._current_node_config and hasattr(self._current_node_config, 'log_prompts'):
            if self._current_node_config.log_prompts is not None:
                return self._current_node_config.log_prompts

        # Use workflow-level default
        return self.mlflow_config.log_prompts

    def _check_tracking_server_accessible(self, timeout: float = 3.0) -> bool:
        """
        Check if MLFlow tracking server is accessible (for HTTP/HTTPS URIs).

        Args:
            timeout: Connection timeout in seconds (default: 3.0)

        Returns:
            True if server is accessible or URI is file-based, False otherwise
        """
        tracking_uri = self.mlflow_config.tracking_uri

        # File-based URIs don't need server check
        if tracking_uri.startswith("file://") or not tracking_uri.startswith(("http://", "https://")):
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

    def _initialize_mlflow(self) -> None:
        """Initialize MLFlow tracking URI and experiment."""
        if not self.enabled:
            return

        try:
            # Check if tracking server is accessible (for HTTP URIs)
            if not self._check_tracking_server_accessible(timeout=3.0):
                logger.warning(
                    f"MLFlow tracking server not accessible at {self.mlflow_config.tracking_uri}. "
                    "Disabling MLFlow tracking. "
                    "If using http:// URI, ensure MLFlow server is running. "
                    "For local tracking, use: tracking_uri='file://./mlruns'"
                )
                self.enabled = False
                return

            # Set tracking URI
            mlflow.set_tracking_uri(self.mlflow_config.tracking_uri)
            logger.debug(f"MLFlow tracking URI: {self.mlflow_config.tracking_uri}")

            # Configure environment variables for faster timeouts
            # MLFlow uses requests library which respects these
            os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "10")

            # Set or create experiment
            experiment = mlflow.set_experiment(self.mlflow_config.experiment_name)
            logger.debug(
                f"MLFlow experiment: {self.mlflow_config.experiment_name} "
                f"(ID: {experiment.experiment_id})"
            )

        except Exception as e:
            logger.error(f"Failed to initialize MLFlow: {e}")
            logger.warning("Disabling MLFlow tracking for this run")
            self.enabled = False

    @contextmanager
    def track_workflow(self, inputs: Dict[str, Any]):
        """Context manager for tracking workflow execution.

        Starts an MLFlow run, logs workflow parameters and inputs,
        yields control for execution, then logs final metrics and outputs.

        Args:
            inputs: Workflow inputs (will be logged as artifact)

        Yields:
            None

        Example:
            >>> with tracker.track_workflow(inputs={"topic": "AI"}):
            ...     result = execute_workflow()
            ...     tracker.finalize_workflow(result, status="success")
        """
        if not self.enabled:
            yield
            return

        self._workflow_start_time = time.time()

        try:
            # Determine run name
            run_name = self.mlflow_config.run_name
            if run_name is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                run_name = f"{self.workflow_config.flow.name}_{timestamp}"

            # Start MLFlow run
            mlflow.start_run(run_name=run_name)
            logger.info(f"Started MLFlow run: {run_name}")

            # Log workflow parameters
            self._log_workflow_params()

            # Log inputs as artifact (minimal level and above)
            if self._should_log_artifacts("minimal"):
                self._log_dict_artifact(inputs, "inputs.json")

            yield

        except Exception as e:
            # Log error and re-raise
            logger.error(f"Workflow execution failed: {e}")
            self._log_workflow_error(e)
            raise

        finally:
            # End MLFlow run
            if mlflow.active_run():
                mlflow.end_run()
                logger.debug("Ended MLFlow run")

    def _log_workflow_params(self) -> None:
        """Log workflow-level parameters to MLFlow."""
        if not self.enabled or not mlflow.active_run():
            return

        try:
            # Workflow metadata
            mlflow.log_param("workflow_name", self.workflow_config.flow.name)
            if self.workflow_config.flow.version:
                mlflow.log_param("workflow_version", self.workflow_config.flow.version)
            mlflow.log_param("schema_version", self.workflow_config.schema_version)

            # Global LLM config
            if self.workflow_config.config and self.workflow_config.config.llm:
                llm_config = self.workflow_config.config.llm
                if llm_config.provider:
                    mlflow.log_param("global_provider", llm_config.provider)
                if llm_config.model:
                    mlflow.log_param("global_model", llm_config.model)
                if llm_config.temperature is not None:
                    mlflow.log_param("global_temperature", llm_config.temperature)

            # Node count
            mlflow.log_param("node_count", len(self.workflow_config.nodes))

        except Exception as e:
            logger.warning(f"Failed to log workflow params: {e}")

    def finalize_workflow(
        self, final_state: Dict[str, Any], status: str = "success"
    ) -> None:
        """Log final workflow metrics and outputs.

        Args:
            final_state: Final workflow state (outputs)
            status: Workflow status ("success" or "failure")
        """
        if not self.enabled or not mlflow.active_run():
            return

        try:
            # Calculate duration
            duration = time.time() - self._workflow_start_time

            # Log metrics
            mlflow.log_metric("duration_seconds", round(duration, 2))
            mlflow.log_metric("total_input_tokens", self._total_input_tokens)
            mlflow.log_metric("total_output_tokens", self._total_output_tokens)
            mlflow.log_metric("total_cost_usd", self._total_cost)
            mlflow.log_metric("node_count", self._node_count)
            mlflow.log_metric("retry_count", self._retry_count)
            mlflow.log_metric("status", 1 if status == "success" else 0)

            # Log outputs as artifact (minimal level and above)
            if self._should_log_artifacts("minimal"):
                self._log_dict_artifact(final_state, "outputs.json")

            logger.info(
                f"Workflow tracking complete: {duration:.2f}s, "
                f"{self._total_input_tokens + self._total_output_tokens} tokens, "
                f"${self._total_cost:.6f}"
            )

        except Exception as e:
            logger.warning(f"Failed to finalize workflow tracking: {e}")

    @contextmanager
    def track_node(self, node_id: str, model: str, tools: Optional[list] = None, node_config: Optional[Any] = None):
        """Context manager for tracking node execution.

        Creates a nested MLFlow run for node-level tracking.

        Args:
            node_id: Node identifier
            model: Model name being used
            tools: List of tools (optional)
            node_config: Node configuration for observability overrides (optional)

        Yields:
            None

        Example:
            >>> with tracker.track_node("write_node", "gemini-1.5-flash", node_config=node_cfg):
            ...     result = execute_node()
            ...     tracker.log_node_metrics(input_tokens=150, output_tokens=500)
        """
        if not self.enabled or not mlflow.active_run():
            yield
            return

        self._node_start_time = time.time()
        self._node_count += 1
        self._current_node_config = node_config  # Store for override checks

        try:
            # Start nested run
            with mlflow.start_run(run_name=f"node_{node_id}", nested=True):
                # Log node parameters
                mlflow.log_param("node_id", node_id)
                mlflow.log_param("node_model", model)
                if tools:
                    mlflow.log_param("tools", json.dumps(tools))

                yield

        except Exception as e:
            logger.warning(f"Error tracking node {node_id}: {e}")

        finally:
            self._current_node_config = None  # Clear after node execution

    def log_node_metrics(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
        retries: int = 0,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
    ) -> None:
        """Log node-level metrics and artifacts.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name
            retries: Number of retries (default: 0)
            prompt: Prompt text (optional)
            response: Response text (optional)
        """
        if not self.enabled or not mlflow.active_run():
            return

        try:
            # Calculate node duration
            node_duration_ms = (time.time() - self._node_start_time) * 1000

            # Estimate cost
            cost = self.cost_estimator.estimate_cost(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            # Log metrics
            mlflow.log_metric("node_duration_ms", round(node_duration_ms, 2))
            mlflow.log_metric("input_tokens", input_tokens)
            mlflow.log_metric("output_tokens", output_tokens)
            mlflow.log_metric("node_cost_usd", cost)
            mlflow.log_metric("retries", retries)

            # Update workflow totals
            self._total_input_tokens += input_tokens
            self._total_output_tokens += output_tokens
            self._total_cost += cost
            self._retry_count += retries

            # Log prompts in UI (as tags, visible but not downloadable)
            if self._should_log_prompts():
                if prompt:
                    # Truncate if too long for UI display
                    prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
                    mlflow.set_tag("prompt", prompt_preview)
                if response:
                    response_preview = response[:500] + "..." if len(response) > 500 else response
                    mlflow.set_tag("response", response_preview)

            # Log as downloadable artifacts (standard level and above)
            if self._should_log_artifacts("standard"):
                if prompt:
                    self._log_text_artifact(prompt, "prompt.txt")
                if response:
                    self._log_text_artifact(response, "response.txt")

        except Exception as e:
            logger.warning(f"Failed to log node metrics: {e}")

    def _log_workflow_error(self, error: Exception) -> None:
        """Log workflow error details.

        Args:
            error: Exception that occurred
        """
        if not self.enabled or not mlflow.active_run():
            return

        try:
            # Log error status
            mlflow.log_metric("status", 0)  # 0 = failure

            # Log error details as artifact (minimal level and above)
            if self._should_log_artifacts("minimal"):
                error_details = {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
                self._log_dict_artifact(error_details, "error.json")

        except Exception as e:
            logger.warning(f"Failed to log workflow error: {e}")

    def _log_dict_artifact(self, data: Dict[str, Any], filename: str) -> None:
        """Log dictionary as JSON artifact.

        Args:
            data: Dictionary to log
            filename: Artifact filename
        """
        try:
            mlflow.log_dict(data, filename)
        except Exception as e:
            logger.warning(f"Failed to log artifact {filename}: {e}")

    def _log_text_artifact(self, text: str, filename: str) -> None:
        """Log text as artifact.

        Args:
            text: Text content
            filename: Artifact filename
        """
        try:
            mlflow.log_text(text, filename)
        except Exception as e:
            logger.warning(f"Failed to log artifact {filename}: {e}")
