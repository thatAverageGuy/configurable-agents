"""Tests for runtime feature gating."""

import warnings

import pytest

from configurable_agents.config import (
    EdgeConfig,
    FlowMetadata,
    GlobalConfig,
    NodeConfig,
    ObservabilityConfig,
    ObservabilityMLFlowConfig,
    OutputSchema,
    Route,
    RouteCondition,
    StateFieldConfig,
    StateSchema,
    WorkflowConfig,
)
from configurable_agents.runtime import (
    UnsupportedFeatureError,
    check_feature_support,
    get_supported_features,
    validate_runtime_support,
)


# ============================================
# Test Fixtures
# ============================================


def make_minimal_config(**overrides) -> WorkflowConfig:
    """Create a minimal valid v0.1 config."""
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
# Valid v0.1 Config Tests
# ============================================


def test_valid_minimal_config():
    """Test that minimal v0.1 config passes feature gate."""
    config = make_minimal_config()
    # Should not raise
    validate_runtime_support(config)


def test_valid_config_with_multiple_nodes():
    """Test that multi-node linear workflow passes."""
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
    validate_runtime_support(config)


def test_valid_config_with_basic_logging():
    """Test that basic logging config (v0.1 feature) passes."""
    from configurable_agents.config import ObservabilityLoggingConfig

    config = make_minimal_config(
        config=GlobalConfig(
            observability=ObservabilityConfig(
                logging=ObservabilityLoggingConfig(level="DEBUG")
            )
        )
    )
    # Should not raise or warn
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Turn warnings into errors
        validate_runtime_support(config)


# ============================================
# Conditional Routing Tests (NOW SUPPORTED)
# ============================================


def test_conditional_routing_supported():
    """Test that conditional routing is now supported in v0.2."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "score": StateFieldConfig(type="float", default=0.5),
                "output": StateFieldConfig(type="str", default=""),
            }
        ),
        edges=[
            EdgeConfig(
                from_="START",
                routes=[
                    Route(condition=RouteCondition(logic="state.score > 0.8"), to="END"),
                    Route(condition=RouteCondition(logic="default"), to="END"),
                ],
            ),
        ],
    )

    # Should not raise - conditional routing is now supported
    validate_runtime_support(config)


def test_conditional_routing_with_default_route():
    """Test that conditional edges with default route are supported."""
    config = make_minimal_config(
        state=StateSchema(
            fields={
                "input": StateFieldConfig(type="str", required=True),
                "approved": StateFieldConfig(type="bool", default=False),
                "output": StateFieldConfig(type="str", default=""),
            }
        ),
        edges=[
            EdgeConfig(
                from_="START",
                routes=[
                    Route(condition=RouteCondition(logic="state.approved"), to="END"),
                    Route(condition=RouteCondition(logic="default"), to="END"),
                ],
            ),
        ],
    )

    # Should not raise - conditional routing is now supported
    validate_runtime_support(config)


# ============================================
# Observability Tests (v0.2+ - SOFT BLOCK)
# ============================================


def test_mlflow_observability_supported():
    """Test that MLFlow observability is supported in v0.1 (no warning)."""
    config = make_minimal_config(
        config=GlobalConfig(
            observability=ObservabilityConfig(
                mlflow=ObservabilityMLFlowConfig(
                    enabled=True,
                    experiment="test_experiment",
                )
            )
        )
    )

    # MLFlow is now fully supported in v0.1 - no warning should be raised
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Turn warnings into errors
        validate_runtime_support(config)  # Should not raise


def test_mlflow_disabled_no_warning():
    """Test that disabled MLFlow doesn't trigger warning."""
    config = make_minimal_config(
        config=GlobalConfig(
            observability=ObservabilityConfig(
                mlflow=ObservabilityMLFlowConfig(enabled=False)
            )
        )
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        # Should not raise
        validate_runtime_support(config)


# ============================================
# Feature Support Query Tests
# ============================================


def test_get_supported_features():
    """Test getting list of supported features."""
    features = get_supported_features()

    assert "version" in features
    assert features["version"] == "0.2.0-dev"

    assert "flow_control" in features
    assert "Linear workflows (START -> nodes -> END)" in features["flow_control"]
    # Conditional routing, loops, and parallel are now supported
    assert "Conditional routing (if/else based on state)" in features["flow_control"]
    assert "Loops and retries (with iteration limits)" in features["flow_control"]
    assert "Parallel node execution (fan-out/fan-in)" in features["flow_control"]

    assert "state" in features
    assert "nodes" in features
    assert "llm" in features
    assert "validation" in features

    assert "not_supported" in features
    assert "v0.4" in features["not_supported"]


def test_check_feature_support_supported():
    """Test checking support for a v0.2 feature (now supported)."""
    result = check_feature_support("Conditional routing (if/else based on state)")

    assert result["supported"] is True
    assert result["version"] == "0.2.0-dev"
    assert "Available now" in result["timeline"]


def test_check_feature_support_unknown():
    """Test checking support for unknown feature."""
    result = check_feature_support("Quantum computing integration")

    assert result["supported"] is False
    assert result["version"] == "unknown"
    assert "Not in current roadmap" in result["timeline"]


# ============================================
# Integration Tests
# ============================================


def test_complex_valid_v01_config():
    """Test that a complex but valid v0.1 config passes all checks."""
    from configurable_agents.config import (
        ExecutionConfig,
        LLMConfig,
        ObservabilityLoggingConfig,
        OutputSchemaField,
    )

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
                "summary": StateFieldConfig(type="str", default=""),
            }
        ),
        nodes=[
            NodeConfig(
                id="generate_query",
                prompt="Generate search query for: {topic}",
                outputs=["query"],
                output_schema=OutputSchema(type="str"),
            ),
            NodeConfig(
                id="summarize",
                prompt="Summarize: {query}",
                outputs=["summary"],
                output_schema=OutputSchema(type="str"),
                llm=LLMConfig(temperature=0.3),  # Node-level LLM override (v0.1)
            ),
        ],
        edges=[
            EdgeConfig(from_="START", to="generate_query"),
            EdgeConfig(from_="generate_query", to="summarize"),
            EdgeConfig(from_="summarize", to="END"),
        ],
        config=GlobalConfig(
            llm=LLMConfig(provider="google", model="gemini-pro", temperature=0.7),
            execution=ExecutionConfig(timeout=120, max_retries=3),
            observability=ObservabilityConfig(
                logging=ObservabilityLoggingConfig(level="INFO")
            ),
        ),
    )

    # Should pass without errors or warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        validate_runtime_support(config)
