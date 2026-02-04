"""Quality gate enforcement for workflow metrics.

Enforces cost, latency, and other threshold-based quality gates
on workflow execution with configurable actions (warn, fail, block_deploy).

Key features:
- Define thresholds for metrics (max cost, max latency)
- Configurable actions: WARN, FAIL, BLOCK_DEPLOY
- Aggregate gate checking with detailed results
- Integration with executor for post-execution validation
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GateAction(Enum):
    """Action to take when quality gate fails.

    Attributes:
        WARN: Log warning but allow execution to continue
        FAIL: Raise exception to fail the workflow
        BLOCK_DEPLOY: Set flag to prevent deployment (doesn't fail execution)
    """

    WARN = "warn"
    FAIL = "fail"
    BLOCK_DEPLOY = "block_deploy"


@dataclass
class QualityGate:
    """A single quality gate threshold.

    Attributes:
        metric: Metric name to check (e.g., "cost_usd", "duration_ms")
        max: Maximum allowed value (exclusive)
        min: Minimum allowed value (optional)
        description: Human-readable description
    """

    metric: str
    max: Optional[float] = None
    min: Optional[float] = None
    description: Optional[str] = None

    def check(self, value: float) -> bool:
        """Check if value passes the gate.

        Args:
            value: Metric value to check

        Returns:
            True if gate passes, False otherwise
        """
        if self.max is not None and value > self.max:
            return False
        if self.min is not None and value < self.min:
            return False
        return True


@dataclass
class GatesConfig:
    """Configuration for quality gates.

    Attributes:
        gates: List of quality gates to check
        on_fail: Action to take when gates fail
    """

    gates: List[QualityGate] = field(default_factory=list)
    on_fail: GateAction = GateAction.WARN


@dataclass
class GateResult:
    """Result of checking a single gate.

    Attributes:
        gate: The gate that was checked
        passed: Whether the gate passed
        actual: The actual value
        threshold: The threshold that was checked
        message: Human-readable result message
    """

    gate: QualityGate
    passed: bool
    actual: float
    threshold: Optional[float]
    message: str


class QualityGateError(Exception):
    """Raised when quality gates fail with on_fail=FAIL action.

    Contains details about which gates failed and why.
    """

    def __init__(self, message: str, failed_gates: List[GateResult]):
        """Initialize quality gate error.

        Args:
            message: Error message
            failed_gates: List of failed gate results
        """
        super().__init__(message)
        self.failed_gates = failed_gates

    def __str__(self) -> str:
        """Format error with gate details."""
        lines = [super().__str__(), "\nFailed gates:"]
        for result in self.failed_gates:
            lines.append(f"  - {result.gate.metric}: {result.message}")
        return "\n".join(lines)


# In-memory flag storage for BLOCK_DEPLOY action
# In production, this should be persisted to storage
_deploy_block_flags: Dict[str, Any] = {}


def check_gates(
    metrics: Dict[str, Any],
    config: GatesConfig,
) -> List[GateResult]:
    """Check quality gates against metrics.

    Args:
        metrics: Dict of metric name to value
        config: Gates configuration

    Returns:
        List of GateResult for each gate checked

    Example:
        >>> from configurable_agents.optimization import check_gates, GatesConfig, QualityGate
        >>> metrics = {"cost_usd": 0.5, "duration_ms": 5000}
        >>> config = GatesConfig(
        ...     gates=[
        ...         QualityGate(metric="cost_usd", max=1.0),
        ...         QualityGate(metric="duration_ms", max=10000),
        ...     ],
        ...     on_fail=GateAction.WARN,
        ... )
        >>> results = check_gates(metrics, config)
        >>> all(r.passed for r in results)
        True
    """
    results = []

    for gate in config.gates:
        # Get metric value (support direct name or with suffixes)
        value = None
        for key in [gate.metric, f"{gate.metric}_avg", f"avg_{gate.metric}"]:
            if key in metrics:
                value = metrics[key]
                break

        if value is None:
            logger.warning(f"Gate metric not found in metrics: {gate.metric}")
            # Create failed result for missing metric
            results.append(GateResult(
                gate=gate,
                passed=False,
                actual=0,
                threshold=gate.max,
                message=f"Metric '{gate.metric}' not found in execution metrics",
            ))
            continue

        # Check the gate
        passed = True
        message = "Passed"
        threshold = None

        if gate.max is not None and value > gate.max:
            passed = False
            threshold = gate.max
            message = f"Value {value} exceeds maximum {gate.max}"
        elif gate.min is not None and value < gate.min:
            passed = False
            threshold = gate.min
            message = f"Value {value} below minimum {gate.min}"
        elif gate.max is not None:
            threshold = gate.max
            message = f"Value {value} within maximum {gate.max}"
        elif gate.min is not None:
            threshold = gate.min
            message = f"Value {value} within minimum {gate.min}"
        else:
            message = f"Value {value} (no threshold configured)"

        results.append(GateResult(
            gate=gate,
            passed=passed,
            actual=float(value) if value is not None else 0,
            threshold=threshold,
            message=message,
        ))

    return results


def take_action(
    results: List[GateResult],
    action: GateAction,
    context: Optional[str] = None,
) -> None:
    """Take action based on gate check results.

    Args:
        results: List of gate check results
        action: Action to take
        context: Optional context string (e.g., workflow name)

    Raises:
        QualityGateError: If action is FAIL and gates failed
    """
    # Filter failed gates
    failed = [r for r in results if not r.passed]

    if not failed:
        logger.debug("All quality gates passed")
        return

    # Log failures
    for result in failed:
        logger.warning(
            f"Quality gate failed: {result.gate.metric} = {result.actual} "
            f"(threshold: {result.threshold})"
        )

    # Take action based on configuration
    if action == GateAction.WARN:
        logger.warning(
            f"Quality gates failed but continuing (WARN action): "
            f"{len(failed)} gate(s) failed"
        )
        for result in failed:
            logger.warning(f"  - {result.message}")

    elif action == GateAction.FAIL:
        error = QualityGateError(
            f"Quality gates failed for {context or 'workflow'}: "
            f"{len(failed)} gate(s) failed",
            failed_gates=failed,
        )
        logger.error(str(error))
        raise error

    elif action == GateAction.BLOCK_DEPLOY:
        # Set deploy block flag
        flag_key = f"deploy_block:{context or 'default'}"
        _deploy_block_flags[flag_key] = {
            "timestamp": None,  # Could add timestamp
            "failed_gates": [r.gate.metric for r in failed],
        }
        logger.error(
            f"Quality gates failed: deployment blocked for {context or 'workflow'}. "
            f"{len(failed)} gate(s) failed. Clear flags to re-enable deployment."
        )
        # Don't raise - execution continues but deployment is blocked

    else:
        logger.warning(f"Unknown gate action: {action}")


def is_deploy_blocked(context: Optional[str] = None) -> bool:
    """Check if deployment is blocked for a workflow.

    Args:
        context: Optional context string (e.g., workflow name)

    Returns:
        True if deployment is blocked
    """
    flag_key = f"deploy_block:{context or 'default'}"
    return flag_key in _deploy_block_flags


def clear_deploy_block(context: Optional[str] = None) -> None:
    """Clear deployment block flag for a workflow.

    Args:
        context: Optional context string (e.g., workflow name)
    """
    flag_key = f"deploy_block:{context or 'default'}"
    if flag_key in _deploy_block_flags:
        del _deploy_block_flags[flag_key]
        logger.info(f"Cleared deploy block for {context or 'default'}")


def get_failed_gates(context: Optional[str] = None) -> List[str]:
    """Get list of failed gates for blocked deployment.

    Args:
        context: Optional context string (e.g., workflow name)

    Returns:
        List of failed gate metric names
    """
    flag_key = f"deploy_block:{context or 'default'}"
    flag_data = _deploy_block_flags.get(flag_key, {})
    return flag_data.get("failed_gates", [])
