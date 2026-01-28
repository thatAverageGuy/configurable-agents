"""Tests for Google Gemini LLM provider.

Tests cover:
- LLM creation with valid configuration
- API key validation
- Error handling for missing configuration
- Model defaults and configuration
- Integration test with real API (marked as slow)
"""

import os
from unittest.mock import patch

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from configurable_agents.config import LLMConfig
from configurable_agents.llm.google import (
    create_google_llm,
    get_default_model,
    get_supported_models,
    validate_google_config,
)
from configurable_agents.llm.provider import LLMConfigError


class TestCreateGoogleLLM:
    """Test create_google_llm factory function."""

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key-123"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_with_valid_api_key(self, mock_chat):
        """Test creating Google LLM with valid API key."""
        config = LLMConfig(model="gemini-pro")
        llm = create_google_llm(config)

        # Should create ChatGoogleGenerativeAI
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "gemini-pro"
        assert call_kwargs["google_api_key"] == "test-key-123"

    @patch.dict(os.environ, {}, clear=True)
    def test_create_without_api_key_raises_error(self):
        """Test that missing API key raises LLMConfigError."""
        config = LLMConfig(model="gemini-pro")

        with pytest.raises(LLMConfigError) as exc_info:
            create_google_llm(config)

        error = exc_info.value
        assert error.provider == "google"
        assert "GOOGLE_API_KEY" in str(error)
        assert "environment variable" in str(error).lower()
        assert error.suggestion is not None
        assert "https://ai.google.dev" in error.suggestion

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_with_default_model(self, mock_chat):
        """Test creating LLM with no model specified uses default."""
        config = LLMConfig()  # No model specified
        llm = create_google_llm(config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "gemini-2.5-flash-lite"  # Default model

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_with_temperature(self, mock_chat):
        """Test creating LLM with temperature setting."""
        config = LLMConfig(model="gemini-pro", temperature=0.7)
        llm = create_google_llm(config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_with_max_tokens(self, mock_chat):
        """Test creating LLM with max_tokens setting."""
        config = LLMConfig(model="gemini-pro", max_tokens=2048)
        llm = create_google_llm(config)

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["max_output_tokens"] == 2048

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_without_optional_params(self, mock_chat):
        """Test creating LLM without optional parameters."""
        config = LLMConfig(model="gemini-pro")
        llm = create_google_llm(config)

        call_kwargs = mock_chat.call_args[1]
        # Optional params should not be in kwargs
        assert "temperature" not in call_kwargs
        assert "max_output_tokens" not in call_kwargs

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    @patch("configurable_agents.llm.google.ChatGoogleGenerativeAI")
    def test_create_handles_initialization_error(self, mock_chat):
        """Test that initialization errors are wrapped in LLMConfigError."""
        mock_chat.side_effect = ValueError("Invalid model name")
        config = LLMConfig(model="invalid-model")

        with pytest.raises(LLMConfigError) as exc_info:
            create_google_llm(config)

        error = exc_info.value
        assert error.provider == "google"
        assert "Failed to initialize" in error.reason
        assert error.suggestion is not None


class TestValidateGoogleConfig:
    """Test validate_google_config function."""

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    def test_validate_with_api_key_returns_true(self):
        """Test validation succeeds when API key is set."""
        assert validate_google_config() is True

    @patch.dict(os.environ, {}, clear=True)
    def test_validate_without_api_key_returns_false(self):
        """Test validation fails when API key is not set."""
        assert validate_google_config() is False

    @patch.dict(os.environ, {"GOOGLE_API_KEY": ""}, clear=False)
    def test_validate_with_empty_api_key_returns_false(self):
        """Test validation fails when API key is empty."""
        assert validate_google_config() is False


class TestGetDefaultModel:
    """Test get_default_model function."""

    def test_returns_flash_model(self):
        """Test that default model is gemini-2.5-flash-lite."""
        assert get_default_model() == "gemini-2.5-flash-lite"


class TestGetSupportedModels:
    """Test get_supported_models function."""

    def test_returns_list_of_models(self):
        """Test that supported models list is returned."""
        models = get_supported_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert "gemini-2.5-flash-lite" in models
        assert "gemini-1.5-pro" in models
        assert "gemini-pro" in models

    def test_all_models_are_strings(self):
        """Test that all model names are strings."""
        models = get_supported_models()
        assert all(isinstance(model, str) for model in models)


# Integration tests (require real API key)


@pytest.mark.integration
@pytest.mark.slow
class TestGoogleLLMIntegration:
    """Integration tests with real Google Gemini API.

    These tests require GOOGLE_API_KEY to be set and will make real API calls.
    They are marked as slow and integration tests.
    """

    def test_create_and_invoke_real_llm(self):
        """Test creating and invoking real Google Gemini LLM."""
        # Skip if no API key
        if not os.getenv("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not set")

        config = LLMConfig(model="gemini-2.5-flash-lite", temperature=0.7)
        llm = create_google_llm(config)

        # Verify LLM was created
        assert isinstance(llm, ChatGoogleGenerativeAI)

        # Test basic invoke
        response = llm.invoke("Say 'Hello, integration test!'")
        assert response is not None
        assert len(str(response.content)) > 0

    def test_structured_output_with_real_llm(self):
        """Test structured output with real Google Gemini LLM."""
        # Skip if no API key
        if not os.getenv("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not set")

        class Greeting(BaseModel):
            message: str
            language: str

        config = LLMConfig(model="gemini-2.5-flash-lite")
        llm = create_google_llm(config)

        # Bind structured output
        structured_llm = llm.with_structured_output(Greeting)
        result = structured_llm.invoke(
            "Generate a greeting in English. Return a JSON object with 'message' and 'language' fields."
        )

        # Verify result
        assert isinstance(result, Greeting)
        assert isinstance(result.message, str)
        assert len(result.message) > 0
        assert result.language.lower() == "english"
