# Observability Guide

**Comprehensive guide to tracking, monitoring, and optimizing your LLM workflows**

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [MLFlow Integration (v0.1)](#mlflow-integration-v01)
- [Configuration Reference](#configuration-reference)
- [What Gets Tracked](#what-gets-tracked)
- [Cost Tracking](#cost-tracking)
- [Docker Integration](#docker-integration)
- [Querying & Reporting](#querying--reporting)
- [Best Practices](#best-practices)
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

### 1. Install MLFlow

```bash
pip install mlflow
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

  observability:         # NEW
    mlflow:
      enabled: true      # Enable tracking

state:
  fields:
    topic: {type: str, required: true}

nodes:
  - id: write
    prompt: "Write an article about {state.topic}"
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
✓ MLFlow tracking enabled (file://./mlruns)
✓ MLFlow run ID: a3f9b2c1d4e5678901234567

Results:
{
  "article": "AI Safety is a field of research..."
}

MLFlow UI: mlflow ui
```

### 4. View Traces

```bash
mlflow ui
```

Open http://localhost:5000 in your browser.

**What you'll see**:
- List of all workflow runs
- Metrics: duration, tokens, cost
- Parameters: workflow name, model, temperature
- Artifacts: inputs, outputs, prompts, responses

---

## MLFlow Integration (v0.1)

### Architecture

```
Workflow Execution
      ↓
MLFlow Tracking (if enabled)
      ↓
file://./mlruns/
├── experiments/
│   └── 0/
│       └── a3f9b2c1d4e5.../
│           ├── params/
│           ├── metrics/
│           └── artifacts/
```

### What is MLFlow?

**MLFlow** is an open-source platform for tracking machine learning experiments.

**Why we chose it**:
- ✅ LLM-native (tracks prompts, tokens, costs)
- ✅ Open-source (no vendor lock-in)
- ✅ Self-hosted (free forever)
- ✅ Scales (file → PostgreSQL → S3 → Databricks)
- ✅ DSPy-ready (v0.3 optimization)

**Alternatives considered** (and why we rejected them):
- LangSmith: SaaS-only, vendor lock-in
- Weights & Biases: ML-focused, not LLM-native
- Custom solution: Reinventing the wheel

See [ADR-011](adr/ADR-011-mlflow-observability.md) for detailed rationale.

### Storage Backends

**v0.1: Local File Storage** (default):
```yaml
config:
  observability:
    mlflow:
      tracking_uri: "file://./mlruns"  # Relative path
      # or: "file:///absolute/path/mlruns"
```

**Pros**:
- Zero setup (works immediately)
- Works offline
- Simple debugging (files on disk)

**Cons**:
- Not suitable for team collaboration
- Doesn't scale to high throughput

**v0.2+: Remote Backends**:
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

### Full Schema

```yaml
config:
  observability:
    mlflow:
      enabled: true                          # Enable tracking (default: false)
      tracking_uri: "file://./mlruns"        # Storage backend
      experiment_name: "my_workflows"        # Group related runs
      run_name: null                         # Custom run naming (optional)
```

**Note**: In v0.1, the config is minimal. Future versions may add options for artifact control, retention policies, and PII redaction.

### Field Descriptions

**enabled** (bool, default: `false`):
- Master switch for observability
- If disabled, no performance overhead

**tracking_uri** (str, default: `"file://./mlruns"`):
- Where to store tracking data
- Local: `file://./mlruns`
- Remote: `postgresql://...`, `s3://...`, `databricks://...`

**experiment_name** (str, default: `"configurable_agents"`):
- Logical grouping for runs
- Use meaningful names: `"production"`, `"testing"`, `"team_data_science"`

**run_name** (str, optional):
- Template for individual run names
- If not specified, MLFlow generates timestamp-based names

### Enterprise Hooks (v0.2+)

**retention_days** (int, optional):
- Automatically delete runs older than N days
- Useful for compliance (GDPR, data retention policies)
- Example: `retention_days: 90` (keep 3 months)

**redact_pii** (bool, default: `false`):
- Sanitize personally identifiable information before logging
- Uses regex/NER to detect PII in inputs/outputs
- Example: Email addresses, phone numbers, SSNs

**Note**: These are design hooks for future enterprise features. Not enforced in v0.1.

---

## What Gets Tracked

### Workflow-Level Metrics

**Parameters** (configuration):
- `workflow_name`: `"article_writer"`
- `workflow_version`: `"1.0.0"`
- `schema_version`: `"1.0"`
- `global_model`: `"gemini-1.5-flash"`
- `global_temperature`: `0.7`

**Metrics** (measurements):
- `duration_seconds`: `5.2`
- `total_input_tokens`: `150`
- `total_output_tokens`: `500`
- `total_cost_usd`: `0.0023`
- `node_count`: `2`
- `retry_count`: `0`
- `status`: `1` (1 = success, 0 = failure)

**Artifacts** (files):
- `inputs.json`: Workflow inputs
- `outputs.json`: Workflow outputs
- `error.json`: Error details if workflow failed

### Node-Level Traces (Nested Runs)

Each node execution creates a nested MLFlow run:

**Parameters**:
- `node_id`: `"write"`
- `node_model`: `"gemini-1.5-flash"` (if overridden)
- `tools`: `"[]"` (or list of tools used)

**Metrics**:
- `node_duration_ms`: `2100`
- `input_tokens`: `150`
- `output_tokens`: `500`
- `node_cost_usd`: `0.0015`
- `retries`: `0`

**Artifacts** (files):
- `prompt.txt`: Full resolved prompt template
- `response.txt`: Full raw LLM response (JSON formatted)

### Example Trace Hierarchy

```
Workflow: article_writer (5.2s)
├─ params: workflow_name=article_writer, global_model=gemini-1.5-flash
├─ metrics: duration_seconds=5.2, cost_usd=0.0023
├─ artifacts: inputs.json, outputs.json
└─ nested_runs:
    ├─ Node: write (2.1s)
    │   ├─ params: node_id=write, tools=[]
    │   ├─ metrics: node_duration_ms=2100, input_tokens=150, output_tokens=500
    │   └─ artifacts: prompt.txt, response.txt
```

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
CMD mlflow ui --host 0.0.0.0 --port 5000 --backend-store-uri file:///app/mlruns & \
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
      - ./mlruns:/app/mlruns  # Traces persist across restarts
```

**Benefits**:
- Traces survive container restarts
- Easy backup (just copy `./mlruns` directory)
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
- `--tracking-uri` - MLFlow URI (default: file://./mlruns)
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
mlflow.set_tracking_uri("file://./mlruns")

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

**File-based storage grows unbounded** → Monitor disk usage:

```bash
du -sh ./mlruns
# 2.3G	./mlruns
```

**Manual cleanup**:
```bash
# Delete runs older than 90 days
find ./mlruns -mtime +90 -delete
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
- File-based storage: Unix permissions (`chmod 700 mlruns`)
- Remote storage: PostgreSQL user permissions, S3 bucket policies

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
      tracking_uri: "file://./mlruns"  # Is this correct?

# Start UI from same directory
cd /path/to/project
mlflow ui
```

**Check file permissions**:
```bash
ls -la mlruns
# Should be readable/writable by your user
```

### High Disk Usage

**Check storage**:
```bash
du -sh ./mlruns
# 5.2G	./mlruns
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

**Last Updated**: 2026-01-30
