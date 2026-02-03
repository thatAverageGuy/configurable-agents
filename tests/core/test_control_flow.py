"""Tests for control flow functions."""

import pytest
from pydantic import BaseModel

from configurable_agents.config.schema import LoopConfig, Route, RouteCondition
from configurable_agents.core import (
    ControlFlowError,
    create_loop_router,
    create_routing_function,
    get_loop_iteration_key,
    increment_loop_iteration,
)


class SimpleState(BaseModel):
    """Simple state for testing."""

    score: float = 0.5
    approved: bool = False
    status: str = "pending"
    count: int = 0


class TestEvaluateCondition:
    """Test condition evaluation."""

    def test_simple_comparison_greater_than(self):
        """Test state.field > value comparison."""
        from configurable_agents.core.control_flow import _evaluate_condition

        result = _evaluate_condition("state.score > 0.8", {"score": 0.9})
        assert result is True

        result = _evaluate_condition("state.score > 0.8", {"score": 0.7})
        assert result is False

    def test_simple_comparison_less_than(self):
        """Test state.field < value comparison."""
        from configurable_agents.core.control_flow import _evaluate_condition

        result = _evaluate_condition("state.count < 10", {"count": 5})
        assert result is True

        result = _evaluate_condition("state.count < 10", {"count": 15})
        assert result is False

    def test_simple_comparison_equal(self):
        """Test state.field == value comparison."""
        from configurable_agents.core.control_flow import _evaluate_condition

        result = _evaluate_condition('state.status == "approved"', {"status": "approved"})
        assert result is True

        result = _evaluate_condition('state.status == "approved"', {"status": "pending"})
        assert result is False

    def test_simple_comparison_not_equal(self):
        """Test state.field != value comparison."""
        from configurable_agents.core.control_flow import _evaluate_condition

        result = _evaluate_condition('state.status != "rejected"', {"status": "approved"})
        assert result is True

        result = _evaluate_condition('state.status != "rejected"', {"status": "rejected"})
        assert result is False

    def test_boolean_field_check(self):
        """Test boolean field truthiness check."""
        from configurable_agents.core.control_flow import _evaluate_condition

        result = _evaluate_condition("state.approved", {"approved": True})
        assert result is True

        result = _evaluate_condition("state.approved", {"approved": False})
        assert result is False

    def test_boolean_negation(self):
        """Test 'not state.field' check."""
        from configurable_agents.core.control_flow import _evaluate_condition

        result = _evaluate_condition("not state.approved", {"approved": False})
        assert result is True

        result = _evaluate_condition("not state.approved", {"approved": True})
        assert result is False

    def test_compound_and(self):
        """Test compound expression with 'and'."""
        from configurable_agents.core.control_flow import _evaluate_condition

        result = _evaluate_condition(
            "state.score > 0.5 and state.approved", {"score": 0.8, "approved": True}
        )
        assert result is True

        result = _evaluate_condition(
            "state.score > 0.5 and state.approved", {"score": 0.3, "approved": True}
        )
        assert result is False

        result = _evaluate_condition(
            "state.score > 0.5 and state.approved", {"score": 0.8, "approved": False}
        )
        assert result is False

    def test_compound_or(self):
        """Test compound expression with 'or'."""
        from configurable_agents.core.control_flow import _evaluate_condition

        result = _evaluate_condition(
            "state.score > 0.8 or state.approved", {"score": 0.9, "approved": False}
        )
        assert result is True

        result = _evaluate_condition(
            "state.score > 0.8 or state.approved", {"score": 0.5, "approved": True}
        )
        assert result is True

        result = _evaluate_condition(
            "state.score > 0.8 or state.approved", {"score": 0.5, "approved": False}
        )
        assert result is False

    def test_parenthesized_expression(self):
        """Test parenthesized expressions."""
        from configurable_agents.core.control_flow import _evaluate_condition

        result = _evaluate_condition("(state.score > 0.5)", {"score": 0.8})
        assert result is True

    def test_missing_field_returns_false(self):
        """Test that missing field references return False."""
        from configurable_agents.core.control_flow import _evaluate_condition

        result = _evaluate_condition("state.missing_field", {"other": 1})
        assert result is False

    def test_dangerous_expression_raises_error(self):
        """Test that dangerous expressions are rejected."""
        from configurable_agents.core.control_flow import _evaluate_condition

        with pytest.raises(ControlFlowError):
            _evaluate_condition("state.field > __import__('os').system('ls')", {"field": 1})

        with pytest.raises(ControlFlowError):
            _evaluate_condition("eval('1+1')", {})

        with pytest.raises(ControlFlowError):
            _evaluate_condition("lambda x: x", {})


class TestCreateRoutingFunction:
    """Test routing function creation."""

    def test_routing_with_matching_condition(self):
        """Test routing returns correct target when condition matches."""
        routes = [
            Route(condition=RouteCondition(logic="state.score > 0.8"), to="high_score_node"),
            Route(condition=RouteCondition(logic="default"), to="default_node"),
        ]

        routing_fn = create_routing_function(routes, {})

        state = SimpleState(score=0.9)
        result = routing_fn(state)
        assert result == "high_score_node"

    def test_routing_with_non_matching_condition(self):
        """Test routing returns default when no conditions match."""
        routes = [
            Route(condition=RouteCondition(logic="state.score > 0.8"), to="high_score_node"),
            Route(condition=RouteCondition(logic="default"), to="default_node"),
        ]

        routing_fn = create_routing_function(routes, {})

        state = SimpleState(score=0.5)
        result = routing_fn(state)
        assert result == "default_node"

    def test_routing_checks_conditions_in_order(self):
        """Test that conditions are checked in order (first match wins)."""
        routes = [
            Route(condition=RouteCondition(logic="state.score > 0.5"), to="first_match"),
            Route(condition=RouteCondition(logic="state.score > 0.8"), to="second_match"),
            Route(condition=RouteCondition(logic="default"), to="default_node"),
        ]

        routing_fn = create_routing_function(routes, {})

        state = SimpleState(score=0.9)
        result = routing_fn(state)
        assert result == "first_match"  # First condition matches

    def test_routing_with_end_target(self):
        """Test routing to END constant."""
        from langgraph.graph import END

        routes = [
            Route(condition=RouteCondition(logic="state.approved"), to="END"),
            Route(condition=RouteCondition(logic="default"), to="retry_node"),
        ]

        routing_fn = create_routing_function(routes, {})

        state = SimpleState(approved=True)
        result = routing_fn(state)
        assert result == END

    def test_routing_without_default_raises_error(self):
        """Test that routing without default route raises error."""
        routes = [
            Route(condition=RouteCondition(logic="state.score > 0.8"), to="high_score_node"),
        ]

        with pytest.raises(ControlFlowError, match="must include a default route"):
            create_routing_function(routes, {})

    def test_routing_with_pydantic_state(self):
        """Test routing works with Pydantic state models."""
        routes = [
            Route(condition=RouteCondition(logic="state.approved"), to="approved_node"),
            Route(condition=RouteCondition(logic="default"), to="default_node"),
        ]

        routing_fn = create_routing_function(routes, {})

        state = SimpleState(approved=True)
        result = routing_fn(state)
        assert result == "approved_node"


class TestCreateLoopRouter:
    """Test loop router creation."""

    def test_loop_continues_when_condition_not_met(self):
        """Test loop returns to from_node when condition not met."""
        loop_config = LoopConfig(condition_field="is_done", exit_to="END", max_iterations=10)
        loop_fn = create_loop_router(loop_config, "process_node")

        state = {"is_done": False, "_loop_iteration_process_node": 0}
        result = loop_fn(state)
        assert result == "process_node"

    def test_loop_exits_when_condition_met(self):
        """Test loop exits to exit_to when condition is met."""
        from langgraph.graph import END

        loop_config = LoopConfig(condition_field="is_done", exit_to="END", max_iterations=10)
        loop_fn = create_loop_router(loop_config, "process_node")

        state = {"is_done": True, "_loop_iteration_process_node": 0}
        result = loop_fn(state)
        assert result == END

    def test_loop_exits_at_max_iterations(self):
        """Test loop exits when max iterations reached."""
        loop_config = LoopConfig(condition_field="is_done", exit_to="next_node", max_iterations=5)
        loop_fn = create_loop_router(loop_config, "process_node")

        state = {"is_done": False, "_loop_iteration_process_node": 5}
        result = loop_fn(state)
        assert result == "next_node"

    def test_loop_continues_below_max_iterations(self):
        """Test loop continues when below max iterations."""
        loop_config = LoopConfig(condition_field="is_done", exit_to="next_node", max_iterations=5)
        loop_fn = create_loop_router(loop_config, "process_node")

        state = {"is_done": False, "_loop_iteration_process_node": 3}
        result = loop_fn(state)
        assert result == "process_node"

    def test_loop_with_missing_iteration_key(self):
        """Test loop handles missing iteration key (starts at 0)."""
        loop_config = LoopConfig(condition_field="is_done", exit_to="next_node", max_iterations=5)
        loop_fn = create_loop_router(loop_config, "process_node")

        state = {"is_done": False}
        result = loop_fn(state)
        assert result == "process_node"

    def test_loop_with_pydantic_state(self):
        """Test loop router works with Pydantic state."""
        loop_config = LoopConfig(condition_field="approved", exit_to="END", max_iterations=3)

        class LoopState(BaseModel):
            approved: bool = False
            _loop_iteration_process: int = 0

        loop_fn = create_loop_router(loop_config, "process")

        state = LoopState(approved=False)
        result = loop_fn(state)
        assert result == "process"


class TestLoopIterationHelpers:
    """Test loop iteration helper functions."""

    def test_get_loop_iteration_key(self):
        """Test iteration key generation."""
        key = get_loop_iteration_key("my_node")
        assert key == "_loop_iteration_my_node"

    def test_increment_loop_iteration(self):
        """Test iteration counter increment."""
        state = {}
        new_count = increment_loop_iteration(state, "my_node")
        assert new_count == 1
        assert state["_loop_iteration_my_node"] == 1

        new_count = increment_loop_iteration(state, "my_node")
        assert new_count == 2
        assert state["_loop_iteration_my_node"] == 2

    def test_increment_from_existing_count(self):
        """Test incrementing from existing counter."""
        state = {"_loop_iteration_my_node": 5}
        new_count = increment_loop_iteration(state, "my_node")
        assert new_count == 6
