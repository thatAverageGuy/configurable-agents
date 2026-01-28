"""Google Gemini LLM provider implementation.

This module provides Google Gemini-specific LLM creation and configuration.
Requires GOOGLE_API_KEY environment variable to be set.

Example:
    >>> from configurable_agents.llm.google import create_google_llm
    >>> from configurable_agents.config import LLMConfig
    >>>
    >>> config = LLMConfig(model="gemini-2.5-flash-lite", temperature=0.7)
    >>> llm = create_google_llm(config)
"""

import os
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from configurable_agents.llm.provider import LLMConfigError


def create_google_llm(llm_config: Any) -> ChatGoogleGenerativeAI:
    """Create a Google Gemini LLM instance from configuration.

    This factory function handles:
    - API key validation
    - Model selection and defaults
    - Parameter configuration
    - Error handling

    Args:
        llm_config: LLMConfig object with Google Gemini settings

    Returns:
        ChatGoogleGenerativeAI instance ready to use

    Raises:
        LLMConfigError: If GOOGLE_API_KEY is missing or configuration is invalid

    Example:
        >>> import os
        >>> os.environ["GOOGLE_API_KEY"] = "your-key-here"
        >>> from configurable_agents.config import LLMConfig
        >>> config = LLMConfig(model="gemini-2.5-flash-lite", temperature=0.7)
        >>> llm = create_google_llm(config)
    """
    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise LLMConfigError(
            reason="GOOGLE_API_KEY environment variable not set",
            provider="google",
            suggestion=(
                "Set the environment variable: GOOGLE_API_KEY\n"
                "Get your API key from: https://ai.google.dev/\n"
                "Example: export GOOGLE_API_KEY=your-api-key-here"
            ),
        )

    # Get configuration parameters
    model = llm_config.model or "gemini-2.5-flash-lite"  # Default to flash lite model
    temperature = llm_config.temperature
    max_tokens = llm_config.max_tokens

    # Build kwargs for ChatGoogleGenerativeAI
    kwargs = {
        "model": model,
        "google_api_key": api_key,
    }

    # Add optional parameters if specified
    if temperature is not None:
        kwargs["temperature"] = temperature

    if max_tokens is not None:
        kwargs["max_output_tokens"] = max_tokens

    # Create LLM instance
    try:
        llm = ChatGoogleGenerativeAI(**kwargs)
    except Exception as e:
        raise LLMConfigError(
            reason=f"Failed to initialize Google Gemini: {e}",
            provider="google",
            suggestion="Check that your API key is valid and the model name is correct.",
        ) from e

    return llm


def validate_google_config() -> bool:
    """Validate that Google Gemini is properly configured.

    Checks if GOOGLE_API_KEY environment variable is set.
    Does not validate the key itself (no API call).

    Returns:
        True if configuration is valid, False otherwise

    Example:
        >>> import os
        >>> os.environ["GOOGLE_API_KEY"] = "test-key"
        >>> validate_google_config()
        True
        >>> del os.environ["GOOGLE_API_KEY"]
        >>> validate_google_config()
        False
    """
    return bool(os.getenv("GOOGLE_API_KEY"))


def get_default_model() -> str:
    """Get the default Google Gemini model for v0.1.

    Returns:
        Default model name

    Example:
        >>> get_default_model()
        'gemini-2.5-flash-lite'
    """
    return "gemini-2.5-flash-lite"


def get_supported_models() -> list[str]:
    """Get list of supported Google Gemini models.

    Returns:
        List of supported model names

    Example:
        >>> models = get_supported_models()
        >>> "gemini-2.5-flash-lite" in models
        True
    """
    return [
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-pro",
        "gemini-pro-vision",
    ]
