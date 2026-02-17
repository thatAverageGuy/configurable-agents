# Performance Optimization

This guide covers techniques for optimizing workflow performance, reducing costs, and improving resource utilization.

## Table of Contents
- [Overview](#overview)
- [Profiling and Bottleneck Detection](#profiling-and-bottleneck-detection)
- [Cost Optimization](#cost-optimization)
- [Resource Management](#resource-management)
- [Performance Tuning Checklist](#performance-tuning-checklist)
- [Performance Benchmarks](#performance-benchmarks)

## Overview

Performance optimization involves:
- **Latency**: Reducing execution time
- **Cost**: Minimizing API expenses
- **Throughput**: Increasing parallel execution capacity
- **Resource Usage**: Optimizing CPU, memory, and storage

## Profiling and Bottleneck Detection

### Enable Profiling

```bash
export CONFIGURABLE_AGENTS_PROFILING=true
configurable-agents run workflow.yaml
```

### View Profile Report

```bash
configurable-agents profile-report
```

**Output:**

```
Node Execution Profile
======================

research_node:
  Duration: 2,345ms
  Cost: $0.023
  Status: ⚠️ SLOW (avg: 1,200ms, 95th percentile)
  Recommendation: Consider caching or prompt optimization

write_node:
  Duration: 890ms
  Cost: $0.015
  Status: ✅ OK (within normal range)

analyze_node:
  Duration: 4,567ms
  Cost: $0.045
  Status: ❌ BOTTLENECK (2.3x average, 95th percentile)
  Recommendation: Major bottleneck - investigate LLM calls

Workflow Totals:
  Total Duration: 7,802ms
  Total Cost: $0.083
  Most Expensive Node: analyze_node (54% of cost)
  Slowest Node: analyze_node (58% of duration)
```

### Bottleneck Optimization Strategies

**1. Response Caching**

```yaml
nodes:
  - name: cacheable_node
    cache:
      enabled: true
      ttl: 3600  # Cache for 1 hour
```

**Benefits:**
- Instant response for repeated queries
- Reduced API costs (cached calls = $0)
- Lower latency

**When to Use:**
- Read-heavy workloads
- Idempotent operations
- High repeated query patterns

**2. Parallel Execution**

```yaml
nodes:
  - name: parallel_1
    # Runs in parallel with parallel_2
  - name: parallel_2
    # Runs in parallel with parallel_1

edges:
  - from: parallel_1
    to: merge
  - from: parallel_2
    to: merge
```

**Benefits:**
- Reduces total execution time
- Better resource utilization
- Independent nodes run simultaneously

**When to Use:**
- Independent operations
- No data dependencies
- Resource constraints allow

**3. Prompt Optimization**

- Reduce prompt length (fewer tokens = lower cost)
- Use more specific prompts (fewer retries)
- Remove redundant instructions
- Use system prompts wisely

**4. Model Selection**

```yaml
nodes:
  - name: simple_task
    llm:
      provider: openai
      model: gpt-3.5-turbo  # Cheaper, faster
  - name: complex_task
    llm:
      provider: openai
      model: gpt-4  # More capable
```

**Model Comparison:**

| Model | Cost (1M tokens) | Speed | Quality | Best For |
|-------|-----------------|-------|---------|----------|
| GPT-3.5-turbo | $0.50 | Fast | Good | Simple tasks |
| GPT-4 | $30.00 | Medium | Excellent | Complex reasoning |
| Gemini Flash | $0.075 | Very Fast | Good | Fast responses |
| Gemini Pro | $0.70 | Medium | Excellent | Complex tasks |

## Cost Optimization

### Token Budgeting

```yaml
workflow:
  name: budgeted_workflow
  max_tokens: 10000  # Total workflow limit
```

**Behavior:**
- Tracks total tokens used across all nodes
- Stops execution if limit exceeded
- Logs warning when approaching limit

### Cost Estimation

```bash
# Estimate cost before running
configurable-agents run workflow.yaml --dry-run --estimate-cost
```

**Output:**

```
Cost Estimation
===============

Workflow: workflow.yaml
Estimated Cost: $0.23 (range: $0.18 - $0.28)
Estimated Tokens: 8,500 (input: 6,000, output: 2,500)
Breakdown by Node:
  - research_node: $0.12 (5,000 tokens)
  - analyze_node: $0.08 (2,500 tokens)
  - summarize_node: $0.03 (1,000 tokens)
```

### Cost Tracking

```bash
# View cost report
configurable-agents cost-report
```

**Output:**

```
Cost Report (Last 7 Days)
==========================

Workflow: workflow.yaml
Total Executions: 234
Total Cost: $18.42
Average Cost: $0.079
Min Cost: $0.058
Max Cost: $0.124

Cost by Provider:
  - google: $12.34 (67%)
  - openai: $6.08 (33%)

Cost by Node:
  - research_node: $9.21 (50%)  ← Most expensive
  - analyze_node: $6.13 (33%)
  - summarize_node: $3.08 (17%)

Recommendation: Optimize research_node prompts for 20-30% cost reduction
```

### Cost Reduction Techniques

**1. Cheaper Models**
- Use GPT-3.5-turbo instead of GPT-4 for simple tasks
- Use Gemini Flash for fast responses
- Reserve expensive models for complex reasoning

**2. Caching**
- Cache LLM responses for repeated queries
- Cache API responses
- Use cache-first strategy for read-heavy workloads

**3. Parallel Execution**
- Run independent nodes in parallel
- Reduce total workflow time
- Lower infrastructure costs

**4. Prompt Engineering**
- Reduce prompt length
- Eliminate redundant instructions
- Use more specific prompts (fewer retries)
- A/B test for optimal prompts

## Resource Management

### Sandbox Resources

```yaml
nodes:
  - name: heavy_computation
    type: code
    code: |
      result = expensive_computation()
    sandbox:
      resource_preset: "high"  # 4 CPUs, 2GB RAM
      timeout: 120
```

**Resource Presets:**

| Preset | CPUs | Memory | Timeout | Use Case |
|--------|------|--------|---------|----------|
| `low` | 1 | 512MB | 30s | Simple transformations |
| `medium` | 2 | 1GB | 60s | Standard processing |
| `high` | 4 | 2GB | 120s | Complex computations |
| `max` | 8 | 4GB | 300s | Heavy data processing |

### Memory Management

```yaml
nodes:
  - name: memory_intensive
    memory:
      enabled: true
      namespace: "my_workflow"
```

**Memory Usage:**
- State persists across executions
- Automatic cleanup on TTL expiration
- Shared memory for parallel nodes
- Memory namespace isolation

**When to Use:**
- Multi-step workflows requiring state
- Expensive computations to reuse
- Caching intermediate results
- Cross-execution learning

## Performance Tuning Checklist

### Workflow Design

- [ ] Minimize node count (reduce overhead)
- [ ] Use parallel execution where possible
- [ ] Cache expensive operations
- [ ] Select appropriate models per task
- [ ] Optimize prompt length
- [ ] Eliminate redundant data transformations

### Configuration

- [ ] Set appropriate timeouts
- [ ] Configure resource presets
- [ ] Enable profiling for bottlenecks
- [ ] Configure token budgets
- [ ] Enable response caching

### Monitoring

- [ ] Track cost per execution
- [ ] Monitor latency metrics
- [ ] Review MLFlow dashboard
- [ ] Set up alerts for violations
- [ ] Profile regularly
- [ ] Review cost reports

### Optimization

- [ ] Optimize bottleneck nodes
- [ ] Cache LLM responses
- [ ] Use parallel execution
- [ ] Select cost-effective models
- [ ] Reduce prompt length

## Performance Benchmarks

### Reference Performance

| Workflow Type | Nodes | Avg Time | Avg Cost | Notes |
|--------------|-------|----------|----------|-------|
| Simple (echo) | 1 | 2-3s | $0.01-0.02 | Minimal processing |
| Medium (article writer) | 2-3 | 8-15s | $0.05-0.15 | Web search + writing |
| Complex (multi-step) | 5-10 | 30-60s | $0.20-0.50 | Research + analysis |
| Code execution | +1 per node | +5-10s | +$0.02-0.05 | Sandbox overhead |

### Target Metrics

**Latency:**
- Simple nodes: < 3s
- Medium nodes: < 10s
- Complex nodes: < 30s
- Total workflow: < 60s (typical)

**Cost:**
- Simple workflow: < $0.05
- Medium workflow: < $0.15
- Complex workflow: < $0.50
- Per node: < $0.10 (average)

**Quality:**
- Success rate: > 95%
- Error rate: < 5%
- Timeout rate: < 1%
- Cache hit rate: > 70% (when applicable)

**Bottlenecks:**
- Per node: < 20% of total time
- Most expensive: < 50% of total cost
- Parallel utilization: > 60% when possible

### Optimization Impact

**Typical Improvements:**

| Technique | Cost Reduction | Latency Reduction | Effort |
|-----------|----------------|-------------------|---------|
| Caching | 50-80% | 80-95% | Low |
| Model selection | 40-70% | 10-30% | Low |
| Prompt optimization | 15-30% | 10-20% | Medium |
| Parallel execution | 0% | 30-60% | Medium |

## Related Documentation

- [Observability Guide](OBSERVABILITY.md) - MLFlow integration
- [Configuration Reference](CONFIG_REFERENCE.md) - Performance options
- [Security Guide](SECURITY_GUIDE.md) - Resource limits
- [Production Deployment](PRODUCTION_DEPLOYMENT.md) - Scaling strategies

---

**Level**: Advanced (⭐⭐⭐⭐)
**Prerequisites**: Familiarity with workflows, basic observability
**Time Investment**: 4-8 hours to implement optimization strategies
**ROI**: High - 50-80% cost reduction, 30-60% latency improvement
