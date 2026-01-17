"""
Tool Registry Module

This module maintains a registry of available tools that can be used by agents.
Only tools registered here can be referenced in configuration.
"""

from typing import Any, Dict
from crewai_tools import SerperDevTool


# Tool registry - maps tool names to tool instances
_TOOL_REGISTRY: Dict[str, Any] = {}


def register_default_tools():
    """Register default tools available to all agents."""
    # Register SerperDevTool for web search
    _TOOL_REGISTRY['serper_search'] = SerperDevTool()
    
    # Future: Add more tools here
    # _TOOL_REGISTRY['file_read'] = FileReadTool()
    # _TOOL_REGISTRY['scrape_website'] = ScrapeWebsiteTool()


def get_tool(tool_name: str) -> Any:
    """
    Get a tool instance by name.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Tool instance
        
    Raises:
        ValueError: If tool is not registered
    """
    if not _TOOL_REGISTRY:
        register_default_tools()
    
    if tool_name not in _TOOL_REGISTRY:
        raise ValueError(
            f"Tool '{tool_name}' not found in registry. "
            f"Available tools: {list(_TOOL_REGISTRY.keys())}"
        )
    
    return _TOOL_REGISTRY[tool_name]


def list_available_tools() -> list:
    """
    List all available tool names.
    
    Returns:
        List of tool names
    """
    if not _TOOL_REGISTRY:
        register_default_tools()
    
    return list(_TOOL_REGISTRY.keys())