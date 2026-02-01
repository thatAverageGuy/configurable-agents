# ADR-018: MLFlow 3.9 Upgrade for GenAI/Agent Tracing

**Status**: Proposed
**Date**: 2026-02-02
**Deciders**: Technical Lead
**Related**: ADR-011 (MLFlow Observability Foundation), T-018-021 (MLFlow Implementation)
**Supersedes**: None
**Implements**: T-028 (MLFlow 3.9 Upgrade)

---

## Context

Our current MLFlow integration (T-018-021) was built against MLFlow 2.9+ using traditional logging patterns. Since implementation, MLFlow has evolved significantly with version 3.0+ introducing dedicated GenAI/agent features that better align with our use case.

### Current State (MLFlow 2.9+ Pattern)

**Implementation** (`src/configurable_agents/observability/mlflow_tracker.py`):
```python
class MLFlowTracker:
    def __init__(self, config, workflow_config):
        # Manual setup
        mlflow.set_tracking_uri(config.tracking_uri)
        mlflow.set_experiment(config.experiment_name)

    @contextmanager
    def track_workflow(self, inputs):
        # Manual run management
        mlflow.start_run(run_name=...)
        mlflow.log_params(inputs)
        yield
        mlflow.log_metrics(...)
        mlflow.end_run()

    @contextmanager
    def track_node(self, node_id, model):
        # Manual nested run creation
        mlflow.start_run(run_name=node_id, nested=True)
        yield
        mlflow.log_metrics(...)
        mlflow.end_run()
```

**Characteristics**:
- ✅ Works reliably
- ✅ Full control over what's logged
- ❌ Manual run management (start/end, nested runs)
- ❌ No automatic instrumentation
- ❌ Verbose boilerplate code
- ❌ File-based backend default (`file://./mlruns`)
- ❌ No span/trace model (uses nested runs)
- ❌ Limited integration with GenAI libraries

### MLFlow 3.0+ Capabilities

**Released**: MLFlow 3.0 (June 2024), 3.9.0 (January 29, 2026)

**Major GenAI Features**:

1. **Tracing API** (MLFlow 3.0+):
   - `@mlflow.trace` decorator for automatic tracing
   - `mlflow.start_span()` for manual span creation
   - Span/trace model (not nested runs)
   - Distributed tracing support

2. **Auto-Instrumentation** (MLFlow 3.0+):
   - `mlflow.langchain.autolog()` - Automatic LangChain tracing
   - Support for 15+ frameworks (OpenAI, Anthropic, LlamaIndex, DSPy, etc.)
   - Zero-code instrumentation for supported libraries

3. **GenAI Dashboard** (MLFlow 3.9+):
   - Trace Overview tab with performance/quality metrics
   - Tool call summaries for agent workflows
   - Pre-built statistics for LLM applications

4. **Online Monitoring** (MLFlow 3.9+):
   - LLM judges auto-run on traces
   - Custom judge builder UI
   - Quality assessment automation

5. **Backend Changes** (MLFlow 3.7+):
   - Default changed from `file://./mlruns` to `sqlite:///mlflow.db`
   - Better performance for queries and concurrent writes
   - Backward compatibility: auto-detects existing `./mlruns`

6. **Agent-Specific Features** (MLFlow 3.9+):
   - Streaming response tracing (`ResponsesAgent.predict_stream`)
   - Multi-agent workflow support
   - Tool call tracking and visualization

### Problem Statement

**Gap Analysis**:

| Feature | Current (2.9+) | MLFlow 3.9 | Impact |
|---------|----------------|------------|--------|
| Auto-instrumentation | ❌ Manual | ✅ `autolog()` | Less boilerplate |
| Tracing model | Nested runs | Spans/traces | Better for agents |
| Default backend | File-based | SQLite | Better performance |
| GenAI dashboard | ❌ Generic | ✅ Specialized | Better UX |
| LangChain integration | ❌ Manual | ✅ Auto | Easier setup |
| Distributed tracing | ❌ No | ✅ Yes | Multi-service support |
| Agent patterns | ❌ Custom | ✅ Built-in | Best practices |

**Why Upgrade Now**:
1. **Alignment**: We're building agent workflows - MLFlow 3.9 is designed for this
2. **Best Practices**: Current patterns are pre-GenAI era, 3.9 is modern standard
3. **Maintenance**: Less custom code to maintain with auto-instrumentation
4. **Features**: GenAI dashboard, LLM judges, streaming support
5. **Performance**: SQLite backend faster than file-based
6. **Community**: MLFlow 3.x is the focus for new features/docs

### Current Pain Points

**From BUG-004** (MLFlow Blocking Without Server):
- MLFlow 2.9 patterns require manual connection handling
- No built-in fallback mechanisms
- Long timeouts for unreachable servers
- ✅ Fixed: Added pre-check and timeout configuration

**From User Feedback**:
- File-based backend slow for multiple runs
- No visibility into LangChain internals (we use LangGraph, similar)
- Manual span creation verbose

---

## Decision

**We will upgrade to MLFlow 3.9 and adopt modern GenAI tracing patterns.**

### Core Changes

1. **Dependency Upgrade**:
   ```toml
   # Before
   mlflow>=2.9.0

   # After
   mlflow>=3.9.0
   ```

2. **Tracing Model Migration**:
   ```python
   # Before: Nested runs (manual)
   with tracker.track_workflow(inputs):
       with tracker.track_node(node_id, model):
           result = execute_node()

   # After: Spans/traces (automatic)
   @mlflow.trace(name="workflow", span_type=SpanType.CHAIN)
   def run_workflow(config, inputs):
       for node in workflow.nodes:
           result = execute_node(node)  # Auto-traced if LangChain
       return result
   ```

3. **Auto-Instrumentation**:
   ```python
   # Enable automatic tracing for LangChain (LangGraph compatible)
   import mlflow
   mlflow.langchain.autolog()

   # All LangGraph calls automatically traced
   graph.invoke(state)  # ← Automatically creates spans!
   ```

4. **Backend Migration**:
   ```python
   # Graceful fallback for unreachable servers
   def _initialize_mlflow(self):
       try:
           # Pre-check server accessibility
           if not self._check_server_accessible(timeout=3):
               logger.warning("Server unreachable, falling back to SQLite")
               mlflow.set_tracking_uri("sqlite:///mlflow.db")
           else:
               mlflow.set_tracking_uri(self.config.tracking_uri)
       except Exception as e:
           logger.warning(f"MLFlow init failed: {e}, using local SQLite")
           mlflow.set_tracking_uri("sqlite:///mlflow.db")
   ```

### Migration Strategy

**Phase 1: Backward Compatible Upgrade** (Safe)
- Upgrade dependency to `mlflow>=3.9.0`
- Keep existing `MLFlowTracker` API unchanged
- Add auto-instrumentation as **optional** enhancement
- Default backend: Keep `file://./mlruns` for existing users
- SQLite fallback for new users or server failures

**Phase 2: Modern API Adoption** (Recommended)
- Introduce `@mlflow.trace` decorator wrapper
- Enable `mlflow.langchain.autolog()` for LangGraph
- Deprecate manual `track_node()` calls (still supported)
- Add configuration option: `use_autolog: true` (default: false for v0.2)

**Phase 3: Full Migration** (Future, v0.3+)
- Make auto-instrumentation default
- Remove legacy `track_node()` manual tracking
- Switch default backend to SQLite
- Migrate examples and docs fully to 3.9 patterns

---

## Consequences

### Positive

1. **Less Code to Maintain**:
   - Auto-instrumentation reduces `mlflow_tracker.py` complexity
   - No manual span creation for LangChain/LangGraph calls
   - Built-in error handling and retries

2. **Better User Experience**:
   - GenAI dashboard shows agent-specific metrics
   - Tool call visualization out-of-the-box
   - Quality metrics with LLM judges

3. **Performance Improvements**:
   - SQLite backend faster for queries
   - Better concurrent write handling
   - Smaller disk footprint

4. **Future-Proof**:
   - Aligned with MLFlow's GenAI direction
   - Access to new features (streaming, distributed tracing)
   - Community support focused on 3.x

5. **Better Integration**:
   - LangGraph automatically traced
   - No custom instrumentation needed
   - Consistent with MLFlow best practices

### Negative

1. **Breaking Changes** (Mitigated):
   - Default backend change (3.7+): File → SQLite
   - **Mitigation**: Auto-detect existing `./mlruns`, graceful fallback

2. **Migration Effort** (Moderate):
   - Update `mlflow_tracker.py` (~200 lines)
   - Update tests (mock new APIs)
   - Update documentation and examples
   - **Estimated**: 1-2 days

3. **Learning Curve** (Low):
   - New APIs (`@mlflow.trace`, `autolog()`)
   - Span/trace mental model vs nested runs
   - **Mitigation**: Comprehensive docs and examples

4. **Version Compatibility** (Minor):
   - Users with MLFlow 2.x configs need migration
   - **Mitigation**: Backward-compatible Phase 1 approach

5. **Testing Complexity** (Minor):
   - Need to mock new auto-instrumentation
   - **Mitigation**: MLFlow provides test utilities

### Neutral

1. **File-based Backend Still Supported**:
   - Users can still use `file://./mlruns`
   - No forced migration to SQLite

2. **Optional Auto-Instrumentation**:
   - Can still use manual tracking if preferred
   - Gradual adoption possible

3. **Existing Data Compatible**:
   - MLFlow 3.9 reads MLFlow 2.x data
   - No data migration needed

---

## Implementation Plan

### Prerequisites

- [x] All current observability features working (T-018-021 complete)
- [x] Current tests passing
- [x] Bug fixes complete (BUG-001 through BUG-004)

### Phase 1: Safe Upgrade (T-028 Part 1) - 1 day

**Goal**: Upgrade dependency without breaking changes

**Tasks**:
1. Update `pyproject.toml`: `mlflow>=2.9.0` → `mlflow>=3.9.0`
2. Add fallback logic to `_initialize_mlflow()`:
   - If server unreachable → fallback to `sqlite:///mlflow.db`
   - Log clear warning message
   - Continue workflow execution
3. Update tests to work with MLFlow 3.9
4. Run full test suite, verify no breakage
5. Update documentation: note MLFlow 3.9 compatibility

**Success Criteria**:
- All existing tests pass with MLFlow 3.9
- Backward compatible (no API changes)
- Server fallback works correctly
- Documentation updated

### Phase 2: Auto-Instrumentation (T-028 Part 2) - 1 day

**Goal**: Add optional auto-instrumentation

**Tasks**:
1. Add `mlflow.langchain.autolog()` initialization
2. Create wrapper for `@mlflow.trace` decorator
3. Add config option: `autolog_enabled: bool` (default: false)
4. Update examples with auto-instrumentation
5. Benchmark: manual vs auto-instrumentation
6. Document when to use each approach

**Implementation**:
```python
class MLFlowTracker:
    def __init__(self, config, workflow_config):
        self.config = config
        self.workflow_config = workflow_config

        # Initialize tracking
        self._initialize_mlflow()

        # Enable auto-instrumentation if configured
        if config.autolog_enabled:
            import mlflow.langchain
            mlflow.langchain.autolog()
            logger.info("MLFlow auto-instrumentation enabled")

    def _initialize_mlflow(self):
        """Initialize with fallback to SQLite."""
        try:
            if not self._check_server_accessible(timeout=3):
                logger.warning("MLFlow server unreachable, using SQLite")
                mlflow.set_tracking_uri("sqlite:///mlflow.db")
            else:
                mlflow.set_tracking_uri(self.config.tracking_uri)
        except Exception as e:
            logger.warning(f"MLFlow init failed: {e}, using SQLite fallback")
            mlflow.set_tracking_uri("sqlite:///mlflow.db")

        mlflow.set_experiment(self.config.experiment_name)
```

**Success Criteria**:
- Auto-instrumentation works with LangGraph
- Manual tracking still works (backward compatible)
- Config option controls behavior
- Benchmarks show performance (no regression)

### Phase 3: Documentation & Examples (T-028 Part 3) - 0.5 days

**Goal**: Update all documentation

**Tasks**:
1. Update `OBSERVABILITY.md`:
   - Add section on MLFlow 3.9 features
   - Document auto-instrumentation
   - Update examples to use new patterns
   - Add migration guide from 2.9 to 3.9
2. Update `CONFIG_REFERENCE.md`:
   - Add `autolog_enabled` option
   - Document tracking URI fallback behavior
3. Update examples:
   - `article_writer_mlflow.yaml`: Add autolog example
   - Create `article_writer_sqlite.yaml`: SQLite backend example
4. Create migration guide: `docs/MLFLOW_MIGRATION.md`

**Success Criteria**:
- All docs reference MLFlow 3.9
- Examples use modern patterns
- Migration guide clear and actionable

### Phase 4: Testing & Validation (T-028 Part 4) - 0.5 days

**Goal**: Comprehensive testing

**Tasks**:
1. Unit tests: Mock `mlflow.langchain.autolog()`
2. Integration tests: Real MLFlow 3.9 tracking
3. Fallback tests: Server unreachable scenarios
4. Performance tests: Manual vs auto-instrumentation
5. Backward compatibility tests: File-based backend
6. Migration tests: Upgrading existing data

**Success Criteria**:
- All tests pass with MLFlow 3.9
- Fallback logic tested and working
- Performance acceptable (no regression)
- Backward compatibility verified

---

## Alternative Approaches Considered

### Option 1: Stay on MLFlow 2.9

**Approach**: Don't upgrade, keep current implementation

**Pros**:
- ✅ No migration effort
- ✅ Known stable patterns
- ✅ Current implementation works

**Cons**:
- ❌ Missing GenAI-specific features
- ❌ Not aligned with community direction
- ❌ Manual instrumentation verbose
- ❌ File-based backend limitations
- ❌ No access to new features (3.9+)

**Decision**: ❌ **Rejected** - Technical debt, misses GenAI improvements

### Option 2: Gradual Adoption (Chosen Approach)

**Approach**: Phase 1 (safe upgrade) → Phase 2 (optional auto-instrumentation) → Phase 3 (full migration in v0.3)

**Pros**:
- ✅ Backward compatible
- ✅ Low risk (can rollback)
- ✅ User choice (manual vs auto)
- ✅ Gradual learning curve

**Cons**:
- ⚠️ Temporary dual patterns (manual + auto)
- ⚠️ Migration effort spread over time

**Decision**: ✅ **Accepted** - Balanced approach, minimizes risk

### Option 3: Big Bang Migration

**Approach**: Immediately switch to auto-instrumentation only, deprecate manual tracking

**Pros**:
- ✅ Clean codebase (one pattern)
- ✅ Fastest to full modernization
- ✅ Less maintenance

**Cons**:
- ❌ High risk (breaking changes)
- ❌ Users must migrate immediately
- ❌ No fallback if auto-instrumentation issues

**Decision**: ❌ **Rejected** - Too risky, breaks existing users

---

## Migration Guide (User-Facing)

### For Existing Users (MLFlow 2.9+ → 3.9)

**No Action Required** - Your existing configs will continue to work:

```yaml
# Existing config (still works)
observability:
  mlflow:
    enabled: true
    tracking_uri: "file://./mlruns"
    experiment_name: "my_experiment"
```

**Optional Enhancements**:

1. **Switch to SQLite** (better performance):
   ```yaml
   tracking_uri: "sqlite:///mlflow.db"
   ```

2. **Enable Auto-Instrumentation** (less code):
   ```yaml
   observability:
     mlflow:
       enabled: true
       tracking_uri: "sqlite:///mlflow.db"
       autolog_enabled: true  # ← New feature
   ```

3. **Graceful Fallback** (automatic):
   - If `tracking_uri: "http://..."` unreachable → auto-fallback to SQLite
   - Warning logged, execution continues

### For New Users

**Recommended Configuration**:

```yaml
observability:
  mlflow:
    enabled: true
    tracking_uri: "sqlite:///mlflow.db"  # Fast, reliable
    experiment_name: "my_agent_workflow"
    autolog_enabled: true  # Auto-trace LangGraph
```

**View Results**:
```bash
# Start MLFlow UI
mlflow ui --backend-store-uri sqlite:///mlflow.db

# Open browser: http://localhost:5000
# See GenAI dashboard with agent metrics
```

---

## References

- [MLFlow 3.0 Release Blog](https://www.databricks.com/blog/mlflow-30-unified-ai-experimentation-observability-and-governance)
- [MLFlow 3.9.0 Release Notes](https://mlflow.org/releases)
- [MLFlow Tracing Documentation](https://mlflow.org/docs/latest/genai/tracing/)
- [MLFlow Auto-Instrumentation Guide](https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/automatic/)
- [Tracing LangGraph with MLFlow](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/langgraph/)
- [MLFlow 3 GenAI Features](https://mlflow.org/docs/3.6.0/genai/mlflow-3/)
- [Introducing MLFlow Tracing Blog](https://mlflow.github.io/mlflow-website/blog/mlflow-tracing/)

---

## Timeline

- **Proposal**: 2026-02-02
- **Phase 1 (Safe Upgrade)**: 2026-02-03 (1 day)
- **Phase 2 (Auto-Instrumentation)**: 2026-02-04 (1 day)
- **Phase 3 (Documentation)**: 2026-02-05 (0.5 days)
- **Phase 4 (Testing)**: 2026-02-05 (0.5 days)
- **Completion**: 2026-02-05 (3 days total)

---

## Success Metrics

**Technical**:
- All tests pass with MLFlow 3.9
- Server fallback works reliably
- Auto-instrumentation reduces code by ~30%
- Performance: SQLite backend ≥ file-based

**User Experience**:
- Zero breaking changes for existing users
- Clear migration path documented
- GenAI dashboard provides value (metrics, tool calls)
- Setup time reduced (autolog vs manual)

**Maintenance**:
- Reduced custom tracking code
- Aligned with MLFlow best practices
- Future MLFlow upgrades easier

---

**Status**: Ready for implementation
**Next Step**: Create T-028 in TASKS.md and begin Phase 1

---

*This ADR will be updated as implementation progresses.*
