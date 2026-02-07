"""
Node executor - Execute individual workflow nodes.

Integrates:
- Template resolver (T-010): Resolve prompts
- LLM provider (T-009): Call LLM with structured output
- Tool registry (T-008): Load and bind tools
- Output builder (T-007): Enforce output schema
- State builder (T-006): Manage workflow state
- Memory (T-12): Persistent agent memory with namespaced keys
- Tools (T-13): Pre-built tools for web, file, data, system operations

Design decisions:
- Copy-on-write state updates (immutable pattern)
- Fail-fast error handling with context
- Input mappings resolved before prompt resolution
- {state.field} syntax preprocessed to {field} for template resolver
  (TODO T-011.1: Update template resolver to handle state. prefix natively)
"""

import json
import logging
import re
import time
from typing import TYPE_CHECKING, Any, Optional, Union

from pydantic import BaseModel, ValidationError

from configurable_agents.config.schema import GlobalConfig, MemoryConfig, NodeConfig, ToolConfig
from configurable_agents.core.output_builder import OutputBuilderError, build_output_model
from configurable_agents.core.template import TemplateResolutionError, resolve_prompt
from configurable_agents.llm import (
    LLMAPIError,
    LLMConfigError,
    LLMProviderError,
    call_llm_structured,
    create_llm,
    merge_llm_config,
)
from configurable_agents.memory import AgentMemory
from configurable_agents.observability.cost_estimator import CostEstimator
from configurable_agents.storage.base import MemoryRepository
from configurable_agents.tools import ToolConfigError, ToolNotFoundError, get_tool

# Optional sandbox import for code execution
try:
    from configurable_agents.sandbox import (
        DockerSandboxExecutor,
        PythonSandboxExecutor,
        SafetyError,
        get_preset,
        SandboxResult,
    )
    SANDBOX_AVAILABLE = True
except ImportError:
    SANDBOX_AVAILABLE = False
    DockerSandboxExecutor = None
    PythonSandboxExecutor = None
    SafetyError = None
    get_preset = None
    SandboxResult = None

# Optional MLFlow import for direct metric logging
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MLFLOW_AVAILABLE = False

if TYPE_CHECKING:
    from configurable_agents.observability import MLFlowTracker

logger = logging.getLogger(__name__)


class NodeExecutionError(Exception):
    """
    Raised when node execution fails.

    Provides context about which node failed and why.
    """

    def __init__(self, message: str, node_id: Optional[str] = None):
        """
        Initialize node execution error.

        Args:
            message: Error message
            node_id: ID of the node that failed (if known)
        """
        self.node_id = node_id
        self.message = message
        super().__init__(message)


def _strip_state_prefix(template: str) -> str:
    """
    Strip {state.field} → {field} for template resolver compatibility.

    The validator (T-004) accepts {state.field} syntax in prompts, and
    SPEC.md examples use this syntax. However, the template resolver (T-010)
    expects {field} to access state fields directly.

    This is a temporary workaround until the template resolver is updated
    to handle state. prefix natively.

    TODO T-011.1: Update template resolver to handle {state.X} syntax directly
    and remove this preprocessing step.

    Args:
        template: Template string potentially with {state.X} references

    Returns:
        Template with state. prefix removed from all placeholders

    Examples:
        >>> _strip_state_prefix("{state.topic}")
        "{topic}"
        >>> _strip_state_prefix("Process {state.input} and {state.metadata.author}")
        "Process {input} and {metadata.author}"
        >>> _strip_state_prefix("{query}")  # No state prefix
        "{query}"
        >>> _strip_state_prefix("No placeholders")
        "No placeholders"
    """
    # Replace {state.field} with {field}
    # This regex matches {state.anything} and replaces with {anything}
    return re.sub(r"\{state\.([^}]+)\}", r"{\1}", template)


def execute_node(
    node_config: NodeConfig,
    state: BaseModel,
    global_config: Optional[GlobalConfig] = None,
    tracker: Optional["MLFlowTracker"] = None,
) -> dict:
    """
    Execute a single workflow node.

    Execution flow:
    1. Resolve input mappings from state
    2. Resolve prompt template with inputs and state
    3. Load tools from registry
    4. Configure LLM (merge node + global config)
    5. Build output Pydantic model from schema
    6. Call LLM with structured output enforcement
    7. Track metrics with MLFlow (if tracker provided)
    8. Update state with output values
    9. Return updated state (new instance)

    Args:
        node_config: Node configuration
        state: Current workflow state (Pydantic model)
        global_config: Global configuration (optional)
        tracker: MLFlow tracker for observability (optional)

    Returns:
        Dict of updated output fields (partial update for LangGraph reducers)

    Raises:
        NodeExecutionError: If any execution step fails

    Example:
        >>> state = WorkflowState(topic="AI Safety", research="")
        >>> node = NodeConfig(
        ...     id="research_node",
        ...     prompt="Research {topic}",
        ...     output_schema=OutputSchema(type="str"),
        ...     outputs=["research"],
        ... )
        >>> updated_state = execute_node(node, state)
        >>> assert updated_state.research != ""
    """
    node_id = node_config.id

    # Extract storage repos from tracker (attached by executor)
    execution_state_repo = getattr(tracker, 'execution_state_repo', None) if tracker else None
    run_id = getattr(tracker, 'run_id', None) if tracker else None
    memory_repo = getattr(tracker, 'memory_repo', None) if tracker else None

    # Extract workflow context from tracker (attached by runtime executor)
    workflow_name = getattr(tracker, 'workflow_name', None) if tracker else None
    workflow_id = getattr(tracker, 'workflow_id', None) if tracker else None

    # Get agent_id from workflow name for memory namespacing
    agent_id = workflow_name or "default_agent"

    try:
        # ========================================
        # 1. RESOLVE INPUT MAPPINGS
        # ========================================
        resolved_inputs = {}
        if node_config.inputs:
            for local_name, template_str in node_config.inputs.items():
                # Input mapping values are templates like "{topic}" or "{metadata.author}"
                # Resolve them against state to get actual values
                try:
                    # Strip {state.X} prefix if present in input mapping templates
                    cleaned_template = _strip_state_prefix(template_str)
                    # Resolve with no inputs (only state) to get the value
                    value = resolve_prompt(cleaned_template, {}, state)
                    resolved_inputs[local_name] = value
                except TemplateResolutionError as e:
                    raise NodeExecutionError(
                        f"Node '{node_id}': Failed to resolve input mapping '{local_name}' "
                        f"from template '{template_str}': {e}",
                        node_id=node_id,
                    )

        logger.debug(
            f"Node '{node_id}': Resolved {len(resolved_inputs)} input mappings: "
            f"{list(resolved_inputs.keys())}"
        )

        # ========================================
        # 2. RESOLVE PROMPT TEMPLATE
        # ========================================
        try:
            # Strip {state.X} → {X} for template resolver compatibility
            cleaned_prompt = _strip_state_prefix(node_config.prompt)
            # Resolve with inputs (override state) and state (fallback)
            resolved_prompt = resolve_prompt(cleaned_prompt, resolved_inputs, state)
        except TemplateResolutionError as e:
            raise NodeExecutionError(
                f"Node '{node_id}': Prompt template resolution failed: {e}",
                node_id=node_id,
            )

        logger.debug(
            f"Node '{node_id}': Resolved prompt ({len(resolved_prompt)} chars)"
        )

        # ========================================
        # 3. CREATE MEMORY CONTEXT (if enabled)
        # ========================================
        agent_memory = None
        if node_config.memory and node_config.memory.enabled and memory_repo:
            memory_config = node_config.memory
            # Get scope (node-level overrides workflow-level defaults)
            scope = memory_config.default_scope or "agent"

            agent_memory = AgentMemory(
                agent_id=agent_id,
                workflow_id=workflow_id,
                node_id=node_id,
                scope=scope,
                repo=memory_repo,
            )
            logger.debug(
                f"Node '{node_id}': Memory enabled with scope '{scope}'"
            )

        # ========================================
        # 4. LOAD TOOLS (with ToolConfig support)
        # ========================================
        tools = []
        tool_error_modes = {}  # Track error handling per tool
        if node_config.tools:
            try:
                for tool_config in node_config.tools:
                    if isinstance(tool_config, str):
                        # Simple string tool name
                        tool = get_tool(tool_config)
                        tools.append(tool)
                        tool_error_modes[tool_config] = "fail"
                    elif isinstance(tool_config, dict):
                        # ToolConfig dict
                        tool_name = tool_config.get("name")
                        if not tool_name:
                            raise NodeExecutionError(
                                f"Node '{node_id}': Tool config missing 'name' field",
                                node_id=node_id,
                            )
                        tool = get_tool(tool_name)
                        tools.append(tool)
                        tool_error_modes[tool_name] = tool_config.get("on_error", "fail")
                    else:
                        raise NodeExecutionError(
                            f"Node '{node_id}': Invalid tool config type: {type(tool_config)}",
                            node_id=node_id,
                        )

                tool_names = [t.name for t in tools]
                logger.debug(
                    f"Node '{node_id}': Loaded {len(tools)} tools: {tool_names}"
                )
            except (ToolNotFoundError, ToolConfigError) as e:
                raise NodeExecutionError(
                    f"Node '{node_id}': Tool loading failed: {e}",
                    node_id=node_id,
                )

        # ========================================
        # 4.5. CODE EXECUTION (if code field is present)
        # ========================================
        if node_config.code and SANDBOX_AVAILABLE:
            logger.info(f"Node '{node_id}': Executing code in sandbox")

            sandbox_config = node_config.sandbox
            if sandbox_config and sandbox_config.enabled:
                # Determine which executor to use
                use_docker = sandbox_config.mode == "docker"

                # Get resource preset
                preset = get_preset(sandbox_config.preset) if get_preset else {}
                resources = preset.copy()
                if sandbox_config.resources:
                    resources.update(sandbox_config.resources)

                # Determine timeout
                timeout = resources.get("timeout", 60)
                if sandbox_config.timeout:
                    timeout = sandbox_config.timeout

                # Add network config
                if not sandbox_config.network:
                    resources["network"] = False

                # For code execution, we need actual values from state, not strings
                # Create code_inputs dict with actual values
                code_inputs = {}
                if node_config.inputs:
                    for local_name, template_str in node_config.inputs.items():
                        # Extract the actual field name from template (e.g., "{numbers}" -> "numbers")
                        field_name = template_str.strip("{}")
                        if hasattr(state, field_name):
                            code_inputs[local_name] = getattr(state, field_name)
                        else:
                            # Fallback to resolved input string value
                            code_inputs[local_name] = resolved_inputs.get(local_name)

                # Create executor and run code
                try:
                    if use_docker:
                        executor = DockerSandboxExecutor()
                        sandbox_result: SandboxResult = executor.execute(
                            code=node_config.code,
                            inputs=code_inputs,
                            timeout=timeout,
                            resources=resources,
                        )
                    else:
                        executor = PythonSandboxExecutor()
                        # PythonSandboxExecutor doesn't use resources dict
                        sandbox_result: SandboxResult = executor.execute(
                            code=node_config.code,
                            inputs=code_inputs,
                            timeout=timeout,
                        )

                    if not sandbox_result.success:
                        raise NodeExecutionError(
                            f"Node '{node_id}': Sandbox execution failed: {sandbox_result.error}",
                            node_id=node_id,
                        )

                    # Return partial update dict
                    output_name = node_config.outputs[0]
                    logger.info(
                        f"Node '{node_id}': Sandbox execution complete, "
                        f"output={output_name}={sandbox_result.output}"
                    )
                    return {output_name: sandbox_result.output}

                except SafetyError as e:
                    raise NodeExecutionError(
                        f"Node '{node_id}': Code safety violation: {e}",
                        node_id=node_id,
                    )
            else:
                # Sandbox disabled - this is unsafe but allowed
                logger.warning(
                    f"Node '{node_id}': Sandbox disabled, executing code directly "
                    f"(this is unsafe and not recommended)"
                )
                # Execute code directly without sandbox (unsafe!)
                try:
                    exec_globals = {
                        "inputs": resolved_inputs,
                        "result": None,
                        "memory": agent_memory,  # Inject memory for code access
                    }
                    exec(node_config.code, exec_globals)
                    output_name = node_config.outputs[0]
                    return {output_name: exec_globals["result"]}
                except Exception as e:
                    raise NodeExecutionError(
                        f"Node '{node_id}': Direct code execution failed: {e}",
                        node_id=node_id,
                    )
        elif node_config.code and not SANDBOX_AVAILABLE:
            raise NodeExecutionError(
                f"Node '{node_id}': Code execution requested but sandbox module not available",
                node_id=node_id,
            )

        # ========================================
        # 4. CONFIGURE LLM
        # ========================================
        # Merge node-level LLM config with global (node overrides global)
        merged_llm_config = merge_llm_config(
            node_config.llm,
            global_config.llm if global_config else None,
        )

        try:
            llm = create_llm(merged_llm_config)
            logger.debug(f"Node '{node_id}': Created LLM instance")
        except (LLMConfigError, LLMProviderError) as e:
            raise NodeExecutionError(
                f"Node '{node_id}': LLM creation failed: {e}",
                node_id=node_id,
            )

        # ========================================
        # 5. BUILD OUTPUT MODEL
        # ========================================
        try:
            OutputModel = build_output_model(node_config.output_schema, node_id)
            logger.debug(f"Node '{node_id}': Built output model: {OutputModel.__name__}")
        except OutputBuilderError as e:
            raise NodeExecutionError(
                f"Node '{node_id}': Output model creation failed: {e}",
                node_id=node_id,
            )

        # ========================================
        # 6. CALL LLM WITH STRUCTURED OUTPUT
        # ========================================
        # Get max_retries from global config
        max_retries = 3  # Default
        if global_config and global_config.execution:
            max_retries = global_config.execution.max_retries

        # Get model name (for logging and debugging)
        model_name = merged_llm_config.model or "gemini-1.5-flash"  # Default from config

        # NOTE: Node-level tracing is now automatic via mlflow.langchain.autolog()
        # The tracker parameter is kept for backward compatibility and config access,
        # but actual tracing happens automatically - no manual track_node() needed!

        # Start timing for node execution
        node_start_time = time.time()

        try:
            # Call LLM with structured output enforcement
            # Tools are bound if present, retries handled automatically
            # Token usage automatically captured by MLflow 3.9 via mlflow.langchain.autolog()
            result, usage = call_llm_structured(
                llm=llm,
                prompt=resolved_prompt,
                output_model=OutputModel,
                tools=tools if tools else None,
                max_retries=max_retries,
            )
            logger.info(f"Node '{node_id}': LLM call successful")

            # Log token usage for immediate visibility (MLflow captures this too)
            logger.debug(
                f"Node '{node_id}': {usage.input_tokens} input tokens, "
                f"{usage.output_tokens} output tokens"
            )

        except (LLMAPIError, ValidationError) as e:
            # Save failed execution state before raising
            if execution_state_repo and run_id:
                try:
                    error_state = {
                        "node_id": node_id,
                        "duration_seconds": round(time.time() - node_start_time, 4),
                        "status": "failed",
                        "error": str(e)[:500],  # Truncate long error messages
                    }
                    execution_state_repo.save_state(
                        run_id=run_id,
                        state_data=error_state,
                        node_id=node_id,
                    )
                except Exception:
                    pass  # Double-fault: don't let storage errors mask the real error
            raise NodeExecutionError(
                f"Node '{node_id}': LLM call failed: {e}",
                node_id=node_id,
            )

        node_duration = time.time() - node_start_time
        node_duration_ms = node_duration * 1000

        # ========================================
        # 6.5: RECORD TO PROFILER AND LOG METRICS
        # ========================================
        # Record timing to BottleneckAnalyzer (if set by runtime executor)
        # Lazy import to avoid circular dependency with runtime module
        try:
            from configurable_agents.runtime.profiler import get_profiler
            analyzer = get_profiler()
            if analyzer:
                analyzer.record_node(node_id, node_duration_ms)
        except ImportError:
            pass  # Profiler not available

        # Log per-node metrics to MLFlow
        if MLFLOW_AVAILABLE and mlflow.active_run():
            try:
                mlflow.log_metric(f"node_{node_id}_duration_ms", node_duration_ms)
                logger.debug(f"Logged MLFlow metric: node_{node_id}_duration_ms = {node_duration_ms:.2f}ms")
            except Exception as e:
                logger.warning(f"Failed to log node duration to MLFlow: {e}")

        # Calculate cost using CostEstimator
        cost_usd = 0.0
        try:
            cost_estimator = CostEstimator()
            cost_usd = cost_estimator.estimate_cost(
                model=model_name,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )
            # Log per-node cost to MLFlow
            if MLFLOW_AVAILABLE and mlflow.active_run():
                try:
                    mlflow.log_metric(f"node_{node_id}_cost_usd", cost_usd)
                    logger.debug(f"Logged MLFlow metric: node_{node_id}_cost_usd = ${cost_usd:.6f}")
                except Exception as e:
                    logger.warning(f"Failed to log node cost to MLFlow: {e}")
        except Exception as e:
            logger.debug(f"Failed to estimate cost for node '{node_id}': {e}")

        # ========================================
        # 7. BUILD OUTPUT DICT (partial update for LangGraph reducers)
        # ========================================
        updates = {}

        # Extract output values from LLM result
        if node_config.output_schema.type == "object":
            # Object output: multiple fields
            for output_name in node_config.outputs:
                value = getattr(result, output_name)
                updates[output_name] = value
                logger.debug(
                    f"Node '{node_id}': Updated state.{output_name} "
                    f"(type: {type(value).__name__})"
                )
        else:
            # Simple output: single field wrapped in 'result' (from T-007)
            output_name = node_config.outputs[0]
            value = result.result
            updates[output_name] = value
            logger.debug(
                f"Node '{node_id}': Updated state.{output_name} "
                f"(type: {type(value).__name__})"
            )

        # ========================================
        # 7.5: VALIDATE OUTPUT DICT
        # ========================================
        try:
            state_dict = state.model_dump()
            merged = {**state_dict, **updates}
            type(state).model_validate(merged)
        except ValidationError as val_err:
            raise NodeExecutionError(
                f"Node '{node_id}': Output validation failed: {val_err}",
                node_id=node_id,
            )

        # ========================================
        # 8: PERSIST EXECUTION STATE (if storage available)
        # ========================================
        if execution_state_repo and run_id:
            try:
                state_snapshot = {
                    "node_id": node_id,
                    "duration_seconds": round(node_duration, 4),
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.input_tokens + usage.output_tokens,
                    "model": model_name,
                    "status": "completed",
                }

                # Add cost if available from cost estimator
                try:
                    from configurable_agents.observability.cost_estimator import CostEstimator
                    estimator = CostEstimator()
                    cost = estimator.estimate_cost(
                        model=model_name,
                        input_tokens=usage.input_tokens,
                        output_tokens=usage.output_tokens,
                    )
                    state_snapshot["cost_usd"] = cost
                except Exception:
                    state_snapshot["cost_usd"] = 0.0

                # Include the output state values (for trace inspection)
                output_values = {}
                for output_name in node_config.outputs:
                    val = updates.get(output_name)
                    if val is not None:
                        # Truncate large string outputs for storage efficiency
                        str_val = str(val)
                        output_values[output_name] = str_val[:500] if len(str_val) > 500 else str_val
                state_snapshot["outputs"] = output_values

                execution_state_repo.save_state(
                    run_id=run_id,
                    state_data=state_snapshot,
                    node_id=node_id,
                )
                logger.debug(
                    f"Node '{node_id}': Saved execution state "
                    f"(duration={node_duration:.3f}s, tokens={usage.input_tokens + usage.output_tokens})"
                )
            except Exception as e:
                # Storage failure must not break execution
                logger.warning(f"Node '{node_id}': Failed to save execution state: {e}")

        logger.info(
            f"Node '{node_id}': Execution complete, updated {len(node_config.outputs)} "
            f"state fields"
        )

        return updates

    except NodeExecutionError:
        # Re-raise NodeExecutionError as-is
        raise
    except Exception as e:
        # Wrap any unexpected errors
        raise NodeExecutionError(
            f"Node '{node_id}': Unexpected error during execution: {e}",
            node_id=node_id,
        ) from e
