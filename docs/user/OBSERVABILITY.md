# Observability Guide

**Comprehensive guide to tracking, monitoring, and optimizing your LLM workflows**

**Updated for MLflow 3.9** (February 2026) - Now with automatic tracing!

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [MLFlow 3.9 Integration](#mlflow-39-integration)
- [Configuration Reference](#configuration-reference)
- [What Gets Tracked](#what-gets-tracked)
- [Cost Tracking](#cost-tracking)
- [Docker Integration](#docker-integration)
- [Querying & Reporting](#querying--reporting)
- [Best Practices](#best-practices)
- [Migration from Pre-3.9](#migration-from-pre-39)
- [OpenTelemetry (v0.2)](#opentelemetry-v02)
- [Prometheus & Grafana (v0.3)](#prometheus--grafana-v03)
- [Comparison Matrix](#comparison-matrix)
- [Enterprise Features](#enterprise-features)
- [Troubleshooting](#troubleshooting)

---

## Overview

### Why Observability Matters

LLM-based workflows are expensive, unpredictable, and hard to debug:
- **Costs**: Each API call costs money (tokens × pricing). Without tracking, budgets spiral.
- **Debugging**: When workflows fail, you need to see prompts, responses, and retries.
- **Optimization**: DSPy optimization requires baseline metrics to improve prompts.
- **Production**: SLA monitoring, error rates, and performance trends are essential.

### Three-Tier Strategy

Configurable Agents uses a complementary observability stack:

```
┌─────────────────────────────────────────┐
│  Tier 1: MLFlow (LLM Experiments)      │  ← v0.1
│  Track prompts, tokens, costs           │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Tier 2: OpenTelemetry (Tracing)       │  ← v0.2
│  Latency breakdown, bottlenecks         │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Tier 3: Prometheus (Infrastructure)   │  ← v0.3
│  SLA monitoring, alerting, dashboards   │
└─────────────────────────────────────────┘
```

**Each tier serves a distinct purpose**:
- **MLFlow**: "Why did this cost $5?" → View token breakdown, prompts
- **OTEL**: "Where are the 2s of latency?" → Span waterfall
- **Prometheus**: "Is the service meeting 99.9% uptime?" → Real-time dashboards

This guide covers all three tiers, with v0.1 focus on MLFlow.

---

## Quick Start

### 1. Install MLFlow 3.9+

```bash
pip install mlflow>=3.9.0
```

(Already included if you installed `configurable-agents` with `pip install -e .`)

### 2. Enable in Workflow Config

```yaml
# workflow.yaml
schema_version: "1.0"
flow:
  name: article_writer
  version: "1.0.0"

config:
  llm:
    provider: google
    model: gemini-1.5-flash

  observability:
    mlflow:
      enabled: true
      tracking_uri: "sqlite:///mlflow.db"  # Recommended (default)
      async_logging: true  # NEW: Zero-latency production mode

state:
  fields:
    topic: {type: str, required: true}

nodes:
  - id: write
    prompt: "Write an article about {topic}"
    outputs: [article]
    output_schema:
      type: object
      fields:
        - {name: article, type: str}

edges:
  - {from: START, to: write}
  - {from: write, to: END}
```

### 3. Run Workflow

```bash
configurable-agents run workflow.yaml --input topic="AI Safety"
```

**Output**:
```
✓ Validating workflow...
✓ Executing workflow...
✓ MLflow 3.9 auto-instrumentation enabled
✓ Experiment: configurable_agents (ID: 1)

Results:
{
  "article": "AI Safety is a field of research..."
}

Workflow cost: $0.000450, 600 tokens

MLFlow UI: mlflow ui --backend-store-uri sqlite:///mlflow.db
```

### 4. View Traces

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Open http://localhost:5000 in your browser.

**What you'll see** (MLflow 3.9 GenAI Dashboard):
- **Trace Timeline**: Visual span waterfall for each workflow
- **Token Usage**: Automatic token tracking per node
- **Cost Breakdown**: Per-node and total costs
- **Metrics**: Duration, tokens, cost, retries
- **Artifacts**: Cost summary JSON

---

## MLFlow 3.9 Integration

### What's New in MLflow 3.9?

**MLflow 3.9** (January 2026) introduced major improvements for GenAI observability:

✅ **Automatic tracing** via `mlflow.langchain.autolog()` - no manual instrumentation
✅ **Span/trace model** - cleaner hierarchy than nested runs
✅ **Auto token tracking** - captures usage from LLM responses
✅ **GenAI dashboard** - specialized UI for LLM workflows
✅ **Async logging** - zero-latency production mode
✅ **SQLite default** - better performance than deprecated file:// backend

See [docs/MLFLOW_39_FEATURES.md](MLFLOW_39_FEATURES.md) for comprehensive feature documentation.

### Architecture (MLflow 3.9)

```
Workflow Execution
      ↓
mlflow.langchain.autolog()  ← Automatic instrumentation
      ↓
@mlflow.trace decorator
      ↓
Traces & Spans (automatic)
      ↓
sqlite:///mlflow.db  (default)
├── traces/
│   └── trace_abc123.../
│       ├── spans/  (workflow, nodes)
│       └── token_usage/  (automatic)
```

**Key Difference from Pre-3.9**:
- ❌ Old: Manual context managers (`with tracker.track_workflow()`)
- ✅ New: Automatic tracing (just enable MLflow)

### What is MLFlow?

**MLFlow** is an open-source platform for tracking machine learning experiments.

**Why we chose it** (still valid with 3.9):
- ✅ LLM-native (GenAI dashboard, token tracking)
- ✅ Open-source (no vendor lock-in)
- ✅ Self-hosted (free forever)
- ✅ Scales (SQLite → PostgreSQL → S3 → Databricks)
- ✅ DSPy-ready (v0.3 optimization)
- ✅ **NEW**: Automatic tracing (no manual instrumentation)

**Alternatives considered** (and why we rejected them):
- LangSmith: SaaS-only, vendor lock-in
- Weights & Biases: ML-focused, not LLM-native
- Custom solution: Reinventing the wheel

See [ADR-011](adr/ADR-011-mlflow-observability.md) and [ADR-018](adr/ADR-018-mlflow-39-upgrade-genai-tracing.md) for detailed rationale.

### Storage Backends

**Recommended: SQLite** (default in MLflow 3.9):
```yaml
config:
  observability:
    mlflow:
      tracking_uri: "sqlite:///mlflow.db"  # Recommended
```

**Pros**:
- Zero setup (works immediately)
- Better performance than file://
- Works offline
- Handles concurrent access well
- Single-file database (easy backup)

**Cons**:
- Not suitable for high-concurrency production (use PostgreSQL)
- File-based (not cloud-native)

**Still Supported: File Backend** (deprecated):
```yaml
tracking_uri: "sqlite:///mlflow.db"  # Default — recommended
```

**Remote Backends** (team collaboration, production):
```yaml
# PostgreSQL (team collaboration)
tracking_uri: "postgresql://user:pass@db.example.com/mlflow"

# AWS S3 (cloud storage)
tracking_uri: "s3://company-mlflow/workflows"

# Databricks (managed, enterprise)
tracking_uri: "databricks://workspace"
```

---

## Configuration Reference

### Full Schema (MLflow 3.9)

```yaml
config:
  observability:
    mlflow:
      # Core settings
      enabled: true                          # Enable tracking (default: false)
      tracking_uri: "sqlite:///mlflow.db"    # Storage backend (default)
      experiment_name: "my_workflows"        # Group related runs

      # MLflow 3.9 features
      async_logging: true                    # Async trace logging (default: true)

      # Artifact control
      log_artifacts: true                    # Save artifacts (default: true)
      artifact_level: "standard"             # minimal | standard | full

      # Optional
      run_name: null                         # Custom run naming (optional)
```

### Field Descriptions

**enabled** (bool, default: `false`):
- Master switch for observability
- If disabled, no performance overhead
- MLflow 3.9 auto-tracing activates when enabled

**tracking_uri** (str, default: `"sqlite:///mlflow.db"`):
- Where to store tracking data
- **Recommended**: `sqlite:///mlflow.db` (default in 3.9)
- **Deprecated**: `file://./mlruns` (still works for backward compatibility, but not recommended)
- **Remote**: `postgresql://...`, `s3://...`, `databricks://...`

**experiment_name** (str, default: `"configurable_agents"`):
- Logical grouping for runs
- Use meaningful names: `"production"`, `"testing"`, `"team_data_science"`
- All runs in same experiment are comparable

**async_logging** (bool, default: `true`):
- **NEW in MLflow 3.9**: Enable async trace logging
- Zero-latency production mode (non-blocking I/O)
- 20+ concurrent workers, 2000-item queue, automatic retry
- Traces appear in UI with < 1s delay
- Set to `false` for tests or if you need synchronous guarantees

**log_artifacts** (bool, default: `true`):
- Save artifacts (cost summaries, traces)
- Disable to reduce storage usage
- Even when disabled, metrics are still logged

**artifact_level** (str, default: `"standard"`):
- Control artifact verbosity:
  - `"minimal"`: Only cost summary
  - `"standard"`: Cost summary + basic traces
  - `"full"`: Everything (prompts, responses, intermediate outputs)
- Higher levels = more storage, better debugging

**run_name** (str, optional):
- Template for individual run names
- If not specified, MLFlow generates timestamp-based names
- Example: `"workflow_{workflow_name}_{timestamp}"`

### Enterprise Hooks (v0.2+)

**retention_days** (int, optional):
- Automatically delete runs older than N days
- Useful for compliance (GDPR, data retention policies)
- Example: `retention_days: 90` (keep 3 months)
- Not enforced in v0.1 (design hook)

**redact_pii** (bool, default: `false`):
- Sanitize personally identifiable information before logging
- Uses regex/NER to detect PII in inputs/outputs
- Example: Email addresses, phone numbers, SSNs
- Not enforced in v0.1 (design hook)

**Note**: Enterprise hooks are placeholders for future features.

---

## What Gets Tracked

### MLflow 3.9 Automatic Tracking

**MLflow 3.9 automatically captures** (via `mlflow.langchain.autolog()`):
- ✅ Workflow execution traces (entire workflow as root span)
- ✅ Node execution spans (each node as child span)
- ✅ Token usage (from LLM responses, per span)
- ✅ Model names (gemini-1.5-flash, etc.)
- ✅ Execution timestamps and durations
- ✅ LLM tool calls (if tools used)

**We additionally compute**:
- ✅ Cost breakdown (per node, using token usage)
- ✅ Workflow metrics (total tokens, total cost)
- ✅ Cost summary artifact (JSON with detailed breakdown)

### Trace Structure (MLflow 3.9 Span Model)

```
Trace: workflow_article_writer
├─ Span Type: WORKFLOW
├─ Attributes:
│  ├─ workflow_name: "article_writer"
│  ├─ workflow_version: "1.0.0"
│  └─ node_count: 2
├─ Spans (children):
│  ├─ Span: research_node
│  │  ├─ Span Type: AGENT
│  │  ├─ Attributes:
│  │  │  ├─ ai.model.name: "gemini-1.5-flash"
│  │  │  └─ mlflow.chat.tokenUsage:  ← Automatic!
│  │  │     ├─ prompt_tokens: 150
│  │  │     ├─ completion_tokens: 500
│  │  │     └─ total_tokens: 650
│  │  └─ Duration: 2100ms
│  └─ Span: write_node
│     ├─ Span Type: AGENT
│     ├─ Attributes:
│     │  ├─ ai.model.name: "gemini-1.5-flash"
│     │  └─ mlflow.chat.tokenUsage:  ← Automatic!
│     │     ├─ prompt_tokens: 200
│     │     ├─ completion_tokens: 600
│     │     └─ total_tokens: 800
│     └─ Duration: 3000ms
```

### Workflow-Level Metrics (Logged by Framework)

**Metrics** (numeric):
- `total_cost_usd`: `0.0023` - Total workflow cost
- `total_tokens`: `1450` - Total tokens across all nodes
- `prompt_tokens`: `350` - Input tokens
- `completion_tokens`: `1100` - Output tokens
- `node_count`: `2` - Number of nodes executed

**Artifacts** (files):
- `cost_summary.json`: Detailed cost breakdown per node

### Per-Node Tracking (Automatic via Spans)

**Captured automatically by MLflow 3.9**:
- Span name: Node ID
- Span type: `AGENT`
- Start/end timestamps
- Duration (nanoseconds)
- Token usage in `mlflow.chat.tokenUsage` attribute
- Model name in `ai.model.name` attribute
- Tool calls in `mlflow.tool` attributes (if tools used)

**Computed by framework**:
- Per-node cost (from token usage + pricing table)
- Per-node duration (milliseconds)

### Example Cost Summary Artifact

```json
{
  "trace_id": "abc123...",
  "workflow_name": "article_writer",
  "workflow_version": "1.0.0",
  "total_tokens": {
    "prompt_tokens": 350,
    "completion_tokens": 1100,
    "total_tokens": 1450
  },
  "total_cost_usd": 0.0023,
  "node_breakdown": {
    "research_node": {
      "tokens": {
        "prompt_tokens": 150,
        "completion_tokens": 500,
        "total_tokens": 650
      },
      "cost_usd": 0.0015,
      "model": "gemini-1.5-flash",
      "duration_ms": 2100
    },
    "write_node": {
      "tokens": {
        "prompt_tokens": 200,
        "completion_tokens": 600,
        "total_tokens": 800
      },
      "cost_usd": 0.0020,
      "model": "gemini-1.5-flash",
      "duration_ms": 3000
    }
  }
}
```

### What's Different from Pre-3.9?

**Old (Pre-3.9)**: Nested MLflow runs
- Workflow = Parent run
- Nodes = Nested child runs
- Manual tracking code required

**New (3.9+)**: Trace & Span model
- Workflow = Root span (type: WORKFLOW)
- Nodes = Child spans (type: AGENT)
- Automatic tracking via `autolog()`
- Better visualization in MLflow UI

---

## Cost Tracking

### Token Pricing

Built-in pricing tables for automatic cost calculation (as of January 2025):

```python
# configurable_agents/observability/cost_estimator.py
GEMINI_PRICING = {
    "gemini-3-pro": {"input": 0.002, "output": 0.012},              # $/1K tokens
    "gemini-3-flash": {"input": 0.0005, "output": 0.003},
    "gemini-2.5-pro": {"input": 0.00125, "output": 0.010},
    "gemini-2.5-flash": {"input": 0.0003, "output": 0.0025},
    "gemini-2.5-flash-lite": {"input": 0.0001, "output": 0.0004},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-1.5-flash-8b": {"input": 0.0000375, "output": 0.00015},
    "gemini-1.0-pro": {"input": 0.0005, "output": 0.0015},
    # More providers added in v0.2+ (OpenAI, Anthropic, etc.)
}
```

**Calculation**:
```
cost_usd = (input_tokens / 1000 * input_price) + (output_tokens / 1000 * output_price)
```

### Viewing Costs

**In MLFlow UI**:
1. Open http://localhost:5000
2. Click on a run
3. Scroll to "Metrics" section
4. See `cost_usd` and `cost_per_node_avg`

**Via Python**:
```python
import mlflow

client = mlflow.tracking.MlflowClient()

# Get all runs in experiment
runs = client.search_runs(experiment_ids=["0"])

# Calculate total cost
total_cost = sum(
    run.data.metrics.get("cost_usd", 0)
    for run in runs
)

print(f"Total spent: ${total_cost:.4f}")
```

### Monthly Cost Report

See `examples/notebooks/cost_report.ipynb` for a Jupyter notebook that:
- Queries all runs
- Aggregates costs by workflow, model, time period
- Exports to CSV
- Visualizes trends (matplotlib/seaborn)

**Example output**:
```
Total Cost (January 2026): $45.23

By Workflow:
- article_writer: $23.45 (52%)
- data_analyzer: $15.30 (34%)
- summarizer: $6.48 (14%)

By Model:
- gemini-1.5-flash: $38.90 (86%)
- gemini-1.5-pro: $6.33 (14%)
```

---

## Docker Integration

### MLFlow UI in Container

When deploying workflows as Docker containers, MLFlow UI runs inside:

**Deployment**:
```bash
configurable-agents deploy workflow.yaml
```

**Container exposes two ports**:
- **8000**: FastAPI server (workflow API)
- **5000**: MLFlow UI (observability dashboard)

**Architecture**:
```dockerfile
CMD mlflow ui --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///app/mlflow.db & \
    python server.py
```

### Accessing MLFlow UI

**Local deployment**:
```bash
# Deploy
configurable-agents deploy workflow.yaml

# Access MLFlow UI
open http://localhost:5000
```

**Remote deployment** (v0.2+):
```bash
# Deploy to remote server
configurable-agents deploy workflow.yaml --platform ecs

# Access via public URL
open https://workflow.example.com:5000
```

### Persistent Traces

**docker-compose.yml**:
```yaml
services:
  workflow:
    image: article_writer:latest
    ports:
      - "8000:8000"
      - "5000:5000"
    volumes:
      - ./mlflow.db:/app/mlflow.db  # Traces persist across restarts
```

**Benefits**:
- Traces survive container restarts
- Easy backup (just copy `./mlflow.db` file)
- Can query from host machine

---

## Querying & Reporting

### CLI Cost Reporting

Configurable Agents provides a built-in CLI command for querying and reporting workflow costs:

**Basic Usage**:
```bash
# View all costs
configurable-agents report costs

# Last 7 days with breakdown
configurable-agents report costs --period last_7_days --breakdown

# Export to CSV
configurable-agents report costs --output costs.csv --format csv

# Custom date range
configurable-agents report costs \
  --start-date 2026-01-01 \
  --end-date 2026-01-31 \
  --breakdown
```

**Available Options**:
- `--tracking-uri` - MLFlow URI (default: sqlite:///mlflow.db)
- `--experiment` - Filter by experiment name
- `--workflow` - Filter by workflow name
- `--period` - Predefined periods: today, yesterday, last_7_days, last_30_days, this_month
- `--start-date` / `--end-date` - Custom date range (ISO format: YYYY-MM-DD)
- `--status` - Filter by success/failure
- `--breakdown` - Show breakdown by workflow and model
- `--aggregate-by` - Aggregate by daily/weekly/monthly
- `-o, --output` - Export to file
- `--format` - json or csv (default: json)

**Example Output**:
```
Cost Summary:
  Total Cost:        $0.045123
  Total Runs:        15
  Successful:        14
  Failed:            1
  Total Tokens:      45,000
  Avg Cost/Run:      $0.003008
  Avg Tokens/Run:    3000

Cost by Workflow:
  article_writer               $0.035000
  summarizer                   $0.010123

Cost by Model:
  gemini-1.5-flash            $0.030000
  gemini-2.5-flash            $0.015123
```

### MLFlow Python API

```python
import mlflow

# Connect to tracking server
mlflow.set_tracking_uri("sqlite:///mlflow.db")

# Get experiment
experiment = mlflow.get_experiment_by_name("my_workflows")

# Search runs
client = mlflow.tracking.MlflowClient()
runs = client.search_runs(
    experiment_ids=[experiment.experiment_id],
    filter_string="metrics.cost_usd > 0.01",  # Filter by cost
    order_by=["start_time DESC"],            # Most recent first
    max_results=100
)

# Extract data
for run in runs:
    print(f"Run: {run.info.run_id}")
    print(f"  Duration: {run.data.metrics['duration_seconds']:.2f}s")
    print(f"  Cost: ${run.data.metrics['cost_usd']:.4f}")
    print(f"  Status: {'Success' if run.data.metrics['status'] == 1 else 'Failed'}")
```

### Common Queries

**Total cost this month**:
```python
import mlflow
from datetime import datetime, timedelta

client = mlflow.tracking.MlflowClient()

# Get runs from last 30 days
cutoff = datetime.now() - timedelta(days=30)
cutoff_ms = int(cutoff.timestamp() * 1000)

runs = client.search_runs(
    experiment_ids=["0"],
    filter_string=f"attributes.start_time >= {cutoff_ms}"
)

total = sum(r.data.metrics.get("cost_usd", 0) for r in runs)
print(f"Cost (last 30 days): ${total:.2f}")
```

**Average duration per workflow**:
```python
from collections import defaultdict

durations = defaultdict(list)

for run in runs:
    workflow_name = run.data.params.get("workflow_name")
    duration = run.data.metrics.get("duration_seconds")
    if workflow_name and duration:
        durations[workflow_name].append(duration)

for workflow, times in durations.items():
    avg = sum(times) / len(times)
    print(f"{workflow}: {avg:.2f}s average")
```

**Failed runs (for debugging)**:
```python
failed_runs = client.search_runs(
    experiment_ids=["0"],
    filter_string="metrics.status = 0"  # 0 = failed
)

for run in failed_runs:
    print(f"Failed: {run.info.run_id}")
    # Download error.txt artifact
    client.download_artifacts(run.info.run_id, "error.txt", ".")
```

### Export to CSV

```python
import pandas as pd
import mlflow

client = mlflow.tracking.MlflowClient()
runs = client.search_runs(experiment_ids=["0"])

data = []
for run in runs:
    data.append({
        "run_id": run.info.run_id,
        "workflow": run.data.params.get("workflow_name"),
        "duration": run.data.metrics.get("duration_seconds"),
        "cost": run.data.metrics.get("cost_usd"),
        "tokens_in": run.data.metrics.get("total_input_tokens"),
        "tokens_out": run.data.metrics.get("total_output_tokens"),
        "timestamp": run.info.start_time,
    })

df = pd.DataFrame(data)
df.to_csv("mlflow_runs.csv", index=False)
print("Exported to mlflow_runs.csv")
```

---

## Best Practices

### When to Enable Observability

**Always enable**:
- Production workflows (cost tracking essential)
- Development/debugging (view prompts, responses)
- DSPy optimization (need baseline metrics)

**Consider disabling**:
- High-throughput batch jobs (I/O overhead from artifact logging)
- Cost-sensitive scenarios (MLFlow adds ~50-100ms per run)

**Note**: In v0.1, observability is enabled/disabled at the workflow level. Future versions may add fine-grained controls for artifact logging and node-level overrides.

### Storage Management

**SQLite storage grows unbounded** → Monitor disk usage:

```bash
du -sh ./mlflow.db
# 2.3G	./mlflow.db
```

**Manual cleanup** (via MLflow API):
```python
import mlflow
client = mlflow.tracking.MlflowClient()
# Delete old runs programmatically (see below)
```

**Programmatic cleanup** (v0.2+):
```python
import mlflow
from datetime import datetime, timedelta

client = mlflow.tracking.MlflowClient()
cutoff = datetime.now() - timedelta(days=90)

runs = client.search_runs(experiment_ids=["0"])
for run in runs:
    if run.info.start_time < cutoff.timestamp() * 1000:
        client.delete_run(run.info.run_id)
```

### Security Considerations

**PII in logs**:
- MLFlow logs inputs/outputs as-is (no sanitization in v0.1)
- User responsibility to avoid logging sensitive data
- Consider `redact_pii: true` in v0.2+ (when implemented)

**Example**: Don't log credit card numbers, SSNs, passwords.

**Workaround**:
```python
# Pre-process inputs before running
inputs = {
    "query": "Customer inquiry about account 1234",
    # "credit_card": "4111-1111-1111-1111"  # DON'T log this
}
```

**Access control**:
- SQLite storage: Unix file permissions (`chmod 600 mlflow.db`)
- Remote storage: PostgreSQL user permissions, S3 bucket policies

---

## Migration from Pre-3.9

### For Config File Users (Most Users)

**Good news**: No changes required! Your configs continue to work.

MLflow 3.9 is **backward compatible** for config files:

```yaml
# This config works with both pre-3.9 and 3.9+
config:
  observability:
    mlflow:
      enabled: true
```

**Optional improvements**:
1. Switch to SQLite backend: `tracking_uri: "sqlite:///mlflow.db"`
2. Enable async logging: `async_logging: true`

See [docs/MLFLOW_39_USER_MIGRATION_GUIDE.md](MLFLOW_39_USER_MIGRATION_GUIDE.md) for detailed migration instructions.

### For Python API Users

If you were using the Python API directly (rare), APIs have changed:

**Removed**:
- ❌ `tracker.track_workflow()` - No longer needed (automatic)
- ❌ `tracker.track_node()` - No longer needed (automatic)
- ❌ `tracker.log_node_metrics()` - Captured automatically
- ❌ `tracker.finalize_workflow()` - No longer needed

**New APIs**:
- ✅ `tracker.get_trace_decorator(name, **attrs)` - Get @mlflow.trace decorator
- ✅ `tracker.get_workflow_cost_summary()` - Get cost breakdown from traces
- ✅ `tracker.log_workflow_summary(cost_summary)` - Log metrics to MLflow

**Migration example**:

```python
# OLD (Pre-3.9) - Don't use
with tracker.track_workflow(inputs):
    with tracker.track_node("node1", "gemini-1.5-flash"):
        result = llm.invoke(prompt)
        tracker.log_node_metrics(tokens=100, ...)
    tracker.finalize_workflow(state, status="success")

# NEW (3.9+) - Just enable tracker
tracker = MLFlowTracker(config, workflow_config)

# Define traced function
@tracker.get_trace_decorator("workflow", workflow_name="test")
def execute():
    return graph.invoke(state)

# Execute (tracing happens automatically)
result = execute()

# Get cost summary
cost_summary = tracker.get_workflow_cost_summary()
tracker.log_workflow_summary(cost_summary)
```

### Data Migration

**Old traces are preserved**:
- Old file-based runs in `file://./mlruns` remain accessible if present
- MLflow 3.9 defaults to `sqlite:///mlflow.db` for new traces
- Historical data is not lost

**New traces use new format**:
- Span/trace model (not nested runs)
- Stored in same backend
- Queries work across both formats

**No action required**: Old and new traces coexist in same backend.

---

## OpenTelemetry (v0.2)

**Status**: Planned for v0.2 (Q2 2026)

### Why Add OpenTelemetry?

MLFlow answers "What happened?" (post-run analysis).
OTEL answers "Where are the bottlenecks?" (real-time tracing).

### Architecture

```
Workflow Execution
      ↓
OpenTelemetry Instrumentation
      ↓
Traces (spans)
      ↓
Jaeger / Tempo / Honeycomb (backend)
      ↓
Span Waterfall Visualization
```

### Example Span Waterfall

```
Workflow: article_writer [5.2s]
├─ Node: research [2.1s]
│  ├─ LLM call [1.8s]
│  │  ├─ Token encoding [50ms]
│  │  ├─ API request [1.6s]  ← BOTTLENECK
│  │  └─ Response parsing [150ms]
│  └─ Tool: serper_search [300ms]
├─ Node: write [3.0s]
│  └─ LLM call [2.9s]
└─ State update [100ms]
```

### Configuration (v0.2)

```yaml
config:
  observability:
    mlflow:
      enabled: true
    opentelemetry:  # NEW in v0.2
      enabled: true
      exporter: jaeger
      endpoint: "http://localhost:14268/api/traces"
      service_name: "configurable-agents"
      sampling_rate: 1.0  # 100% (use 0.01 for 1% in production)
```

### Backends

- **Jaeger** (free, self-hosted): `docker run -p 16686:16686 jaegertracing/all-in-one`
- **Grafana Tempo** (free, self-hosted): Integrates with Grafana
- **Honeycomb** (paid SaaS): Best UX, powerful querying

### Use Cases

- "Why is this workflow slow?" → View span waterfall
- "Which LLM API is fastest?" → Compare span durations
- "How long does validation take?" → Check validation span

See [ADR-014](adr/ADR-014-three-tier-observability-strategy.md) for detailed design.

---

## Prometheus & Grafana (v0.3)

**Status**: Planned for v0.3 (Q3 2026)

### Why Add Prometheus?

MLFlow + OTEL answer "What happened in this run?"
Prometheus answers "Is the service healthy right now?"

### Architecture

```
FastAPI Server
      ↓
/metrics endpoint (Prometheus format)
      ↓
Prometheus (scrapes every 15s)
      ↓
Grafana (dashboards, alerts)
```

### Metrics Exposed

```python
# Counters
workflow_runs_total{workflow="article_writer", status="success"} 1523
llm_tokens_total{model="gemini-1.5-flash", type="input"} 450230
llm_cost_usd{model="gemini-1.5-flash"} 23.45

# Histograms
workflow_duration_seconds_bucket{workflow="article_writer", le="5.0"} 1200
workflow_duration_seconds_bucket{workflow="article_writer", le="10.0"} 1500

# Gauges
active_workflows 5
```

### Grafana Dashboards

Pre-built panels (JSON exports provided):
- **Workflow Performance**: Throughput, latency (p50/p95/p99), error rate
- **LLM Usage**: Tokens per hour, cost per day, model distribution
- **System Health**: CPU, memory, request queue

### Alerting Rules

```yaml
# prometheus.yml
groups:
  - name: sla_violations
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, workflow_duration_seconds_bucket) > 10
        for: 5m
        annotations:
          summary: "p95 latency > 10s"

      - alert: HighErrorRate
        expr: rate(workflow_runs_total{status="error"}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "Error rate > 10%"
```

**Integrations**:
- PagerDuty (oncall alerting)
- Slack (team notifications)
- Email (reports)

### Configuration (v0.3)

```yaml
config:
  observability:
    prometheus:  # NEW in v0.3
      enabled: true
      port: 9090
      path: "/metrics"
```

See [ADR-014](adr/ADR-014-three-tier-observability-strategy.md) for detailed design.

---

## Comparison Matrix

| Question | Use This | Why |
|----------|----------|-----|
| "Why did this cost $5?" | MLFlow | View token breakdown per node |
| "What did the prompt look like?" | MLFlow | Artifacts: prompt.txt |
| "Where are the 2s of latency?" | OTEL (v0.2) | Span waterfall shows breakdown |
| "Which API call is slowest?" | OTEL (v0.2) | Compare span durations |
| "Is the service meeting SLA?" | Prometheus (v0.3) | Real-time metrics, alerts |
| "How much did we spend this month?" | MLFlow | Aggregate cost_usd across runs |

| Feature | MLFlow | OpenTelemetry | Prometheus |
|---------|--------|---------------|------------|
| **Purpose** | LLM experiments | Latency tracing | Infrastructure monitoring |
| **Granularity** | Per run, per node | Per span (operation) | Aggregated (time series) |
| **Retention** | Forever (user-managed) | 7-30 days | 15 days (longer with Thanos) |
| **Visualization** | MLFlow UI | Jaeger waterfall | Grafana dashboards |
| **Alerting** | No | No | Yes (Alertmanager) |
| **DSPy Support** | Yes | Indirect | No |
| **Cost Tracking** | Yes (per run) | No | Yes (aggregated) |
| **Real-Time** | No (post-run) | Near real-time | Real-time (15s lag) |

---

## Enterprise Features

### Multi-Tenancy (v0.2+)

**Per-customer experiments**:
```yaml
# customer_a.yaml
config:
  observability:
    mlflow:
      experiment_name: "customer_a_production"

# customer_b.yaml
config:
  observability:
    mlflow:
      experiment_name: "customer_b_production"
```

**Isolated storage**:
```yaml
config:
  observability:
    mlflow:
      tracking_uri: "s3://company-mlflow/customer_a/"  # Per-tenant prefix
```

### User Attribution

**Track who ran what**:
```python
import mlflow

mlflow.set_tag("user_id", "alice@company.com")
mlflow.set_tag("team", "data-science")
mlflow.set_tag("cost_center", "R&D")
```

**Query by user**:
```python
runs = client.search_runs(
    experiment_ids=["0"],
    filter_string="tags.user_id = 'alice@company.com'"
)
```

### Data Retention Policies (v0.2+)

**Automatic cleanup**:
```yaml
config:
  observability:
    mlflow:
      retention_days: 90  # Delete runs older than 90 days
```

**Compliance** (GDPR, HIPAA):
- Ensure old data is purged
- Document retention policy in privacy policy

### PII Redaction (v0.2+)

**Automatic sanitization**:
```yaml
config:
  observability:
    mlflow:
      redact_pii: true  # Sanitize before logging
```

**Implementation** (future):
- Regex patterns (emails, phones, SSNs)
- NER models (detect PII with spaCy/transformers)
- Allowlist exceptions (company emails OK)

---

## Troubleshooting

### MLFlow UI Not Showing Runs

**Check tracking URI**:
```bash
# In workflow config
config:
  observability:
    mlflow:
      tracking_uri: "sqlite:///mlflow.db"  # Is this correct?

# Start UI from same directory
cd /path/to/project
mlflow ui
```

**Check file permissions**:
```bash
ls -la mlflow.db
# Should be readable/writable by your user
```

### High Disk Usage

**Check storage**:
```bash
du -sh ./mlflow.db
# 5.2G	./mlflow.db
```

**Solution**: Delete old runs or move to remote backend.

### Missing Metrics

**Check if observability is enabled**:
```yaml
config:
  observability:
    mlflow:
      enabled: true  # Must be true
```

**Check logs**:
```bash
configurable-agents run workflow.yaml --verbose
# Look for: "MLFlow tracking enabled"
```

### Performance Overhead

**Symptoms**: Workflows 20-30% slower with MLFlow enabled.

**Cause**: Artifact logging (saving inputs/outputs/prompts/responses to disk).

**Solution**: Consider disabling observability for high-throughput batch jobs, or wait for v0.2 which will add granular artifact control options.

### Docker Container MLFlow UI Not Accessible

**Check ports**:
```bash
docker ps
# Should show: 0.0.0.0:5000->5000/tcp
```

**Fix**: Ensure MLFlow UI is bound to 0.0.0.0 (not 127.0.0.1):
```dockerfile
CMD mlflow ui --host 0.0.0.0 --port 5000
```

---

## Next Steps

- **Enable observability**: Add `config.observability.mlflow.enabled: true` to your workflow
- **Run a workflow**: See traces in MLFlow UI
- **Track costs**: Query `cost_usd` metric for budget monitoring
- **Plan for v0.2**: Add OpenTelemetry for latency debugging
- **Plan for v0.3**: Add Prometheus for production monitoring

---

## Resources

- **MLFlow Documentation**: https://mlflow.org/docs/latest/index.html
- **MLFlow LangChain Integration**: https://mlflow.org/docs/latest/llms/langchain/index.html
- **ADR-011**: MLFlow for Observability (internal design doc)
- **ADR-014**: Three-Tier Observability Strategy (internal design doc)
- **Example Notebook**: `examples/notebooks/cost_report.ipynb`

---

**Last Updated**: 2026-02-02 (MLflow 3.9 migration)
