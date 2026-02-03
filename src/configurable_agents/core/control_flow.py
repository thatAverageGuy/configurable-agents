"""
Control flow functions for advanced workflow patterns.

Provides routing functions for conditional branching and loop logic.
Implements safe condition evaluation without eval/exec.
"""

import ast
import operator
import re
from typing import Any, Callable, Dict, List

from langgraph.graph import END

from configurable_agents.config.schema import LoopConfig, Route


class ControlFlowError(Exception):
    """Raised when control flow evaluation fails."""

    pass


def _evaluate_condition(logic: str, state: Dict[str, Any]) -> bool:
    """
    Safely evaluate a condition expression against state.

    Supports:
    - Comparison: state.field > value, state.field == "string", state.field < 10
    - Boolean: state.field (truthy check), not state.field
    - Compound: state.field > 0.5 and state.other == "yes"
    - Parentheses for grouping

    Does NOT use eval() or exec() for security.

    Args:
        logic: Condition expression (e.g., "state.score > 0.8")
        state: State dictionary with field values

    Returns:
        Boolean result of condition evaluation

    Raises:
        ControlFlowError: If expression is invalid or contains unsupported operations
    """
    if not logic or logic.strip() == "default":
        return True

    logic = logic.strip()

    # Tokenize the condition into field references, operators, and literals
    # Parse expressions like: state.field > 0.5 and state.other == "yes"

    # First, normalize state.field references to just field names
    # Replace "state.field_name" with placeholders
    field_pattern = r"\bstate\.(\w+)\b"

    # Find all state field references
    field_refs = list(re.finditer(field_pattern, logic))

    if not field_refs:
        # No state references - might be a simple literal check
        # For now, reject expressions without state references
        raise ControlFlowError(
            f"Condition must reference state fields: {logic}",
        )

    # Check for dangerous patterns (function calls, imports, etc.)
    dangerous_patterns = [
        r"\(",  # Function calls (though we allow parentheses for grouping)
        r"\)",
        r"__",
        r"import",
        r"exec",
        r"eval",
        r"lambda",
    ]

    # We'll allow parentheses for grouping but check for other dangerous patterns
    for pattern in [r"__", r"import", r"exec", r"eval", r"lambda"]:
        if re.search(pattern, logic, re.IGNORECASE):
            raise ControlFlowError(
                f"Unsupported expression in condition: {logic}",
            )

    # Parse and evaluate the condition
    try:
        result = _parse_and_evaluate_condition(logic, state)
        return bool(result)
    except Exception as e:
        raise ControlFlowError(f"Failed to evaluate condition '{logic}': {e}") from e


def _parse_and_evaluate_condition(logic: str, state: Dict[str, Any]) -> bool:
    """
    Parse and evaluate a condition using AST walking.

    This is safer than eval() as we control exactly what operations are allowed.
    """
    # Check for compound expressions FIRST (before single comparison)
    # Pattern 1: Compound expression with 'and'
    # Split by ' and ' (but not inside parentheses or strings)
    if " and " in logic and "(" not in logic:
        parts = logic.split(" and ")
        results = []
        for part in parts:
            part = part.strip()
            # Recursively evaluate each part - each part is a full expression
            results.append(_parse_and_evaluate_condition(part, state))
        return all(results)

    # Pattern 2: Compound expression with 'or'
    if " or " in logic and "(" not in logic:
        parts = logic.split(" or ")
        results = []
        for part in parts:
            part = part.strip()
            # Recursively evaluate each part - each part is a full expression
            results.append(_parse_and_evaluate_condition(part, state))
        return any(results)

    # Pattern 3: Single comparison: state.field OP value
    # Use non-greedy matching to avoid matching compound expressions
    single_comparison = re.match(
        r"^state\.(\w+)\s*(==|!=|>=|<=|>|<)\s*([^']+)$", logic.strip()
    )
    if not single_comparison:
        # Try matching with quoted string values
        single_comparison = re.match(
            r'^state\.(\w+)\s*(==|!=|>=|<=|>|<)\s*"([^"]*)"$', logic.strip()
        )
    if not single_comparison:
        # Try matching with single-quoted string values
        single_comparison = re.match(
            r"^state\.(\w+)\s*(==|!=|>=|<=|>|<)\s*'([^']*)'$", logic.strip()
        )

    if single_comparison:
        field_name, op, value_str = single_comparison.groups()
        if field_name not in state:
            # Field doesn't exist in state
            return False
        field_value = state[field_name]
        return _apply_comparison(field_value, op, _parse_value(value_str))

    # Pattern 4: Boolean check: state.field or not state.field (MUST come before field_only_check)
    boolean_check = re.match(r"^(not\s+)?state\.(\w+)$", logic.strip())
    if boolean_check:
        negation, field_name = boolean_check.groups()
        if field_name not in state:
            return False
        value = bool(state[field_name])
        return not value if negation else value

    # Pattern 5: Boolean check without state prefix (from compound expressions)
    # Only if it looks like a simple field name AND has no operators
    has_operators = any(op in logic for op in ["==", "!=", ">=", "<=", ">", "<"])
    field_only_check = re.match(r"^(not\s+)?(\w+)$", logic.strip())
    if field_only_check and not has_operators:
        negation, field_name = field_only_check.groups()
        if field_name in state:
            value = bool(state[field_name])
            return not value if negation else value

    # Pattern 6: Parenthesized expression - simple case with one comparison
    if logic.startswith("(") and logic.endswith(")"):
        inner = logic[1:-1].strip()
        return _parse_and_evaluate_condition(inner, state)

    # If we get here, the expression is not supported
    raise ControlFlowError(f"Unsupported condition expression: {logic}")


def _apply_comparison(left: Any, op: str, right: Any) -> bool:
    """Apply a comparison operator."""
    ops = {
        "==": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
    }
    if op not in ops:
        raise ControlFlowError(f"Unknown operator: {op}")
    return ops[op](left, right)


def _parse_value(value_str: str) -> Any:
    """Parse a value string to its Python type."""
    value_str = value_str.strip()

    # Remove quotes for strings
    if (value_str.startswith('"') and value_str.endswith('"')) or (
        value_str.startswith("'") and value_str.endswith("'")
    ):
        return value_str[1:-1]

    # Try to parse as number
    try:
        if "." in value_str:
            return float(value_str)
        return int(value_str)
    except ValueError:
        pass

    # Boolean
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False

    # Return as string
    return value_str


def create_routing_function(
    routes: List[Route], state_fields: Dict[str, Any]
) -> Callable:
    """
    Create a routing function that evaluates conditions and returns target node.

    Args:
        routes: List of Route objects with conditions and targets
        state_fields: Dictionary mapping state field names to types (for validation)

    Returns:
        Function that takes state and returns the target node name or END

    The returned function:
    - Evaluates each route condition in order
    - Returns the first matching route's target
    - Returns the default route if no conditions match
    - Raises ControlFlowError if no default route exists
    """
    # Validate: at least one route should have logic="default"
    has_default = any(route.condition.logic == "default" for route in routes)
    if not has_default:
        raise ControlFlowError("Routes must include a default route (logic='default')")

    def routing_fn(state):
        """Evaluate conditions and return target node."""
        # Convert state to dict if it's a Pydantic model
        if hasattr(state, "model_dump"):
            state_dict = state.model_dump()
        elif hasattr(state, "dict"):
            state_dict = state.dict()
        else:
            state_dict = dict(state)

        # Try each route in order
        for route in routes:
            if route.condition.logic == "default":
                # Save default for later, continue checking other conditions
                default_target = route.to
                continue

            try:
                if _evaluate_condition(route.condition.logic, state_dict):
                    target = route.to if route.to != "END" else END
                    return target
            except ControlFlowError:
                # Skip failed condition evaluation, continue to next
                continue

        # No condition matched, use default
        target = default_target if default_target != "END" else END
        return target

    return routing_fn


def create_loop_router(loop_config: LoopConfig, from_node: str) -> Callable:
    """
    Create a routing function for loop edges.

    The loop function:
    - Tracks iteration count in state (as _loop_iteration_{node})
    - Checks loop condition field
    - Returns to the from_node if condition not met and iterations < max
    - Returns exit_to when condition is met or max_iterations reached

    Args:
        loop_config: Loop configuration
        from_node: Node that loops back to itself

    Returns:
        Function that takes state and returns the next target node
    """
    iteration_key = f"_loop_iteration_{from_node}"

    def loop_fn(state):
        """Determine whether to continue looping or exit."""
        # Convert state to dict if it's a Pydantic model
        if hasattr(state, "model_dump"):
            state_dict = state.model_dump()
        elif hasattr(state, "dict"):
            state_dict = state.dict()
        else:
            state_dict = dict(state)

        # Get current iteration count
        iteration = state_dict.get(iteration_key, 0)

        # Check loop condition
        condition_met = state_dict.get(loop_config.condition_field, False)

        # Exit if condition met or max iterations reached
        if condition_met or iteration >= loop_config.max_iterations:
            target = loop_config.exit_to if loop_config.exit_to != "END" else END
            return target

        # Continue looping
        return from_node

    return loop_fn


def get_loop_iteration_key(from_node: str) -> str:
    """Get the state key for tracking loop iterations."""
    return f"_loop_iteration_{from_node}"


def increment_loop_iteration(state: Dict[str, Any], from_node: str) -> int:
    """
    Increment the loop iteration counter for a node.

    Args:
        state: Current state dictionary
        from_node: Node name

    Returns:
        New iteration count
    """
    iteration_key = get_loop_iteration_key(from_node)
    iteration = state.get(iteration_key, 0) + 1
    state[iteration_key] = iteration
    return iteration
