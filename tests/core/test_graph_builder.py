"""
Tests for graph builder (T-012).

Test organization:
- Section dividers for clarity
- AAA pattern (Arrange, Act, Assert)
- Mock execute_node for unit tests
- Real execute_node with mocked LLM for integration tests
"""

import os
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel

from configurable_agents.config.schema import (
    EdgeConfig,
    FlowMetadata,
    GlobalConfig,
    LLMConfig,
    NodeConfig,
    OutputSchema,
    OutputSchemaField,
    StateFieldConfig,
    StateSchema,
    WorkflowConfig,
)
from configurable_agents.core import GraphBuilderError, build_graph
from configurable_agents.core.node_executor import NodeExecutionError
from configurable_agents.llm import LLMUsageMetadata


# ============================================
# Test Helpers
# ============================================


def make_usage(input_tokens=100, output_tokens=50):
    """Create mock LLM usage metadata."""
    return LLMUsageMetadata(input_tokens=input_tokens, output_tokens=output_tokens)


# ============================================
# Test Fixtures
# ============================================


class SimpleState(BaseModel):
    """Simple state for testing."""

    input: str
    output: str = ""


class MultiStepState(BaseModel):
    """Multi-step state for testing."""

    topic: str
    research: str = ""
    article: str = ""


def make_simple_config() -> WorkflowConfig:
    """Create simple 2-node linear config."""
    return WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="test_flow", description="Test workflow"),
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "output": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process: {input}",
                output_schema=OutputSchema(type="str", description="Processed output"),
                outputs=["output"],
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="process"),
            EdgeConfig(from_="process", to="END"),
        ],
    )


def make_multi_step_config() -> WorkflowConfig:
    """Create 3-node linear config."""
    return WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="research_flow"),
        state=StateSchema(
            fields={
                "topic": StateFieldConfig(type="str", required=True),
                "research": StateFieldConfig(type="str", default=""),
                "article": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="research",
                prompt="Research {topic}",
                output_schema=OutputSchema(type="str"),
                outputs=["research"],
            ),
            NodeConfig(
                id="write",
                prompt="Write article about {topic} using {research}",
                output_schema=OutputSchema(type="str"),
                outputs=["article"],
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="research"),
            EdgeConfig(from_="research", to="write"),
            EdgeConfig(from_="write", to="END"),
        ],
    )


# ============================================
# Test: Basic Graph Building
# ============================================


@patch("configurable_agents.core.graph_builder.execute_node")
def test_build_simple_linear_graph(mock_execute):
    """Should build and compile 2-node linear graph."""
    # Arrange
    config = make_simple_config()

    # Mock execute_node to return updated state
    def mock_exec(node_config, state, global_config, tracker=None):
        new_state = state.model_copy()
        new_state.output = f"processed by {node_config.id}"
        return new_state

    mock_execute.side_effect = mock_exec

    # Act
    graph = build_graph(config, SimpleState)

    # Assert - graph compiled successfully
    assert graph is not None

    # Execute graph to verify
    initial = SimpleState(input="test", output="")
    final = graph.invoke(initial)

    # LangGraph returns dict (not BaseModel)
    assert final["output"] == "processed by process"
    assert final["input"] == "test"
    assert mock_execute.call_count == 1


@patch("configurable_agents.core.graph_builder.execute_node")
def test_build_multi_step_graph(mock_execute):
    """Should build 3-node linear workflow."""
    # Arrange
    config = make_multi_step_config()

    # Mock execute_node for multi-step
    def mock_exec(node_config, state, global_config, tracker=None):
        new_state = state.model_copy()
        if node_config.id == "research":
            new_state.research = "research findings"
        elif node_config.id == "write":
            new_state.article = f"article based on {state.research}"
        return new_state

    mock_execute.side_effect = mock_exec

    # Act
    graph = build_graph(config, MultiStepState)
    initial = MultiStepState(topic="AI", research="", article="")
    final = graph.invoke(initial)

    # Assert - LangGraph returns dict
    assert final["research"] == "research findings"
    assert final["article"] == "article based on research findings"
    assert mock_execute.call_count == 2


@patch("configurable_agents.core.graph_builder.execute_node")
def test_build_with_global_config(mock_execute):
    """Should pass global config to node functions."""
    # Arrange
    config = make_simple_config()
    global_config = GlobalConfig(llm=LLMConfig(model="gemini-pro"))

    # Mock that captures args
    captured_args = []

    def mock_exec(node_config, state, global_config, tracker=None):
        captured_args.append((node_config, state, global_config))
        return state.model_copy()

    mock_execute.side_effect = mock_exec

    # Act
    graph = build_graph(config, SimpleState, global_config)
    initial = SimpleState(input="test")
    graph.invoke(initial)

    # Assert - global_config passed to execute_node
    assert len(captured_args) == 1
    assert captured_args[0][2] == global_config


# ============================================
# Test: START/END Handling
# ============================================


@patch("configurable_agents.core.graph_builder.execute_node")
def test_start_edge_connects_to_first_node(mock_execute):
    """Should connect START to first node."""
    # Arrange
    config = make_simple_config()

    def mock_exec(node_config, state, global_config, tracker=None):
        return state.model_copy()

    mock_execute.side_effect = mock_exec

    # Act
    graph = build_graph(config, SimpleState)
    initial = SimpleState(input="test")
    final = graph.invoke(initial)

    # Assert - graph executed (START connected)
    assert mock_execute.called
    assert final["input"] == "test"


@patch("configurable_agents.core.graph_builder.execute_node")
def test_end_edge_terminates_graph(mock_execute):
    """Should connect last node to END."""
    # Arrange
    config = make_simple_config()

    def mock_exec(node_config, state, global_config, tracker=None):
        new_state = state.model_copy()
        new_state.output = "done"
        return new_state

    mock_execute.side_effect = mock_exec

    # Act
    graph = build_graph(config, SimpleState)
    initial = SimpleState(input="test")
    final = graph.invoke(initial)

    # Assert - graph terminated at END
    assert final["output"] == "done"


# ============================================
# Test: Node Function Creation
# ============================================


@patch("configurable_agents.core.graph_builder.execute_node")
def test_make_node_function_calls_execute_node(mock_execute):
    """Should call execute_node with correct arguments."""
    # Arrange
    config = make_simple_config()
    node_config = config.nodes[0]
    global_config = GlobalConfig(llm=LLMConfig(model="gemini-pro"))

    captured = []

    def mock_exec(nc, state, gc, tracker=None):
        captured.append((nc, state, gc))
        return state.model_copy()

    mock_execute.side_effect = mock_exec

    # Act
    graph = build_graph(config, SimpleState, global_config)
    initial = SimpleState(input="test")
    graph.invoke(initial)

    # Assert - execute_node called with correct args
    assert len(captured) == 1
    assert captured[0][0].id == node_config.id
    assert isinstance(captured[0][1], SimpleState)
    assert captured[0][2] == global_config


@patch("configurable_agents.core.graph_builder.execute_node")
def test_node_function_propagates_node_execution_error(mock_execute):
    """Should propagate NodeExecutionError unchanged."""
    # Arrange
    config = make_simple_config()
    error = NodeExecutionError("Test error", node_id="process")
    mock_execute.side_effect = error

    # Act
    graph = build_graph(config, SimpleState)
    initial = SimpleState(input="test")

    # Assert - NodeExecutionError propagates
    with pytest.raises(NodeExecutionError) as exc_info:
        graph.invoke(initial)

    assert str(exc_info.value) == "Test error"
    assert exc_info.value.node_id == "process"


@patch("configurable_agents.core.graph_builder.execute_node")
def test_node_function_wraps_unexpected_errors(mock_execute):
    """Should wrap unexpected errors in NodeExecutionError."""
    # Arrange
    config = make_simple_config()
    mock_execute.side_effect = ValueError("Unexpected error")

    # Act
    graph = build_graph(config, SimpleState)
    initial = SimpleState(input="test")

    # Assert - unexpected error wrapped
    with pytest.raises(NodeExecutionError) as exc_info:
        graph.invoke(initial)

    assert "process" in str(exc_info.value)
    assert "Unexpected error" in str(exc_info.value)
    assert exc_info.value.node_id == "process"


# ============================================
# Test: State Flow
# ============================================


@patch("configurable_agents.core.graph_builder.execute_node")
def test_state_flows_through_nodes(mock_execute):
    """Should pass state through node pipeline correctly."""
    # Arrange
    config = make_multi_step_config()

    # Track state changes
    states_seen = []

    def mock_exec(node_config, state, global_config, tracker=None):
        states_seen.append((node_config.id, state.model_copy()))
        new_state = state.model_copy()
        if node_config.id == "research":
            new_state.research = "findings"
        elif node_config.id == "write":
            new_state.article = f"article using {state.research}"
        return new_state

    mock_execute.side_effect = mock_exec

    # Act
    graph = build_graph(config, MultiStepState)
    initial = MultiStepState(topic="AI", research="", article="")
    final = graph.invoke(initial)

    # Assert - state flowed correctly
    assert len(states_seen) == 2
    assert states_seen[0][0] == "research"
    assert states_seen[0][1].topic == "AI"
    assert states_seen[1][0] == "write"
    assert states_seen[1][1].research == "findings"
    assert final["article"] == "article using findings"


@patch("configurable_agents.core.graph_builder.execute_node")
def test_state_copy_on_write_preserved(mock_execute):
    """Should maintain copy-on-write pattern from execute_node."""
    # Arrange
    config = make_simple_config()

    original_states = []

    def mock_exec(node_config, state, global_config, tracker=None):
        original_states.append(state)
        new_state = state.model_copy()
        new_state.output = "modified"
        return new_state

    mock_execute.side_effect = mock_exec

    # Act
    graph = build_graph(config, SimpleState)
    initial = SimpleState(input="test", output="original")
    final = graph.invoke(initial)

    # Assert - original state unchanged
    assert len(original_states) == 1
    assert original_states[0].output == "original"  # execute_node received original
    assert final["output"] == "modified"  # final state updated


# ============================================
# Test: Error Handling - Defensive Validation
# ============================================


def test_defensive_validation_no_nodes():
    """Should raise GraphBuilderError if no nodes."""
    # Arrange - config with no nodes (bypass Pydantic validation with model_construct)
    # This simulates a bug where validator (T-004) fails to catch this
    config = WorkflowConfig.model_construct(
        schema_version="1.0",
        flow=FlowMetadata(name="test"),
        state=StateSchema(fields={"input": StateFieldConfig(type="str")}),
        nodes=[],  # No nodes - bypasses Pydantic validation
        edges=[EdgeConfig(from_="START", to="END")],
    )

    # Act & Assert
    with pytest.raises(GraphBuilderError) as exc_info:
        build_graph(config, SimpleState)

    assert "No nodes defined" in str(exc_info.value)
    assert "Validator should have caught this" in str(exc_info.value)


def test_defensive_validation_no_edges():
    """Should raise GraphBuilderError if no edges."""
    # Arrange - config with no edges (bypass Pydantic validation)
    config = WorkflowConfig.model_construct(
        schema_version="1.0",
        flow=FlowMetadata(name="test"),
        state=StateSchema(fields={"input": StateFieldConfig(type="str")}),
        nodes=[
            NodeConfig(
                id="test",
                prompt="test",
                output_schema=OutputSchema(type="str"),
                outputs=["output"],
            )
        ],
        edges=[],  # No edges - bypasses Pydantic validation
    )

    # Act & Assert
    with pytest.raises(GraphBuilderError) as exc_info:
        build_graph(config, SimpleState)

    assert "No edges defined" in str(exc_info.value)


def test_defensive_validation_no_start_edge():
    """Should raise GraphBuilderError if no START edge."""
    # Arrange - config with no START edge
    config = WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="test"),
        state=StateSchema(fields={"input": StateFieldConfig(type="str")}),
        nodes=[
            NodeConfig(
                id="node1",
                prompt="test",
                output_schema=OutputSchema(type="str"),
                outputs=["output"],
            ),
            NodeConfig(
                id="node2",
                prompt="test",
                output_schema=OutputSchema(type="str"),
                outputs=["output"],
            ),
        ],
        edges=[
            EdgeConfig(from_="node1", to="node2"),  # No START
            EdgeConfig(from_="node2", to="END"),
        ],
    )

    # Act & Assert
    with pytest.raises(GraphBuilderError) as exc_info:
        build_graph(config, SimpleState)

    assert "No START edge found" in str(exc_info.value)


def test_defensive_validation_multiple_start_edges():
    """Should raise GraphBuilderError if multiple START edges."""
    # Arrange - config with multiple START edges
    config = WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="test"),
        state=StateSchema(fields={"input": StateFieldConfig(type="str")}),
        nodes=[
            NodeConfig(
                id="node1",
                prompt="test",
                output_schema=OutputSchema(type="str"),
                outputs=["output"],
            ),
            NodeConfig(
                id="node2",
                prompt="test",
                output_schema=OutputSchema(type="str"),
                outputs=["output"],
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="node1"),  # START 1
            EdgeConfig(from_="START", to="node2"),  # START 2
            EdgeConfig(from_="node1", to="END"),
            EdgeConfig(from_="node2", to="END"),
        ],
    )

    # Act & Assert
    with pytest.raises(GraphBuilderError) as exc_info:
        build_graph(config, SimpleState)

    assert "Multiple START edges" in str(exc_info.value)


# ============================================
# Test: Conditional Edge Support
# ============================================


def test_conditional_routing_supported():
    """Should now support conditional routing edges."""
    # Arrange - config with conditional routes
    from configurable_agents.config.schema import Route, RouteCondition
    from langgraph.graph import END

    config = WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="test"),
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "score": StateFieldConfig(type="float", default=0.5),
                "output": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="node1",
                prompt="test {input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            )
        ],
        edges=[
            EdgeConfig(from_="START", to="node1"),
            EdgeConfig(
                from_="node1",
                routes=[
                    Route(condition=RouteCondition(logic="state.score > 0.8"), to="END"),
                    Route(condition=RouteCondition(logic="default"), to="END"),
                ],
            ),
        ],
    )

    # Act - graph should build without error
    graph = build_graph(config, SimpleState)

    # Assert - graph compiled successfully
    assert graph is not None


def test_linear_flow_validation_rejects_branching():
    """Multiple outgoing edges from same node now supported via routes."""
    # This is now supported - the test is removed/updated
    pass


# ============================================
# Test: Integration (Real execute_node, Mock LLM)
# ============================================


@pytest.mark.integration
@patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key-123"}, clear=False)
@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
def test_graph_integration_multi_step(mock_create_llm, mock_call_llm):
    """Integration: Multi-step workflow with real execute_node."""
    # Arrange
    config = make_multi_step_config()

    mock_llm = Mock()
    mock_create_llm.return_value = mock_llm

    # Mock LLM responses for each node
    class SimpleOutput(BaseModel):
        result: str

    mock_call_llm.side_effect = [
        (SimpleOutput(result="research findings"), make_usage()),
        (SimpleOutput(result="article content"), make_usage()),
    ]

    # Act
    graph = build_graph(config, MultiStepState)
    initial = MultiStepState(topic="AI Safety", research="", article="")
    final = graph.invoke(initial)

    # Assert - both nodes executed
    assert mock_call_llm.call_count == 2
    assert final["research"] == "research findings"
    assert final["article"] == "article content"
    assert final["topic"] == "AI Safety"


# ============================================
# Test: Loop Edge Support
# ============================================


@patch("configurable_agents.core.graph_builder.execute_node")
def test_loop_edge_supported(mock_execute):
    """Should support loop edges with iteration tracking."""
    from configurable_agents.config.schema import LoopConfig
    from langgraph.graph import END

    # Arrange
    mock_execute.side_effect = lambda nc, state, gc, tracker: state.model_copy()

    config = WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="test"),
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "is_complete": StateFieldConfig(type="bool", default=False),
                "output": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="test",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            )
        ],
        edges=[
            EdgeConfig(from_="START", to="process"),
            EdgeConfig(
                from_="process",
                loop=LoopConfig(condition_field="is_complete", exit_to="END", max_iterations=3),
            ),
        ],
    )

    # Act - graph should build with loop support
    graph = build_graph(config, SimpleState)

    # Assert - graph compiled successfully
    assert graph is not None


# ============================================
# Test: Parallel Edge Support
# ============================================


@patch("configurable_agents.core.graph_builder.execute_node")
def test_parallel_edge_supported(mock_execute):
    """Should support parallel fan-out edges."""
    from configurable_agents.config.schema import ParallelConfig

    # Arrange
    mock_execute.side_effect = lambda nc, state, gc, tracker: state.model_copy()

    config = WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="test"),
        state=StateSchema(
            fields={
                "items": StateFieldConfig(type="list[str]", required=True),
                "result": StateFieldConfig(type="str", default=""),
                "results": StateFieldConfig(type="list[str]", default=[]),
            }
        ),
        nodes=[
            NodeConfig(
                id="worker",
                prompt="test",
                outputs=["result"],
                output_schema=OutputSchema(type="str"),
            )
        ],
        edges=[
            EdgeConfig(
                from_="START",
                parallel=ParallelConfig(
                    items_field="items", target_node="worker", collect_field="results"
                ),
            ),
            EdgeConfig(from_="worker", to="END"),
        ],
    )

    # Act - graph should build with parallel support
    graph = build_graph(config, SimpleState)

    # Assert - graph compiled successfully
    assert graph is not None
