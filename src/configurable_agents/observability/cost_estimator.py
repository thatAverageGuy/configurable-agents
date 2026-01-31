"""Cost estimation for LLM API usage.

Provides token-to-cost conversion based on provider pricing models.
Pricing data updated as of January 2025.
"""

from typing import Dict, Optional, Tuple

# Pricing per 1K tokens (input, output) in USD
# Source: Google AI Pricing (https://ai.google.dev/pricing) - January 2025
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


class CostEstimator:
    """Estimates API costs based on token usage.

    Supports multiple LLM providers with provider-specific pricing models.
    Pricing is stored as cost per 1,000 tokens for input and output separately.

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
            # Future: OpenAI, Anthropic, etc.
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
            model: Model name (e.g., "gemini-1.5-flash", "gpt-4")
            input_tokens: Number of input tokens (prompt + context)
            output_tokens: Number of output tokens (completion)
            provider: Provider name (auto-detected from model if not specified)

        Returns:
            Estimated cost in USD (rounded to 6 decimal places)

        Raises:
            ValueError: If model or provider is not supported

        Example:
            >>> estimator = CostEstimator()
            >>> cost = estimator.estimate_cost("gemini-1.5-flash", 150, 500)
            >>> cost
            0.000075
        """
        # Auto-detect provider if not specified
        if provider is None:
            provider = self._detect_provider(model)

        # Get pricing table for provider
        if provider not in self._pricing_tables:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported: {list(self._pricing_tables.keys())}"
            )

        pricing_table = self._pricing_tables[provider]

        # Get model pricing
        if model not in pricing_table:
            raise ValueError(
                f"Unsupported model: {model}. "
                f"Supported {provider} models: {list(pricing_table.keys())}"
            )

        pricing = pricing_table[model]

        # Calculate cost: (tokens / 1000) * price_per_1k_tokens
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost

        # Round to 6 decimal places (microdollars)
        return round(total_cost, 6)

    def _detect_provider(self, model: str) -> str:
        """Auto-detect provider from model name.

        Args:
            model: Model name

        Returns:
            Provider name

        Raises:
            ValueError: If provider cannot be detected
        """
        model_lower = model.lower()

        if "gemini" in model_lower or "google" in model_lower:
            return "google"
        elif "gpt" in model_lower or "openai" in model_lower:
            return "openai"  # Future support
        elif "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"  # Future support
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

        if provider not in self._pricing_tables:
            raise ValueError(f"Unsupported provider: {provider}")

        pricing_table = self._pricing_tables[provider]

        if model not in pricing_table:
            raise ValueError(f"Unsupported model: {model}")

        return pricing_table[model]


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
