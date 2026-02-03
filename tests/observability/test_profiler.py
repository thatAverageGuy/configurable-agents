"""Tests for performance profiling decorator."""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from configurable_agents.runtime.profiler import (
    BottleneckAnalyzer,
    NodeTimings,
    clear_profiler,
    get_profiler,
    profile_node,
    set_profiler,
)


class TestProfileNodeSync:
    """Test profile_node decorator with synchronous functions."""

    def test_profile_node_times_sync_function(self):
        """Test that decorator measures timing accurately for sync function."""
        @profile_node("test_node")
        def sync_function():
            time.sleep(0.01)
            return "done"

        result = sync_function()
        assert result == "done"

    def test_profile_node_captures_exception(self):
        """Test that timing is captured even when function raises exception."""
        analyzer = BottleneckAnalyzer()
        set_profiler(analyzer)

        @profile_node("error_node")
        def error_function():
            time.sleep(0.005)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            error_function()

        # Timing should still be recorded
        summary = analyzer.get_summary()
        assert summary["node_count"] == 1
        assert "error_node" in [t.node_id for t in analyzer._timings.values()]

        clear_profiler()

    def test_profile_node_multiple_calls_aggregate_timing(self):
        """Test that multiple calls to same node aggregate correctly."""
        analyzer = BottleneckAnalyzer()
        set_profiler(analyzer)

        @profile_node("multi_call_node")
        def multi_function():
            time.sleep(0.005)
            return "result"

        multi_function()
        multi_function()
        multi_function()

        summary = analyzer.get_summary()
        assert summary["node_count"] == 1

        timings = analyzer._timings["multi_call_node"]
        assert timings.call_count == 3
        assert timings.total_duration_ms > 0
        assert timings.avg_duration_ms == timings.total_duration_ms / 3

        clear_profiler()


class TestProfileNodeAsync:
    """Test profile_node decorator with async functions."""

    @pytest.mark.asyncio
    async def test_profile_node_times_async_function(self):
        """Test that decorator measures timing accurately for async function."""
        @profile_node("async_node")
        async def async_function():
            await asyncio.sleep(0.01)
            return "async_done"

        result = await async_function()
        assert result == "async_done"

    @pytest.mark.asyncio
    async def test_profile_node_async_captures_exception(self):
        """Test that timing is captured when async function raises exception."""
        analyzer = BottleneckAnalyzer()
        set_profiler(analyzer)

        @profile_node("async_error_node")
        async def async_error_function():
            await asyncio.sleep(0.005)
            raise ValueError("Async error")

        with pytest.raises(ValueError, match="Async error"):
            await async_error_function()

        # Timing should still be recorded
        summary = analyzer.get_summary()
        assert summary["node_count"] == 1
        assert "async_error_node" in [t.node_id for t in analyzer._timings.values()]

        clear_profiler()


class TestTimingStorageInThreadLocalContext:
    """Test that timing is stored in global context."""

    def test_timing_stored_in_thread_local_context(self):
        """Test that timing stored in global context via set_profiler."""
        analyzer = BottleneckAnalyzer()
        set_profiler(analyzer)

        # Verify get_profiler returns the same instance
        retrieved = get_profiler()
        assert retrieved is analyzer
        assert retrieved.enabled is True

        clear_profiler()

    def test_clear_profiler_removes_from_context(self):
        """Test that clear_profiler removes analyzer from thread-local context."""
        analyzer = BottleneckAnalyzer()
        set_profiler(analyzer)

        assert get_profiler() is analyzer

        clear_profiler()
        assert get_profiler() is None


class TestMLFlowLogging:
    """Test MLFlow metric logging."""

    def test_profile_node_logs_to_mlflow(self):
        """Test that decorator logs duration to MLFlow (mocked)."""
        analyzer = BottleneckAnalyzer()
        set_profiler(analyzer)

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = MagicMock()

        with patch("configurable_agents.runtime.profiler.mlflow", mock_mlflow):
            with patch("configurable_agents.runtime.profiler.MLFLOW_AVAILABLE", True):
                @profile_node("mlflow_test_node")
                def test_function():
                    time.sleep(0.005)
                    return "done"

                test_function()

                # Verify MLFlow metric was logged
                mock_mlflow.log_metric.assert_called()
                call_args = mock_mlflow.log_metric.call_args
                assert call_args[0][0] == "node_mlflow_test_node_duration_ms"
                assert call_args[0][1] > 0

        clear_profiler()

    def test_profile_node_graceful_mlflow_failure(self):
        """Test that function works even when MLFlow logging fails."""
        analyzer = BottleneckAnalyzer()
        set_profiler(analyzer)

        mock_mlflow = MagicMock()
        mock_mlflow.active_run.return_value = MagicMock()
        mock_mlflow.log_metric.side_effect = Exception("MLFlow error")

        with patch("configurable_agents.runtime.profiler.mlflow", mock_mlflow):
            with patch("configurable_agents.runtime.profiler.MLFLOW_AVAILABLE", True):
                @profile_node("failing_mlflow_node")
                def test_function():
                    return "done"

                # Should not raise exception
                result = test_function()
                assert result == "done"

                # Timing should still be recorded to analyzer
                summary = analyzer.get_summary()
                assert summary["node_count"] == 1

        clear_profiler()


class TestNodeTimingsDataclass:
    """Test NodeTimings dataclass."""

    def test_node_timings_initial_state(self):
        """Test that NodeTimings initializes with correct defaults."""
        timings = NodeTimings(node_id="test_node")

        assert timings.node_id == "test_node"
        assert timings.call_count == 0
        assert timings.total_duration_ms == 0.0
        assert timings.avg_duration_ms == 0.0
        assert timings.timestamps == []

    def test_node_timings_add_call(self):
        """Test that add_call correctly aggregates timing data."""
        timings = NodeTimings(node_id="test_node")

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        timings.add_call(100.0, now)
        assert timings.call_count == 1
        assert timings.total_duration_ms == 100.0
        assert timings.avg_duration_ms == 100.0
        assert len(timings.timestamps) == 1

        timings.add_call(200.0, now)
        assert timings.call_count == 2
        assert timings.total_duration_ms == 300.0
        assert timings.avg_duration_ms == 150.0
        assert len(timings.timestamps) == 2
