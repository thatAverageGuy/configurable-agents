# Testing Patterns

**Analysis Date:** 2026-02-02

## Test Framework

**Runner:**
- `pytest` (v7.4.0+)
- Config: `pytest.ini` (at root) and `pyproject.toml`
- Python: 3.10+

**Assertion Library:**
- Built-in `assert` statements (pytest default)
- `pytest.raises()` for exception testing
- `unittest.mock` for mocking/patching

**Run Commands:**
```bash
pytest                              # Run all tests
pytest -v                           # Verbose output
pytest tests/config/               # Run specific directory
pytest -k test_execute_node         # Run matching tests
pytest --cov=configurable_agents    # With coverage
pytest -m "not integration"         # Exclude integration tests
pytest -m "unit"                    # Run only unit tests
```

## Test File Organization

**Location:**
- Co-located strategy: test files mirror source structure
- `src/configurable_agents/config/schema.py` → `tests/config/test_schema.py`
- `src/configurable_agents/core/node_executor.py` → `tests/core/test_node_executor.py`

**Naming:**
- Test files: `test_<module>.py`
- Test classes: `Test<Subject>` (e.g., `TestFlowMetadata`, `TestNodeExecutor`)
- Test functions: `test_<specific_behavior>` (e.g., `test_execute_node_simple_output`)
- Fixtures: lowercase with underscores: `sample_config`, `simple_state`, `check_google_api_key`

**Structure:**
```
tests/
├── conftest.py                    # Shared fixtures for all tests
├── config/
│   ├── __init__.py
│   ├── conftest.py               # Config-specific fixtures (if needed)
│   ├── fixtures/                 # Config test data
│   ├── test_parser.py
│   ├── test_schema.py
│   ├── test_schema_integration.py
│   ├── test_types.py
│   ├── test_validator.py
├── core/
│   ├── __init__.py
│   ├── test_graph_builder.py
│   ├── test_node_executor.py
│   ├── test_output_builder.py
│   ├── test_state_builder.py
│   ├── test_template.py
├── deploy/
│   ├── test_generator.py
│   ├── test_generator_integration.py
│   ├── test_server_integration.py
│   ├── test_server_template.py
├── integration/
│   ├── conftest.py              # Integration test fixtures
│   ├── test_error_scenarios.py
│   └── [other integration tests]
```

## Test Structure

**Suite Organization:**
Classes group related tests:
```python
class TestFlowMetadata:
    """Test FlowMetadata model."""

    def test_valid_minimal(self):
        """Should create with only required fields."""
        flow = FlowMetadata(name="test_flow")
        assert flow.name == "test_flow"
```

Source: `tests/config/test_schema.py` lines 28-35

**Setup Pattern:**
- Use pytest fixtures for shared state
- Create test data directly in test methods (no setUp/tearDown for simple tests)
- Use `tmp_path` fixture for file operations

**Teardown Pattern:**
- Pytest handles cleanup automatically via fixture scope
- No explicit cleanup needed for mocks (teardown automatic)
- Use `@pytest.fixture(scope="session")` for expensive setup

**Assertion Pattern:**
- Simple assert statements: `assert updated_state.research == "..."`
- Verify state immutability: `assert updated_state is not state` (copy-on-write)
- Verify mock calls: `mock_call_llm.assert_called_once()`, `call_kwargs = mock_call_llm.call_args[1]`
- Use `pytest.raises()` for exception testing (see `tests/config/test_schema.py` line 46-47)

Example from `tests/core/test_node_executor.py` lines 135-171:
```python
@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_execute_node_simple_output(mock_build_output, mock_create_llm, mock_call_llm):
    """Should execute node with simple output"""
    state = SimpleState(topic="AI Safety", research="", score=0)
    node_config = NodeConfig(
        id="test_node",
        prompt="Research {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )
    mock_build_output.return_value = SimpleOutput
    mock_result = SimpleOutput(result="AI safety research findings...")
    mock_call_llm.return_value = (mock_result, make_usage())

    updated_state = execute_node(node_config, state)

    assert updated_state.research == "AI safety research findings..."
    assert updated_state is not state
    mock_call_llm.assert_called_once()
```

## Mocking

**Framework:** `unittest.mock` (standard library)

**Patterns:**
- `@patch()` decorator for function/method replacement
- Patch at usage point: `@patch("module.function_used_here")` not where defined
- Example: `@patch("configurable_agents.core.node_executor.call_llm_structured")` patches call site in node_executor

**Mock Setup:**
```python
# Simple return value
mock_object.return_value = expected_value

# Tuple return (for functions returning multiple values)
mock_object.return_value = (result, usage_metadata)

# Side effect for exceptions
mock_object.side_effect = ValueError("error message")
```

**Verification:**
- `mock_object.assert_called_once()` - called exactly once
- `mock_object.assert_called_with(arg1, arg2)` - called with specific args
- `call_kwargs = mock_object.call_args[1]` - extract kwargs from last call
- `assert mock_object.call_count == 2` - count calls

**What to Mock:**
- External API calls (LLM, tools, services)
- File I/O and network operations
- Database connections
- Third-party library calls

**What NOT to Mock:**
- Pydantic model validation (test real models)
- Core business logic (test actual implementation)
- Custom exceptions (test real ones)
- Helper functions within module being tested

Example from `tests/core/test_node_executor.py`: Mocks `call_llm_structured()` but tests `_strip_state_prefix()` directly (lines 78-125)

## Fixtures and Factories

**Test Data:**
`tests/conftest.py` defines shared fixtures:
```python
@pytest.fixture
def sample_config():
    """Sample minimal workflow configuration for testing"""
    return {
        "schema_version": "1.0",
        "flow": {"name": "test_workflow", ...},
        "state": {"fields": {...}},
        ...
    }
```

**Location:**
- Shared fixtures: `tests/conftest.py` (root level)
- Module-specific fixtures: `tests/<module>/conftest.py` (if needed)
- Integration fixtures: `tests/integration/conftest.py`

**Example Fixtures from Codebase:**

From `tests/conftest.py`:
- `sample_config`: Minimal valid workflow config dict
- `check_google_api_key`: Session-scoped, skips test if env var missing

From `tests/integration/conftest.py`:
- `check_google_api_key`: Validate required API keys
- `check_serper_api_key`: Tool integration validation
- `examples_dir`: Path to examples/
- `echo_workflow`, `simple_workflow`, etc.: Paths to example YAML files
- `api_tracker`: Session-scoped tracker for cost reporting
- `run_workflow_with_timing()`: Helper function fixture
- `validate_workflow_helper()`: Validator wrapper

**Test Helpers:**
```python
def make_usage(input_tokens=100, output_tokens=50):
    """Create mock LLM usage metadata."""
    return LLMUsageMetadata(input_tokens=input_tokens, output_tokens=output_tokens)
```
Source: `tests/core/test_node_executor.py` lines 36-38

## Coverage

**Requirements:** None enforced (but testing is comprehensive across modules)

**View Coverage:**
```bash
pytest --cov=configurable_agents --cov-report=html
# Opens htmlcov/index.html with coverage breakdown by file
```

**Coverage by Module:**
Based on test file existence and structure:
- `src/configurable_agents/config/`: Well-covered (5 test files)
- `src/configurable_agents/core/`: Well-covered (5 test files)
- `src/configurable_agents/llm/`: Covered (via core tests + LLM-specific tests)
- `src/configurable_agents/observability/`: Cost tracker tested
- `src/configurable_agents/deploy/`: Deployment code tested (4 test files)

## Test Types

**Unit Tests:**
- Scope: Individual functions/classes in isolation
- Example: `tests/config/test_schema.py` - Tests Pydantic model validation
- Example: `tests/core/test_template.py` - Tests prompt template resolution
- Use mocks for external dependencies
- Fast execution (< 1 second per test)
- Location: Most tests without `_integration` suffix

**Integration Tests:**
- Scope: Multiple components working together
- Markers: `@pytest.mark.integration`
- Example: `tests/config/test_schema_integration.py` - Full config parsing + validation
- Example: `tests/deploy/test_server_integration.py` - Deploy server setup
- Example: `tests/integration/test_error_scenarios.py` - Real error handling paths
- May use real external services if API keys available
- Slower execution (seconds to minutes)
- Can be skipped with: `pytest -m "not integration"`

**E2E Tests:**
- Framework: Not explicitly used; integration tests serve this purpose
- Real workflows with actual LLM calls marked with `@pytest.mark.integration`
- Example: `tests/integration/` directory contains workflow end-to-end tests
- Require environment variables (GOOGLE_API_KEY, SERPER_API_KEY)

## Common Patterns

**Async Testing:**
Not used in current codebase (no async functions). If needed, use `pytest-asyncio`:
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_func()
    assert result == expected
```

**Error Testing:**
```python
# Pattern 1: Using pytest.raises
with pytest.raises(ValidationError) as exc_info:
    FlowMetadata(name="")
assert "cannot be empty" in str(exc_info.value).lower()

# Pattern 2: Checking exception attributes
try:
    raise NodeExecutionError("message", node_id="node1")
except NodeExecutionError as e:
    assert e.node_id == "node1"
```

Examples from `tests/config/test_schema.py` lines 45-56 and `tests/integration/test_error_scenarios.py` lines 52-58

**Parametrized Tests:**
Not heavily used; tests are explicit and descriptive instead. Could use `@pytest.mark.parametrize()` for data-driven tests if needed.

**Fixture Scope:**
```python
@pytest.fixture(scope="function")  # Default - new per test
@pytest.fixture(scope="class")     # Shared within class
@pytest.fixture(scope="module")    # Shared within module
@pytest.fixture(scope="session")   # Shared across all tests
```

Examples from `tests/integration/conftest.py`:
- `scope="session"`: `check_google_api_key`, `examples_dir`, `api_tracker`
- `scope="function"`: `track_api_call`, `run_workflow_with_timing`

## Test Markers

**Defined in `pytest.ini`:**
```
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests (require API keys)
    unit: marks tests as unit tests (no external dependencies)
```

**Usage:**
```python
@pytest.mark.slow
def test_real_api_call(): ...

@pytest.mark.integration
def test_with_google_api(): ...

@pytest.mark.unit
def test_schema_validation(): ...
```

**Run with markers:**
```bash
pytest -m "not integration"   # Exclude integration tests
pytest -m "unit"              # Only unit tests
pytest -m "slow"              # Only slow tests
```

## Test Configuration

**File:** `pytest.ini` and `pyproject.toml`

**Key Settings:**
```ini
[pytest]
minversion = "7.0"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",                    # Verbose
    "--strict-markers",      # Fail on unknown markers
    "--tb=short",           # Short traceback format
    "--disable-warnings",   # Hide warnings
]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration",
    "unit: marks tests as unit",
]
```

---

*Testing analysis: 2026-02-02*
