"""
Dynamic Pydantic output model builder from config.

Generates runtime Pydantic BaseModel classes from OutputSchema configs,
enabling type-enforced LLM responses.
"""

from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field, create_model

from configurable_agents.config.schema import OutputSchema, OutputSchemaField
from configurable_agents.config.types import get_python_type


class OutputBuilderError(Exception):
    """Raised when output model building fails."""

    pass


def build_output_model(output_schema: OutputSchema, node_id: str) -> Type[BaseModel]:
    """
    Build dynamic Pydantic model from output schema.

    Args:
        output_schema: Output schema configuration
        node_id: Node identifier (for model naming and error messages)

    Returns:
        Pydantic BaseModel class for the output

    Raises:
        OutputBuilderError: If model building fails

    Example:
        >>> from configurable_agents.config import OutputSchema, OutputSchemaField
        >>> # Simple output
        >>> schema = OutputSchema(type="str", description="Article text")
        >>> OutputModel = build_output_model(schema, "write")
        >>> output = OutputModel(result="Hello world")
        >>> output.result
        'Hello world'
        >>>
        >>> # Object output
        >>> schema = OutputSchema(
        ...     type="object",
        ...     fields=[
        ...         OutputSchemaField(name="article", type="str"),
        ...         OutputSchemaField(name="word_count", type="int"),
        ...     ]
        ... )
        >>> OutputModel = build_output_model(schema, "write")
        >>> output = OutputModel(article="...", word_count=500)
        >>> output.article
        '...'
    """
    if not output_schema:
        raise OutputBuilderError(f"Node '{node_id}': output_schema is required")

    output_type = output_schema.type

    # Handle simple types (non-object)
    if output_type != "object":
        return _build_simple_output_model(output_schema, node_id)

    # Handle object types (multiple fields)
    return _build_object_output_model(output_schema, node_id)


def _build_simple_output_model(
    output_schema: OutputSchema, node_id: str
) -> Type[BaseModel]:
    """
    Build Pydantic model for simple (non-object) output.

    Simple outputs are wrapped in a single field called "result".

    Args:
        output_schema: Output schema with simple type
        node_id: Node identifier

    Returns:
        Pydantic BaseModel with single "result" field
    """
    type_str = output_schema.type

    # Get Python type
    try:
        field_type = get_python_type(type_str)
    except Exception as e:
        raise OutputBuilderError(
            f"Node '{node_id}': Invalid output type '{type_str}': {e}"
        ) from e

    # Create field with description
    field_kwargs = {}
    if output_schema.description:
        field_kwargs["description"] = output_schema.description

    # Build single-field model
    field_definitions = {
        "result": (field_type, Field(..., **field_kwargs))
    }

    model_name = f"Output_{node_id}"
    try:
        return create_model(model_name, **field_definitions)
    except Exception as e:
        raise OutputBuilderError(
            f"Node '{node_id}': Failed to create output model: {e}"
        ) from e


def _build_object_output_model(
    output_schema: OutputSchema, node_id: str
) -> Type[BaseModel]:
    """
    Build Pydantic model for object output (multiple fields).

    Args:
        output_schema: Output schema with type='object'
        node_id: Node identifier

    Returns:
        Pydantic BaseModel with fields from schema
    """
    # Sanity check (should be caught by OutputSchema validator)
    if not output_schema.fields:
        raise OutputBuilderError(
            f"Node '{node_id}': Output schema with type='object' must have fields"
        )

    # Build field definitions
    field_definitions: Dict[str, Any] = {}

    for field_spec in output_schema.fields:
        try:
            field_definitions[field_spec.name] = _create_output_field_definition(
                field_spec, node_id
            )
        except Exception as e:
            raise OutputBuilderError(
                f"Node '{node_id}': Failed to create field '{field_spec.name}': {e}"
            ) from e

    # Create model
    model_name = f"Output_{node_id}"
    try:
        return create_model(model_name, **field_definitions)
    except Exception as e:
        raise OutputBuilderError(
            f"Node '{node_id}': Failed to create output model: {e}"
        ) from e


def _create_output_field_definition(
    field_spec: OutputSchemaField, node_id: str
) -> tuple[Type, Any]:
    """
    Create Pydantic field definition for an output field.

    Args:
        field_spec: Output field specification
        node_id: Node identifier (for error messages)

    Returns:
        Tuple of (type, Field) for Pydantic create_model
    """
    field_name = field_spec.name
    type_str = field_spec.type

    # Get Python type (handles nested objects recursively)
    field_type = _get_output_field_type(field_spec, node_id)

    # Build Pydantic Field with description
    field_kwargs = {}
    if field_spec.description:
        field_kwargs["description"] = field_spec.description

    # All output fields are required (LLM must provide them)
    return (field_type, Field(..., **field_kwargs))


def _get_output_field_type(
    field_spec: OutputSchemaField, node_id: str
) -> Type:
    """
    Get Python type for an output field, handling nested objects.

    Note: For now, we don't support nested objects in output schemas.
    This can be added in future versions if needed.

    Args:
        field_spec: Output field specification
        node_id: Node identifier

    Returns:
        Python type for the field
    """
    type_str = field_spec.type

    # Handle nested objects (future enhancement)
    if type_str == "object":
        raise OutputBuilderError(
            f"Node '{node_id}': Nested objects in output schema not yet supported. "
            f"Field '{field_spec.name}' has type 'object'. "
            f"Use basic types, lists, or dicts instead."
        )

    # Use type system for all other types
    try:
        return get_python_type(type_str)
    except Exception as e:
        raise OutputBuilderError(
            f"Node '{node_id}': Invalid type '{type_str}' for field '{field_spec.name}': {e}"
        ) from e
