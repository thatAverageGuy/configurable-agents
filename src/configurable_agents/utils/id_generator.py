"""
Utilities Module

Common utility functions used across the application.
"""

import re
from typing import List
from uuid import uuid4


def generate_unique_id(base_name: str, existing_ids: List[str]) -> str:
    """
    Generate a unique ID by appending numbers if needed.
    
    Args:
        base_name: Base name for the ID (e.g., 'new_agent')
        existing_ids: List of existing IDs to check against
        
    Returns:
        Unique ID string
        
    Example:
        >>> generate_unique_id('agent', ['agent', 'agent_1'])
        'agent_2'
    """
    # Sanitize base name (replace spaces with underscores, remove special chars)
    base_name = re.sub(r'[^a-zA-Z0-9_]', '_', base_name.lower())
    base_name = re.sub(r'_+', '_', base_name).strip('_')
    
    if not base_name:
        base_name = 'item'
    
    # If base name is unique, return it
    if base_name not in existing_ids:
        return base_name
    
    # Otherwise, append number
    counter = 1
    while f"{base_name}_{counter}" in existing_ids:
        counter += 1
    
    return f"{base_name}_{counter}"


def generate_execution_id() -> str:
    """
    Generate a unique execution ID.
    
    Returns:
        UUID string for execution tracking
        
    Example:
        >>> execution_id = generate_execution_id()
        >>> print(execution_id)
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
    """
    return str(uuid4())


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to be filesystem-safe.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
        
    Example:
        >>> sanitize_filename("My Config: Version 2")
        'my_config_version_2'
    """
    # Convert to lowercase
    filename = filename.lower()
    
    # Replace spaces and special chars with underscores
    filename = re.sub(r'[^a-z0-9_\-.]', '_', filename)
    
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing underscores
    filename = filename.strip('_')
    
    return filename or 'untitled'


def format_timestamp(timestamp: str, format: str = "display") -> str:
    """
    Format ISO timestamp for display.
    
    Args:
        timestamp: ISO format timestamp
        format: Output format ('display', 'short', 'date')
        
    Returns:
        Formatted timestamp string
    """
    from datetime import datetime
    
    try:
        dt = datetime.fromisoformat(timestamp)
        
        if format == "display":
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        elif format == "short":
            return dt.strftime("%m/%d %H:%M")
        elif format == "date":
            return dt.strftime("%Y-%m-%d")
        else:
            return timestamp
    except (ValueError, AttributeError):
        return timestamp


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to append if truncated
        
    Returns:
        Truncated text
        
    Example:
        >>> truncate_text("This is a very long text", max_length=15)
        'This is a ve...'
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def parse_key_value_text(text: str) -> dict:
    """
    Parse key-value pairs from text.
    
    Format: "key: value" or "key = value", one per line
    
    Args:
        text: Text with key-value pairs
        
    Returns:
        Dictionary of parsed values
        
    Example:
        >>> parse_key_value_text("name: John\\nage: 30")
        {'name': 'John', 'age': '30'}
    """
    result = {}
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Try colon separator
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()
        # Try equals separator
        elif '=' in line:
            key, value = line.split('=', 1)
            result[key.strip()] = value.strip()
    
    return result