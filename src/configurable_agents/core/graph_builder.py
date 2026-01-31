"""
Graph builder - Build LangGraph from WorkflowConfig.

Integrates:
- Node executor (T-011): Execute individual nodes
- State builder (T-006): Dynamic Pydantic models
- Config schema (T-003): WorkflowConfig structure

Design decisions:
- Direct Pydantic BaseModel integration with LangGraph
- Closure-based node functions (captures node_config and global_config)
- START/END as entry/exit points (not identity nodes)
- Compiled graph return (ready for execution)
- Minimal defensive validation (T-004 already validates)
"""

import logging
from typing import TYPE_CHECKING, Callable, Optional, Type

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from configurable_agents.config.schema import (
    EdgeConfig,
    GlobalConfig,
    NodeConfig,
    WorkflowConfig,
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
    _validate_linear_flow(config)

    # Create StateGraph with Pydantic model
    graph = StateGraph(state_model)
    logger.debug(f"Created StateGraph with state: {state_model.__name__}")

    # Add nodes (via closure-based functions)
    for node_config in config.nodes:
        node_fn = make_node_function(node_config, global_config, tracker)
        graph.add_node(node_config.id, node_fn)
        logger.debug(f"Added node: {node_config.id}")

    # Add edges (translate START/END)
    for edge in config.edges:
        _add_edge(graph, edge)
        logger.debug(f"Added edge: {edge.from_} -> {edge.to}")

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
        Node function: (state: BaseModel) -> BaseModel

    Design:
        - Closure captures node_config, global_config, and tracker
        - Calls execute_node from T-011
        - NodeExecutionError propagated unchanged (already has context)
        - Unexpected errors wrapped with node context
    """

    def node_fn(state: BaseModel) -> BaseModel:
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


def _add_edge(graph: StateGraph, edge: EdgeConfig) -> None:
    """
    Add edge to graph, translating START/END strings to constants.

    Args:
        graph: StateGraph instance
        edge: Edge configuration

    Design:
        - "START" string → START constant
        - "END" string → END constant
        - Other strings remain as node IDs
    """
    from_node = START if edge.from_ == "START" else edge.from_
    to_node = END if edge.to == "END" else edge.to
    graph.add_edge(from_node, to_node)


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


def _validate_linear_flow(config: WorkflowConfig) -> None:
    """
    Verify linear flow constraint (v0.1).

    Should never fail - T-004 enforces this.
    This is defensive validation.

    Args:
        config: Workflow configuration

    Raises:
        GraphBuilderError: If conditional routing found

    Checks:
        - No conditional routes (edge.routes)
        - No branching (multiple outgoing edges per node)
    """
    # Check for routes (conditional edges) - v0.2+ feature
    for edge in config.edges:
        if edge.routes:
            raise GraphBuilderError(
                f"Conditional routing not supported in v0.1\n"
                f"Found routes in edge from '{edge.from_}'\n\n"
                "Validator should have caught this. "
                "This is a bug - please report."
            )

    # Check for multiple outgoing edges (branching)
    outgoing_counts = {}
    for edge in config.edges:
        if edge.from_ != "START":
            outgoing_counts[edge.from_] = outgoing_counts.get(edge.from_, 0) + 1

    for node, count in outgoing_counts.items():
        if count > 1:
            raise GraphBuilderError(
                f"Node '{node}' has {count} outgoing edges. "
                "v0.1 supports linear flows only (no branching). "
                "Validator should have caught this."
            )
