# ADR-025: Optimization Architecture

**Status**: Accepted
**Date**: 2026-02-04
**Deciders**: thatAverageGuy, Claude Code

---

## Context

The system needs to optimize prompts automatically using MLFlow experimentation and A/B testing. Users should be able to:

1. Evaluate prompt performance across multiple runs
2. Compare prompt variants (A/B testing)
3. Apply optimized prompts to workflows
4. Set quality gates (block deployment if metrics degrade)

### Requirements

- **OBS-01**: System provides full MLFlow production features (prompt optimization, evaluations, A/B testing)

### Constraints

- Must use MLFlow as experiment tracking backend
- Must support percentile aggregation (p50, p95, p99)
- Must support quality gates (WARN, FAIL, BLOCK_DEPLOY)
- Must not modify workflow configs without backup

---

## Decision

**Use MLFlow experiment aggregation for metrics, CLI commands for evaluation/optimization, and quality gates for automated validation.**

---

## Rationale

### Why MLFlow for Optimization?

1. **Existing Infrastructure**: Already using MLFlow for tracking (ADR-011)
2. **Experiment Tracking**: MLFlow is designed for A/B testing
3. **Metrics Aggregation**: Built-in query and aggregation APIs
4. **UI**: MLFlow UI visualizes experiments
5. **Production-Grade**: Used by ML teams for hyperparameter tuning

### Why Quality Gates?

1. **Automated Validation**: Prevent deploying bad prompts
2. **Flexible Actions**: WARN (log), FAIL (raise error), BLOCK_DEPLOY (set flag)
3. **Configurable**: Users define thresholds per metric
4. **Integration**: Can integrate into CI/CD pipelines

### Why CLI Commands?

1. **Developer-Friendly**: Evaluate, apply, and test from terminal
2. **Scriptable**: Easy to integrate into CI/CD
3. **Transparent**: Users see exactly what changes before applying

---

## Implementation

### Experiment Evaluator

```python
class ExperimentEvaluator:
    """Aggregate MLFlow experiment metrics"""

    def evaluate_experiment(
        self,
        experiment_name: str,
        metrics: List[str] = None
    ) -> ExperimentSummary:
        """Aggregate metrics across runs in experiment"""
        client = mlflow.tracking.MlflowClient()

        # Get all runs in experiment
        runs = client.search_runs(experiment_ids=[experiment_id])

        # Aggregate metrics
        summary = {}
        for metric in metrics:
            values = [run.data.metrics.get(metric, 0) for run in runs]
            summary[metric] = {
                "p50": self._percentile(values, 50),
                "p95": self._percentile(values, 95),
                "p99": self._percentile(values, 99),
                "mean": np.mean(values),
                "count": len(values),
            }

        return ExperimentSummary(
            experiment_name=experiment_name,
            metrics=summary,
            run_count=len(runs)
        )

    def _percentile(self, values: List[float], p: int) -> float:
        """Calculate percentile using nearest-rank method"""
        sorted_values = sorted(values)
        index = math.ceil(p / 100 * len(values)) - 1
        return sorted_values[index]
```

### A/B Test Runner

```python
class ABTestRunner:
    """Compare two prompt variants"""

    def run_ab_test(
        self,
        workflow_path: str,
        variant_a: str,  # Experiment ID or config override
        variant_b: str,
        metric: str = "cost_usd",
        inputs: dict = None
    ) -> ABTestResult:
        """Run A/B test between two variants"""

        # Run variant A
        result_a = run_workflow(workflow_path, inputs, config_override=variant_a)

        # Run variant B
        result_b = run_workflow(workflow_path, inputs, config_override=variant_b)

        # Compare metrics
        value_a = result_a.metrics[metric]
        value_b = result_b.metrics[metric]

        winner = "A" if value_a < value_b else "B"  # Lower cost is better
        improvement = abs((value_a - value_b) / value_a) * 100

        return ABTestResult(
            variant_a_id=variant_a,
            variant_b_id=variant_b,
            metric=metric,
            value_a=value_a,
            value_b=value_b,
            winner=winner,
            improvement_pct=improvement
        )
```

### Quality Gate Checker

```python
class QualityGateChecker:
    """Validate metrics against quality gates"""

    def check_gates(
        self,
        metrics: Dict[str, float],
        gates: List[QualityGate]
    ) -> List[QualityGateResult]:
        """Check all quality gates"""
        results = []

        for gate in gates:
            value = metrics.get(gate.metric, 0)

            passed = value <= gate.threshold if gate.action != "WARN" else True

            result = QualityGateResult(
                metric=gate.metric,
                threshold=gate.threshold,
                value=value,
                passed=passed,
                action=gate.action
            )

            results.append(result)

            # Handle failures
            if not passed:
                if gate.action == "FAIL":
                    raise QualityGateError(f"Quality gate failed: {gate.metric}={value} > {gate.threshold}")
                elif gate.action == "BLOCK_DEPLOY":
                    # Set deployment block flag
                    self._set_deploy_block(gate.metric, value)
                    logger.warning(f"Deployment blocked: {gate.metric}={value} > {gate.threshold}")

        return results
```

### Prompt Optimizer

```python
class PromptOptimizer:
    """Apply optimized prompts to workflow config"""

    def apply_optimized_prompt(
        self,
        workflow_path: str,
        node_id: str,
        optimized_prompt: str,
        experiment_id: str
    ) -> str:
        """Apply optimized prompt to workflow"""

        # Backup original config
        backup_path = self._backup_config(workflow_path)

        # Load config
        config = load_config(workflow_path)

        # Find node and update prompt
        for node in config.nodes:
            if node.id == node_id:
                node.prompt = optimized_prompt
                node.metadata = node.metadata or {}
                node.metadata["optimized_by_experiment"] = experiment_id

        # Save updated config
        save_config(workflow_path, config)

        logger.info(f"Applied optimized prompt from {experiment_id} to {node_id}")
        logger.info(f"Original config backed up to {backup_path}")

        return backup_path
```

---

## Configuration

### Optimization Config

```yaml
optimization:
  enabled: true
  strategy: "BootstrapFewShot"
  metric: "semantic_match"
  max_demos: 8
  quality_gates:
    - metric: "cost_usd"
      threshold: 0.10
      action: "WARN"
    - metric: "duration_seconds"
      threshold: 30
      action: "FAIL"
    - metric: "accuracy"
      threshold: 0.90
      action: "BLOCK_DEPLOY"
```

---

## CLI Commands

### Evaluate Experiment

```bash
# Evaluate experiment metrics
configurable-agents optimization evaluate article_writer.yaml

# Output:
# Experiment: article_writer_optimization
# Runs: 10
# Metrics:
#   cost_usd:   p50=0.05, p95=0.08, p99=0.10
#   duration:   p50=15.2, p95=20.1, p99=25.3
#   accuracy:   p50=0.92, p95=0.95, p99=0.98
```

### Apply Optimized Prompt

```bash
# Apply best prompt from experiment
configurable-agents optimization apply-optimized article_writer.yaml \
    --experiment-id 12345 \
    --node-id write_node

# Output:
# Applied optimized prompt from experiment 12345 to write_node
# Original config backed up to article_writer.yaml.backup.2026-02-04
```

### Run A/B Test

```bash
# Compare two prompt variants
configurable-agents optimization ab-test article_writer.yaml \
    --variant-a exp1 \
    --variant-b exp2 \
    --metric cost_usd \
    --input topic="AI"

# Output:
# A/B Test Results:
# Variant A (exp1): cost_usd=0.05
# Variant B (exp2): cost_usd=0.03
# Winner: B
# Improvement: 40.0% reduction
```

---

## Quality Gate Actions

### WARN

```python
# Log warning but continue
logger.warning(f"Quality gate warning: {metric}={value} > {threshold}")
# Execution continues
```

### FAIL

```python
# Raise exception, block execution
raise QualityGateError(f"Quality gate failed: {metric}={value} > {threshold}")
# Workflow stops
```

### BLOCK_DEPLOY

```python
# Set deployment block flag
deploy_block.set(metric, value, threshold)
# Deployment command checks flag before applying
```

---

## Alternatives Considered

### Alternative 1: DSPy Optimization

**Pros**:
- Automatic prompt optimization
- Few-shot learning
- Programmatic prompting

**Cons**:
- Heavy dependency (DSPy library)
- Complex integration (DSPy modules vs LangGraph)
- Overkill for basic A/B testing

**Why deferred**: MLFlow provides sufficient optimization for v1.0. DSPy can be added in v1.1 if needed.

### Alternative 2: Custom Optimization Framework

**Pros**:
- Full control
- No dependencies

**Cons**:
- Reinventing the wheel
- Time-consuming
- Maintenance burden

**Why rejected**: MLFlow already provides experiment tracking and A/B testing.

### Alternative 3: External Optimization Service

**Pros**:
- Managed service
- No operational overhead

**Cons**:
- Vendor lock-in
- Cost
- Data privacy concerns

**Why rejected**: Violates local-first principle.

---

## Consequences

### Positive Consequences

1. **Automated Optimization**: Users can A/B test prompts automatically
2. **Quality Gates**: Prevent deploying bad prompts to production
3. **Metric Aggregation**: MLFlow provides p50/p95/p99 out of the box
4. **CLI Integration**: Easy to script and integrate into CI/CD
5. **Backup Safety**: Original configs backed up before modification

### Negative Consequences

1. **MLFlow Dependency**: Optimization requires MLFlow (but already using for tracking)
2. **Manual Steps**: Users must explicitly apply optimized prompts (no auto-deployment)
3. **Metric Selection**: Users must choose which metrics to optimize
4. **No DSPy**: Limited to prompt variants (no automatic FewShot optimization yet)

### Risks

#### Risk 1: Overfitting to Test Data

**Likelihood**: Medium
**Impact**: Medium
**Mitigation**: Use diverse test inputs. Validate on holdout set.

#### Risk 2: Metric Gaming

**Likelihood**: Low
**Impact**: Low
**Mitigation**: Use multiple quality gates. Don't optimize single metric in isolation.

#### Risk 3: MLFlow Query Performance

**Likelihood**: Low (MLFlow is efficient)
**Impact**: Low
**Mitigation**: MLFlow SQL backend scales well. Can add caching if needed.

---

## Related Decisions

- [ADR-011](ADR-011-mlflow-observability.md): MLFlow tracking foundation
- [ADR-014](ADR-014-three-tier-observability-strategy.md): Three-tier observability strategy

---

## Implementation Status

**Status**: ✅ Complete (v1.0)

**Files**:
- `src/configurable_agents/optimization/evaluator.py` - ExperimentEvaluator
- `src/configurable_agents/optimization/ab_testing.py` - ABTestRunner
- `src/configurable_agents/optimization/quality_gates.py` - QualityGateChecker
- `src/configurable_agents/optimization/optimizer.py` - PromptOptimizer
- `src/configurable_agents/cli.py` - CLI optimization command group

**Features**:
- MLFlow experiment aggregation (p50, p95, p99 percentiles)
- A/B testing between prompt variants
- Quality gates (WARN, FAIL, BLOCK_DEPLOY actions)
- Config backup before applying optimizations
- CLI commands (evaluate, apply-optimized, ab-test)

**Testing**: 23 tests covering evaluation, A/B testing, quality gates, and backup

---

## Superseded By

None (current)
