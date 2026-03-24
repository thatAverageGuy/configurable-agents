"""Unit tests for T-014: Runtime memory override (_apply_runtime_overrides)."""

import pytest

from configurable_agents.config.schema import (
    EdgeConfig,
    FlowMetadata,
    GlobalConfig,
    MemoryConfig,
    MemoryRuntimeOverride,
    NodeConfig,
    OutputSchema,
    OutputSchemaField,
    RuntimeOverrides,
    StateFieldConfig,
    StateSchema,
    WorkflowConfig,
)
from configurable_agents.runtime.executor import _apply_runtime_overrides


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(node_memory: MemoryConfig | None = None) -> WorkflowConfig:
    """Build a minimal WorkflowConfig with one node."""
    return WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="test_flow"),
        state=StateSchema(fields={"result": StateFieldConfig(type="str")}),
        nodes=[
            NodeConfig(
                id="node1",
                prompt="do something",
                output_schema=OutputSchema(type="str"),
                outputs=["result"],
                memory=node_memory,
            )
        ],
        edges=[EdgeConfig(**{"from": "START", "to": "node1"})],
    )


# ---------------------------------------------------------------------------
# scope=none disables memory
# ---------------------------------------------------------------------------


class TestScopeNone:
    def test_disables_node_with_memory_enabled(self):
        config = _make_config(MemoryConfig(enabled=True))
        overrides = RuntimeOverrides(memory=MemoryRuntimeOverride(scope="none"))
        result = _apply_runtime_overrides(config, overrides)
        assert result.nodes[0].memory.enabled is False

    def test_disables_node_without_memory_config(self):
        """scope=none must also inject MemoryConfig(enabled=False) on nodes with no memory config."""
        config = _make_config(node_memory=None)
        overrides = RuntimeOverrides(memory=MemoryRuntimeOverride(scope="none"))
        result = _apply_runtime_overrides(config, overrides)
        assert result.nodes[0].memory is not None
        assert result.nodes[0].memory.enabled is False

    def test_disables_workflow_level_memory(self):
        config = _make_config()
        config.memory = MemoryConfig(enabled=True, default_scope="agent")
        overrides = RuntimeOverrides(memory=MemoryRuntimeOverride(scope="none"))
        result = _apply_runtime_overrides(config, overrides)
        assert result.memory.enabled is False


# ---------------------------------------------------------------------------
# scope=workflow sets scope
# ---------------------------------------------------------------------------


class TestScopeWorkflow:
    def test_sets_scope_on_node_with_memory(self):
        config = _make_config(MemoryConfig(enabled=True, default_scope="agent"))
        overrides = RuntimeOverrides(memory=MemoryRuntimeOverride(scope="workflow"))
        result = _apply_runtime_overrides(config, overrides)
        assert result.nodes[0].memory.default_scope == "workflow"
        # enabled is unchanged (was True)
        assert result.nodes[0].memory.enabled is True

    def test_does_not_create_memory_config_for_node_with_none(self):
        """scope!=none should not inject MemoryConfig on a node that had none."""
        config = _make_config(node_memory=None)
        overrides = RuntimeOverrides(memory=MemoryRuntimeOverride(scope="workflow"))
        result = _apply_runtime_overrides(config, overrides)
        # Node had no memory config → still None (we only create on scope=none)
        assert result.nodes[0].memory is None


# ---------------------------------------------------------------------------
# enabled override
# ---------------------------------------------------------------------------


class TestEnabledOverride:
    def test_explicitly_disable_memory(self):
        config = _make_config(MemoryConfig(enabled=True))
        overrides = RuntimeOverrides(memory=MemoryRuntimeOverride(enabled=False))
        result = _apply_runtime_overrides(config, overrides)
        assert result.nodes[0].memory.enabled is False

    def test_explicitly_enable_memory(self):
        config = _make_config(MemoryConfig(enabled=False))
        overrides = RuntimeOverrides(memory=MemoryRuntimeOverride(enabled=True))
        result = _apply_runtime_overrides(config, overrides)
        assert result.nodes[0].memory.enabled is True


# ---------------------------------------------------------------------------
# No-op cases
# ---------------------------------------------------------------------------


class TestNoOp:
    def test_no_overrides_returns_config_unchanged(self):
        config = _make_config(MemoryConfig(enabled=True, default_scope="agent"))
        overrides = RuntimeOverrides()  # no memory override
        result = _apply_runtime_overrides(config, overrides)
        assert result.nodes[0].memory.enabled is True
        assert result.nodes[0].memory.default_scope == "agent"

    def test_memory_override_with_no_fields_is_noop(self):
        config = _make_config(MemoryConfig(enabled=True))
        overrides = RuntimeOverrides(memory=MemoryRuntimeOverride())
        result = _apply_runtime_overrides(config, overrides)
        # Nothing should change
        assert result.nodes[0].memory.enabled is True


# ---------------------------------------------------------------------------
# RuntimeOverrides model validation
# ---------------------------------------------------------------------------


class TestRuntimeOverridesModel:
    def test_scope_none_is_valid(self):
        o = RuntimeOverrides(memory={"scope": "none"})
        assert o.memory.scope == "none"

    def test_scope_workflow_is_valid(self):
        o = RuntimeOverrides(memory={"scope": "workflow"})
        assert o.memory.scope == "workflow"

    def test_scope_agent_is_valid(self):
        o = RuntimeOverrides(memory={"scope": "agent"})
        assert o.memory.scope == "agent"

    def test_invalid_scope_raises(self):
        with pytest.raises(Exception):
            RuntimeOverrides(memory={"scope": "invalid"})

    def test_empty_overrides_valid(self):
        o = RuntimeOverrides()
        assert o.memory is None
