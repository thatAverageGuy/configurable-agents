"""
Graph builder - Build LangGraph from WorkflowConfig.

Integrates:
- Node executor (T-011): Execute individual nodes
- State builder (T-006): Dynamic Pydantic models
- Config schema (T-003): WorkflowConfig structure
- Control flow (T-013): Conditional routing and loop functions
- Fork-join parallel: Multiple concurrent nodes via list `to`

Design decisions:
- Direct Pydantic BaseModel integration with LangGraph
- Closure-based node functions (captures node_config and global_config)
- START/END as entry/exit points (not identity nodes)
- Compiled graph return (ready for execution)
- Minimal defensive validation (T-004 already validates)
- Support for conditional edges, loop edges, and fork-join parallel
"""

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Type

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from configurable_agents.config.schema import (
    EdgeConfig,
    GlobalConfig,
    NodeConfig,
    WorkflowConfig,
)
from configurable_agents.core.control_flow import (
    create_loop_router,
    create_routing_function,
    get_loop_iteration_key,
    increment_loop_iteration,
)
from configurable_agents.core.node_executor import NodeExecutionError, execute_node

if TYPE_CHECKING:
    from configurable_agents.observability import MLFlowTracker

logger = logging.getLogger(__name__)


class GraphBuilderError(Exception):
    """
    Raised when graph construction fails.

    This indicates either:
    1. A bug in the validator (T-004) - config should have been rejected
    2. A LangGraph compatibility issue
    3. Internal logic error in graph builder
    """

    pass


def build_graph(
    config: WorkflowConfig,
    state_model: Type[BaseModel],
    global_config: Optional[GlobalConfig] = None,
    tracker: Optional["MLFlowTracker"] = None,
) -> CompiledStateGraph:
    """
    Build and compile LangGraph from config.

    Supports:
    - Linear edges (from -> to)
    - Fork-join parallel edges (from -> [to1, to2, ...])
    - Conditional edges (routes with state-based conditions)
    - Loop edges (iteration with termination conditions)

    Args:
        config: Validated workflow configuration
        state_model: Pydantic state model (from build_state_model)
        global_config: Global configuration (optional)
        tracker: MLFlow tracker for observability (optional)

    Returns:
        Compiled LangGraph ready for execution

    Raises:
        GraphBuilderError: If graph construction or compilation fails

    Example:
        >>> from configurable_agents.config import parse_config_file, WorkflowConfig
        >>> from configurable_agents.core import build_state_model, build_graph
        >>>
        >>> config_dict = parse_config_file("workflow.yaml")
        >>> config = WorkflowConfig(**config_dict)
        >>> state_model = build_state_model(config.state)
        >>> graph = build_graph(config, state_model, config.config)
        >>>
        >>> # Execute graph
        >>> initial = state_model(topic="AI Safety")
        >>> final = graph.invoke(initial)
        >>> print(final.research)
    """
    logger.info(f"Building graph for workflow '{config.flow.name}'")

    # Defensive validation (should never fail on valid configs)
    _validate_config_for_graph(config)

    # Collect nodes that are targets of loops for iteration tracking
    loop_targets = _collect_loop_targets(config)

    # Create StateGraph with Pydantic model
    graph = StateGraph(state_model)
    logger.debug(f"Created StateGraph with state: {state_model.__name__}")

    # Add nodes (via closure-based functions)
    for node_config in config.nodes:
        node_fn = make_node_function(node_config, global_config, tracker)
        # Wrap with loop counter if this node is a loop target
        if node_config.id in loop_targets:
            node_fn = _wrap_with_loop_counter(node_fn, node_config.id)
        graph.add_node(node_config.id, node_fn)
        logger.debug(f"Added node: {node_config.id}")

    # Add edges (all types: linear, conditional, loop, parallel)
    state_fields = {name: field.type for name, field in config.state.fields.items()}
    for edge in config.edges:
        _add_edge(graph, edge, state_fields, config.nodes)
        edge_desc = _describe_edge(edge)
        logger.debug(f"Added edge: {edge_desc}")

    # Compile graph
    logger.info("Compiling graph...")
    try:
        compiled = graph.compile()
        logger.info(
            f"Graph compiled successfully "
            f"({len(config.nodes)} nodes, {len(config.edges)} edges)"
        )
        return compiled
    except Exception as e:
        raise GraphBuilderError(
            f"Graph compilation failed: {e}\n"
            "This indicates a bug in config validation (T-004) or LangGraph compatibility."
        ) from e


def make_node_function(
    node_config: NodeConfig,
    global_config: Optional[GlobalConfig],
    tracker: Optional["MLFlowTracker"] = None,
) -> Callable[[BaseModel], BaseModel]:
    """
    Create LangGraph-compatible node function.

    Returns a closure that captures node_config, global_config, and tracker,
    calls execute_node, and handles errors with node context.

    Args:
        node_config: Node configuration
        global_config: Global configuration (optional)
        tracker: MLFlow tracker for observability (optional)

    Returns:
        Node function: (state: BaseModel) -> dict

    Design:
        - Closure captures node_config, global_config, and tracker
        - Calls execute_node from T-011
        - NodeExecutionError propagated unchanged (already has context)
        - Unexpected errors wrapped with node context
    """

    def node_fn(state: BaseModel) -> dict:
        """Node function that executes the node."""
        try:
            updated_state = execute_node(node_config, state, global_config, tracker)
            return updated_state
        except NodeExecutionError:
            # Already has node context, re-raise as-is
            raise
        except Exception as e:
            # Wrap unexpected errors with node context
            raise NodeExecutionError(
                f"Node '{node_config.id}': Unexpected error: {e}",
                node_id=node_config.id,
            ) from e

    # Set function name for debugging
    node_fn.__name__ = f"node_{node_config.id}"
    return node_fn


def _add_edge(
    graph: StateGraph,
    edge: EdgeConfig,
    state_fields: Dict[str, str],
    nodes: list,
) -> None:
    """
    Add edge to graph, handling all edge types.

    Args:
        graph: StateGraph instance
        edge: Edge configuration
        state_fields: State field names and types
        nodes: List of node configs for reference

    Edge types:
        - Linear: edge.to as str (direct edge)
        - Fork-join: edge.to as list (multiple parallel targets)
        - Conditional: edge.routes (conditional routing based on state)
        - Loop: edge.loop (iteration with exit condition)
    """
    from_node = START if edge.from_ == "START" else edge.from_

    # Linear or fork-join edge
    if edge.to:
        if isinstance(edge.to, list):
            # Fork-join: add edge to each target
            for target in edge.to:
                to_node = END if target == "END" else target
                graph.add_edge(from_node, to_node)
        else:
            to_node = END if edge.to == "END" else edge.to
            graph.add_edge(from_node, to_node)
        return

    # Conditional edge (routes)
    if edge.routes:
        routing_fn = create_routing_function(edge.routes, state_fields)
        graph.add_conditional_edges(from_node, routing_fn)
        return

    # Loop edge
    if edge.loop:
        loop_fn = create_loop_router(edge.loop, from_node)
        graph.add_conditional_edges(from_node, loop_fn)
        return



def _collect_loop_targets(config: WorkflowConfig) -> set:
    """
    Collect node IDs that are targets of loop edges.

    These nodes need their output functions wrapped to increment loop counters.

    Args:
        config: Workflow configuration

    Returns:
        Set of node IDs that are targets of loops
    """
    # Nodes that have incoming loop edges (where they loop back to themselves)
    loop_targets = set()

    # A node is a loop target if it has an incoming loop edge from itself
    # or from another node that causes it to repeat
    for edge in config.edges:
        if edge.loop:
            # The node loops back to itself
            loop_targets.add(edge.from_)

    return loop_targets


def _wrap_with_loop_counter(node_fn: Callable, node_id: str) -> Callable:
    """
    Wrap a node function to increment its loop iteration counter.

    The wrapped function increments _loop_iteration_{node_id} in state
    before executing the original node function.

    Args:
        node_fn: Original node function
        node_id: Node identifier

    Returns:
        Wrapped node function that increments loop counter
    """
    iteration_key = get_loop_iteration_key(node_id)

    def wrapped_fn(state: BaseModel) -> dict:
        """Execute node with loop counter increment."""
        # Increment iteration counter
        if hasattr(state, "model_dump"):
            state_dict = state.model_dump()
        else:
            state_dict = dict(state)

        # Increment counter
        current = state_dict.get(iteration_key, 0)

        # Execute original node function with current state
        result = node_fn(state)

        # Merge counter update into returned dict
        if isinstance(result, dict):
            result[iteration_key] = current + 1
        return result

    # Preserve function name for debugging
    wrapped_fn.__name__ = f"loop_wrapped_{node_fn.__name__}"
    return wrapped_fn


def _describe_edge(edge: EdgeConfig) -> str:
    """Get a human-readable description of an edge for logging."""
    from_node = edge.from_

    if edge.to:
        if isinstance(edge.to, list):
            return f"{from_node} -> fork-join({', '.join(edge.to)})"
        return f"{from_node} -> {edge.to} (linear)"

    if edge.routes:
        targets = [r.to for r in edge.routes]
        return f"{from_node} -> routes({', '.join(targets)}) (conditional)"

    if edge.loop:
        return f"{from_node} -> loop({edge.loop.condition_field}, exit={edge.loop.exit_to})"

    return f"{from_node} -> unknown"


def _validate_config_for_graph(config: WorkflowConfig) -> None:
    """
    Defensive validation before building graph.

    Should never fail on valid configs.
    If this fails, it's a bug in the validator (T-004).

    Args:
        config: Workflow configuration

    Raises:
        GraphBuilderError: If config is invalid

    Checks:
        - At least one node exists
        - At least one edge exists
        - Exactly one START edge
    """
    if not config.nodes:
        raise GraphBuilderError(
            "No nodes defined. Validator should have caught this. "
            "This is a bug - please report."
        )

    if not config.edges:
        raise GraphBuilderError(
            "No edges defined. Validator should have caught this. "
            "This is a bug - please report."
        )

    # Check START edge exists (exactly one)
    start_edges = [e for e in config.edges if e.from_ == "START"]
    if len(start_edges) == 0:
        raise GraphBuilderError(
            "No START edge found. Validator should have caught this. "
            "This is a bug - please report."
        )
    if len(start_edges) > 1:
        raise GraphBuilderError(
            f"Multiple START edges found ({len(start_edges)}). "
            "Validator should have caught this. "
            "This is a bug - please report."
        )
