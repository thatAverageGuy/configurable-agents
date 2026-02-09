"""LiteLLM-based multi-provider LLM integration.

This module provides a unified interface for multiple LLM providers through LiteLLM,
which supports 100+ providers with a single OpenAI-compatible API.

Supported providers:
- OpenAI (openai/)
- Anthropic (anthropic/)
- Google Gemini (gemini/)
- Ollama local models (ollama_chat/)

Example:
    >>> from configurable_agents.llm.litellm_provider import create_litellm_llm
    >>> from configurable_agents.config import LLMConfig
    >>>
    >>> config = LLMConfig(provider="openai", model="gpt-4o")
    >>> llm = create_litellm_llm(config)
"""

from typing import Any, Dict, Optional

# Check for LiteLLM availability
try:
    import litellm

    LITELLM_AVAILABLE = True

    # Configure LiteLLM to drop unsupported parameters
    # This is needed for VertexAI/Gemini which doesn't support some LangChain defaults
    litellm.drop_params = True  # type: ignore
except ImportError:
    LITELLM_AVAILABLE = False
    litellm = None  # type: ignore


def get_litellm_model_string(provider: str, model: str) -> str:
    """Convert provider and model to LiteLLM model string format.

    LiteLLM uses "provider/model" format for unified API access.
    Different providers have different prefixes.

    Args:
        provider: Provider name (openai, anthropic, google, ollama)
        model: Model name (e.g., gpt-4o, claude-sonnet-4-20250514)

    Returns:
        LiteLLM model string (e.g., "openai/gpt-4o")

    Raises:
        ValueError: If provider is not supported

    Example:
        >>> get_litellm_model_string("openai", "gpt-4o")
        'openai/gpt-4o'
        >>> get_litellm_model_string("google", "gemini-2.5-flash")
        'gemini/gemini-2.5-flash'
        >>> get_litellm_model_string("ollama", "llama3")
        'ollama_chat/llama3'
    """
    provider_model_map = {
        "openai": "openai",
        "anthropic": "anthropic",
        "google": "gemini",  # LiteLLM uses "gemini/" not "google/"
        "ollama": "ollama_chat",  # Use ollama_chat per LiteLLM best practices
    }

    if provider not in provider_model_map:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported: {list(provider_model_map.keys())}"
        )

    litellm_provider = provider_model_map[provider]
    return f"{litellm_provider}/{model}"


def create_litellm_llm(llm_config: Any) -> Any:
    """Create a LangChain BaseChatModel using LiteLLM.

    Uses ChatLiteLLM from langchain-litellm, which wraps litellm.completion()
    to provide the standard BaseChatModel interface expected by the rest of the
    codebase (compatible with with_structured_output).

    Args:
        llm_config: LLMConfig object with provider, model, temperature, etc.

    Returns:
        ChatLiteLLM instance (BaseChatModel subclass)

    Raises:
        LLMConfigError: If LiteLLM is not available or config is invalid
        ImportError: If langchain-litellm is not installed

    Example:
        >>> from configurable_agents.config import LLMConfig
        >>> config = LLMConfig(provider="anthropic", model="claude-sonnet-4-20250514")
        >>> llm = create_litellm_llm(config)
    """
    from configurable_agents.llm.provider import LLMConfigError

    if not LITELLM_AVAILABLE:
        raise LLMConfigError(
            reason="LiteLLM is not installed. Multi-provider support requires litellm.",
            suggestion="Install litellm: pip install litellm>=1.80.0",
        )

    # Import ChatLiteLLM from langchain-litellm (migrated from deprecated langchain-community)
    try:
        from langchain_litellm import ChatLiteLLM
    except ImportError as e:
        raise ImportError(
            "langchain-litellm is required for LiteLLM integration. "
            "Install: pip install 'langchain-litellm>=0.2.0'"
        ) from e

    # Get provider and model
    provider = llm_config.provider or "google"  # Default to Google for backward compat
    model = llm_config.model or "gemini-2.5-flash-lite"

    # Build LiteLLM model string
    model_string = get_litellm_model_string(provider, model)

    # Configure LiteLLM to drop unsupported parameters
    # This is needed for VertexAI/Gemini which doesn't support some LangChain defaults
    litellm.drop_params = True  # type: ignore

    # Also set it as an environment variable for extra safety
    import os
    os.environ["LITELLM_DROP_PARAMS"] = "true"

    # Build ChatLiteLLM kwargs
    kwargs = {"model": model_string}

    # Add optional parameters if specified
    if llm_config.temperature is not None:
        kwargs["temperature"] = llm_config.temperature

    if llm_config.max_tokens is not None:
        kwargs["max_tokens"] = llm_config.max_tokens

    # For Ollama, set default API base to localhost
    if provider == "ollama":
        # Allow override via api_base in config
        api_base = getattr(llm_config, "api_base", None) or "http://localhost:11434"
        kwargs["api_base"] = api_base

    # Create and return ChatLiteLLM instance
    try:
        llm = ChatLiteLLM(**kwargs)
    except Exception as e:
        raise LLMConfigError(
            reason=f"Failed to initialize LiteLLM with model '{model_string}': {e}",
            provider=provider,
            suggestion="Check that the model name is correct and API credentials are set.",
        ) from e

    return llm


def call_litellm_completion(
    provider: str,
    model: str,
    messages: list,
    **kwargs,
) -> Dict[str, Any]:
    """Call LiteLLM completion directly without LangChain wrapper.

    This is a standalone function for direct LiteLLM usage when you don't need
    the BaseChatModel interface (e.g., for simple completions).

    Args:
        provider: Provider name (openai, anthropic, google, ollama)
        model: Model name
        messages: List of message dicts with role and content
        **kwargs: Additional parameters (temperature, max_tokens, etc.)

    Returns:
        Dict with:
            - content: str - Response text content
            - input_tokens: int - Input token count
            - output_tokens: int - Output token count
            - total_tokens: int - Total token count
            - cost_usd: float - Estimated cost in USD

    Raises:
        LLMConfigError: If LiteLLM is not available
        litellm.exceptions.APIError: If API call fails

    Example:
        >>> messages = [{"role": "user", "content": "Hello"}]
        >>> result = call_litellm_completion("openai", "gpt-4o", messages)
        >>> print(result["content"])
        >>> print(f"Cost: ${result['cost_usd']:.6f}")
    """
    from configurable_agents.llm.provider import LLMConfigError

    if not LITELLM_AVAILABLE:
        raise LLMConfigError(
            reason="LiteLLM is not installed.",
            suggestion="Install litellm: pip install litellm>=1.80.0",
        )

    # Import LiteLLM exceptions
    from litellm.exceptions import APIError, AuthenticationError

    # Build model string
    model_string = get_litellm_model_string(provider, model)

    # Prepare completion parameters
    completion_kwargs = {"model": model_string, "messages": messages, **kwargs}

    try:
        # Call LiteLLM
        response = litellm.completion(**completion_kwargs)  # type: ignore

        # Extract content and usage
        choices = response.get("choices", [])
        content = choices[0]["message"]["content"] if choices else ""

        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

        # Calculate cost using LiteLLM's built-in cost calculation
        cost_usd = 0.0
        try:
            cost_usd = litellm.completion_cost(completion_kwargs)  # type: ignore
        except Exception:
            # Cost calculation may fail for some models
            pass

        return {
            "content": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
        }

    except AuthenticationError as e:
        raise LLMConfigError(
            reason=f"Authentication failed for provider '{provider}': {e}",
            provider=provider,
            suggestion=f"Check that API key for {provider} is set correctly.",
        ) from e
    except APIError as e:
        raise LLMConfigError(
            reason=f"API error from provider '{provider}': {e}",
            provider=provider,
            suggestion="Check your request parameters and try again.",
        ) from e
