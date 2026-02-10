"""Tests for quality gates."""

import pytest

from configurable_agents.runtime.gates import (
    GateAction,
    GatesConfig,
    QualityGate,
    QualityGateError,
    GateResult,
    check_gates,
    take_action,
    is_deploy_blocked,
    clear_deploy_block,
    get_failed_gates,
)


class TestQualityGate:
    """Test QualityGate dataclass."""

    def test_quality_gate_creation(self):
        """Test creating a quality gate."""
        gate = QualityGate(metric="cost_usd", max=1.0)

        assert gate.metric == "cost_usd"
        assert gate.max == 1.0
        assert gate.min is None
        assert gate.description is None

    def test_quality_gate_with_min_max(self):
        """Test quality gate with both min and max."""
        gate = QualityGate(metric="temperature", min=18.0, max=25.0)

        assert gate.min == 18.0
        assert gate.max == 25.0

    def test_quality_gate_check_pass(self):
        """Test gate check with passing value."""
        gate = QualityGate(metric="cost_usd", max=1.0)

        assert gate.check(0.5) is True
        assert gate.check(1.0) is True  # At threshold still passes

    def test_quality_gate_check_fail_max(self):
        """Test gate check with value exceeding max."""
        gate = QualityGate(metric="cost_usd", max=1.0)

        assert gate.check(1.1) is False
        assert gate.check(2.0) is False

    def test_quality_gate_check_fail_min(self):
        """Test gate check with value below min."""
        gate = QualityGate(metric="score", min=0.5)

        assert gate.check(0.4) is False
        assert gate.check(0.0) is False

    def test_quality_gate_check_pass_min(self):
        """Test gate check with value at/above min."""
        gate = QualityGate(metric="score", min=0.5)

        assert gate.check(0.5) is True
        assert gate.check(1.0) is True


class TestGatesConfig:
    """Test GatesConfig dataclass."""

    def test_gates_config_creation(self):
        """Test creating gates config."""
        gates = [
            QualityGate(metric="cost_usd", max=1.0),
            QualityGate(metric="duration_ms", max=5000),
        ]
        config = GatesConfig(gates=gates, on_fail=GateAction.WARN)

        assert len(config.gates) == 2
        assert config.on_fail == GateAction.WARN

    def test_gates_config_defaults(self):
        """Test default values."""
        config = GatesConfig()

        assert config.gates == []
        assert config.on_fail == GateAction.WARN


class TestCheckGates:
    """Test check_gates function."""

    def test_check_gates_all_pass(self):
        """Test checking gates where all pass."""
        metrics = {"cost_usd": 0.5, "duration_ms": 3000}
        config = GatesConfig(
            gates=[
                QualityGate(metric="cost_usd", max=1.0),
                QualityGate(metric="duration_ms", max=5000),
            ]
        )

        results = check_gates(metrics, config)

        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_check_gates_some_fail(self):
        """Test checking gates where some fail."""
        metrics = {"cost_usd": 1.5, "duration_ms": 3000}
        config = GatesConfig(
            gates=[
                QualityGate(metric="cost_usd", max=1.0),
                QualityGate(metric="duration_ms", max=5000),
            ]
        )

        results = check_gates(metrics, config)

        assert len(results) == 2
        assert not results[0].passed  # Cost gate failed
        assert results[1].passed  # Duration gate passed

    def test_check_gates_with_avg_suffix(self):
        """Test checking gates with metric name suffix variations."""
        metrics = {"cost_usd_avg": 0.5}
        config = GatesConfig(
            gates=[QualityGate(metric="cost_usd", max=1.0)]
        )

        results = check_gates(metrics, config)

        assert len(results) == 1
        assert results[0].passed is True

    def test_check_gates_with_avg_prefix(self):
        """Test checking gates with avg_ prefix."""
        metrics = {"avg_cost_usd": 0.5}
        config = GatesConfig(
            gates=[QualityGate(metric="cost_usd", max=1.0)]
        )

        results = check_gates(metrics, config)

        assert len(results) == 1
        assert results[0].passed is True

    def test_check_gates_metric_not_found(self):
        """Test checking gates when metric not found."""
        metrics = {"duration_ms": 3000}
        config = GatesConfig(
            gates=[QualityGate(metric="cost_usd", max=1.0)]
        )

        results = check_gates(metrics, config)

        assert len(results) == 1
        assert results[0].passed is False
        assert "not found" in results[0].message

    def test_check_gates_min_threshold(self):
        """Test checking gates with min threshold."""
        metrics = {"success_rate": 0.95}
        config = GatesConfig(
            gates=[QualityGate(metric="success_rate", min=0.9)]
        )

        results = check_gates(metrics, config)

        assert results[0].passed is True

    def test_check_gates_min_threshold_fail(self):
        """Test checking gates with min threshold that fails."""
        metrics = {"success_rate": 0.85}
        config = GatesConfig(
            gates=[QualityGate(metric="success_rate", min=0.9)]
        )

        results = check_gates(metrics, config)

        assert results[0].passed is False
        assert "below minimum" in results[0].message


class TestTakeAction:
    """Test take_action function."""

    def test_take_action_all_pass(self):
        """Test taking action when all gates pass."""
        gates = [
            QualityGate(metric="cost_usd", max=1.0),
        ]
        results = [
            GateResult(
                gate=gates[0],
                passed=True,
                actual=0.5,
                threshold=1.0,
                message="Passed",
            )
        ]

        # Should not raise
        take_action(results, GateAction.WARN)

    def test_take_action_warn(self):
        """Test WARN action doesn't raise."""
        gates = [QualityGate(metric="cost_usd", max=1.0)]
        results = [
            GateResult(
                gate=gates[0],
                passed=False,
                actual=1.5,
                threshold=1.0,
                message="Exceeded maximum",
            )
        ]

        # Should not raise
        take_action(results, GateAction.WARN)

    def test_take_action_fail_raises(self):
        """Test FAIL action raises exception."""
        gates = [QualityGate(metric="cost_usd", max=1.0)]
        results = [
            GateResult(
                gate=gates[0],
                passed=False,
                actual=1.5,
                threshold=1.0,
                message="Exceeded maximum",
            )
        ]

        with pytest.raises(QualityGateError) as exc_info:
            take_action(results, GateAction.FAIL, context="test_workflow")

        assert "Quality gates failed" in str(exc_info.value)
        assert exc_info.value.failed_gates == results

    def test_take_action_block_deploy_sets_flag(self):
        """Test BLOCK_DEPLOY action sets flag."""
        gates = [QualityGate(metric="cost_usd", max=1.0)]
        results = [
            GateResult(
                gate=gates[0],
                passed=False,
                actual=1.5,
                threshold=1.0,
                message="Exceeded maximum",
            )
        ]

        # Clear any existing flag
        clear_deploy_block("test_workflow")

        # Should not raise
        take_action(results, GateAction.BLOCK_DEPLOY, context="test_workflow")

        # Check flag is set
        assert is_deploy_blocked("test_workflow") is True

    def test_take_action_multiple_failed_gates(self):
        """Test action with multiple failed gates."""
        gates = [
            QualityGate(metric="cost_usd", max=1.0),
            QualityGate(metric="duration_ms", max=5000),
        ]
        results = [
            GateResult(
                gate=gates[0],
                passed=False,
                actual=1.5,
                threshold=1.0,
                message="Exceeded",
            ),
            GateResult(
                gate=gates[1],
                passed=False,
                actual=6000,
                threshold=5000,
                message="Exceeded",
            ),
        ]

        with pytest.raises(QualityGateError) as exc_info:
            take_action(results, GateAction.FAIL)

        assert len(exc_info.value.failed_gates) == 2


class TestDeployBlockFlags:
    """Test deploy block flag management."""

    def test_is_deploy_blocked_default(self):
        """Test default state is not blocked."""
        assert is_deploy_blocked("nonexistent") is False

    def test_deploy_block_flag_lifecycle(self):
        """Test setting and clearing deploy block flag."""
        context = "test_lifecycle"

        # Initially not blocked
        assert is_deploy_blocked(context) is False

        # Set flag via take_action
        gates = [QualityGate(metric="cost", max=1.0)]
        results = [
            GateResult(
                gate=gates[0],
                passed=False,
                actual=2.0,
                threshold=1.0,
                message="Failed",
            )
        ]

        take_action(results, GateAction.BLOCK_DEPLOY, context=context)

        # Now blocked
        assert is_deploy_blocked(context) is True

        # Clear flag
        clear_deploy_block(context)

        # No longer blocked
        assert is_deploy_blocked(context) is False

    def test_get_failed_gates(self):
        """Test getting list of failed gates."""
        context = "test_failed_gates"

        # Clear first
        clear_deploy_block(context)

        gates = [
            QualityGate(metric="cost_usd", max=1.0),
            QualityGate(metric="duration_ms", max=5000),
        ]
        results = [
            GateResult(
                gate=gates[0],
                passed=False,
                actual=2.0,
                threshold=1.0,
                message="Failed",
            ),
            GateResult(
                gate=gates[1],
                passed=False,
                actual=6000,
                threshold=5000,
                message="Failed",
            ),
        ]

        take_action(results, GateAction.BLOCK_DEPLOY, context=context)

        failed = get_failed_gates(context)

        assert set(failed) == {"cost_usd", "duration_ms"}


class TestGateAction:
    """Test GateAction enum."""

    def test_gate_action_values(self):
        """Test GateAction enum values."""
        assert GateAction.WARN.value == "warn"
        assert GateAction.FAIL.value == "fail"
        assert GateAction.BLOCK_DEPLOY.value == "block_deploy"


class TestQualityGateError:
    """Test QualityGateError exception."""

    def test_quality_gate_error_creation(self):
        """Test creating quality gate error."""
        gates = [QualityGate(metric="cost", max=1.0)]
        results = [
            GateResult(
                gate=gates[0],
                passed=False,
                actual=2.0,
                threshold=1.0,
                message="Failed",
            )
        ]

        error = QualityGateError("Test error", results)

        assert error.failed_gates == results
        assert "Test error" in str(error)

    def test_quality_gate_error_str_formatting(self):
        """Test string formatting of error."""
        gates = [
            QualityGate(metric="cost", max=1.0),
            QualityGate(metric="duration", max=5000),
        ]
        results = [
            GateResult(
                gate=gates[0],
                passed=False,
                actual=2.0,
                threshold=1.0,
                message="Cost too high",
            ),
            GateResult(
                gate=gates[1],
                passed=False,
                actual=6000,
                threshold=5000,
                message="Too slow",
            ),
        ]

        error = QualityGateError("Gates failed", results)
        error_str = str(error)

        assert "Gates failed" in error_str
        assert "Failed gates:" in error_str
        assert "cost: Cost too high" in error_str
        assert "duration: Too slow" in error_str


class TestGateResult:
    """Test GateResult dataclass."""

    def test_gate_result_creation(self):
        """Test creating gate result."""
        gate = QualityGate(metric="cost", max=1.0)
        result = GateResult(
            gate=gate,
            passed=True,
            actual=0.5,
            threshold=1.0,
            message="Passed",
        )

        assert result.gate == gate
        assert result.passed is True
        assert result.actual == 0.5
        assert result.threshold == 1.0
        assert result.message == "Passed"

    def test_gate_result_with_none_threshold(self):
        """Test gate result when no threshold configured."""
        gate = QualityGate(metric="cost", description="Just tracking")
        result = GateResult(
            gate=gate,
            passed=True,
            actual=0.5,
            threshold=None,
            message="No threshold",
        )

        assert result.threshold is None
