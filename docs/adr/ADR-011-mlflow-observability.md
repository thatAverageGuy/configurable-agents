# ADR-011: MLFlow for LLM Observability

**Status**: Accepted
**Date**: 2026-01-30
**Deciders**: Product team
**Related**: ADR-009 (Full Schema Day One)

---

## Context

LLM-based workflows require comprehensive observability for:
1. **Cost tracking**: Token usage, API costs (critical for budget control)
2. **Debugging**: Prompt inspection, response analysis, retry tracking
3. **Optimization**: DSPy integration (compare baseline vs optimized prompts)
4. **Production monitoring**: Success rates, latency, error patterns

Traditional APM tools (Datadog, New Relic) lack LLM-specific features. We need observability that tracks:
- Prompts (input templates and resolved values)
- LLM responses (raw outputs before validation)
- Token counts (input/output) and estimated costs
- Retries and validation failures
- Per-node execution traces

Additionally, we must support DSPy optimization workflows in v0.3, requiring:
- Experiment comparison (baseline vs optimized)
- Prompt versioning (track changes over time)
- Metric tracking (accuracy, cost, latency)

---

## Decision

**We will use MLFlow as the primary observability backend for v0.1.**

### Architecture: Local-First, Enterprise-Ready

**v0.1: File-Based Local Storage**
```yaml
config:
  observability:
    mlflow:
      enabled: true
      tracking_uri: "file://./mlruns"  # Local file storage
      experiment_name: "production_workflows"
```

**v0.2+: Remote Backend Support**
```yaml
config:
  observability:
    mlflow:
      tracking_uri: "postgresql://user:pass@host/db"  # Shared team server
      # or: "s3://bucket/mlruns"  # Cloud storage
      # or: "databricks://workspace"  # Managed MLFlow
```

### What Gets Tracked

**Workflow-Level Metrics**:
```python
mlflow.log_param("workflow_name", "article_writer")
mlflow.log_param("workflow_version", "1.0.0")
mlflow.log_param("global_model", "gemini-1.5-flash")
mlflow.log_param("global_temperature", 0.7)

mlflow.log_metric("duration_seconds", 5.2)
mlflow.log_metric("total_input_tokens", 150)
mlflow.log_metric("total_output_tokens", 500)
mlflow.log_metric("total_cost_usd", 0.0023)
mlflow.log_metric("node_count", 2)
mlflow.log_metric("retry_count", 0)
mlflow.log_metric("status", 1)  # 1=success, 0=failure

mlflow.log_dict({"topic": "AI Safety"}, "inputs.json")
mlflow.log_dict({"article": "...", "word_count": 500}, "outputs.json")
```

**Node-Level Traces (Nested Runs)**:
```python
with mlflow.start_run(run_name=f"node_{node_id}", nested=True):
    mlflow.log_param("node_id", "write")
    mlflow.log_param("node_model", "gemini-1.5-flash")
    mlflow.log_param("tools", "[]")

    mlflow.log_metric("node_duration_ms", 2100)
    mlflow.log_metric("input_tokens", 150)
    mlflow.log_metric("output_tokens", 500)
    mlflow.log_metric("retries", 0)

    mlflow.log_text("Write article about {state.topic}...", "prompt.txt")
    mlflow.log_text("Comprehensive article on AI Safety...", "response.txt")
```

### Enterprise Hooks (Design, Not Enforced)

**Data Retention** (v0.2+):
```yaml
config:
  observability:
    mlflow:
      retention_days: 90  # Auto-cleanup old runs
```

**PII Redaction** (v0.2+):
```yaml
config:
  observability:
    mlflow:
      redact_pii: true  # Sanitize inputs/outputs
```

**User Attribution** (v0.2+):
```python
mlflow.set_tag("user_id", "alice@corp.com")
mlflow.set_tag("team", "data-science")
mlflow.set_tag("cost_center", "R&D")
```

**Multi-Tenancy** (v0.2+):
```yaml
experiment_name: "{tenant_id}_workflows"  # Isolated per customer
```

---

## Alternatives Considered

### 1. LangSmith (LangChain's SaaS)

**Pros**:
- Native LangChain integration (auto-tracing)
- Excellent UI (prompt playground, comparison)
- Built for LLM workflows

**Cons**:
- ❌ **SaaS-only** (no self-hosted option)
- ❌ **Vendor lock-in** (proprietary, not open-source)
- ❌ **Cost** ($99/month for teams)
- ❌ **No DSPy support** (LangChain-specific)

**Rejected**: Vendor lock-in unacceptable for open-source project.

### 2. Weights & Biases (W&B)

**Pros**:
- Powerful experiment tracking
- Great visualizations
- Popular in ML community

**Cons**:
- ❌ **ML-focused, not LLM-native** (requires custom instrumentation)
- ❌ **SaaS-first** (self-hosted requires enterprise plan)
- ❌ **Heavier than MLFlow** (more complexity)

**Rejected**: Overkill for LLM workflows, not self-hosted by default.

### 3. Arize Phoenix

**Pros**:
- Open-source LLM observability
- LangChain integration
- Nice UI

**Cons**:
- ❌ **Newer/less mature** than MLFlow
- ❌ **No DSPy integration story**
- ❌ **Smaller ecosystem**

**Rejected**: MLFlow more mature, better DSPy fit.

### 4. OpenTelemetry + Jaeger

**Pros**:
- Distributed tracing standard
- See latency breakdown (LLM vs tool vs validation)

**Cons**:
- ❌ **Not LLM-aware** (no token tracking, cost, prompts)
- ❌ **Requires separate cost tracking system**
- ❌ **No experiment comparison**

**Deferred**: Will add OTEL in v0.2 as *complementary* tracing layer.

### 5. Prometheus + Grafana

**Pros**:
- Production monitoring (uptime, throughput, SLA)
- Real-time alerting

**Cons**:
- ❌ **Infrastructure-focused** (not experiment tracking)
- ❌ **No prompt/response storage**
- ❌ **No DSPy integration**

**Deferred**: Will add Prometheus in v0.3 for SLA monitoring.

---

## Rationale

### Why MLFlow Wins

1. **LLM-Native**: Designed for experiment tracking (perfect for prompts, costs)
2. **Open-Source**: Self-hosted, no vendor lock-in
3. **DSPy-Ready**: DSPy community uses MLFlow for optimization tracking
4. **Flexible Backend**: File → PostgreSQL → S3 → Databricks (scales with growth)
5. **Mature**: Battle-tested in ML/AI workflows
6. **Zero-Cost**: Free forever (self-hosted)

### Three-Tier Strategy (v0.1 → v0.3)

```
┌─────────────────────────────────────────┐
│  Tier 1: LLM Experiments (MLFlow)      │  ← v0.1
│  - Prompts, tokens, costs               │
│  - DSPy optimization                    │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│  Tier 2: Distributed Tracing (OTEL)    │  ← v0.2
│  - Latency breakdown                    │
│  - Span waterfall                       │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│  Tier 3: Infrastructure (Prometheus)   │  ← v0.3
│  - SLA monitoring, alerting             │
│  - Real-time dashboards                 │
└─────────────────────────────────────────┘
```

Each tier serves a distinct purpose:
- **MLFlow**: "Why did this workflow cost $5?" (experiment analysis)
- **OTEL**: "Where are the 2s of latency?" (performance debugging)
- **Prometheus**: "Is the service meeting 99.9% uptime SLA?" (production health)

### Local-First Philosophy

**v0.1 starts with file-based storage** (`file://./mlruns`):
- ✅ Zero setup (no server required)
- ✅ Works offline
- ✅ Simple debugging (files on disk)
- ✅ Git-friendly (can commit traces for testing)

**Enterprise evolution path is clear**:
- v0.1: Local files
- v0.2: PostgreSQL (team collaboration)
- v0.3: S3 (scalable, durable)
- v0.4: Databricks Managed MLFlow (SSO, RBAC, SLA)

No breaking changes - just update `tracking_uri`.

---

## Consequences

### Positive

1. **Cost visibility**: Every workflow run shows exact token/$ costs
2. **Debug-friendly**: Full prompt + response history
3. **DSPy-ready**: Optimization workflows work out of the box (v0.3)
4. **No vendor lock-in**: Self-hosted, open-source
5. **Enterprise path**: Can scale to PostgreSQL/S3/Databricks
6. **UI included**: `mlflow ui` provides dashboard (no custom UI needed)

### Negative

1. **Not real-time**: MLFlow optimized for post-run analysis (not live monitoring)
   - *Mitigation*: Add Prometheus in v0.3 for real-time metrics
2. **No distributed tracing**: Can't see span-level latency breakdown
   - *Mitigation*: Add OpenTelemetry in v0.2 for traces
3. **File storage doesn't scale**: Local files bad for high-throughput production
   - *Mitigation*: Document PostgreSQL/S3 migration in v0.2
4. **No built-in alerting**: Can't alert on high costs or errors
   - *Mitigation*: Query MLFlow API for reporting, add Prometheus alerts in v0.3

### Neutral

1. **Requires `pip install mlflow`**: Extra dependency (~40MB)
2. **Opt-in by default**: Users must enable in config (not automatic)
3. **Storage grows unbounded**: Users responsible for cleanup
   - *Enterprise hook*: `retention_days` config (v0.2+)
4. **PII risk**: Prompts/responses logged as-is
   - *User responsibility*: Document security practices
   - *Enterprise hook*: `redact_pii` config (v0.2+)

---

## Implementation Notes

### Config Schema Addition

```python
# src/configurable_agents/config/schema.py

class MLFlowConfig(BaseModel):
    """MLFlow observability configuration"""
    enabled: bool = False
    tracking_uri: str = "file://./mlruns"
    experiment_name: str = "configurable_agents"
    run_name: Optional[str] = None  # Template: "run_{timestamp}"
    log_artifacts: bool = True
    log_system_metrics: bool = False

    # Enterprise hooks (not enforced in v0.1)
    retention_days: Optional[int] = None
    redact_pii: bool = False

class ObservabilityConfig(BaseModel):
    """Observability configuration (v0.1: MLFlow only)"""
    mlflow: Optional[MLFlowConfig] = None
    # Future: opentelemetry, prometheus

class GlobalConfig(BaseModel):
    """Global workflow configuration"""
    llm: Optional[LLMConfig] = None
    execution: Optional[ExecutionConfig] = None
    observability: Optional[ObservabilityConfig] = None  # NEW
```

### Instrumentation Points

**runtime/executor.py** (workflow-level):
```python
def run_workflow_from_config(config, inputs, verbose=False):
    # Check if MLFlow enabled
    if config.config and config.config.observability and config.config.observability.mlflow:
        mlflow_config = config.config.observability.mlflow
        if mlflow_config.enabled:
            mlflow.set_tracking_uri(mlflow_config.tracking_uri)
            mlflow.set_experiment(mlflow_config.experiment_name)

            with mlflow.start_run(run_name=mlflow_config.run_name):
                # Log params, execute, log metrics
                return _run_workflow_with_mlflow(config, inputs, verbose)

    # Standard execution (no MLFlow)
    return _run_workflow_standard(config, inputs, verbose)
```

**core/node_executor.py** (node-level):
```python
def execute_node(node_config, state, global_config):
    # Check if MLFlow active
    if mlflow.active_run():
        with mlflow.start_run(run_name=f"node_{node_config.id}", nested=True):
            # Log node params, execute, log metrics
            return _execute_node_with_mlflow(node_config, state, global_config)

    # Standard execution
    return _execute_node_standard(node_config, state, global_config)
```

### Cost Tracking

```python
# observability/cost_estimator.py

GEMINI_PRICING = {
    "gemini-3-pro": {"input": 0.002, "output": 0.012},
    "gemini-3-flash": {"input": 0.0005, "output": 0.003},
    "gemini-2.5-pro": {"input": 0.00125, "output": 0.010},
    "gemini-2.5-flash": {"input": 0.0003, "output": 0.0025},
    "gemini-2.5-flash-lite": {"input": 0.0001, "output": 0.0004},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-1.5-flash-8b": {"input": 0.0000375, "output": 0.00015},
    "gemini-1.0-pro": {"input": 0.0005, "output": 0.0015},
    # Future: OpenAI, Anthropic, etc.
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost in USD"""
    pricing = GEMINI_PRICING.get(model, {"input": 0, "output": 0})
    cost = (input_tokens / 1000 * pricing["input"]) + \
           (output_tokens / 1000 * pricing["output"])
    return round(cost, 6)
```

### Docker Integration

**MLFlow UI runs inside container**:
```dockerfile
# Dockerfile (generated by deploy command)
CMD mlflow ui --host 0.0.0.0 --port 5000 --backend-store-uri file:///app/mlruns & \
    python server.py
```

**Persistent storage**:
```yaml
# docker-compose.yml
volumes:
  - ./mlruns:/app/mlruns  # Traces survive container restarts
```

---

## References

- MLFlow Documentation: https://mlflow.org/docs/latest/index.html
- MLFlow LangChain Integration: https://mlflow.org/docs/latest/llms/langchain/index.html
- DSPy + MLFlow Examples: https://github.com/stanfordnlp/dspy/discussions
- Three-Tier Observability Pattern: Internal design discussion (2026-01-30)

---

## Implementation Planning

**Status**: ⏳ Planned for v0.1 (not yet implemented)
**Related Tasks**: T-018 (MLFlow Foundation), T-019 (Instrumentation), T-020 (Cost Tracking), T-021 (Documentation)
**Target Date**: February 2026
**Estimated Effort**: 9 days (2+3+2+2)

### Implementation Tasks

**T-018: MLFlow Integration Foundation** (2 days):
- Initialize MLFlow tracking (set URI, experiment)
- Start/end workflow runs with parameters
- Log metrics and artifacts
- Handle disabled state gracefully (no-op mode)
- Test with local file backend (`file://./mlruns`)

**T-019: MLFlow Instrumentation** (3 days):
- Instrument runtime executor (workflow-level tracking)
- Instrument node executor (node-level nested runs)
- Extract token counts from LLM responses
- Log prompts and responses as artifacts
- Track execution times per node

**T-020: Cost Tracking & Reporting** (2 days):
- Implement token-to-cost conversion
- Add pricing tables for Gemini, OpenAI, Anthropic
- Calculate cumulative costs per workflow
- Log costs as MLFlow metrics
- Provide cost reporting utilities

**T-021: Observability Documentation** (2 days):
- Complete OBSERVABILITY.md (already drafted)
- Add configuration examples
- Document querying and reporting
- Best practices guide
- Troubleshooting section

### Current State

**Completed**:
- ✅ Architecture designed (this ADR)
- ✅ Documentation complete (docs/OBSERVABILITY.md - comprehensive guide)
- ✅ Schema defined (SPEC.md `config.observability.mlflow`)
- ✅ Three-tier strategy documented (ADR-014)
- ✅ T-018: MLFlow integration foundation (2026-01-31)
- ✅ T-019: MLFlow node instrumentation with automatic tracking (2026-01-31)
- ✅ T-020: Cost tracking and reporting with CLI commands (2026-01-31)
- ✅ T-021: Observability documentation (2026-01-31)
- ✅ Cost tracking implementation with 9 Gemini models
- ✅ MLFlowTracker with workflow/node-level tracking
- ✅ CLI cost reporting: `configurable-agents report costs`
- ✅ 544 unit tests passing (100% pass rate)
- ✅ Feature gate updated (MLFlow fully supported in v0.1)

**Production Ready**: MLFlow observability is fully implemented and documented for v0.1

**Next Steps**: T-022 - Docker deployment with MLFlow UI in containers

---

## Supersedes

None (first observability decision)

---

## Related Decisions

- **ADR-012**: Docker deployment architecture (MLFlow UI in container)
- **ADR-014**: Three-tier observability strategy (MLFlow + OTEL + Prometheus)
- **Future ADR**: OpenTelemetry integration (v0.2)
- **Future ADR**: Prometheus integration (v0.3)
