"""Tool registry for loading and managing tools by name.

This module provides a centralized registry for tools that can be referenced
by name in workflow configurations. Tools are loaded lazily on demand.

Example:
    >>> from configurable_agents.tools import get_tool, list_tools
    >>> tool = get_tool("serper_search")
    >>> tools = list_tools()
"""

import os
from typing import Callable, Dict

from langchain_core.tools import BaseTool


class ToolNotFoundError(Exception):
    """Raised when a requested tool is not found in the registry."""

    def __init__(self, tool_name: str, available_tools: list[str]):
        self.tool_name = tool_name
        self.available_tools = available_tools
        message = (
            f"Tool '{tool_name}' not found in registry.\n"
            f"Available tools: {', '.join(available_tools)}\n\n"
            f"Suggestion: Check the tool name for typos. "
            f"Tools are case-sensitive."
        )
        super().__init__(message)


class ToolConfigError(Exception):
    """Raised when a tool cannot be configured (e.g., missing API key)."""

    def __init__(self, tool_name: str, reason: str, env_var: str = None):
        self.tool_name = tool_name
        self.reason = reason
        self.env_var = env_var
        message = f"Tool '{tool_name}' configuration failed: {reason}"
        if env_var:
            message += f"\n\nSet the environment variable: {env_var}"
            message += f"\nExample: export {env_var}=your-api-key-here"
        super().__init__(message)


# Type alias for tool factory functions
ToolFactory = Callable[[], BaseTool]


class ToolRegistry:
    """Registry for managing and loading tools by name.

    Tools are registered as factory functions that create tool instances
    on demand. This allows lazy loading and validation of configuration
    (e.g., API keys) only when a tool is actually used.
    """

    def __init__(self):
        self._factories: Dict[str, ToolFactory] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register all built-in tools available in v0.2."""
        # Import here to avoid circular dependencies
        from configurable_agents.tools.serper import create_serper_search

        self._factories["serper_search"] = create_serper_search

        # Register web tools
        from configurable_agents.tools.web_tools import (
            register_tools as register_web_tools,
        )
        register_web_tools(self)

        # Register file tools
        from configurable_agents.tools.file_tools import (
            register_tools as register_file_tools,
        )
        register_file_tools(self)

        # Register data tools
        from configurable_agents.tools.data_tools import (
            register_tools as register_data_tools,
        )
        register_data_tools(self)

        # Register system tools
        from configurable_agents.tools.system_tools import (
            register_tools as register_system_tools,
        )
        register_system_tools(self)

    def register_tool(self, name: str, factory: ToolFactory):
        """Register a tool factory function.

        Args:
            name: Unique name for the tool (used in configs)
            factory: Callable that creates and returns a BaseTool instance

        Raises:
            ValueError: If tool name already registered
        """
        if name in self._factories:
            raise ValueError(f"Tool '{name}' is already registered")
        self._factories[name] = factory

    def get_tool(self, name: str) -> BaseTool:
        """Get a tool instance by name.

        Args:
            name: Name of the tool to retrieve

        Returns:
            BaseTool instance ready to use

        Raises:
            ToolNotFoundError: If tool name not found in registry
            ToolConfigError: If tool configuration fails (e.g., missing API key)
        """
        if name not in self._factories:
            raise ToolNotFoundError(name, self.list_tools())

        try:
            return self._factories[name]()
        except Exception as e:
            # Re-raise ToolConfigError as-is
            if isinstance(e, ToolConfigError):
                raise
            # Wrap other exceptions
            raise ToolConfigError(name, str(e)) from e

    def list_tools(self) -> list[str]:
        """List all available tool names.

        Returns:
            Sorted list of tool names that can be used in configs
        """
        return sorted(self._factories.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: Tool name to check

        Returns:
            True if tool is registered, False otherwise
        """
        return name in self._factories


# Global registry instance
_global_registry = ToolRegistry()


# Public API functions
def get_tool(name: str) -> BaseTool:
    """Get a tool instance by name from the global registry.

    This is a convenience function that uses the global registry instance.

    Args:
        name: Name of the tool to retrieve

    Returns:
        BaseTool instance ready to use

    Raises:
        ToolNotFoundError: If tool name not found
        ToolConfigError: If tool configuration fails

    Example:
        >>> tool = get_tool("serper_search")
        >>> result = tool.run("Python programming")
    """
    return _global_registry.get_tool(name)


def list_tools() -> list[str]:
    """List all available tool names.

    Returns:
        Sorted list of tool names that can be used in configs

    Example:
        >>> tools = list_tools()
        >>> print(tools)
        ['serper_search']
    """
    return _global_registry.list_tools()


def register_tool(name: str, factory: ToolFactory):
    """Register a custom tool in the global registry.

    This allows users to extend the registry with their own tools.

    Args:
        name: Unique name for the tool
        factory: Callable that creates and returns a BaseTool instance

    Raises:
        ValueError: If tool name already registered

    Example:
        >>> def create_my_tool():
        ...     return MyCustomTool()
        >>> register_tool("my_tool", create_my_tool)
    """
    _global_registry.register_tool(name, factory)


def has_tool(name: str) -> bool:
    """Check if a tool is registered in the global registry.

    Args:
        name: Tool name to check

    Returns:
        True if tool is registered, False otherwise

    Example:
        >>> has_tool("serper_search")
        True
        >>> has_tool("unknown_tool")
        False
    """
    return _global_registry.has_tool(name)
