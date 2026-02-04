"""
MLFlow-based prompt optimization with A/B testing and experiment comparison.

Provides automated prompt variant testing, experiment evaluation,
quality gates, and bidirectional prompt synchronization between YAML
and MLFlow.

Key exports:
- ABTestRunner: Run A/B tests across prompt variants
- ExperimentEvaluator: Compare experiment results and find best variant
- QualityGate, check_gates: Enforce cost/latency thresholds
- apply_prompt_to_workflow: Apply optimized prompts from MLFlow to YAML
"""

from configurable_agents.optimization.ab_test import (
    ABTestConfig,
    ABTestRunner,
    VariantConfig,
    apply_prompt_to_workflow,
    run_ab_test,
)
from configurable_agents.optimization.evaluator import (
    ExperimentEvaluator,
    calculate_percentiles,
    compare_variants,
    find_best_variant,
    format_comparison_table,
)
from configurable_agents.optimization.gates import (
    GateAction,
    GatesConfig,
    QualityGate,
    QualityGateError,
    check_gates,
    take_action,
)

__all__ = [
    # A/B testing
    "ABTestRunner",
    "ABTestConfig",
    "VariantConfig",
    "run_ab_test",
    "apply_prompt_to_workflow",
    # Evaluation
    "ExperimentEvaluator",
    "compare_variants",
    "find_best_variant",
    "format_comparison_table",
    "calculate_percentiles",
    # Quality gates
    "QualityGate",
    "GatesConfig",
    "GateAction",
    "QualityGateError",
    "check_gates",
    "take_action",
]
