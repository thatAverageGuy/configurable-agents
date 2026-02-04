"""
Sandbox executors for safe code execution.

This module provides two sandbox execution strategies:

1. **PythonSandboxExecutor** (default): RestrictedPython-based execution
   - Works everywhere without Docker
   - Blocks unsafe operations via AST transformation
   - Suitable for local development and trusted environments

2. **DockerSandboxExecutor** (opt-in): Container-based isolation
   - Requires Docker daemon
   - Full OS-level isolation with resource limits
   - Suitable for production and untrusted code

Usage:
    from configurable_agents.sandbox import PythonSandboxExecutor, execute_code

    executor = PythonSandboxExecutor()
    result = executor.execute(code="x = 1 + 1", inputs={}, timeout=30)
    if result.success:
        print(f"Output: {result.output}")

    # Or use convenience function
    result = execute_code('__result = sum(inputs["nums"])', inputs={"nums": [1, 2, 3]})
"""

from .base import SafetyError, SandboxExecutor, SandboxResult
from .python_executor import PythonSandboxExecutor, execute_code

__all__ = [
    # Base types
    "SafetyError",
    "SandboxExecutor",
    "SandboxResult",
    # Python executor
    "PythonSandboxExecutor",
    "execute_code",
]

# Try to import Docker executor if available
try:
    from .docker_executor import (
        DockerSandboxExecutor,
        RESOURCE_PRESETS,
        execute_in_container,
        get_preset,
    )

    __all__.extend([
        "DockerSandboxExecutor",
        "RESOURCE_PRESETS",
        "execute_in_container",
        "get_preset",
    ])
except ImportError:
    # Docker not available - this is normal
    pass
