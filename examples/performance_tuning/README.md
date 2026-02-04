# Performance Tuning Example

This example demonstrates various performance optimization techniques to reduce cost and latency.

## Techniques Demonstrated

### 1. Model Selection
- Use cheaper models (gemini-1.5-flash) for simple tasks
- Reserve expensive models (gemini-1.5-pro) for complex analysis
- Cost savings: 60-80% per node

### 2. Response Caching
```yaml
cache:
  enabled: true
  ttl: 3600  # Cache for 1 hour
```

**Benefits:**
- Instant response for repeated queries
- Reduced API costs (cached calls = $0)
- Lower latency (100-200ms vs 2-5 seconds)

### 3. A/B Testing
```yaml
optimization:
  ab_test:
    variants:
      - name: prompt_v1
      - name: prompt_v2
    metric: cost_usd
    direction: minimize
    sample_size: 50
```

**Workflow:**
1. Run both variants 50 times
2. Collect metrics in MLFlow
3. Compare performance
4. Apply winning variant

### 4. Quality Gates
```yaml
gates:
  - metric: cost_usd
    max: 0.10
    action: WARN
  - metric: latency_ms
    max: 3000
    action: FAIL
```

**Actions:**
- `WARN` - Log warning, continue
- `FAIL` - Raise exception, stop
- `BLOCK_DEPLOY` - Flag for manual review

## Performance Comparison

### Run Baseline

```bash
# Run unoptimized version
configurable-agents run baseline.yaml \
  --query "performance optimization"

# Check MLFlow for metrics
```

**Expected:**
- Cost: ~$0.05-0.08 per execution
- Latency: ~8-12 seconds
- No caching (every call hits LLM API)

### Run Optimized

```bash
# Run optimized version
configurable-agents run performance_tuning.yaml \
  --query "performance optimization"

# Check MLFlow for metrics
```

**Expected:**
- Cost: ~$0.01-0.03 per execution (after cache warm)
- Latency: ~2-4 seconds (cached), ~5-8 seconds (uncached)
- **60-80% cost reduction**
- **50-60% latency reduction**

## Benchmark Script

### Run Automated Benchmark

```bash
# Install dependencies (if needed)
pip install -e .

# Run benchmark
python benchmark.py
```

**Output:**

```
======================================================================
Performance Benchmark: Baseline vs Optimized
======================================================================
Query: performance optimization techniques for LLM workflows
Iterations: 10

1. Running Baseline (Unoptimized)
----------------------------------------------------------------------
Running 10 iterations...
  Run 1: $0.0623, 9234ms
  Run 2: $0.0618, 9102ms
  ...
  Run 10: $0.0631, 9456ms

Baseline Results:
  Average Cost:     $0.0624
  Average Latency:  9180ms
  Cost Range:       $0.0618 - $0.0631
  Latency Range:    9102ms - 9456ms
  Successful Runs:  10/10

2. Running Optimized Workflow
----------------------------------------------------------------------
Running 10 iterations...
  Run 1: $0.0182, 3124ms (cache miss)
  Run 2: $0.0002, 234ms (cache hit)
  ...
  Run 10: $0.0001, 198ms (cache hit)

Optimized Results:
  Average Cost:     $0.0184
  Average Latency:  3120ms
  Cost Range:       $0.0001 - $0.0182
  Latency Range:    198ms - 3124ms
  Successful Runs:  10/10

======================================================================
Improvement Summary
======================================================================
Cost:     70.5% reduction
Latency:  66.0% reduction

Estimated Savings (100 runs/day):
  Daily:   $4.40
  Monthly: $132.00

Performance Tier: EXCELLENT ⭐⭐⭐⭐⭐
======================================================================

Recommendations:
  - Caching is working excellently (80%+ hit rate)
  - Consider increasing TTL for frequently accessed data
  - Monitor MLFlow for continued performance tracking
```

## A/B Testing Workflow

### 1. Run A/B Test

```bash
# Execute workflow with A/B test enabled
for i in {1..100}; do
  configurable-agents run performance_tuning.yaml \
    --query "test run $i"
done
```

### 2. View Results

```bash
# Compare variants in MLFlow
configurable-agents optimization evaluate \
  --workflow performance_tuning.yaml \
  --experiment-name "performance_optimization"
```

**Output:**

```
A/B Test Results
===============

Variant      | Avg Cost | Avg Latency | Success Rate
-------------+----------+-------------+-------------
prompt_v1    | $0.018   | 2,950ms     | 98%
prompt_v2    | $0.022   | 3,200ms     | 99%

Winner: prompt_v1 (18% cheaper, 8% faster)

Recommendation: Apply prompt_v1 to production
```

### 3. Apply Winning Variant

```bash
configurable-agents optimization apply-optimized \
  --workflow performance_tuning.yaml \
  --experiment-name "performance_optimization"
```

## Profiling

### Enable Profiling

```bash
export CONFIGURABLE_AGENTS_PROFILING=true
configurable-agents run performance_tuning.yaml
```

### View Profile Report

```bash
# Get run ID from MLFlow
configurable-agents observability profile-report \
  --run-id $MLFLOW_RUN_ID
```

**Output:**

```
Node Execution Profile
======================

search:
  Duration: 1,245ms (cached)
  Cost: $0.000 (cache hit)
  Cache Hit Rate: 85%
  Status: ✅ OPTIMAL

analyze:
  Duration: 1,850ms
  Cost: $0.018
  Quality Gates: PASSED
  Status: ✅ OPTIMAL

Total: 3,095ms, $0.018

Recommendations:
- Cache hit rate is excellent (85%)
- All nodes within performance targets
- No bottlenecks detected
```

## Production Optimization Checklist

### Workflow Design
- [ ] Select appropriate models per task
- [ ] Minimize node count (reduce overhead)
- [ ] Use parallel execution where possible
- [ ] Cache expensive operations

### Configuration
- [ ] Enable caching for repeated queries
- [ ] Set up A/B testing for prompts
- [ ] Configure quality gates
- [ ] Enable profiling
- [ ] Set appropriate timeouts

### Monitoring
- [ ] Track cost per execution
- [ ] Monitor latency metrics
- [ ] Review MLFlow dashboard
- [ ] Set up alerts for violations
- [ ] Regular performance reviews

### Optimization
- [ ] A/B test prompts regularly
- [ ] Apply winning variants
- [ ] Optimize bottlenecks
- [ ] Cache LLM responses
- [ ] Use cost-effective models

## Performance Benchmarks

### Reference Performance

| Workflow Type | Nodes | Avg Time | Avg Cost |
|--------------|-------|----------|----------|
| Simple (echo) | 1 | 2-3s | $0.01-0.02 |
| Medium (article writer) | 2-3 | 8-15s | $0.05-0.15 |
| Complex (multi-step) | 5-10 | 30-60s | $0.20-0.50 |

### Target Metrics

- **Latency**: < 5s per node (average)
- **Cost**: < $0.10 per workflow (typical)
- **Success Rate**: > 95%
- **Cache Hit Rate**: > 70% (when applicable)
- **Bottleneck**: < 20% per node

## Troubleshooting

### Poor Cache Performance

**Problem**: Low cache hit rate

**Solutions:**
1. Increase cache TTL
2. Check if inputs are deterministic
3. Review cache key generation
4. Consider warm-up queries

### High Costs

**Problem**: Costs above targets

**Solutions:**
1. Switch to cheaper models
2. Enable caching
3. Optimize prompts (shorter = cheaper)
4. Use parallel execution (reduce total time)
5. Run A/B tests to find optimal prompts

### Slow Execution

**Problem**: High latency

**Solutions:**
1. Enable profiling to find bottlenecks
2. Use parallel execution
3. Implement caching
4. Switch to faster models
5. Optimize prompt length

## See Also

- [Performance Optimization Guide](../../docs/PERFORMANCE_OPTIMIZATION.md)
- [Observability Guide](../../docs/OBSERVABILITY.md)
- [Configuration Reference](../../docs/CONFIG_REFERENCE.md)

---

**Level**: Advanced (⭐⭐⭐⭐)
**Prerequisites**: MLFlow setup, basic performance concepts
**Time Investment**: 1-2 hours to run and analyze
**ROI**: Very High - 50-80% cost reduction achievable
