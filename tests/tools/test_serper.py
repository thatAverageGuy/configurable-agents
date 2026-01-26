"""Tests for Serper web search tool.

Tests cover:
- Tool creation with valid configuration
- API key validation
- Error handling for missing configuration
- Tool behavior and properties
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.tools import BaseTool

from configurable_agents.tools.registry import ToolConfigError
from configurable_agents.tools.serper import (
    create_serper_search,
    validate_serper_config,
)


class TestCreateSerperSearch:
    """Test create_serper_search factory function."""

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key-123"}, clear=False)
    def test_create_with_valid_api_key(self):
        """Test creating Serper tool with valid API key."""
        tool = create_serper_search()

        assert isinstance(tool, BaseTool)
        assert tool.name == "serper_search"
        assert tool.description is not None
        assert len(tool.description) > 0

    @patch.dict(os.environ, {}, clear=True)
    def test_create_without_api_key_raises_error(self):
        """Test that missing API key raises ToolConfigError."""
        with pytest.raises(ToolConfigError) as exc_info:
            create_serper_search()

        error = exc_info.value
        assert error.tool_name == "serper_search"
        assert error.env_var == "SERPER_API_KEY"
        assert "SERPER_API_KEY" in str(error)
        assert "environment variable" in str(error).lower()

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False)
    def test_tool_description_is_helpful(self):
        """Test that tool description is helpful for LLM."""
        tool = create_serper_search()

        description = tool.description.lower()
        # Should mention what it does
        assert "search" in description or "find" in description
        # Should mention the source
        assert "google" in description or "serper" in description or "web" in description
        # Should hint at use cases
        assert any(
            word in description
            for word in ["current", "information", "news", "articles", "content"]
        )

    @patch.dict(os.environ, {"SERPER_API_KEY": ""}, clear=False)
    def test_empty_api_key_treated_as_missing(self):
        """Test that empty string API key is treated as missing."""
        with pytest.raises(ToolConfigError):
            create_serper_search()

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.tools.serper.GoogleSerperAPIWrapper")
    def test_wrapper_initialization_failure(self, mock_wrapper):
        """Test that wrapper initialization failure raises ToolConfigError."""
        mock_wrapper.side_effect = RuntimeError("API initialization failed")

        with pytest.raises(ToolConfigError) as exc_info:
            create_serper_search()

        error = exc_info.value
        assert error.tool_name == "serper_search"
        assert "Failed to initialize" in str(error)

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False)
    def test_tool_func_is_callable(self):
        """Test that tool function is callable."""
        tool = create_serper_search()

        assert hasattr(tool, "func")
        assert callable(tool.func)


class TestValidateSerperConfig:
    """Test validate_serper_config validation function."""

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False)
    def test_valid_config_returns_true(self):
        """Test that valid configuration returns True."""
        assert validate_serper_config() is True

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key_returns_false(self):
        """Test that missing API key returns False."""
        assert validate_serper_config() is False

    @patch.dict(os.environ, {"SERPER_API_KEY": ""}, clear=False)
    def test_empty_api_key_returns_false(self):
        """Test that empty API key returns False."""
        assert validate_serper_config() is False

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key-123"}, clear=False)
    def test_validation_does_not_make_api_calls(self):
        """Test that validation only checks env var, no API calls."""
        # This should complete instantly without network calls
        result = validate_serper_config()
        assert result is True


class TestSerperToolBehavior:
    """Test Serper tool behavior and integration."""

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.tools.serper.GoogleSerperAPIWrapper")
    def test_tool_run_calls_wrapper(self, mock_wrapper_class):
        """Test that tool.run calls the Serper wrapper."""
        # Setup mock
        mock_wrapper = MagicMock()
        mock_wrapper.run.return_value = "Search results"
        mock_wrapper_class.return_value = mock_wrapper

        # Create tool and run
        tool = create_serper_search()
        result = tool.run("test query")

        # Verify wrapper was called
        mock_wrapper.run.assert_called_once_with("test query")
        assert result == "Search results"

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False)
    def test_tool_name_matches_registry_expectation(self):
        """Test that tool name matches what registry expects."""
        tool = create_serper_search()
        # Name should match the key used in registry
        assert tool.name == "serper_search"

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False)
    def test_multiple_tool_instances_independent(self):
        """Test that multiple tool instances are independent."""
        tool1 = create_serper_search()
        tool2 = create_serper_search()

        # Should be different instances
        assert tool1 is not tool2
        # But same name and type
        assert tool1.name == tool2.name
        assert type(tool1) == type(tool2)


@pytest.mark.integration
@pytest.mark.slow
class TestSerperRealAPI:
    """Integration tests with real Serper API.

    These tests require:
    - SERPER_API_KEY environment variable set
    - Network connection
    - Valid Serper API account

    Run with: pytest -m integration
    Skip with: pytest -m "not integration"
    """

    def test_real_search_query(self):
        """Test real search query (requires valid API key)."""
        if not os.getenv("SERPER_API_KEY"):
            pytest.skip("SERPER_API_KEY not set (integration test)")

        tool = create_serper_search()
        result = tool.run("Python programming language")

        # Basic sanity checks on result
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain something about Python
        assert "python" in result.lower()

    def test_real_search_various_queries(self):
        """Test various query types with real API."""
        if not os.getenv("SERPER_API_KEY"):
            pytest.skip("SERPER_API_KEY not set (integration test)")

        tool = create_serper_search()

        queries = [
            "artificial intelligence",
            "weather today",
            "latest technology news",
        ]

        for query in queries:
            result = tool.run(query)
            assert isinstance(result, str)
            assert len(result) > 0


class TestSerperErrorMessages:
    """Test that error messages are helpful and actionable."""

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key_error_is_actionable(self):
        """Test that missing key error tells user what to do."""
        with pytest.raises(ToolConfigError) as exc_info:
            create_serper_search()

        message = str(exc_info.value)
        # Should tell them what variable to set
        assert "SERPER_API_KEY" in message
        # Should tell them how to set it
        assert "export" in message.lower() or "set" in message.lower()
        # Should show an example
        assert "=" in message or "example" in message.lower()

    @patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.tools.serper.GoogleSerperAPIWrapper")
    def test_initialization_error_is_clear(self, mock_wrapper):
        """Test that initialization errors are clear."""
        mock_wrapper.side_effect = ValueError("Invalid API key format")

        with pytest.raises(ToolConfigError) as exc_info:
            create_serper_search()

        message = str(exc_info.value)
        assert "serper_search" in message
        assert "Failed to initialize" in message
        assert "Invalid API key format" in message
