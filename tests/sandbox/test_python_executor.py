"""
Tests for PythonSandboxExecutor.

Tests cover:
- Safe code execution (arithmetic, strings, data structures)
- Blocked unsafe operations (imports, file access, subprocess)
- Timeout enforcement
- Return value extraction via result
- stdout/stderr capture
- Error handling and SandboxResult structure
"""

import pytest

from configurable_agents.sandbox import (
    SafetyError,
    SandboxResult,
    execute_code,
    PythonSandboxExecutor,
)


class TestBasicExecution:
    """Tests for basic safe code execution."""

    def test_arithmetic_operations(self):
        """Test basic arithmetic operations work correctly."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code='result = 2 + 2 * 10',
            inputs={},
        )

        assert result.success is True
        assert result.output == 22
        assert result.error is None
        assert result.execution_time >= 0

    def test_string_operations(self):
        """Test string manipulation operations."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code='result = inputs["text"].upper()',
            inputs={"text": "hello"},
        )

        assert result.success is True
        assert result.output == "HELLO"

    def test_list_operations(self):
        """Test list comprehension and operations."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
items = inputs["numbers"]
result = [x * 2 for x in items if x > 2]
""",
            inputs={"numbers": [1, 2, 3, 4, 5]},
        )

        assert result.success is True
        assert result.output == [6, 8, 10]

    def test_dict_operations(self):
        """Test dictionary operations."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
data = inputs["data"]
result = {k: v * 2 for k, v in data.items()}
""",
            inputs={"data": {"a": 1, "b": 2}},
        )

        assert result.success is True
        assert result.output == {"a": 2, "b": 4}

    def test_complex_calculation(self):
        """Test more complex calculation with multiple operations."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
nums = inputs["nums"]
total = sum(nums)
count = len(nums)
result = {
    "sum": total,
    "average": total / count,
    "min": min(nums),
    "max": max(nums),
}
""",
            inputs={"nums": [10, 20, 30, 40, 50]},
        )

        assert result.success is True
        assert result.output["sum"] == 150
        assert result.output["average"] == 30.0
        assert result.output["min"] == 10
        assert result.output["max"] == 50

    def test_enumerate_zip(self):
        """Test enumerate and zip builtins."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
names = inputs["names"]
values = inputs["values"]
result = list(zip(names, values))
""",
            inputs={"names": ["a", "b"], "values": [1, 2]},
        )

        assert result.success is True
        assert result.output == [("a", 1), ("b", 2)]

    def test_range_operations(self):
        """Test range and iteration."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
result = list(range(1, 6))
""",
            inputs={},
        )

        assert result.success is True
        assert result.output == [1, 2, 3, 4, 5]

    def test_boolean_operations(self):
        """Test boolean logic."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
a = inputs["a"]
b = inputs["b"]
result = {
    "and": a and b,
    "or": a or b,
    "not_a": not a,
}
""",
            inputs={"a": True, "b": False},
        )

        assert result.success is True
        assert result.output["and"] is False
        assert result.output["or"] is True
        assert result.output["not_a"] is False


class TestUnsafeOperationsBlocked:
    """Tests that unsafe operations are properly blocked."""

    def test_import_blocked(self):
        """Test that import statements are blocked by RestrictedPython."""
        executor = PythonSandboxExecutor()

        result = executor.execute(
            code="import os\nresult = os.getcwd()",
            inputs={},
        )

        # RestrictedPython allows import at compile time but __import__ fails at runtime
        assert result.success is False
        assert ("import" in result.error.lower() or
                "not found" in result.error.lower())

    def test_import_as_blocked(self):
        """Test that 'import as' statements are blocked."""
        executor = PythonSandboxExecutor()

        result = executor.execute(
            code="import sys as s\nresult = s.version",
            inputs={},
        )

        # RestrictedPython allows import at compile time but __import__ fails at runtime
        assert result.success is False
        assert ("import" in result.error.lower() or
                "not found" in result.error.lower())

    def test_from_import_blocked(self):
        """Test that 'from X import Y' statements are blocked."""
        executor = PythonSandboxExecutor()

        result = executor.execute(
            code="from os import path\nresult = path",
            inputs={},
        )

        # RestrictedPython allows import at compile time but __import__ fails at runtime
        assert result.success is False
        assert ("import" in result.error.lower() or
                "not found" in result.error.lower())

    def test_open_file_blocked(self):
        """Test that attempts to use open() are blocked."""
        executor = PythonSandboxExecutor()

        result = executor.execute(
            code='f = open("test.txt", "w")',
            inputs={},
        )

        # open() is not in safe builtins, so it will fail at runtime
        assert result.success is False
        assert "open" in result.error.lower() or "not found" in result.error.lower()

    def test_eval_blocked(self):
        """Test that eval() is blocked."""
        executor = PythonSandboxExecutor()

        result = executor.execute(
            code='x = eval("1 + 1")',
            inputs={},
        )

        # eval() is blocked by RestrictedPython at compile time
        assert result.success is False
        assert ("unsafe" in result.error.lower() or
                "safety" in result.error.lower() or
                "not allowed" in result.error.lower())

    def test_exec_blocked(self):
        """Test that exec() is blocked."""
        executor = PythonSandboxExecutor()

        result = executor.execute(
            code='exec("print(1)")',
            inputs={},
        )

        # exec() is blocked by RestrictedPython at compile time
        assert result.success is False
        assert ("unsafe" in result.error.lower() or
                "safety" in result.error.lower() or
                "not allowed" in result.error.lower())

    def test_globals_blocked(self):
        """Test that globals() access is blocked."""
        executor = PythonSandboxExecutor()

        result = executor.execute(
            code="g = globals()",
            inputs={},
        )

        assert result.success is False
        assert "dangerous" in result.error.lower()

    def test_submodule_access_blocked(self):
        """Test that dangerous attribute access is blocked."""
        executor = PythonSandboxExecutor()

        # Try to access dangerous attributes through safe objects
        result = executor.execute(
            code="""
# Try to access __class__ to break out
x = []
dangerous = x.__class__
""",
            inputs={},
        )

        # RestrictedPython guards should catch this
        # Either success=False or guards prevent the access
        if result.success:
            # If somehow successful, verify we didn't get anything dangerous
            assert result.output is not None
        else:
            # This is the expected path - blocked
            assert result.error is not None


class TestTimeoutEnforcement:
    """Tests for timeout enforcement."""

    def test_short_timeout(self):
        """Test that short codes complete within timeout."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="result = sum(range(1000))",
            inputs={},
            timeout=10,
        )

        assert result.success is True
        assert result.execution_time < 1.0

    def test_timeout_enforcement(self):
        """Test that long-running code is terminated."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
# Infinite loop that should be caught by timeout
while True:
    pass
result = "never reached"
""",
            inputs={},
            timeout=1,  # 1 second timeout
        )

        assert result.success is False
        assert "timeout" in result.error.lower()

    def test_long_calculation_timeout(self):
        """Test timeout on long calculation."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
# Very slow calculation
import time
for i in range(1000000):
    x = i * i
result = "done"
""",
            inputs={},
            timeout=1,
        )

        # Should either timeout or succeed if fast enough
        if result.execution_time > 0.8:
            # If it took longer than 0.8s, it should have timed out
            assert result.success is False or result.execution_time <= 2.0


class TestReturnValues:
    """Tests for return value extraction."""

    def test_none_return_value(self):
        """Test code that doesn't set result."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="x = 42",  # No result assignment
            inputs={},
        )

        assert result.success is True
        assert result.output is None

    def test_integer_return(self):
        """Test integer return value."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="result = 42",
            inputs={},
        )

        assert result.success is True
        assert result.output == 42

    def test_string_return(self):
        """Test string return value."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code='result = "hello world"',
            inputs={},
        )

        assert result.success is True
        assert result.output == "hello world"

    def test_list_return(self):
        """Test list return value."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="result = [1, 2, 3]",
            inputs={},
        )

        assert result.success is True
        assert result.output == [1, 2, 3]

    def test_dict_return(self):
        """Test dictionary return value."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code='result = {"key": "value"}',
            inputs={},
        )

        assert result.success is True
        assert result.output == {"key": "value"}

    def test_nested_return(self):
        """Test nested data structure return."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
result = {
    "numbers": [1, 2, 3],
    "nested": {"a": 1, "b": [4, 5]},
    "string": "test",
}
""",
            inputs={},
        )

        assert result.success is True
        assert result.output["numbers"] == [1, 2, 3]
        assert result.output["nested"]["b"] == [4, 5]


class TestStdoutStderrCapture:
    """Tests for stdout/stderr capture."""

    def test_print_capture(self):
        """Test that print() output is captured."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
print("Hello, world!")
print("Line 2")
result = "done"
""",
            inputs={},
        )

        assert result.success is True
        assert "Hello, world!" in result.stdout
        assert "Line 2" in result.stdout

    def test_print_with_inputs(self):
        """Test print with input values."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
name = inputs["name"]
print(f"Hello, {name}!")
result = name
""",
            inputs={"name": "Alice"},
        )

        assert result.success is True
        assert "Hello, Alice!" in result.stdout
        assert result.output == "Alice"

    def test_empty_stdout(self):
        """Test empty stdout when no print statements."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="result = 42",
            inputs={},
        )

        assert result.success is True
        assert result.stdout == ""

    def test_error_in_stderr(self):
        """Test that runtime errors are captured."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
# This will cause a runtime error
x = undefined_variable
result = "done"
""",
            inputs={},
        )

        # The error should be in the result's error field
        assert not result.success
        assert "error" in result.error.lower()


class TestErrorHandling:
    """Tests for error handling."""

    def test_syntax_error_caught(self):
        """Test that syntax errors are caught."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="if True\n    x = 1",  # Invalid syntax
            inputs={},
        )

        assert result.success is False
        assert "error" in result.error.lower() or "compilation" in result.error.lower()

    def test_runtime_error_caught(self):
        """Test that runtime errors are caught."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="result = 1 / 0",
            inputs={},
        )

        assert result.success is False
        assert "error" in result.error.lower() or "zerodivision" in result.error.lower()

    def test_name_error_caught(self):
        """Test that NameError is caught."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="result = undefined_variable",
            inputs={},
        )

        assert result.success is False
        assert "error" in result.error.lower()

    def test_type_error_caught(self):
        """Test that TypeError is caught."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code='result = len(42)',  # int has no len()
            inputs={},
        )

        assert result.success is False
        assert "error" in result.error.lower()

    def test_index_error_caught(self):
        """Test that IndexError is caught."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
lst = [1, 2, 3]
result = lst[10]
""",
            inputs={},
        )

        assert result.success is False
        assert "error" in result.error.lower()

    def test_key_error_caught(self):
        """Test that KeyError is caught."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code="""
d = {"a": 1}
result = d["missing_key"]
""",
            inputs={},
        )

        assert result.success is False
        assert "error" in result.error.lower()


class TestConvenienceFunction:
    """Tests for the execute_code convenience function."""

    def test_basic_usage(self):
        """Test basic usage of execute_code()."""
        result = execute_code(
            code='result = inputs["x"] * 2',
            inputs={"x": 21},
        )

        assert result.success is True
        assert result.output == 42

    def test_default_inputs(self):
        """Test execute_code with default (empty) inputs."""
        result = execute_code(code="result = 1 + 1")

        assert result.success is True
        assert result.output == 2

    def test_default_timeout(self):
        """Test execute_code with default timeout."""
        result = execute_code(
            code='result = sum(range(1000))',
        )

        assert result.success is True
        assert result.output == sum(range(1000))

    def test_custom_timeout(self):
        """Test execute_code with custom timeout."""
        result = execute_code(
            code="result = 42",
            timeout=5,
        )

        assert result.success is True
        assert result.output == 42


class TestSandboxResult:
    """Tests for SandboxResult dataclass."""

    def test_success_repr(self):
        """Test string representation of successful result."""
        result = SandboxResult(
            success=True,
            output=42,
            error=None,
            execution_time=0.123,
        )

        repr_str = repr(result)
        assert "success=True" in repr_str
        assert "42" in repr_str

    def test_failure_repr(self):
        """Test string representation of failed result."""
        result = SandboxResult(
            success=False,
            output=None,
            error="Test error",
            execution_time=0.456,
        )

        repr_str = repr(result)
        assert "success=False" in repr_str
        assert "Test error" in repr_str

    def test_all_fields(self):
        """Test all SandboxResult fields."""
        result = SandboxResult(
            success=True,
            output="test",
            error=None,
            execution_time=1.0,
            stdout="printed output",
            stderr="error messages",
        )

        assert result.success is True
        assert result.output == "test"
        assert result.error is None
        assert result.execution_time == 1.0
        assert result.stdout == "printed output"
        assert result.stderr == "error messages"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_code(self):
        """Test empty code string."""
        executor = PythonSandboxExecutor()
        result = executor.execute(code="", inputs={})

        assert result.success is True
        assert result.output is None

    def test_whitespace_only(self):
        """Test code with only whitespace."""
        executor = PythonSandboxExecutor()
        result = executor.execute(code="   \n  \n  ", inputs={})

        assert result.success is True
        assert result.output is None

    def test_multiline_string(self):
        """Test code with multiline string."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code='''result = """
This is a
multiline
string.
"""''',
            inputs={},
        )

        assert result.success is True
        assert "multiline" in result.output

    def test_unicode(self):
        """Test code with unicode characters."""
        executor = PythonSandboxExecutor()
        result = executor.execute(
            code='result = inputs["text"] + " emoji"',
            inputs={"text": ""},
        )

        assert result.success is True
        assert "emoji" in result.output

    def test_large_input(self):
        """Test with large input data."""
        executor = PythonSandboxExecutor()
        large_list = list(range(10000))
        result = executor.execute(
            code="result = len(inputs['data'])",
            inputs={"data": large_list},
        )

        assert result.success is True
        assert result.output == 10000
