"""Performance profiling decorator for workflow nodes.

Provides:
- profile_node decorator: Times node execution using time.perf_counter()
- NodeTimings: Dataclass for storing timing data
- BottleneckAnalyzer: Identifies nodes consuming disproportionate time
- Thread-local context: Stores analyzer for decorator access

Key features:
- Works with both sync and async functions
- Captures timing even on exceptions (try/finally)
- Logs duration_ms to MLFlow as metric: node_{node_id}_duration_ms
- Thread-local storage for parallel execution safety
"""

import asyncio
import functools
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

# Optional MLFlow import for metric logging
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MLFLOW_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class NodeTimings:
    """
    Stores aggregated timing data for a single node.

    Attributes:
        node_id: Node identifier
        call_count: Number of times the node was executed
        total_duration_ms: Total execution time across all calls (milliseconds)
        avg_duration_ms: Average execution time per call (milliseconds)
        timestamps: List of timestamps when the node was called
    """
    node_id: str
    call_count: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    timestamps: list[datetime] = field(default_factory=list)

    def add_call(self, duration_ms: float, timestamp: datetime) -> None:
        """Add a new execution call to the timing data."""
        self.call_count += 1
        self.total_duration_ms += duration_ms
        self.timestamps.append(timestamp)
        # Update average
        self.avg_duration_ms = self.total_duration_ms / self.call_count


class BottleneckAnalyzer:
    """
    Analyzes node execution times to identify performance bottlenecks.

    Tracks timing data across workflow execution and provides:
    - Bottleneck detection (nodes >50% of total time by default)
    - Slowest node identification
    - Complete performance summary

    Example:
        >>> analyzer = BottleneckAnalyzer()
        >>> analyzer.record_node("node1", 100.0)
        >>> analyzer.record_node("node2", 500.0)
        >>> analyzer.get_slowest_node()
        {'node_id': 'node2', 'total_duration_ms': 500.0, ...}
        >>> analyzer.get_bottlenecks(threshold_percent=50.0)
        [{'node_id': 'node2', 'percent_of_total': 83.3, ...}]
    """

    def __init__(self) -> None:
        """Initialize bottleneck analyzer with empty timing data."""
        self._timings: dict[str, NodeTimings] = {}
        self.enabled: bool = True

    def record_node(self, node_id: str, duration_ms: float) -> None:
        """
        Record execution time for a node.

        Aggregates timing data if the node has been called before.

        Args:
            node_id: Node identifier
            duration_ms: Execution time in milliseconds

        Example:
            >>> analyzer = BottleneckAnalyzer()
            >>> analyzer.record_node("research", 150.5)
            >>> analyzer.record_node("research", 200.0)  # Aggregates
            >>> analyzer._timings["research"].call_count
            2
        """
        if not self.enabled:
            return

        timestamp = datetime.now(timezone.utc)

        if node_id in self._timings:
            # Aggregate existing node timing
            self._timings[node_id].add_call(duration_ms, timestamp)
        else:
            # Create new timing entry
            self._timings[node_id] = NodeTimings(
                node_id=node_id,
                call_count=1,
                total_duration_ms=duration_ms,
                avg_duration_ms=duration_ms,
                timestamps=[timestamp],
            )

        logger.debug(
            f"Recorded node timing: {node_id} = {duration_ms:.2f}ms "
            f"(total: {self._timings[node_id].total_duration_ms:.2f}ms, "
            f"calls: {self._timings[node_id].call_count})"
        )

    def get_bottlenecks(
        self, threshold_percent: float = 50.0
    ) -> list[dict[str, Any]]:
        """
        Identify nodes contributing more than threshold_percent of total time.

        Args:
            threshold_percent: Minimum percentage of total time to be considered
                a bottleneck (default: 50.0)

        Returns:
            List of bottleneck dictionaries, each containing:
            - node_id: Node identifier
            - total_duration_ms: Total execution time
            - avg_duration_ms: Average execution time per call
            - call_count: Number of calls
            - percent_of_total: Percentage of total workflow time

        Example:
            >>> analyzer = BottleneckAnalyzer()
            >>> analyzer.record_node("fast", 50)
            >>> analyzer.record_node("slow", 450)
            >>> bottlenecks = analyzer.get_bottlenecks(50.0)
            >>> len(bottlenecks)
            1
            >>> bottlenecks[0]["node_id"]
            'slow'
        """
        if not self._timings:
            return []

        # Calculate total workflow time
        total_time_ms = sum(t.total_duration_ms for t in self._timings.values())

        if total_time_ms == 0:
            return []

        bottlenecks = []
        for node_id, timings in self._timings.items():
            percent = (timings.total_duration_ms / total_time_ms) * 100
            if percent > threshold_percent:
                bottlenecks.append({
                    "node_id": node_id,
                    "total_duration_ms": timings.total_duration_ms,
                    "avg_duration_ms": timings.avg_duration_ms,
                    "call_count": timings.call_count,
                    "percent_of_total": round(percent, 2),
                })

        # Sort by percentage descending
        bottlenecks.sort(key=lambda x: x["percent_of_total"], reverse=True)
        return bottlenecks

    def get_slowest_node(self) -> Optional[dict[str, Any]]:
        """
        Get the node with the highest total execution time.

        Returns:
            Dictionary with node_id, total_duration_ms, avg_duration_ms, call_count
            Returns None if no timings have been recorded.

        Example:
            >>> analyzer = BottleneckAnalyzer()
            >>> analyzer.record_node("node1", 100)
            >>> analyzer.record_node("node2", 200)
            >>> analyzer.get_slowest_node()["node_id"]
            'node2'
        """
        if not self._timings:
            return None

        slowest = max(
            self._timings.items(),
            key=lambda x: x[1].total_duration_ms
        )
        node_id, timings = slowest

        return {
            "node_id": node_id,
            "total_duration_ms": timings.total_duration_ms,
            "avg_duration_ms": timings.avg_duration_ms,
            "call_count": timings.call_count,
        }

    def get_summary(self) -> dict[str, Any]:
        """
        Get complete performance summary.

        Returns:
            Dictionary containing:
            - total_time_ms: Total workflow execution time
            - node_count: Number of distinct nodes executed
            - slowest_node: Node with highest total time (or None)
            - bottlenecks: List of nodes >50% threshold

        Example:
            >>> analyzer = BottleneckAnalyzer()
            >>> analyzer.record_node("node1", 100)
            >>> summary = analyzer.get_summary()
            >>> summary["total_time_ms"]
            100.0
        """
        total_time_ms = sum(t.total_duration_ms for t in self._timings.values())

        return {
            "total_time_ms": total_time_ms,
            "node_count": len(self._timings),
            "slowest_node": self.get_slowest_node(),
            "bottlenecks": self.get_bottlenecks(threshold_percent=50.0),
        }


# Thread-local storage for profiler context
# Enables safe parallel execution by storing analyzer per thread
_context = threading.local()


def get_profiler() -> Optional[BottleneckAnalyzer]:
    """
    Get the BottleneckAnalyzer for the current thread.

    Returns:
        BottleneckAnalyzer instance if set, None otherwise

    Example:
        >>> analyzer = get_profiler()
        >>> if analyzer:
        ...     summary = analyzer.get_summary()
    """
    return getattr(_context, "analyzer", None)


def set_profiler(analyzer: BottleneckAnalyzer) -> None:
    """
    Set the BottleneckAnalyzer for the current thread.

    Args:
        analyzer: BottleneckAnalyzer instance to use for this thread

    Example:
        >>> analyzer = BottleneckAnalyzer()
        >>> set_profiler(analyzer)
        >>> # Now @profile_node decorator will use this analyzer
    """
    _context.analyzer = analyzer


def clear_profiler() -> None:
    """Remove the BottleneckAnalyzer from the current thread.

    Example:
        >>> clear_profiler()
        >>> get_profiler() is None
        True
    """
    if hasattr(_context, "analyzer"):
        delattr(_context, "analyzer")


def profile_node(node_id: str) -> Callable:
    """
    Decorator that measures and logs execution time for a node.

    Uses time.perf_counter() for high-resolution timing.
    Works with both sync and async functions.
    Captures timing even on exceptions (try/finally).

    Args:
        node_id: Node identifier for logging and MLFlow metrics

    Returns:
        Decorator function

    Example:
        >>> @profile_node("my_node")
        ... def my_function():
        ...     return "result"
        >>>
        >>> @profile_node("async_node")
        ... async def my_async_function():
        ...     return await asyncio.sleep(0.1)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Wrapper for synchronous functions."""
            start_time = time.perf_counter()
            duration_ms: float
            result: Any

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Always record timing, even on exception
                duration_ms = (time.perf_counter() - start_time) * 1000
                _record_timing(node_id, duration_ms)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Wrapper for asynchronous functions."""
            start_time = time.perf_counter()
            duration_ms: float
            result: Any

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                # Always record timing, even on exception
                duration_ms = (time.perf_counter() - start_time) * 1000
                _record_timing(node_id, duration_ms)

        # Detect if function is async and return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _record_timing(node_id: str, duration_ms: float) -> None:
    """
    Record timing data to BottleneckAnalyzer and MLFlow.

    Args:
        node_id: Node identifier
        duration_ms: Execution time in milliseconds
    """
    # Record to BottleneckAnalyzer (if set)
    analyzer = get_profiler()
    if analyzer:
        analyzer.record_node(node_id, duration_ms)

    # Log to MLFlow (if available and active run exists)
    if MLFLOW_AVAILABLE and mlflow.active_run():
        try:
            metric_name = f"node_{node_id}_duration_ms"
            mlflow.log_metric(metric_name, duration_ms)
            logger.debug(f"Logged MLFlow metric: {metric_name} = {duration_ms:.2f}ms")
        except Exception as e:
            # MLFlow logging failures should not break workflow execution
            logger.warning(f"Failed to log timing to MLFlow: {e}")

    # Always log for debugging
    logger.debug(f"Node '{node_id}' executed in {duration_ms:.2f}ms")
