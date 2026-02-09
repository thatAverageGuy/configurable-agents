"""LLM provider factory and base functionality.

This module provides the main interface for creating and configuring LLM instances
from workflow configuration. It abstracts away provider-specific details.

Multi-provider support (v0.1+):
    Supports OpenAI, Anthropic, Google Gemini, and Ollama via LiteLLM integration.

Example:
    >>> from configurable_agents.llm import create_llm, call_llm_structured
    >>> from configurable_agents.config import LLMConfig
    >>>
    >>> config = LLMConfig(provider="openai", model="gpt-4o", temperature=0.7)
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
            f"Note: LiteLLM is required for multi-provider support. "
            f"Install: pip install litellm>=1.80.0"
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

    Multi-provider support (v0.1+):
        Supports OpenAI, Anthropic, Google Gemini, and Ollama via LiteLLM.
        Falls back to direct Google implementation if LiteLLM unavailable.

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
        >>> config = LLMConfig(provider="openai", model="gpt-4o")
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

    # Default to Google Gemini for backward compatibility
    provider = llm_config.provider or "google"

    # Supported providers (with LiteLLM)
    supported_providers = ["openai", "anthropic", "google", "ollama"]

    # Google provider: use direct implementation for better compatibility
    # The direct Google provider has better compatibility with LangChain features
    # like with_structured_output() and bind_tools()
    if provider == "google":
        from configurable_agents.llm.google import create_google_llm

        return create_google_llm(llm_config)

    # For other providers, try LiteLLM route
    try:
        from configurable_agents.llm.litellm_provider import (
            LITELLM_AVAILABLE,
            create_litellm_llm,
        )

        if LITELLM_AVAILABLE:
            # Validate provider
            if provider not in supported_providers:
                raise LLMProviderError(provider, supported_providers)

            return create_litellm_llm(llm_config)
    except ImportError:
        # LiteLLM not available, can't support non-Google providers
        pass

    # If we reach here, provider is not supported without LiteLLM
    raise LLMProviderError(
        provider,
        ["google"],  # Only Google works without LiteLLM
    )


class LLMUsageMetadata:
    """Token usage metadata from LLM response."""

    def __init__(self, input_tokens: int, output_tokens: int):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


def _execute_tool_loop(
    llm: BaseChatModel,
    prompt: str,
    tools: List[BaseTool],
    max_iterations: int = 10,
) -> tuple[str, LLMUsageMetadata]:
    """Execute tool calls in a loop until the LLM stops requesting tools.

    Binds tools to the LLM and runs an agent loop:
    invoke LLM -> detect tool calls -> execute tools -> feed results back -> repeat.

    After the loop, returns an enriched prompt containing the original prompt
    plus all tool results, suitable for a follow-up structured output call.

    Args:
        llm: Base LLM instance (tools will be bound to a copy)
        prompt: The original user prompt
        tools: List of LangChain BaseTool instances
        max_iterations: Safety limit on tool call rounds (default 10)

    Returns:
        Tuple of (enriched_prompt with tool results, token usage from tool loop)
    """
    import logging
    from langchain_core.messages import HumanMessage, ToolMessage as LCToolMessage

    logger = logging.getLogger(__name__)

    # Bind tools to LLM (without structured output)
    try:
        from langchain_litellm import ChatLiteLLM
        if isinstance(llm, ChatLiteLLM):
            model = getattr(llm, "model", "")
            if isinstance(model, str) and "gemini/" in model:
                llm_with_tools = llm.bind_tools(tools, tool_choice="auto")
            else:
                llm_with_tools = llm.bind_tools(tools)
        else:
            llm_with_tools = llm.bind_tools(tools)
    except (ImportError, AttributeError):
        llm_with_tools = llm.bind_tools(tools)

    messages = [HumanMessage(content=prompt)]
    total_input_tokens = 0
    total_output_tokens = 0
    tool_results = []

    for iteration in range(max_iterations):
        response = llm_with_tools.invoke(messages)

        # Track token usage
        usage_data = getattr(response, "usage_metadata", None)
        if usage_data:
            total_input_tokens += getattr(usage_data, "input_tokens", 0)
            total_output_tokens += getattr(usage_data, "output_tokens", 0)

        messages.append(response)

        # Check for tool calls
        if not getattr(response, "tool_calls", None):
            break

        logger.debug(
            f"Tool loop iteration {iteration + 1}: "
            f"{len(response.tool_calls)} tool call(s)"
        )

        # Execute each tool call
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call.get("id", f"call_{iteration}")

            # Find matching tool
            tool = next((t for t in tools if t.name == tool_name), None)
            if tool is None:
                result_str = f"Error: Tool '{tool_name}' not found"
                logger.warning(f"Tool '{tool_name}' not found in registry")
            else:
                try:
                    logger.debug(f"Executing tool '{tool_name}' with args: {tool_args}")
                    result = tool.invoke(tool_args)
                    result_str = str(result)
                    # Truncate very large tool results to avoid prompt overflow
                    if len(result_str) > 8000:
                        result_str = result_str[:8000] + "\n... (truncated)"
                    logger.debug(f"Tool '{tool_name}' returned {len(result_str)} chars")
                except Exception as e:
                    result_str = f"Error executing tool '{tool_name}': {e}"
                    logger.warning(f"Tool '{tool_name}' execution failed: {e}")

            tool_results.append((tool_name, result_str))
            messages.append(LCToolMessage(
                content=result_str,
                tool_call_id=tool_call_id,
            ))

    # Build enriched prompt with tool results for structured output phase
    if tool_results:
        tool_context = "\n\n".join(
            f"[{name}]:\n{result}" for name, result in tool_results
        )
        enriched_prompt = (
            f"{prompt}\n\n"
            f"Tool Results:\n{tool_context}\n\n"
            f"Using the tool results above, provide your response."
        )
        logger.info(f"Tool loop complete: {len(tool_results)} tool(s) executed")
    else:
        enriched_prompt = prompt
        logger.debug("Tool loop complete: no tools were called by the LLM")

    usage = LLMUsageMetadata(total_input_tokens, total_output_tokens)
    return enriched_prompt, usage


def call_llm_structured(
    llm: BaseChatModel,
    prompt: str,
    output_model: Type[BaseModel],
    tools: Optional[List[BaseTool]] = None,
    max_retries: int = 3,
) -> tuple[BaseModel, LLMUsageMetadata]:
    """Call LLM with structured output enforcement.

    This function wraps the LLM call with:
    - Pydantic schema binding for type-enforced outputs
    - Tool binding (if provided)
    - Automatic retry on validation failures
    - Error handling
    - Token usage extraction

    Args:
        llm: LLM instance (from create_llm)
        prompt: The prompt to send to the LLM
        output_model: Pydantic model for output validation
        tools: Optional list of tools the LLM can use
        max_retries: Maximum retry attempts on validation failure

    Returns:
        Tuple of (output_model instance, usage_metadata)

    Raises:
        LLMAPIError: If LLM call fails
        ValidationError: If output doesn't match schema after retries

    Example:
        >>> from pydantic import BaseModel
        >>> class Article(BaseModel):
        ...     title: str
        ...     content: str
        >>> llm = create_llm(config)
        >>> result, usage = call_llm_structured(
        ...     llm, "Write an article about AI", Article
        ... )
        >>> print(result.title)
        >>> print(f"Tokens: {usage.input_tokens + usage.output_tokens}")
    """
    from pydantic import ValidationError

    # Track total token usage across tool loop and structured output phases
    total_input_tokens = 0
    total_output_tokens = 0

    # Phase 1: Tool execution loop (if tools provided)
    # Execute tools first, enrich prompt with results, then extract structured output
    if tools:
        prompt, tool_usage = _execute_tool_loop(llm, prompt, tools)
        total_input_tokens += tool_usage.input_tokens
        total_output_tokens += tool_usage.output_tokens

    # Phase 2: Structured output extraction (clean LLM, no tools bound)
    structured_llm = llm.with_structured_output(output_model, include_raw=True)

    # Attempt call with retries
    last_error = None
    for attempt in range(max_retries):
        try:
            # Call LLM with include_raw=True to get usage metadata
            response = structured_llm.invoke(prompt)

            # Extract structured output and raw response
            # with_structured_output(include_raw=True) returns dict with 'parsed' and 'raw'
            if isinstance(response, dict) and "parsed" in response and "raw" in response:
                result = response["parsed"]
                raw_message = response["raw"]

                # Extract token usage from raw message
                usage_data = getattr(raw_message, "usage_metadata", None)
                if usage_data:
                    input_tokens = getattr(usage_data, "input_tokens", 0)
                    output_tokens = getattr(usage_data, "output_tokens", 0)
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens
            else:
                # Fallback for unexpected response format
                result = response

            # Validate result
            if isinstance(result, output_model):
                usage = LLMUsageMetadata(total_input_tokens, total_output_tokens)
                return result, usage

            # If result is a dict, try to parse it
            if isinstance(result, dict):
                parsed = output_model(**result)
                usage = LLMUsageMetadata(total_input_tokens, total_output_tokens)
                return parsed, usage

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
