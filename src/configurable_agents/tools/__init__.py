"""Tool registry and implementations.

This module provides a centralized registry for tools that can be used
in workflow configurations. Tools are loaded by name and configured
automatically from environment variables.

Available tools in v0.1:
- serper_search: Web search using Google Search via Serper API

Example:
    >>> from configurable_agents.tools import get_tool, list_tools
    >>> # List all available tools
    >>> print(list_tools())
    ['serper_search']
    >>> # Get a specific tool
    >>> search = get_tool("serper_search")
    >>> results = search.run("Python programming")
"""

from configurable_agents.tools.registry import (
    ToolConfigError,
    ToolNotFoundError,
    ToolRegistry,
    get_tool,
    has_tool,
    list_tools,
    register_tool,
)

__all__ = [
    # Main API
    "get_tool",
    "list_tools",
    "has_tool",
    "register_tool",
    # Classes
    "ToolRegistry",
    # Exceptions
    "ToolNotFoundError",
    "ToolConfigError",
]
