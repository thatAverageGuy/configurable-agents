"""Serper web search tool implementation.

Serper (https://serper.dev) provides Google Search API access.
Requires SERPER_API_KEY environment variable to be set.

Example:
    >>> from configurable_agents.tools import get_tool
    >>> search = get_tool("serper_search")
    >>> results = search.run("Python programming best practices")
"""

import os

from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools import Tool

from configurable_agents.tools.registry import ToolConfigError


def create_serper_search() -> Tool:
    """Create a Serper web search tool instance.

    This factory function checks for the required SERPER_API_KEY environment
    variable and creates a configured search tool.

    Returns:
        Tool: LangChain Tool instance wrapping Serper search

    Raises:
        ToolConfigError: If SERPER_API_KEY environment variable is not set

    Example:
        >>> # Set API key first
        >>> import os
        >>> os.environ["SERPER_API_KEY"] = "your-key-here"
        >>> tool = create_serper_search()
        >>> result = tool.run("latest AI news")
    """
    # Check for API key
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ToolConfigError(
            tool_name="serper_search",
            reason="SERPER_API_KEY environment variable not set",
            env_var="SERPER_API_KEY",
        )

    # Create Serper wrapper
    try:
        search = GoogleSerperAPIWrapper(serper_api_key=api_key)
    except Exception as e:
        raise ToolConfigError(
            tool_name="serper_search",
            reason=f"Failed to initialize Serper API: {e}",
            env_var="SERPER_API_KEY",
        ) from e

    # Wrap in LangChain Tool
    tool = Tool(
        name="serper_search",
        description=(
            "Search the web using Google Search via Serper API. "
            "Useful for finding current information, news, articles, "
            "and general web content. Input should be a search query string."
        ),
        func=search.run,
    )

    return tool


def validate_serper_config() -> bool:
    """Validate that Serper is properly configured.

    Checks if SERPER_API_KEY environment variable is set.
    Does not validate the key itself (no API call).

    Returns:
        True if configuration is valid, False otherwise

    Example:
        >>> import os
        >>> os.environ["SERPER_API_KEY"] = "test-key"
        >>> validate_serper_config()
        True
        >>> del os.environ["SERPER_API_KEY"]
        >>> validate_serper_config()
        False
    """
    return bool(os.getenv("SERPER_API_KEY"))
