# Observability Module

The observability module provides MLFlow integration, cost tracking, and performance profiling.

## MLFlow Tracking

### MLFlowTracker

```{py:class} configurable_agents.observability.mlflow_tracker.MLFlowTracker
```

MLFlow integration for tracking workflow executions.

**Configuration:**

```python
from configurable_agents.observability import MLFlowTracker

tracker = MLFlowTracker(
    tracking_uri="http://localhost:5000",
    experiment_name="my-experiment"
)
```

**Environment Variables:**
- `MLFLOW_TRACKING_URI` - MLFlow server URI
- `MLFLOW_EXPERIMENT_NAME` - Default experiment name

## Cost Tracking

### CostReporter

```{py:class} configurable_agents.observability.cost_reporter.CostReporter
```

Track and report LLM API costs.

**Methods:**
- `track_cost(provider: str, model: str, cost: float)` - Record cost
- `get_total_cost() -> float` - Get total cost for session
- `get_cost_by_provider() -> dict` - Get cost breakdown by provider

### CostEstimator

```{py:class} configurable_agents.observability.cost_estimator.CostEstimator
```

Estimate token costs before LLM calls.

**Supported Models:**
- OpenAI (GPT-4, GPT-3.5-turbo)
- Google (Gemini Pro, Gemini Flash)
- Anthropic (Claude Opus, Claude Sonnet)
- Ollama (local models - $0.00)

## Profiling

### NodeProfiler

```{py:class} configurable_agents.runtime.profiler.NodeProfiler
```

Profile node execution for performance analysis.

**Environment Variables:**
- `CONFIGURABLE_AGENTS_PROFILING` - Enable profiling (set to "true")

**Usage:**

```bash
export CONFIGURABLE_AGENTS_PROFILING=true
configurable-agents run workflow.yaml
```

## CLI Commands

### Cost Report

```bash
configurable-agents observability cost-report \
  --workflow workflow.yaml \
  --last 7days
```

### Profile Report

```bash
configurable-agents observability profile-report \
  --run-id <mlflow_run_id>
```

## Full API

```{py:module} configurable_agents.observability
```

## See Also

- [Observability Guide](../OBSERVABILITY.md) - MLFlow setup and usage
- [Performance Optimization](../PERFORMANCE_OPTIMIZATION.md) - Tuning and profiling
