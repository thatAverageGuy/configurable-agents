"""LLM provider factory and base functionality.

This module provides the main interface for creating and configuring LLM instances
from workflow configuration. It abstracts away provider-specific details.

Example:
    >>> from configurable_agents.llm import create_llm, call_llm_structured
    >>> from configurable_agents.config import LLMConfig
    >>>
    >>> config = LLMConfig(provider="google", model="gemini-pro", temperature=0.7)
    >>> llm = create_llm(config)
"""

import time
from typing import Any, Dict, List, Optional, Type

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel


class LLMConfigError(Exception):
    """Raised when LLM configuration is invalid."""

    def __init__(self, reason: str, provider: str = None, suggestion: str = None):
        self.reason = reason
        self.provider = provider
        self.suggestion = suggestion
        message = f"LLM configuration failed: {reason}"
        if provider:
            message = f"LLM configuration failed for provider '{provider}': {reason}"
        if suggestion:
            message += f"\n\nSuggestion: {suggestion}"
        super().__init__(message)


class LLMProviderError(Exception):
    """Raised when an LLM provider is not supported."""

    def __init__(self, provider: str, supported_providers: List[str]):
        self.provider = provider
        self.supported_providers = supported_providers
        message = (
            f"LLM provider '{provider}' is not supported.\n"
            f"Supported providers: {', '.join(supported_providers)}\n\n"
            f"Note: v0.1 only supports Google Gemini. "
            f"Additional providers coming in v0.2+ (8-12 weeks)."
        )
        super().__init__(message)


class LLMAPIError(Exception):
    """Raised when LLM API call fails."""

    def __init__(self, reason: str, retryable: bool = False):
        self.reason = reason
        self.retryable = retryable
        message = f"LLM API call failed: {reason}"
        if retryable:
            message += " (retryable)"
        super().__init__(message)


def create_llm(llm_config: Any, global_config: Any = None) -> BaseChatModel:
    """Create an LLM instance from configuration.

    This is the main factory function for creating LLM instances. It handles
    provider selection, configuration merging (node-level overrides global),
    and validation.

    Args:
        llm_config: LLMConfig object (can be node-level or global config)
        global_config: Optional global config to merge with (node config takes precedence)

    Returns:
        BaseChatModel instance ready to use

    Raises:
        LLMProviderError: If provider is not supported
        LLMConfigError: If configuration is invalid

    Example:
        >>> from configurable_agents.config import LLMConfig
        >>> config = LLMConfig(provider="google", model="gemini-pro")
        >>> llm = create_llm(config)
    """
    # Import here to avoid issues with config module
    from configurable_agents.config import LLMConfig

    # Handle None config
    if llm_config is None:
        llm_config = LLMConfig()

    # Merge configs if global provided (node overrides global)
    if global_config is not None:
        merged = {}
        # Start with global config
        if global_config.provider is not None:
            merged["provider"] = global_config.provider
        if global_config.model is not None:
            merged["model"] = global_config.model
        if global_config.temperature is not None:
            merged["temperature"] = global_config.temperature
        if global_config.max_tokens is not None:
            merged["max_tokens"] = global_config.max_tokens

        # Override with node config
        if llm_config.provider is not None:
            merged["provider"] = llm_config.provider
        if llm_config.model is not None:
            merged["model"] = llm_config.model
        if llm_config.temperature is not None:
            merged["temperature"] = llm_config.temperature
        if llm_config.max_tokens is not None:
            merged["max_tokens"] = llm_config.max_tokens

        llm_config = LLMConfig(**merged)

    # Default to Google Gemini (v0.1 only provider)
    provider = llm_config.provider or "google"

    # Validate provider
    supported_providers = ["google"]
    if provider not in supported_providers:
        raise LLMProviderError(provider, supported_providers)

    # Route to provider-specific implementation
    if provider == "google":
        from configurable_agents.llm.google import create_google_llm

        return create_google_llm(llm_config)

    # Should never reach here due to validation above
    raise LLMProviderError(provider, supported_providers)


def call_llm_structured(
    llm: BaseChatModel,
    prompt: str,
    output_model: Type[BaseModel],
    tools: Optional[List[BaseTool]] = None,
    max_retries: int = 3,
) -> BaseModel:
    """Call LLM with structured output enforcement.

    This function wraps the LLM call with:
    - Pydantic schema binding for type-enforced outputs
    - Tool binding (if provided)
    - Automatic retry on validation failures
    - Error handling

    Args:
        llm: LLM instance (from create_llm)
        prompt: The prompt to send to the LLM
        output_model: Pydantic model for output validation
        tools: Optional list of tools the LLM can use
        max_retries: Maximum retry attempts on validation failure

    Returns:
        Instance of output_model with validated LLM response

    Raises:
        LLMAPIError: If LLM call fails
        ValidationError: If output doesn't match schema after retries

    Example:
        >>> from pydantic import BaseModel
        >>> class Article(BaseModel):
        ...     title: str
        ...     content: str
        >>> llm = create_llm(config)
        >>> result = call_llm_structured(
        ...     llm, "Write an article about AI", Article
        ... )
        >>> print(result.title)
    """
    from pydantic import ValidationError

    # Bind structured output to LLM
    structured_llm = llm.with_structured_output(output_model)

    # Bind tools if provided
    if tools:
        structured_llm = structured_llm.bind_tools(tools)

    # Attempt call with retries
    last_error = None
    for attempt in range(max_retries):
        try:
            # Call LLM
            result = structured_llm.invoke(prompt)

            # If we got a valid result, return it
            if isinstance(result, output_model):
                return result

            # If result is a dict, try to parse it
            if isinstance(result, dict):
                return output_model(**result)

            # Unexpected result type
            raise LLMAPIError(
                f"LLM returned unexpected type: {type(result).__name__}",
                retryable=False,
            )

        except ValidationError as e:
            last_error = e
            # On validation error, retry with clarified prompt
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                clarified_prompt = (
                    f"{prompt}\n\n"
                    f"Previous attempt failed validation. "
                    f"Please ensure the response matches the required schema exactly."
                )
                prompt = clarified_prompt
            continue

        except Exception as e:
            # Check if it's a retryable error (rate limit, timeout, etc.)
            error_msg = str(e).lower()
            retryable = any(
                keyword in error_msg
                for keyword in ["rate limit", "timeout", "temporarily unavailable"]
            )

            if retryable and attempt < max_retries - 1:
                # Exponential backoff
                wait_time = 2**attempt
                time.sleep(wait_time)
                continue

            # Non-retryable error or out of retries
            raise LLMAPIError(str(e), retryable=retryable) from e

    # Out of retries
    raise last_error


def merge_llm_config(node_config: Any, global_config: Any) -> Any:
    """Merge node-level and global LLM configurations.

    Node-level settings take precedence over global settings.

    Args:
        node_config: Node-level LLMConfig (can be None)
        global_config: Global LLMConfig (can be None)

    Returns:
        Merged LLMConfig with node overrides applied

    Example:
        >>> global_cfg = LLMConfig(provider="google", temperature=0.5)
        >>> node_cfg = LLMConfig(temperature=0.9)
        >>> merged = merge_llm_config(node_cfg, global_cfg)
        >>> print(merged.temperature)  # 0.9 (node override)
        >>> print(merged.provider)     # "google" (from global)
    """
    from configurable_agents.config import LLMConfig

    if node_config is None and global_config is None:
        return LLMConfig()

    if node_config is None:
        return global_config

    if global_config is None:
        return node_config

    # Build merged config
    merged = {}

    # Start with global
    if global_config.provider is not None:
        merged["provider"] = global_config.provider
    if global_config.model is not None:
        merged["model"] = global_config.model
    if global_config.temperature is not None:
        merged["temperature"] = global_config.temperature
    if global_config.max_tokens is not None:
        merged["max_tokens"] = global_config.max_tokens

    # Override with node config
    if node_config.provider is not None:
        merged["provider"] = node_config.provider
    if node_config.model is not None:
        merged["model"] = node_config.model
    if node_config.temperature is not None:
        merged["temperature"] = node_config.temperature
    if node_config.max_tokens is not None:
        merged["max_tokens"] = node_config.max_tokens

    return LLMConfig(**merged)
