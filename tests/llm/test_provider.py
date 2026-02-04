"""Tests for LLM provider factory and core functionality.

Tests cover:
- LLM creation with various configurations
- Configuration merging (node overrides global)
- Provider validation
- Error handling for invalid configurations
- Structured output calling
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, ValidationError

from configurable_agents.config import LLMConfig
from configurable_agents.llm import (
    LLMAPIError,
    LLMConfigError,
    LLMProviderError,
    LLMUsageMetadata,
    call_llm_structured,
    create_llm,
    merge_llm_config,
)


def make_mock_response(parsed_output, input_tokens=100, output_tokens=50):
    """Create mock LangChain response with usage metadata."""
    usage = Mock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    raw = Mock()
    raw.usage_metadata = usage

    return {"parsed": parsed_output, "raw": raw}


class TestCreateLLM:
    """Test create_llm factory function."""

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key-123"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_with_google_provider(self, mock_chat):
        """Test creating LLM with Google provider uses direct implementation."""
        config = LLMConfig(provider="google", model="gemini-pro")
        llm = create_llm(config)

        # Should call ChatGoogleGenerativeAI directly (not through LiteLLM)
        # This provides better compatibility with LangChain features
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "gemini-pro"
        assert call_kwargs["google_api_key"] == "test-key-123"

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_with_default_provider(self, mock_chat):
        """Test creating LLM with no provider specified defaults to Google."""
        config = LLMConfig(model="gemini-pro")
        llm = create_llm(config)

        # Should default to Google via direct implementation
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "gemini-pro"

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_with_none_config(self, mock_chat):
        """Test creating LLM with None config uses defaults."""
        llm = create_llm(None)

        # Should use defaults (Google provider, default model)
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "gemini-2.5-flash-lite"  # Default model

    @patch("langchain_community.chat_models.ChatLiteLLM")
    def test_create_with_openai_provider(self, mock_chat):
        """Test creating LLM with OpenAI provider via LiteLLM."""
        config = LLMConfig(provider="openai", model="gpt-4o")
        llm = create_llm(config)

        # Should call ChatLiteLLM with OpenAI model string
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "openai/gpt-4o"

    @patch("langchain_community.chat_models.ChatLiteLLM")
    def test_create_with_anthropic_provider(self, mock_chat):
        """Test creating LLM with Anthropic provider via LiteLLM."""
        config = LLMConfig(provider="anthropic", model="claude-sonnet-4-20250514")
        llm = create_llm(config)

        # Should call ChatLiteLLM with Anthropic model string
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "anthropic/claude-sonnet-4-20250514"

    @patch("langchain_community.chat_models.ChatLiteLLM")
    def test_create_with_ollama_provider(self, mock_chat):
        """Test creating LLM with Ollama provider via LiteLLM."""
        config = LLMConfig(provider="ollama", model="llama3")
        llm = create_llm(config)

        # Should call ChatLiteLLM with Ollama model string and api_base
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "ollama_chat/llama3"
        assert call_kwargs["api_base"] == "http://localhost:11434"

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_with_temperature(self, mock_chat):
        """Test creating LLM with temperature setting."""
        config = LLMConfig(provider="google", temperature=0.7)
        llm = create_llm(config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_with_max_tokens(self, mock_chat):
        """Test creating LLM with max_tokens setting."""
        config = LLMConfig(provider="google", max_tokens=2048)
        llm = create_llm(config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["max_output_tokens"] == 2048

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_merges_node_and_global_config(self, mock_chat):
        """Test that node config overrides global config."""
        global_config = LLMConfig(provider="google", model="gemini-pro", temperature=0.5)
        node_config = LLMConfig(temperature=0.9)  # Override temperature only

        llm = create_llm(node_config, global_config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "gemini-pro"  # From global
        assert call_kwargs["temperature"] == 0.9  # From node (override)

    def test_create_openai_without_litellm_raises_error(self):
        """Test that OpenAI raises error when LiteLLM is unavailable."""
        with patch("configurable_agents.llm.litellm_provider.LITELLM_AVAILABLE", False):
            config = LLMConfig(provider="openai", model="gpt-4o")

            with pytest.raises(LLMProviderError) as exc_info:
                create_llm(config)

            error = exc_info.value
            assert error.provider == "openai"
            assert "google" in error.supported_providers

    def test_create_with_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises error."""
        # Pydantic validates provider before create_llm is called
        # So we expect a ValidationError for invalid provider
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(provider="invalid")

        # Verify validation error message mentions supported providers
        assert "invalid" in str(exc_info.value).lower() or "not supported" in str(exc_info.value).lower()


class TestMergeLLMConfig:
    """Test merge_llm_config function."""

    def test_merge_with_both_configs(self):
        """Test merging node and global configs."""
        global_config = LLMConfig(provider="google", model="gemini-pro", temperature=0.5)
        node_config = LLMConfig(temperature=0.9, max_tokens=1024)

        merged = merge_llm_config(node_config, global_config)

        assert merged.provider == "google"  # From global
        assert merged.model == "gemini-pro"  # From global
        assert merged.temperature == 0.9  # From node (override)
        assert merged.max_tokens == 1024  # From node

    def test_merge_with_none_node_config(self):
        """Test merging when node config is None."""
        global_config = LLMConfig(provider="google", model="gemini-pro")
        merged = merge_llm_config(None, global_config)

        assert merged == global_config

    def test_merge_with_none_global_config(self):
        """Test merging when global config is None."""
        node_config = LLMConfig(temperature=0.9)
        merged = merge_llm_config(node_config, None)

        assert merged == node_config

    def test_merge_with_both_none(self):
        """Test merging when both configs are None."""
        merged = merge_llm_config(None, None)

        assert merged.provider is None
        assert merged.model is None


class TestCallLLMStructured:
    """Test call_llm_structured function."""

    def test_call_with_valid_output(self):
        """Test successful LLM call with valid structured output."""

        class TestOutput(BaseModel):
            result: str

        # Mock LLM
        mock_llm = Mock(spec=BaseChatModel)
        mock_structured = Mock()
        mock_structured.invoke.return_value = make_mock_response(
            TestOutput(result="Hello, world!")
        )
        mock_llm.with_structured_output.return_value = mock_structured

        # Call
        result, usage = call_llm_structured(mock_llm, "Say hello", TestOutput)

        # Verify
        assert isinstance(result, TestOutput)
        assert result.result == "Hello, world!"
        assert isinstance(usage, LLMUsageMetadata)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        mock_llm.with_structured_output.assert_called_once_with(TestOutput, include_raw=True)
        mock_structured.invoke.assert_called_once_with("Say hello")

    def test_call_with_dict_response(self):
        """Test LLM call when response is dict (auto-converted to model)."""

        class TestOutput(BaseModel):
            result: str

        # Mock LLM returning dict
        mock_llm = Mock(spec=BaseChatModel)
        mock_structured = Mock()
        mock_structured.invoke.return_value = make_mock_response({"result": "Test"})
        mock_llm.with_structured_output.return_value = mock_structured

        # Call
        result, usage = call_llm_structured(mock_llm, "Test", TestOutput)

        # Verify
        assert isinstance(result, TestOutput)
        assert result.result == "Test"
        assert isinstance(usage, LLMUsageMetadata)

    def test_call_with_tools(self):
        """Test LLM call with tools binding."""

        class TestOutput(BaseModel):
            result: str

        # Mock tools
        mock_tool1 = Mock()
        mock_tool2 = Mock()
        tools = [mock_tool1, mock_tool2]

        # Mock LLM (tools bound first, then structured output)
        mock_llm = Mock(spec=BaseChatModel)
        mock_with_tools = Mock()
        mock_structured = Mock()
        mock_structured.invoke.return_value = make_mock_response(TestOutput(result="Done"))
        mock_with_tools.with_structured_output.return_value = mock_structured
        mock_llm.bind_tools.return_value = mock_with_tools

        # Call
        result, usage = call_llm_structured(mock_llm, "Test", TestOutput, tools=tools)

        # Verify tools were bound first, then structured output
        mock_llm.bind_tools.assert_called_once_with(tools)
        mock_with_tools.with_structured_output.assert_called_once_with(TestOutput, include_raw=True)
        assert isinstance(result, TestOutput)
        assert isinstance(usage, LLMUsageMetadata)

    @patch("configurable_agents.llm.provider.time.sleep")
    def test_call_retries_on_validation_error(self, mock_sleep):
        """Test that call retries on ValidationError."""

        class TestOutput(BaseModel):
            result: str

        # Mock LLM that fails twice then succeeds
        mock_llm = Mock(spec=BaseChatModel)
        mock_structured = Mock()
        mock_structured.invoke.side_effect = [
            ValidationError.from_exception_data(
                "test",
                [{"type": "missing", "loc": ("result",), "msg": "Field required", "input": {}}],
            ),
            ValidationError.from_exception_data(
                "test",
                [{"type": "missing", "loc": ("result",), "msg": "Field required", "input": {}}],
            ),
            make_mock_response(TestOutput(result="Success")),
        ]
        mock_llm.with_structured_output.return_value = mock_structured

        # Call
        result, usage = call_llm_structured(mock_llm, "Test", TestOutput, max_retries=3)

        # Should succeed on 3rd attempt
        assert result.result == "Success"
        assert isinstance(usage, LLMUsageMetadata)
        assert mock_structured.invoke.call_count == 3
        # Should sleep between retries
        assert mock_sleep.call_count == 2

    @patch("configurable_agents.llm.provider.time.sleep")
    def test_call_raises_after_max_retries(self, mock_sleep):
        """Test that call raises ValidationError after max retries."""

        class TestOutput(BaseModel):
            result: str

        # Mock LLM that always fails
        mock_llm = Mock(spec=BaseChatModel)
        mock_structured = Mock()
        mock_structured.invoke.side_effect = ValidationError.from_exception_data(
            "test", [{"type": "missing", "loc": ("result",), "msg": "Field required", "input": {}}]
        )
        mock_llm.with_structured_output.return_value = mock_structured

        # Call should raise after retries
        with pytest.raises(ValidationError):
            call_llm_structured(mock_llm, "Test", TestOutput, max_retries=2)

        # Should try twice
        assert mock_structured.invoke.call_count == 2

    def test_call_raises_llm_api_error_on_non_validation_error(self):
        """Test that non-validation errors are wrapped in LLMAPIError."""

        class TestOutput(BaseModel):
            result: str

        # Mock LLM that raises generic error
        mock_llm = Mock(spec=BaseChatModel)
        mock_structured = Mock()
        mock_structured.invoke.side_effect = RuntimeError("API Error")
        mock_llm.with_structured_output.return_value = mock_structured

        # Call should raise LLMAPIError
        with pytest.raises(LLMAPIError) as exc_info:
            call_llm_structured(mock_llm, "Test", TestOutput)

        error = exc_info.value
        assert "API Error" in error.reason
        assert not error.retryable

    @patch("configurable_agents.llm.provider.time.sleep")
    def test_call_retries_on_rate_limit(self, mock_sleep):
        """Test that call retries on rate limit errors."""

        class TestOutput(BaseModel):
            result: str

        # Mock LLM that fails with rate limit then succeeds
        mock_llm = Mock(spec=BaseChatModel)
        mock_structured = Mock()
        mock_structured.invoke.side_effect = [
            RuntimeError("Rate limit exceeded"),
            make_mock_response(TestOutput(result="Success")),
        ]
        mock_llm.with_structured_output.return_value = mock_structured

        # Call should retry and succeed
        result, usage = call_llm_structured(mock_llm, "Test", TestOutput, max_retries=3)

        assert result.result == "Success"
        assert isinstance(usage, LLMUsageMetadata)
        assert mock_structured.invoke.call_count == 2
        # Should use exponential backoff (2^0 = 1 second)
        mock_sleep.assert_called_once_with(1)

    def test_call_with_unexpected_result_type_raises_error(self):
        """Test that unexpected result type raises LLMAPIError."""

        class TestOutput(BaseModel):
            result: str

        # Mock LLM returning unexpected type
        mock_llm = Mock(spec=BaseChatModel)
        mock_structured = Mock()
        mock_structured.invoke.return_value = "unexpected string"
        mock_llm.with_structured_output.return_value = mock_structured

        # Call should raise
        with pytest.raises(LLMAPIError) as exc_info:
            call_llm_structured(mock_llm, "Test", TestOutput)

        error = exc_info.value
        assert "unexpected type" in error.reason
        assert not error.retryable
