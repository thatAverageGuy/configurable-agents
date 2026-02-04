"""
RestrictedPython-based sandbox executor.

Provides safe Python code execution using RestrictedPython's AST
transformation to block unsafe operations while maintaining full
Python functionality for legitimate use cases.

Design decisions:
- Uses RestrictedPython.compile_restricted() for AST-based safety
- Safe builtins only (no file I/O, subprocess, eval, etc.)
- Timeout via func_timeout library (cross-platform)
- Return value via 'result' variable (user code should assign to 'result')
- Captures stdout/stderr for debugging
"""

import io
import logging
import time
from typing import Any

# RestrictedPython for AST-based code restriction
from RestrictedPython import compile_restricted
from RestrictedPython.Guards import (
    guarded_iter_unpack_sequence,
    guarded_unpack_sequence,
    safe_builtins,
)
from func_timeout import FunctionTimedOut, func_timeout

from .base import SafetyError, SandboxExecutor, SandboxResult

logger = logging.getLogger(__name__)


# Allowed "private" attributes that RestrictedPython normally blocks
# These are safe for our sandbox environment
_ALLOWED_PRIVATE_ATTRS = frozenset({
    '_call_print',  # For print() support
    '_print_',  # For print wrapper object
})


def _safe_getattr(obj: Any, name: str | None = None, default: Any = None) -> Any:
    """
    Custom getattr for sandbox that allows specific safe private attributes.

    This is a modified version of RestrictedPython's safer_getattr that
    allows our specific private attributes while still blocking dangerous ones.

    Args:
        obj: Object to get attribute from
        name: Attribute name (if None, returns obj itself)
        default: Default value if attribute not found

    Returns:
        Attribute value or default
    """
    # If no name provided, return the object itself
    # This happens in RestrictedPython's print transformation
    if name is None:
        return obj

    if type(name) is not str:
        raise TypeError('type(name) must be str')

    # Block format() on strings (security risk)
    if name in ('format', 'format_map') and (
            isinstance(obj, str) or
            (isinstance(obj, type) and issubclass(obj, str))):
        raise NotImplementedError(
            'Using the format*() methods of `str` is not safe')

    # Allow our specific private attributes
    if name in _ALLOWED_PRIVATE_ATTRS:
        return getattr(obj, name, default)

    # Block other private/underscore attributes
    if name.startswith('_'):
        raise AttributeError(
            f'"{name}" is an invalid attribute name because it '
            f'starts with "_"')

    # Safe attribute access
    if default is not None:
        return getattr(obj, name, default)
    return getattr(obj, name)


class _SafePrint:
    """Safe print wrapper for RestrictedPython.

    RestrictedPython's print transformation instantiates this class
    and then calls _call_print on the instance.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize (called by RestrictedPython's bytecode)."""
        pass

    def _call_print(self, *args: Any, **kwargs: Any) -> None:
        """Print function that RestrictedPython will call."""
        print(*args, **kwargs)

# Safe builtins available in sandbox execution
# Excludes: open, __import__, eval, exec, compile, etc.
SAFE_BUILTINS: dict[str, Any] = {
    # Basic types
    "dict": dict,
    "list": list,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "tuple": tuple,
    "set": set,
    "frozenset": frozenset,
    "bytes": bytes,
    # Common functions
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "sum": sum,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "pow": pow,
    "divmod": divmod,
    "any": any,
    "all": all,
    "sorted": sorted,
    "reversed": reversed,
    "map": map,
    "filter": filter,
    # Type conversion
    "ord": ord,
    "chr": chr,
    "bin": bin,
    "hex": hex,
    "oct": oct,
    # String operations
    "str": str,
    "format": str.format,
    # Collections (safe versions)
    "slice": slice,
    # Iterables support
    "iter": iter,
    "next": next,
    # Constants
    "True": True,
    "False": False,
    "None": None,
    # Print for debugging
    "print": print,
}

# Merge RestrictedPython's safe builtins with our custom set
_SANDBOX_BUILTINS = {**safe_builtins, **SAFE_BUILTINS}


def _execute_with_timeout(
    code_obj: Any,
    globals_dict: dict[str, Any],
    timeout_seconds: int,
) -> tuple[bool, Any, str]:
    """
    Execute compiled code with timeout enforcement.

    Args:
        code_obj: Compiled code object
        globals_dict: Global variables for execution
        timeout_seconds: Maximum execution time

    Returns:
        Tuple of (success, result, error_message)
    """
    try:
        func_timeout(
            timeout_seconds,
            exec,
            args=(code_obj, globals_dict),
        )
        return True, None, ""
    except FunctionTimedOut:
        error_msg = f"Code execution exceeded timeout of {timeout_seconds} seconds"
        logger.warning(error_msg)
        return False, None, error_msg
    except MemoryError:
        error_msg = "Code execution exceeded memory limits"
        logger.warning(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Runtime error during execution: {type(e).__name__}: {e}"
        logger.warning(error_msg)
        return False, None, error_msg


class PythonSandboxExecutor(SandboxExecutor):
    """
    RestrictedPython-based sandbox executor.

    Provides safe Python code execution without requiring Docker.
    Uses AST transformation to block unsafe operations at compile time.

    Safety features:
    - Blocks: import statements, file I/O, subprocess, eval, exec
    - Safe builtins only (no open, __import__, compile, etc.)
    - Attribute access guarded (prevents access to dangerous attributes)
    - Timeout enforcement via func_timeout

    Usage:
        Code should assign its return value to 'result' variable:
            result = calculate(inputs["value"])

    Note: Variables starting with underscore are blocked by RestrictedPython,
    so we use 'result' instead of '__result'.
    """

    def __init__(self) -> None:
        """Initialize the Python sandbox executor."""
        self._restricted_globals = self._build_restricted_globals()

    def _build_restricted_globals(self) -> dict[str, Any]:
        """
        Build the restricted globals dict for code execution.

        Returns:
            Dict with safe builtins and RestrictedPython guards
        """
        return {
            "__builtins__": _SANDBOX_BUILTINS,
            "__name__": "__sandbox__",
            "_getattr_": _safe_getattr,  # Custom getattr that allows _call_print
            "_getiter_": iter,  # Safe iteration
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            "_unpack_sequence_": guarded_unpack_sequence,
            "_getitem_": lambda x, i: x[i],  # Safe item access for subscript
            "_print_": _SafePrint,  # RestrictedPython-compatible print class (not instance!)
        }

    def _validate_code(self, code: str) -> None:
        """
        Validate code for security issues before execution.

        Uses RestrictedPython's compile_restricted() to detect
        unsafe operations at AST level.

        Args:
            code: Python code to validate

        Raises:
            SafetyError: If code contains unsafe operations
        """
        # Try to compile with restrictions
        # compile_restricted raises SyntaxError if there are security violations
        try:
            compile_restricted(
                code,
                filename="<sandbox>",
                mode="exec",
            )
        except SyntaxError as e:
            # Convert SyntaxError to SafetyError
            raise SafetyError(
                f"Code contains unsafe or invalid operations: {e}",
                code_snippet=code[:200],
            )

        # Additional validation: check for explicit attempts to access builtins
        # Note: RestrictedPython already blocks most of these at compile time
        # This is an extra layer for patterns that might slip through
        dangerous_patterns = [
            "__import__",
            "__builtins__",
            "globals()",
            "locals()",
            "vars()",
        ]

        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                raise SafetyError(
                    f"Code contains potentially dangerous pattern: '{pattern}'",
                    code_snippet=code[:200],
                )

        # Check for eval/exec (these might not always be caught by AST)
        if "eval(" in code_lower or "exec(" in code_lower:
            raise SafetyError(
                "Code contains potentially dangerous function: eval() or exec()",
                code_snippet=code[:200],
            )

    def execute(
        self,
        code: str,
        inputs: dict[str, Any],
        timeout: int = 30,
    ) -> SandboxResult:
        """
        Execute Python code in RestrictedPython sandbox.

        Args:
            code: Python code to execute
            inputs: Input variables available as 'inputs' dict
            timeout: Maximum execution time in seconds

        Returns:
            SandboxResult with execution outcome

        Raises:
            SafetyError: If code validation fails
        """
        start_time = time.time()

        # Capture stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # Step 1: Validate code for security issues
            self._validate_code(code)

            # Step 2: Compile with restrictions
            # compile_restricted returns a code object on success
            code_obj = compile_restricted(
                code,
                filename="<sandbox>",
                mode="exec",
            )

            # Step 3: Prepare execution environment
            exec_globals = self._restricted_globals.copy()
            exec_globals["inputs"] = inputs
            exec_globals["result"] = None  # Initialize result variable

            # Redirect stdout/stderr during execution
            import sys

            original_stdout = sys.stdout
            original_stderr = sys.stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            try:
                # Step 4: Execute with timeout
                success, _, error_msg = _execute_with_timeout(
                    code_obj,
                    exec_globals,
                    timeout,
                )

                execution_time = time.time() - start_time

                if not success:
                    return SandboxResult(
                        success=False,
                        output=None,
                        error=error_msg,
                        execution_time=execution_time,
                        stderr=stderr_capture.getvalue(),
                    )

                # Step 5: Extract result from special 'result' variable
                result_value = exec_globals.get("result", None)

                return SandboxResult(
                    success=True,
                    output=result_value,
                    error=None,
                    execution_time=execution_time,
                    stdout=stdout_capture.getvalue(),
                    stderr=stderr_capture.getvalue(),
                )

            finally:
                # Restore stdout/stderr
                sys.stdout = original_stdout
                sys.stderr = original_stderr

        except SafetyError as e:
            execution_time = time.time() - start_time
            return SandboxResult(
                success=False,
                output=None,
                error=f"Safety violation: {e.message}",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"Unexpected error during sandbox execution: {e}")
            return SandboxResult(
                success=False,
                output=None,
                error=f"Unexpected error: {type(e).__name__}: {e}",
                execution_time=execution_time,
                stderr=stderr_capture.getvalue(),
            )


def execute_code(
    code: str,
    inputs: dict[str, Any] | None = None,
    timeout: int = 30,
) -> SandboxResult:
    """
    Convenience function to execute code in Python sandbox.

    Args:
        code: Python code to execute
        inputs: Optional input variables (defaults to empty dict)
        timeout: Maximum execution time in seconds

    Returns:
        SandboxResult with execution outcome

    Example:
        >>> result = execute_code('result = sum(inputs["numbers"])', {"numbers": [1, 2, 3]})
        >>> assert result.success
        >>> assert result.output == 6
    """
    executor = PythonSandboxExecutor()
    return executor.execute(code, inputs or {}, timeout)
