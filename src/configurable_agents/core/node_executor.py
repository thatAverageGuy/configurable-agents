"""
Node executor - Execute individual workflow nodes.

Integrates:
- Template resolver (T-010): Resolve prompts
- LLM provider (T-009): Call LLM with structured output
- Tool registry (T-008): Load and bind tools
- Output builder (T-007): Enforce output schema
- State builder (T-006): Manage workflow state

Design decisions:
- Copy-on-write state updates (immutable pattern)
- Fail-fast error handling with context
- Input mappings resolved before prompt resolution
- {state.field} syntax preprocessed to {field} for template resolver
  (TODO T-011.1: Update template resolver to handle state. prefix natively)
"""

import logging
import re
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ValidationError

from configurable_agents.config.schema import GlobalConfig, NodeConfig
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
from configurable_agents.tools import ToolConfigError, ToolNotFoundError, get_tool

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
) -> BaseModel:
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
        Updated state (new Pydantic instance with outputs applied)

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
        # 3. LOAD TOOLS
        # ========================================
        tools = []
        if node_config.tools:
            try:
                tools = [get_tool(name) for name in node_config.tools]
                logger.debug(
                    f"Node '{node_id}': Loaded {len(tools)} tools: {node_config.tools}"
                )
            except (ToolNotFoundError, ToolConfigError) as e:
                raise NodeExecutionError(
                    f"Node '{node_id}': Tool loading failed: {e}",
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

        # Get model name for tracking
        model_name = merged_llm_config.model or "gemini-1.5-flash"  # Default from config

        # Prepare tool names for tracking
        tool_names = node_config.tools if node_config.tools else None

        # Track node execution with MLFlow
        tracker_context = (
            tracker.track_node(
                node_id=node_id,
                model=model_name,
                tools=tool_names,
                node_config=node_config,
            )
            if tracker
            else None
        )

        try:
            # Enter tracking context if available
            if tracker_context:
                tracker_context.__enter__()

            # Call LLM with structured output enforcement
            # Tools are bound if present, retries handled automatically
            result, usage = call_llm_structured(
                llm=llm,
                prompt=resolved_prompt,
                output_model=OutputModel,
                tools=tools if tools else None,
                max_retries=max_retries,
            )
            logger.info(f"Node '{node_id}': LLM call successful")

            # Log node metrics if tracker available
            if tracker:
                # Convert result to JSON for response logging
                try:
                    response_text = result.model_dump_json(indent=2)
                except Exception:
                    response_text = str(result)

                tracker.log_node_metrics(
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    model=model_name,
                    retries=max_retries - 1 if usage.input_tokens > 0 else 0,  # Estimate retries
                    prompt=resolved_prompt,
                    response=response_text,
                )

        except (LLMAPIError, ValidationError) as e:
            raise NodeExecutionError(
                f"Node '{node_id}': LLM call failed: {e}",
                node_id=node_id,
            )
        finally:
            # Exit tracking context if available
            if tracker_context:
                try:
                    tracker_context.__exit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Failed to exit tracker context: {e}")

        # ========================================
        # 7. UPDATE STATE
        # ========================================
        # Copy-on-write: create new state instance (immutable pattern)
        new_state = state.model_copy()

        # Extract output values from LLM result and update state
        if node_config.output_schema.type == "object":
            # Object output: multiple fields
            for output_name in node_config.outputs:
                value = getattr(result, output_name)
                setattr(new_state, output_name, value)
                logger.debug(
                    f"Node '{node_id}': Updated state.{output_name} "
                    f"(type: {type(value).__name__})"
                )
        else:
            # Simple output: single field wrapped in 'result' (from T-007)
            output_name = node_config.outputs[0]
            value = result.result
            setattr(new_state, output_name, value)
            logger.debug(
                f"Node '{node_id}': Updated state.{output_name} "
                f"(type: {type(value).__name__})"
            )

        # Pydantic auto-validates on setattr
        # If validation fails, raises ValidationError (caught above)

        logger.info(
            f"Node '{node_id}': Execution complete, updated {len(node_config.outputs)} "
            f"state fields"
        )

        return new_state

    except NodeExecutionError:
        # Re-raise NodeExecutionError as-is
        raise
    except Exception as e:
        # Wrap any unexpected errors
        raise NodeExecutionError(
            f"Node '{node_id}': Unexpected error during execution: {e}",
            node_id=node_id,
        ) from e
