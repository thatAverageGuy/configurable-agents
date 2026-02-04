"""Tests for tool registry functionality.

Tests cover:
- Tool registration and retrieval
- Error handling (tool not found, missing API keys)
- Listing available tools
- Custom tool registration
"""

import os
from unittest.mock import Mock, patch

import pytest
from langchain_core.tools import BaseTool, Tool

from configurable_agents.tools import (
    ToolConfigError,
    ToolNotFoundError,
    ToolRegistry,
    get_tool,
    has_tool,
    list_tools,
    register_tool,
)


class TestToolRegistry:
    """Test ToolRegistry class functionality."""

    def test_registry_initialization(self):
        """Test that registry initializes with built-in tools."""
        registry = ToolRegistry()
        tools = registry.list_tools()
        assert "serper_search" in tools
        assert len(tools) > 0

    def test_list_tools_returns_sorted(self):
        """Test that list_tools returns sorted tool names."""
        registry = ToolRegistry()
        tools = registry.list_tools()
        assert tools == sorted(tools)

    def test_has_tool_positive(self):
        """Test has_tool returns True for existing tools."""
        registry = ToolRegistry()
        assert registry.has_tool("serper_search") is True

    def test_has_tool_negative(self):
        """Test has_tool returns False for non-existent tools."""
        registry = ToolRegistry()
        assert registry.has_tool("nonexistent_tool") is False

    def test_register_custom_tool(self):
        """Test registering a custom tool."""
        registry = ToolRegistry()

        def create_custom_tool():
            return Tool(name="custom", description="Custom tool", func=lambda x: x)

        registry.register_tool("custom_tool", create_custom_tool)
        assert registry.has_tool("custom_tool")
        assert "custom_tool" in registry.list_tools()

    def test_register_duplicate_tool_raises_error(self):
        """Test that registering duplicate tool name raises ValueError."""
        registry = ToolRegistry()

        def create_tool():
            return Tool(name="test", description="Test", func=lambda x: x)

        registry.register_tool("test_tool", create_tool)

        with pytest.raises(ValueError, match="already registered"):
            registry.register_tool("test_tool", create_tool)

    def test_get_tool_not_found_raises_error(self):
        """Test that getting non-existent tool raises ToolNotFoundError."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotFoundError) as exc_info:
            registry.get_tool("nonexistent_tool")

        assert "nonexistent_tool" in str(exc_info.value)
        assert "Available tools:" in str(exc_info.value)

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False)
    def test_get_tool_success(self):
        """Test successful tool retrieval."""
        registry = ToolRegistry()
        tool = registry.get_tool("serper_search")
        assert isinstance(tool, BaseTool)
        assert tool.name == "serper_search"

    @patch.dict(os.environ, {}, clear=True)
    def test_get_tool_missing_api_key_raises_error(self):
        """Test that missing API key raises ToolConfigError."""
        registry = ToolRegistry()

        with pytest.raises(ToolConfigError) as exc_info:
            registry.get_tool("serper_search")

        assert "SERPER_API_KEY" in str(exc_info.value)
        assert "environment variable" in str(exc_info.value)

    def test_get_tool_factory_exception_wrapped(self):
        """Test that factory exceptions are wrapped in ToolConfigError."""
        registry = ToolRegistry()

        def failing_factory():
            raise RuntimeError("Factory failed")

        registry.register_tool("failing_tool", failing_factory)

        with pytest.raises(ToolConfigError) as exc_info:
            registry.get_tool("failing_tool")

        assert "failing_tool" in str(exc_info.value)
        assert "Factory failed" in str(exc_info.value)


class TestGlobalAPI:
    """Test global convenience functions."""

    def test_list_tools_global(self):
        """Test global list_tools function."""
        tools = list_tools()
        assert isinstance(tools, list)
        assert "serper_search" in tools

    def test_has_tool_global(self):
        """Test global has_tool function."""
        assert has_tool("serper_search") is True
        assert has_tool("nonexistent_tool") is False

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False)
    def test_get_tool_global(self):
        """Test global get_tool function."""
        tool = get_tool("serper_search")
        assert isinstance(tool, BaseTool)
        assert tool.name == "serper_search"

    def test_get_tool_global_not_found(self):
        """Test global get_tool raises ToolNotFoundError."""
        with pytest.raises(ToolNotFoundError):
            get_tool("nonexistent_tool")

    def test_register_tool_global(self):
        """Test global register_tool function."""

        def create_test_tool():
            return Tool(name="test_global", description="Test", func=lambda x: x)

        # Register using global function
        register_tool("test_global_tool", create_test_tool)

        # Verify it's registered
        assert has_tool("test_global_tool")
        assert "test_global_tool" in list_tools()

        # Clean up (for other tests)
        from configurable_agents.tools.registry import _global_registry

        _global_registry._factories.pop("test_global_tool", None)


class TestToolNotFoundError:
    """Test ToolNotFoundError exception."""

    def test_error_attributes(self):
        """Test that error has correct attributes."""
        available = ["tool1", "tool2"]
        error = ToolNotFoundError("missing_tool", available)

        assert error.tool_name == "missing_tool"
        assert error.available_tools == available
        assert "missing_tool" in str(error)
        assert "tool1" in str(error)
        assert "tool2" in str(error)

    def test_error_message_helpful(self):
        """Test that error message includes helpful suggestions."""
        error = ToolNotFoundError("missing", ["available1", "available2"])
        message = str(error)

        assert "not found" in message
        assert "Available tools:" in message
        assert "Suggestion:" in message


class TestToolConfigError:
    """Test ToolConfigError exception."""

    def test_error_with_env_var(self):
        """Test error with environment variable suggestion."""
        error = ToolConfigError("test_tool", "Missing API key", "TEST_API_KEY")

        assert error.tool_name == "test_tool"
        assert error.reason == "Missing API key"
        assert error.env_var == "TEST_API_KEY"
        assert "TEST_API_KEY" in str(error)
        assert "environment variable" in str(error)
        assert "export" in str(error)

    def test_error_without_env_var(self):
        """Test error without environment variable."""
        error = ToolConfigError("test_tool", "Configuration failed")

        assert error.tool_name == "test_tool"
        assert error.reason == "Configuration failed"
        assert error.env_var is None
        assert "test_tool" in str(error)
        assert "Configuration failed" in str(error)


class TestRegistryIntegration:
    """Integration tests for registry with real tool creation."""

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-api-key-123"}, clear=False)
    def test_serper_tool_loaded_successfully(self):
        """Test that serper_search tool can be loaded with valid config."""
        tool = get_tool("serper_search")

        # Verify tool properties
        assert isinstance(tool, BaseTool)
        assert tool.name == "serper_search"
        assert "search" in tool.description.lower()
        assert "google" in tool.description.lower() or "serper" in tool.description.lower()

    @patch.dict(os.environ, {}, clear=True)
    def test_serper_tool_fails_without_api_key(self):
        """Test that serper_search tool fails gracefully without API key."""
        with pytest.raises(ToolConfigError) as exc_info:
            get_tool("serper_search")

        error = exc_info.value
        assert error.tool_name == "serper_search"
        assert error.env_var == "SERPER_API_KEY"
        assert "SERPER_API_KEY" in str(error)

    def test_all_registered_tools_documented(self):
        """Test that all tools are properly registered and accessible."""
        tools = list_tools()

        # v0.2 should have all these tools
        # Web tools
        web_tools = ["http_client", "web_scrape", "web_search"]
        # File tools
        file_tools = ["file_glob", "file_move", "file_read", "file_write"]
        # Data tools
        data_tools = ["dataframe_to_csv", "json_parse", "sql_query", "yaml_parse"]
        # System tools
        system_tools = ["env_vars", "process", "shell"]
        # Search tools (legacy)
        search_tools = ["serper_search"]

        expected_tools = web_tools + file_tools + data_tools + system_tools + search_tools

        assert set(tools) == set(expected_tools)

        # All tools should be gettable (with proper config)
        for tool_name in tools:
            assert has_tool(tool_name)
