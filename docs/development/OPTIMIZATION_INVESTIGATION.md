# Prompt Optimization — Investigation & Future Direction

**Status**: PARKED — Module to be removed and redesigned
**Created**: 2026-02-09
**Related**: [OBSERVABILITY_REFERENCE.md](OBSERVABILITY_REFERENCE.md) (MLflow 3.9 GenAI model)

---

## Context

The `optimization/` module was built early in development as a manual A/B testing system.
It predates the MLflow 3.9 GenAI trace paradigm and uses legacy `mlflow.start_run()` APIs.
The module does not deliver the intended value — it compares hand-written prompt variants
rather than automatically optimizing prompts.

## Original Vision

Given a workflow with prompts:
1. Auto-register prompts in MLflow (keyed by workflow name)
2. Log all workflow runs and their outcomes
3. Define optimization/evaluation criteria (config-driven or built-in defaults)
4. Optimize prompts automatically for cost, quality, latency
5. Seamless lifecycle: config → register → run → evaluate → optimize → redeploy

Inspired by **DSPy** (automatic prompt optimization), with **MLflow 3.9 GenAI** as
the tracking/evaluation backend.

## Current Module (To Be Removed)

### What exists

```
src/configurable_agents/optimization/
├── __init__.py        # Exports
├── ab_test.py         # ABTestRunner — manual variant comparison
├── evaluator.py       # ExperimentEvaluator — queries MLflow runs
├── gates.py           # QualityGate — metric thresholds
```

CLI commands: `optimization evaluate`, `optimization apply-optimized`, `optimization ab-test`

Config schema: `ABTestConfig`, `VariantConfig`, `QualityGateModel`, `GatesModel` in `config/schema.py`

### What it actually does

- User manually defines 2+ prompt variants in config YAML
- `ab-test` runs each variant N times, creates MLflow runs with metrics
- `evaluate` queries those runs, compares average cost
- `apply-optimized` writes the cheapest variant's prompt back to YAML

### Why it doesn't work

1. **Not optimization** — It's manual variant comparison. User writes all prompts.
2. **Wrong MLflow paradigm** — Uses `start_run()` (legacy ML runs), not GenAI traces
3. **Only measures cost** — No quality scoring (relevance, faithfulness, etc.)
4. **No auto-registration** — Prompts are not tracked in MLflow by default
5. **No lifecycle integration** — Disconnected from deploy pipeline
6. **VF-006**: `optimization` with no subcommand crashes (AttributeError)

### Verification findings

| Test | Result |
|------|--------|
| `optimization` (no subcommand) | CRASH — VF-006 |
| `optimization --help` | PASS |
| `evaluate --experiment nonexistent` | PASS — clear error |
| `apply-optimized --dry-run` | PASS — error handling works |
| `ab-test` (no ab_test in config) | PASS — clear error + example |

---

## MLflow 3.9 GenAI Capabilities (To Explore)

Reference: `docs/development/OBSERVABILITY_REFERENCE.md`

### What MLflow 3.9 offers natively

1. **Tracing** (already integrated in executor)
   - Automatic span capture for LLM calls
   - Token usage, latency, cost per span
   - Our executor already creates traces correctly

2. **`mlflow.evaluate()`**
   - Built-in scorers: relevance, faithfulness, toxicity, answer_similarity
   - Custom scorer functions
   - Evaluates against datasets or trace data
   - Returns metrics per example and aggregated

3. **Prompt Engineering UI**
   - Compare prompt variations visually
   - Side-by-side output comparison
   - Built into MLflow tracking UI

4. **Experiment Comparison**
   - Compare traces across experiments
   - Filter by tags, metrics, parameters
   - Native UI for variant analysis

### What this means for us

The executor already creates traces. If we:
- Auto-register prompts as MLflow parameters/tags on each trace
- Use `mlflow.evaluate()` with appropriate scorers
- Define evaluation criteria in workflow config

...then MLflow gives us most of the evaluation pipeline for free. The missing piece
is the **optimization loop** (automatically generating better prompts).

---

## DSPy Capabilities (Future Option)

### What DSPy offers

- **Automatic prompt optimization**: MIPRO, bootstrap few-shot, etc.
- **Metric-driven compilation**: Define a metric, DSPy finds the best prompt
- **Few-shot example selection**: Automatically picks best examples
- **Module composition**: Build complex pipelines with optimizable components

### Integration considerations

- DSPy has its own LLM abstraction — would need adapter for our provider system
- DSPy optimizers need a "trainset" (examples with expected outputs)
- Could run as a build-time optimization step before deployment
- Should be pluggable: config says `optimizer: dspy` or `optimizer: mlflow`

---

## Key Design Questions (For Future Task)

### 1. Prompt Registration
- When a workflow config is loaded, should prompts be auto-registered in MLflow?
- Should each prompt get a unique ID (workflow_name + node_id + hash)?
- How to track prompt versions over time?

### 2. Evaluation Criteria
- Config-driven: `evaluation.scorers: [relevance, faithfulness]`
- Built-in defaults per node type (e.g., LLM nodes always get cost + latency)
- Custom scorer functions (user-defined Python)
- Schema enhancement needed in `config/schema.py`

### 3. Lifecycle: Build-Time vs Runtime

**Option A: Build-time optimization**
```
config → optimize prompts → deploy optimized config → run in production
```
- Optimization runs during CI/build
- Deployed container uses pre-optimized prompts
- Simpler, predictable
- Requires re-deploy for prompt changes

**Option B: Runtime optimization**
```
config → deploy → run → evaluate → optimize → hot-reload prompts
```
- Running container optimizes prompts based on live data
- More complex (hot-reload, state management)
- Better for adaptive systems
- Risk: prompt drift, unpredictable behavior

**Option C: Hybrid (Recommended direction to explore)**
```
Build-time: Initial optimization → deploy
Runtime: Monitor + evaluate → flag for re-optimization → trigger rebuild
```
- Production uses stable, tested prompts
- Monitoring detects quality degradation
- Triggers rebuild pipeline, not in-place mutation
- Keeps deployments predictable

### 4. System Integration
- How does `deploy` command pick up optimized prompts?
- Should `run` command log evaluation data by default?
- How to handle multi-node workflows (optimize each node independently?)
- Where do evaluation datasets come from?

### 5. Plugin Architecture
- `optimizer: mlflow` — Use MLflow evaluate + manual variants
- `optimizer: dspy` — Use DSPy automatic optimization
- `optimizer: none` — No optimization (current default)
- Config-driven selection, no code changes to switch

---

## Removal Plan

When removing the current module:

### Files to remove
- `src/configurable_agents/optimization/` (entire directory)
- CLI commands: `cmd_optimization_evaluate`, `cmd_optimization_apply`, `cmd_optimization_ab_test`
- Parser entries: `optimization` subparser and all sub-subparsers
- Tests: `tests/cli/test_optimization_commands.py`

### Config schema to review
- `ABTestConfig`, `VariantConfig` in `config/schema.py` — remove or keep as placeholder
- `QualityGateModel`, `GatesModel` — quality gates concept is valid, may want to keep
- `WorkflowConfig.config.ab_test` field — remove
- `WorkflowConfig.config.gates` field — consider keeping

### What to preserve
- **Quality gates concept** (`gates.py`): The idea of enforcing cost/latency thresholds
  is valid and separate from optimization. Could be moved to a `gates/` or `evaluation/`
  module later.
- **Prompt-to-YAML apply logic** (`apply_prompt_to_workflow`): The mechanics of updating
  a YAML file with a new prompt is useful regardless of optimization approach.

---

## References

- [MLflow 3.9 GenAI docs](https://mlflow.org/docs/latest/llms/index.html)
- [DSPy documentation](https://dspy-docs.vercel.app/)
- [OBSERVABILITY_REFERENCE.md](OBSERVABILITY_REFERENCE.md) — MLflow trace model details
- [CL-003 Deep Flag Verification](implementation_logs/phase_5_cleanup_and_verification/CL-003_DEEP_FLAG_VERIFICATION.md) — VF-002, VF-004 findings on runs vs traces

---

*This document captures the investigation state. When this work is picked up, start here
and then create a proper implementation log with detailed design decisions.*
