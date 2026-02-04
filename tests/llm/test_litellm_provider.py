"""Tests for LiteLLM provider integration.

Tests cover:
- Model string mapping for all supported providers
- LLM creation with ChatLiteLLM wrapper
- Direct completion calls
- Error handling for API and authentication errors
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from configurable_agents.config import LLMConfig
from configurable_agents.llm.litellm_provider import (
    LITELLM_AVAILABLE,
    call_litellm_completion,
    create_litellm_llm,
    get_litellm_model_string,
)


class TestGetLiteLLMModelString:
    """Test get_litellm_model_string function."""

    def test_openai_provider(self):
        """Test OpenAI provider model string mapping."""
        result = get_litellm_model_string("openai", "gpt-4o")
        assert result == "openai/gpt-4o"

    def test_anthropic_provider(self):
        """Test Anthropic provider model string mapping."""
        result = get_litellm_model_string("anthropic", "claude-sonnet-4-20250514")
        assert result == "anthropic/claude-sonnet-4-20250514"

    def test_google_provider(self):
        """Test Google provider model string mapping (uses 'gemini/' prefix)."""
        result = get_litellm_model_string("google", "gemini-2.5-flash")
        assert result == "gemini/gemini-2.5-flash"

    def test_ollama_provider(self):
        """Test Ollama provider model string mapping (uses 'ollama_chat/' prefix)."""
        result = get_litellm_model_string("ollama", "llama3")
        assert result == "ollama_chat/llama3"

    def test_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_litellm_model_string("unknown", "model")
        assert "Unsupported provider" in str(exc_info.value)
        assert "unknown" in str(exc_info.value)


class TestCreateLiteLLM:
    """Test create_litellm_llm function."""

    @patch("langchain_community.chat_models.ChatLiteLLM")
    def test_create_with_openai_provider(self, mock_chat):
        """Test creating LLM with OpenAI provider."""
        config = LLMConfig(provider="openai", model="gpt-4o", temperature=0.7)
        llm = create_litellm_llm(config)

        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "openai/gpt-4o"
        assert call_kwargs["temperature"] == 0.7

    @patch("langchain_community.chat_models.ChatLiteLLM")
    def test_create_with_anthropic_provider(self, mock_chat):
        """Test creating LLM with Anthropic provider."""
        config = LLMConfig(provider="anthropic", model="claude-sonnet-4-20250514")
        llm = create_litellm_llm(config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "anthropic/claude-sonnet-4-20250514"

    @patch("langchain_community.chat_models.ChatLiteLLM")
    def test_create_with_google_provider(self, mock_chat):
        """Test creating LLM with Google provider."""
        config = LLMConfig(provider="google", model="gemini-2.5-flash")
        llm = create_litellm_llm(config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "gemini/gemini-2.5-flash"

    @patch("langchain_community.chat_models.ChatLiteLLM")
    def test_create_with_ollama_provider_sets_api_base(self, mock_chat):
        """Test creating LLM with Ollama provider sets api_base."""
        config = LLMConfig(provider="ollama", model="llama3")
        llm = create_litellm_llm(config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "ollama_chat/llama3"
        assert call_kwargs["api_base"] == "http://localhost:11434"

    @patch("langchain_community.chat_models.ChatLiteLLM")
    def test_create_with_ollama_custom_api_base(self, mock_chat):
        """Test Ollama with custom api_base from config."""
        config = LLMConfig(provider="ollama", model="llama3", api_base="http://192.168.1.100:11434")
        llm = create_litellm_llm(config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["api_base"] == "http://192.168.1.100:11434"

    @patch("langchain_community.chat_models.ChatLiteLLM")
    def test_create_with_max_tokens(self, mock_chat):
        """Test creating LLM with max_tokens setting."""
        config = LLMConfig(provider="openai", model="gpt-4o", max_tokens=2048)
        llm = create_litellm_llm(config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["max_tokens"] == 2048

    @patch("langchain_community.chat_models.ChatLiteLLM")
    def test_create_with_default_provider(self, mock_chat):
        """Test creating LLM with no provider defaults to Google."""
        config = LLMConfig(model="gemini-2.5-flash")
        llm = create_litellm_llm(config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "gemini/gemini-2.5-flash"

    @patch("langchain_community.chat_models.ChatLiteLLM")
    def test_create_error_wrapped_in_llm_config_error(self, mock_chat):
        """Test that ChatLiteLLM errors are wrapped in LLMConfigError."""
        from configurable_agents.llm.provider import LLMConfigError

        mock_chat.side_effect = RuntimeError("API connection failed")

        config = LLMConfig(provider="openai", model="gpt-4o")
        with pytest.raises(LLMConfigError) as exc_info:
            create_litellm_llm(config)

        assert "Failed to initialize LiteLLM" in str(exc_info.value)
        assert exc_info.value.provider == "openai"

    def test_create_without_litellm_raises_error(self):
        """Test that missing LiteLLM raises LLMConfigError."""
        from configurable_agents.llm.provider import LLMConfigError

        # Temporarily set LITELLM_AVAILABLE to False
        with patch(
            "configurable_agents.llm.litellm_provider.LITELLM_AVAILABLE", False
        ):
            config = LLMConfig(provider="openai", model="gpt-4o")
            with pytest.raises(LLMConfigError) as exc_info:
                create_litellm_llm(config)

            assert "LiteLLM is not installed" in str(exc_info.value)


class TestCallLiteLLMCompletion:
    """Test call_litellm_completion function."""

    @patch("configurable_agents.llm.litellm_provider.litellm")
    def test_call_returns_content_and_tokens(self, mock_litellm):
        """Test successful completion returns content and usage."""
        mock_response = {
            "choices": [{"message": {"content": "Hello, world!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_litellm.completion.return_value = mock_response
        mock_litellm.completion_cost.return_value = 0.0001

        result = call_litellm_completion(
            "openai", "gpt-4o", [{"role": "user", "content": "Hello"}]
        )

        assert result["content"] == "Hello, world!"
        assert result["input_tokens"] == 10
        assert result["output_tokens"] == 5
        assert result["total_tokens"] == 15
        assert result["cost_usd"] == 0.0001

    @patch("configurable_agents.llm.litellm_provider.litellm")
    def test_call_with_kwargs_passed_to_litellm(self, mock_litellm):
        """Test that additional kwargs are passed to litellm.completion."""
        mock_response = {
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_litellm.completion.return_value = mock_response
        mock_litellm.completion_cost.return_value = 0.0001

        call_litellm_completion(
            "openai",
            "gpt-4o",
            [{"role": "user", "content": "Hello"}],
            temperature=0.5,
            max_tokens=100,
        )

        call_kwargs = mock_litellm.completion.call_args[1]
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 100

    @patch("configurable_agents.llm.litellm_provider.litellm")
    def test_call_anthropic_provider(self, mock_litellm):
        """Test completion with Anthropic provider."""
        mock_response = {
            "choices": [{"message": {"content": "Claude response"}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
        }
        mock_litellm.completion.return_value = mock_response
        mock_litellm.completion_cost.return_value = 0.0003

        result = call_litellm_completion(
            "anthropic", "claude-sonnet-4-20250514", [{"role": "user", "content": "Hi"}]
        )

        # Verify model string uses anthropic/ prefix
        call_kwargs = mock_litellm.completion.call_args[1]
        assert call_kwargs["model"] == "anthropic/claude-sonnet-4-20250514"
        assert result["content"] == "Claude response"

    @patch("configurable_agents.llm.litellm_provider.litellm")
    def test_call_ollama_provider(self, mock_litellm):
        """Test completion with Ollama provider."""
        mock_response = {
            "choices": [{"message": {"content": "Local response"}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
        }
        mock_litellm.completion.return_value = mock_response
        mock_litellm.completion_cost.return_value = 0.0

        result = call_litellm_completion("ollama", "llama3", [{"role": "user", "content": "Hi"}])

        # Verify model string uses ollama_chat/ prefix
        call_kwargs = mock_litellm.completion.call_args[1]
        assert call_kwargs["model"] == "ollama_chat/llama3"
        assert result["content"] == "Local response"

    @patch("configurable_agents.llm.litellm_provider.litellm")
    def test_call_handles_empty_choices(self, mock_litellm):
        """Test completion with empty choices returns empty content."""
        mock_response = {
            "choices": [],
            "usage": {"prompt_tokens": 10, "completion_tokens": 0, "total_tokens": 10},
        }
        mock_litellm.completion.return_value = mock_response
        mock_litellm.completion_cost.return_value = 0.0

        result = call_litellm_completion(
            "openai", "gpt-4o", [{"role": "user", "content": "Hi"}]
        )

        assert result["content"] == ""
        assert result["input_tokens"] == 10

    @patch("configurable_agents.llm.litellm_provider.litellm")
    def test_call_handles_missing_usage(self, mock_litellm):
        """Test completion with missing usage defaults to zero tokens."""
        mock_response = {"choices": [{"message": {"content": "Response"}}]}
        mock_litellm.completion.return_value = mock_response
        mock_litellm.completion_cost.return_value = 0.0001

        result = call_litellm_completion(
            "openai", "gpt-4o", [{"role": "user", "content": "Hi"}]
        )

        assert result["content"] == "Response"
        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0

    @patch("configurable_agents.llm.litellm_provider.litellm")
    def test_call_cost_calculation_failure_fallback(self, mock_litellm):
        """Test that completion_cost failure is handled gracefully."""
        mock_response = {
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_litellm.completion.return_value = mock_response
        mock_litellm.completion_cost.side_effect = Exception("Cost not available")

        result = call_litellm_completion(
            "openai", "gpt-4o", [{"role": "user", "content": "Hi"}]
        )

        # Should return cost as 0.0 when calculation fails
        assert result["cost_usd"] == 0.0

    def test_authentication_error_wrapped(self):
        """Test that AuthenticationError is wrapped in LLMConfigError."""
        from configurable_agents.llm.provider import LLMConfigError
        from litellm.exceptions import AuthenticationError
        from unittest.mock import patch

        # Patch litellm.completion to raise AuthenticationError
        with patch("configurable_agents.llm.litellm_provider.litellm") as mock_litellm:
            mock_litellm.completion.side_effect = AuthenticationError(
                message="Invalid API key", llm_provider="openai", model="gpt-4o"
            )

            with pytest.raises(LLMConfigError) as exc_info:
                call_litellm_completion("openai", "gpt-4o", [{"role": "user", "content": "Hi"}])

            assert "Authentication failed" in str(exc_info.value) or "API error" in str(exc_info.value)

    def test_api_error_wrapped(self):
        """Test that APIError is wrapped in LLMConfigError."""
        from configurable_agents.llm.provider import LLMConfigError
        from litellm.exceptions import APIError
        from unittest.mock import patch

        # Patch litellm.completion to raise APIError
        with patch("configurable_agents.llm.litellm_provider.litellm") as mock_litellm:
            mock_litellm.completion.side_effect = APIError(
                message="Rate limit exceeded",
                llm_provider="openai",
                model="gpt-4o",
                status_code=429,
            )

            with pytest.raises(LLMConfigError) as exc_info:
                call_litellm_completion("openai", "gpt-4o", [{"role": "user", "content": "Hi"}])

            assert "API error" in str(exc_info.value) or "Authentication failed" in str(exc_info.value)

    def test_call_without_litellm_raises_error(self):
        """Test that missing LiteLLM raises LLMConfigError."""
        from configurable_agents.llm.provider import LLMConfigError

        with patch(
            "configurable_agents.llm.litellm_provider.LITELLM_AVAILABLE", False
        ):
            with pytest.raises(LLMConfigError) as exc_info:
                call_litellm_completion("openai", "gpt-4o", [])

            assert "LiteLLM is not installed" in str(exc_info.value)


class TestLiteLLMAvailable:
    """Test LITELLM_AVAILABLE flag."""

    def test_litellm_available_is_boolean(self):
        """Test that LITELLM_AVAILABLE is a boolean."""
        assert isinstance(LITELLM_AVAILABLE, bool)
        # If litellm is installed, it should be True
        # Otherwise False (acceptable in tests)
