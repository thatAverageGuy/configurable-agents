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
    OptimizationConfig,
    OptimizeConfig,
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
# Conditional Routing Tests (v0.2+ - HARD BLOCK)
# ============================================


def test_conditional_routing_blocked():
    """Test that conditional routing raises UnsupportedFeatureError."""
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

    with pytest.raises(UnsupportedFeatureError) as exc_info:
        validate_runtime_support(config)

    error = exc_info.value
    assert error.feature == "Conditional routing (edge routes)"
    assert error.available_in == "v0.2"
    assert "8-12 weeks" in error.timeline
    assert "linear edges" in error.workaround.lower()
    assert "v0.2" in str(error)


def test_conditional_routing_error_message():
    """Test that conditional routing error has helpful message."""
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

    with pytest.raises(UnsupportedFeatureError) as exc_info:
        validate_runtime_support(config)

    error_msg = str(exc_info.value)
    assert "not supported in v0.1" in error_msg
    assert "Available in: v0.2" in error_msg
    assert "timeline" in error_msg.lower()
    assert "roadmap" in error_msg.lower()


# ============================================
# Optimization Tests (v0.3+ - SOFT BLOCK)
# ============================================


def test_global_optimization_warns():
    """Test that global optimization config triggers warning."""
    config = make_minimal_config(
        optimization=OptimizationConfig(
            enabled=True,
            strategy="BootstrapFewShot",
            metric="semantic_match",
        )
    )

    with pytest.warns(UserWarning) as record:
        validate_runtime_support(config)

    # Should have exactly one warning
    assert len(record) == 1
    warning_msg = str(record[0].message)

    assert "DSPy optimization" in warning_msg
    assert "not supported in v0.1" in warning_msg
    assert "v0.3" in warning_msg
    assert "IGNORED" in warning_msg
    assert "12-16 weeks" in warning_msg


def test_optimization_disabled_no_warning():
    """Test that disabled optimization doesn't trigger warning."""
    config = make_minimal_config(
        optimization=OptimizationConfig(
            enabled=False,  # Disabled
            strategy="BootstrapFewShot",
        )
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Turn warnings into errors
        # Should not raise
        validate_runtime_support(config)


def test_node_level_optimization_warns():
    """Test that node-level optimization triggers warning."""
    config = make_minimal_config(
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
                optimize=OptimizeConfig(enabled=True, metric="accuracy"),
            )
        ]
    )

    with pytest.warns(UserWarning) as record:
        validate_runtime_support(config)

    assert len(record) == 1
    warning_msg = str(record[0].message)

    assert "Node-level optimization" in warning_msg
    assert "process" in warning_msg
    assert "not supported in v0.1" in warning_msg
    assert "v0.3" in warning_msg


def test_multiple_optimization_warnings():
    """Test that both global and node-level optimization trigger separate warnings."""
    config = make_minimal_config(
        optimization=OptimizationConfig(enabled=True),
        nodes=[
            NodeConfig(
                id="process",
                prompt="Process {input}",
                outputs=["output"],
                output_schema=OutputSchema(type="str"),
                optimize=OptimizeConfig(enabled=True),
            )
        ],
    )

    with pytest.warns(UserWarning) as record:
        validate_runtime_support(config)

    # Should have two warnings (global + node-level)
    assert len(record) == 2


# ============================================
# Observability Tests (v0.2+ - SOFT BLOCK)
# ============================================


def test_mlflow_observability_warns():
    """Test that MLFlow observability triggers warning."""
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

    with pytest.warns(UserWarning) as record:
        validate_runtime_support(config)

    assert len(record) == 1
    warning_msg = str(record[0].message)

    assert "MLFlow observability" in warning_msg
    assert "not supported in v0.1" in warning_msg
    assert "v0.2" in warning_msg
    assert "IGNORED" in warning_msg
    assert "console logging" in warning_msg.lower()


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
    assert features["version"] == "0.1.0-dev"

    assert "flow_control" in features
    assert "Linear workflows (START -> nodes -> END)" in features["flow_control"]

    assert "state" in features
    assert "nodes" in features
    assert "llm" in features
    assert "validation" in features

    assert "not_supported" in features
    assert "v0.2" in features["not_supported"]
    assert "v0.3" in features["not_supported"]


def test_check_feature_support_supported():
    """Test checking support for a v0.1 feature."""
    result = check_feature_support("Linear workflows (START -> nodes -> END)")

    assert result["supported"] is True
    assert result["version"] == "0.1.0-dev"
    assert "Available now" in result["timeline"]


def test_check_feature_support_v02():
    """Test checking support for a v0.2 feature."""
    result = check_feature_support("Conditional routing (if/else)")

    assert result["supported"] is False
    assert result["version"] == "v0.2"
    assert "8-12 weeks" in result["timeline"]


def test_check_feature_support_v03():
    """Test checking support for a v0.3 feature."""
    result = check_feature_support("DSPy prompt optimization")

    assert result["supported"] is False
    assert result["version"] == "v0.3"
    assert "12-16 weeks" in result["timeline"]


def test_check_feature_support_unknown():
    """Test checking support for unknown feature."""
    result = check_feature_support("Quantum computing integration")

    assert result["supported"] is False
    assert result["version"] == "unknown"
    assert "Not in current roadmap" in result["timeline"]


# ============================================
# Combined Feature Tests
# ============================================


def test_multiple_unsupported_features_hard_block_first():
    """Test that hard blocks (conditional routing) fail before soft blocks warn."""
    config = make_minimal_config(
        optimization=OptimizationConfig(enabled=True),  # Soft block (v0.3)
        edges=[
            EdgeConfig(
                from_="START",
                routes=[  # Hard block (v0.2)
                    Route(condition=RouteCondition(logic="true"), to="process"),
                ],
            ),
            EdgeConfig(from_="process", to="END"),
        ],
    )

    # Should raise error for hard block, not get to soft block
    with pytest.raises(UnsupportedFeatureError) as exc_info:
        validate_runtime_support(config)

    # Error should be about conditional routing, not optimization
    assert "Conditional routing" in str(exc_info.value)


def test_multiple_soft_blocks_all_warn():
    """Test that multiple soft blocks all trigger warnings."""
    config = make_minimal_config(
        optimization=OptimizationConfig(enabled=True),  # Soft block 1
        config=GlobalConfig(
            observability=ObservabilityConfig(
                mlflow=ObservabilityMLFlowConfig(enabled=True)  # Soft block 2
            )
        ),
    )

    with pytest.warns(UserWarning) as record:
        validate_runtime_support(config)

    # Should have two warnings
    assert len(record) == 2

    messages = [str(w.message) for w in record]
    assert any("optimization" in msg.lower() for msg in messages)
    assert any("mlflow" in msg.lower() for msg in messages)


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
