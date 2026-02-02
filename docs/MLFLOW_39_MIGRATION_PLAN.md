# MLflow 3.9 Comprehensive Migration Plan

> **Purpose**: Detailed migration plan from MLflow 2.9+ patterns to MLflow 3.9 with GenAI-specific features
>
> **Created**: 2026-02-02 (Phase 2 of T-028: MLFlow 3.9 Comprehensive Migration)
>
> **Status**: Planning Complete - Ready for Phase 3 (Enhanced Observability Design)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Implementation Analysis](#2-current-implementation-analysis)
3. [Feature Mapping](#3-feature-mapping)
4. [Proposed Architecture](#4-proposed-architecture)
5. [Migration Strategy](#5-migration-strategy)
6. [Breaking Changes & Compatibility](#6-breaking-changes--compatibility)
7. [Implementation Phases](#7-implementation-phases)
8. [Testing Strategy](#8-testing-strategy)
9. [Rollback Plan](#9-rollback-plan)
10. [Success Criteria](#10-success-criteria)

---

## 1. Executive Summary

### Migration Goals

**Primary Objectives:**
1. Replace manual run management with MLflow 3.9 tracing API
2. Leverage `mlflow.langchain.autolog()` for automatic LangGraph instrumentation
3. Adopt GenAI dashboard for enhanced observability
4. Simplify codebase by removing boilerplate
5. Enable advanced features (LLM judges, prompt versioning)

### Key Benefits

| Aspect | Current | After Migration | Impact |
|--------|---------|-----------------|--------|
| Code complexity | ~484 lines manual tracking | ~200 lines with autolog | -60% code |
| Instrumentation | Manual context managers | Automatic decorator-based | Less maintenance |
| Token tracking | Manual extraction | Automatic | Zero overhead |
| Dashboard | Basic metrics | GenAI-specific insights | Better UX |
| Backend | File-based (`./mlruns`) | SQLite (`mlflow.db`) | Better performance |
| Integration | Custom callbacks | Native LangGraph support | Future-proof |

### Risk Assessment

**Low Risk:**
- MLflow 3.9 stable and production-ready
- Backward compatible with SQLite migration (auto-detects existing `./mlruns`)
- Can keep current config schema mostly intact
- Gradual rollout possible (feature flag)

**Mitigation:**
- Comprehensive testing (unit + integration)
- Rollback plan (revert to current implementation)
- Feature flag for gradual rollout

---

## 2. Current Implementation Analysis

### 2.1 File Structure

```
src/configurable_agents/observability/
├── mlflow_tracker.py          # 484 lines - Main tracker class
├── cost_estimator.py           # Cost calculation (keep as-is)
└── __init__.py                 # Exports

Key integration points:
├── src/configurable_agents/core/node_executor.py
│   └── execute_node() - Uses tracker.track_node() + log_node_metrics()
├── src/configurable_agents/runtime/executor.py
│   └── run_workflow() - Uses tracker.track_workflow() + finalize_workflow()
└── src/configurable_agents/config/schema.py
    └── ObservabilityMLFlowConfig - Config schema
```

### 2.2 Current MLFlowTracker Class

**File:** `src/configurable_agents/observability/mlflow_tracker.py`

#### Core Responsibilities

1. **Initialization & Setup** (lines 54-202)
   - MLflow availability check
   - Tracking URI configuration
   - Experiment creation
   - Server accessibility check (3s timeout)
   - Graceful degradation when unavailable

2. **Workflow-Level Tracking** (lines 204-259)
   - Context manager: `track_workflow(inputs)`
   - Logs workflow parameters (name, version, node count)
   - Logs inputs/outputs as artifacts
   - Calculates total duration, tokens, cost
   - Handles errors and status logging

3. **Node-Level Tracking** (lines 326-369)
   - Context manager: `track_node(node_id, model, tools, node_config)`
   - Creates nested MLflow runs
   - Logs node parameters
   - Supports per-node observability overrides

4. **Metrics & Artifacts Logging** (lines 371-436)
   - `log_node_metrics()` - Token counts, cost, duration, prompts, responses
   - Manual cost estimation via `CostEstimator`
   - Configurable artifact levels (minimal, standard, full)
   - Prompt/response logging with UI preview + downloadable files

5. **Configuration Management** (lines 87-131)
   - Per-node observability overrides
   - Artifact level checking
   - Prompt logging toggles

#### Key Patterns

**Manual Run Management:**
```python
mlflow.start_run(run_name=run_name)
try:
    # Log params/metrics
    mlflow.log_param("workflow_name", name)
    mlflow.log_metric("duration_seconds", duration)
    yield
finally:
    mlflow.end_run()
```

**Nested Runs for Nodes:**
```python
with mlflow.start_run(run_name=f"node_{node_id}", nested=True):
    mlflow.log_param("node_id", node_id)
    mlflow.log_metric("input_tokens", input_tokens)
    # ...
```

**Manual Token Tracking:**
```python
self._total_input_tokens += input_tokens
self._total_output_tokens += output_tokens
cost = self.cost_estimator.estimate_cost(model, input_tokens, output_tokens)
self._total_cost += cost
```

### 2.3 Integration Points

#### node_executor.py (lines 250-292)

```python
def execute_node(..., tracker: Optional["MLFlowTracker"] = None):
    # ...
    tracker_context = (
        tracker.track_node(
            node_id=node_id,
            model=model_name,
            tools=tool_names,
            node_config=node_config,
        )
        if tracker
        else None
    )

    try:
        if tracker_context:
            tracker_context.__enter__()

        result, usage = call_llm_structured(...)

        if tracker:
            tracker.log_node_metrics(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                model=model_name,
                prompt=resolved_prompt,
                response=response_text,
            )
    finally:
        if tracker_context:
            tracker_context.__exit__(...)
```

**Key Observations:**
- Manual context manager entry/exit
- Tracker passed as optional parameter
- Usage info extracted from `call_llm_structured()` return value

#### executor.py (workflow level)

```python
def run_workflow(...):
    tracker = MLFlowTracker(mlflow_config, workflow_config)

    with tracker.track_workflow(inputs=initial_dict):
        # Execute graph
        final_state = graph.invoke(initial)

        # Finalize tracking
        tracker.finalize_workflow(final_state_dict, status="success")
```

### 2.4 Configuration Schema

**File:** `src/configurable_agents/config/schema.py` (lines 256-306)

```python
class ObservabilityMLFlowConfig(BaseModel):
    enabled: bool = False
    tracking_uri: str = "file://./mlruns"
    experiment_name: str = "configurable_agents"
    run_name: Optional[str] = None

    # Observability controls (workflow-level defaults)
    log_prompts: bool = True
    log_artifacts: bool = True
    artifact_level: str = "standard"  # minimal, standard, full

    # Future (v0.2+)
    retention_days: Optional[int] = None
    redact_pii: bool = False
```

**Node-level overrides** (lines 159-165):
```python
class NodeConfig(BaseModel):
    # ...
    log_prompts: Optional[bool] = None  # Override workflow default
    log_artifacts: Optional[bool] = None  # Override workflow default
```

### 2.5 Current Strengths

✅ **Robust error handling** - Graceful degradation when MLflow unavailable
✅ **Flexible configuration** - Workflow + node-level overrides
✅ **Artifact levels** - Control observability verbosity (minimal/standard/full)
✅ **Server pre-check** - 3s timeout prevents 30-60s hangs (BUG-004 fix)
✅ **Cost tracking** - Comprehensive token and cost estimation
✅ **Comprehensive tests** - 67 CLI tests passing, dedicated MLflow unit/integration tests

### 2.6 Current Limitations

❌ **Manual boilerplate** - 484 lines of manual run/metric management
❌ **Nested runs** - Not ideal for agent workflows (spans/traces better)
❌ **No auto-instrumentation** - Must manually call tracking methods
❌ **Manual token extraction** - Requires parsing LLM responses
❌ **File backend** - Slower than SQLite for queries
❌ **Limited GenAI features** - No judges, no prompt versioning, no tool tracking
❌ **Context manager overhead** - Manual entry/exit, error-prone

---

## 3. Feature Mapping

### 3.1 Current Implementation → MLflow 3.9 Equivalents

| Current Feature | Implementation | MLflow 3.9 Equivalent | Benefit |
|----------------|----------------|-----------------------|---------|
| `track_workflow()` | Manual `start_run()` / `end_run()` | `@mlflow.trace` on workflow function | Automatic |
| `track_node()` | Nested `start_run()` with manual params | Auto-captured via `mlflow.langchain.autolog()` | Zero code |
| `log_node_metrics()` | Manual `log_metric()` calls | Automatic span attributes | Zero overhead |
| Token counting | Manual extraction from usage | `mlflow.chat.tokenUsage` (automatic) | Accurate |
| Cost tracking | `CostEstimator` class | Keep + enhance with trace-level view | Enhanced |
| Prompt/response logging | Manual `log_text()` / tags | Automatic span inputs/outputs | Better UX |
| Artifact levels | Custom logic | Keep via config, apply to artifacts | Preserve flexibility |
| Server pre-check | Custom socket check | Keep for backward compat | Preserve safety |
| Graceful degradation | Custom `enabled` flag | Keep via feature flag | Preserve robustness |

### 3.2 New Capabilities from MLflow 3.9

| Feature | Description | Value for Us |
|---------|-------------|--------------|
| **GenAI Dashboard** | Trace Overview tab with agent metrics | Better visibility into workflow performance |
| **Auto-instrumentation** | `mlflow.langchain.autolog()` | -60% code, automatic LangGraph tracing |
| **Tool call tracking** | Automatic tool invocation logging | See which tools used, when, and results |
| **LLM judges** | Automatic quality assessment | Post-deployment quality monitoring |
| **Prompt Registry** | Version control for prompts | Track prompt evolution alongside configs |
| **Async trace logging** | Background trace upload | Zero-latency production impact |
| **SQLite backend** | Default local storage | 10x faster queries, better concurrency |
| **Streaming traces** | Real-time in-progress trace viewing | Debug long-running workflows |
| **Distributed tracing** | Cross-service trace correlation | Future multi-service architecture |

### 3.3 Features to Keep from Current Implementation

✅ **Server accessibility check** (BUG-004 fix) - Keep 3s timeout for http:// URIs
✅ **Graceful degradation** - Keep `enabled` flag and fallback logic
✅ **Artifact level control** - Keep minimal/standard/full levels
✅ **Node-level overrides** - Keep `log_prompts`/`log_artifacts` per-node config
✅ **Cost estimator** - Keep `CostEstimator` class, enhance with trace integration
✅ **Configuration schema** - Keep existing config mostly intact (minor updates)

---

## 4. Proposed Architecture

### 4.1 New Architecture Overview

**Principle:** Leverage MLflow 3.9 auto-instrumentation where possible, keep manual control where valuable.

```
┌─────────────────────────────────────────────────────────────┐
│ Workflow Execution (runtime/executor.py)                    │
│                                                              │
│  def run_workflow():                                         │
│      mlflow.langchain.autolog()  # Enable auto-tracing      │
│      mlflow.set_experiment(...)                              │
│                                                              │
│      @mlflow.trace(name="workflow", attributes={...})        │
│      def _execute():                                         │
│          graph = build_graph()                               │
│          result = graph.invoke(initial_state)  # Auto-traced│
│          return result                                       │
│                                                              │
│      result = _execute()                                     │
│      _log_workflow_summary(result)  # Post-process          │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ Automatic tracing
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ LangGraph Execution (core/graph_builder.py)                 │
│                                                              │
│  graph = StateGraph(state_model)                             │
│  for node in nodes:                                          │
│      graph.add_node(node.id, execute_node_wrapper)           │
│                                                              │
│  compiled_graph.invoke(state)  ◄─── Auto-traced by MLflow  │
│      ├─ Node 1 execution ◄────────── Span created          │
│      ├─ LLM call ◄───────────────── Span created           │
│      ├─ Tool calls ◄─────────────── Spans created          │
│      └─ Node 2 execution...                                  │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ Token usage auto-captured
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ MLflow 3.9 Tracing Backend                                   │
│                                                              │
│  SQLite Database (mlflow.db)                                 │
│  ├─ Traces (workflows)                                       │
│  │   ├─ Span: workflow execution                            │
│  │   ├─ Span: node_1 (with token usage)                     │
│  │   │   └─ Span: llm_call                                  │
│  │   ├─ Span: node_2                                         │
│  │   └─ ...                                                  │
│  └─ Cost data (computed from token usage)                    │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ View in UI
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ MLflow GenAI Dashboard                                       │
│                                                              │
│  ├─ Trace Overview: Performance metrics, tool calls         │
│  ├─ Trace Details: Span hierarchy, inputs/outputs           │
│  ├─ Cost Analysis: Token usage, estimated costs             │
│  └─ Quality Metrics: LLM judge scores (optional)            │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 New MLFlowTracker Class Design

**Simplified architecture** - Focus on configuration and post-processing, not manual tracking.

```python
# src/configurable_agents/observability/mlflow_tracker.py (v3.9)

class MLFlowTracker:
    """
    MLflow 3.9 integration for workflow observability.

    Responsibilities (SIMPLIFIED from 484 → ~200 lines):
    1. Initialize MLflow (set URI, experiment, enable autolog)
    2. Configure observability settings (artifact levels, overrides)
    3. Provide helper methods for cost calculation (post-trace)
    4. Graceful degradation (enabled flag, server check)

    What's REMOVED:
    - Manual run management (start_run/end_run)
    - Context managers (track_workflow, track_node)
    - Manual metric logging (log_metric, log_param)
    - Nested run creation
    - Token counting state (_total_input_tokens, etc.)

    What's NEW:
    - Uses mlflow.langchain.autolog() for automatic tracing
    - Leverages @mlflow.trace for workflow-level tracing
    - Post-processes traces for cost calculation
    - Async trace logging configuration
    """

    def __init__(
        self,
        mlflow_config: Optional[ObservabilityMLFlowConfig],
        workflow_config: WorkflowConfig,
    ):
        self.enabled = (
            mlflow_config is not None
            and mlflow_config.enabled
            and MLFLOW_AVAILABLE
        )
        self.mlflow_config = mlflow_config
        self.workflow_config = workflow_config
        self.cost_estimator = CostEstimator()

        if self.enabled:
            self._initialize_mlflow_39()

    def _initialize_mlflow_39(self) -> None:
        """Initialize MLflow 3.9 with auto-instrumentation."""
        # Server check (keep from current implementation)
        if not self._check_tracking_server_accessible(timeout=3.0):
            logger.warning("MLFlow server not accessible. Disabling tracking.")
            self.enabled = False
            return

        try:
            # Set tracking URI
            mlflow.set_tracking_uri(self.mlflow_config.tracking_uri)

            # Set experiment
            mlflow.set_experiment(self.mlflow_config.experiment_name)

            # Enable async trace logging (production optimization)
            os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = "true"

            # Enable auto-instrumentation for LangChain/LangGraph
            mlflow.langchain.autolog(
                log_input_examples=True,
                log_model_signatures=True,
                log_models=False,  # Don't log model artifacts (config-driven)
                log_inputs_outputs=self._should_log_artifacts("standard"),
                silent=False,
            )

            logger.info("MLflow 3.9 auto-instrumentation enabled")

        except Exception as e:
            logger.error(f"Failed to initialize MLflow 3.9: {e}")
            self.enabled = False

    def get_trace_decorator(self, name: str, **attributes):
        """
        Get @mlflow.trace decorator configured for this tracker.

        Usage:
            @tracker.get_trace_decorator("workflow", workflow_name=name)
            def execute_workflow():
                # Workflow logic
                pass
        """
        if not self.enabled:
            # Return no-op decorator if disabled
            def noop_decorator(func):
                return func
            return noop_decorator

        return mlflow.trace(
            name=name,
            span_type="WORKFLOW" if "workflow" in name else "AGENT",
            attributes=attributes,
        )

    def get_workflow_cost_summary(self, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate cost summary from trace token usage.

        Args:
            trace_id: Trace ID (default: get latest from current run)

        Returns:
            Cost summary with total tokens, cost, node breakdown
        """
        if not self.enabled:
            return {}

        try:
            # Get trace (from ID or latest run)
            if trace_id:
                trace = mlflow.get_trace(trace_id)
            else:
                # Get latest trace from current experiment
                traces = mlflow.search_traces(
                    experiment_ids=[mlflow.get_experiment_by_name(
                        self.mlflow_config.experiment_name
                    ).experiment_id],
                    max_results=1,
                )
                trace = traces[0] if traces else None

            if not trace:
                return {}

            # Extract token usage from trace metadata
            total_tokens = trace.info.token_usage  # MLflow 3.4+
            # Returns: {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}

            # Calculate costs per node (iterate spans)
            node_costs = {}
            for span in trace.spans:
                if span.attributes.get("mlflow.chat.tokenUsage"):
                    tokens = span.attributes["mlflow.chat.tokenUsage"]
                    model = span.attributes.get("ai.model.name", "unknown")
                    cost = self.cost_estimator.estimate_cost(
                        model=model,
                        input_tokens=tokens.get("prompt_tokens", 0),
                        output_tokens=tokens.get("completion_tokens", 0),
                    )
                    node_costs[span.name] = {
                        "tokens": tokens,
                        "cost_usd": cost,
                        "model": model,
                    }

            return {
                "total_tokens": total_tokens,
                "total_cost_usd": sum(n["cost_usd"] for n in node_costs.values()),
                "node_breakdown": node_costs,
                "trace_id": trace.info.trace_id,
            }

        except Exception as e:
            logger.warning(f"Failed to get cost summary: {e}")
            return {}

    # Keep these helper methods from current implementation:
    # - _check_tracking_server_accessible()
    # - _should_log_artifacts()
    # - _should_log_prompts()
```

### 4.3 Integration with Execution Flow

#### executor.py (NEW)

```python
def run_workflow(
    workflow_config: WorkflowConfig,
    initial_inputs: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute workflow with MLflow 3.9 auto-tracing."""

    # Initialize tracker
    mlflow_config = (
        workflow_config.config.observability.mlflow
        if workflow_config.config and workflow_config.config.observability
        else None
    )
    tracker = MLFlowTracker(mlflow_config, workflow_config)

    # Build graph
    state_model = build_state_model(workflow_config.state)
    output_model = build_output_model(workflow_config.output)
    graph = build_graph(workflow_config, state_model, workflow_config.config)
    compiled_graph = graph.compile()

    # Define traced execution function
    @tracker.get_trace_decorator(
        name=f"workflow_{workflow_config.flow.name}",
        workflow_name=workflow_config.flow.name,
        workflow_version=workflow_config.flow.version or "unversioned",
        node_count=len(workflow_config.nodes),
    )
    def _execute_workflow():
        """Execute workflow (automatically traced by MLflow)."""
        try:
            # Validate inputs
            initial_state = state_model(**initial_inputs)

            # Execute graph (LangGraph execution auto-traced via autolog)
            final_state = compiled_graph.invoke(initial_state)

            # Extract outputs
            return extract_outputs(final_state, output_model)

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise

    # Execute workflow (tracing happens automatically)
    try:
        result = _execute_workflow()

        # Post-process: Calculate and log cost summary
        if tracker.enabled:
            cost_summary = tracker.get_workflow_cost_summary()
            logger.info(
                f"Workflow complete: {cost_summary.get('total_tokens', 0)} tokens, "
                f"${cost_summary.get('total_cost_usd', 0):.6f}"
            )

            # Log cost as custom metric for easy querying
            if mlflow.active_run():
                mlflow.log_metrics({
                    "total_cost_usd": cost_summary.get("total_cost_usd", 0),
                    "total_tokens": cost_summary.get("total_tokens", 0),
                })

        return result

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        raise
```

#### node_executor.py (SIMPLIFIED)

```python
def execute_node(
    node_config: NodeConfig,
    state: BaseModel,
    global_config: Optional[GlobalConfig] = None,
    tracker: Optional["MLFlowTracker"] = None,  # Kept for compatibility
) -> BaseModel:
    """
    Execute node (automatically traced by MLflow.langchain.autolog).

    NOTE: tracker parameter kept for backward compatibility but not used
    for tracing (handled automatically by autolog). Still used for config
    checks (e.g., artifact levels, observability overrides).
    """

    # ... (existing logic unchanged)

    # LLM call - automatically traced by mlflow.langchain.autolog()
    result, usage = call_llm_structured(
        llm=llm,
        prompt=resolved_prompt,
        output_model=OutputModel,
        tools=tools if tools else None,
        max_retries=max_retries,
    )
    # Token usage automatically captured in span attributes!

    # ... (rest of logic unchanged)
```

### 4.4 Configuration Changes

#### Minimal Changes to Config Schema

```python
class ObservabilityMLFlowConfig(BaseModel):
    """MLFlow observability config (v0.1+, updated for 3.9)."""

    enabled: bool = Field(False, description="Enable MLFlow tracking")
    tracking_uri: str = Field(
        "sqlite:///mlflow.db",  # CHANGED: Default now SQLite (MLflow 3.9 default)
        description="MLFlow backend URI (sqlite://, file://, postgresql://, s3://, etc.)"
    )
    experiment_name: str = Field(
        "configurable_agents",
        description="Experiment name for grouping runs"
    )
    run_name: Optional[str] = Field(
        None,
        description="Template for run names (default: timestamp-based)"
    )

    # Observability controls (workflow-level defaults, can be overridden per-node)
    log_prompts: bool = Field(
        True,
        description="Show prompts/responses in MLFlow UI (auto-captured by autolog)"
    )
    log_artifacts: bool = Field(
        True,
        description="Save artifacts as downloadable files"
    )
    artifact_level: str = Field(
        "standard",
        description="Artifact detail level: 'minimal', 'standard', or 'full'"
    )

    # NEW: Async trace logging (MLflow 3.5+)
    async_logging: bool = Field(
        True,
        description="Enable async trace logging for production (recommended)"
    )

    # NEW: LLM judges (MLflow 3.9+)
    enable_judges: bool = Field(
        False,
        description="Enable automatic LLM judges for quality assessment (v0.2+)"
    )

    # NEW: Prompt versioning (MLflow 3.7+)
    enable_prompt_registry: bool = Field(
        False,
        description="Enable prompt versioning in MLflow registry (v0.2+)"
    )

    # Enterprise hooks (reserved for v0.2+, not enforced)
    retention_days: Optional[int] = Field(
        None,
        description="Auto-cleanup old runs after N days (v0.2+)"
    )
    redact_pii: bool = Field(
        False,
        description="Sanitize PII before logging (v0.2+)"
    )

    @field_validator("tracking_uri")
    @classmethod
    def validate_tracking_uri_format(cls, v: str) -> str:
        """Validate tracking URI format."""
        if v.startswith("file://./mlruns"):
            # Warn about deprecated file backend
            logger.warning(
                "File backend (file://./mlruns) is deprecated in MLflow 3.9. "
                "Consider migrating to SQLite: sqlite:///mlflow.db"
            )
        return v
```

**Migration Note for Users:**
- Existing configs with `tracking_uri: "file://./mlruns"` will continue to work (auto-detected)
- New users default to SQLite (`sqlite:///mlflow.db`)
- No breaking changes to existing YAML configs

---

## 5. Migration Strategy

### 5.1 Phased Approach

**Phase 3: Enhanced Observability Design** (Before Implementation)
- Design enhanced metrics and visualization strategy
- Plan LLM judge integration points
- Identify new observability opportunities
- Document artifact schema changes

**Phase 4: Implementation** (After Phase 3 Complete)
- **Step 1**: Update dependencies (`mlflow>=3.9.0`)
- **Step 2**: Rewrite `MLFlowTracker` class (new architecture)
- **Step 3**: Update `executor.py` integration
- **Step 4**: Update `node_executor.py` (minimal changes)
- **Step 5**: Update configuration schema (backward compatible)
- **Step 6**: Update tests (unit + integration)
- **Step 7**: Update documentation
- **Step 8**: Performance benchmarking

### 5.2 Backward Compatibility

**Preserved:**
✅ Config schema structure (minor additions only)
✅ Existing `file://./mlruns` databases (auto-detected)
✅ Artifact levels (minimal, standard, full)
✅ Node-level observability overrides
✅ Graceful degradation when MLflow unavailable
✅ Server accessibility check (3s timeout)

**Changed (Internal Only):**
- `MLFlowTracker` internal implementation
- Context managers replaced with decorators
- Manual metric logging → automatic span capture

**User Impact:**
- Zero impact on existing YAML configs
- Existing `./mlruns` data remains accessible
- New features opt-in via config flags

### 5.3 Feature Flags for Gradual Rollout

```python
class ObservabilityMLFlowConfig(BaseModel):
    # ...

    # Feature flags for gradual adoption
    use_mlflow_39_tracing: bool = Field(
        True,
        description="Use MLflow 3.9 tracing (disable to use legacy tracking)"
    )
```

**Rollout Strategy:**
1. **Alpha** (Internal): `use_mlflow_39_tracing=True` by default, test thoroughly
2. **Beta** (Early Adopters): Document migration, collect feedback
3. **GA** (General Availability): Remove legacy code path (if no issues)

### 5.4 Data Migration

**No migration required!**

MLflow 3.9 automatically detects existing `./mlruns` directories:
- If `./mlruns` exists with data → continues using file store
- If no existing data → creates `mlflow.db` SQLite database

**Optional: Manual SQLite Migration**
- For users wanting to migrate `./mlruns` → `mlflow.db`
- Provide migration script in `scripts/migrate_mlflow_to_sqlite.py`
- Document in `docs/MLFLOW_39_MIGRATION_GUIDE.md`

---

## 6. Breaking Changes & Compatibility

### 6.1 No Breaking Changes for Users

**Public API (Config YAMLs):**
- ✅ All existing config fields remain valid
- ✅ Default values backward compatible (with deprecation warnings)
- ✅ Existing experiments and runs remain accessible

**Python API (for developers extending the system):**
- ⚠️ `MLFlowTracker` class signature changes (internal implementation)
- ⚠️ Context managers removed (replaced with decorators)
- ✅ Cost estimator API unchanged
- ✅ Config schema mostly unchanged (additions only)

### 6.2 Internal Breaking Changes

**Removed (Internal):**
- `MLFlowTracker.track_workflow()` context manager
- `MLFlowTracker.track_node()` context manager
- `MLFlowTracker.log_node_metrics()` method
- `MLFlowTracker.finalize_workflow()` method
- `MLFlowTracker._log_workflow_params()` method
- Manual state tracking (`_total_input_tokens`, `_total_output_tokens`, etc.)

**Replaced With:**
- `MLFlowTracker.get_trace_decorator()` - Returns configured `@mlflow.trace`
- `MLFlowTracker.get_workflow_cost_summary()` - Post-trace cost calculation
- Automatic tracing via `mlflow.langchain.autolog()`

**Migration Path for Custom Code:**
```python
# OLD (deprecated)
with tracker.track_workflow(inputs):
    with tracker.track_node("node1", "model"):
        result = execute()
        tracker.log_node_metrics(tokens, cost)

# NEW (MLflow 3.9)
@tracker.get_trace_decorator("workflow")
def execute_workflow():
    # Automatically traced via mlflow.langchain.autolog()
    result = graph.invoke(state)
    return result
```

### 6.3 Deprecation Warnings

**File Backend Warning:**
```python
if tracking_uri.startswith("file://"):
    warnings.warn(
        "File backend (file://./mlruns) is deprecated. "
        "Consider migrating to SQLite: sqlite:///mlflow.db",
        DeprecationWarning,
        stacklevel=2
    )
```

**No Hard Failures:**
- Deprecation warnings logged, but functionality preserved
- Users have time to migrate at their own pace

---

## 7. Implementation Phases

### Phase 3: Enhanced Observability Design (Before Implementation)

**Duration:** 1-2 days

**Deliverables:**
1. Enhanced observability design document
2. Artifact schema specifications
3. LLM judge integration design
4. Quality metrics definitions
5. Visualization dashboard mockups

**Key Decisions:**
- Which LLM judges to enable by default?
- What quality metrics to track?
- How to visualize tool call patterns?
- Artifact schema for GenAI features?

### Phase 4: Implementation (After Phase 3)

#### 4.1 Dependency Updates

**Duration:** 1 hour

**Tasks:**
1. Update `pyproject.toml`:
   ```toml
   [tool.poetry.dependencies]
   mlflow = "^3.9.0"  # Updated from "^2.9.0"
   ```

2. Update `requirements.txt` (if used):
   ```
   mlflow>=3.9.0
   ```

3. Run dependency update:
   ```bash
   poetry update mlflow
   # or
   pip install --upgrade mlflow>=3.9.0
   ```

4. Verify installation:
   ```bash
   python -c "import mlflow; print(mlflow.__version__)"
   # Should print: 3.9.0 or higher
   ```

#### 4.2 Rewrite MLFlowTracker

**Duration:** 4-6 hours

**File:** `src/configurable_agents/observability/mlflow_tracker.py`

**Changes:**
1. Remove context managers (`track_workflow`, `track_node`)
2. Remove manual metric logging methods
3. Remove token counting state variables
4. Add `_initialize_mlflow_39()` with `autolog()`
5. Add `get_trace_decorator()` helper
6. Add `get_workflow_cost_summary()` for post-processing
7. Keep server check, graceful degradation, artifact level logic
8. Update docstrings to reflect new architecture

**Target:** Reduce from 484 lines → ~200 lines

#### 4.3 Update executor.py

**Duration:** 2-3 hours

**File:** `src/configurable_agents/runtime/executor.py`

**Changes:**
1. Remove `tracker.track_workflow()` context manager usage
2. Add `@tracker.get_trace_decorator()` to workflow function
3. Add post-execution cost summary logging
4. Update error handling (still graceful, but simpler)

#### 4.4 Update node_executor.py

**Duration:** 1-2 hours

**File:** `src/configurable_agents/core/node_executor.py`

**Changes:**
1. Keep `tracker` parameter (for config checks, but not active tracing)
2. Remove manual `tracker.track_node()` / `tracker.log_node_metrics()` calls
3. Add comment explaining auto-tracing via `autolog()`
4. Simplify error handling (no manual metric logging)

#### 4.5 Update Configuration Schema

**Duration:** 1 hour

**File:** `src/configurable_agents/config/schema.py`

**Changes:**
1. Change default `tracking_uri` to `"sqlite:///mlflow.db"`
2. Add new fields: `async_logging`, `enable_judges`, `enable_prompt_registry`
3. Add validator with deprecation warning for `file://` URIs
4. Update docstrings

#### 4.6 Update Tests

**Duration:** 6-8 hours

**Files:**
- `tests/observability/test_mlflow_tracker.py`
- `tests/observability/test_mlflow_integration.py`
- `tests/runtime/test_executor.py`

**Changes:**
1. Update unit tests for new `MLFlowTracker` class
   - Remove context manager tests
   - Add decorator tests
   - Add cost summary tests
   - Update mock setup for `autolog()`

2. Update integration tests
   - Verify auto-tracing works with real LangGraph execution
   - Verify token usage captured automatically
   - Verify traces visible in MLflow UI
   - Verify cost calculation accurate

3. Add new tests for MLflow 3.9 features
   - Test async logging configuration
   - Test SQLite backend (default)
   - Test file backend compatibility (existing data)
   - Test trace retrieval and cost calculation

**Target:** Maintain 100% pass rate (67 CLI tests + unit/integration tests)

#### 4.7 Update Documentation

**Duration:** 3-4 hours

**Files:**
- `docs/OBSERVABILITY.md`
- `docs/QUICKSTART.md`
- `docs/CONFIG_REFERENCE.md`
- `docs/MLFLOW_39_MIGRATION_GUIDE.md` (new)
- `docs/TROUBLESHOOTING.md`
- `README.md`

**Changes:**
1. Update `OBSERVABILITY.md`:
   - Document new MLflow 3.9 features
   - Update setup instructions (SQLite default)
   - Add GenAI dashboard screenshots
   - Document LLM judges, prompt versioning

2. Create `MLFLOW_39_MIGRATION_GUIDE.md`:
   - Guide for users migrating from v0.1
   - Data migration instructions (optional)
   - Feature comparison table
   - Troubleshooting tips

3. Update config examples:
   - Change default `tracking_uri` in examples
   - Add examples for new features
   - Add deprecation notes

#### 4.8 Performance Benchmarking

**Duration:** 2-3 hours

**Benchmark Scenarios:**
1. **Baseline**: Current implementation (MLflow 2.9+)
2. **MLflow 3.9 + autolog**: New implementation
3. **MLflow 3.9 + async**: New implementation with async logging

**Metrics to Compare:**
- Workflow execution time (overhead from tracing)
- Memory usage
- Trace log upload time
- Query performance (SQLite vs file backend)
- Concurrent workflow execution

**Acceptance Criteria:**
- ✅ Execution overhead < 5% (compared to current)
- ✅ Async logging reduces overhead to < 1%
- ✅ SQLite queries 10x faster than file backend
- ✅ Memory usage comparable or better

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Coverage Target:** >80% (maintain current standard)

**Test Categories:**

1. **MLFlowTracker Initialization:**
   - Test enabled/disabled states
   - Test server accessibility check
   - Test autolog configuration
   - Test graceful degradation

2. **Configuration:**
   - Test config validation
   - Test default values
   - Test backward compatibility (file:// URIs)
   - Test deprecation warnings

3. **Cost Calculation:**
   - Test `get_workflow_cost_summary()`
   - Test token extraction from traces
   - Test cost estimator integration
   - Test missing token usage handling

4. **Artifact Levels:**
   - Test minimal/standard/full filtering
   - Test node-level overrides
   - Test artifact logging decisions

### 8.2 Integration Tests

**Note:** Integration tests use real MLflow and LLM APIs (costs ~$0.50 per run)

**Test Scenarios:**

1. **End-to-End Workflow:**
   - Execute article_writer workflow
   - Verify trace created in MLflow
   - Verify spans for each node
   - Verify token usage captured
   - Verify cost calculation accurate

2. **LangGraph Auto-Tracing:**
   - Execute multi-node workflow
   - Verify LangGraph execution traced
   - Verify node spans created automatically
   - Verify tool calls captured (if tools used)

3. **SQLite Backend:**
   - Execute workflow with `sqlite:///mlflow.db`
   - Verify database created
   - Verify traces queryable
   - Verify performance acceptable

4. **File Backend Compatibility:**
   - Execute workflow with existing `./mlruns`
   - Verify auto-detection works
   - Verify backward compatibility

5. **Async Logging:**
   - Enable `async_logging=True`
   - Execute workflow
   - Verify traces logged asynchronously
   - Verify zero execution overhead

### 8.3 Manual Testing

**MLflow UI Verification:**
1. Start MLflow UI: `mlflow ui`
2. Run sample workflows
3. Verify:
   - Traces visible in UI
   - GenAI dashboard shows metrics
   - Tool calls visible (if applicable)
   - Prompts/responses logged correctly
   - Cost data accurate

**Backward Compatibility:**
1. Test with existing `file://./mlruns` data
2. Verify auto-detection
3. Verify existing runs still accessible
4. Verify new runs work

---

## 9. Rollback Plan

### 9.1 Rollback Triggers

**Trigger rollback if:**
- Critical bug discovered in production
- Performance degradation >10%
- Data loss or corruption
- Integration test failures
- User-reported blocking issues

### 9.2 Rollback Procedure

**Step 1: Revert Code**
```bash
git revert <migration-commit-hash>
# or
git checkout <previous-stable-tag>
```

**Step 2: Downgrade MLflow**
```bash
poetry add mlflow@^2.9.0
# or
pip install mlflow==2.9.2
```

**Step 3: Restore Configuration**
- Revert config schema changes
- Restore old `MLFlowTracker` class

**Step 4: Verify Rollback**
- Run full test suite
- Verify existing data accessible
- Execute sample workflows

**Step 5: Communicate**
- Notify users of rollback
- Document issues encountered
- Plan fixes before retry

### 9.3 Data Safety

**No data loss on rollback:**
- MLflow 3.9 traces stored in same format as 2.9+
- Backward compatible read/write
- Existing `./mlruns` or `mlflow.db` remain intact

**Worst-case scenario:**
- New traces created during migration period might not be accessible in old version
- Solution: Keep MLflow 3.9 for querying, rollback only application code

---

## 10. Success Criteria

### 10.1 Functional Requirements

✅ **Core Functionality:**
- [ ] All 67 CLI tests pass
- [ ] All unit tests pass (>80% coverage maintained)
- [ ] All integration tests pass
- [ ] Workflows execute successfully with tracing
- [ ] Token usage captured automatically
- [ ] Cost calculation accurate

✅ **MLflow 3.9 Features:**
- [ ] Auto-instrumentation via `mlflow.langchain.autolog()` working
- [ ] Traces visible in MLflow UI
- [ ] GenAI dashboard displays metrics
- [ ] Span hierarchy correct (workflow → nodes → LLM calls)
- [ ] Tool calls captured (if tools used)

✅ **Backward Compatibility:**
- [ ] Existing YAML configs work unchanged
- [ ] Existing `./mlruns` data accessible
- [ ] Deprecation warnings shown (not errors)
- [ ] Graceful degradation when MLflow unavailable

### 10.2 Non-Functional Requirements

✅ **Performance:**
- [ ] Execution overhead < 5% (compared to current)
- [ ] Async logging reduces overhead to < 1%
- [ ] SQLite queries 10x faster than file backend
- [ ] Memory usage comparable or better

✅ **Code Quality:**
- [ ] Code reduced from 484 → ~200 lines (60% reduction)
- [ ] Simpler architecture (no manual run management)
- [ ] Maintainable and well-documented
- [ ] No pylint/mypy errors

✅ **Documentation:**
- [ ] Migration guide complete
- [ ] Config reference updated
- [ ] Observability docs updated
- [ ] Troubleshooting guide updated
- [ ] README reflects changes

### 10.3 User Experience

✅ **Developer Experience:**
- [ ] Easier to understand and modify
- [ ] Less boilerplate code
- [ ] Clear error messages
- [ ] Helpful logging

✅ **End-User Experience:**
- [ ] Zero breaking changes to configs
- [ ] Better observability insights
- [ ] Faster query performance (SQLite)
- [ ] Optional new features (judges, prompt versioning)

---

## Summary & Next Steps

### Phase 2 Complete ✅

This comprehensive migration plan covers:
- ✅ Current implementation analysis (detailed breakdown)
- ✅ Feature mapping (current → MLflow 3.9)
- ✅ Proposed architecture (simplified, auto-instrumented)
- ✅ Migration strategy (phased, backward compatible)
- ✅ Breaking changes assessment (none for users!)
- ✅ Implementation phases (8 detailed steps)
- ✅ Testing strategy (unit + integration + manual)
- ✅ Rollback plan (safe and straightforward)
- ✅ Success criteria (functional + non-functional)

### Key Insights

**Major Benefits:**
1. **60% code reduction** (484 → 200 lines)
2. **Zero breaking changes** for users
3. **Automatic instrumentation** via `mlflow.langchain.autolog()`
4. **Better performance** with SQLite backend
5. **Enhanced observability** with GenAI dashboard

**Low Risk Migration:**
- Backward compatible (existing data + configs work)
- Gradual rollout possible (feature flags)
- Safe rollback plan
- Comprehensive testing strategy

### Ready for Phase 3: Enhanced Observability Design

**Next Steps:**
1. Design enhanced metrics and artifacts
2. Plan LLM judge integration
3. Define quality assessment strategy
4. Design visualization enhancements
5. Document artifact schema

**After Phase 3, proceed to Phase 4: Implementation**

---

*Last Updated: 2026-02-02*
*Phase 2 of T-028: MLFlow 3.9 Comprehensive Migration*
*Status: Planning Complete → Ready for Phase 3 (Enhanced Observability Design)*
