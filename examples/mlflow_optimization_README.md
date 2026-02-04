# MLFlow Optimization Example

This workflow demonstrates advanced prompt optimization using MLFlow with A/B testing, quality gates, and automatic experiment tracking.

## Features

- **A/B Testing**: Test 4 different prompt variants simultaneously
- **Quality Gates**: Automatic validation of cost, latency, and quality metrics
- **MLFlow Integration**: Automatic experiment tracking and comparison
- **CLI Commands**: Built-in commands for evaluation and applying optimized prompts

## Quick Start

### 1. Install Dependencies

```bash
pip install mlflow>=3.9.0 rich>=13.0.0
```

### 2. Run A/B Test

Execute all variants with sample inputs:

```bash
configurable-agents optimization ab-test mlflow_optimization.yaml \
  --input topic="AI Safety"
```

This will run each variant 3 times (12 total runs) and log results to MLFlow.

### 3. Evaluate Results

Compare variants by cost (or any metric):

```bash
configurable-agents optimization evaluate --experiment prompt_opt_test
```

Output shows:
- Variant ranking by metric
- Run counts per variant
- Average cost, latency, and tokens
- Best variant highlighted

### 4. Apply Best Variant

Apply the best performing prompt to your workflow:

```bash
configurable-agents optimization apply-optimized \
  --experiment prompt_opt_test \
  --workflow mlflow_optimization.yaml
```

A backup is created automatically before modifying the file.

## Configuration Options

### A/B Test Configuration

```yaml
ab_test:
  enabled: true
  experiment: "my_experiment"    # MLFlow experiment name
  run_count: 5                    # Runs per variant
  variants:
    - name: "variant_a"
      prompt: "Your prompt here"
      node_id: "writer"           # Node to apply prompt to
    - name: "variant_b"
      prompt: "Alternative prompt"
      node_id: "writer"
```

### Quality Gates

```yaml
gates:
  - name: "cost_limit"
    metric: "cost_usd_avg"
    threshold: 0.01              # Max $0.01 per run
    action: "WARN"               # WARN, FAIL, or BLOCK_DEPLOY

  - name: "quality_minimum"
    metric: "quality_score_avg"
    min_threshold: 0.6           # Minimum score
    action: "FAIL"
```

### MLFlow Configuration

```yaml
mlflow:
  enabled: true
  tracking_uri: "file://./mlruns"
  experiment_name: "prompt_optimization"
```

## Dashboard Integration

Launch the dashboard to visualize experiments:

```bash
configurable-agents dashboard --mlflow-uri file://./mlruns
```

Navigate to:
- http://localhost:7861/optimization/experiments - View all experiments
- http://localhost:7861/optimization/compare?experiment=prompt_opt_test - Compare variants
- http://localhost:7861/mlflow - Full MLFlow UI

## Available Metrics

Metrics automatically tracked for each variant:

- `cost_usd_avg`: Average cost per run (USD)
- `duration_ms_avg`: Average duration (milliseconds)
- `total_tokens_avg`: Average total tokens used
- Any custom metrics logged by your workflow

## Best Practices

1. **Start Simple**: Test 2-3 variants before scaling up
2. **Sufficient Runs**: Use `run_count: 5+` for statistical significance
3. **Quality Gates**: Set appropriate thresholds to catch regressions
4. **Backup**: Always keep backups before applying optimizations
5. **Iterate**: Use insights to refine prompts and re-test

## Troubleshooting

**MLFlow not found error:**
```bash
pip install mlflow>=3.9.0
```

**No experiments found:**
- Ensure MLFlow tracking URI matches between config and CLI
- Check that `ab_test.enabled: true` in workflow config

**Quality gate failures:**
- Review gate thresholds in workflow config
- Use `--verbose` flag for detailed error messages
- Check MLFlow UI for actual metric values
