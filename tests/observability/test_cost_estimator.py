"""Unit tests for CostEstimator."""

import pytest

from configurable_agents.observability.cost_estimator import (
    CostEstimator,
    get_model_pricing,
    GEMINI_PRICING,
)


class TestCostEstimator:
    """Test suite for CostEstimator class."""

    def test_estimate_cost_gemini_flash(self):
        """Test cost estimation for Gemini 1.5 Flash."""
        estimator = CostEstimator()

        # 150 input tokens, 500 output tokens
        cost = estimator.estimate_cost(
            model="gemini-1.5-flash",
            input_tokens=150,
            output_tokens=500,
        )

        # Manual calculation:
        # Input: (150 / 1000) * 0.000075 = 0.00001125
        # Output: (500 / 1000) * 0.0003 = 0.00015
        # Total: 0.00016125
        expected = 0.000161  # Rounded to 6 decimals
        assert cost == expected

    def test_estimate_cost_gemini_pro(self):
        """Test cost estimation for Gemini 1.5 Pro."""
        estimator = CostEstimator()

        cost = estimator.estimate_cost(
            model="gemini-1.5-pro",
            input_tokens=100,
            output_tokens=200,
        )

        # Manual calculation:
        # Input: (100 / 1000) * 0.00125 = 0.000125
        # Output: (200 / 1000) * 0.005 = 0.001
        # Total: 0.001125
        expected = 0.001125
        assert cost == expected

    def test_estimate_cost_gemini_flash_lite(self):
        """Test cost estimation for Gemini 2.5 Flash Lite."""
        estimator = CostEstimator()

        cost = estimator.estimate_cost(
            model="gemini-2.5-flash-lite",
            input_tokens=1000,
            output_tokens=2000,
        )

        # Manual calculation:
        # Input: (1000 / 1000) * 0.0001 = 0.0001
        # Output: (2000 / 1000) * 0.0004 = 0.0008
        # Total: 0.0009
        expected = 0.0009
        assert cost == expected

    def test_estimate_cost_zero_tokens(self):
        """Test cost estimation with zero tokens."""
        estimator = CostEstimator()

        cost = estimator.estimate_cost(
            model="gemini-1.5-flash",
            input_tokens=0,
            output_tokens=0,
        )

        assert cost == 0.0

    def test_estimate_cost_only_input_tokens(self):
        """Test cost estimation with only input tokens."""
        estimator = CostEstimator()

        cost = estimator.estimate_cost(
            model="gemini-1.5-flash",
            input_tokens=500,
            output_tokens=0,
        )

        # Input: (500 / 1000) * 0.000075 = 0.0000375
        expected = 0.000037  # Rounded to 6 decimals (0.0000375 -> 0.000037)
        assert cost == expected

    def test_estimate_cost_only_output_tokens(self):
        """Test cost estimation with only output tokens."""
        estimator = CostEstimator()

        cost = estimator.estimate_cost(
            model="gemini-1.5-flash",
            input_tokens=0,
            output_tokens=1000,
        )

        # Output: (1000 / 1000) * 0.0003 = 0.0003
        expected = 0.0003
        assert cost == expected

    def test_estimate_cost_explicit_provider(self):
        """Test cost estimation with explicit provider."""
        estimator = CostEstimator()

        cost = estimator.estimate_cost(
            model="gemini-1.5-flash",
            input_tokens=100,
            output_tokens=200,
            provider="google",
        )

        assert cost > 0

    def test_estimate_cost_unsupported_model(self):
        """Test cost estimation with unsupported model."""
        estimator = CostEstimator()

        with pytest.raises(ValueError, match="Unsupported model"):
            estimator.estimate_cost(
                model="nonexistent-model",
                input_tokens=100,
                output_tokens=200,
                provider="google",
            )

    def test_estimate_cost_unsupported_provider(self):
        """Test cost estimation with unsupported provider."""
        estimator = CostEstimator()

        with pytest.raises(ValueError, match="Unsupported provider"):
            estimator.estimate_cost(
                model="gemini-1.5-flash",
                input_tokens=100,
                output_tokens=200,
                provider="nonexistent",
            )

    def test_detect_provider_gemini(self):
        """Test provider auto-detection for Gemini models."""
        estimator = CostEstimator()

        provider = estimator._detect_provider("gemini-1.5-flash")
        assert provider == "google"

        provider = estimator._detect_provider("gemini-2.5-flash-lite")
        assert provider == "google"

    def test_detect_provider_unknown(self):
        """Test provider auto-detection for unknown models."""
        estimator = CostEstimator()

        with pytest.raises(ValueError, match="Cannot auto-detect provider"):
            estimator._detect_provider("unknown-model-xyz")

    def test_get_pricing(self):
        """Test get_pricing method."""
        estimator = CostEstimator()

        pricing = estimator.get_pricing("gemini-1.5-flash")

        assert pricing["input"] == GEMINI_PRICING["gemini-1.5-flash"]["input"]
        assert pricing["output"] == GEMINI_PRICING["gemini-1.5-flash"]["output"]

    def test_get_pricing_explicit_provider(self):
        """Test get_pricing with explicit provider."""
        estimator = CostEstimator()

        pricing = estimator.get_pricing("gemini-1.5-flash", provider="google")

        assert pricing["input"] == 0.000075
        assert pricing["output"] == 0.0003

    def test_get_pricing_unsupported_model(self):
        """Test get_pricing with unsupported model."""
        estimator = CostEstimator()

        with pytest.raises(ValueError, match="Unsupported model"):
            estimator.get_pricing("nonexistent-model", provider="google")

    def test_get_model_pricing_function(self):
        """Test get_model_pricing convenience function."""
        input_price, output_price = get_model_pricing("gemini-1.5-flash")

        assert input_price == 0.000075
        assert output_price == 0.0003

    def test_get_model_pricing_all_gemini_models(self):
        """Test that all Gemini models have pricing defined."""
        gemini_models = [
            "gemini-3-pro",
            "gemini-3-flash",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.0-pro",
        ]

        estimator = CostEstimator()

        for model in gemini_models:
            # Should not raise
            pricing = estimator.get_pricing(model)
            assert "input" in pricing
            assert "output" in pricing
            assert pricing["input"] > 0
            assert pricing["output"] > 0

    def test_cost_rounding(self):
        """Test that costs are rounded to 6 decimal places."""
        estimator = CostEstimator()

        # Use values that would create more than 6 decimals
        cost = estimator.estimate_cost(
            model="gemini-1.5-flash",
            input_tokens=1,  # Very small cost
            output_tokens=1,
        )

        # Check that result has at most 6 decimal places
        cost_str = f"{cost:.10f}"
        decimal_part = cost_str.split(".")[1]
        # Should be 6 significant decimals or fewer
        assert len(decimal_part.rstrip("0")) <= 6

    def test_large_token_counts(self):
        """Test cost estimation with large token counts."""
        estimator = CostEstimator()

        # 100K input, 50K output tokens
        cost = estimator.estimate_cost(
            model="gemini-1.5-flash",
            input_tokens=100000,
            output_tokens=50000,
        )

        # Input: (100000 / 1000) * 0.000075 = 0.0075
        # Output: (50000 / 1000) * 0.0003 = 0.015
        # Total: 0.0225
        expected = 0.0225
        assert cost == expected
