"""
Dynamic Pydantic state model builder from config.

Generates runtime Pydantic BaseModel classes from StateSchema configs,
supporting all type system types including nested objects.

LangGraph Compatibility:
    All state fields are wrapped with Annotated types and reducer functions
    to support concurrent updates from conditional branches, loops, and
    parallel execution. Without reducers, LangGraph throws:
    "Can receive only one value per step. Use an Annotated key to handle multiple values."
"""

import operator
from typing import Annotated, Any, Callable, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, create_model

from configurable_agents.config.schema import StateFieldConfig, StateSchema
from configurable_agents.config.types import get_python_type


# ============================================================
# LangGraph Reducer Functions
# ============================================================
# These reducers tell LangGraph how to handle concurrent updates
# to state fields from parallel branches, conditionals, or loops.

def _last_value_reducer(current: Any, new: Any) -> Any:
    """
    'Last writer wins' reducer - returns the new value, discarding current.

    Used for scalar types (str, int, float, bool) where we simply want
    the most recent value.
    """
    return new


def _list_concat_reducer(current: List, new: Union[List, Any]) -> List:
    """
    List concatenation reducer - appends new items to current list.

    Used for list types where concurrent updates should be merged.
    If new is a single item, wraps it in a list before concatenating.
    """
    if current is None:
        current = []
    if new is None:
        return current
    if isinstance(new, list):
        return current + new
    return current + [new]


def _get_reducer_for_type(python_type: Type) -> Callable:
    """
    Get the appropriate reducer function for a Python type.

    Args:
        python_type: The Python type of the field

    Returns:
        Reducer function for LangGraph Annotated wrapper
    """
    # Check if it's a list type
    origin = getattr(python_type, '__origin__', None)
    if origin is list or python_type is list:
        return _list_concat_reducer

    # Default: last writer wins for all other types
    return _last_value_reducer


class StateBuilderError(Exception):
    """Raised when state model building fails."""

    pass


def build_state_model(state_config: StateSchema) -> Type[BaseModel]:
    """
    Build dynamic Pydantic model from state config.

    Args:
        state_config: State schema configuration

    Returns:
        Pydantic BaseModel class for the state

    Raises:
        StateBuilderError: If model building fails

    Example:
        >>> from configurable_agents.config import StateSchema, StateFieldConfig
        >>> state_config = StateSchema(fields={
        ...     "topic": StateFieldConfig(type="str", required=True),
        ...     "score": StateFieldConfig(type="int", default=0),
        ... })
        >>> StateModel = build_state_model(state_config)
        >>> state = StateModel(topic="AI Safety")
        >>> state.topic
        'AI Safety'
        >>> state.score
        0
    """
    # Sanity check (should be caught by validator already)
    if not state_config.fields:
        raise StateBuilderError("State must have at least one field")

    # Build field definitions for Pydantic
    field_definitions: Dict[str, Any] = {}

    for field_name, field_config in state_config.fields.items():
        try:
            field_definitions[field_name] = _create_field_definition(
                field_name, field_config
            )
        except Exception as e:
            raise StateBuilderError(
                f"Failed to create field '{field_name}': {e}"
            ) from e

    # Create Pydantic model
    try:
        return create_model("WorkflowState", **field_definitions)
    except Exception as e:
        raise StateBuilderError(f"Failed to create state model: {e}") from e


def _create_field_definition(
    field_name: str, field_config: StateFieldConfig
) -> tuple[Type, Any]:
    """
    Create Pydantic field definition (type, Field(...)) tuple.

    All fields are wrapped with Annotated[type, reducer] for LangGraph
    compatibility with concurrent updates from conditionals/loops/parallel.

    Args:
        field_name: Name of the field
        field_config: Field configuration

    Returns:
        Tuple of (Annotated[type, reducer], Field) for Pydantic create_model
    """
    # Get the Python type for this field
    field_type = _get_field_type(field_name, field_config)

    # Get appropriate reducer for this type
    reducer = _get_reducer_for_type(field_type)

    # Build Pydantic Field with description
    field_kwargs = {}
    if field_config.description:
        field_kwargs["description"] = field_config.description

    # Handle required vs optional vs default
    # Wrap with Annotated for LangGraph reducer support
    if field_config.required:
        # Required field - must be provided
        annotated_type = Annotated[field_type, reducer]
        return (annotated_type, Field(..., **field_kwargs))
    elif field_config.default is not None:
        # Has default value
        annotated_type = Annotated[field_type, reducer]
        return (annotated_type, Field(default=field_config.default, **field_kwargs))
    else:
        # Optional field (not required, no default) - defaults to None
        annotated_type = Annotated[Optional[field_type], reducer]
        return (annotated_type, Field(default=None, **field_kwargs))


def _get_field_type(field_name: str, field_config: StateFieldConfig) -> Type:
    """
    Get Python type for a field, handling nested objects recursively.

    Args:
        field_name: Name of the field (for nested model naming)
        field_config: Field configuration

    Returns:
        Python type for the field

    Raises:
        StateBuilderError: If type cannot be resolved
    """
    type_str = field_config.type

    # Handle nested object types
    if type_str == "object":
        if field_config.schema_ is None:
            raise StateBuilderError(
                f"Field '{field_name}' has type 'object' but no 'schema' defined"
            )
        if not field_config.schema_:  # Empty dict check
            raise StateBuilderError(
                f"Field '{field_name}' has type 'object' with empty schema"
            )
        return _build_nested_model(field_name, field_config.schema_)

    # Use type system for all other types
    try:
        return get_python_type(type_str)
    except Exception as e:
        raise StateBuilderError(
            f"Invalid type '{type_str}' for field '{field_name}': {e}"
        ) from e


def _build_nested_model(parent_name: str, schema_dict: Dict[str, Any]) -> Type[BaseModel]:
    """
    Recursively build nested Pydantic model from schema dict.

    Args:
        parent_name: Parent field name (for model naming)
        schema_dict: Dictionary mapping field names to type strings or configs

    Returns:
        Pydantic BaseModel class for the nested object

    Example schema_dict formats:
        Simple: {"name": "str", "age": "int"}
        Complex: {"field": {"type": "str", "required": true, "description": "..."}}
    """
    if not schema_dict:
        raise StateBuilderError(
            f"Nested object '{parent_name}' has empty schema"
        )

    # Build field definitions for nested model
    nested_fields: Dict[str, Any] = {}

    for field_name, field_spec in schema_dict.items():
        # Handle both simple type strings and full field configs
        if isinstance(field_spec, str):
            # Simple format: "name": "str"
            field_config = StateFieldConfig(type=field_spec)
        elif isinstance(field_spec, dict):
            # Full format: "name": {"type": "str", "required": true, ...}
            try:
                field_config = StateFieldConfig(**field_spec)
            except Exception as e:
                raise StateBuilderError(
                    f"Invalid field config for '{parent_name}.{field_name}': {e}"
                ) from e
        else:
            raise StateBuilderError(
                f"Invalid field spec for '{parent_name}.{field_name}': "
                f"expected string or dict, got {type(field_spec)}"
            )

        # Create field definition recursively
        nested_fields[field_name] = _create_field_definition(
            f"{parent_name}_{field_name}", field_config
        )

    # Create nested model with descriptive name
    model_name = f"WorkflowState_{parent_name}"
    try:
        return create_model(model_name, **nested_fields)
    except Exception as e:
        raise StateBuilderError(
            f"Failed to create nested model '{model_name}': {e}"
        ) from e
