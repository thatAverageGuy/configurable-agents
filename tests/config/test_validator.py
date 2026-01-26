"""Tests for config validator."""

import pytest

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
from configurable_agents.config.validator import ValidationError, validate_config


# ============================================
# Test Fixtures
# ============================================


def make_minimal_config(**overrides) -> WorkflowConfig:
    """Create a minimal valid config for testing."""
    defaults = {
        "schema_version": "1.0",
        "flow": FlowMetadata(name="test_flow"),
        "state": StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "output": StateFieldConfig(type="str", default=""),
            }
        ),
        "nodes": [
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            )
        ],
        "edges": [
            EdgeConfig(from_="START", to="process"),
            EdgeConfig(from_="process", to="END"),
        ],
    }
    defaults.update(overrides)
    return WorkflowConfig(**defaults)


# ============================================
# Valid Config Tests
# ============================================


def test_valid_minimal_config():
    """Test that minimal valid config passes validation."""
    config = make_minimal_config()
    # Should not raise
    validate_config(config)


def test_valid_config_with_multiple_nodes():
    """Test valid config with multiple nodes."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "intermediate": StateFieldConfig(type="str", default=""),
                "output": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="step1",
                prompt="Process {input}",
                outputs=["intermediate"],
                output_schema=OutputSchema(type="str"),
            ),
            NodeConfig(
                id="step2",
                prompt="Refine {intermediate}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="step1"),
            EdgeConfig(from_="step1", to="step2"),
            EdgeConfig(from_="step2", to="END"),
        ],
    )
    validate_config(config)


def test_valid_config_with_object_output():
    """Test valid config with object output schema."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "title": StateFieldConfig(type="str", default=""),
                "summary": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["title", "summary"],
                output_schema=OutputSchema(
                    type="object",
                    fields=[
                        OutputSchemaField(name="title", type="str"),
                        OutputSchemaField(name="summary", type="str"),
                    ],
                ),
            )
        ],
    )
    validate_config(config)


def test_valid_config_with_input_mapping():
    """Test valid config with input mappings."""
    config = make_minimal_config(
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {topic}",
                inputs={"topic": "input"},
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            )
        ],
    )
    validate_config(config)


# ============================================
# Edge Reference Validation Tests
# ============================================


def test_invalid_edge_from_unknown_node():
    """Test that edge from unknown node fails."""
    config = make_minimal_config(
        edges=[
            EdgeConfig(from_="START", to="process"),
            EdgeConfig(from_="unknown", to="END"),
        ]
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "unknown node 'unknown'" in str(exc_info.value)
    assert "Did you mean" in str(exc_info.value) or "Valid nodes" in str(exc_info.value)


def test_invalid_edge_to_unknown_node():
    """Test that edge to unknown node fails."""
    config = make_minimal_config(
        edges=[
            EdgeConfig(from_="START", to="missing"),
            EdgeConfig(from_="process", to="END"),
        ]
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "unknown node 'missing'" in str(exc_info.value)


def test_edge_suggestion_for_typo():
    """Test that similar node names are suggested for typos."""
    config = make_minimal_config(
        edges=[
            EdgeConfig(from_="START", to="proces"),  # typo: missing 's'
            EdgeConfig(from_="process", to="END"),
        ]
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "Did you mean 'process'?" in str(exc_info.value)


# ============================================
# Node Output Validation Tests
# ============================================


def test_invalid_node_output_not_in_state():
    """Test that node output not in state fails."""
    config = make_minimal_config(
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["missing_field"],
                output_schema=OutputSchema(type="str"),
            )
        ]
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "output 'missing_field' not found in state fields" in str(exc_info.value)
    assert "Available fields" in str(exc_info.value)


def test_output_suggestion_for_typo():
    """Test that similar field names are suggested."""
    config = make_minimal_config(
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["outpt"],  # typo
                output_schema=OutputSchema(type="str"),
            )
        ]
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "Did you mean 'output'?" in str(exc_info.value)


# ============================================
# Output Schema Alignment Tests
# ============================================


def test_invalid_object_schema_missing_fields():
    """Test that object output schema without fields fails at Pydantic level."""
    # This is actually caught by Pydantic validation (which is good!)
    from pydantic import ValidationError as PydanticValidationError

    with pytest.raises(PydanticValidationError) as exc_info:
        config = make_minimal_config(
            nodes=[
                NodeConfig(
                    id="process",
                    prompt="Process {input}",
                    outputs=["output"],
                    output_schema=OutputSchema(type="object", fields=[]),
                )
            ]
        )
    assert "must have fields" in str(exc_info.value)


def test_invalid_outputs_not_in_schema():
    """Test that outputs not in schema fields fails."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "title": StateFieldConfig(type="str", default=""),
                "summary": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["title", "summary"],
                output_schema=OutputSchema(
                    type="object",
                    fields=[
                        OutputSchemaField(name="title", type="str"),
                        # Missing summary!
                    ],
                ),
            )
        ],
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "not defined in output_schema.fields" in str(exc_info.value)


def test_invalid_schema_fields_not_in_outputs():
    """Test that schema fields not in outputs fails."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "title": StateFieldConfig(type="str", default=""),
                "extra": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["title"],
                output_schema=OutputSchema(
                    type="object",
                    fields=[
                        OutputSchemaField(name="title", type="str"),
                        OutputSchemaField(name="extra", type="str"),
                    ],
                ),
            )
        ],
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "not in outputs" in str(exc_info.value)


def test_invalid_simple_type_multiple_outputs():
    """Test that simple output type with multiple outputs fails."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "out1": StateFieldConfig(type="str", default=""),
                "out2": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["out1", "out2"],
                output_schema=OutputSchema(type="str"),
            )
        ],
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "simple type" in str(exc_info.value).lower()
    assert "2 items" in str(exc_info.value) or "multiple" in str(exc_info.value).lower()


# ============================================
# Type Alignment Tests
# ============================================


def test_invalid_output_type_mismatch():
    """Test that output type mismatch fails."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "output": StateFieldConfig(type="int", default=0),  # int, not str
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),  # str, not int
            )
        ],
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "type 'str'" in str(exc_info.value)
    assert "type 'int'" in str(exc_info.value)


def test_invalid_object_field_type_mismatch():
    """Test that object field type mismatch fails."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "title": StateFieldConfig(type="str", default=""),
                "count": StateFieldConfig(type="int", default=0),
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["title", "count"],
                output_schema=OutputSchema(
                    type="object",
                    fields=[
                        OutputSchemaField(name="title", type="str"),
                        OutputSchemaField(name="count", type="str"),  # Should be int
                    ],
                ),
            )
        ],
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "type 'str'" in str(exc_info.value)
    assert "type 'int'" in str(exc_info.value)


# ============================================
# Prompt Placeholder Tests
# ============================================


def test_invalid_prompt_placeholder_unknown_field():
    """Test that unknown placeholder fails."""
    config = make_minimal_config(
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {unknown_field}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            )
        ]
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "placeholder '{unknown_field}'" in str(exc_info.value)


def test_invalid_prompt_placeholder_with_state_prefix():
    """Test that state.unknown_field fails."""
    config = make_minimal_config(
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {state.missing}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            )
        ]
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "state.missing" in str(exc_info.value)


def test_valid_prompt_placeholder_with_state_prefix():
    """Test that state.valid_field passes."""
    config = make_minimal_config(
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {state.input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            )
        ]
    )
    validate_config(config)


def test_valid_prompt_placeholder_from_input_mapping():
    """Test that placeholders from input mapping are valid."""
    config = make_minimal_config(
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {topic}",
                inputs={"topic": "input"},
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            )
        ]
    )
    validate_config(config)


# ============================================
# State Type Validation Tests
# ============================================


def test_invalid_state_field_type():
    """Test that invalid state field type fails."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="invalid_type", required=True),
                "output": StateFieldConfig(type="str", default=""),
            }
        )
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "invalid type" in str(exc_info.value).lower()


def test_valid_state_complex_types():
    """Test that complex state types are valid."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "items": StateFieldConfig(type="list[str]", default=[]),
                "mapping": StateFieldConfig(type="dict[str, int]", default={}),
                "output": StateFieldConfig(type="str", default=""),
            }
        )
    )
    validate_config(config)


# ============================================
# Graph Structure Tests
# ============================================


def test_invalid_no_edge_from_start():
    """Test that missing START edge fails."""
    config = make_minimal_config(
        edges=[
            EdgeConfig(from_="process", to="END"),
        ]
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "No edge from START" in str(exc_info.value)


def test_invalid_multiple_edges_from_start():
    """Test that multiple START edges fail."""
    config = make_minimal_config(
        nodes=[
            NodeConfig(
                id="process1",
                prompt="Process {input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            ),
            NodeConfig(
                id="process2",
                prompt="Process {input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="process1"),
            EdgeConfig(from_="START", to="process2"),
            EdgeConfig(from_="process1", to="END"),
            EdgeConfig(from_="process2", to="END"),
        ],
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "Multiple edges from START" in str(exc_info.value)


def test_invalid_unreachable_node():
    """Test that unreachable node fails."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "output": StateFieldConfig(type="str", default=""),
                "other": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            ),
            NodeConfig(
                id="orphan",
                prompt="Orphan {input}",
                outputs=["other"],
                output_schema=OutputSchema(type="str"),
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="process"),
            EdgeConfig(from_="process", to="END"),
            # No edge to/from orphan
        ],
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "not reachable from START" in str(exc_info.value)
    assert "orphan" in str(exc_info.value)


def test_invalid_node_cannot_reach_end():
    """Test that node without path to END fails."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "output": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="process"),
            # Missing edge to END
        ],
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "cannot reach END" in str(exc_info.value)


# ============================================
# Linear Flow Tests (v0.1 Constraints)
# ============================================


def test_invalid_conditional_routing():
    """Test that conditional routing fails in v0.1."""
    from configurable_agents.config import Route, RouteCondition

    config = make_minimal_config(
        edges=[
            EdgeConfig(
                from_="START",
                routes=[
                    Route(condition=RouteCondition(logic="true"), to="process"),
                ],
            ),
            EdgeConfig(from_="process", to="END"),
        ]
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "Conditional routing not supported in v0.1" in str(exc_info.value)
    assert "v0.2+" in str(exc_info.value)


def test_invalid_multiple_outgoing_edges():
    """Test that multiple outgoing edges fail in v0.1."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "output": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            ),
            NodeConfig(
                id="other",
                prompt="Other {input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="process"),
            EdgeConfig(from_="process", to="other"),
            EdgeConfig(from_="process", to="END"),  # Multiple from process
        ],
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "2 outgoing edges" in str(exc_info.value)
    assert "linear flows only" in str(exc_info.value).lower()


def test_invalid_cycle_in_graph():
    """Test that cycles fail in v0.1."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "temp": StateFieldConfig(type="str", default=""),
                "output": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="step1",
                prompt="Step 1 {input}",
                outputs=["temp"],
                output_schema=OutputSchema(type="str"),
            ),
            NodeConfig(
                id="step2",
                prompt="Step 2 {temp}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="step1"),
            EdgeConfig(from_="step1", to="step2"),
            EdgeConfig(from_="step2", to="step1"),  # Cycle!
        ],
    )
    with pytest.raises(ValidationError) as exc_info:
        validate_config(config)
    assert "Cycle detected" in str(exc_info.value)
    assert "step1" in str(exc_info.value)
    assert "step2" in str(exc_info.value)


# ============================================
# Integration Tests
# ============================================


def test_complex_valid_workflow():
    """Test a complex valid workflow passes all validation."""
    config = WorkflowConfig(
        schema_version="1.0",
        flow=FlowMetadata(
            name="research_workflow",
            description="Multi-step research workflow",
            version="1.0.0",
        ),
        state=StateSchema(
            fields={
                "topic": StateFieldConfig(type="str", required=True),
                "query": StateFieldConfig(type="str", default=""),
                "results": StateFieldConfig(type="list[str]", default=[]),
                "summary": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="generate_query",
                prompt="Generate search query for topic: {state.topic}",
                outputs=["query"],
                output_schema=OutputSchema(type="str"),
            ),
            NodeConfig(
                id="summarize",
                prompt="Summarize results: {results}",
                inputs={"results": "results"},
                outputs=["summary"],
                output_schema=OutputSchema(type="str"),
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="generate_query"),
            EdgeConfig(from_="generate_query", to="summarize"),
            EdgeConfig(from_="summarize", to="END"),
        ],
    )
    validate_config(config)
