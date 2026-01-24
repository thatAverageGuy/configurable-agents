"""
Type system for parsing and validating config type strings.

Supports:
- Basic types: str, int, float, bool
- Collection types: list, dict, list[T], dict[K, V]
- Nested object types: object (with schema)
"""

import re
from typing import Any, Dict, Optional, Type, Union

# Basic type mapping
BASIC_TYPES: Dict[str, Type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}

# Collection type names
COLLECTION_TYPES = {"list", "dict"}


class TypeParseError(Exception):
    """Raised when a type string cannot be parsed."""

    def __init__(self, type_string: str, message: str):
        self.type_string = type_string
        super().__init__(f"Invalid type '{type_string}': {message}")


def parse_type_string(type_str: str) -> Dict[str, Any]:
    """
    Parse a type string into a structured representation.

    Args:
        type_str: Type string (e.g., "str", "list[int]", "dict[str, int]", "object")

    Returns:
        Dict with parsed type information:
        - For basic types: {"kind": "basic", "type": <python_type>}
        - For list: {"kind": "list", "item_type": <parsed_type> or None}
        - For dict: {"kind": "dict", "key_type": <parsed_type> or None, "value_type": <parsed_type> or None}
        - For object: {"kind": "object"}

    Raises:
        TypeParseError: If type string is invalid
    """
    type_str = type_str.strip()

    if not type_str:
        raise TypeParseError(type_str, "Type string cannot be empty")

    # Check for basic types
    if type_str in BASIC_TYPES:
        return {"kind": "basic", "type": BASIC_TYPES[type_str], "name": type_str}

    # Check for object type
    if type_str == "object":
        return {"kind": "object", "name": "object"}

    # Check for generic list (no type parameter)
    if type_str == "list":
        return {"kind": "list", "item_type": None, "name": "list"}

    # Check for generic dict (no type parameters)
    if type_str == "dict":
        return {"kind": "dict", "key_type": None, "value_type": None, "name": "dict"}

    # Check for typed list: list[T]
    list_match = re.match(r"^list\[(.+)\]$", type_str)
    if list_match:
        item_type_str = list_match.group(1).strip()
        item_type = parse_type_string(item_type_str)
        return {"kind": "list", "item_type": item_type, "name": type_str}

    # Check for typed dict: dict[K, V]
    dict_match = re.match(r"^dict\[(.+),\s*(.+)\]$", type_str)
    if dict_match:
        key_type_str = dict_match.group(1).strip()
        value_type_str = dict_match.group(2).strip()

        key_type = parse_type_string(key_type_str)
        value_type = parse_type_string(value_type_str)

        return {
            "kind": "dict",
            "key_type": key_type,
            "value_type": value_type,
            "name": type_str,
        }

    # If we get here, type string is invalid
    raise TypeParseError(
        type_str,
        f"Unknown type. Supported: {', '.join(BASIC_TYPES.keys())}, list, dict, list[T], dict[K,V], object",
    )


def validate_type_string(type_str: str) -> bool:
    """
    Validate a type string without raising exceptions.

    Args:
        type_str: Type string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        parse_type_string(type_str)
        return True
    except TypeParseError:
        return False


def get_python_type(type_str: str) -> Type:
    """
    Convert a type string to a Python type.

    Args:
        type_str: Type string

    Returns:
        Python type

    Raises:
        TypeParseError: If type string is invalid or cannot be converted
    """
    parsed = parse_type_string(type_str)

    if parsed["kind"] == "basic":
        return parsed["type"]
    elif parsed["kind"] == "list":
        return list
    elif parsed["kind"] == "dict":
        return dict
    elif parsed["kind"] == "object":
        return dict  # Object types are represented as dicts
    else:
        raise TypeParseError(type_str, f"Cannot convert to Python type: {parsed}")
