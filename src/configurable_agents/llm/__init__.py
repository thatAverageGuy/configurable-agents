"""LLM provider integration.

This module provides the main interface for creating and using LLM instances
in configurable-agents workflows.

Public API:
    - create_llm: Create LLM from configuration
    - call_llm_structured: Call LLM with structured output
    - merge_llm_config: Merge node and global configs
    - LLMConfigError: Configuration error exception
    - LLMProviderError: Provider not supported exception
    - LLMAPIError: API call failure exception

Example:
    >>> from configurable_agents.llm import create_llm, call_llm_structured
    >>> from configurable_agents.config import LLMConfig
    >>> from pydantic import BaseModel
    >>>
    >>> class Output(BaseModel):
    ...     result: str
    >>>
    >>> config = LLMConfig(provider="google", model="gemini-pro")
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

__all__ = [
    "create_llm",
    "call_llm_structured",
    "merge_llm_config",
    "LLMConfigError",
    "LLMProviderError",
    "LLMAPIError",
    "LLMUsageMetadata",
]
