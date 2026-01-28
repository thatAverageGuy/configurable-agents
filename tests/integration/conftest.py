"""Pytest fixtures and configuration for integration tests."""

import os
import time
from pathlib import Path
from typing import Any, Dict

import pytest


# ============================================
# Environment Validation
# ============================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (real API calls)")
    config.addinivalue_line(
        "markers", "requires_serper: marks tests requiring SERPER_API_KEY"
    )


@pytest.fixture(scope="session")
def check_google_api_key():
    """Verify GOOGLE_API_KEY is set before running integration tests."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not set - skipping integration test")
    return api_key


@pytest.fixture(scope="session")
def check_serper_api_key():
    """Verify SERPER_API_KEY is set before running tool integration tests."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        pytest.skip("SERPER_API_KEY not set - skipping tool integration test")
    return api_key


# ============================================
# Path Fixtures
# ============================================


@pytest.fixture(scope="session")
def examples_dir():
    """Path to examples directory."""
    return Path(__file__).parent.parent.parent / "examples"


@pytest.fixture(scope="session")
def echo_workflow(examples_dir):
    """Path to echo.yaml example."""
    return examples_dir / "echo.yaml"


@pytest.fixture(scope="session")
def simple_workflow(examples_dir):
    """Path to simple_workflow.yaml example."""
    return examples_dir / "simple_workflow.yaml"


@pytest.fixture(scope="session")
def nested_state_workflow(examples_dir):
    """Path to nested_state.yaml example."""
    return examples_dir / "nested_state.yaml"


@pytest.fixture(scope="session")
def type_enforcement_workflow(examples_dir):
    """Path to type_enforcement.yaml example."""
    return examples_dir / "type_enforcement.yaml"


@pytest.fixture(scope="session")
def article_writer_workflow(examples_dir):
    """Path to article_writer.yaml example."""
    return examples_dir / "article_writer.yaml"


# ============================================
# Cost Tracking
# ============================================


class APICallTracker:
    """Track API calls and approximate costs for integration tests."""

    def __init__(self):
        self.calls = []
        self.total_time = 0.0

    def track_call(self, test_name: str, workflow: str, duration: float, result: Dict[str, Any]):
        """Record an API call."""
        self.calls.append(
            {
                "test": test_name,
                "workflow": workflow,
                "duration": duration,
                "result_keys": list(result.keys()) if result else [],
            }
        )
        self.total_time += duration

    def report(self):
        """Generate cost report."""
        if not self.calls:
            return "No API calls tracked"

        report = [
            "\n" + "=" * 60,
            "INTEGRATION TEST COST REPORT",
            "=" * 60,
            f"Total API Calls: {len(self.calls)}",
            f"Total Time: {self.total_time:.2f}s",
            f"Average Time: {self.total_time / len(self.calls):.2f}s per call",
            "\nDetailed Breakdown:",
            "-" * 60,
        ]

        for i, call in enumerate(self.calls, 1):
            report.append(
                f"{i}. {call['test']} - {call['workflow']} ({call['duration']:.2f}s)"
            )

        report.append("=" * 60)
        return "\n".join(report)


@pytest.fixture(scope="session")
def api_tracker():
    """API call tracker for cost reporting."""
    tracker = APICallTracker()
    yield tracker
    # Print report after all tests
    print(tracker.report())


@pytest.fixture
def track_api_call(api_tracker, request):
    """Fixture to track individual API calls."""

    def _track(workflow: str, result: Dict[str, Any], duration: float):
        test_name = request.node.name
        api_tracker.track_call(test_name, workflow, duration, result)

    return _track


# ============================================
# Helper Fixtures
# ============================================


@pytest.fixture
def run_workflow_with_timing():
    """Helper to run workflow and track timing."""
    from configurable_agents.runtime import run_workflow

    def _run(config_path: str, inputs: Dict[str, Any], **kwargs):
        start = time.time()
        result = run_workflow(config_path, inputs, **kwargs)
        duration = time.time() - start
        return result, duration

    return _run


@pytest.fixture
def validate_workflow_helper():
    """Helper to validate workflow configs."""
    from configurable_agents.runtime import validate_workflow

    def _validate(config_path: str):
        validate_workflow(config_path)
        return True

    return _validate
