"""Unit tests for MultiProviderCostTracker."""

from dataclasses import dataclass
from unittest.mock import Mock, MagicMock, patch
import pytest

from configurable_agents.observability.multi_provider_tracker import (
    MultiProviderCostTracker,
    generate_cost_report,
    _extract_provider,
    _is_ollama_model,
    ProviderCostEntry,
    ProviderCostSummary,
)


# Mock LLM response objects
@dataclass
class MockUsage:
    """Mock usage object for LLM responses."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class MockLLMResponse:
    """Mock LLM response object."""

    usage: MockUsage


class TestProviderDetection:
    """Test suite for provider detection functions."""

    def test_provider_detection_openai_with_prefix(self):
        """Test OpenAI detection with provider prefix."""
        assert _extract_provider("openai/gpt-4o") == "openai"
        assert _extract_provider("openai/gpt-4-turbo") == "openai"
        assert _extract_provider("openai/gpt-3.5-turbo") == "openai"

    def test_provider_detection_openai_bare_model(self):
        """Test OpenAI detection from bare model name."""
        assert _extract_provider("gpt-4o") == "openai"
        assert _extract_provider("gpt-4-turbo") == "openai"
        assert _extract_provider("gpt-3.5-turbo") == "openai"

    def test_provider_detection_anthropic_with_prefix(self):
        """Test Anthropic detection with provider prefix."""
        assert _extract_provider("anthropic/claude-3-opus") == "anthropic"
        assert _extract_provider("anthropic/claude-3-sonnet") == "anthropic"

    def test_provider_detection_anthropic_bare_model(self):
        """Test Anthropic detection from bare model name."""
        assert _extract_provider("claude-3-opus") == "anthropic"
        assert _extract_provider("claude-3-sonnet") == "anthropic"
        assert _extract_provider("claude-3-haiku") == "anthropic"

    def test_provider_detection_google_with_prefix(self):
        """Test Google detection with provider prefix."""
        assert _extract_provider("google/gemini-pro") == "google"
        assert _extract_provider("google/gemini-1.5-flash") == "google"

    def test_provider_detection_google_bare_model(self):
        """Test Google detection from bare model name."""
        assert _extract_provider("gemini-pro") == "google"
        assert _extract_provider("gemini-1.5-flash") == "google"
        assert _extract_provider("gemini-2.5-flash") == "google"

    def test_provider_detection_ollama_with_prefix(self):
        """Test Ollama detection with provider prefix."""
        assert _extract_provider("ollama/llama2") == "ollama"
        assert _extract_provider("ollama/mistral") == "ollama"

    def test_provider_detection_ollama_chat_prefix(self):
        """Test Ollama detection with ollama_chat prefix."""
        assert _extract_provider("ollama_chat/llama3") == "ollama"

    def test_provider_detection_local_models(self):
        """Test Ollama detection for common local model names."""
        assert _extract_provider("llama2") == "ollama"
        assert _extract_provider("llama3") == "ollama"
        assert _extract_provider("mistral") == "ollama"
        assert _extract_provider("qwen") == "ollama"
        assert _extract_provider("phi") == "ollama"
        assert _extract_provider("gemma") == "ollama"
        assert _extract_provider("deepseek") == "ollama"

    def test_provider_detection_unknown(self):
        """Test provider detection for unknown models."""
        assert _extract_provider("unknown-model") == "unknown"
        assert _extract_provider("some-random-name") == "unknown"

    def test_is_ollama_model(self):
        """Test _is_ollama_model helper."""
        assert _is_ollama_model("ollama") is True
        assert _is_ollama_model("openai") is False
        assert _is_ollama_model("anthropic") is False
        assert _is_ollama_model("google") is False


class TestMultiProviderCostTracker:
    """Test suite for MultiProviderCostTracker class."""

    def test_tracker_initialization_without_mlflow(self):
        """Test tracker initialization without MLFlow tracker."""
        tracker = MultiProviderCostTracker()

        assert tracker.mlflow_tracker is None
        assert tracker.cost_estimator is not None
        assert len(tracker.get_history()) == 0

    def test_tracker_initialization_with_mlflow(self):
        """Test tracker initialization with MLFlow tracker."""
        mock_mlflow_tracker = Mock()
        tracker = MultiProviderCostTracker(mlflow_tracker=mock_mlflow_tracker)

        assert tracker.mlflow_tracker is mock_mlflow_tracker
        assert tracker.cost_estimator is not None

    def test_track_call_extracts_tokens_from_response_object(self):
        """Test token extraction from LLM response object."""
        tracker = MultiProviderCostTracker()

        # Create mock response with usage object
        mock_usage = MockUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        mock_response = MockLLMResponse(usage=mock_usage)

        result = tracker.track_call("google", "gemini-1.5-flash", mock_response)

        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["provider"] == "google"
        assert result["model"] == "gemini-1.5-flash"

    def test_track_call_extracts_tokens_from_dict(self):
        """Test token extraction from dict response."""
        tracker = MultiProviderCostTracker()

        # Create dict-style response
        mock_response = {
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "total_tokens": 300
            }
        }

        result = tracker.track_call("google", "gemini-1.5-pro", mock_response)

        assert result["input_tokens"] == 200
        assert result["output_tokens"] == 100
        assert result["total_tokens"] == 300

    def test_track_call_handles_none_response(self):
        """Test tracking with None response."""
        tracker = MultiProviderCostTracker()

        result = tracker.track_call("google", "gemini-1.5-flash", None)

        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0
        assert result["total_tokens"] == 0
        assert result["cost_usd"] == 0.0

    def test_track_call_calculates_cost_for_google(self):
        """Test cost calculation for Google models."""
        tracker = MultiProviderCostTracker()

        mock_usage = MockUsage(
            prompt_tokens=150,
            completion_tokens=500,
            total_tokens=650
        )
        mock_response = MockLLMResponse(usage=mock_usage)

        result = tracker.track_call("google", "gemini-1.5-flash", mock_response)

        # gemini-1.5-flash: input $0.000075/1K, output $0.0003/1K
        # Input: (150 / 1000) * 0.000075 = 0.00001125
        # Output: (500 / 1000) * 0.0003 = 0.00015
        # Total: ~0.000161
        assert result["cost_usd"] > 0
        assert round(result["cost_usd"], 6) == 0.000161

    def test_ollama_zero_cost(self):
        """Test that Ollama models return zero cost."""
        tracker = MultiProviderCostTracker()

        mock_usage = MockUsage(
            prompt_tokens=1000,
            completion_tokens=2000,
            total_tokens=3000
        )
        mock_response = MockLLMResponse(usage=mock_usage)

        result = tracker.track_call("ollama", "llama2", mock_response)

        assert result["cost_usd"] == 0.0

    def test_track_call_stores_in_history(self):
        """Test that tracked calls are stored in history."""
        tracker = MultiProviderCostTracker()

        mock_usage = MockUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        mock_response = MockLLMResponse(usage=mock_usage)

        tracker.track_call("google", "gemini-1.5-flash", mock_response)

        history = tracker.get_history()
        assert len(history) == 1
        assert history[0].provider == "google"
        assert history[0].model == "gemini-1.5-flash"
        assert history[0].total_tokens == 150

    def test_cost_summary_aggregation_single_provider(self):
        """Test cost summary aggregation for single provider."""
        tracker = MultiProviderCostTracker()

        # Track multiple calls - use Google model which has pricing defined
        for i in range(3):
            mock_usage = MockUsage(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150
            )
            mock_response = MockLLMResponse(usage=mock_usage)
            tracker.track_call("google", "gemini-1.5-flash", mock_response)

        summary = tracker.get_cost_summary()

        assert summary.total_calls == 3
        assert summary.total_tokens == 450  # 3 * 150
        assert summary.total_cost_usd > 0
        assert "google" in summary.by_provider

    def test_cost_summary_by_provider(self):
        """Test by_provider breakdown is correct."""
        tracker = MultiProviderCostTracker()

        # Track Google calls
        mock_usage_google = MockUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        mock_response_google = MockLLMResponse(usage=mock_usage_google)
        tracker.track_call("google", "gemini-1.5-flash", mock_response_google)
        tracker.track_call("google", "gemini-1.5-flash", mock_response_google)

        # Track Ollama calls (zero cost)
        mock_usage_ollama = MockUsage(
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300
        )
        mock_response_ollama = MockLLMResponse(usage=mock_usage_ollama)
        tracker.track_call("ollama", "llama2", mock_response_ollama)

        summary = tracker.get_cost_summary()

        # Check both providers present
        assert "google" in summary.by_provider
        assert "ollama" in summary.by_provider

        # Check Google aggregation
        google_data = summary.by_provider["google"]
        assert google_data["calls"] == 2
        assert google_data["total_tokens"] == 300  # 2 * 150
        assert google_data["total_cost_usd"] > 0

        # Check Ollama aggregation (zero cost)
        ollama_data = summary.by_provider["ollama"]
        assert ollama_data["calls"] == 1
        assert ollama_data["total_tokens"] == 300
        assert ollama_data["total_cost_usd"] == 0.0

    def test_cost_summary_with_ollama(self):
        """Test cost summary includes Ollama with zero cost."""
        tracker = MultiProviderCostTracker()

        # Track Ollama call (should be zero cost)
        mock_usage_ollama = MockUsage(
            prompt_tokens=1000,
            completion_tokens=2000,
            total_tokens=3000
        )
        mock_response_ollama = MockLLMResponse(usage=mock_usage_ollama)
        tracker.track_call("ollama", "llama2", mock_response_ollama)

        # Track Google call (should have cost)
        mock_usage_google = MockUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        mock_response_google = MockLLMResponse(usage=mock_usage_google)
        tracker.track_call("google", "gemini-1.5-flash", mock_response_google)

        summary = tracker.get_cost_summary()

        # Ollama should be present with zero cost
        assert "ollama" in summary.by_provider
        assert summary.by_provider["ollama"]["total_cost_usd"] == 0.0
        assert summary.by_provider["ollama"]["total_tokens"] == 3000

        # Google should have cost
        assert summary.by_provider["google"]["total_cost_usd"] > 0

    def test_cost_summary_empty_history(self):
        """Test cost summary with no tracked calls."""
        tracker = MultiProviderCostTracker()

        summary = tracker.get_cost_summary()

        assert summary.total_cost_usd == 0.0
        assert summary.total_tokens == 0
        assert summary.total_calls == 0
        assert summary.by_provider == {}

    def test_clear_history(self):
        """Test clearing call history."""
        tracker = MultiProviderCostTracker()

        # Add some calls
        mock_usage = MockUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        mock_response = MockLLMResponse(usage=mock_usage)
        tracker.track_call("openai", "gpt-4o", mock_response)

        assert len(tracker.get_history()) == 1

        # Clear history
        tracker.clear_history()

        assert len(tracker.get_history()) == 0

        # Summary should be empty
        summary = tracker.get_cost_summary()
        assert summary.total_calls == 0

    def test_generate_report_requires_mlflow(self):
        """Test that generate_report requires MLFlow."""
        tracker = MultiProviderCostTracker()

        with patch("configurable_agents.observability.multi_provider_tracker.MLFLOW_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="MLFlow is not installed"):
                tracker.generate_report("test_experiment")

    def test_generate_report_experiment_not_found(self):
        """Test generate_report with non-existent experiment."""
        tracker = MultiProviderCostTracker()

        with patch("configurable_agents.observability.multi_provider_tracker.MLFLOW_AVAILABLE", True):
            with patch("mlflow.get_experiment_by_name") as mock_get_exp:
                mock_get_exp.return_value = None  # Experiment not found

                with pytest.raises(ValueError, match="Experiment not found"):
                    tracker.generate_report("nonexistent_experiment")


class TestGenerateCostReport:
    """Test suite for standalone generate_cost_report function."""

    def test_generate_cost_report_requires_mlflow(self):
        """Test that generate_cost_report requires MLFlow."""
        with patch("configurable_agents.observability.multi_provider_tracker.MLFLOW_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="MLFlow is not installed"):
                generate_cost_report("test_experiment")

    @patch("configurable_agents.observability.multi_provider_tracker.MLFLOW_AVAILABLE", True)
    @patch("configurable_agents.observability.multi_provider_tracker.mlflow")
    @patch("configurable_agents.observability.multi_provider_tracker.MlflowClient")
    def test_generate_cost_report_success(self, mock_client_class, mock_mlflow):
        """Test successful cost report generation."""
        # Mock experiment
        mock_experiment = Mock()
        mock_experiment.experiment_id = "exp-123"
        mock_mlflow.get_experiment_by_name.return_value = mock_experiment

        # Mock client
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock runs with provider/model params and metrics
        mock_run = Mock()
        mock_run.data.params = {
            "provider": "openai",
            "model": "gpt-4o",
        }
        mock_run.data.metrics = {
            "total_cost_usd": 0.001,
            "total_tokens": 1000,
        }
        mock_client.search_runs.return_value = [mock_run]

        result = generate_cost_report("test_experiment")

        assert result["experiment"] == "test_experiment"
        assert result["experiment_id"] == "exp-123"
        assert result["total_cost_usd"] == 0.001
        assert result["total_tokens"] == 1000
        assert "by_provider" in result
        assert "openai" in result["by_provider"]


class TestProviderCostEntry:
    """Test suite for ProviderCostEntry dataclass."""

    def test_provider_cost_entry_creation(self):
        """Test creating a ProviderCostEntry."""
        entry = ProviderCostEntry(
            provider="openai",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.001
        )

        assert entry.provider == "openai"
        assert entry.model == "gpt-4o"
        assert entry.input_tokens == 100
        assert entry.output_tokens == 50
        assert entry.total_tokens == 150
        assert entry.cost_usd == 0.001
        assert entry.timestamp is not None  # Should have default timestamp


class TestProviderCostSummary:
    """Test suite for ProviderCostSummary dataclass."""

    def test_provider_cost_summary_creation(self):
        """Test creating a ProviderCostSummary."""
        summary = ProviderCostSummary(
            total_cost_usd=0.01,
            total_tokens=5000,
            by_provider={
                "openai": {
                    "total_cost_usd": 0.006,
                    "total_tokens": 3000,
                    "calls": 10,
                },
                "anthropic": {
                    "total_cost_usd": 0.004,
                    "total_tokens": 2000,
                    "calls": 5,
                }
            },
            total_calls=15
        )

        assert summary.total_cost_usd == 0.01
        assert summary.total_tokens == 5000
        assert summary.total_calls == 15
        assert len(summary.by_provider) == 2
