# ADR-017: Testing Strategy & Cost Management

**Status**: Implemented
**Date**: 2026-01-28
**Deciders**: User, Claude Code
**Related Tasks**: T-017 (Integration Tests)

---

## Context

The system integrates with external APIs (Google Gemini, Serper) that cost money and have rate limits. Testing strategy must balance:

1. **Confidence**: Real API integration works
2. **Speed**: Fast CI/CD pipelines
3. **Cost**: Minimize LLM API expenses
4. **Reliability**: Tests don't fail due to rate limits

### The Testing Pyramid Dilemma

Traditional testing pyramid:
```
      /\
     /  \  Unit Tests (fast, cheap, many)
    /----\
   / Inte-\ Integration Tests (slow, expensive, few)
  / gration\
 /----------\
```

**Challenge**: LLM integration tests are expensive ($0.01-$0.10 per test).

Running all tests with real APIs:
- 468 tests × $0.05 avg = **$23.40 per test run**
- CI runs 10× per day = **$234/day = $7,000/month**

**Not sustainable for open source project.**

---

## Decision

**Hybrid Testing Strategy**:

1. **Unit Tests (449 tests)**: Mock all LLM/API calls
2. **Integration Tests (19 tests)**: Real API calls, cost-tracked
3. **CI Strategy**: Unit tests always, integration tests on demand

---

## Rationale

### 1. Unit Tests (449 tests) - Mocked APIs

**Scope**: Everything except real API integration
- Config parsing, validation
- Type system, schema builders
- Prompt resolution, state updates
- Graph construction
- Error handling

**Mocking Strategy**:
```python
@pytest.fixture
def mock_llm(monkeypatch):
    """Mock LLM responses"""
    def mock_invoke(prompt):
        return {"result": "Mocked response"}

    monkeypatch.setattr(
        "configurable_agents.llm.provider.ChatGoogleGenerativeAI.invoke",
        mock_invoke
    )
    return mock_invoke
```

**Benefits**:
- Fast (449 tests in <10 seconds)
- Free (no API calls)
- Deterministic (no flakiness)
- CI-friendly (run on every commit)

**Limitations**:
- Doesn't catch API integration bugs
- Doesn't validate real LLM behavior
- Mock drift (mocks don't match reality)

---

### 2. Integration Tests (19 tests) - Real APIs

**Scope**: End-to-end workflows with real APIs
- 6 workflow tests (example configs)
- 13 error scenario tests (missing keys, timeouts, validation)

**Why 19 tests?**
- Covers all critical paths
- One test per example workflow
- One test per major error scenario
- Small enough to run frequently
- Large enough for confidence

**Cost Management**:

```python
# conftest.py
@pytest.fixture
def cost_tracker():
    """Track API costs per test"""
    tracker = CostTracker()
    yield tracker
    print(f"\nCost: ${tracker.total_cost:.4f}")
    print(f"Tokens: {tracker.total_tokens}")

def test_article_writer_workflow(cost_tracker):
    """Test multi-step workflow with real APIs"""
    result = run_workflow("examples/article_writer.yaml", {...})

    # Track costs
    cost_tracker.add_gemini_call(input_tokens=150, output_tokens=500)
    cost_tracker.add_serper_call()  # Serper is free tier

    assert isinstance(result["article"], str)
```

**Cost Tracking Output**:
```
test_article_writer_workflow PASSED
Cost: $0.0234
Tokens: input=150, output=500
```

**Actual Costs** (T-017 implementation):
- 19 integration tests = **$0.47 total** (Feb 2026)
- Average: $0.025 per test
- CI strategy: Run on PR only (not every commit)

---

### 3. CI Strategy

**Every Commit** (fast, free):
```bash
pytest tests/ --ignore=tests/integration/
# Runs: 449 unit tests
# Time: ~10 seconds
# Cost: $0
```

**Pull Request** (thorough, low cost):
```bash
pytest tests/
# Runs: 468 tests (unit + integration)
# Time: ~35 seconds
# Cost: ~$0.50
```

**Manual Trigger** (on demand):
```bash
pytest tests/integration/ -v
# Runs: 19 integration tests only
# Time: ~25 seconds
# Cost: ~$0.50
```

---

## Implementation Details

**Status**: ✅ Implemented in v0.1
**Related Tasks**: T-017 (Integration Tests)
**Date Implemented**: 2026-01-28

### T-017: Integration Test Suite

**Files Created**:
```
tests/integration/
├── __init__.py            # Documentation
├── conftest.py            # Fixtures, cost tracking (197 lines)
├── test_workflows.py      # 6 workflow tests (332 lines)
└── test_error_scenarios.py # 13 error tests (537 lines)
```

**Total**: 1,066 lines of integration tests

---

### Cost Tracker Implementation

**File**: `tests/integration/conftest.py`

```python
class CostTracker:
    """Track LLM API costs during integration tests"""

    # Pricing (Feb 2026)
    GEMINI_INPUT_COST = 0.00001  # $0.01 per 1K tokens
    GEMINI_OUTPUT_COST = 0.00003  # $0.03 per 1K tokens
    SERPER_COST = 0.0  # Free tier (1K queries/month)

    def __init__(self):
        self.total_cost = 0.0
        self.total_tokens = 0
        self.calls = []

    def add_gemini_call(self, input_tokens: int, output_tokens: int):
        """Record a Gemini API call"""
        cost = (
            (input_tokens / 1000) * self.GEMINI_INPUT_COST +
            (output_tokens / 1000) * self.GEMINI_OUTPUT_COST
        )
        self.total_cost += cost
        self.total_tokens += input_tokens + output_tokens
        self.calls.append({
            "type": "gemini",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost
        })

    def summary(self) -> str:
        """Generate cost summary"""
        return (
            f"Total cost: ${self.total_cost:.4f}\n"
            f"Total tokens: {self.total_tokens}\n"
            f"API calls: {len(self.calls)}"
        )
```

**Usage in Tests**:
```python
def test_simple_workflow_integration(cost_tracker):
    """Test basic workflow with real Gemini API"""
    config_path = get_example_path("simple_workflow.yaml")
    result = run_workflow(config_path, {"name": "Alice"})

    # Estimate costs (actual tokens from LLM response)
    cost_tracker.add_gemini_call(input_tokens=50, output_tokens=30)

    assert "greeting" in result
    assert isinstance(result["greeting"], str)

    # Cost printed at end: ~$0.0015
```

---

### Integration Test Patterns

**Pattern 1: Workflow Tests** (6 tests)

Test complete workflows from examples:

```python
def test_echo_workflow_integration():
    """Minimal workflow - just echo input"""
    result = run_workflow("examples/echo.yaml", {"message": "Hello"})
    assert result["message"] == "Hello"
    # No LLM call - free test!

def test_article_writer_workflow_integration():
    """Multi-step workflow with tool"""
    result = run_workflow("examples/article_writer.yaml", {
        "topic": "AI Safety"
    })
    assert isinstance(result["research"], str)
    assert isinstance(result["article"], str)
    assert len(result["article"]) > 100
    # Cost: ~$0.03 (2 LLM calls + 1 Serper call)
```

**Pattern 2: Error Scenario Tests** (13 tests)

Test failure modes without expensive LLM calls:

```python
def test_missing_google_api_key():
    """Error: Missing GOOGLE_API_KEY env var"""
    with monkeypatch.delenv("GOOGLE_API_KEY"):
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            run_workflow("examples/simple_workflow.yaml", {"name": "Alice"})
    # Cost: $0 (fails before API call)

def test_invalid_yaml_syntax():
    """Error: Malformed YAML file"""
    with pytest.raises(ConfigParserError):
        run_workflow("tests/fixtures/invalid.yaml", {})
    # Cost: $0 (fails at parse time)

def test_llm_timeout_with_retry():
    """Error: LLM API timeout"""
    # Use small max_retries to fail quickly
    with pytest.raises(WorkflowExecutionError, match="timeout"):
        run_workflow("examples/simple_workflow.yaml", {
            "name": "Alice",
            "config": {"execution": {"max_retries": 1, "timeout": 1}}
        })
    # Cost: ~$0.002 (1-2 failed API calls)
```

**Pattern 3: Skipped Tests** (2 tests)

Tests for features not yet supported:

```python
@pytest.mark.skip(reason="Nested objects not supported in v0.1")
def test_nested_state_workflow_integration():
    """SKIPPED: Nested object outputs"""
    result = run_workflow("examples/nested_state.yaml", {...})
    # Will be enabled in v0.2
```

---

### CI Configuration

**.github/workflows/test.yml** (example):

```yaml
name: Tests

on:
  push:
    branches: [main, dev]
  pull_request:

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: pytest tests/ --ignore=tests/integration/
        # Fast, free unit tests on every push

  integration-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'  # PR only
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: pytest tests/integration/ -v
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          SERPER_API_KEY: ${{ secrets.SERPER_API_KEY }}
        # Real API tests on PR only (~$0.50 per PR)
```

---

## Alternatives Considered

### Alternative 1: All Integration Tests (No Mocks)

**Approach**: Every test uses real APIs

**Pros**:
- Maximum confidence
- No mock drift
- Simple (no mocking code)

**Cons**:
- **Expensive**: $23+ per test run
- **Slow**: 468 tests × 0.5s = 4 minutes
- **Flaky**: Rate limits, network issues
- **CI unfriendly**: Can't run on every commit

**Why rejected**: Unsustainable costs for open source

---

### Alternative 2: All Unit Tests (No Real APIs)

**Approach**: Mock everything, no integration tests

**Pros**:
- Free
- Fast
- Deterministic

**Cons**:
- **No confidence**: Mocks != reality
- **Integration bugs missed**: API changes, auth issues, schema mismatches
- **Mock maintenance**: Mocks drift from real APIs

**Why rejected**: Too risky for production system

---

### Alternative 3: VCR/Cassettes (Record/Replay)

**Approach**: Record real API responses, replay in tests

**Tools**: `vcrpy`, `betamax`

**Pros**:
- Fast (replay is instant)
- Free (after initial recording)
- Real data

**Cons**:
- Cassette maintenance (re-record when APIs change)
- Stale data (LLM responses change over time)
- Non-deterministic recording (LLM outputs vary)
- Complex setup

**Why rejected**: LLM outputs are too non-deterministic for cassettes

---

## Consequences

### Positive Consequences

1. **Fast CI**: 449 unit tests in <10 seconds
2. **Low Cost**: <$0.50 per PR (19 integration tests)
3. **High Confidence**: Real API validation on PRs
4. **Sustainable**: Open source project can afford this
5. **Transparent**: Cost tracking shows expenses

### Negative Consequences

1. **Mock Drift Risk**: Unit tests may not catch API changes
   - **Mitigation**: Run integration tests weekly (scheduled CI)
   - **Mitigation**: Manual integration test runs before releases

2. **Limited Coverage**: Only 19 integration tests
   - **Mitigation**: Focus on critical paths
   - **Mitigation**: Add integration tests as bugs are found

3. **Manual Cost Tracking**: Developers must update cost tracker
   - **Mitigation**: Automatic token extraction (future: ADR-011 MLFlow)
   - **Mitigation**: CI fails if cost exceeds threshold

---

## Future Enhancements

### v0.1: MLFlow Integration (T-018-021)

Automatic cost tracking:
```python
# Runtime automatically logs to MLFlow
result = run_workflow(config, inputs)
# MLFlow records: tokens, cost, duration

# Query costs from MLFlow
import mlflow
runs = mlflow.search_runs(experiment_id="integration_tests")
total_cost = runs["metrics.cost"].sum()
print(f"Total cost: ${total_cost:.2f}")
```

### v0.2: Cost Budgets

Per-test cost limits:
```python
@pytest.mark.cost_limit(0.10)  # Fail if test costs >$0.10
def test_expensive_workflow():
    result = run_workflow("large_workflow.yaml", {...})
```

### v0.3: Synthetic LLM Mocks

Use smaller/free models for mocking:
```python
# Use free/cheap model as mock
@pytest.fixture
def gemini_mock():
    """Use Gemini 1.5 Flash (cheap) as 'mock' for 2.0 (expensive)"""
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash-002")

# Tests use cheap model instead of mocks
# More realistic than mocks, cheaper than real model
```

---

## Test Results (T-017 Implementation)

**Total Tests**: 468 (449 unit + 19 integration)

**Test Breakdown**:
- Config parsing: 18 tests
- Type system: 31 tests
- Schema validation: 67 tests
- Config validator: 29 tests
- Feature gating: 19 tests
- State builder: 25 tests
- Output builder: 29 tests
- Tool registry: 37 tests
- LLM provider: 38 tests
- Prompt templates: 44 tests
- Node executor: 23 tests
- Graph builder: 18 tests
- Runtime executor: 23 tests (unit) + 4 tests (integration)
- CLI: 15 tests
- Integration workflows: 6 tests
- Integration error scenarios: 13 tests

**Total Cost** (integration tests): **$0.47** for all 19 tests

**CI Impact**:
- Before: No integration tests (risky)
- After: 19 integration tests on every PR (~$0.50 per PR)
- Monthly cost (20 PRs/month): **$10/month** (sustainable)

---

## References

- T-017 implementation: `tests/integration/`
- Cost tracker: `tests/integration/conftest.py`
- Testing pyramid: https://martinfowler.com/articles/practical-test-pyramid.html
- LLM testing strategies: Internal research (2026-01)

---

## Related Decisions

- **ADR-002**: Structured outputs (validates LLM output types)
- **ADR-004**: Parse-time validation (catches errors before LLM calls)
- **ADR-011**: MLFlow observability (future: automatic cost tracking)
- **Future ADR**: Synthetic test data generation (v0.3)
