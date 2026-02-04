# Phase 07: CLI Testing & Fixes - Research

**Researched:** 2026-02-05
**Domain:** CLI Testing & Bug Fixing
**Confidence:** HIGH

## Summary

Phase 07 focuses on testing and fixing all CLI commands to ensure they work without errors. Research reveals that CLI testing requires a **multi-layered approach**: unit tests for individual command functions, integration tests for full CLI workflows, and cross-platform validation (Windows, macOS, Linux). The current codebase has **heavily mocked tests** that don't verify actual functionality, which is why bugs like the UnboundLocalError in `cmd_run` slipped through.

**Primary recommendation:** Implement a testing pyramid for CLI: (1) Unit tests with real function calls (not mocks), (2) Integration tests using subprocess for end-to-end validation, (3) Cross-platform CI testing to catch platform-specific bugs. Focus on **actionable error messages** that tell users exactly what went wrong and how to fix it.

**Key insight from Real Python:** "All CLI testing is a matter of comparing your expected outputs to your actual outputs, given some set of inputs" ([4 Techniques for Testing Python Command-Line (CLI) Apps](https://realpython.com/python-cli-testing/)).

## Standard Stack

### Core Testing Framework

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **pytest** | >=7.0 | Test runner | Industry standard, powerful fixtures, parametrization |
| **subprocess** | Built-in | Real CLI invocation | Tests actual installed CLI, catches import errors |
| **pytest-cov** | Latest | Coverage reporting | Ensures test completeness |
| **pytest-xdist** | Latest | Parallel execution | Faster cross-platform testing |

### CLI Testing Helpers

| Library | Purpose | When to Use |
|---------|---------|-------------|
| **click.testing.CliRunner** | In-process Click testing | Unit tests (if using Click) |
| **unittest.mock** | Isolate external dependencies | Avoid API calls in tests |
| **tmp_path** (pytest fixture) | Temporary file/dir creation | File I/O testing |

**Installation:**
```bash
# Already in project dev dependencies
pip install pytest pytest-cov pytest-xdist
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| subprocess | CliRunner (Click) | CliRunner is faster but subprocess tests real entry point |
| unittest | pytest | pytest has better fixtures, cleaner syntax |
| mocks | real calls | Mocks are faster but don't catch integration bugs |

## Architecture Patterns

### Testing Pyramid for CLI

```
                    /\
                   /  \
                  / E2E\           subprocess tests (slow, real)
                 /------\
                /        \
               /Integration\    pytest with real deps (medium)
              /------------\
             /              \
            /    Unit Tests    \  pytest with mocks (fast, isolated)
           /------------------\
```

**Layer breakdown:**

1. **Unit Tests (Fast, Isolated)**
   - Test individual functions: `parse_input_args()`, `colorize()`
   - Mock external dependencies: LLM calls, file system
   - Quick feedback during development

2. **Integration Tests (Medium, Real)**
   - Test command functions with real dependencies: `cmd_run()`, `cmd_validate()`
   - Use temp files for config I/O
   - Verify error handling with real exception types

3. **E2E Tests (Slow, Real)**
   - Invoke actual CLI via `subprocess.run()`
   - Test installed package behavior
   - Catch import/entry point bugs

### Pattern 1: Subprocess Integration Test

**What:** Test the actual installed CLI via subprocess
**When to use:** Validating end-to-end workflows, catching import errors
**Example:**
```python
# Source: https://realpython.com/python-cli-testing/
import subprocess
import sys
import pytest

@pytest.mark.integration
def test_cli_run_simple_workflow(tmp_path):
    """Integration test: Run actual workflow via CLI."""
    # Create valid workflow config
    config_file = tmp_path / "workflow.yaml"
    config_file.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    message: {type: str, required: true}
nodes:
  - id: echo
    prompt: "Say: {state.message}"
    outputs: [result]
edges:
  - {from: START, to: echo}
  - {from: echo, to: END}
""")

    # Run via subprocess (tests actual CLI entry point)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "configurable_agents",
            "run",
            str(config_file),
            "--input",
            "message=Hello",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Assert success
    assert result.returncode == 0
    assert "Hello" in result.stdout or "completed" in result.stdout.lower()
```

**Key points:**
- Uses `sys.executable -m configurable_agents` to test actual module invocation
- `capture_output=True` and `text=True` for string comparison
- `timeout` prevents hangs
- Tests real entry point, catches import/attribute errors

### Pattern 2: CliRunner for Faster Testing

**What:** Use Click's CliRunner for in-process testing (if using Click)
**When to use:** Rapid unit testing of CLI commands
**Example:**
```python
from click.testing import CliRunner
from configurable_agents.cli import create_parser

def test_validate_command_cli_runner(tmp_path):
    """Test validate command via CliRunner."""
    runner = CliRunner()

    # Create valid config
    config_file = tmp_path / "valid.yaml"
    config_file.write_text("flow:\n  name: test\n")

    # Invoke command
    result = runner.invoke(
        create_parser(),
        ["validate", str(config_file)]
    )

    # Assert
    assert result.exit_code == 0
    assert "valid" in result.output.lower()
```

**Tradeoff:** Faster than subprocess but may miss import/entry point bugs.

### Pattern 3: Error Message Testing

**What:** Verify error messages are clear and actionable
**When to use:** All error paths
**Example:**
```python
def test_run_command_missing_file():
    """Test helpful error when config file doesn't exist."""
    result = subprocess.run(
        [sys.executable, "-m", "configurable_agents", "run", "missing.yaml"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    # Clear error message
    assert "not found" in result.stderr.lower() or "no such file" in result.stderr.lower()
    # Actionable suggestion
    assert "yaml" in result.stderr.lower()
```

**Key principle:** Every error should say (1) what went wrong, (2) why, (3) how to fix it.

### Anti-Patterns to Avoid

- **Over-mocking:** Tests that mock everything pass but code fails in production
  - **Why bad:** The UnboundLocalError bug wasn't caught because tests mocked `run_workflow()`
  - **Fix:** Test with real function calls in integration tests

- **Only testing happy path:** Tests only verify success cases
  - **Why bad:** Error handling has bugs that only surface when things fail
  - **Fix:** Test every error branch with intentional failures

- **Ignoring stderr:** Tests only check stdout
  - **Why bad:** Error messages go to stderr, bugs in error handling are missed
  - **Fix:** Always capture and assert on both stdout and stderr

- **Platform assumptions:** Tests assume Unix paths
  - **Why bad:** Windows uses backslashes, different behavior
  - **Fix:** Use `pathlib.Path` for cross-platform paths

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI argument parsing | Custom `sys.argv` parser | argparse/Click | Edge cases: quoting, escapes, help generation |
| Output formatting | Manual string concatenation | Rich library | Tables, colors, progress bars handled |
| Temporary files | Manual mkdir/cleanup | pytest `tmp_path` fixture | Auto-cleanup, unique per test |
| Process spawning | raw `os.system()` or `os.popen()` | `subprocess.run()` | Secure, timeout support, output capture |
| Test parallelization | Manual test splitting | `pytest-xdist` | Proven, handles locking, reporting |

**Key insight:** Building your own CLI testing framework is a rabbit hole. Use pytest + subprocess and focus on your actual CLI logic.

## Common Pitfalls

### Pitfall 1: Tests Pass But CLI Fails (Mock Overuse)

**What goes wrong:**
Tests use `@patch` to mock `run_workflow()`, so they pass even when `cmd_run()` has bugs. The UnboundLocalError in `cmd_run` wasn't caught because the real function was never called.

**Why it happens:**
Mocking is faster and avoids side effects, but it doesn't test the actual integration between command parsing and execution.

**How to avoid:**
1. Have three test layers: unit (mocked), integration (real), E2E (subprocess)
2. Integration tests should call real functions without mocks
3. E2E tests should use subprocess to test actual CLI invocation

**Warning signs:**
- Tests use `@patch` on the function they're testing
- `assert_called_with()` checks mock instead of real output
- Code works in tests but fails from command line

### Pitfall 2: Windows Path Handling

**What goes wrong:**
Tests use hardcoded forward slashes (`/path/to/file`) which fail on Windows. Or they assume path separator is `/`.

**Why it happens:**
Developers often test on Unix-like systems (macOS, Linux) and forget Windows differences.

**How to avoid:**
1. Use `pathlib.Path` for all file paths (handles separators automatically)
2. Use `tmp_path` fixture instead of `/tmp/`
3. Test on all three platforms in CI

**Example:**
```python
# Bad - fails on Windows
config_path = "/tmp/test.yaml"

# Good - works everywhere
config_path = tmp_path / "test.yaml"
```

### Pitfall 3: Subprocess Tests Time Out or Hang

**What goes wrong:**
Subprocess tests hang forever if the CLI has a bug or waits for input.

**Why it happens:**
No timeout set on `subprocess.run()`, or CLI prompts for input unexpectedly.

**How to avoid:**
1. Always set `timeout` parameter (e.g., `timeout=30`)
2. Use `capture_output=True` to prevent blocking on stdin
3. Test with invalid inputs to ensure clean exit

**Example:**
```python
result = subprocess.run(
    ["cli", "command"],
    capture_output=True,
    timeout=30,  # Critical: prevents hangs
)
```

### Pitfall 4: Error Messages Not Actionable

**What goes wrong:**
CLI errors say what failed but not how to fix it. Example: "Error: File not found" vs "Error: Config file 'missing.yaml' not found. Create a workflow config file or check the path."

**Why it happens:**
Developers write errors for themselves, not for users. They know what the error means and forget to explain.

**How to avoid:**
1. **Template for error messages:**
   ```
   Error: [What went wrong]
   Cause: [Why it happened]
   Fix: [How to resolve]
   ```
2. Test error messages with regex or substring matches
3. Review all error paths for clarity

**Test example:**
```python
def test_validate_missing_field_shows_suggestion():
    """Test that validation errors include suggestions."""
    result = subprocess.run(
        ["cli", "validate", "incomplete.yaml"],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    # Check for actionable guidance
    assert any(word in result.stderr for word in ["add", "include", "specify", "required"])
```

### Pitfall 5: Testing Only One Command

**What goes wrong:**
Tests cover `run` command but not `validate`, `deploy`, `ui`. Bugs in untested commands ship to users.

**Why it happens:**
`run` is the primary use case, others are added later and get less testing attention.

**How to avoid:**
1. Test matrix: every command should have at least one happy path test and one error path test
2. Use parametrized tests to cover all commands
3. Check coverage report per command

**Parametrization example:**
```python
@pytest.mark.parametrize("command,args,expected_in_output", [
    ("run", ["workflow.yaml"], "completed"),
    ("validate", ["workflow.yaml"], "valid"),
    ("deploy", ["workflow.yaml", "--generate"], "generated"),
])
def test_cli_commands(command, args, expected_in_output, tmp_path):
    """Test all CLI commands have basic functionality."""
    # ... test implementation
```

### Pitfall 6: Cross-Platform Incompatibilities

**What goes wrong:**
CLI works on macOS but fails on Windows due to:
- Different path separators (`\` vs `/`)
- Fork vs spawn process behavior
- Signal handling differences
- Color support in terminals

**Why it happens:**
Python's multiprocessing uses `fork` on Unix but `spawn` on Windows, requiring pickle compatibility.

**How to avoid:**
1. Use `pathlib.Path` for paths
2. Put multiprocess target functions at module level (for pickle)
3. Test on all three platforms in CI
4. Use `subprocess.STARTUPINFO` on Windows for hidden windows

**Example (Windows-compatible process function):**
```python
# Module-level function for pickle compatibility
def _run_service_with_config(config: dict) -> None:
    """Run service - module level for Windows multiprocessing."""
    # Must be at module level, not nested
    run_service(config["host"], config["port"])

# Then use it
from multiprocessing import Process
p = Process(target=_run_service_with_config, args=(config,))
```

**Note:** This pattern is already used in `cli.py` (`_run_dashboard_with_config`, `_run_chat_with_config`).

### Pitfall 7: Assuming CLI is Installed

**What goes wrong:**
Tests import CLI functions directly, but the entry point is broken. CLI works when imported but fails when invoked as command.

**Why it happens:**
Entry point configuration in `pyproject.toml` may be wrong, or module has import side effects.

**How to avoid:**
1. Always have at least one subprocess test that invokes via `python -m`
2. Test actual installed package in CI

## Code Examples

### Example 1: Comprehensive CLI Test Suite

```python
"""
Integration tests for CLI commands using subprocess.

Tests actual CLI invocation, not just function imports.
Catches import errors, entry point bugs, and integration issues.
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestCLICommands:
    """Test all CLI commands work end-to-end."""

    def test_run_help(self):
        """Test that --help works for run command."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()

    def test_validate_help(self):
        """Test that --help works for validate command."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_deploy_help(self):
        """Test that --help works for deploy command."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "deploy", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_ui_help(self):
        """Test that --help works for ui command."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "ui", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0


class TestCLIValidation:
    """Test validate command behavior."""

    def test_validate_valid_config(self, tmp_path):
        """Test validate succeeds on valid config."""
        config = tmp_path / "valid.yaml"
        config.write_text("""
schema_version: "1.0"
flow:
  name: test
state:
  fields:
    msg: {type: str, required: true}
nodes: []
edges: []
""")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "valid" in result.stdout.lower()

    def test_validate_missing_file(self):
        """Test validate fails clearly on missing file."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", "missing.yaml"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        # Clear error message
        assert "not found" in result.stderr.lower() or "no such file" in result.stderr.lower()

    def test_validate_invalid_yaml(self, tmp_path):
        """Test validate fails clearly on malformed YAML."""
        config = tmp_path / "invalid.yaml"
        config.write_text("invalid: yaml: content: [unclosed")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "yaml" in result.stderr.lower() or "syntax" in result.stderr.lower()


class TestCLIRun:
    """Test run command behavior."""

    def test_run_missing_file(self):
        """Test run fails clearly on missing config file."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "run", "missing.yaml"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "no such file" in result.stderr.lower()

    def test_run_invalid_input_format(self, tmp_path):
        """Test run fails on invalid --input format."""
        config = tmp_path / "test.yaml"
        config.write_text("flow:\n  name: test\n")

        result = subprocess.run(
            [
                sys.executable, "-m", "configurable_agents", "run",
                str(config), "--input", "invalid_no_equals"
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "format" in result.stderr.lower() or "equals" in result.stderr.lower()

    @pytest.mark.integration
    def test_run_simple_workflow(self, tmp_path):
        """Integration test: Run actual simple workflow."""
        config = tmp_path / "simple.yaml"
        config.write_text("""
schema_version: "1.0"
flow:
  name: echo_test
state:
  fields:
    message: {type: str, required: true}
nodes:
  - id: echo
    prompt: "Echo: {state.message}"
    outputs: [result]
edges:
  - {from: START, to: echo}
  - {from: echo, to: END}
""")

        result = subprocess.run(
            [
                sys.executable, "-m", "configurable_agents", "run",
                str(config), "--input", "message=HelloWorld"
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # May fail due to API key, but should parse correctly
        assert result.returncode in [0, 1]  # 0=success, 1=API error
        # Check it attempted to run
        assert "echo" in result.stdout.lower() or "api" in result.stderr.lower()


class TestCLIDeploy:
    """Test deploy command behavior."""

    def test_deploy_help(self):
        """Test deploy help shows options."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "deploy", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--generate" in result.stdout

    def test_deploy_generate_only(self, tmp_path):
        """Test deploy --generate exits after artifacts."""
        config = tmp_path / "workflow.yaml"
        config.write_text("flow:\n  name: test\n")

        output_dir = tmp_path / "deploy"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "configurable_agents", "deploy",
                str(config), "--generate", "--output-dir", str(output_dir)
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0
        # Check artifacts created
        assert (output_dir / "Dockerfile").exists() or "dockerfile" in result.stdout.lower()


class TestCLIUI:
    """Test ui command behavior."""

    def test_ui_help(self):
        """Test ui help shows port options."""
        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "ui", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--port" in result.stdout or "--dashboard-port" in result.stdout

    # Note: Actual ui start test is hard due to server startup
    # Consider using timeout and process termination


class TestCrossPlatform:
    """Cross-platform compatibility tests."""

    def test_path_handling(self, tmp_path):
        """Test that paths with spaces work on all platforms."""
        config_dir = tmp_path / "my folder" / "sub folder"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "workflow with spaces.yaml"
        config_file.write_text("flow:\n  name: test\n")

        result = subprocess.run(
            [sys.executable, "-m", "configurable_agents", "validate", str(config_file)],
            capture_output=True,
            text=True,
        )

        # Should handle spaces correctly
        # Note: May return validation error, but not "file not found"
        assert "not found" not in result.stderr.lower()
```

### Example 2: Error Message Validation

```python
"""
Test that CLI error messages are clear and actionable.
"""

def test_error_messages_are_actionable():
    """Verify all error messages provide next steps."""
    # Test each error scenario
    scenarios = [
        ("missing_file.yaml", ["create", "check path", "file not found"]),
        ("invalid.yaml", ["yaml", "syntax", "format"]),
    ]

    for file_hint, expected_words in scenarios:
        result = subprocess.run(
            ["configurable-agents", "validate", file_hint],
            capture_output=True,
            text=True,
        )

        # At least one actionable word should appear
        assert any(word in result.stderr.lower() for word in expected_words), (
            f"Error message not actionable: {result.stderr}"
        )
```

### Example 3: Windows Multiprocessing Compatibility

```python
"""
Test Windows-compatible multiprocessing patterns.

On Windows, multiprocessing uses spawn which requires:
1. Target functions at module level (picklable)
2. No functools.partial with weakrefs
3. Proper if __name__ == "__main__" guards
"""

import subprocess
import sys

def test_ui_command_windows_compatible():
    """Test ui command uses module-level functions for Windows."""
    # The cli.py file should have module-level functions like:
    # def _run_dashboard_with_config(config: dict) -> None:
    #     ...
    #
    # def _run_chat_with_config(config: dict) -> None:
    #     ...

    # Import and verify functions exist at module level
    import configurable_agents.cli as cli_module

    # Check for module-level functions
    assert hasattr(cli_module, "_run_dashboard_with_config")
    assert hasattr(cli_module, "_run_chat_with_config")
    assert hasattr(cli_module, "_run_dashboard_service")
    assert hasattr(cli_module, "_run_chat_service")

    # Verify they're callable
    assert callable(cli_module._run_dashboard_with_config)
    assert callable(cli_module._run_chat_with_config)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tests only happy path | Test all error branches | 2020s | Better reliability |
| Heavily mocked | Layered testing (unit + integration + E2E) | 2018+ | Catch real bugs |
| Unix-only testing | Cross-platform CI | 2020s | Windows support |
| Manual test execution | Automated CI with pytest-xdist | 2019+ | Faster feedback |

**Deprecated/outdated:**
- **unittest.mock for everything**: Mocking entire functions defeats testing purpose
- **Only unit tests**: Integration and E2E tests are essential for CLI
- **Testing only on developer's machine**: CI must test on all platforms

## Open Questions

1. **How to test long-running commands like `ui`?**
   - **What we know:** `ui` starts servers that run indefinitely
   - **What's unclear:** Best pattern to start, verify, and stop servers in tests
   - **Recommendation:** Use `subprocess.Popen` with timeout, send SIGTERM after verification

2. **Should we test `deploy` with real Docker?**
   - **What we know:** `deploy` generates Docker artifacts and optionally builds
   - **What's unclear:** Whether to run actual Docker commands in tests
   - **Recommendation:** Test artifact generation with mocks, test Docker in separate smoke tests

3. **MLFlow dependency for cost-report commands?**
   - **What we know:** Some commands require MLFlow which may not be installed
   - **What's unclear:** How to test gracefully when MLFlow is unavailable
   - **Recommendation:** Use `pytest.importorskip("mlflow")` for MLFlow-dependent tests

## Sources

### Primary (HIGH confidence)

- [4 Techniques for Testing Python Command-Line (CLI) Apps](https://realpython.com/python-cli-testing/) - Comprehensive guide to CLI testing techniques
- [How to test command line applications in Python?](https://stackoverflow.com/questions/51736864/how-to-test-command-line-applications-in-python) - Community approaches
- [Testing shell commands from Python](https://blog.esciencecenter.nl/testing-shell-commands-from-python-2a2ec87ebf71) - Subprocess testing patterns
- [Mocking subprocess with pytest-subprocess](https://til.simonwillison.net/pytest/pytest-subprocess) - Subprocess mocking techniques
- [rhcarvalho/pytest-subprocess-example](https://github.com/rhcarvalho/pytest-subprocess-example) - Example subprocess test code

### Secondary (MEDIUM confidence)

- Project files:
  - `C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents\src\configurable_agents\cli.py` - Current CLI implementation
  - `C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents\tests\test_cli.py` - Existing CLI tests
  - `C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents\tests\test_cli_deploy.py` - Existing deploy tests
  - `C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents\docs\adr\ADR-015-cli-interface-design.md` - CLI design decisions
  - `C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents\.planning\STATE.md` - Known bugs and context
  - `C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents\.planning\research\PITFALLS.md` - UX improvement pitfalls

### Tertiary (LOW confidence)

- General pytest documentation for fixtures and parametrization
- Python subprocess module documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pytest and subprocess are industry standard
- Architecture: HIGH - Based on Real Python's established patterns
- Pitfalls: HIGH - Observed directly in current codebase (UnboundLocalError from over-mocking)

**Research date:** 2026-02-05
**Valid until:** 2026-06-01 (6 months - testing practices evolve slowly)

## Appendix: Current CLI Commands Inventory

Based on analysis of `cli.py`, these commands exist and need testing:

| Command | Purpose | Test Priority |
|---------|---------|---------------|
| `run` | Execute workflow | HIGH - primary use case |
| `validate` | Validate config | HIGH - first step before running |
| `deploy` | Generate deployment artifacts | HIGH - deployment critical |
| `ui` | Start dashboard + chat UI | HIGH - user-facing |
| `dashboard` | Start dashboard only | MEDIUM - subset of ui |
| `chat` | Start chat UI only | MEDIUM - subset of ui |
| `report-costs` | Generate cost report | MEDIUM - observability |
| `cost-report` | Unified cost report (Rich) | LOW - requires Rich |
| `profile-report` | Profiling report | LOW - optimization |
| `observability-status` | Show MLFlow status | LOW - debugging |
| `agent-registry` (start/list/cleanup) | Agent registry commands | LOW - advanced feature |

**Success criteria for Phase 07:**
1. All HIGH priority commands have subprocess tests
2. All error paths tested with actionable message verification
3. Tests run on Windows, macOS, and Linux in CI
4. Existing bugs (UnboundLocalError, etc.) are covered by regression tests
