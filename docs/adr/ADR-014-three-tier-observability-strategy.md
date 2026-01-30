# ADR-014: Three-Tier Observability Strategy

**Status**: Accepted
**Date**: 2026-01-30
**Deciders**: Product team
**Related**: ADR-011 (MLFlow Observability)

---

## Context

Comprehensive observability requires tracking different aspects of the system:
1. **LLM Experiments**: Prompts, tokens, costs, DSPy optimization
2. **Distributed Tracing**: Latency breakdown, span waterfall, bottleneck identification
3. **Infrastructure**: Uptime, throughput, SLA compliance, alerting

No single tool addresses all three. We need a **complementary stack** where each tier serves a distinct purpose.

---

## Decision

**We will implement a three-tier observability architecture, deployed incrementally across v0.1 → v0.3.**

```
┌─────────────────────────────────────────────────────┐
│  Tier 1: LLM Experiments & Costs (MLFlow)         │  ← v0.1
│                                                     │
│  Purpose: Track prompts, tokens, costs, DSPy       │
│  When: Post-run analysis, experiment comparison    │
│  UI: MLFlow dashboard (http://localhost:5000)      │
│  Retention: Unlimited (user-managed)               │
│  Cost: Free (self-hosted)                          │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│  Tier 2: Distributed Tracing (OpenTelemetry)      │  ← v0.2
│                                                     │
│  Purpose: Latency breakdown, performance debugging │
│  When: Real-time tracing, finding bottlenecks      │
│  UI: Jaeger waterfall (http://localhost:16686)     │
│  Retention: 7-30 days (configurable)               │
│  Cost: Free (Jaeger) or paid (Honeycomb SaaS)     │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│  Tier 3: Infrastructure & Alerting (Prometheus)   │  ← v0.3
│                                                     │
│  Purpose: SLA monitoring, uptime, alerting         │
│  When: Production health, real-time dashboards     │
│  UI: Grafana dashboards (http://localhost:3000)    │
│  Retention: 15 days default (longer with Thanos)   │
│  Cost: Free (self-hosted)                          │
└─────────────────────────────────────────────────────┘
```

---

## Tier Breakdown

### Tier 1: MLFlow (LLM-Native)

**What it tracks**:
- Prompts (resolved templates)
- LLM responses (raw outputs)
- Token counts (input/output per node)
- Estimated costs ($ per run, $ per workflow)
- Retries and validation failures
- Node-level nested traces
- DSPy optimization metrics (baseline vs optimized)

**Example queries**:
- "What did this workflow cost?" → Check `cost_usd` metric
- "Why did the LLM retry 3 times?" → View prompt + response artifacts
- "How much did we spend this month?" → Aggregate `cost_usd` across runs
- "Which prompt version performed better?" → Compare experiments

**When to use**:
- Post-run analysis ("What happened in this workflow?")
- Cost attribution ("How much did Team A spend?")
- DSPy optimization ("Did the optimized prompt improve accuracy?")
- Debugging LLM behavior ("Why did it generate wrong output?")

**Implementation** (v0.1):
```yaml
config:
  observability:
    mlflow:
      enabled: true
      tracking_uri: "file://./mlruns"
      experiment_name: "production_workflows"
```

**See**: ADR-011 for detailed MLFlow decision.

---

### Tier 2: OpenTelemetry (Performance Tracing)

**What it tracks**:
- Span per operation (workflow → node → LLM call → tool call)
- Latency per span (duration in milliseconds)
- Parent/child relationships (call hierarchy)
- Context propagation (trace ID across services)

**Example span waterfall**:
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

**Example queries**:
- "Where is the 3-second latency?" → View span waterfall
- "Is the tool call slow or the LLM?" → Compare span durations
- "How long does validation take?" → Check validation span

**When to use**:
- Performance debugging ("Where are the bottlenecks?")
- Latency analysis ("Why is this workflow slow?")
- Service dependencies ("Which external calls are slow?")

**Implementation** (v0.2):
```python
from opentelemetry import trace
from opentelemetry.instrumentation.langchain import LangChainInstrumentor

# Auto-instrument LangChain
LangChainInstrumentor().instrument()

# Traces sent to Jaeger
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("node_execution"):
    # Execute node
    pass
```

**Config**:
```yaml
config:
  observability:
    opentelemetry:
      enabled: true
      exporter: jaeger  # or tempo, honeycomb, otlp
      endpoint: "http://localhost:14268/api/traces"
      service_name: "configurable-agents"
      sampling_rate: 1.0  # 100% in dev, 0.01 (1%) in prod
```

**Backends**:
- **Jaeger** (free, self-hosted): `docker run -p 16686:16686 jaegertracing/all-in-one`
- **Grafana Tempo** (free, self-hosted): Integrates with Grafana
- **Honeycomb** (paid SaaS): Best UX, powerful querying

---

### Tier 3: Prometheus + Grafana (Infrastructure)

**What it tracks**:
- Workflow throughput (requests/second)
- Workflow duration (p50, p95, p99 latencies)
- Error rates (% failures)
- Token usage over time (cumulative)
- Cost trends ($ per hour/day/month)
- Active workflows (concurrent executions)

**Example metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge

# Counters (monotonic)
workflow_runs_total = Counter('workflow_runs_total', 'Total runs', ['workflow', 'status'])
llm_tokens_total = Counter('llm_tokens_total', 'Total tokens', ['model', 'type'])
llm_cost_usd = Counter('llm_cost_usd', 'Total cost', ['model'])

# Histograms (distributions)
workflow_duration_seconds = Histogram(
    'workflow_duration_seconds',
    'Execution time',
    ['workflow'],
    buckets=[0.1, 0.5, 1, 2.5, 5, 10, 30, 60]
)

# Gauges (current value)
active_workflows = Gauge('active_workflows', 'Currently executing workflows')
```

**Example queries** (PromQL):
```promql
# p95 latency over last hour
histogram_quantile(0.95, rate(workflow_duration_seconds_bucket[1h]))

# Error rate (last 5 minutes)
rate(workflow_runs_total{status="error"}[5m]) / rate(workflow_runs_total[5m])

# Total cost today
increase(llm_cost_usd[1d])
```

**When to use**:
- Production monitoring ("Is the service healthy?")
- SLA compliance ("Are we meeting 99.9% uptime?")
- Real-time alerting ("Page oncall if error rate > 5%")
- Capacity planning ("Do we need to scale up?")

**Implementation** (v0.3):
```python
# Expose /metrics endpoint
from prometheus_client import generate_latest
from fastapi import Response

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

# Instrument workflow execution
workflow_runs_total.labels(workflow='article_writer', status='success').inc()
workflow_duration_seconds.labels(workflow='article_writer').observe(5.2)
llm_cost_usd.labels(model='gemini-1.5-flash').inc(0.0023)
```

**Config**:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'configurable-agents'
    static_configs:
      - targets: ['localhost:8000']  # FastAPI /metrics
    scrape_interval: 15s
```

**Alerting**:
```yaml
# Prometheus alerting rules
groups:
  - name: sla_violations
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, workflow_duration_seconds_bucket) > 10
        for: 5m
        annotations:
          summary: "p95 latency > 10s for 5 minutes"

      - alert: HighErrorRate
        expr: rate(workflow_runs_total{status="error"}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "Error rate > 10%"
```

**Dashboards**: Grafana with pre-built panels
- Workflow throughput (time series)
- Latency percentiles (heatmap)
- Error rate (gauge)
- Cost trends (line chart)

---

## Why Three Tiers?

### Complementary, Not Redundant

Each tier serves a distinct purpose:

| Question | Tier | Tool |
|----------|------|------|
| "Why did this cost $5?" | Tier 1 | MLFlow (view tokens per node) |
| "Where are the 2s of latency?" | Tier 2 | OTEL (span waterfall) |
| "Is the service meeting SLA?" | Tier 3 | Prometheus (real-time metrics) |
| "What did the prompt look like?" | Tier 1 | MLFlow (artifact storage) |
| "Which API call is slowest?" | Tier 2 | OTEL (span comparison) |
| "Should we scale up?" | Tier 3 | Prometheus (throughput trends) |

### Overlaps are Intentional

**Duration tracking**:
- MLFlow: Post-run analysis (exact duration per run)
- OTEL: Real-time tracing (breakdown by operation)
- Prometheus: Aggregated metrics (p95 latency over time)

Each provides different granularity and use case.

**Cost tracking**:
- MLFlow: Per-run attribution ("This workflow cost $0.03")
- Prometheus: Aggregated trends ("Spent $150 today")

---

## Incremental Rollout

### v0.1: MLFlow Only

**Why start with MLFlow**:
- ✅ LLM-native (tokens, costs, prompts)
- ✅ DSPy-ready (optimization workflows)
- ✅ Zero external dependencies (file-based)
- ✅ Low complexity (optional, opt-in)

**What's missing**:
- ❌ No real-time monitoring
- ❌ No distributed tracing
- ❌ No alerting

**Acceptable for v0.1**: Local development, experimentation

---

### v0.2: Add OpenTelemetry

**Why add OTEL**:
- Performance debugging becomes critical (production usage)
- Users need to find bottlenecks
- Standard for cloud-native apps (k8s, service mesh)

**What it adds**:
- ✅ Span-level latency breakdown
- ✅ Distributed tracing (multi-service workflows in future)
- ✅ Real-time insights

**Config** (backward compatible):
```yaml
config:
  observability:
    mlflow:
      enabled: true  # Still works
    opentelemetry:  # NEW
      enabled: true
      exporter: jaeger
```

**Deployment**:
```yaml
# docker-compose.yml (add Jaeger)
services:
  workflow:
    # ...
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "14268:14268"  # Collector
```

---

### v0.3: Add Prometheus + Grafana

**Why add Prometheus**:
- Production monitoring is essential (uptime, SLA)
- Alerting needed (PagerDuty, Slack integration)
- Capacity planning (scale up decisions)

**What it adds**:
- ✅ Real-time dashboards
- ✅ Alerting (violation notifications)
- ✅ Long-term trends (months/years with Thanos)

**Config** (backward compatible):
```yaml
config:
  observability:
    mlflow:
      enabled: true
    opentelemetry:
      enabled: true
    prometheus:  # NEW
      enabled: true
      port: 9090
      path: "/metrics"
```

**Deployment**:
```yaml
# docker-compose.yml (add Prometheus + Grafana)
services:
  workflow:
    # ...
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
```

---

## Alternatives Considered

### 1. Single Tool (All-in-One)

**Approach**: Use one tool for everything (e.g., LangSmith, Datadog).

**Pros**:
- Simpler (one dashboard, one API)

**Cons**:
- ❌ **Vendor lock-in** (proprietary, can't swap)
- ❌ **Cost** (SaaS pricing for all tiers)
- ❌ **Overkill** (pay for features you don't use)
- ❌ **No DSPy support** (LLM-specific tools don't handle infrastructure)

**Rejected**: Open-source, modular stack is more flexible and cost-effective.

### 2. Custom Observability Backend

**Approach**: Build our own observability system (database + UI).

**Pros**:
- Full control

**Cons**:
- ❌ **Huge effort** (months of development)
- ❌ **Maintenance burden** (bugs, updates, scaling)
- ❌ **Reinventing the wheel** (mature tools exist)

**Rejected**: Focus on core product, not observability infra.

### 3. Only Prometheus (Skip MLFlow and OTEL)

**Approach**: Use Prometheus for everything (aggregate metrics only).

**Pros**:
- Simpler (one tool)

**Cons**:
- ❌ **No prompt tracking** (can't debug LLM behavior)
- ❌ **No per-run details** (only aggregated metrics)
- ❌ **No DSPy support** (experiment comparison impossible)
- ❌ **No span traces** (can't find latency bottlenecks)

**Rejected**: MLFlow is essential for LLM observability.

### 4. Only MLFlow (Skip OTEL and Prometheus)

**Approach**: Use MLFlow for everything.

**Pros**:
- Simpler (one tool)

**Cons**:
- ❌ **Not real-time** (post-run analysis only)
- ❌ **No alerting** (can't page oncall on errors)
- ❌ **No latency breakdown** (no span traces)
- ❌ **Not production-ready** (no uptime monitoring)

**Rejected**: Prometheus is essential for production monitoring.

---

## Rationale

### Why Incremental (v0.1 → v0.3)?

**User journey**:
1. **v0.1**: Local development → MLFlow for debugging, cost tracking
2. **v0.2**: Deploy to staging → OTEL for performance tuning
3. **v0.3**: Production → Prometheus for SLA monitoring, alerting

**Complexity ramp**:
- MLFlow: Zero setup (file-based)
- OTEL: Requires Jaeger container (still simple)
- Prometheus: Requires Prometheus + Grafana + Alertmanager (complex)

**Avoid overwhelming users**: Start simple, grow as needed.

### Why Not Custom Integrations?

**Approach**: Build custom dashboards that aggregate MLFlow + OTEL + Prometheus.

**Pros**:
- Unified UI

**Cons**:
- ❌ Development effort (custom UI = months)
- ❌ Each tool has excellent native UI (Jaeger, Grafana)
- ❌ Users familiar with existing tools

**Deferred**: Consider unified dashboard in v0.4 (if demand exists).

---

## Consequences

### Positive

1. **Comprehensive**: Covers LLM experiments, tracing, and infrastructure
2. **Best-in-class**: Each tier uses the best tool for its purpose
3. **Open-source**: No vendor lock-in, self-hosted, free
4. **Incremental**: Users adopt as complexity grows
5. **Standard tools**: Industry-standard (easy hiring, documentation)
6. **Backward compatible**: Each tier optional (no breaking changes)

### Negative

1. **Multiple UIs**: Users must learn MLFlow, Jaeger, Grafana
   - *Mitigation*: Document when to use each
2. **Setup complexity**: Tier 3 requires multiple containers
   - *Mitigation*: Provide docker-compose templates
3. **Data duplication**: Duration tracked in all three tiers
   - *Acceptable*: Each serves different use case

### Neutral

1. **Not fully integrated**: No single pane of glass
   - *Future*: Unified dashboard in v0.4 (if needed)
2. **Resource overhead**: Three systems running
   - *Acceptable*: Users opt-in per tier

---

## Implementation Roadmap

### v0.1 (Now) - 4 tasks
- T-018: MLFlow integration (schema, instrumentation)
- T-019: Workflow-level tracking (params, metrics, artifacts)
- T-020: Node-level tracking (nested runs, prompts, responses)
- T-021: Cost tracking (token pricing, $ calculation)

### v0.2 (Q2 2026) - 3 tasks
- T-XXX: OpenTelemetry SDK integration
- T-XXX: LangChain auto-instrumentation
- T-XXX: Jaeger backend setup (docker-compose)

### v0.3 (Q3 2026) - 4 tasks
- T-XXX: Prometheus metrics endpoint
- T-XXX: Instrumentation (counters, histograms, gauges)
- T-XXX: Alerting rules (latency, error rate, cost)
- T-XXX: Grafana dashboards (pre-built panels)

---

## References

- **MLFlow**: https://mlflow.org/
- **OpenTelemetry**: https://opentelemetry.io/
- **Prometheus**: https://prometheus.io/
- **Grafana**: https://grafana.com/
- **Jaeger**: https://www.jaegertracing.io/
- **Three Pillars of Observability**: https://www.oreilly.com/library/view/distributed-systems-observability/9781492033431/ch04.html

---

## Supersedes

None (first multi-tier observability decision)

---

## Related Decisions

- **ADR-011**: MLFlow for LLM observability (Tier 1 details)
- **ADR-012**: Docker deployment (MLFlow UI in container)
- **Future ADR**: OpenTelemetry integration (v0.2)
- **Future ADR**: Prometheus integration (v0.3)
