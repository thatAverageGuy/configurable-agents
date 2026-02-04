"""
Prompt template resolution for node prompts.

Resolves {variable} placeholders from input mappings and state.
"""

import re
from typing import Any, Dict, Set
from pydantic import BaseModel


class TemplateResolutionError(Exception):
    """Error resolving template variables."""

    def __init__(
        self,
        message: str,
        variable: str = None,
        suggestion: str = None,
    ):
        super().__init__(message)
        self.variable = variable
        self.suggestion = suggestion


def resolve_prompt(
    prompt_template: str,
    inputs: Dict[str, Any],
    state: BaseModel,
) -> str:
    """
    Resolve {variable} placeholders in prompt template.

    Resolution order:
    1. Check inputs dict (node-level mappings)
    2. Check state fields (workflow state)

    Supports nested access: {metadata.author}

    Args:
        prompt_template: Template string with {variable} placeholders
        inputs: Input mappings from node config (overrides state)
        state: Workflow state (Pydantic model)

    Returns:
        Resolved prompt string

    Raises:
        TemplateResolutionError: If variable cannot be resolved

    Examples:
        >>> resolve_prompt("Hello {name}", {"name": "Alice"}, state)
        "Hello Alice"

        >>> resolve_prompt("Topic: {topic}", {}, state)
        "Topic: AI Safety"  # from state.topic

        >>> resolve_prompt("Author: {metadata.author}", {}, state)
        "Author: Bob"  # nested state access
    """
    if not prompt_template:
        return ""

    # Extract all variable references
    variables = extract_variables(prompt_template)

    # Resolve each variable
    resolved = prompt_template
    for var in variables:
        value = resolve_variable(var, inputs, state)
        # Replace {variable} with resolved value
        resolved = resolved.replace(f"{{{var}}}", str(value))

    return resolved


def extract_variables(template: str) -> Set[str]:
    """
    Extract all {variable} references from template.

    Args:
        template: Template string

    Returns:
        Set of variable names (without braces)

    Examples:
        >>> extract_variables("Hello {name}, topic: {topic}")
        {"name", "topic"}

        >>> extract_variables("Author: {metadata.author}")
        {"metadata.author"}
    """
    # Match {variable} patterns, including nested: {a.b.c}
    pattern = r"\{([a-zA-Z_][a-zA-Z0-9_\.]*)\}"
    matches = re.findall(pattern, template)
    return set(matches)


def resolve_variable(
    variable: str,
    inputs: Dict[str, Any],
    state: BaseModel,
) -> Any:
    """
    Resolve a single variable from inputs or state.

    Resolution order:
    1. Check inputs dict
    2. Check state fields (supports nested access)

    Args:
        variable: Variable name (may include dots for nested access)
        inputs: Input mappings dict
        state: Workflow state

    Returns:
        Resolved value

    Raises:
        TemplateResolutionError: If variable not found

    Examples:
        >>> resolve_variable("topic", {"topic": "AI"}, state)
        "AI"

        >>> resolve_variable("topic", {}, state)
        # Returns state.topic

        >>> resolve_variable("metadata.author", {}, state)
        # Returns state.metadata.author
    """
    # First check inputs (overrides state)
    if variable in inputs:
        return inputs[variable]

    # Then check state (supports nested access)
    try:
        value = get_nested_value(state, variable)
        return value
    except (AttributeError, KeyError, TypeError) as e:
        # Variable not found - build helpful error
        available_inputs = list(inputs.keys())
        available_state = list(state.model_fields.keys())

        # Try to suggest similar variable
        suggestion = _suggest_variable(variable, available_inputs, available_state)

        message = f"Variable '{variable}' not found in inputs or state"
        if suggestion:
            message += f"\nSuggestion: Did you mean '{suggestion}'?"
        message += f"\nAvailable inputs: {available_inputs}"
        message += f"\nAvailable state fields: {available_state}"

        raise TemplateResolutionError(
            message=message,
            variable=variable,
            suggestion=suggestion,
        )


def get_nested_value(obj: Any, path: str) -> Any:
    """
    Get nested value from object using dot notation.

    Args:
        obj: Object to access (BaseModel or dict)
        path: Dot-separated path (e.g., "metadata.author")

    Returns:
        Nested value

    Raises:
        AttributeError: If path not found

    Examples:
        >>> get_nested_value(state, "topic")
        "AI Safety"

        >>> get_nested_value(state, "metadata.author")
        "Alice"
    """
    parts = path.split(".")
    current = obj

    for i, part in enumerate(parts):
        if isinstance(current, BaseModel):
            # Access Pydantic model field
            if not hasattr(current, part):
                partial_path = ".".join(parts[: i + 1])
                raise AttributeError(
                    f"State has no field '{part}' (accessing '{partial_path}')"
                )
            current = getattr(current, part)
        elif isinstance(current, dict):
            # Access dict key
            if part not in current:
                partial_path = ".".join(parts[: i + 1])
                raise KeyError(
                    f"Dict has no key '{part}' (accessing '{partial_path}')"
                )
            current = current[part]
        else:
            # Cannot access further
            partial_path = ".".join(parts[: i + 1])
            raise TypeError(
                f"Cannot access '{part}' on {type(current).__name__} "
                f"(accessing '{partial_path}')"
            )

    return current


def _suggest_variable(
    variable: str,
    available_inputs: list[str],
    available_state: list[str],
) -> str | None:
    """
    Suggest a similar variable name using edit distance.

    Args:
        variable: Variable that was not found
        available_inputs: Available input variables
        available_state: Available state fields

    Returns:
        Suggested variable name, or None if no close match

    Examples:
        >>> _suggest_variable("topik", ["topic", "author"], [])
        "topic"
    """
    all_available = available_inputs + available_state

    if not all_available:
        return None

    # Simple edit distance for suggestions
    best_match = None
    best_distance = float("inf")

    for candidate in all_available:
        distance = _edit_distance(variable.lower(), candidate.lower())
        if distance < best_distance and distance <= 2:  # Max 2 edits
            best_distance = distance
            best_match = candidate

    return best_match


def _edit_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein edit distance between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Edit distance (number of single-character edits)
    """
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]
