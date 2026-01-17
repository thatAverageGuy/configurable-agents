"""
Utility functions for configurable agents.

Handles template resolution, state management helpers, and other utilities.
"""

import re
from typing import Any
from pydantic import BaseModel


def resolve_template(template: str, state: BaseModel) -> Any:
    """
    Resolve template strings with state values.
    
    Supports patterns like:
    - {state.custom_var.company_name}
    - {state.execution_id}
    
    Args:
        template: Template string with placeholders
        state: State object containing values
        
    Returns:
        Resolved value (string or original type)
    """
    if not isinstance(template, str):
        return template
    
    # Pattern to match {state.path.to.value}
    pattern = r'\{state\.([\w\.]+)\}'
    
    def replace_match(match):
        path = match.group(1)
        return str(get_nested_value(state, path))
    
    # Check if entire string is a single template
    if re.fullmatch(pattern, template):
        # Return the actual value, not string
        path = re.match(pattern, template).group(1)
        return get_nested_value(state, path)
    
    # Otherwise, do string replacement
    resolved = re.sub(pattern, replace_match, template)
    return resolved


def get_nested_value(obj: Any, path: str) -> Any:
    """
    Get a nested value from an object using dot notation.
    
    Example: "custom_var.company_name" gets obj.custom_var['company_name']
    
    Args:
        obj: Object to navigate
        path: Dot-separated path
        
    Returns:
        Value at the path
        
    Raises:
        ValueError: If path cannot be resolved
    """
    parts = path.split('.')
    current = obj
    
    for part in parts:
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise ValueError(f"Cannot resolve path '{path}' - '{part}' not found")
    
    return current


def set_nested_value(obj: Any, path: str, value: Any) -> None:
    """
    Set a nested value in an object using dot notation.
    
    Example: "custom_var.result" sets obj.custom_var['result'] = value
    
    Args:
        obj: Object to modify
        path: Dot-separated path
        value: Value to set
    """
    parts = path.split('.')
    current = obj
    
    # Navigate to parent
    for part in parts[:-1]:
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict):
            if part not in current:
                current[part] = {}
            current = current[part]
        else:
            raise ValueError(f"Cannot navigate to '{part}' in path '{path}'")
    
    # Set final value
    final_key = parts[-1]
    if isinstance(current, dict):
        current[final_key] = value
    elif hasattr(current, final_key):
        setattr(current, final_key, value)
    else:
        raise ValueError(f"Cannot set '{final_key}' in path '{path}'")