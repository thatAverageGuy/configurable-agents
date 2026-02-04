#!/usr/bin/env python
"""
Benchmark performance comparison between baseline and optimized workflows.

This script runs both workflows multiple times and compares:
- Average cost per execution
- Average latency per execution
- Cost and latency reduction percentages
"""

import time
import statistics
from configurable_agents.runtime import run_workflow

def benchmark_workflow(config_path: str, query: str, iterations: int = 10):
    """
    Run workflow multiple times and collect metrics.

    Args:
        config_path: Path to workflow configuration
        query: Search query to use
        iterations: Number of times to run workflow

    Returns:
        Dictionary with benchmark metrics
    """
    costs = []
    latencies = []

    print(f"Running {iterations} iterations...")

    for i in range(iterations):
        start = time.time()

        try:
            result = run_workflow(
                config_path,
                query=query
            )

            latency = (time.time() - start) * 1000  # Convert to ms
            cost = result.get('metrics', {}).get('cost_usd', 0.0)

            costs.append(cost)
            latencies.append(latency)

            print(f"  Run {i+1}: ${cost:.4f}, {latency:.0f}ms")

        except Exception as e:
            print(f"  Run {i+1}: FAILED - {e}")
            continue

    if not costs:
        raise ValueError("No successful runs")

    return {
        'avg_cost': statistics.mean(costs),
        'avg_latency': statistics.mean(latencies),
        'min_cost': min(costs),
        'max_cost': max(costs),
        'min_latency': min(latencies),
        'max_latency': max(latencies),
        'successful_runs': len(costs),
    }

def main():
    """Run benchmark and display results."""
    query = "performance optimization techniques for LLM workflows"
    iterations = 10

    print("=" * 70)
    print("Performance Benchmark: Baseline vs Optimized")
    print("=" * 70)
    print(f"Query: {query}")
    print(f"Iterations: {iterations}")
    print()

    # Run baseline
    print("1. Running Baseline (Unoptimized)")
    print("-" * 70)
    try:
        baseline = benchmark_workflow('baseline.yaml', query, iterations)
        print(f"\nBaseline Results:")
        print(f"  Average Cost:     ${baseline['avg_cost']:.4f}")
        print(f"  Average Latency:  {baseline['avg_latency']:.0f}ms")
        print(f"  Cost Range:       ${baseline['min_cost']:.4f} - ${baseline['max_cost']:.4f}")
        print(f"  Latency Range:    {baseline['min_latency']:.0f}ms - {baseline['max_latency']:.0f}ms")
        print(f"  Successful Runs:  {baseline['successful_runs']}/{iterations}")
    except Exception as e:
        print(f"Baseline failed: {e}")
        return

    print()

    # Run optimized
    print("2. Running Optimized Workflow")
    print("-" * 70)
    try:
        optimized = benchmark_workflow('performance_tuning.yaml', query, iterations)
        print(f"\nOptimized Results:")
        print(f"  Average Cost:     ${optimized['avg_cost']:.4f}")
        print(f"  Average Latency:  {optimized['avg_latency']:.0f}ms")
        print(f"  Cost Range:       ${optimized['min_cost']:.4f} - ${optimized['max_cost']:.4f}")
        print(f"  Latency Range:    {optimized['min_latency']:.0f}ms - {optimized['max_latency']:.0f}ms")
        print(f"  Successful Runs:  {optimized['successful_runs']}/{iterations}")
    except Exception as e:
        print(f"Optimized failed: {e}")
        return

    print()
    print("=" * 70)
    print("Improvement Summary")
    print("=" * 70)

    # Calculate improvements
    cost_reduction = (1 - optimized['avg_cost'] / baseline['avg_cost']) * 100
    latency_reduction = (1 - optimized['avg_latency'] / baseline['avg_latency']) * 100

    print(f"Cost:     {cost_reduction:+.1f}% reduction")
    print(f"Latency:  {latency_reduction:+.1f}% reduction")
    print()

    # Cost savings estimate
    daily_savings = (baseline['avg_cost'] - optimized['avg_cost']) * 100  # 100 runs/day
    monthly_savings = daily_savings * 30

    print(f"Estimated Savings (100 runs/day):")
    print(f"  Daily:   ${daily_savings:.2f}")
    print(f"  Monthly: ${monthly_savings:.2f}")
    print()

    # Performance tier
    if cost_reduction > 70:
        tier = "EXCELLENT ⭐⭐⭐⭐⭐"
    elif cost_reduction > 50:
        tier = "VERY GOOD ⭐⭐⭐⭐"
    elif cost_reduction > 30:
        tier = "GOOD ⭐⭐⭐"
    elif cost_reduction > 10:
        tier = "FAIR ⭐⭐"
    else:
        tier = "NEEDS IMPROVEMENT ⭐"

    print(f"Performance Tier: {tier}")
    print("=" * 70)

    # Recommendations
    print("\nRecommendations:")
    if cost_reduction < 30:
        print("  - Consider using cheaper models (gemini-1.5-flash)")
        print("  - Enable response caching")
        print("  - Optimize prompts to reduce token usage")
    if latency_reduction < 30:
        print("  - Use parallel execution where possible")
        print("  - Implement caching for repeated queries")
        print("  - Profile to identify bottlenecks")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure both YAML files exist in current directory")
        print("2. Check API keys are configured")
        print("3. Verify network connectivity")
        print("4. Try with fewer iterations")
