"""Tests for parallel execution functions."""

import pytest
from pydantic import BaseModel, PrivateAttr

from configurable_agents.config.schema import ParallelConfig
from configurable_agents.core import (
    create_fan_out_function,
    get_parallel_item,
    get_parallel_index,
    is_parallel_execution,
)


class TestCreateFanOutFunction:
    """Test fan-out function creation."""

    def test_returns_empty_list_for_no_items(self):
        """Test that empty items list returns empty Send list."""
        config = ParallelConfig(
            items_field="items", target_node="worker", collect_field="results"
        )
        fan_out_fn = create_fan_out_function(config)

        state = {"items": []}
        result = fan_out_fn(state)
        assert result == []

    def test_returns_empty_list_for_missing_field(self):
        """Test that missing items field returns empty Send list."""
        config = ParallelConfig(
            items_field="items", target_node="worker", collect_field="results"
        )
        fan_out_fn = create_fan_out_function(config)

        state = {}  # No 'items' field
        result = fan_out_fn(state)
        assert result == []

    def test_creates_send_objects_for_each_item(self):
        """Test that one Send object is created per item."""
        from langgraph.types import Send

        config = ParallelConfig(
            items_field="items", target_node="worker", collect_field="results"
        )
        fan_out_fn = create_fan_out_function(config)

        state = {"items": ["task1", "task2", "task3"]}
        result = fan_out_fn(state)

        assert len(result) == 3

        # Check each Send object
        for i, send in enumerate(result):
            assert isinstance(send, Send)
            assert send.node == "worker"

    def test_send_has_correct_state_with_parallel_item(self):
        """Test that Send objects include _parallel_item in state."""
        from langgraph.types import Send

        config = ParallelConfig(
            items_field="items", target_node="worker", collect_field="results"
        )
        fan_out_fn = create_fan_out_function(config)

        state = {"items": ["a", "b"], "other": "value"}
        result = fan_out_fn(state)

        # First Send
        assert result[0].node == "worker"
        send_state = result[0].arg
        assert send_state["_parallel_item"] == "a"
        assert send_state["_parallel_index"] == 0
        assert send_state["_parallel_source"] == "items"
        assert send_state["other"] == "value"  # Original state preserved

        # Second Send
        assert result[1].node == "worker"
        send_state = result[1].arg
        assert send_state["_parallel_item"] == "b"
        assert send_state["_parallel_index"] == 1

    def test_works_with_pydantic_state(self):
        """Test that fan-out works with Pydantic state models."""
        from langgraph.types import Send

        class State(BaseModel):
            items: list[str]
            count: int = 0

        config = ParallelConfig(
            items_field="items", target_node="worker", collect_field="results"
        )
        fan_out_fn = create_fan_out_function(config)

        state = State(items=["x", "y"], count=5)
        result = fan_out_fn(state)

        assert len(result) == 2
        assert result[0].arg["_parallel_item"] == "x"
        assert result[0].arg["count"] == 5


class TestGetParallelItem:
    """Test get_parallel_item helper."""

    def test_returns_item_from_dict(self):
        """Test getting parallel item from dict state."""
        state = {"_parallel_item": "my_item", "other": "value"}
        result = get_parallel_item(state)
        assert result == "my_item"

    def test_returns_item_from_pydantic_with_private_attr(self):
        """Test getting parallel item from Pydantic state with PrivateAttr."""
        class State(BaseModel):
            other: str = "value"
            _parallel_item: str = PrivateAttr(default=None)

        state = State(other="value")
        state._parallel_item = "my_item"
        result = get_parallel_item(state)
        assert result == "my_item"

    def test_raises_key_error_for_missing_item(self):
        """Test that missing _parallel_item raises KeyError."""
        state = {"other": "value"}
        with pytest.raises(KeyError, match="_parallel_item"):
            get_parallel_item(state)


class TestGetParallelIndex:
    """Test get_parallel_index helper."""

    def test_returns_index_from_dict(self):
        """Test getting parallel index from dict state."""
        state = {"_parallel_index": 3, "other": "value"}
        result = get_parallel_index(state)
        assert result == 3

    def test_returns_index_from_pydantic_with_private_attr(self):
        """Test getting parallel index from Pydantic state with PrivateAttr."""
        class State(BaseModel):
            other: str = "value"
            _parallel_index: int = PrivateAttr(default=None)

        state = State(other="value")
        state._parallel_index = 5
        result = get_parallel_index(state)
        assert result == 5

    def test_raises_key_error_for_missing_index(self):
        """Test that missing _parallel_index raises KeyError."""
        state = {"other": "value"}
        with pytest.raises(KeyError, match="_parallel_index"):
            get_parallel_index(state)


class TestIsParallelExecution:
    """Test is_parallel_execution helper."""

    def test_returns_true_when_parallel_item_present(self):
        """Test that presence of _parallel_item indicates parallel execution."""
        state = {"_parallel_item": "item", "_parallel_index": 0}
        assert is_parallel_execution(state) is True

    def test_returns_true_when_only_index_present(self):
        """Test that _parallel_index alone also indicates parallel execution."""
        state = {"_parallel_index": 0}
        assert is_parallel_execution(state) is True

    def test_returns_false_when_no_parallel_markers(self):
        """Test that absence of markers indicates non-parallel execution."""
        state = {"other": "value"}
        assert is_parallel_execution(state) is False

    def test_works_with_pydantic_with_private_attr(self):
        """Test with Pydantic state using PrivateAttr."""
        class State(BaseModel):
            other: str = "value"
            _parallel_item: str = PrivateAttr(default=None)
            _parallel_index: int = PrivateAttr(default=None)

        state = State(other="value")
        state._parallel_item = "x"
        state._parallel_index = 0
        assert is_parallel_execution(state) is True

        class State2(BaseModel):
            other: str = "value"

        state2 = State2(other="value")
        assert is_parallel_execution(state2) is False
