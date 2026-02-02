# MLflow 3.9 Migration Guide for Users

**Quick reference for migrating workflows to MLflow 3.9 automatic tracing**

---

## What Changed?

**MLflow 3.9** introduces automatic tracing for LangChain/LangGraph applications, eliminating the need for manual instrumentation.

### Key Changes

✅ **Automatic tracing** via `mlflow.langchain.autolog()`
✅ **Automatic token tracking** from LLM responses
✅ **Simplified configuration** - just enable MLflow
✅ **Better async support** with `run_tracer_inline=True`
✅ **SQLite backend** as default (replaces deprecated file://)

❌ **Removed**: Manual context managers and tracking code
❌ **Deprecated**: `file://` backend (still works, but use `sqlite://` instead)

---

## Quick Migration Checklist

### 1. Update Dependencies

```bash
pip install --upgrade mlflow>=3.9.0
```

### 2. Update Config (Optional but Recommended)

**Before (file:// backend)**:
```yaml
config:
  observability:
    mlflow:
      enabled: true
      tracking_uri: "file://./mlruns"  # Still works but deprecated
```

**After (SQLite backend)**:
```yaml
config:
  observability:
    mlflow:
      enabled: true
      tracking_uri: "sqlite:///mlflow.db"  # Recommended
      async_logging: true  # NEW: Zero-latency production mode
```

### 3. That's It!

No code changes required. MLflow 3.9 automatically traces your workflows.

---

## Configuration Changes

### New Fields

```yaml
config:
  observability:
    mlflow:
      enabled: true
      tracking_uri: "sqlite:///mlflow.db"  # SQLite (recommended)
      experiment_name: "my_workflows"

      # NEW in MLflow 3.9
      async_logging: true  # Enable async trace logging (default: true)

      # Existing fields (unchanged)
      log_artifacts: true
      artifact_level: "standard"  # minimal | standard | full
```

### Backend Migration

**Migrate from file:// to SQLite**:

```bash
# Old data is in file://./mlruns
# New data will be in sqlite:///mlflow.db

# Option 1: Keep using file:// (works but deprecated)
tracking_uri: "file://./mlruns"

# Option 2: Migrate to SQLite (recommended)
# 1. Export old data
mlflow experiments csv --experiment-id 0 > old_data.csv

# 2. Switch to SQLite in config
tracking_uri: "sqlite:///mlflow.db"

# 3. Import data (manual, if needed for historical analysis)
```

**Note**: MLflow 3.9 can still read `file://./mlruns` data, but future versions may drop support.

---

## What You'll See in MLflow UI

### Trace View (New in 3.9)

Open `http://localhost:5000` and click on a workflow run:

```
workflow_article_writer (5.2s)
├─ research_node (2.1s)
│  ├─ Token usage: 150 input, 500 output
│  ├─ Cost: $0.0015
│  └─ Model: gemini-1.5-flash
└─ write_node (3.0s)
   ├─ Token usage: 200 input, 600 output
   ├─ Cost: $0.0020
   └─ Model: gemini-1.5-flash
```

### Metrics Tab

- `total_cost_usd`: Total workflow cost
- `total_tokens`: Total tokens used
- `prompt_tokens`: Input tokens
- `completion_tokens`: Output tokens
- `node_count`: Number of nodes executed

### Artifacts

- `cost_summary.json`: Detailed cost breakdown

---

## Breaking Changes (None for Users!)

**Good news**: If you're using config files, there are **no breaking changes**.

Your existing configs will continue to work:

```yaml
# This still works exactly as before
config:
  observability:
    mlflow:
      enabled: true
```

MLflow 3.9 automatically handles all tracing behind the scenes.

---

## Advanced Features

### Async Logging (Production Performance)

MLflow 3.9 supports async trace logging for zero-latency production:

```yaml
config:
  observability:
    mlflow:
      async_logging: true  # Default: true
```

**Benefits**:
- No blocking I/O during workflow execution
- 20+ concurrent workers for trace uploads
- Automatic retry with exponential backoff
- 2000-item queue buffer

**Trade-off**: Traces may appear in UI with slight delay (< 1 second)

### Artifact Levels

Control what gets logged:

```yaml
config:
  observability:
    mlflow:
      artifact_level: "standard"  # minimal | standard | full
```

- **minimal**: Only cost summary
- **standard**: Cost summary + basic traces (default)
- **full**: Everything (prompts, responses, intermediate outputs)

### Remote Backends

**Team collaboration** (PostgreSQL):
```yaml
tracking_uri: "postgresql://user:pass@db.example.com/mlflow"
```

**Cloud storage** (AWS S3):
```yaml
tracking_uri: "s3://company-mlflow/workflows"
```

**Managed service** (Databricks):
```yaml
tracking_uri: "databricks://workspace"
```

---

## Troubleshooting

### "MLflow not tracking anything"

Check logs:
```bash
configurable-agents run workflow.yaml --verbose
```

Look for:
```
✓ MLflow 3.9 auto-instrumentation enabled (langchain.autolog)
✓ Experiment: my_workflows (ID: 1)
```

### "File locking errors on Windows"

Switch to SQLite:
```yaml
tracking_uri: "sqlite:///mlflow.db"
```

SQLite handles Windows file locking better than `file://`.

### "Traces not showing in UI"

Check tracking URI matches:
```bash
# In config
tracking_uri: "sqlite:///mlflow.db"

# Start UI from same directory
cd /path/to/project
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

### "Missing token usage"

Token usage is automatically captured from LLM responses. If missing:
- Check that LLM provider returns usage metadata
- Google Gemini: Always returns usage ✅
- Check MLflow logs for warnings

---

## FAQ

### Do I need to change my workflow configs?

**No**. Existing configs work as-is. Optionally update `tracking_uri` to `sqlite://` for better performance.

### What happened to manual tracking APIs?

Removed in favor of automatic tracing. If you were using Python API directly:
- ❌ `tracker.track_workflow()` → Auto-traced
- ❌ `tracker.track_node()` → Auto-traced
- ❌ `tracker.log_node_metrics()` → Auto-captured

### Can I still use file:// backend?

Yes, but it's deprecated. You'll see a warning:
```
WARNING: File backend (file://./mlruns) is deprecated in MLflow 3.9.
Consider migrating to SQLite: sqlite:///mlflow.db
```

### How do I query traces programmatically?

```python
import mlflow

# Connect
mlflow.set_tracking_uri("sqlite:///mlflow.db")

# Get latest trace
experiment = mlflow.get_experiment_by_name("my_workflows")
traces = mlflow.search_traces(
    experiment_ids=[experiment.experiment_id],
    max_results=1,
    order_by=["timestamp DESC"]
)

trace = traces[0]
print(f"Trace ID: {trace.info.trace_id}")
print(f"Tokens: {trace.info.token_usage}")

# Get cost breakdown per node
for span in trace.data.spans:
    token_usage = span.attributes.get("mlflow.chat.tokenUsage")
    if token_usage:
        print(f"{span.name}: {token_usage['total_tokens']} tokens")
```

### Where can I learn more about MLflow 3.9?

- [MLflow 3.9 Release Notes](https://github.com/mlflow/mlflow/releases/tag/v3.9.0)
- [MLflow LangChain Integration](https://mlflow.org/docs/latest/llms/langchain/index.html)
- [docs/MLFLOW_39_FEATURES.md](MLFLOW_39_FEATURES.md) - Comprehensive feature reference

---

## Getting Help

**Issues**: https://github.com/anthropics/configurable-agents/issues
**Docs**: [docs/OBSERVABILITY.md](OBSERVABILITY.md)
**MLflow Docs**: https://mlflow.org/docs/latest/

---

**Last Updated**: 2026-02-02 (v0.1, MLflow 3.9 migration)
