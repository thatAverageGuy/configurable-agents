"""LLM provider integration.

This module provides the main interface for creating and using LLM instances
in configurable-agents workflows.

Multi-provider support (v0.1+):
    Supports OpenAI, Anthropic, Google Gemini, and Ollama via LiteLLM.

Public API:
    - create_llm: Create LLM from configuration
    - call_llm_structured: Call LLM with structured output
    - merge_llm_config: Merge node and global configs
    - stream_chat: Stream chat completion with async generator
    - LLMConfigError: Configuration error exception
    - LLMProviderError: Provider not supported exception
    - LLMAPIError: API call failure exception
    - LITELLM_AVAILABLE: Whether LiteLLM is installed

Example:
    >>> from configurable_agents.llm import create_llm, call_llm_structured, stream_chat
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
    >>>
    >>> # Or stream for chat UI
    >>> async for chunk in stream_chat(llm, "Hello"):
    ...     print(chunk, end="")
"""

import asyncio
from typing import AsyncGenerator, List, Optional, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

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


async def stream_chat(
    llm: BaseChatModel,
    message: str,
    history: Optional[List[tuple[str, str]]] = None,
    system_prompt: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream LLM chat completion with async generator.

    This function provides non-blocking streaming for chat UIs like Gradio.
    It builds conversation context from history and streams response chunks.

    Args:
        llm: LLM instance (from create_llm)
        message: Current user message
        history: Optional conversation history as list of (user, assistant) tuples
        system_prompt: Optional system prompt to prepend

    Yields:
        Response text chunks as they arrive from the LLM

    Example:
        >>> llm = create_llm(config)
        >>> async for chunk in stream_chat(llm, "Hello"):
        ...     print(chunk, end="")
    """
    # Build message list from history
    messages: List[Union[SystemMessage, HumanMessage, AIMessage]] = []

    # Add system prompt if provided
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))

    # Add conversation history (last 10 messages to avoid context overflow)
    if history:
        for user_msg, asst_msg in history[-10:]:
            if user_msg:
                messages.append(HumanMessage(content=user_msg))
            if asst_msg:
                messages.append(AIMessage(content=asst_msg))

    # Add current message
    messages.append(HumanMessage(content=message))

    try:
        # Stream response from LLM
        # LangChain's stream() returns a generator of AIMessage chunks
        for chunk in llm.stream(messages):
            if hasattr(chunk, "content") and chunk.content:
                # Handle both string content and list content
                content = chunk.content
                if isinstance(content, str):
                    yield content
                elif isinstance(content, list):
                    # Handle complex content (e.g., with tool calls)
                    for item in content:
                        if isinstance(item, str):
                            yield item
                        elif hasattr(item, "text"):
                            yield item.text
    except Exception as e:
        raise LLMAPIError(f"Streaming failed: {e}") from e


__all__ = [
    "create_llm",
    "call_llm_structured",
    "merge_llm_config",
    "stream_chat",
    "LLMConfigError",
    "LLMProviderError",
    "LLMAPIError",
    "LLMUsageMetadata",
    "LITELLM_AVAILABLE",
]
