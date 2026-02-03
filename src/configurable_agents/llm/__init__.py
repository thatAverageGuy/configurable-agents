"""LLM provider integration.

This module provides the main interface for creating and using LLM instances
in configurable-agents workflows.

Multi-provider support (v0.1+):
    Supports OpenAI, Anthropic, Google Gemini, and Ollama via LiteLLM.

Public API:
    - create_llm: Create LLM from configuration
    - call_llm_structured: Call LLM with structured output
    - merge_llm_config: Merge node and global configs
    - LLMConfigError: Configuration error exception
    - LLMProviderError: Provider not supported exception
    - LLMAPIError: API call failure exception
    - LITELLM_AVAILABLE: Whether LiteLLM is installed

Example:
    >>> from configurable_agents.llm import create_llm, call_llm_structured
    >>> from configurable_agents.config import LLMConfig
    >>> from pydantic import BaseModel
    >>>
    >>> class Output(BaseModel):
    ...     result: str
    >>>
    >>> config = LLMConfig(provider="openai", model="gpt-4o")
    >>> llm = create_llm(config)
    >>> output = call_llm_structured(llm, "Say hello", Output)
    >>> print(output.result)
"""

from configurable_agents.llm.provider import (
    LLMAPIError,
    LLMConfigError,
    LLMProviderError,
    LLMUsageMetadata,
    call_llm_structured,
    create_llm,
    merge_llm_config,
)

# Try to import LiteLLM availability flag
try:
    from configurable_agents.llm.litellm_provider import LITELLM_AVAILABLE
except ImportError:
    LITELLM_AVAILABLE = False

__all__ = [
    "create_llm",
    "call_llm_structured",
    "merge_llm_config",
    "LLMConfigError",
    "LLMProviderError",
    "LLMAPIError",
    "LLMUsageMetadata",
    "LITELLM_AVAILABLE",
]
