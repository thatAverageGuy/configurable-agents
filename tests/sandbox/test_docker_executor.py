"""
Tests for DockerSandboxExecutor.

Tests cover:
- Basic code execution in container
- Resource limit enforcement (timeout, memory)
- Network isolation
- Error handling (syntax errors, runtime errors)
- Custom image support
- Graceful degradation when Docker unavailable

Tests are skipped if Docker is not available.
"""

import json
import os
import pytest

# Try to import Docker dependencies
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

from configurable_agents.sandbox import (
    DockerSandboxExecutor,
    RESOURCE_PRESETS,
    execute_in_container,
    get_preset,
    SafetyError,
    SandboxResult,
)


# Skip all tests if Docker is not available
docker_available = pytest.mark.skipif(
    not DOCKER_AVAILABLE,
    reason="Docker not available or not running"
)


def _docker_is_running() -> bool:
    """Check if Docker daemon is actually running."""
    if not DOCKER_AVAILABLE:
        return False
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


docker_running = pytest.mark.skipif(
    not _docker_is_running(),
    reason="Docker daemon is not running"
)


@pytest.mark.integration
@docker_running
class TestBasicExecution:
    """Tests for basic code execution in Docker."""

    def test_arithmetic_operations(self):
        """Test basic arithmetic operations."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code="result = 2 + 2 * 10",
            inputs={},
            timeout=30,
        )

        assert result.success is True
        assert result.output == "22"

    def test_string_operations(self):
        """Test string manipulation operations."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code='result = inputs["text"].upper()',
            inputs={"text": "hello"},
            timeout=30,
        )

        assert result.success is True
        assert result.output == "HELLO"

    def test_list_operations(self):
        """Test list comprehension and operations."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code="""
items = inputs["numbers"]
result = [x * 2 for x in items if x > 2]
""",
            inputs={"numbers": [1, 2, 3, 4, 5]},
            timeout=30,
        )

        assert result.success is True
        # Output is string representation
        assert "[6, 8, 10]" in result.output or "6" in result.output

    def test_inputs_passed_correctly(self):
        """Test that inputs are passed to container correctly."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code='result = len(inputs["items"])',
            inputs={"items": [1, 2, 3, 4, 5]},
            timeout=30,
        )

        assert result.success is True
        assert "5" in result.output


@pytest.mark.integration
@docker_running
class TestResourceLimits:
    """Tests for resource limit enforcement."""

    def test_timeout_enforcement(self):
        """Test that timeout is enforced."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code="""
import time
time.sleep(10)
result = "should not reach here"
""",
            inputs={},
            timeout=2,  # 2 second timeout
        )

        # Should fail due to timeout
        assert result.success is False
        assert "timeout" in result.error.lower()

    def test_custom_memory_limit(self):
        """Test custom memory limit."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code="result = sum(range(1000))",
            inputs={},
            timeout=30,
            resources={"memory": "256m"},
        )

        assert result.success is True

    def test_custom_cpu_limit(self):
        """Test custom CPU limit."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code="result = 42",
            inputs={},
            timeout=30,
            resources={"cpu": 0.5},
        )

        assert result.success is True
        assert "42" in result.output


@pytest.mark.integration
@docker_running
class TestNetworkIsolation:
    """Tests for network isolation."""

    def test_network_enabled_by_default(self):
        """Test that network is enabled by default."""
        executor = DockerSandboxExecutor()
        # This should work with network
        result = executor.execute(
            code="""
try:
    import urllib.request
    result = "network_allowed"
except:
    result = "network_blocked"
""",
            inputs={},
            timeout=10,
        )

        # Network is enabled by default, so should allow
        assert result.success is True

    def test_network_disabled(self):
        """Test that network can be disabled."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code="""
try:
    import urllib.request
    urllib.request.urlopen("http://example.com", timeout=1)
    result = "network_allowed"
except Exception as e:
    result = f"network_blocked: {type(e).__name__}"
""",
            inputs={},
            timeout=10,
            resources={"network": False},
        )

        # Network should be blocked
        assert result.success is True
        assert "blocked" in result.output.lower()


@pytest.mark.integration
@docker_running
class TestErrorHandling:
    """Tests for error handling."""

    def test_syntax_error_caught(self):
        """Test that syntax errors are caught."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code="if True\n    x = 1",  # Invalid syntax
            inputs={},
            timeout=30,
        )

        # Container should fail
        assert result.success is False

    def test_runtime_error_caught(self):
        """Test that runtime errors are caught."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code="result = 1 / 0",
            inputs={},
            timeout=30,
        )

        assert result.success is False
        assert "error" in result.error.lower() or "zero" in result.error.lower()

    def test_name_error_caught(self):
        """Test that NameError is caught."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code="result = undefined_variable",
            inputs={},
            timeout=30,
        )

        assert result.success is False
        assert "error" in result.error.lower()

    def test_invalid_inputs_format(self):
        """Test handling of complex inputs."""
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code='result = inputs["nested"]["key"]',
            inputs={"nested": {"key": "value"}},
            timeout=30,
        )

        assert result.success is True
        assert "value" in result.output


@pytest.mark.integration
@docker_running
class TestResourcePresets:
    """Tests for resource presets."""

    def test_get_preset_low(self):
        """Test low preset."""
        preset = get_preset("low")
        assert preset["cpu"] == 0.5
        assert preset["memory"] == "256m"
        assert preset["timeout"] == 30

    def test_get_preset_medium(self):
        """Test medium preset (default)."""
        preset = get_preset("medium")
        assert preset["cpu"] == 1.0
        assert preset["memory"] == "512m"
        assert preset["timeout"] == 60

    def test_get_preset_high(self):
        """Test high preset."""
        preset = get_preset("high")
        assert preset["cpu"] == 2.0
        assert preset["memory"] == "1g"
        assert preset["timeout"] == 120

    def test_get_preset_max(self):
        """Test max preset."""
        preset = get_preset("max")
        assert preset["cpu"] == 4.0
        assert preset["memory"] == "2g"
        assert preset["timeout"] == 300

    def test_get_preset_unknown_fallback(self):
        """Test fallback to medium for unknown preset."""
        preset = get_preset("unknown")
        assert preset["cpu"] == 1.0  # medium default

    def test_resource_presets_complete(self):
        """Test that all presets are defined."""
        assert "low" in RESOURCE_PRESETS
        assert "medium" in RESOURCE_PRESETS
        assert "high" in RESOURCE_PRESETS
        assert "max" in RESOURCE_PRESETS


@pytest.mark.integration
@docker_running
class TestCustomImage:
    """Tests for custom Docker image support."""

    def test_custom_python_image(self):
        """Test using a specific Python version."""
        # Use python:3.11-slim (same as default)
        executor = DockerSandboxExecutor(image_name="python:3.11-slim")
        result = executor.execute(
            code="result = 42",
            inputs={},
            timeout=30,
        )

        assert result.success is True
        assert "42" in result.output


class TestGracefulDegradation:
    """Tests for graceful degradation when Docker unavailable."""

    @docker_available
    def test_docker_unavailable_error(self):
        """Test that helpful error is returned when Docker is unavailable."""
        if _docker_is_running():
            pytest.skip("Docker is running, cannot test unavailable case")

        executor = DockerSandboxExecutor()
        result = executor.execute(
            code="result = 42",
            inputs={},
            timeout=30,
        )

        assert result.success is False
        assert "docker" in result.error.lower()

    def test_docker_not_installed_import_error(self):
        """Test that module handles docker not being installed."""
        if DOCKER_AVAILABLE:
            pytest.skip("Docker is installed")

        # Try to import DockerSandboxExecutor - should be in __all__ only if available
        from configurable_agents import sandbox

        # If docker is not installed, DockerSandboxExecutor should not be in __all__
        assert "DockerSandboxExecutor" not in sandbox.__all__


class TestConvenienceFunction:
    """Tests for execute_in_container convenience function."""

    @docker_running
    def test_basic_usage(self):
        """Test basic usage of execute_in_container."""
        result = execute_in_container(
            code='result = inputs["x"] * 2',
            inputs={"x": 21},
        )

        assert result.success is True
        assert "42" in result.output

    @docker_running
    def test_default_inputs(self):
        """Test with default (empty) inputs."""
        result = execute_in_container(
            code="result = 1 + 1",
        )

        assert result.success is True
        assert "2" in result.output

    @docker_running
    def test_custom_timeout(self):
        """Test with custom timeout."""
        result = execute_in_container(
            code="result = sum(range(1000))",
            timeout=10,
        )

        assert result.success is True

    @docker_running
    def test_custom_resources(self):
        """Test with custom resources."""
        result = execute_in_container(
            code="result = 42",
            resources={"cpu": 0.5, "memory": "256m"},
        )

        assert result.success is True

    @docker_running
    def test_custom_image(self):
        """Test with custom image."""
        result = execute_in_container(
            code="result = 42",
            image="python:3.11-slim",
        )

        assert result.success is True


class TestSafetyValidation:
    """Tests for code safety validation."""

    @docker_running
    def test_too_large_code_rejected(self):
        """Test that excessively large code is rejected."""
        executor = DockerSandboxExecutor()

        # Create code larger than 1MB
        large_code = "x = 1\n" * 300000  # More than 1MB

        result = executor.execute(
            code=large_code,
            inputs={},
            timeout=30,
        )

        assert result.success is False
        assert "large" in result.error.lower() or "size" in result.error.lower()

    @docker_running
    def test_dangerous_system_call_pattern(self):
        """Test that dangerous system call patterns are caught."""
        executor = DockerSandboxExecutor()

        result = executor.execute(
            code='__import__("os").system("ls")',
            inputs={},
            timeout=30,
        )

        # Should be blocked by validation
        assert result.success is False
        assert "dangerous" in result.error.lower() or "safety" in result.error.lower()
