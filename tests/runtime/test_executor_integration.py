"""Integration tests for runtime executor with real components."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from configurable_agents.runtime import run_workflow, run_workflow_from_config


# ============================================
# Integration Tests (no mocking)
# ============================================


@pytest.mark.integration
def test_run_workflow_from_config_full_integration():
    """Test full workflow execution with real components (mocked LLM only)."""
    # Create a valid config with minimal setup
    from configurable_agents.config import (
        EdgeConfig,
        FlowMetadata,
        NodeConfig,
        OutputSchema,
        OutputSchemaField,
        StateFieldConfig,
        StateSchema,
        WorkflowConfig,
    )

    config = WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="integration_test"),
        state=StateSchema(
            fields={
                "topic": StateFieldConfig(type="str", required=True),
                "article": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="write",
                prompt="Write a short article about {state.topic}",
                outputs=["article"],
                output_schema=OutputSchema(
                    type="object",
                    fields=[
                        OutputSchemaField(
                            name="article",
                            type="str",
                            description="The article text",
                        )
                    ],
                ),
            )
        ],
        edges=[
            EdgeConfig(from_="START", to="write"),
            EdgeConfig(from_="write", to="END"),
        ],
    )

    # Mock only the LLM call (everything else is real)
    with patch("configurable_agents.core.node_executor.create_llm") as mock_create_llm:
        # Mock LLM that returns structured output
        mock_llm = Mock()
        mock_llm.with_structured_output.return_value.invoke.return_value = Mock(
            article="This is an article about AI Safety."
        )
        mock_create_llm.return_value = mock_llm

        # Execute workflow (real validation, real state building, real graph building)
        result = run_workflow_from_config(config, {"topic": "AI Safety"})

        # Verify result
        assert isinstance(result, dict)
        assert "topic" in result
        assert "article" in result
        assert result["topic"] == "AI Safety"
        assert result["article"] == "This is an article about AI Safety."


@pytest.mark.integration
def test_run_workflow_from_file_full_integration(tmp_path):
    """Test full workflow execution from file with real components (mocked LLM only)."""
    # Create a valid config file
    config_yaml = """
schema_version: "1.0"
flow:
  name: file_integration_test

state:
  fields:
    name: {type: str, required: true}
    greeting: {type: str, default: ""}

nodes:
  - id: greet
    prompt: "Generate a friendly greeting for {state.name}"
    outputs: [greeting]
    output_schema:
      type: object
      fields:
        - name: greeting
          type: str
          description: A friendly greeting message

edges:
  - {from: START, to: greet}
  - {from: greet, to: END}
"""
    config_path = tmp_path / "test_workflow.yaml"
    config_path.write_text(config_yaml)

    # Mock only the LLM call
    with patch("configurable_agents.core.node_executor.create_llm") as mock_create_llm:
        # Mock LLM
        mock_llm = Mock()
        mock_llm.with_structured_output.return_value.invoke.return_value = Mock(
            greeting="Hello Alice, nice to meet you!"
        )
        mock_create_llm.return_value = mock_llm

        # Execute workflow from file
        result = run_workflow(str(config_path), {"name": "Alice"})

        # Verify result
        assert isinstance(result, dict)
        assert "name" in result
        assert "greeting" in result
        assert result["name"] == "Alice"
        assert result["greeting"] == "Hello Alice, nice to meet you!"


@pytest.mark.integration
def test_run_workflow_with_nested_state():
    """Test workflow with nested state objects."""
    from configurable_agents.config import (
        EdgeConfig,
        FlowMetadata,
        NodeConfig,
        OutputSchema,
        OutputSchemaField,
        StateFieldConfig,
        StateSchema,
        WorkflowConfig,
    )

    config = WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="nested_state_test"),
        state=StateSchema(
            fields={
                "query": StateFieldConfig(type="str", required=True),
                "metadata": StateFieldConfig(
                    type="object",
                    required=False,
                    schema={
                        "source": StateFieldConfig(type="str", default="user"),
                        "timestamp": StateFieldConfig(type="int", default=0),
                    },
                ),
                "result": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process query: {state.query}",
                outputs=["result"],
                output_schema=OutputSchema(
                    type="object",
                    fields=[
                        OutputSchemaField(name="result", type="str"),
                    ],
                ),
            )
        ],
        edges=[
            EdgeConfig(from_="START", to="process"),
            EdgeConfig(from_="process", to="END"),
        ],
    )

    # Mock LLM
    with patch("configurable_agents.core.node_executor.create_llm") as mock_create_llm:
        mock_llm = Mock()
        mock_llm.with_structured_output.return_value.invoke.return_value = Mock(
            result="Processed query successfully"
        )
        mock_create_llm.return_value = mock_llm

        # Execute with nested state
        result = run_workflow_from_config(
            config,
            {
                "query": "test query",
                "metadata": {"source": "api", "timestamp": 1234567890},
            },
        )

        # Verify nested state preserved
        assert result["query"] == "test query"
        assert result["metadata"]["source"] == "api"
        assert result["metadata"]["timestamp"] == 1234567890
        assert result["result"] == "Processed query successfully"


@pytest.mark.integration
def test_run_workflow_multi_node_pipeline():
    """Test workflow with multiple nodes in sequence."""
    from configurable_agents.config import (
        EdgeConfig,
        FlowMetadata,
        NodeConfig,
        OutputSchema,
        OutputSchemaField,
        StateFieldConfig,
        StateSchema,
        WorkflowConfig,
    )

    config = WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(name="multi_node_test"),
        state=StateSchema(
            fields={
                "topic": StateFieldConfig(type="str", required=True),
                "outline": StateFieldConfig(type="str", default=""),
                "article": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="create_outline",
                prompt="Create an outline for: {state.topic}",
                outputs=["outline"],
                output_schema=OutputSchema(
                    type="object",
                    fields=[
                        OutputSchemaField(name="outline", type="str"),
                    ],
                ),
            ),
            NodeConfig(
                id="write_article",
                prompt="Write article based on: {state.outline}",
                outputs=["article"],
                output_schema=OutputSchema(
                    type="object",
                    fields=[
                        OutputSchemaField(name="article", type="str"),
                    ],
                ),
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="create_outline"),
            EdgeConfig(from_="create_outline", to="write_article"),
            EdgeConfig(from_="write_article", to="END"),
        ],
    )

    # Mock LLM with different responses per node
    with patch("configurable_agents.core.node_executor.create_llm") as mock_create_llm:
        mock_llm = Mock()

        # First call returns outline, second call returns article
        mock_llm.with_structured_output.return_value.invoke.side_effect = [
            Mock(outline="1. Introduction\n2. Main points\n3. Conclusion"),
            Mock(article="Full article based on the outline..."),
        ]
        mock_create_llm.return_value = mock_llm

        # Execute multi-node workflow
        result = run_workflow_from_config(config, {"topic": "Python Programming"})

        # Verify both nodes executed
        assert result["topic"] == "Python Programming"
        assert result["outline"] == "1. Introduction\n2. Main points\n3. Conclusion"
        assert result["article"] == "Full article based on the outline..."

        # Verify LLM was called twice (once per node)
        assert mock_llm.with_structured_output.return_value.invoke.call_count == 2
