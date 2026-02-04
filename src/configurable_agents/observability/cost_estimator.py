"""Cost estimation for LLM API usage.

Provides token-to-cost conversion based on provider pricing models.
Uses LiteLLM pricing when available, with fallback to hardcoded pricing.
Pricing data updated as of January 2025.
"""

from typing import Dict, Optional, Tuple

# Check for LiteLLM availability
try:
    import litellm

    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    litellm = None  # type: ignore

# Pricing per 1K tokens (input, output) in USD
# Source: Google AI Pricing (https://ai.google.dev/pricing) - January 2025
# Used as fallback when LiteLLM is unavailable
GEMINI_PRICING = {
    "gemini-3-pro": {
        "input": 0.002,  # $0.00200 per 1K input tokens
        "output": 0.012,  # $0.01200 per 1K output tokens
    },
    "gemini-3-flash": {
        "input": 0.0005,  # $0.00050 per 1K input tokens
        "output": 0.003,  # $0.00300 per 1K output tokens
    },
    "gemini-2.5-pro": {
        "input": 0.00125,  # $0.00125 per 1K input tokens
        "output": 0.010,  # $0.01000 per 1K output tokens
    },
    "gemini-2.5-flash": {
        "input": 0.0003,  # $0.00030 per 1K input tokens
        "output": 0.0025,  # $0.00250 per 1K output tokens
    },
    "gemini-2.5-flash-lite": {
        "input": 0.0001,  # $0.00010 per 1K input tokens
        "output": 0.0004,  # $0.00040 per 1K output tokens
    },
    "gemini-1.5-pro": {
        "input": 0.00125,  # $0.00125 per 1K input tokens
        "output": 0.005,  # $0.00500 per 1K output tokens
    },
    "gemini-1.5-flash": {
        "input": 0.000075,  # $0.000075 per 1K input tokens
        "output": 0.0003,  # $0.000300 per 1K output tokens
    },
    "gemini-1.5-flash-8b": {
        "input": 0.0000375,  # $0.0000375 per 1K input tokens
        "output": 0.00015,  # $0.0001500 per 1K output tokens
    },
    "gemini-1.0-pro": {
        "input": 0.0005,  # $0.00050 per 1K input tokens
        "output": 0.0015,  # $0.00150 per 1K output tokens
    },
}

# Ollama models are local and free (zero cost)
_OLLAMA_PRICING = {
    "input": 0.0,
    "output": 0.0,
}


class CostEstimator:
    """Estimates API costs based on token usage.

    Supports multiple LLM providers with provider-specific pricing models.
    Uses LiteLLM pricing data when available for accurate cost tracking.

    Example:
        >>> estimator = CostEstimator()
        >>> cost = estimator.estimate_cost("gemini-1.5-flash", input_tokens=150, output_tokens=500)
        >>> print(f"Estimated cost: ${cost:.6f}")
        Estimated cost: $0.000075
    """

    def __init__(self):
        """Initialize cost estimator with current pricing data."""
        self._pricing_tables = {
            "google": GEMINI_PRICING,
            "ollama": {"default": _OLLAMA_PRICING},
        }

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: Optional[str] = None,
    ) -> float:
        """Calculate estimated cost in USD for an LLM API call.

        Args:
            model: Model name (e.g., "gemini-1.5-flash", "gpt-4", "openai/gpt-4o")
            input_tokens: Number of input tokens (prompt + context)
            output_tokens: Number of output tokens (completion)
            provider: Provider name (auto-detected from model if not specified)

        Returns:
            Estimated cost in USD (rounded to 6 decimal places)

        Example:
            >>> estimator = CostEstimator()
            >>> cost = estimator.estimate_cost("gemini-1.5-flash", 150, 500)
            >>> cost
            0.000075
        """
        # Handle LiteLLM-style model strings (e.g., "openai/gpt-4o")
        base_model = model
        if "/" in model:
            # Extract base model from "provider/model" format
            base_model = model.split("/", 1)[1]

        # Auto-detect provider if not specified
        if provider is None:
            provider = self._detect_provider(model)

        # Ollama models are free
        if provider == "ollama":
            return 0.0

        # Try LiteLLM pricing first (most accurate, supports all providers)
        if LITELLM_AVAILABLE:
            try:
                # LiteLLM's cost_per_token returns standard pricing
                input_cost = litellm.cost_per_token(model=model, input_tokens=input_tokens)  # type: ignore
                output_cost = litellm.cost_per_token(  # type: ignore
                    model=model, output_tokens=output_tokens
                )
                return round(input_cost + output_cost, 6)
            except Exception:
                # Fall through to hardcoded pricing if LiteLLM lookup fails
                pass

        # Fallback to hardcoded pricing tables
        pricing_table = self._pricing_tables.get(provider, {})

        if not pricing_table:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported: {list(self._pricing_tables.keys())}"
            )

        # For pricing tables with single "default" entry (like Ollama)
        if "default" in pricing_table:
            pricing = pricing_table["default"]
        elif base_model in pricing_table:
            pricing = pricing_table[base_model]
        else:
            raise ValueError(
                f"Unsupported model: {base_model}. "
                f"Supported {provider} models: {list(pricing_table.keys())}"
            )

        # Calculate cost: (tokens / 1000) * price_per_1k_tokens
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost

        # Round to 6 decimal places (microdollars)
        return round(total_cost, 6)

    def _detect_provider(self, model: str) -> str:
        """Auto-detect provider from model name.

        Handles both bare model names ("gpt-4o") and LiteLLM-style
        provider-prefixed names ("openai/gpt-4o").

        Args:
            model: Model name

        Returns:
            Provider name

        Raises:
            ValueError: If provider cannot be detected
        """
        model_lower = model.lower()

        # Check for LiteLLM-style provider prefix
        if "/" in model_lower:
            provider_prefix = model_lower.split("/", 1)[0]
            provider_map = {
                "openai": "openai",
                "anthropic": "anthropic",
                "gemini": "google",
                "ollama_chat": "ollama",
                "ollama": "ollama",
            }
            if provider_prefix in provider_map:
                return provider_map[provider_prefix]

        # Auto-detect from model name
        if "gemini" in model_lower or "google" in model_lower:
            return "google"
        elif "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif "llama" in model_lower or "mistral" in model_lower or "qwen" in model_lower:
            # Common local models, assume Ollama
            return "ollama"
        else:
            raise ValueError(
                f"Cannot auto-detect provider for model: {model}. "
                f"Please specify provider explicitly."
            )

    def get_pricing(
        self, model: str, provider: Optional[str] = None
    ) -> Dict[str, float]:
        """Get pricing information for a specific model.

        Args:
            model: Model name
            provider: Provider name (auto-detected if not specified)

        Returns:
            Dict with "input" and "output" pricing per 1K tokens

        Raises:
            ValueError: If model or provider is not supported

        Example:
            >>> estimator = CostEstimator()
            >>> pricing = estimator.get_pricing("gemini-1.5-flash")
            >>> pricing
            {'input': 0.000035, 'output': 0.00014}
        """
        if provider is None:
            provider = self._detect_provider(model)

        # Ollama is free
        if provider == "ollama":
            return {"input": 0.0, "output": 0.0}

        # Try LiteLLM first
        if LITELLM_AVAILABLE:
            try:
                # Get standard pricing from LiteLLM
                # Note: LiteLLM doesn't expose a direct pricing lookup,
                # so we use cost_per_token with 1000 tokens
                input_price = litellm.cost_per_token(model=model, input_tokens=1000)  # type: ignore
                output_price = litellm.cost_per_token(model=model, output_tokens=1000)  # type: ignore
                return {"input": input_price, "output": output_price}
            except Exception:
                pass

        # Fallback to hardcoded pricing
        if provider not in self._pricing_tables:
            raise ValueError(f"Unsupported provider: {provider}")

        pricing_table = self._pricing_tables[provider]

        # Handle bare model name
        base_model = model.split("/")[-1] if "/" in model else model

        if "default" in pricing_table:
            return pricing_table["default"]
        elif base_model in pricing_table:
            return pricing_table[base_model]
        else:
            raise ValueError(f"Unsupported model: {model}")


def get_model_pricing(model: str) -> Tuple[float, float]:
    """Get pricing for a model (convenience function).

    Args:
        model: Model name

    Returns:
        Tuple of (input_price_per_1k, output_price_per_1k)

    Raises:
        ValueError: If model is not supported

    Example:
        >>> input_price, output_price = get_model_pricing("gemini-1.5-flash")
        >>> input_price
        0.000035
        >>> output_price
        0.00014
    """
    estimator = CostEstimator()
    pricing = estimator.get_pricing(model)
    return pricing["input"], pricing["output"]
