"""
Parallel execution functions for fan-out/fan-in patterns.

Provides Send object factories for parallel node execution via LangGraph.
"""

from typing import Any, Callable, Dict, List

from langgraph.types import Send

from configurable_agents.config.schema import ParallelConfig


def create_fan_out_function(parallel_config: ParallelConfig) -> Callable:
    """
    Create a fan-out function for parallel execution.

    The returned function creates Send objects for each item in the items_field,
    allowing the target node to execute concurrently for each item.

    Args:
        parallel_config: Parallel execution configuration

    Returns:
        Function that takes state and returns list of Send objects

    Each Send object:
    - Targets the configured node
    - Passes state with _parallel_item (current item) and _parallel_index (position)
    - Results are collected via state reducer on collect_field
    """
    def fan_out_fn(state):
        """Create Send objects for each item to process in parallel."""
        # Convert state to dict if it's a Pydantic model
        if hasattr(state, "model_dump"):
            state_dict = state.model_dump()
        elif hasattr(state, "dict"):
            state_dict = state.dict()
        else:
            state_dict = dict(state)

        # Get items to fan out over
        items = state_dict.get(parallel_config.items_field, [])

        if not items:
            return []  # No items to process, skip fan-out

        # Create Send object for each item
        sends = []
        for i, item in enumerate(items):
            # Each parallel invocation gets the full state plus item-specific context
            item_state = {
                **state_dict,
                "_parallel_item": item,
                "_parallel_index": i,
                "_parallel_source": parallel_config.items_field,
            }
            sends.append(Send(parallel_config.target_node, item_state))

        return sends

    return fan_out_fn


def get_parallel_item(state: Any) -> Any:
    """
    Get the current parallel item from state.

    Args:
        state: State dict or Pydantic model

    Returns:
        The current parallel item (_parallel_item)

    Raises:
        KeyError: If _parallel_item not in state
    """
    if hasattr(state, "model_dump"):
        # Pydantic v2 excludes underscore fields by default
        # Use model_dump(mode='python') or exclude_unset/exclude_none
        state_dict = state.model_dump(exclude_none=False, exclude_unset=False)
        # Also check __dict__ and __pydantic_fields_set__ for underscore fields
        if "_parallel_item" not in state_dict:
            # Underscore fields might not be in the model dump
            # Try to get them from __dict__ or object attributes
            if hasattr(state, "_parallel_item"):
                return state._parallel_item
            raise KeyError("_parallel_item")
    elif hasattr(state, "dict"):
        state_dict = state.dict()
    else:
        state_dict = dict(state)

    return state_dict["_parallel_item"]


def get_parallel_index(state: Any) -> int:
    """
    Get the current parallel index from state.

    Args:
        state: State dict or Pydantic model

    Returns:
        The current parallel index (_parallel_index)

    Raises:
        KeyError: If _parallel_index not in state
    """
    if hasattr(state, "model_dump"):
        state_dict = state.model_dump(exclude_none=False, exclude_unset=False)
        if "_parallel_index" not in state_dict:
            if hasattr(state, "_parallel_index"):
                return state._parallel_index
            raise KeyError("_parallel_index")
    elif hasattr(state, "dict"):
        state_dict = state.dict()
    else:
        state_dict = dict(state)

    return state_dict["_parallel_index"]


def is_parallel_execution(state: Any) -> bool:
    """
    Check if current execution is part of a parallel fan-out.

    Args:
        state: State dict or Pydantic model

    Returns:
        True if _parallel_item or _parallel_index is in state (parallel execution), False otherwise
    """
    if hasattr(state, "model_dump"):
        state_dict = state.model_dump(exclude_none=False, exclude_unset=False)
        # Also check attributes directly for underscore fields
        has_item = "_parallel_item" in state_dict or hasattr(state, "_parallel_item")
        has_index = "_parallel_index" in state_dict or hasattr(state, "_parallel_index")
        return has_item or has_index
    elif hasattr(state, "dict"):
        state_dict = state.dict()
    else:
        state_dict = dict(state)

    return "_parallel_item" in state_dict or "_parallel_index" in state_dict
