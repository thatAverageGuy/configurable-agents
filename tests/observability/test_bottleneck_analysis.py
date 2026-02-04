"""Tests for BottleneckAnalyzer."""

import pytest

from configurable_agents.runtime.profiler import BottleneckAnalyzer, NodeTimings


class TestBottleneckAnalyzerRecordNode:
    """Test record_node method."""

    def test_bottleneck_analyzer_record_node(self):
        """Test that node timing is recorded correctly."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("node1", 100.0)

        assert "node1" in analyzer._timings
        assert analyzer._timings["node1"].node_id == "node1"
        assert analyzer._timings["node1"].call_count == 1
        assert analyzer._timings["node1"].total_duration_ms == 100.0

    def test_bottleneck_analyzer_aggregates_multiple_calls(self):
        """Test that multiple calls to same node aggregate timing data."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("node1", 100.0)
        analyzer.record_node("node1", 200.0)
        analyzer.record_node("node1", 150.0)

        timings = analyzer._timings["node1"]
        assert timings.call_count == 3
        assert timings.total_duration_ms == 450.0
        assert timings.avg_duration_ms == 150.0

    def test_bottleneck_analyzer_disabled(self):
        """Test that recording is skipped when analyzer is disabled."""
        analyzer = BottleneckAnalyzer()
        analyzer.enabled = False

        analyzer.record_node("node1", 100.0)

        assert "node1" not in analyzer._timings


class TestGetBottlenecks:
    """Test get_bottlenecks method."""

    def test_get_bottlenecks_default_threshold(self):
        """Test that bottlenecks are identified with default 50% threshold."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("fast", 50.0)
        analyzer.record_node("slow", 450.0)

        bottlenecks = analyzer.get_bottlenecks(threshold_percent=50.0)

        assert len(bottlenecks) == 1
        assert bottlenecks[0]["node_id"] == "slow"
        assert bottlenecks[0]["percent_of_total"] == 90.0

    def test_get_bottlenecks_custom_threshold(self):
        """Test that custom threshold parameter is respected."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("node1", 100.0)
        analyzer.record_node("node2", 200.0)
        analyzer.record_node("node3", 100.0)

        # 66% threshold - only node2 should qualify (50% exactly is not > 50%)
        bottlenecks = analyzer.get_bottlenecks(threshold_percent=66.0)
        assert len(bottlenecks) == 0  # node2 is exactly 50%, not > 66%

        # 40% threshold - node2 should qualify (50% > 40%)
        bottlenecks = analyzer.get_bottlenecks(threshold_percent=40.0)
        assert len(bottlenecks) == 1
        assert bottlenecks[0]["node_id"] == "node2"

        # 49% threshold - node2 should qualify (50% > 49%)
        bottlenecks = analyzer.get_bottlenecks(threshold_percent=49.0)
        assert len(bottlenecks) == 1
        assert bottlenecks[0]["node_id"] == "node2"

    def test_get_bottlenecks_returns_complete_info(self):
        """Test that bottleneck entries contain all required fields."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("bottleneck_node", 300.0)
        analyzer.record_node("bottleneck_node", 200.0)  # Total: 500

        bottlenecks = analyzer.get_bottlenecks(threshold_percent=50.0)

        assert len(bottlenecks) == 1
        b = bottlenecks[0]
        assert "node_id" in b
        assert "total_duration_ms" in b
        assert "avg_duration_ms" in b
        assert "call_count" in b
        assert "percent_of_total" in b
        assert b["call_count"] == 2
        assert b["total_duration_ms"] == 500.0
        assert b["avg_duration_ms"] == 250.0

    def test_get_bottlenecks_single_node(self):
        """Test edge case: single node with 100% is >50% threshold."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("only_node", 100.0)

        bottlenecks = analyzer.get_bottlenecks(threshold_percent=50.0)

        # Single node with 100% is >50%
        assert len(bottlenecks) == 1
        assert bottlenecks[0]["node_id"] == "only_node"
        assert bottlenecks[0]["percent_of_total"] == 100.0

    def test_get_bottlenecks_empty_analyzer(self):
        """Test that empty analyzer returns empty list."""
        analyzer = BottleneckAnalyzer()
        bottlenecks = analyzer.get_bottlenecks()
        assert bottlenecks == []

    def test_get_bottlenecks_sorted_by_percentage(self):
        """Test that bottlenecks are sorted by percentage descending."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("node1", 100.0)
        analyzer.record_node("node2", 400.0)
        analyzer.record_node("node3", 200.0)

        bottlenecks = analyzer.get_bottlenecks(threshold_percent=40.0)

        # Only node2 (57.1%) and node3 (28.6%) are > 40%
        # Wait, 28.6% is NOT > 40%, so only node2 should qualify
        assert len(bottlenecks) == 1
        assert bottlenecks[0]["node_id"] == "node2"  # 57.14% > 40%


class TestGetSlowestNode:
    """Test get_slowest_node method."""

    def test_get_slowest_node(self):
        """Test that get_slowest_node returns correct node."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("node1", 100.0)
        analyzer.record_node("node2", 500.0)
        analyzer.record_node("node3", 200.0)

        slowest = analyzer.get_slowest_node()

        assert slowest is not None
        assert slowest["node_id"] == "node2"
        assert slowest["total_duration_ms"] == 500.0

    def test_get_slowest_node_with_aggregated_calls(self):
        """Test that slowest node considers aggregated total duration."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("node1", 100.0)
        analyzer.record_node("node1", 100.0)  # Total: 200
        analyzer.record_node("node2", 150.0)   # Total: 150

        slowest = analyzer.get_slowest_node()

        assert slowest["node_id"] == "node1"
        assert slowest["total_duration_ms"] == 200.0
        assert slowest["call_count"] == 2

    def test_get_slowest_node_empty_analyzer(self):
        """Test that empty analyzer returns None."""
        analyzer = BottleneckAnalyzer()
        slowest = analyzer.get_slowest_node()
        assert slowest is None

    def test_get_slowest_node_returns_complete_info(self):
        """Test that slowest node dict contains all required fields."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("slowest", 300.0)
        analyzer.record_node("slowest", 200.0)

        slowest = analyzer.get_slowest_node()

        assert "node_id" in slowest
        assert "total_duration_ms" in slowest
        assert "avg_duration_ms" in slowest
        assert "call_count" in slowest
        assert slowest["call_count"] == 2
        assert slowest["avg_duration_ms"] == 250.0


class TestGetSummary:
    """Test get_summary method."""

    def test_get_summary_returns_complete_analysis(self):
        """Test that get_summary returns all required fields."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("node1", 100.0)
        analyzer.record_node("node2", 400.0)

        summary = analyzer.get_summary()

        assert "total_time_ms" in summary
        assert "node_count" in summary
        assert "slowest_node" in summary
        assert "bottlenecks" in summary
        assert summary["total_time_ms"] == 500.0
        assert summary["node_count"] == 2

    def test_get_summary_includes_slowest_node(self):
        """Test that summary includes correct slowest node."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("fast", 50.0)
        analyzer.record_node("slow", 450.0)

        summary = analyzer.get_summary()

        assert summary["slowest_node"]["node_id"] == "slow"
        assert summary["slowest_node"]["total_duration_ms"] == 450.0

    def test_get_summary_includes_bottlenecks(self):
        """Test that summary includes bottlenecks list."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("fast", 50.0)
        analyzer.record_node("slow", 450.0)

        summary = analyzer.get_summary()

        assert len(summary["bottlenecks"]) == 1
        assert summary["bottlenecks"][0]["node_id"] == "slow"

    def test_get_summary_empty_analyzer(self):
        """Test that empty analyzer returns summary with zeros."""
        analyzer = BottleneckAnalyzer()
        summary = analyzer.get_summary()

        assert summary["total_time_ms"] == 0
        assert summary["node_count"] == 0
        assert summary["slowest_node"] is None
        assert summary["bottlenecks"] == []

    def test_zero_duration_handled(self):
        """Test that zero duration nodes don't cause errors."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("zero", 0.0)
        analyzer.record_node("positive", 100.0)

        summary = analyzer.get_summary()

        assert summary["node_count"] == 2
        assert summary["total_time_ms"] == 100.0

        # Zero duration node should not be a bottleneck
        bottlenecks = analyzer.get_bottlenecks(threshold_percent=50.0)
        assert len(bottlenecks) == 1
        assert bottlenecks[0]["node_id"] == "positive"


class TestBottleneckAnalyzerEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_threshold_returns_all_nodes(self):
        """Test that 0% threshold returns all nodes."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("node1", 10.0)
        analyzer.record_node("node2", 20.0)

        bottlenecks = analyzer.get_bottlenecks(threshold_percent=0.0)

        assert len(bottlenecks) == 2

    def test_hundred_threshold_no_bottlenecks(self):
        """Test that 100% threshold returns no nodes (not > 100%)."""
        analyzer = BottleneckAnalyzer()
        analyzer.record_node("node1", 100.0)

        bottlenecks = analyzer.get_bottlenecks(threshold_percent=100.0)

        assert len(bottlenecks) == 0
