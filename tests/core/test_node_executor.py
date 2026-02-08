"""
Tests for node executor (T-011).

Covers:
- Basic node execution (simple and object outputs)
- Input mapping resolution
- Prompt template resolution with state prefix stripping
- Tool loading and binding
- LLM configuration merging
- State updates (copy-on-write pattern)
- Error handling (all failure modes)
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import BaseModel, ValidationError

from configurable_agents.config.schema import (
    ExecutionConfig,
    GlobalConfig,
    LLMConfig,
    NodeConfig,
    OutputSchema,
    OutputSchemaField,
)
from configurable_agents.core import execute_node
from configurable_agents.core.node_executor import (
    NodeExecutionError,
    _strip_state_prefix,
)
from configurable_agents.llm import LLMUsageMetadata


# Test helper
def make_usage(input_tokens=100, output_tokens=50):
    """Create mock LLM usage metadata."""
    return LLMUsageMetadata(input_tokens=input_tokens, output_tokens=output_tokens)


# Test fixtures
class SimpleState(BaseModel):
    """Simple state for testing."""

    topic: str
    research: str = ""
    score: int = 0


class ObjectState(BaseModel):
    """State with nested object."""

    topic: str
    summary: str = ""
    word_count: int = 0
    sources: list = []


class SimpleOutput(BaseModel):
    """Simple output model."""

    result: str


class ObjectOutput(BaseModel):
    """Object output model."""

    summary: str
    word_count: int
    sources: list


# ============================================
# Test: _strip_state_prefix helper
# ============================================


def test_strip_state_prefix_basic():
    """Should strip {state.field} → {field}"""
    template = "{state.topic}"
    result = _strip_state_prefix(template)
    assert result == "{topic}"


def test_strip_state_prefix_multiple():
    """Should strip multiple {state.X} references"""
    template = "Process {state.input} and {state.metadata.author}"
    result = _strip_state_prefix(template)
    assert result == "Process {input} and {metadata.author}"


def test_strip_state_prefix_no_prefix():
    """Should leave {field} unchanged"""
    template = "{query}"
    result = _strip_state_prefix(template)
    assert result == "{query}"


def test_strip_state_prefix_mixed():
    """Should handle mixed {state.X} and {field} references"""
    template = "Topic: {state.topic}, Query: {query}"
    result = _strip_state_prefix(template)
    assert result == "Topic: {topic}, Query: {query}"


def test_strip_state_prefix_nested():
    """Should handle nested state references"""
    template = "Author: {state.metadata.author}"
    result = _strip_state_prefix(template)
    assert result == "Author: {metadata.author}"


def test_strip_state_prefix_no_placeholders():
    """Should leave templates without placeholders unchanged"""
    template = "No placeholders here"
    result = _strip_state_prefix(template)
    assert result == "No placeholders here"


def test_strip_state_prefix_empty():
    """Should handle empty template"""
    template = ""
    result = _strip_state_prefix(template)
    assert result == ""


# ============================================
# Test: Basic node execution
# ============================================


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_execute_node_simple_output(mock_build_output, mock_create_llm, mock_call_llm):
    """Should execute node with simple output"""
    # Setup state
    state = SimpleState(topic="AI Safety", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Research {topic}",
        output_schema=OutputSchema(type="str", description="Research findings"),
        outputs=["research"],
    )

    # Mock output model
    mock_build_output.return_value = SimpleOutput

    # Mock LLM result
    mock_result = SimpleOutput(result="AI safety research findings...")
    mock_call_llm.return_value = (mock_result, make_usage())

    # Execute node
    updated_state = execute_node(node_config, state)

    # Verify state updated
    assert updated_state["research"] == "AI safety research findings..."
    # execute_node returns only updated fields (partial state dict for LangGraph reducers)
    assert "topic" not in updated_state
    assert "score" not in updated_state

    # Verify state is a new instance (copy-on-write)
    assert updated_state is not state

    # Verify LLM was called with resolved prompt
    mock_call_llm.assert_called_once()
    call_kwargs = mock_call_llm.call_args[1]
    assert call_kwargs["prompt"] == "Research AI Safety"  # {topic} resolved
    assert call_kwargs["output_model"] == SimpleOutput


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_execute_node_object_output(mock_build_output, mock_create_llm, mock_call_llm):
    """Should execute node with object output (multiple fields)"""
    # Setup state
    state = ObjectState(topic="AI", summary="", word_count=0, sources=[])

    # Setup node config
    node_config = NodeConfig(
        id="summarize",
        prompt="Summarize {topic}",
        output_schema=OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(name="summary", type="str"),
                OutputSchemaField(name="word_count", type="int"),
                OutputSchemaField(name="sources", type="list"),
            ],
        ),
        outputs=["summary", "word_count", "sources"],
    )

    # Mock output model
    mock_build_output.return_value = ObjectOutput

    # Mock LLM result
    mock_result = ObjectOutput(
        summary="AI summary text",
        word_count=42,
        sources=["https://example.com"],
    )
    mock_call_llm.return_value = (mock_result, make_usage())

    # Execute node
    updated_state = execute_node(node_config, state)

    # Verify all fields updated
    assert updated_state["summary"] == "AI summary text"
    assert updated_state["word_count"] == 42
    assert updated_state["sources"] == ["https://example.com"]
    # execute_node returns only updated fields (partial state dict)
    assert "topic" not in updated_state


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_execute_node_with_state_prefix(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Should handle {state.field} syntax in prompts"""
    # Setup state
    state = SimpleState(topic="Robotics", research="", score=0)

    # Setup node config with {state.topic} syntax
    node_config = NodeConfig(
        id="test_node",
        prompt="Research {state.topic}",  # Using state. prefix
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock output model and LLM
    mock_build_output.return_value = SimpleOutput
    mock_call_llm.return_value = (SimpleOutput(result="Research findings"), make_usage())

    # Execute node
    updated_state = execute_node(node_config, state)

    # Verify prompt was preprocessed and resolved correctly
    mock_call_llm.assert_called_once()
    call_kwargs = mock_call_llm.call_args[1]
    assert call_kwargs["prompt"] == "Research Robotics"  # {state.topic} → Robotics


# ============================================
# Test: Input mappings
# ============================================


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_execute_node_with_input_mappings(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Should resolve input mappings and use in prompt"""
    # Setup state
    state = SimpleState(topic="Machine Learning", research="Prior research", score=0)

    # Setup node config with input mappings
    node_config = NodeConfig(
        id="test_node",
        inputs={
            "query": "{topic}",  # Map state.topic → local var 'query'
            "context": "{research}",  # Map state.research → local var 'context'
        },
        prompt="Research {query} with context: {context}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock output model and LLM
    mock_build_output.return_value = SimpleOutput
    mock_call_llm.return_value = (SimpleOutput(result="New research"), make_usage())

    # Execute node
    updated_state = execute_node(node_config, state)

    # Verify prompt resolved with input mappings
    mock_call_llm.assert_called_once()
    call_kwargs = mock_call_llm.call_args[1]
    expected_prompt = "Research Machine Learning with context: Prior research"
    assert call_kwargs["prompt"] == expected_prompt


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_execute_node_input_mappings_with_state_prefix(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Should handle {state.field} in input mapping templates"""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config with {state.X} in input mappings
    node_config = NodeConfig(
        id="test_node",
        inputs={
            "query": "{state.topic}",  # Using state. prefix in mapping
        },
        prompt="Research {query}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock output model and LLM
    mock_build_output.return_value = SimpleOutput
    mock_call_llm.return_value = (SimpleOutput(result="Research"), make_usage())

    # Execute node
    updated_state = execute_node(node_config, state)

    # Verify prompt resolved correctly
    mock_call_llm.assert_called_once()
    call_kwargs = mock_call_llm.call_args[1]
    assert call_kwargs["prompt"] == "Research AI"


# ============================================
# Test: Tool loading
# ============================================


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
@patch("configurable_agents.core.node_executor.get_tool")
def test_execute_node_with_tools(
    mock_get_tool, mock_build_output, mock_create_llm, mock_call_llm
):
    """Should load tools and bind to LLM"""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config with tools
    node_config = NodeConfig(
        id="search_node",
        prompt="Search for {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
        tools=["serper_search"],
    )

    # Mock tool
    mock_tool = Mock()
    mock_get_tool.return_value = mock_tool

    # Mock output model and LLM
    mock_build_output.return_value = SimpleOutput
    mock_call_llm.return_value = (SimpleOutput(result="Search results"), make_usage())

    # Execute node
    updated_state = execute_node(node_config, state)

    # Verify tool was loaded
    mock_get_tool.assert_called_once_with("serper_search")

    # Verify tools passed to LLM
    mock_call_llm.assert_called_once()
    call_kwargs = mock_call_llm.call_args[1]
    assert call_kwargs["tools"] == [mock_tool]


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
@patch("configurable_agents.core.node_executor.get_tool")
def test_execute_node_multiple_tools(
    mock_get_tool, mock_build_output, mock_create_llm, mock_call_llm
):
    """Should load multiple tools"""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config with multiple tools
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
        tools=["tool1", "tool2"],
    )

    # Mock tools
    mock_tool1 = Mock()
    mock_tool2 = Mock()
    mock_get_tool.side_effect = [mock_tool1, mock_tool2]

    # Mock output model and LLM
    mock_build_output.return_value = SimpleOutput
    mock_call_llm.return_value = (SimpleOutput(result="Result"), make_usage())

    # Execute node
    updated_state = execute_node(node_config, state)

    # Verify all tools loaded
    assert mock_get_tool.call_count == 2
    mock_get_tool.assert_any_call("tool1")
    mock_get_tool.assert_any_call("tool2")

    # Verify tools passed to LLM
    call_kwargs = mock_call_llm.call_args[1]
    assert call_kwargs["tools"] == [mock_tool1, mock_tool2]


# ============================================
# Test: LLM configuration merging
# ============================================


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
@patch("configurable_agents.core.node_executor.merge_llm_config")
def test_execute_node_llm_config_merging(
    mock_merge_config, mock_build_output, mock_create_llm, mock_call_llm
):
    """Should merge node-level and global LLM configs"""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config with node-level LLM config
    node_llm_config = LLMConfig(temperature=0.7)
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
        llm=node_llm_config,
    )

    # Setup global config
    global_llm_config = LLMConfig(model="gemini-1.5-flash", temperature=0.5)
    global_config = GlobalConfig(llm=global_llm_config)

    # Mock merge result
    merged_config = LLMConfig(model="gemini-1.5-flash", temperature=0.7)
    mock_merge_config.return_value = merged_config

    # Mock output model and LLM
    mock_build_output.return_value = SimpleOutput
    mock_call_llm.return_value = (SimpleOutput(result="Result"), make_usage())

    # Execute node
    updated_state = execute_node(node_config, state, global_config)

    # Verify merge_llm_config was called with node and global configs
    mock_merge_config.assert_called_once_with(node_llm_config, global_llm_config)

    # Verify create_llm was called with merged config
    mock_create_llm.assert_called_once_with(merged_config)


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_execute_node_max_retries_from_global_config(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Should use max_retries from global execution config"""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Setup global config with custom max_retries
    global_config = GlobalConfig(execution=ExecutionConfig(max_retries=5))

    # Mock output model and LLM
    mock_build_output.return_value = SimpleOutput
    mock_call_llm.return_value = (SimpleOutput(result="Result"), make_usage())

    # Execute node
    updated_state = execute_node(node_config, state, global_config)

    # Verify call_llm_structured was called with max_retries=5
    mock_call_llm.assert_called_once()
    call_kwargs = mock_call_llm.call_args[1]
    assert call_kwargs["max_retries"] == 5


# ============================================
# Test: Error handling
# ============================================


@patch("configurable_agents.core.node_executor.resolve_prompt")
def test_execute_node_input_mapping_resolution_error(mock_resolve):
    """Should raise NodeExecutionError if input mapping resolution fails"""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config with input mapping
    node_config = NodeConfig(
        id="test_node",
        inputs={"query": "{unknown_field}"},  # Invalid field
        prompt="Process {query}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock resolve_prompt to raise error on first call (input mapping)
    from configurable_agents.core.template import TemplateResolutionError

    mock_resolve.side_effect = TemplateResolutionError("Field not found", "unknown_field")

    # Execute node should raise NodeExecutionError
    with pytest.raises(NodeExecutionError) as exc_info:
        execute_node(node_config, state)

    assert "test_node" in str(exc_info.value)
    assert "Failed to resolve input mapping" in str(exc_info.value)
    assert "query" in str(exc_info.value)


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
@patch("configurable_agents.core.node_executor.resolve_prompt")
def test_execute_node_prompt_resolution_error(
    mock_resolve, mock_build_output, mock_create_llm, mock_call_llm
):
    """Should raise NodeExecutionError if prompt resolution fails"""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {unknown}",  # Unknown variable
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock resolve_prompt to raise error on second call (prompt resolution)
    from configurable_agents.core.template import TemplateResolutionError

    mock_resolve.side_effect = TemplateResolutionError("Variable not found", "unknown")

    # Execute node should raise NodeExecutionError
    with pytest.raises(NodeExecutionError) as exc_info:
        execute_node(node_config, state)

    assert "test_node" in str(exc_info.value)
    assert "Prompt template resolution failed" in str(exc_info.value)


@patch("configurable_agents.core.node_executor.get_tool")
def test_execute_node_tool_not_found_error(mock_get_tool):
    """Should raise NodeExecutionError if tool not found"""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config with invalid tool
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
        tools=["unknown_tool"],
    )

    # Mock get_tool to raise error
    from configurable_agents.tools import ToolNotFoundError

    mock_get_tool.side_effect = ToolNotFoundError("unknown_tool", ["serper_search"])

    # Execute node should raise NodeExecutionError
    with pytest.raises(NodeExecutionError) as exc_info:
        execute_node(node_config, state)

    assert "test_node" in str(exc_info.value)
    assert "Tool loading failed" in str(exc_info.value)


@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_execute_node_llm_creation_error(mock_build_output, mock_create_llm):
    """Should raise NodeExecutionError if LLM creation fails"""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock create_llm to raise error
    from configurable_agents.llm import LLMConfigError

    mock_create_llm.side_effect = LLMConfigError("API key not set")

    # Execute node should raise NodeExecutionError
    with pytest.raises(NodeExecutionError) as exc_info:
        execute_node(node_config, state)

    assert "test_node" in str(exc_info.value)
    assert "LLM creation failed" in str(exc_info.value)


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_execute_node_output_model_build_error(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Should raise NodeExecutionError if output model creation fails"""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock build_output_model to raise error
    from configurable_agents.core.output_builder import OutputBuilderError

    mock_build_output.side_effect = OutputBuilderError("Invalid output schema")

    # Execute node should raise NodeExecutionError
    with pytest.raises(NodeExecutionError) as exc_info:
        execute_node(node_config, state)

    assert "test_node" in str(exc_info.value)
    assert "Output model creation failed" in str(exc_info.value)


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_execute_node_llm_call_error(mock_build_output, mock_create_llm, mock_call_llm):
    """Should raise NodeExecutionError if LLM call fails"""
    # Setup state
    state = SimpleState(topic="AI", research="", score=0)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock output model
    mock_build_output.return_value = SimpleOutput

    # Mock call_llm_structured to raise error
    from configurable_agents.llm import LLMAPIError

    mock_call_llm.side_effect = LLMAPIError("API timeout")

    # Execute node should raise NodeExecutionError
    with pytest.raises(NodeExecutionError) as exc_info:
        execute_node(node_config, state)

    assert "test_node" in str(exc_info.value)
    assert "LLM call failed" in str(exc_info.value)


# ============================================
# Test: State copy-on-write pattern
# ============================================


@patch("configurable_agents.core.node_executor.call_llm_structured")
@patch("configurable_agents.core.node_executor.create_llm")
@patch("configurable_agents.core.node_executor.build_output_model")
def test_execute_node_state_is_copied(
    mock_build_output, mock_create_llm, mock_call_llm
):
    """Should return new state instance (copy-on-write)"""
    # Setup state
    original_state = SimpleState(topic="AI", research="old", score=5)

    # Setup node config
    node_config = NodeConfig(
        id="test_node",
        prompt="Process {topic}",
        output_schema=OutputSchema(type="str"),
        outputs=["research"],
    )

    # Mock output model and LLM
    mock_build_output.return_value = SimpleOutput
    mock_call_llm.return_value = (SimpleOutput(result="new research"), make_usage())

    # Execute node
    updated_state = execute_node(node_config, original_state)

    # Verify new instance
    assert updated_state is not original_state

    # Verify original state unchanged
    assert original_state.research == "old"
    assert original_state.score == 5

    # Verify updated state has changes
    assert updated_state["research"] == "new research"
    # execute_node returns only updated fields (partial state dict)
    assert "score" not in updated_state
