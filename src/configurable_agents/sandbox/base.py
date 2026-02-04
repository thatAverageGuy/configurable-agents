"""
Sandbox executor base interface.

Provides abstract interface for safe code execution with different
isolation strategies (RestrictedPython, Docker, etc.).

Design decisions:
- SandboxResult dataclass for consistent result reporting
- Abstract execute() method with timeout enforcement
- SafetyError for security violation reporting
- _validate_code() hook for subclass-specific validation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


class SafetyError(Exception):
    """
    Raised when code violates security policies.

    This exception indicates that the code attempted to perform
    an unsafe operation that was blocked by the sandbox (e.g.,
    file I/O, subprocess execution, unsafe imports).

    Attributes:
        message: Human-readable error description
        code_snippet: Optional snippet of the offending code
    """

    def __init__(self, message: str, code_snippet: Optional[str] = None) -> None:
        """
        Initialize safety error.

        Args:
            message: Description of the security violation
            code_snippet: Optional snippet of code that caused the violation
        """
        self.message = message
        self.code_snippet = code_snippet
        super().__init__(message)


@dataclass
class SandboxResult:
    """
    Result of sandbox code execution.

    Attributes:
        success: True if code executed without errors, False otherwise
        output: The return value from code execution (if successful)
        error: Error message if execution failed, None otherwise
        execution_time: Time taken to execute code in seconds
        stdout: Captured standard output (if available)
        stderr: Captured standard error (if available)
    """

    success: bool
    output: Any
    error: Optional[str]
    execution_time: float
    stdout: str = ""
    stderr: str = ""

    def __repr__(self) -> str:
        """String representation showing success/failure."""
        if self.success:
            return f"SandboxResult(success=True, output={repr(self.output)[:50]}, execution_time={self.execution_time:.3f}s)"
        return f"SandboxResult(success=False, error={self.error})"


class SandboxExecutor(ABC):
    """
    Abstract base class for sandbox executors.

    Implementations provide different isolation strategies:
    - PythonSandboxExecutor: RestrictedPython-based (no Docker required)
    - DockerSandboxExecutor: Container-based isolation (requires Docker)

    All implementations must:
    1. Validate code before execution (_validate_code)
    2. Enforce timeout limits
    3. Return structured SandboxResult
    4. Catch and report errors appropriately
    """

    @abstractmethod
    def execute(
        self,
        code: str,
        inputs: dict[str, Any],
        timeout: int = 30,
    ) -> SandboxResult:
        """
        Execute code in the sandbox.

        Args:
            code: Python code to execute
            inputs: Input variables available to the code (as 'inputs' dict)
            timeout: Maximum execution time in seconds

        Returns:
            SandboxResult with execution outcome

        Raises:
            SafetyError: If code violates security policies
            TimeoutError: If code execution exceeds timeout
        """
        pass

    @abstractmethod
    def _validate_code(self, code: str) -> None:
        """
        Validate code for security issues before execution.

        Should raise SafetyError if unsafe operations are detected.

        Args:
            code: Python code to validate

        Raises:
            SafetyError: If code contains unsafe operations
        """
        pass
