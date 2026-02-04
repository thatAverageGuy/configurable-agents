"""
Docker-based sandbox executor for isolated code execution.

Provides container-based code execution with resource limits,
network isolation, and automatic cleanup. Requires Docker daemon.

Design decisions:
- Graceful degradation when Docker unavailable
- Read-only root filesystem for security
- Resource presets (low/medium/high/max) for common use cases
- Network isolation via "none" mode
- Automatic temp file cleanup in finally blocks
"""

import logging
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .base import SandboxExecutor, SandboxResult

logger = logging.getLogger(__name__)

# Resource presets for different use cases
# Each preset defines CPU, memory, and timeout limits
RESOURCE_PRESETS: dict[str, dict[str, Any]] = {
    "low": {
        "cpu": 0.5,  # 50% of one CPU core
        "memory": "256m",  # 256 MB RAM
        "timeout": 30,  # 30 seconds
    },
    "medium": {
        "cpu": 1.0,  # 1 CPU core
        "memory": "512m",  # 512 MB RAM
        "timeout": 60,  # 60 seconds
    },
    "high": {
        "cpu": 2.0,  # 2 CPU cores
        "memory": "1g",  # 1 GB RAM
        "timeout": 120,  # 120 seconds
    },
    "max": {
        "cpu": 4.0,  # 4 CPU cores
        "memory": "2g",  # 2 GB RAM
        "timeout": 300,  # 300 seconds (5 minutes)
    },
}


def get_preset(name: str) -> dict[str, Any]:
    """
    Get resource preset by name.

    Args:
        name: Preset name ('low', 'medium', 'high', 'max')

    Returns:
        Dict with cpu, memory, and timeout values

    Raises:
        ValueError: If preset name is unknown
    """
    if name not in RESOURCE_PRESETS:
        logger.warning(
            f"Unknown resource preset '{name}', falling back to 'medium'"
        )
        name = "medium"
    return RESOURCE_PRESETS[name].copy()


def _docker_available() -> bool:
    """
    Check if Docker daemon is available.

    Returns:
        True if Docker is available and running, False otherwise
    """
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


@contextmanager
def _temp_code_file(code: str, inputs: dict[str, Any]) -> Path:
    """
    Create a temporary file with code and inputs.

    The file contains Python code that sets up the inputs variable
    and executes the user code.

    Args:
        code: User code to execute
        inputs: Input variables to embed

    Yields:
        Path to the temporary file
    """
    fd, path = tempfile.mkstemp(suffix=".py", text=True)
    try:
        # Write the sandbox wrapper code
        with os.fdopen(fd, "w") as f:
            # Embed inputs as a Python dict
            f.write("# Auto-generated sandbox code\n")
            f.write("import json\n")
            f.write(f"inputs = {json.dumps(inputs)}\n")
            f.write("# User code follows\n")
            f.write(code)
            f.write("\n")
            f.write("# Capture result\n")
            f.write("import sys\n")
            f.write("try:\n")
            f.write("    from _io import StringIO\n")
            f.write("    _old_stdout = sys.stdout\n")
            f.write("    sys.stdout = StringIO()\n")
            f.write("    exec('result = result if \"result\" in dir() else None')\n")
            f.write("    _output = sys.stdout.getvalue()\n")
            f.write("    sys.stdout = _old_stdout\n")
            f.write("    print(json.dumps({\"success\": True, \"output\": str(result) if result is not None else None, \"stdout\": _output}))\n")
            f.write("except Exception as e:\n")
            f.write("    sys.stdout = _old_stdout\n")
            f.write("    print(json.dumps({\"success\": False, \"error\": str(e)}))\n")

        yield Path(path)
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass  # File may have been cleaned up already


import json


class DockerSandboxExecutor(SandboxExecutor):
    """
    Docker-based sandbox executor for isolated code execution.

    Executes Python code in a Docker container with:
    - Resource limits (CPU, memory, timeout)
    - Network isolation (configurable)
    - Read-only root filesystem
    - Automatic cleanup

    Requires Docker daemon to be running. Falls back gracefully
    if Docker is unavailable.

    Usage:
        executor = DockerSandboxExecutor()
        result = executor.execute(
            code="result = sum(inputs['numbers'])",
            inputs={"numbers": [1, 2, 3]},
            timeout=30,
            resources={"cpu": 1.0, "memory": "512m"}
        )
    """

    def __init__(
        self,
        image_name: str = "python:3.11-slim",
    ) -> None:
        """
        Initialize Docker sandbox executor.

        Args:
            image_name: Docker image to use for execution
        """
        self.image_name = image_name
        self._docker_client = None
        self._available = None  # Cached availability check

    def _check_available(self) -> bool:
        """
        Check if Docker is available.

        Returns:
            True if Docker is available, False otherwise
        """
        if self._available is not None:
            return self._available

        self._available = _docker_available()
        if not self._available:
            logger.warning("Docker is not available. DockerSandboxExecutor will fail.")
        return self._available

    def _get_client(self):
        """
        Get Docker client instance.

        Returns:
            Docker client

        Raises:
            RuntimeError: If Docker is not available
        """
        if not self._check_available():
            raise RuntimeError(
                "Docker is not available. Please ensure Docker daemon is running. "
                "You can check with 'docker ps' command."
            )

        if self._docker_client is None:
            import docker
            self._docker_client = docker.from_env()

        return self._docker_client

    def _validate_code(self, code: str) -> None:
        """
        Validate code for execution in Docker.

        Docker provides strong isolation, so we mainly check for
        obviously problematic code patterns.

        Args:
            code: Python code to validate

        Raises:
            SafetyError: If code contains obviously unsafe operations
        """
        # Docker provides strong isolation, so we're less restrictive
        # Just check for extremely long code that might cause issues
        if len(code) > 1_000_000:  # 1MB limit
            raise SafetyError("Code is too large (max 1MB)")

        # Check for obviously problematic patterns
        if "__import__('os').system" in code.lower():
            raise SafetyError("Code contains potentially dangerous system calls")

    def execute(
        self,
        code: str,
        inputs: dict[str, Any],
        timeout: int = 30,
        resources: dict[str, Any] | None = None,
    ) -> SandboxResult:
        """
        Execute code in a Docker container.

        Args:
            code: Python code to execute
            inputs: Input variables available as 'inputs' dict
            timeout: Maximum execution time in seconds
            resources: Resource limits dict (cpu, memory, network)

        Returns:
            SandboxResult with execution outcome
        """
        start_time = time.time()

        # Merge resources with defaults
        if resources is None:
            resources = {}

        cpu = resources.get("cpu", 1.0)
        memory = resources.get("memory", "512m")
        network_enabled = resources.get("network", True)
        timeout = min(timeout, resources.get("timeout", timeout))

        try:
            # Validate code first
            self._validate_code(code)

            # Check Docker availability
            client = self._get_client()

            # Ensure image is available
            try:
                client.images.get(self.image_name)
            except Exception:
                logger.info(f"Pulling Docker image {self.image_name}...")
                client.images.pull(self.image_name)

            # Create temp file with code
            with _temp_code_file(code, inputs) as code_file:
                # Configure container
                container_config = {
                    "image": self.image_name,
                    "command": ["python", str(code_file)],
                    "detach": True,
                    "remove": True,  # Automatically remove container on exit
                    "mem_limit": memory,
                    "memswap_limit": memory,  # No swap
                    "cpu_quota": int(cpu * 100000),  # CPU quota in microseconds
                    "cpu_period": 100000,  # CPU period in microseconds
                    "read_only": True,  # Read-only root filesystem
                    "security_opt": ["no-new-privileges"],  # Prevent privilege escalation
                    "cap_drop": ["ALL"],  # Drop all capabilities
                    "network_mode": "default" if network_enabled else "none",
                    # Mount temp directory as read-write volume
                    "volumes": {
                        str(code_file.parent): {
                            "bind": "/workspace",
                            "mode": "rw",  # Need write for temp files
                        }
                    },
                    "working_dir": "/workspace",
                }

                # Run container
                logger.debug(
                    f"Starting Docker container with {cpu} CPU, {memory} memory, "
                    f"timeout {timeout}s, network={network_enabled}"
                )

                container = client.containers.run(**container_config)

                # Wait for completion with timeout
                try:
                    result = container.wait(timeout=timeout)
                    exit_code = result["StatusCode"] if isinstance(result, dict) else result

                    # Get logs
                    logs = container.logs(stdout=True, stderr=True).decode("utf-8")

                    execution_time = time.time() - start_time

                    if exit_code == 0 and logs:
                        # Parse JSON output from container
                        try:
                            output_data = json.loads(logs.strip())
                            if output_data.get("success"):
                                return SandboxResult(
                                    success=True,
                                    output=output_data.get("output"),
                                    error=None,
                                    execution_time=execution_time,
                                    stdout=output_data.get("stdout", ""),
                                )
                            else:
                                return SandboxResult(
                                    success=False,
                                    output=None,
                                    error=output_data.get("error", "Unknown error"),
                                    execution_time=execution_time,
                                )
                        except json.JSONDecodeError:
                            # Fallback: raw output
                            return SandboxResult(
                                success=True,
                                output=logs.strip(),
                                error=None,
                                execution_time=execution_time,
                                stdout=logs.strip(),
                            )
                    elif exit_code != 0:
                        # Container exited with error
                        error_msg = logs.strip() if logs else f"Container exited with code {exit_code}"
                        return SandboxResult(
                            success=False,
                            output=None,
                            error=error_msg,
                            execution_time=execution_time,
                        )
                    else:
                        # No output
                        return SandboxResult(
                            success=True,
                            output=None,
                            error=None,
                            execution_time=execution_time,
                        )

                except Exception as timeout_err:
                    # Timeout or other error during wait
                    container.stop(timeout=1)
                    container.remove(force=True)
                    execution_time = time.time() - start_time

                    if "timeout" in str(timeout_err).lower():
                        error_msg = f"Execution exceeded timeout of {timeout} seconds"
                    else:
                        error_msg = f"Container execution error: {timeout_err}"

                    return SandboxResult(
                        success=False,
                        output=None,
                        error=error_msg,
                        execution_time=execution_time,
                    )

        except RuntimeError as e:
            # Docker not available
            execution_time = time.time() - start_time
            return SandboxResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"Unexpected error in DockerSandboxExecutor: {e}")
            return SandboxResult(
                success=False,
                output=None,
                error=f"Docker execution error: {type(e).__name__}: {e}",
                execution_time=execution_time,
            )


def execute_in_container(
    code: str,
    inputs: dict[str, Any] | None = None,
    timeout: int = 60,
    resources: dict[str, Any] | None = None,
    image: str = "python:3.11-slim",
) -> SandboxResult:
    """
    Convenience function to execute code in Docker container.

    Args:
        code: Python code to execute
        inputs: Optional input variables (defaults to empty dict)
        timeout: Maximum execution time in seconds
        resources: Optional resource limits (cpu, memory, network)
        image: Docker image to use

    Returns:
        SandboxResult with execution outcome

    Example:
        >>> result = execute_in_container(
        ...     'result = sum(inputs["nums"])',
        ...     inputs={"nums": [1, 2, 3]}
        ... )
        >>> assert result.success
        >>> assert result.output == "6"
    """
    executor = DockerSandboxExecutor(image_name=image)
    return executor.execute(code, inputs or {}, timeout, resources)
