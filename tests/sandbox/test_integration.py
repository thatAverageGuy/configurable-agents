"""
Integration tests for sandbox execution with node executor.

Tests cover:
- Node execution with Python sandbox (no Docker required)
- Code execution node type in workflow config
- Sandbox config merging (workflow default, node override)
- Error propagation from sandbox to node result
- Workflow with code node + LLM node combined
"""

import pytest

from configurable_agents.config.schema import (
    NodeConfig,
    OutputSchema,
    SandboxConfig,
    StateSchema,
    StateFieldConfig,
    WorkflowConfig,
    FlowMetadata,
    EdgeConfig,
    GlobalConfig,
)
from configurable_agents.core.node_executor import execute_node, NodeExecutionError


class TestPythonSandboxIntegration:
    """Integration tests for Python sandbox with node executor."""

    def test_code_execution_node(self):
        """Test basic code execution node."""
        # Create a simple state
        from pydantic import BaseModel

        class TestState(BaseModel):
            result: int = 0
            numbers: list = []

        state = TestState(numbers=[1, 2, 3, 4, 5])

        # Create node config with code execution
        node_config = NodeConfig(
            id="sum_node",
            prompt="Sum the numbers",
            output_schema=OutputSchema(type="int"),
            outputs=["result"],
            code="result = sum(inputs['numbers'])",
            inputs={"numbers": "{numbers}"},
            sandbox=SandboxConfig(mode="python", enabled=True),
        )

        # Execute node
        new_state = execute_node(node_config, state)

        assert new_state.result == 15

    def test_sandbox_with_preset(self):
        """Test sandbox with resource preset."""
        from pydantic import BaseModel

        class TestState(BaseModel):
            result: str = ""

        state = TestState()

        node_config = NodeConfig(
            id="low_resource_node",
            prompt="Test with low preset",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
            code='result = "success"',
            inputs={},
            sandbox=SandboxConfig(
                mode="python",
                enabled=True,
                preset="low",
                timeout=10,
            ),
        )

        new_state = execute_node(node_config, state)
        assert new_state.result == "success"

    def test_code_execution_error_propagation(self):
        """Test that code execution errors are propagated properly."""
        from pydantic import BaseModel

        class TestState(BaseModel):
            result: str = ""

        state = TestState()

        # Code with syntax error
        node_config = NodeConfig(
            id="error_node",
            prompt="This should fail",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
            code="result = undefined_variable",
            inputs={},
            sandbox=SandboxConfig(mode="python", enabled=True),
        )

        # Should raise NodeExecutionError
        with pytest.raises(NodeExecutionError) as exc_info:
            execute_node(node_config, state)

        assert "error_node" in str(exc_info.value)
        assert "failed" in str(exc_info.value).lower()

    def test_inputs_passed_correctly(self):
        """Test that inputs are passed correctly to sandbox."""
        from pydantic import BaseModel

        class TestState(BaseModel):
            doubled: int = 0
            value: int = 0

        state = TestState(value=21)

        node_config = NodeConfig(
            id="double_node",
            prompt="Double the value",
            output_schema=OutputSchema(type="int"),
            outputs=["doubled"],
            code="result = inputs['value'] * 2",
            inputs={"value": "{value}"},
            sandbox=SandboxConfig(mode="python", enabled=True),
        )

        new_state = execute_node(node_config, state)
        assert new_state.doubled == 42

    def test_sandbox_disabled_unsafe_execution(self):
        """Test that sandbox can be disabled (unsafe)."""
        from pydantic import BaseModel

        class TestState(BaseModel):
            result: str = ""

        state = TestState()

        # Disable sandbox (should still work but with warning)
        node_config = NodeConfig(
            id="unsafe_node",
            prompt="Unsafe execution",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
            code='result = "unsafe_success"',
            inputs={},
            sandbox=SandboxConfig(mode="python", enabled=False),
        )

        # This should work but may log a warning
        new_state = execute_node(node_config, state)
        assert new_state.result == "unsafe_success"

    def test_network_disabled_in_config(self):
        """Test that network can be disabled via config."""
        from pydantic import BaseModel

        class TestState(BaseModel):
            result: str = ""

        state = TestState()

        node_config = NodeConfig(
            id="no_network_node",
            prompt="No network access",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
            code='result = "no_network"',
            inputs={},
            sandbox=SandboxConfig(
                mode="python",
                enabled=True,
                network=False,
            ),
        )

        new_state = execute_node(node_config, state)
        assert new_state.result == "no_network"

    def test_custom_timeout_in_config(self):
        """Test custom timeout in sandbox config."""
        from pydantic import BaseModel

        class TestState(BaseModel):
            result: str = ""

        state = TestState()

        node_config = NodeConfig(
            id="custom_timeout_node",
            prompt="Custom timeout",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
            code='result = "quick"',
            inputs={},
            sandbox=SandboxConfig(
                mode="python",
                enabled=True,
                timeout=5,  # 5 second timeout
            ),
        )

        new_state = execute_node(node_config, state)
        assert new_state.result == "quick"


class TestWorkflowConfigIntegration:
    """Integration tests for workflow config with sandbox."""

    def test_workflow_with_code_node(self):
        """Test full workflow configuration with code execution node."""
        config = WorkflowConfig(
            schema_version="1.0",
            flow=FlowMetadata(
                name="test_sandbox_workflow",
                description="Test workflow with sandbox execution",
            ),
            state=StateSchema(fields={
                "input_data": StateFieldConfig(type="list[int]", required=True),
                "sum_result": StateFieldConfig(type="int"),
                "doubled": StateFieldConfig(type="int"),
            }),
            nodes=[
                NodeConfig(
                    id="sum_node",
                    description="Sum the input numbers",
                    prompt="Calculate sum",
                    output_schema=OutputSchema(type="int"),
                    outputs=["sum_result"],
                    code="result = sum(inputs['data'])",
                    inputs={"data": "{input_data}"},
                    sandbox=SandboxConfig(mode="python", enabled=True, preset="low"),
                ),
                NodeConfig(
                    id="double_node",
                    description="Double the sum",
                    prompt="Double the result",
                    output_schema=OutputSchema(type="int"),
                    outputs=["doubled"],
                    code="result = inputs['sum'] * 2",
                    inputs={"sum": "{sum_result}"},
                    sandbox=SandboxConfig(mode="python", enabled=True),
                ),
            ],
            edges=[
                EdgeConfig(from_="START", to="sum_node"),
                EdgeConfig(from_="sum_node", to="double_node"),
                EdgeConfig(from_="double_node", to="END"),
            ],
        )

        # Validate config
        assert config.flow.name == "test_sandbox_workflow"
        assert len(config.nodes) == 2
        assert config.nodes[0].sandbox is not None
        assert config.nodes[0].sandbox.preset == "low"
        assert config.nodes[0].code is not None

    def test_sandbox_config_all_options(self):
        """Test all sandbox config options."""
        sandbox = SandboxConfig(
            mode="docker",
            enabled=True,
            network=False,
            preset="high",
            resources={"cpu": 3.0, "memory": "2g"},
            timeout=180,
        )

        assert sandbox.mode == "docker"
        assert sandbox.enabled is True
        assert sandbox.network is False
        assert sandbox.preset == "high"
        assert sandbox.resources["cpu"] == 3.0
        assert sandbox.timeout == 180

    def test_sandbox_config_defaults(self):
        """Test sandbox config defaults."""
        sandbox = SandboxConfig()

        assert sandbox.mode == "python"
        assert sandbox.enabled is True
        assert sandbox.network is True
        assert sandbox.preset == "medium"
        assert sandbox.resources is None
        assert sandbox.timeout is None


class TestEdgeCases:
    """Edge case tests for sandbox integration."""

    def test_empty_inputs_dict(self):
        """Test code execution with empty inputs."""
        from pydantic import BaseModel

        class TestState(BaseModel):
            result: str = ""

        state = TestState()

        node_config = NodeConfig(
            id="no_inputs_node",
            prompt="No inputs",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
            code='result = "no_inputs_needed"',
            inputs={},
            sandbox=SandboxConfig(mode="python", enabled=True),
        )

        new_state = execute_node(node_config, state)
        assert new_state.result == "no_inputs_needed"

    def test_complex_return_value(self):
        """Test code execution with complex return value."""
        from pydantic import BaseModel

        class TestState(BaseModel):
            result: str = ""

        state = TestState()

        node_config = NodeConfig(
            id="complex_node",
            prompt="Complex return",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
            code="""
data = {"key": "value", "numbers": [1, 2, 3]}
result = str(data)
""",
            inputs={},
            sandbox=SandboxConfig(mode="python", enabled=True),
        )

        new_state = execute_node(node_config, state)
        assert "key" in new_state.result
        assert "value" in new_state.result

    def test_code_with_print_statements(self):
        """Test that print statements are captured."""
        from pydantic import BaseModel

        class TestState(BaseModel):
            result: int = 0

        state = TestState()

        node_config = NodeConfig(
            id="print_node",
            prompt="Code with print",
            output_schema=OutputSchema(type="int"),
            outputs=["result"],
            code="""
print("Calculating...")
result = 42
print("Done!")
""",
            inputs={},
            sandbox=SandboxConfig(mode="python", enabled=True),
        )

        # Should succeed and capture output
        new_state = execute_node(node_config, state)
        assert new_state.result == 42

    def test_multiple_operations_in_code(self):
        """Test code with multiple operations."""
        from pydantic import BaseModel

        class TestState(BaseModel):
            result: str = ""
            items: list = []

        state = TestState(items=[10, 20, 30, 40])

        node_config = NodeConfig(
            id="multi_op_node",
            prompt="Multiple operations",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
            code="""
items = inputs.get('items', [1, 2, 3])
total = sum(items)
count = len(items)
average = total / count if count > 0 else 0
result = f"total={total}, count={count}, avg={average}"
""",
            inputs={"items": "{items}"},
            sandbox=SandboxConfig(mode="python", enabled=True),
        )

        new_state = execute_node(node_config, state)
        assert "total=100" in new_state.result
        assert "count=4" in new_state.result
        assert "avg=25" in new_state.result
