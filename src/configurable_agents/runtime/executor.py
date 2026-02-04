"""Runtime executor for workflow execution."""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import ValidationError as PydanticValidationError

from configurable_agents.config import (
    WorkflowConfig,
    parse_config_file,
    validate_config,
    ValidationError,
)
from configurable_agents.core import build_graph, build_state_model
from configurable_agents.observability import MLFlowTracker
from configurable_agents.runtime.feature_gate import (
    UnsupportedFeatureError,
    validate_runtime_support,
)
from configurable_agents.runtime.profiler import (
    BottleneckAnalyzer,
    clear_profiler,
    get_profiler,
    set_profiler,
)
from configurable_agents.storage import create_storage_backend
from configurable_agents.storage.models import WorkflowRunRecord

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Base exception for execution errors."""

    def __init__(
        self,
        message: str,
        phase: str = None,
        original_error: Exception = None,
    ):
        super().__init__(message)
        self.phase = phase
        self.original_error = original_error


class ConfigLoadError(ExecutionError):
    """Error loading or parsing config file."""

    pass


class ConfigValidationError(ExecutionError):
    """Error validating config."""

    pass


class StateInitializationError(ExecutionError):
    """Error initializing workflow state."""

    pass


class GraphBuildError(ExecutionError):
    """Error building execution graph."""

    pass


class WorkflowExecutionError(ExecutionError):
    """Error during workflow execution."""

    pass


def run_workflow(
    config_path: str,
    inputs: Dict[str, Any],
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Execute workflow from config file and return final state.

    Args:
        config_path: Path to YAML or JSON config file
        inputs: Initial state inputs as dict
        verbose: Enable verbose logging (DEBUG level)

    Returns:
        Final workflow state as dict

    Raises:
        ConfigLoadError: Failed to load or parse config file
        ConfigValidationError: Config validation failed
        StateInitializationError: Failed to initialize state
        GraphBuildError: Failed to build execution graph
        WorkflowExecutionError: Workflow execution failed

    Example:
        >>> result = run_workflow("article_writer.yaml", {"topic": "AI Safety"})
        >>> print(result["article"])
    """
    # Set log level
    if verbose:
        logging.getLogger("configurable_agents").setLevel(logging.DEBUG)

    logger.info(f"Loading workflow config from: {config_path}")

    # Phase 1: Load and parse config
    try:
        config_dict = parse_config_file(config_path)
    except FileNotFoundError as e:
        raise ConfigLoadError(
            f"Config file not found: {config_path}",
            phase="config_load",
            original_error=e,
        )
    except Exception as e:
        raise ConfigLoadError(
            f"Failed to parse config file: {e}",
            phase="config_parse",
            original_error=e,
        )

    # Phase 2: Parse into Pydantic model
    try:
        config = WorkflowConfig(**config_dict)
    except PydanticValidationError as e:
        raise ConfigValidationError(
            f"Config schema validation failed:\n{e}",
            phase="schema_validation",
            original_error=e,
        )

    # Phase 3: Run workflow from config
    return run_workflow_from_config(config, inputs, verbose=verbose)


def run_workflow_from_config(
    config: WorkflowConfig,
    inputs: Dict[str, Any],
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Execute workflow from pre-loaded config and return final state.

    Args:
        config: Validated WorkflowConfig instance
        inputs: Initial state inputs as dict
        verbose: Enable verbose logging (DEBUG level)

    Returns:
        Final workflow state as dict

    Raises:
        ConfigValidationError: Config validation failed
        StateInitializationError: Failed to initialize state
        GraphBuildError: Failed to build execution graph
        WorkflowExecutionError: Workflow execution failed

    Example:
        >>> config = WorkflowConfig(**config_dict)
        >>> result = run_workflow_from_config(config, {"topic": "AI"})
    """
    # Set log level
    if verbose:
        logging.getLogger("configurable_agents").setLevel(logging.DEBUG)

    workflow_name = config.flow.name
    logger.info(f"Executing workflow: {workflow_name}")

    start_time = time.time()

    # Phase 1: Validate config (comprehensive validation)
    try:
        logger.debug("Validating config...")
        validate_config(config)
        logger.debug("Config validation passed")
    except ValidationError as e:
        raise ConfigValidationError(
            f"Config validation failed: {e}",
            phase="config_validation",
            original_error=e,
        )

    # Phase 2: Check runtime support (feature gating)
    try:
        logger.debug("Checking runtime support...")
        validate_runtime_support(config)
        logger.debug("Runtime support check passed")
    except UnsupportedFeatureError as e:
        raise ConfigValidationError(
            f"Unsupported features detected: {e}",
            phase="feature_gating",
            original_error=e,
        )

    # Phase 2.5: Initialize storage backend (optional, graceful degradation)
    workflow_run_repo = None
    execution_state_repo = None
    memory_repo = None
    storage_config = None
    if config.config and config.config.storage:
        storage_config = config.config.storage
    try:
        workflow_run_repo, execution_state_repo, _, _, _, memory_repo = create_storage_backend(storage_config)
        logger.debug("Storage backend initialized")
    except Exception as e:
        logger.warning(f"Storage backend initialization failed, continuing without persistence: {e}")

    # Phase 3: Build state model
    try:
        logger.debug("Building state model...")
        state_model = build_state_model(config.state)
        logger.debug(f"State model built: {state_model.__name__}")
    except Exception as e:
        raise GraphBuildError(
            f"Failed to build state model: {e}",
            phase="state_model_build",
            original_error=e,
        )

    # Phase 4: Initialize state with inputs
    try:
        logger.debug(f"Initializing state with inputs: {list(inputs.keys())}")
        initial_state = state_model(**inputs)
        logger.debug(f"Initial state created: {initial_state}")
    except PydanticValidationError as e:
        raise StateInitializationError(
            f"Failed to initialize state with provided inputs:\n{e}\n\n"
            f"Provided inputs: {list(inputs.keys())}\n"
            f"Required fields: {[name for name, field in state_model.model_fields.items() if field.is_required()]}",
            phase="state_initialization",
            original_error=e,
        )
    except Exception as e:
        raise StateInitializationError(
            f"Failed to initialize state: {e}",
            phase="state_initialization",
            original_error=e,
        )

    # Phase 4.5: Create workflow run record (if storage available)
    run_id = None
    if workflow_run_repo:
        try:
            run_id = str(uuid.uuid4())
            run_record = WorkflowRunRecord(
                id=run_id,
                workflow_name=workflow_name,
                status="running",
                config_snapshot=json.dumps(config.model_dump(), default=str),
                inputs=json.dumps(inputs, default=str),
                started_at=datetime.now(timezone.utc),
            )
            workflow_run_repo.add(run_record)
            logger.debug(f"Persisted workflow run: {run_id}")
        except Exception as e:
            logger.warning(f"Failed to persist workflow run record: {e}")
            run_id = None  # Disable further storage ops for this run

    # Phase 5: Initialize MLFlow tracker
    mlflow_config = None
    if config.config and config.config.observability:
        mlflow_config = config.config.observability.mlflow

    tracker = MLFlowTracker(mlflow_config, config)

    # Attach storage repos to tracker for node executor access
    if run_id:
        if execution_state_repo:
            tracker.execution_state_repo = execution_state_repo
        if memory_repo:
            tracker.memory_repo = memory_repo
        tracker.run_id = run_id
        tracker.workflow_name = workflow_name
        tracker.workflow_id = run_id
        logger.debug(f"Attached storage repos to tracker for run {run_id}")

    # Phase 6: Build and compile graph (with tracker for node instrumentation)
    try:
        logger.debug("Building execution graph...")
        graph = build_graph(config, state_model, config.config, tracker)
        logger.debug("Graph built and compiled successfully")
    except Exception as e:
        raise GraphBuildError(
            f"Failed to build execution graph: {e}",
            phase="graph_build",
            original_error=e,
        )

    # Phase 6.5: Initialize BottleneckAnalyzer for profiling
    profiler_analyzer = BottleneckAnalyzer()
    set_profiler(profiler_analyzer)
    logger.debug("BottleneckAnalyzer initialized for workflow profiling")

    # Phase 7: Execute graph with MLFlow 3.9 auto-tracing
    try:
        logger.info(f"Starting workflow execution: {workflow_name}")
        logger.debug(f"Initial state: {initial_state}")

        # Define traced execution function (MLflow 3.9 @mlflow.trace)
        @tracker.get_trace_decorator(
            name=f"workflow_{workflow_name}",
            workflow_name=workflow_name,
            workflow_version=config.flow.version or "unversioned",
            node_count=len(config.nodes),
        )
        def _execute_workflow():
            """Execute workflow (automatically traced by MLflow via autolog)."""
            # LangGraph's invoke() returns dict, not BaseModel
            # Auto-traced via mlflow.langchain.autolog() - no manual tracking needed!
            return graph.invoke(initial_state)

        # Execute workflow (tracing happens automatically)
        final_state = _execute_workflow()

        # Post-process: Calculate and log cost summary
        if tracker.enabled:
            cost_summary = tracker.get_workflow_cost_summary()
            if cost_summary:
                tracker.log_workflow_summary(cost_summary)
                logger.info(
                    f"Workflow cost: ${cost_summary.get('total_cost_usd', 0):.6f}, "
                    f"{cost_summary.get('total_tokens', {}).get('total_tokens', 0)} tokens"
                )

        execution_time = time.time() - start_time
        logger.info(
            f"Workflow completed successfully: {workflow_name} "
            f"(duration: {execution_time:.2f}s)"
        )
        logger.debug(f"Final state: {final_state}")

        # Post-process: Log bottleneck analysis
        bottleneck_summary = profiler_analyzer.get_summary()
        if bottleneck_summary["node_count"] > 0:
            logger.info(
                f"Bottleneck analysis: {bottleneck_summary['node_count']} nodes, "
                f"total node time: {bottleneck_summary['total_time_ms']:.2f}ms"
            )

            # Log slowest node
            slowest = bottleneck_summary.get("slowest_node")
            if slowest:
                logger.info(
                    f"Slowest node: {slowest['node_id']} "
                    f"({slowest['avg_duration_ms']:.2f}ms avg, "
                    f"{slowest['call_count']} calls, "
                    f"{slowest['total_duration_ms']:.2f}ms total)"
                )

            # Log bottlenecks (>50% threshold)
            bottlenecks = bottleneck_summary.get("bottlenecks", [])
            if bottlenecks:
                logger.info(f"Bottlenecks (>{50.0}% of total time):")
                for b in bottlenecks:
                    logger.info(
                        f"  - {b['node_id']}: {b['percent_of_total']:.1f}% "
                        f"({b['total_duration_ms']:.2f}ms total, "
                        f"{b['avg_duration_ms']:.2f}ms avg, "
                        f"{b['call_count']} calls)"
                    )

        # Clear profiler from thread-local context
        clear_profiler()

        # Phase 7.5: Check quality gates (v0.4+)
        if config.config and config.config.gates:
            from configurable_agents.optimization.gates import (
                check_gates,
                take_action,
                GateAction,
            )

            # Collect metrics for gate checking
            gate_metrics = {}

            # Get cost summary from tracker
            if tracker.enabled:
                cost_summary = tracker.get_workflow_cost_summary()
                if cost_summary:
                    gate_metrics["cost_usd"] = cost_summary.get("total_cost_usd", 0.0)
                    gate_metrics["total_tokens"] = cost_summary.get("total_tokens", {}).get("total_tokens", 0)

            # Add execution time
            gate_metrics["duration_ms"] = execution_time * 1000

            # Add bottleneck info if available
            if bottleneck_summary["node_count"] > 0:
                gate_metrics["bottleneck_node"] = bottleneck_summary.get("slowest_node", {}).get("node_id", "")
                gate_metrics["bottleneck_percent"] = bottleneck_summary.get("slowest_node", {}).get("percent_of_total", 0)

            # Parse on_fail action
            on_fail_str = config.config.gates.on_fail
            try:
                if on_fail_str == "warn":
                    gate_action = GateAction.WARN
                elif on_fail_str == "fail":
                    gate_action = GateAction.FAIL
                elif on_fail_str == "block_deploy":
                    gate_action = GateAction.BLOCK_DEPLOY
                else:
                    gate_action = GateAction.WARN
            except Exception:
                gate_action = GateAction.WARN

            # Convert schema GatesModel to optimization GatesConfig
            from configurable_agents.optimization.gates import QualityGate, GatesConfig
            quality_gates = [
                QualityGate(
                    metric=gm.metric,
                    max=gm.max,
                    min=gm.min,
                    description=gm.metric,
                )
                for gm in config.config.gates.gates
            ]
            gates_config = GatesConfig(gates=quality_gates, on_fail=gate_action)

            # Check gates
            logger.info("Checking quality gates...")
            gate_results = check_gates(gate_metrics, gates_config)

            # Log results
            for result in gate_results:
                if result.passed:
                    logger.debug(f"Gate passed: {result.gate.metric}")
                else:
                    logger.warning(f"Gate failed: {result.message}")

            # Take action based on results
            try:
                take_action(gate_results, gate_action, context=workflow_name)
            except Exception as gate_error:
                # Gate check failed with FAIL action
                logger.error(f"Quality gate check failed: {gate_error}")
                # Still update run record with failure status
                if workflow_run_repo and run_id:
                    try:
                        workflow_run_repo.update_run_completion(
                            run_id=run_id,
                            status="failed",
                            duration_seconds=execution_time,
                            total_tokens=0,
                            total_cost_usd=0.0,
                            error_message=f"Quality gates failed: {str(gate_error)}"[:500],
                        )
                    except Exception:
                        pass
                raise

        # Update workflow run record with completion metrics (including bottleneck info)
        if workflow_run_repo and run_id:
            try:
                # Get cost summary from tracker if available
                total_tokens = 0
                total_cost = 0.0
                if tracker.enabled:
                    cost_summary = tracker.get_workflow_cost_summary()
                    if cost_summary:
                        total_tokens = cost_summary.get('total_tokens', {}).get('total_tokens', 0)
                        total_cost = cost_summary.get('total_cost_usd', 0.0)

                # Convert final state to JSON for outputs
                outputs_json = json.dumps(final_state, default=str)

                # Serialize bottleneck summary to JSON for storage
                bottleneck_json = json.dumps(bottleneck_summary, default=str) if bottleneck_summary["node_count"] > 0 else None

                workflow_run_repo.update_run_completion(
                    run_id=run_id,
                    status="completed",
                    duration_seconds=execution_time,
                    total_tokens=total_tokens,
                    total_cost_usd=total_cost,
                    outputs=outputs_json,
                    bottleneck_info=bottleneck_json,
                )
                logger.debug(f"Updated workflow run record: {run_id} -> completed")
            except Exception as e:
                logger.warning(f"Failed to update workflow run record on completion: {e}")

        return final_state

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            f"Workflow execution failed: {workflow_name} "
            f"(duration: {execution_time:.2f}s)"
        )

        # Clear profiler from thread-local context (even on failure)
        clear_profiler()

        # Update workflow run record with failure status
        if workflow_run_repo and run_id:
            try:
                workflow_run_repo.update_run_completion(
                    run_id=run_id,
                    status="failed",
                    duration_seconds=execution_time,
                    total_tokens=0,
                    total_cost_usd=0.0,
                    error_message=str(e)[:500],  # Truncate long error messages
                )
                logger.debug(f"Updated workflow run record: {run_id} -> failed")
            except Exception as exc:
                logger.warning(f"Failed to update workflow run record on failure: {exc}")

        raise WorkflowExecutionError(
            f"Workflow execution failed: {e}",
            phase="workflow_execution",
            original_error=e,
        )


def validate_workflow(config_path: str) -> bool:
    """
    Validate workflow config without executing it.

    Args:
        config_path: Path to YAML or JSON config file

    Returns:
        True if validation passes

    Raises:
        ConfigLoadError: Failed to load or parse config file
        ConfigValidationError: Config validation failed

    Example:
        >>> validate_workflow("article_writer.yaml")
        True
    """
    logger.info(f"Validating workflow config: {config_path}")

    # Phase 1: Load and parse config
    try:
        config_dict = parse_config_file(config_path)
    except FileNotFoundError as e:
        raise ConfigLoadError(
            f"Config file not found: {config_path}",
            phase="config_load",
            original_error=e,
        )
    except Exception as e:
        raise ConfigLoadError(
            f"Failed to parse config file: {e}",
            phase="config_parse",
            original_error=e,
        )

    # Phase 2: Parse into Pydantic model
    try:
        config = WorkflowConfig(**config_dict)
    except PydanticValidationError as e:
        raise ConfigValidationError(
            f"Config schema validation failed:\n{e}",
            phase="schema_validation",
            original_error=e,
        )

    # Phase 3: Validate config
    try:
        validate_config(config)
        logger.info("Config validation passed")
    except ValidationError as e:
        raise ConfigValidationError(
            f"Config validation failed: {e}",
            phase="config_validation",
            original_error=e,
        )

    # Phase 4: Check runtime support
    try:
        validate_runtime_support(config)
        logger.info("Runtime support check passed")
    except UnsupportedFeatureError as e:
        raise ConfigValidationError(
            f"Unsupported features detected: {e}",
            phase="feature_gating",
            original_error=e,
        )

    logger.info("Validation complete: config is valid")
    return True


async def run_workflow_async(
    config_path: str,
    inputs: Dict[str, Any],
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Execute workflow from config file asynchronously.

    Wraps the synchronous run_workflow() function in an async wrapper
    using asyncio.to_thread(), enabling background task execution from
    FastAPI endpoints without blocking the event loop.

    Args:
        config_path: Path to YAML or JSON config file
        inputs: Initial state inputs as dict
        verbose: Enable verbose logging (DEBUG level)

    Returns:
        Final workflow state as dict

    Raises:
        ConfigLoadError: Failed to load or parse config file
        ConfigValidationError: Config validation failed
        StateInitializationError: Failed to initialize state
        GraphBuildError: Failed to build execution graph
        WorkflowExecutionError: Workflow execution failed

    Example:
        >>> result = await run_workflow_async("article_writer.yaml", {"topic": "AI Safety"})
        >>> print(result["article"])
    """
    # Run the synchronous workflow function in a thread pool
    # This prevents blocking the async event loop during workflow execution
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,  # Use default thread pool executor
        lambda: run_workflow(config_path, inputs, verbose=verbose),
    )
