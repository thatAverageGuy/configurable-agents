# Observability Reference — MLflow 3.9 GenAI Model

**Date**: 2026-02-09
**Purpose**: Single source of truth for how observability works in this project.
**Read this before**: Fixing any observability/profiling/cost-reporting issue.

---

## MLflow 3.9: Two Paradigms

MLflow 3.9 has two distinct paradigms:

| Aspect | ML (Legacy) | GenAI (What We Use) |
|--------|-------------|---------------------|
| Primary unit | **Run** | **Trace** |
| Data structure | Run → metrics, params, artifacts | Trace → spans (tree) |
| Timing | Manual `mlflow.log_metric()` | Automatic via span start/end timestamps |
| Token usage | Manual `mlflow.log_metric("tokens", N)` | Automatic via `mlflow.chat.tokenUsage` span attribute |
| Cost tracking | Manual metric logging | We compute from span token data + CostEstimator |
| Storage default | `./mlruns/` directory | `sqlite:///mlflow.db` |
| API to query | `client.search_runs()` | `client.search_traces()`, `mlflow.get_trace()` |
| UI view | Experiment → Runs table | Experiment → Traces tab |
| Feedback | N/A | `mlflow.log_feedback()` (assessments on traces) |
| Autolog | `mlflow.autolog()` → logs params/metrics to runs | `mlflow.langchain.autolog()` → logs traces with spans |

**Critical rule**: We are a GenAI/agentic project. We use **traces, not runs**. Never introduce `mlflow.start_run()` / `mlflow.log_metric()` to the executor pipeline.

---

## Our Current Architecture (Correct)

### How data flows

```
Workflow Execution
    │
    ├── mlflow.langchain.autolog() ──── auto-creates trace + spans
    │       (configured in MLFlowTracker._initialize_mlflow_39)
    │
    ├── @tracker.get_trace_decorator() ──── wraps _execute_workflow()
    │       Creates root WORKFLOW span with custom attributes:
    │       workflow_name, workflow_version, node_count
    │
    ├── LangGraph graph.invoke() ──── LangChain autolog captures:
    │       - LangGraph span (CHAIN)
    │       - Node spans (CHAIN) — one per workflow node
    │       - RunnableSequence spans
    │       - ChatModel spans (CHAT_MODEL) — THE KEY SPAN
    │       - Parser/Lambda spans
    │
    ├── tracker.get_workflow_cost_summary() ──── reads trace spans
    │       Extracts tokens from CHAT_MODEL spans
    │       Computes cost via CostEstimator
    │       Returns per-node and per-provider breakdown
    │
    └── tracker.log_workflow_summary() ──── writes trace feedback
            mlflow.log_feedback(cost_usd, total_tokens, ...)
            Attached as assessments on the trace
```

### What the autolog captures (verified)

From actual trace inspection of `02_with_observability.yaml` run:

**Trace level**:
- `trace.info.request_id` — unique trace ID (e.g., `tr-142b4636...`)
- `trace.info.status` — `TraceStatus.OK` or error
- `trace.info.execution_time_ms` — total workflow duration (e.g., 2912ms)
- `trace.info.timestamp_ms` — when the trace started
- `trace.info.tags` — includes `mlflow.traceName`, artifact location
- `trace.data.request` — workflow input
- `trace.data.response` — workflow output

**Span hierarchy** (13 spans for a single-node workflow):
```
workflow_test_02_observability  (WORKFLOW, 2911ms)  ← our decorator
  └── LangGraph  (CHAIN, 2903ms)  ← LangGraph graph
        └── process  (CHAIN, 2902ms)  ← our workflow node
              └── RunnableSequence  (CHAIN, 1603ms)
                    ├── RunnableParallel<raw>  (CHAIN, 1580ms)
                    │     └── ChatGoogleGenerativeAI  (CHAT_MODEL, 1577ms)  ★ KEY
                    └── RunnableWithFallbacks  (CHAIN, 19ms)
                          └── [parsing chain...]
```

**The CHAT_MODEL span** is where the gold is:
```
span_type: CHAT_MODEL
attributes:
  mlflow.chat.tokenUsage: {input_tokens: 26, output_tokens: 30, total_tokens: 56}
  invocation_params: {model: "gemini-2.5-flash-lite", temperature: 0.7, ...}
  mlflow.spanInputs: [[{content: "prompt text", type: "human"}]]
  mlflow.spanOutputs: {generations: [[{text: "response", generation_info: {finish_reason, model_name}}]]}
```

**Data available per CHAT_MODEL span**:
| Data | Attribute Key | Example |
|------|--------------|---------|
| Token usage | `mlflow.chat.tokenUsage` | `{input_tokens: 26, output_tokens: 30, total_tokens: 56}` |
| Model name | `invocation_params.model` | `gemini-2.5-flash-lite` |
| Duration | span start/end timestamps | 1577ms (computed) |
| Prompt | `mlflow.spanInputs` | Full prompt text |
| Response | `mlflow.spanOutputs` | Full response with metadata |
| Finish reason | Via `response_metadata.finish_reason` | `STOP` |

---

## What Works Today (Post-Verification)

| Component | Status | Detail |
|-----------|--------|--------|
| `MLFlowTracker._initialize_mlflow_39()` | **Works** | Sets up autolog, creates experiment |
| `mlflow.langchain.autolog()` | **Works** | Captures full trace with spans |
| `@tracker.get_trace_decorator()` | **Works** | Adds workflow-level span |
| `tracker.get_workflow_cost_summary()` | **Works** | Reads trace spans, extracts tokens, computes cost |
| `tracker.log_workflow_summary()` | **Works** | Logs cost/token feedback to trace |
| Storage: `sqlite:///mlflow.db` | **Works** | Default tracking store |

---

## What's Broken (From Verification)

### Reporting commands use legacy Run APIs

| Command | Current API | Should Use | Issue |
|---------|------------|------------|-------|
| `cost-report` | `MultiProviderCostTracker.generate_report()` → `search_runs()` | `search_traces()` + span parsing | VF-004 |
| `profile-report` | `search_runs()` → `node_*_duration_ms` metrics | `search_traces()` + span duration | VF-004 |
| `observability status` | `search_runs()` → counts | `search_traces()` → counts | VF-004 |
| `report costs` | `CostReporter.get_cost_entries()` → `search_runs()` | `search_traces()` + span parsing | VF-004/VF-005 |

### Profiling pipeline disconnected

| Component | Current State | Issue |
|-----------|--------------|-------|
| `--enable-profiling` flag | Sets env var, never read | VF-002 |
| `BottleneckAnalyzer` | Always runs, records to memory | Data logged via `logger.info()` (broken, VF-001) and stored in `workflows.db` `bottleneck_info` |
| `node_executor.py:594` | `mlflow.log_metric()` guarded by `mlflow.active_run()` | `active_run()` is always None (no runs, only traces) |
| `profile-report` | Queries run metrics | No runs exist |

---

## How Reporting Commands SHOULD Work

### Cost Report (via traces)

```python
# Instead of:
runs = client.search_runs(experiment_ids=[...])
for run in runs:
    cost = run.data.metrics.get("total_cost_usd", 0)

# Should be:
traces = client.search_traces(locations=[exp_id])
for trace in traces:
    for span in trace.data.spans:
        token_usage = span.attributes.get("mlflow.chat.tokenUsage")
        if token_usage:
            # Extract model from invocation_params
            # Compute cost via CostEstimator
```

**Note**: `tracker.get_workflow_cost_summary()` already does this correctly for a single trace. The reporting commands need to do it across multiple traces.

### Profile Report (via traces)

```python
# Instead of:
metrics = run.data.metrics
node_timings = {k: v for k, v in metrics.items() if k.startswith("node_") and k.endswith("_duration_ms")}

# Should be:
traces = client.search_traces(locations=[exp_id])
for trace in traces:
    for span in trace.data.spans:
        # Span duration is built-in:
        duration_ms = (span.end_time_ns - span.start_time_ns) / 1_000_000
        # Node identity from span name + metadata.langgraph_node
```

### Observability Status (via traces)

```python
# Instead of:
runs = client.search_runs(experiment_ids=[...])
print(f"{len(runs)} runs in last 24h")

# Should be:
traces = client.search_traces(
    locations=[exp_id],
    filter_string=f"trace.timestamp_ms > {cutoff_ms}",
)
print(f"{len(traces)} traces in last 24h")
```

---

## Storage Architecture

### Files and their purpose

| File | Type | Owner | Purpose |
|------|------|-------|---------|
| `mlflow.db` | SQLite | MLflow | Default tracking store — traces, spans, experiments, assessments |
| `workflows.db` | SQLite | Storage factory | Workflow run records, execution state, memory, bottleneck_info |
| `mlflow_test.db` | SQLite | Per-config | Created when config specifies custom `tracking_uri` |
| `mlruns/` | Directory | MLflow (legacy) | Only for artifacts if `artifactLocation` uses file:// path. NOT for data storage. |

### What goes where

```
mlflow.db (or custom tracking_uri):
├── Experiments table
├── Traces table (GenAI)
├── Spans table (GenAI)
├── Assessments table (feedback/cost data)
├── Runs table (ML legacy — we don't use)
└── Metrics/Params tables (ML legacy — we don't use)

workflows.db:
├── Workflow runs (our own record with bottleneck_info)
├── Execution state per node
└── Memory persistence
```

---

## Key MLflow 3.9 APIs We Should Use

### Querying traces
```python
# Search traces in an experiment
traces = mlflow.search_traces(
    locations=[experiment_id],         # experiment ID(s)
    filter_string="...",              # optional filter
    max_results=100,
    order_by=["timestamp DESC"],
)

# Get a specific trace
trace = mlflow.get_trace(request_id)

# Access trace data
trace.info.request_id        # trace ID
trace.info.execution_time_ms # total duration
trace.info.status            # OK, ERROR
trace.data.spans             # list of Span objects
trace.data.request           # input
trace.data.response          # output
```

### Working with spans
```python
for span in trace.data.spans:
    span.name           # e.g., "ChatGoogleGenerativeAI", "process"
    span.span_type      # WORKFLOW, CHAIN, CHAT_MODEL, etc.
    span.parent_id      # for tree reconstruction
    span.start_time_ns  # nanoseconds
    span.end_time_ns    # nanoseconds
    span.attributes     # dict with all metadata
    span.inputs         # span inputs
    span.outputs        # span outputs
```

### Feedback (assessments on traces)
```python
mlflow.log_feedback(
    trace_id=trace_id,
    name="cost_usd",
    value=0.001234,
    source=AssessmentSource(
        source_type=AssessmentSourceType.CODE,
        source_id="cost_estimator",
    ),
    rationale="56 tokens across 1 provider(s)",
)
```

---

## Rules for Fixing Observability

1. **NEVER** add `mlflow.start_run()` to the executor pipeline
2. **NEVER** use `mlflow.log_metric()` / `mlflow.log_param()` for workflow data
3. **ALWAYS** query traces via `search_traces()` / `get_trace()`, not `search_runs()`
4. **ALWAYS** extract timing from span timestamps, not run metrics
5. **ALWAYS** extract token usage from `mlflow.chat.tokenUsage` span attribute
6. **ALWAYS** use `sqlite:///mlflow.db` as default, not `./mlruns/`
7. Cost estimation goes through `CostEstimator` using span token data
8. The `MLFlowTracker.get_workflow_cost_summary()` is the reference implementation for trace-based cost extraction — reporting commands should follow the same pattern

---

*This document must be consulted before any observability-related code changes.*
