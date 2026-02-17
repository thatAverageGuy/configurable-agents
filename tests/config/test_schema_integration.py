"""Integration tests for config schema - loading YAML/JSON into Pydantic models."""

import tempfile
from pathlib import Path

import pytest
import yaml

from configurable_agents.config import WorkflowConfig, parse_config_file


class TestSchemaIntegration:
    """Test loading complete configs from YAML/JSON into Pydantic models."""

    def test_load_minimal_yaml_config(self):
        """Test loading a minimal valid YAML config."""
        config_yaml = """
schema_version: "1.0"

flow:
  name: minimal_flow

state:
  fields:
    input:
      type: str
      required: true
    output:
      type: str
      default: ""

nodes:
  - id: process
    prompt: "Process {state.input}"
    output_schema:
      type: str
    outputs: [output]

edges:
  - from: START
    to: process
  - from: process
    to: END
"""
        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            temp_path = f.name

        try:
            # Load YAML to dict
            config_dict = parse_config_file(temp_path)

            # Parse into Pydantic model
            config = WorkflowConfig(**config_dict)

            # Verify structure
            assert config.schema_version == "1.0"
            assert config.flow.name == "minimal_flow"
            assert len(config.state.fields) == 2
            assert "input" in config.state.fields
            assert config.state.fields["input"].required is True
            assert len(config.nodes) == 1
            assert config.nodes[0].id == "process"
            assert len(config.edges) == 2
        finally:
            Path(temp_path).unlink()

    def test_load_complete_yaml_config(self):
        """Test loading a complete YAML config with all features."""
        config_yaml = """
schema_version: "1.0"

flow:
  name: article_generator
  description: Research topics and write articles
  version: 1.0.0

state:
  fields:
    topic:
      type: str
      required: true
      description: Topic to research

    research_summary:
      type: str
      default: ""

    sources:
      type: list[str]
      default: []

    article:
      type: str
      default: ""

    word_count:
      type: int
      default: 0

nodes:
  - id: research
    description: Research the topic using web search
    inputs:
      query: "{state.topic}"
    prompt: |
      Research this topic: {query}
      Provide a summary and list of sources.
    output_schema:
      type: object
      fields:
        - name: research_summary
          type: str
          description: Research summary
        - name: sources
          type: list[str]
          description: Source URLs
    outputs: [research_summary, sources]
    tools:
      - serper_search
    llm:
      temperature: 0.3

  - id: write
    description: Write article based on research
    inputs:
      topic: "{state.topic}"
      research: "{state.research_summary}"
    prompt: |
      Write an article about {topic}.
      Use this research: {research}
    output_schema:
      type: object
      fields:
        - name: article
          type: str
        - name: word_count
          type: int
    outputs: [article, word_count]
    llm:
      temperature: 0.9

edges:
  - from: START
    to: research
  - from: research
    to: write
  - from: write
    to: END

config:
  llm:
    provider: google
    model: gemini-2.5-flash-lite
    temperature: 0.7
  execution:
    timeout: 180
    max_retries: 3
  observability:
    logging:
      level: INFO
"""
        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            temp_path = f.name

        try:
            # Load and parse
            config_dict = parse_config_file(temp_path)
            config = WorkflowConfig(**config_dict)

            # Verify flow metadata
            assert config.flow.name == "article_generator"
            assert config.flow.description == "Research topics and write articles"
            assert config.flow.version == "1.0.0"

            # Verify state
            assert len(config.state.fields) == 5
            assert config.state.fields["topic"].required is True
            assert config.state.fields["sources"].type == "list[str]"

            # Verify nodes
            assert len(config.nodes) == 2
            research_node = config.nodes[0]
            assert research_node.id == "research"
            assert research_node.description == "Research the topic using web search"
            assert research_node.inputs == {"query": "{state.topic}"}
            assert research_node.tools == ["serper_search"]
            assert research_node.llm.temperature == 0.3
            assert research_node.output_schema.type == "object"
            assert len(research_node.output_schema.fields) == 2

            write_node = config.nodes[1]
            assert write_node.id == "write"
            assert write_node.llm.temperature == 0.9

            # Verify edges
            assert len(config.edges) == 3
            assert config.edges[0].from_ == "START"
            assert config.edges[0].to == "research"

            # Verify global config
            assert config.config.llm.provider == "google"
            assert config.config.llm.model == "gemini-2.5-flash-lite"
            assert config.config.execution.timeout == 180
            assert config.config.observability.logging.level == "INFO"

        finally:
            Path(temp_path).unlink()

    def test_load_config_with_conditional_edges(self):
        """Test loading config with conditional edges (v0.2+ feature)."""
        config_yaml = """
schema_version: "1.0"

flow:
  name: conditional_flow

state:
  fields:
    input:
      type: str
      required: true
    score:
      type: int
      default: 0

nodes:
  - id: evaluate
    prompt: "Evaluate {state.input}"
    output_schema:
      type: int
    outputs: [score]

edges:
  - from: START
    to: evaluate
  - from: evaluate
    routes:
      - condition:
          logic: "{state.score} >= 8"
        to: END
      - condition:
          logic: "default"
        to: evaluate
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            temp_path = f.name

        try:
            config_dict = parse_config_file(temp_path)
            config = WorkflowConfig(**config_dict)

            # Verify conditional edge
            assert len(config.edges) == 2
            conditional_edge = config.edges[1]
            assert conditional_edge.from_ == "evaluate"
            assert conditional_edge.to is None  # No 'to' for conditional
            assert conditional_edge.routes is not None
            assert len(conditional_edge.routes) == 2
            assert conditional_edge.routes[0].condition.logic == "{state.score} >= 8"
            assert conditional_edge.routes[0].to == "END"

        finally:
            Path(temp_path).unlink()

    def test_invalid_config_fails(self):
        """Test that invalid configs raise validation errors."""
        config_yaml = """
schema_version: "1.0"

flow:
  name: ""  # Empty name should fail

state:
  fields:
    input:
      type: str

nodes:
  - id: node1
    prompt: "Test"
    output_schema:
      type: str
    outputs: [input]

edges:
  - from: START
    to: node1
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(config_yaml)
            temp_path = f.name

        try:
            config_dict = parse_config_file(temp_path)
            with pytest.raises(Exception):  # Pydantic ValidationError
                WorkflowConfig(**config_dict)
        finally:
            Path(temp_path).unlink()

    def test_model_dump_for_export(self):
        """Test that configs can be dumped back to dict/YAML/JSON."""
        config = WorkflowConfig(
            schema_version="1.0",
            flow={"name": "test_flow"},
            state={"fields": {"input": {"type": "str"}}},
            nodes=[
                {
                    "id": "node1",
                    "prompt": "Test",
                    "output_schema": {"type": "str"},
                    "outputs": ["input"],
                }
            ],
            edges=[{"from": "START", "to": "node1"}],
        )

        # Dump to dict
        config_dict = config.model_dump(by_alias=True, exclude_none=True)

        # Verify structure
        assert config_dict["schema_version"] == "1.0"
        assert "from" in config_dict["edges"][0]  # Uses alias

        # Verify we can convert to YAML
        yaml_str = yaml.dump(config_dict)
        assert "schema_version" in yaml_str
        assert "START" in yaml_str

        # Verify we can reload it
        reloaded_dict = yaml.safe_load(yaml_str)
        reloaded_config = WorkflowConfig(**reloaded_dict)
        assert reloaded_config.flow.name == "test_flow"
