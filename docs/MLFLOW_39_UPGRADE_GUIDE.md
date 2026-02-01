# MLFlow 3.9 Upgrade Implementation Guide

> **⚠️ IMPORTANT**: This document represents the **initial incremental migration approach**.
>
> **Strategy has been updated** to a **comprehensive, all-at-once migration** with thorough planning first.
>
> See **ADR-018** for the updated comprehensive migration strategy.
>
> This document will be recreated during the planning phases with the new approach.
>
> **Status**: Superseded - Reference only

---

# Original Document (Incremental Approach - Superseded)

**Task**: T-028 (MLFlow 3.9 Upgrade for GenAI/Agent Tracing)
**Decision**: ADR-018
**Target**: MLFlow 2.9+ → MLFlow 3.9
**Timeline**: 3 days (Phases 1-4)
**Risk Level**: Low (Backward compatible approach)

---

## Table of Contents

1. [Overview](#overview)
2. [Current State Analysis](#current-state-analysis)
3. [Target State](#target-state)
4. [Implementation Phases](#implementation-phases)
5. [Code Changes Detailed](#code-changes-detailed)
6. [Testing Strategy](#testing-strategy)
7. [Rollback Plan](#rollback-plan)
8. [Success Criteria](#success-criteria)

---

## Overview

### Why Upgrade?

**Current**: MLFlow 2.9+ with manual instrumentation
**Target**: MLFlow 3.9 with GenAI auto-instrumentation

**Benefits**:
- ✅ **Auto-instrumentation**: `mlflow.langchain.autolog()` for LangGraph
- ✅ **Better backend**: SQLite default (faster than file-based)
- ✅ **GenAI dashboard**: Agent-specific metrics and visualizations
- ✅ **Graceful fallback**: Auto-fallback to SQLite if server unreachable
- ✅ **Less code**: Reduce custom tracking by ~30%
- ✅ **Future-proof**: Aligned with MLFlow's GenAI direction

### Migration Strategy

**Approach**: Gradual, backward-compatible upgrade

**Phases**:
1. **Phase 1**: Safe dependency upgrade (no API changes)
2. **Phase 2**: Add optional auto-instrumentation
3. **Phase 3**: Update documentation
4. **Phase 4**: Comprehensive testing

**Compatibility**: All existing configs continue to work

---

## Current State Analysis

### Files to Modify

| File | Current Lines | Changes | Complexity |
|------|---------------|---------|------------|
| `pyproject.toml` | 1 line | Dependency version | Trivial |
| `mlflow_tracker.py` | ~400 lines | +100 lines (fallback, autolog) | Moderate |
| `executor.py` | ~300 lines | +10 lines (autolog init) | Low |
| `test_mlflow_tracker.py` | ~200 lines | +50 lines (new mocks) | Moderate |
| `OBSERVABILITY.md` | ~800 lines | +200 lines (3.9 features) | Low |
| `CONFIG_REFERENCE.md` | ~500 lines | +50 lines (autolog option) | Low |
| Examples | 4 files | +2 new examples | Low |

**Total Estimated Changes**: ~400 lines added, ~50 lines modified

### Current MLFlow Usage Patterns

**Pattern 1: Manual Run Management**
```python
# Current pattern in mlflow_tracker.py
@contextmanager
def track_workflow(self, inputs: Dict[str, Any]):
    mlflow.start_run(run_name=...)
    mlflow.log_params(inputs)
    yield
    mlflow.log_metrics(...)
    mlflow.end_run()
```

**Pattern 2: Nested Node Tracking**
```python
# Current pattern for nodes
@contextmanager
def track_node(self, node_id, model):
    mlflow.start_run(run_name=node_id, nested=True)
    mlflow.log_param("node_id", node_id)
    mlflow.log_param("model", model)
    yield
    # Logs metrics/artifacts
    mlflow.end_run()
```

**Pattern 3: Manual Instrumentation**
```python
# In executor.py
with tracker.track_node(node.id, model):
    result = execute_node(node, state, config)
    tracker.log_node_metrics(tokens_used=...)
```

### Current Configuration Schema

```yaml
observability:
  mlflow:
    enabled: true
    tracking_uri: "file://./mlruns"  # File-based default
    experiment_name: "workflow_experiments"
    log_prompts: true
    log_artifacts: true
```

### Current Pain Points

1. **Verbose Manual Tracking**: ~50 lines of boilerplate for context managers
2. **File-Based Limitations**: Slow for multiple runs, locking issues
3. **No LangGraph Visibility**: Can't see internal LangGraph spans
4. **Server Failures**: Long timeouts (partially fixed in BUG-004)
5. **No Agent Metrics**: Generic run metrics, not agent-specific

---

## Target State

### New MLFlow 3.9 Patterns

**Pattern 1: Auto-Instrumentation**
```python
# New pattern - automatic tracing
import mlflow.langchain

# Enable once at initialization
mlflow.langchain.autolog()

# All LangGraph operations automatically traced!
graph = build_graph(config, state_model)
result = graph.invoke(state)  # ← Auto-creates spans
```

**Pattern 2: Decorator-Based Tracing**
```python
# New pattern - decorator for custom functions
from mlflow.entities import SpanType

@mlflow.trace(name="execute_workflow", span_type=SpanType.CHAIN)
def run_workflow(config, inputs):
    # Entire workflow wrapped in trace
    graph = build_graph(config)
    result = graph.invoke(inputs)
    return result
```

**Pattern 3: Fallback to SQLite**
```python
# New pattern - graceful degradation
def _initialize_mlflow(self):
    try:
        if not self._check_server_accessible(timeout=3):
            logger.warning("Server unreachable, using SQLite")
            mlflow.set_tracking_uri("sqlite:///mlflow.db")
        else:
            mlflow.set_tracking_uri(self.config.tracking_uri)
    except Exception as e:
        logger.warning(f"Fallback to SQLite: {e}")
        mlflow.set_tracking_uri("sqlite:///mlflow.db")
```

### New Configuration Schema

```yaml
observability:
  mlflow:
    enabled: true
    tracking_uri: "sqlite:///mlflow.db"  # New default
    experiment_name: "workflow_experiments"
    autolog_enabled: true  # NEW: Enable auto-instrumentation
    log_prompts: true
    log_artifacts: true
```

---

## Implementation Phases

### Phase 1: Safe Upgrade (1 day)

**Goal**: Upgrade dependency without breaking changes

#### Step 1.1: Update Dependency (5 minutes)

**File**: `pyproject.toml`

```toml
# Before
[project]
dependencies = [
    "mlflow>=2.9.0",
    ...
]

# After
[project]
dependencies = [
    "mlflow>=3.9.0",
    ...
]
```

**Verification**:
```bash
pip install -e .
python -c "import mlflow; print(mlflow.__version__)"
# Should print: 3.9.0
```

#### Step 1.2: Add Fallback Logic (2 hours)

**File**: `src/configurable_agents/observability/mlflow_tracker.py`

**Add new method**:
```python
def _get_fallback_uri(self) -> str:
    """
    Get fallback tracking URI when primary fails.

    Returns SQLite URI for local tracking.
    """
    fallback = "sqlite:///mlflow.db"
    logger.info(f"Using fallback tracking URI: {fallback}")
    return fallback

def _initialize_mlflow(self) -> None:
    """Initialize MLFlow tracking URI and experiment with fallback."""
    if not self.enabled:
        return

    tracking_uri = self.mlflow_config.tracking_uri

    try:
        # Check if tracking server is accessible (for HTTP URIs)
        if not self._check_tracking_server_accessible(timeout=3.0):
            logger.warning(
                f"MLFlow tracking server not accessible at {tracking_uri}. "
                "Falling back to local SQLite tracking. "
                "For remote tracking, ensure server is running. "
                "For local tracking, use: tracking_uri='file://./mlruns' or 'sqlite:///mlflow.db'"
            )
            tracking_uri = self._get_fallback_uri()

        # Set tracking URI
        mlflow.set_tracking_uri(tracking_uri)
        logger.debug(f"MLFlow tracking URI: {tracking_uri}")

        # Configure environment variables for faster timeouts
        os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "10")

        # Set or create experiment
        experiment = mlflow.set_experiment(self.mlflow_config.experiment_name)
        logger.debug(
            f"MLFlow experiment: {self.mlflow_config.experiment_name} "
            f"(ID: {experiment.experiment_id})"
        )

    except Exception as e:
        logger.error(f"Failed to initialize MLFlow: {e}")
        logger.warning("Attempting fallback to SQLite")

        try:
            # Last resort: fallback to SQLite
            mlflow.set_tracking_uri(self._get_fallback_uri())
            mlflow.set_experiment(self.mlflow_config.experiment_name)
            logger.info("Successfully initialized with SQLite fallback")
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            logger.warning("Disabling MLFlow tracking for this run")
            self.enabled = False
```

**Key Changes**:
- Fallback to SQLite if server unreachable
- Clear warning messages
- Double fallback (server → SQLite → disable)

#### Step 1.3: Update Tests (2 hours)

**File**: `tests/observability/test_mlflow_tracker.py`

**Add tests**:
```python
def test_fallback_to_sqlite_when_server_unreachable(mocker):
    """Test fallback to SQLite when HTTP server unreachable."""
    # Mock server check to return False
    mocker.patch.object(
        MLFlowTracker,
        "_check_tracking_server_accessible",
        return_value=False
    )

    config = ObservabilityMLFlowConfig(
        enabled=True,
        tracking_uri="http://localhost:9999",  # Unreachable
        experiment_name="test"
    )

    with patch("mlflow.set_tracking_uri") as mock_set_uri:
        tracker = MLFlowTracker(config, mock_workflow_config)

        # Should call with SQLite fallback
        mock_set_uri.assert_called_with("sqlite:///mlflow.db")

def test_double_fallback_when_sqlite_fails(mocker):
    """Test disabling MLFlow when even SQLite fallback fails."""
    mocker.patch("mlflow.set_tracking_uri", side_effect=Exception("DB error"))

    config = ObservabilityMLFlowConfig(
        enabled=True,
        tracking_uri="http://localhost:9999",
        experiment_name="test"
    )

    tracker = MLFlowTracker(config, mock_workflow_config)

    # Should disable tracking
    assert tracker.enabled == False
```

#### Step 1.4: Run Tests (30 minutes)

```bash
# Unit tests
pytest tests/observability/test_mlflow_tracker.py -v

# Integration tests (optional, costs ~$0.50)
pytest tests/integration/test_mlflow_integration.py -v

# All tests
pytest -v
```

**Expected**: All tests pass

---

### Phase 2: Auto-Instrumentation (1 day)

**Goal**: Add optional auto-instrumentation

#### Step 2.1: Add Configuration (15 minutes)

**File**: `src/configurable_agents/config/schema.py`

**Update `ObservabilityMLFlowConfig`**:
```python
class ObservabilityMLFlowConfig(BaseModel):
    """MLFlow observability config."""

    enabled: bool = Field(False, description="Enable MLFlow tracking")
    tracking_uri: str = Field(
        "sqlite:///mlflow.db",  # NEW DEFAULT (was file://./mlruns)
        description="MLFlow backend URI"
    )
    experiment_name: str = Field(
        "configurable_agents",
        description="Experiment name for grouping runs"
    )
    run_name: Optional[str] = Field(
        None,
        description="Template for run names"
    )

    # NEW FIELD
    autolog_enabled: bool = Field(
        False,
        description="Enable automatic instrumentation for LangChain/LangGraph (MLFlow 3.9+)"
    )

    # ... rest of fields unchanged
```

#### Step 2.2: Implement Auto-Instrumentation (3 hours)

**File**: `src/configurable_agents/observability/mlflow_tracker.py`

**Add to `__init__`**:
```python
def __init__(
    self,
    mlflow_config: ObservabilityMLFlowConfig,
    workflow_config: WorkflowConfig,
):
    """Initialize MLFlow tracker with auto-instrumentation support."""
    self.mlflow_config = mlflow_config
    self.workflow_config = workflow_config

    # Check if MLFlow is available
    if not MLFLOW_AVAILABLE:
        self.enabled = False
        logger.warning("MLFlow not installed, tracking disabled")
        return

    self.enabled = mlflow_config.enabled

    # Initialize MLFlow
    if self.enabled:
        self._initialize_mlflow()

        # Enable auto-instrumentation if configured
        if mlflow_config.autolog_enabled:
            self._enable_autolog()

    # ... rest of initialization

def _enable_autolog(self) -> None:
    """Enable automatic instrumentation for LangChain/LangGraph."""
    try:
        import mlflow.langchain

        # Enable LangChain auto-logging
        mlflow.langchain.autolog(
            log_inputs=self.mlflow_config.log_prompts,
            log_outputs=self.mlflow_config.log_prompts,
            log_traces=True,
            disable=False,
            silent=False
        )

        logger.info("MLFlow auto-instrumentation enabled for LangChain/LangGraph")

    except ImportError:
        logger.warning(
            "mlflow.langchain not available. "
            "Auto-instrumentation requires MLFlow 3.0+. "
            "Current version: %s", mlflow.__version__
        )
        logger.info("Falling back to manual instrumentation")
    except Exception as e:
        logger.warning(f"Failed to enable auto-instrumentation: {e}")
        logger.info("Continuing with manual instrumentation")
```

#### Step 2.3: Add Decorator Wrapper (1 hour)

**File**: `src/configurable_agents/observability/mlflow_tracker.py`

**Add helper method**:
```python
def trace_function(self, func: Callable, name: Optional[str] = None, span_type: Optional[str] = None):
    """
    Wrap a function with MLFlow tracing.

    Args:
        func: Function to trace
        name: Trace name (default: function name)
        span_type: Span type (CHAIN, AGENT, TOOL, etc.)

    Returns:
        Traced function

    Example:
        >>> @tracker.trace_function
        ... def my_function(x):
        ...     return x * 2
    """
    if not self.enabled or not MLFLOW_AVAILABLE:
        return func

    try:
        from mlflow.entities import SpanType

        trace_name = name or func.__name__
        trace_type = span_type or SpanType.CHAIN

        return mlflow.trace(name=trace_name, span_type=trace_type)(func)

    except (ImportError, AttributeError):
        logger.debug("MLFlow tracing not available, returning unwrapped function")
        return func
```

#### Step 2.4: Update Executor (2 hours)

**File**: `src/configurable_agents/runtime/executor.py`

**Option A: Keep Manual Tracking** (Phase 2, backward compatible):
```python
def run_workflow_from_config(
    config: WorkflowConfig,
    inputs: Dict[str, Any],
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run workflow with optional auto-instrumentation."""

    # Initialize tracker
    tracker = _get_mlflow_tracker(config)

    # If autolog enabled, entire workflow automatically traced
    # If not, use manual tracking (current behavior)

    with tracker.track_workflow(inputs=inputs):  # Still works!
        # Build and execute graph
        result = graph.invoke(initial_state)

    return result
```

**Option B: Decorator Pattern** (Future, v0.3):
```python
# Future: Wrap entire function
@mlflow.trace(name="run_workflow", span_type=SpanType.CHAIN)
def run_workflow_from_config(...):
    # Automatically traced at top level
    pass
```

#### Step 2.5: Benchmark Performance (1 hour)

**Create benchmark script**:
```python
# scripts/benchmark_mlflow.py
import time
from configurable_agents.runtime import run_workflow

def benchmark_manual():
    """Benchmark with manual tracking."""
    start = time.time()
    run_workflow("test_config.yaml", {"topic": "Test"})
    return time.time() - start

def benchmark_autolog():
    """Benchmark with auto-instrumentation."""
    # Enable autolog in config
    start = time.time()
    run_workflow("test_config.yaml", {"topic": "Test"})
    return time.time() - start

# Run benchmarks
manual_time = benchmark_manual()
autolog_time = benchmark_autolog()

print(f"Manual: {manual_time:.2f}s")
print(f"Autolog: {autolog_time:.2f}s")
print(f"Overhead: {((autolog_time / manual_time) - 1) * 100:.1f}%")
```

**Expected**: < 5% overhead

---

### Phase 3: Documentation (0.5 days)

**Goal**: Update all documentation

#### Step 3.1: Update OBSERVABILITY.md (2 hours)

**File**: `docs/OBSERVABILITY.md`

**Add sections**:

1. **MLFlow 3.9 Features** (new section after introduction)
2. **Auto-Instrumentation Guide** (new section)
3. **Migration from 2.9 to 3.9** (new section)
4. **SQLite vs File-Based Backends** (new section)
5. **Troubleshooting** (update with new patterns)

**Content to add** (abbreviated):
```markdown
## MLFlow 3.9 Features

This project uses MLFlow 3.9+ with modern GenAI/agent tracing capabilities.

### What's New in MLFlow 3.9

- **Auto-Instrumentation**: Automatic tracing for LangChain/LangGraph
- **GenAI Dashboard**: Agent-specific metrics and tool call visualization
- **SQLite Backend**: Faster default backend (replaces file-based)
- **Graceful Fallback**: Auto-fallback to SQLite if server unreachable
- **Span/Trace Model**: Better visualization for multi-step agents

### Auto-Instrumentation

Enable automatic tracing with one configuration option:

\`\`\`yaml
observability:
  mlflow:
    enabled: true
    autolog_enabled: true  # Enable auto-instrumentation
    tracking_uri: "sqlite:///mlflow.db"
\`\`\`

With `autolog_enabled: true`, all LangGraph operations are automatically traced without manual instrumentation.

### Migration from MLFlow 2.9

**No Action Required** - your existing configs work:

\`\`\`yaml
# Existing config (still works)
observability:
  mlflow:
    enabled: true
    tracking_uri: "file://./mlruns"
\`\`\`

**Recommended Upgrade**:
\`\`\`yaml
# Modern config (better performance)
observability:
  mlflow:
    enabled: true
    tracking_uri: "sqlite:///mlflow.db"  # Faster
    autolog_enabled: true  # Auto-trace LangGraph
\`\`\`
```

#### Step 3.2: Update CONFIG_REFERENCE.md (1 hour)

**File**: `docs/CONFIG_REFERENCE.md`

**Update MLFlow section**:
```markdown
### MLFlow Configuration

\`\`\`yaml
observability:
  mlflow:
    enabled: true
    tracking_uri: "sqlite:///mlflow.db"  # NEW DEFAULT (was file://./mlruns)
    experiment_name: "my_experiment"
    autolog_enabled: true  # NEW: Auto-instrumentation (MLFlow 3.9+)
    log_prompts: true
    log_artifacts: true
\`\`\`

**Fields**:

- `enabled` (bool): Enable MLFlow tracking
- `tracking_uri` (str): Backend URI
  - `"sqlite:///mlflow.db"` - SQLite (default, fast, local)
  - `"file://./mlruns"` - File-based (legacy, compatible)
  - `"http://localhost:5000"` - Remote server
- `autolog_enabled` (bool): Enable auto-instrumentation (MLFlow 3.9+)
  - `true`: Automatic tracing for LangGraph (recommended)
  - `false`: Manual tracking (backward compatible)
```

#### Step 3.3: Create Migration Guide (1 hour)

**File**: `docs/MLFLOW_MIGRATION.md`

**Content**: Complete migration guide for users upgrading from 2.9 to 3.9

---

### Phase 4: Testing (0.5 days)

**Goal**: Comprehensive testing

#### Step 4.1: Unit Tests (2 hours)

**Tests to add** (`tests/observability/test_mlflow_tracker.py`):

1. `test_autolog_initialization` - Autolog enabled correctly
2. `test_autolog_disabled_by_default` - Backward compatibility
3. `test_autolog_fallback_if_not_available` - MLFlow 2.x compatibility
4. `test_sqlite_backend_default` - New default works
5. `test_file_backend_still_works` - Backward compatibility
6. `test_server_fallback_to_sqlite` - Graceful degradation
7. `test_trace_decorator_wrapper` - Decorator functionality
8. `test_autolog_with_langchain` - Mock LangChain autolog

#### Step 4.2: Integration Tests (1 hour)

**Tests to add** (`tests/integration/test_mlflow_39_integration.py`):

1. `test_workflow_with_autolog` - Real MLFlow 3.9 autolog
2. `test_sqlite_backend_performance` - SQLite faster than file
3. `test_server_unreachable_fallback` - Fallback in real scenario
4. `test_genai_dashboard_metrics` - Verify new metrics appear

#### Step 4.3: Backward Compatibility Tests (30 minutes)

**Tests to add**:

1. `test_mlflow_29_configs_still_work` - Old configs valid
2. `test_file_based_backend_migration` - Upgrade path
3. `test_no_autolog_field_defaults_false` - Missing field handling

---

## Code Changes Detailed

### Critical Files

**File 1: `pyproject.toml`**
```diff
[project]
dependencies = [
-    "mlflow>=2.9.0",
+    "mlflow>=3.9.0",
]
```

**File 2: `src/configurable_agents/config/schema.py`**
```diff
class ObservabilityMLFlowConfig(BaseModel):
    enabled: bool = Field(False, ...)
    tracking_uri: str = Field(
-        "file://./mlruns",
+        "sqlite:///mlflow.db",
        ...
    )
+    autolog_enabled: bool = Field(
+        False,
+        description="Enable auto-instrumentation (MLFlow 3.9+)"
+    )
```

**File 3: `src/configurable_agents/observability/mlflow_tracker.py`**

Major changes:
1. Add `_get_fallback_uri()` method
2. Update `_initialize_mlflow()` with fallback logic
3. Add `_enable_autolog()` method
4. Add `trace_function()` decorator wrapper
5. Update `__init__` to call `_enable_autolog()`

Estimated: +100 lines, ~10 lines modified

**File 4: `tests/observability/test_mlflow_tracker.py`**

Add tests:
1. Fallback scenarios (3 tests)
2. Autolog initialization (4 tests)
3. Backward compatibility (3 tests)

Estimated: +50 lines

---

## Testing Strategy

### Test Pyramid

**Unit Tests** (Fast, No Cost):
- Mock MLFlow 3.9 APIs
- Test fallback logic
- Test autolog initialization
- Test backward compatibility

**Integration Tests** (Slow, ~$0.50):
- Real MLFlow 3.9 tracking
- SQLite backend performance
- GenAI dashboard verification
- Server fallback scenarios

**Manual Testing** (User Acceptance):
- Run existing examples with 3.9
- Verify GenAI dashboard works
- Test migration from 2.9 config
- Benchmark performance

### Test Coverage Goals

- Unit tests: > 85% coverage
- Integration tests: Critical paths only
- Manual tests: All user-facing features

---

## Rollback Plan

### If Phase 1 Fails

**Symptom**: Tests fail with MLFlow 3.9

**Rollback**:
```bash
# Revert pyproject.toml
git checkout HEAD -- pyproject.toml
pip install -e .
```

### If Phase 2 Fails

**Symptom**: Autolog causes errors

**Mitigation**: Set `autolog_enabled: false` (default)

**Rollback**: No rollback needed, feature is optional

### If Critical Issues Found

**Full Rollback**:
```bash
# Revert all changes
git reset --hard <commit-before-upgrade>
pip install -e .
```

---

## Success Criteria

### Phase 1 Success

- [ ] MLFlow 3.9 installed
- [ ] All existing tests pass
- [ ] Fallback to SQLite works
- [ ] Server unreachable handled gracefully
- [ ] No performance regression

### Phase 2 Success

- [ ] Autolog initialization works
- [ ] LangGraph automatically traced
- [ ] Manual tracking still works (backward compatible)
- [ ] Performance overhead < 5%
- [ ] Config option controls behavior

### Phase 3 Success

- [ ] OBSERVABILITY.md updated with 3.9 features
- [ ] CONFIG_REFERENCE.md includes autolog_enabled
- [ ] Migration guide created
- [ ] Examples updated

### Phase 4 Success

- [ ] All unit tests pass (>85% coverage)
- [ ] Integration tests pass
- [ ] Backward compatibility verified
- [ ] Performance benchmarks acceptable

### Overall Success

- [ ] All phases complete
- [ ] Documentation updated
- [ ] Zero breaking changes for existing users
- [ ] MLFlow 3.9 features accessible
- [ ] Implementation log created
- [ ] ADR-018 updated with results

---

## Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: Safe Upgrade | 1 day | Day 1 | Day 1 |
| Phase 2: Auto-Instrumentation | 1 day | Day 2 | Day 2 |
| Phase 3: Documentation | 0.5 days | Day 3 AM | Day 3 PM |
| Phase 4: Testing | 0.5 days | Day 3 PM | Day 3 PM |
| **Total** | **3 days** | **Day 1** | **Day 3** |

---

## References

- [ADR-018: MLFlow 3.9 Upgrade](docs/adr/ADR-018-mlflow-39-upgrade-genai-tracing.md)
- [MLFlow 3.9 Release Notes](https://mlflow.org/releases)
- [MLFlow Tracing Documentation](https://mlflow.org/docs/latest/genai/tracing/)
- [MLFlow Auto-Instrumentation](https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/automatic/)

---

**Status**: Ready for implementation
**Owner**: Development Team
**Reviewers**: Technical Lead
**Approval**: Pending

---

*This guide will be updated as implementation progresses.*
