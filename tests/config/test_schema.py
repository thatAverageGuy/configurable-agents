"""Tests for config schema Pydantic models."""

import pytest
from pydantic import ValidationError

from configurable_agents.config.schema import (
    EdgeConfig,
    ExecutionConfig,
    FlowMetadata,
    GlobalConfig,
    LLMConfig,
    LoopConfig,
    NodeConfig,
    ObservabilityConfig,
    ObservabilityLoggingConfig,
    ObservabilityMLFlowConfig,
    OptimizationConfig,
    OptimizeConfig,
    OutputSchema,
    OutputSchemaField,
    ParallelConfig,
    Route,
    RouteCondition,
    StateFieldConfig,
    StateSchema,
    WorkflowConfig,
)


class TestFlowMetadata:
    """Test FlowMetadata model."""

    def test_valid_minimal(self):
        flow = FlowMetadata(name="test_flow")
        assert flow.name == "test_flow"
        assert flow.description is None
        assert flow.version is None

    def test_valid_complete(self):
        flow = FlowMetadata(
            name="test_flow", description="Test workflow", version="1.0.0"
        )
        assert flow.name == "test_flow"
        assert flow.description == "Test workflow"
        assert flow.version == "1.0.0"

    def test_name_required(self):
        with pytest.raises(ValidationError):
            FlowMetadata()

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            FlowMetadata(name="")

    def test_whitespace_name(self):
        with pytest.raises(ValidationError):
            FlowMetadata(name="   ")

    def test_name_stripped(self):
        flow = FlowMetadata(name="  test_flow  ")
        assert flow.name == "test_flow"


class TestStateFieldConfig:
    """Test StateFieldConfig model."""

    def test_valid_minimal(self):
        field = StateFieldConfig(type="str")
        assert field.type == "str"
        assert field.required is False
        assert field.default is None
        assert field.description is None

    def test_valid_with_default(self):
        field = StateFieldConfig(type="str", default="hello")
        assert field.type == "str"
        assert field.default == "hello"
        assert field.required is False

    def test_valid_required(self):
        field = StateFieldConfig(type="str", required=True)
        assert field.required is True
        assert field.default is None

    def test_required_with_default_fails(self):
        with pytest.raises(ValidationError):
            StateFieldConfig(type="str", required=True, default="hello")

    def test_with_description(self):
        field = StateFieldConfig(type="str", description="A string field")
        assert field.description == "A string field"

    def test_object_type_with_schema(self):
        field = StateFieldConfig(
            type="object",
            schema={"name": "str", "age": "int"},
        )
        assert field.type == "object"
        assert field.schema_ == {"name": "str", "age": "int"}

    def test_schema_alias(self):
        """Test that 'schema' alias works."""
        field = StateFieldConfig(type="object", **{"schema": {"name": "str"}})
        assert field.schema_ == {"name": "str"}


class TestStateSchema:
    """Test StateSchema model."""

    def test_valid_single_field(self):
        state = StateSchema(fields={"topic": StateFieldConfig(type="str")})
        assert len(state.fields) == 1
        assert "topic" in state.fields

    def test_valid_multiple_fields(self):
        state = StateSchema(
            fields={
                "topic": StateFieldConfig(type="str", required=True),
                "result": StateFieldConfig(type="str", default=""),
            }
        )
        assert len(state.fields) == 2

    def test_empty_fields_fails(self):
        with pytest.raises(ValidationError):
            StateSchema(fields={})


class TestOutputSchemaField:
    """Test OutputSchemaField model."""

    def test_valid_minimal(self):
        field = OutputSchemaField(name="result", type="str")
        assert field.name == "result"
        assert field.type == "str"
        assert field.description is None

    def test_valid_with_description(self):
        field = OutputSchemaField(
            name="result", type="str", description="The result"
        )
        assert field.description == "The result"


class TestOutputSchema:
    """Test OutputSchema model."""

    def test_valid_simple_type(self):
        schema = OutputSchema(type="str")
        assert schema.type == "str"
        assert schema.fields is None

    def test_valid_object_type(self):
        schema = OutputSchema(
            type="object",
            fields=[
                OutputSchemaField(name="summary", type="str"),
                OutputSchemaField(name="count", type="int"),
            ],
        )
        assert schema.type == "object"
        assert len(schema.fields) == 2

    def test_object_without_fields_fails(self):
        with pytest.raises(ValidationError):
            OutputSchema(type="object")

    def test_object_with_empty_fields_fails(self):
        with pytest.raises(ValidationError):
            OutputSchema(type="object", fields=[])


class TestOptimizeConfig:
    """Test OptimizeConfig model."""

    def test_valid_minimal(self):
        config = OptimizeConfig()
        assert config.enabled is False

    def test_valid_enabled(self):
        config = OptimizeConfig(
            enabled=True, metric="accuracy", strategy="BootstrapFewShot", max_demos=5
        )
        assert config.enabled is True
        assert config.metric == "accuracy"


class TestLLMConfig:
    """Test LLMConfig model."""

    def test_valid_minimal(self):
        config = LLMConfig()
        assert config.provider is None

    def test_valid_complete(self):
        config = LLMConfig(
            provider="google",
            model="gemini-2.0-flash-exp",
            temperature=0.7,
            max_tokens=1024,
        )
        assert config.provider == "google"
        assert config.model == "gemini-2.0-flash-exp"
        assert config.temperature == 0.7
        assert config.max_tokens == 1024

    def test_temperature_range_valid(self):
        config = LLMConfig(temperature=0.0)
        assert config.temperature == 0.0
        config = LLMConfig(temperature=1.0)
        assert config.temperature == 1.0

    def test_temperature_below_zero_fails(self):
        with pytest.raises(ValidationError):
            LLMConfig(temperature=-0.1)

    def test_temperature_above_one_fails(self):
        with pytest.raises(ValidationError):
            LLMConfig(temperature=1.1)

    def test_max_tokens_positive(self):
        config = LLMConfig(max_tokens=100)
        assert config.max_tokens == 100

    def test_max_tokens_zero_fails(self):
        with pytest.raises(ValidationError):
            LLMConfig(max_tokens=0)

    def test_max_tokens_negative_fails(self):
        with pytest.raises(ValidationError):
            LLMConfig(max_tokens=-1)


class TestNodeConfig:
    """Test NodeConfig model."""

    def test_valid_minimal(self):
        node = NodeConfig(
            id="test_node",
            prompt="Test prompt",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
        )
        assert node.id == "test_node"
        assert node.prompt == "Test prompt"
        assert len(node.outputs) == 1

    def test_valid_complete(self):
        node = NodeConfig(
            id="research_node",
            description="Research node",
            inputs={"query": "{state.topic}"},
            prompt="Research {query}",
            output_schema=OutputSchema(
                type="object",
                fields=[OutputSchemaField(name="summary", type="str")],
            ),
            outputs=["summary"],
            tools=["serper_search"],
            optimize=OptimizeConfig(enabled=True),
            llm=LLMConfig(temperature=0.5),
        )
        assert node.id == "research_node"
        assert node.description == "Research node"
        assert node.tools == ["serper_search"]

    def test_invalid_id_fails(self):
        with pytest.raises(ValidationError):
            NodeConfig(
                id="invalid-node",  # Hyphens not allowed
                prompt="Test",
                output_schema=OutputSchema(type="str"),
                outputs=["result"],
            )

    def test_id_with_underscore_valid(self):
        node = NodeConfig(
            id="valid_node",
            prompt="Test",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
        )
        assert node.id == "valid_node"

    def test_empty_outputs_fails(self):
        with pytest.raises(ValidationError):
            NodeConfig(
                id="test_node",
                prompt="Test",
                output_schema=OutputSchema(type="str"),
                outputs=[],
            )

    def test_observability_overrides(self):
        """Test node-level observability overrides."""
        node = NodeConfig(
            id="test_node",
            prompt="Test prompt",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
            log_prompts=False,  # Override workflow default
            log_artifacts=True,  # Override workflow default
        )
        assert node.log_prompts is False
        assert node.log_artifacts is True

    def test_observability_overrides_optional(self):
        """Test that observability overrides are optional."""
        node = NodeConfig(
            id="test_node",
            prompt="Test prompt",
            output_schema=OutputSchema(type="str"),
            outputs=["result"],
        )
        assert node.log_prompts is None  # Not set, will use workflow default
        assert node.log_artifacts is None  # Not set, will use workflow default


class TestRouteCondition:
    """Test RouteCondition model."""

    def test_valid(self):
        condition = RouteCondition(logic="{state.score} >= 8")
        assert condition.logic == "{state.score} >= 8"


class TestRoute:
    """Test Route model."""

    def test_valid(self):
        route = Route(
            condition=RouteCondition(logic="{state.score} >= 8"), to="success_node"
        )
        assert route.condition.logic == "{state.score} >= 8"
        assert route.to == "success_node"


class TestEdgeConfig:
    """Test EdgeConfig model."""

    def test_valid_linear_edge(self):
        edge = EdgeConfig(**{"from": "node1", "to": "node2"})
        assert edge.from_ == "node1"
        assert edge.to == "node2"
        assert edge.routes is None

    def test_valid_conditional_edge(self):
        edge = EdgeConfig(
            **{
                "from": "node1",
                "routes": [
                    {
                        "condition": {"logic": "{state.score} >= 8"},
                        "to": "success_node",
                    }
                ],
            }
        )
        assert edge.from_ == "node1"
        assert edge.to is None
        assert len(edge.routes) == 1

    def test_no_to_or_routes_fails(self):
        with pytest.raises(ValidationError):
            EdgeConfig(**{"from": "node1"})

    def test_both_to_and_routes_fails(self):
        with pytest.raises(ValidationError):
            EdgeConfig(
                **{
                    "from": "node1",
                    "to": "node2",
                    "routes": [
                        {
                            "condition": {"logic": "default"},
                            "to": "node3",
                        }
                    ],
                }
            )

    def test_from_alias(self):
        """Test that 'from' alias works."""
        edge = EdgeConfig(from_="node1", to="node2")
        assert edge.from_ == "node1"


class TestLoopConfig:
    """Test LoopConfig model."""

    def test_valid_minimal(self):
        config = LoopConfig(condition_field="is_done", exit_to="END")
        assert config.max_iterations == 10
        assert config.condition_field == "is_done"
        assert config.exit_to == "END"

    def test_valid_custom(self):
        config = LoopConfig(max_iterations=5, condition_field="is_complete", exit_to="next_node")
        assert config.max_iterations == 5
        assert config.condition_field == "is_complete"
        assert config.exit_to == "next_node"

    def test_max_iterations_positive(self):
        with pytest.raises(ValidationError):
            LoopConfig(condition_field="is_done", max_iterations=0)

    def test_max_iterations_upper_bound(self):
        with pytest.raises(ValidationError):
            LoopConfig(condition_field="is_done", max_iterations=101)

    def test_max_iterations_boundary_valid(self):
        config = LoopConfig(condition_field="is_done", max_iterations=1)
        assert config.max_iterations == 1
        config = LoopConfig(condition_field="is_done", max_iterations=100)
        assert config.max_iterations == 100


class TestParallelConfig:
    """Test ParallelConfig model."""

    def test_valid_minimal(self):
        config = ParallelConfig(items_field="tasks", target_node="process_task", collect_field="results")
        assert config.items_field == "tasks"
        assert config.target_node == "process_task"
        assert config.collect_field == "results"


class TestEdgeConfigWithLoopAndParallel:
    """Test EdgeConfig with loop and parallel options."""

    def test_valid_loop_edge(self):
        edge = EdgeConfig(**{"from": "process", "loop": {"condition_field": "is_done", "exit_to": "END"}})
        assert edge.from_ == "process"
        assert edge.loop is not None
        assert edge.loop.condition_field == "is_done"
        assert edge.loop.exit_to == "END"
        assert edge.to is None
        assert edge.routes is None
        assert edge.parallel is None

    def test_valid_parallel_edge(self):
        edge = EdgeConfig(
            **{
                "from": "process",
                "parallel": {"items_field": "items", "target_node": "worker", "collect_field": "results"},
            }
        )
        assert edge.from_ == "process"
        assert edge.parallel is not None
        assert edge.parallel.items_field == "items"
        assert edge.parallel.target_node == "worker"
        assert edge.parallel.collect_field == "results"
        assert edge.to is None
        assert edge.routes is None
        assert edge.loop is None

    def test_multiple_edge_types_fails(self):
        """Edge cannot have both loop and parallel config."""
        with pytest.raises(ValidationError) as exc_info:
            EdgeConfig(
                **{
                    "from": "process",
                    "loop": {"condition_field": "is_done", "exit_to": "END"},
                    "parallel": {"items_field": "items", "target_node": "worker", "collect_field": "results"},
                }
            )
        assert "multiple edge types" in str(exc_info.value).lower()

    def test_loop_and_to_fails(self):
        """Edge cannot have both loop and to."""
        with pytest.raises(ValidationError) as exc_info:
            EdgeConfig(
                **{
                    "from": "process",
                    "to": "next",
                    "loop": {"condition_field": "is_done", "exit_to": "END"},
                }
            )
        assert "multiple edge types" in str(exc_info.value).lower()

    def test_routes_and_parallel_fails(self):
        """Edge cannot have both routes and parallel."""
        from configurable_agents.config.schema import Route, RouteCondition

        with pytest.raises(ValidationError) as exc_info:
            EdgeConfig(
                **{
                    "from": "process",
                    "routes": [{"condition": {"logic": "default"}, "to": "next"}],
                    "parallel": {"items_field": "items", "target_node": "worker", "collect_field": "results"},
                }
            )
        assert "multiple edge types" in str(exc_info.value).lower()


class TestOptimizationConfig:
    """Test OptimizationConfig model."""

    def test_valid_defaults(self):
        config = OptimizationConfig()
        assert config.enabled is False
        assert config.strategy == "BootstrapFewShot"
        assert config.metric == "semantic_match"
        assert config.max_demos == 4

    def test_valid_custom(self):
        config = OptimizationConfig(
            enabled=True, strategy="MIPRO", metric="accuracy", max_demos=8
        )
        assert config.enabled is True
        assert config.strategy == "MIPRO"
        assert config.metric == "accuracy"
        assert config.max_demos == 8

    def test_max_demos_positive(self):
        with pytest.raises(ValidationError):
            OptimizationConfig(max_demos=0)


class TestExecutionConfig:
    """Test ExecutionConfig model."""

    def test_valid_defaults(self):
        config = ExecutionConfig()
        assert config.timeout == 120
        assert config.max_retries == 3

    def test_valid_custom(self):
        config = ExecutionConfig(timeout=180, max_retries=5)
        assert config.timeout == 180
        assert config.max_retries == 5

    def test_timeout_positive(self):
        with pytest.raises(ValidationError):
            ExecutionConfig(timeout=0)

    def test_max_retries_non_negative(self):
        config = ExecutionConfig(max_retries=0)
        assert config.max_retries == 0

        with pytest.raises(ValidationError):
            ExecutionConfig(max_retries=-1)


class TestObservabilityConfig:
    """Test ObservabilityConfig models."""

    def test_mlflow_config_defaults(self):
        config = ObservabilityMLFlowConfig()
        assert config.enabled is False
        assert config.tracking_uri == "file://./mlruns"
        assert config.experiment_name == "configurable_agents"
        assert config.run_name is None
        assert config.log_prompts is True
        assert config.log_artifacts is True
        assert config.artifact_level == "standard"
        assert config.retention_days is None
        assert config.redact_pii is False

    def test_mlflow_config_valid_artifact_levels(self):
        """Test that valid artifact levels are accepted."""
        for level in ["minimal", "standard", "full"]:
            config = ObservabilityMLFlowConfig(artifact_level=level)
            assert config.artifact_level == level

    def test_mlflow_config_invalid_artifact_level(self):
        """Test that invalid artifact levels are rejected."""
        with pytest.raises(ValueError, match="artifact_level must be one of"):
            ObservabilityMLFlowConfig(artifact_level="invalid")

    def test_logging_config_defaults(self):
        config = ObservabilityLoggingConfig()
        assert config.level == "INFO"

    def test_logging_config_valid_levels(self):
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = ObservabilityLoggingConfig(level=level)
            assert config.level == level

    def test_logging_config_case_insensitive(self):
        config = ObservabilityLoggingConfig(level="debug")
        assert config.level == "DEBUG"

    def test_logging_config_invalid_level(self):
        with pytest.raises(ValidationError):
            ObservabilityLoggingConfig(level="INVALID")

    def test_observability_config(self):
        config = ObservabilityConfig(
            mlflow=ObservabilityMLFlowConfig(enabled=True, experiment="test"),
            logging=ObservabilityLoggingConfig(level="DEBUG"),
        )
        assert config.mlflow.enabled is True
        assert config.logging.level == "DEBUG"


class TestGlobalConfig:
    """Test GlobalConfig model."""

    def test_valid_minimal(self):
        config = GlobalConfig()
        assert config.llm is None
        assert config.execution is None

    def test_valid_complete(self):
        config = GlobalConfig(
            llm=LLMConfig(provider="google", temperature=0.7),
            execution=ExecutionConfig(timeout=180),
            observability=ObservabilityConfig(
                logging=ObservabilityLoggingConfig(level="DEBUG")
            ),
        )
        assert config.llm.provider == "google"
        assert config.execution.timeout == 180
        assert config.observability.logging.level == "DEBUG"


class TestWorkflowConfig:
    """Test WorkflowConfig (top-level) model."""

    def test_valid_minimal(self):
        config = WorkflowConfig(
            schema_version="1.0",
            flow=FlowMetadata(name="test_flow"),
            state=StateSchema(fields={"topic": StateFieldConfig(type="str")}),
            nodes=[
                NodeConfig(
                    id="node1",
                    prompt="Test",
                    output_schema=OutputSchema(type="str"),
                    outputs=["topic"],
                )
            ],
            edges=[EdgeConfig(**{"from": "START", "to": "node1"})],
        )
        assert config.schema_version == "1.0"
        assert config.flow.name == "test_flow"

    def test_valid_complete(self):
        config = WorkflowConfig(
            schema_version="1.0",
            flow=FlowMetadata(name="test_flow", version="1.0.0"),
            state=StateSchema(
                fields={
                    "topic": StateFieldConfig(type="str", required=True),
                    "result": StateFieldConfig(type="str", default=""),
                }
            ),
            nodes=[
                NodeConfig(
                    id="node1",
                    prompt="Test {state.topic}",
                    output_schema=OutputSchema(type="str"),
                    outputs=["result"],
                )
            ],
            edges=[
                EdgeConfig(**{"from": "START", "to": "node1"}),
                EdgeConfig(**{"from": "node1", "to": "END"}),
            ],
            optimization=OptimizationConfig(enabled=True),
            config=GlobalConfig(
                llm=LLMConfig(provider="google", temperature=0.7)
            ),
        )
        assert config.schema_version == "1.0"
        assert len(config.nodes) == 1
        assert len(config.edges) == 2

    def test_invalid_schema_version(self):
        with pytest.raises(ValidationError):
            WorkflowConfig(
                schema_version="2.0",
                flow=FlowMetadata(name="test"),
                state=StateSchema(fields={"topic": StateFieldConfig(type="str")}),
                nodes=[
                    NodeConfig(
                        id="node1",
                        prompt="Test",
                        output_schema=OutputSchema(type="str"),
                        outputs=["topic"],
                    )
                ],
                edges=[EdgeConfig(**{"from": "START", "to": "node1"})],
            )

    def test_empty_nodes_fails(self):
        with pytest.raises(ValidationError):
            WorkflowConfig(
                schema_version="1.0",
                flow=FlowMetadata(name="test"),
                state=StateSchema(fields={"topic": StateFieldConfig(type="str")}),
                nodes=[],
                edges=[],
            )

    def test_empty_edges_fails(self):
        with pytest.raises(ValidationError):
            WorkflowConfig(
                schema_version="1.0",
                flow=FlowMetadata(name="test"),
                state=StateSchema(fields={"topic": StateFieldConfig(type="str")}),
                nodes=[
                    NodeConfig(
                        id="node1",
                        prompt="Test",
                        output_schema=OutputSchema(type="str"),
                        outputs=["topic"],
                    )
                ],
                edges=[],
            )

    def test_duplicate_node_ids_fails(self):
        with pytest.raises(ValidationError) as exc_info:
            WorkflowConfig(
                schema_version="1.0",
                flow=FlowMetadata(name="test"),
                state=StateSchema(fields={"topic": StateFieldConfig(type="str")}),
                nodes=[
                    NodeConfig(
                        id="node1",
                        prompt="Test",
                        output_schema=OutputSchema(type="str"),
                        outputs=["topic"],
                    ),
                    NodeConfig(
                        id="node1",  # Duplicate
                        prompt="Test",
                        output_schema=OutputSchema(type="str"),
                        outputs=["topic"],
                    ),
                ],
                edges=[EdgeConfig(**{"from": "START", "to": "node1"})],
            )
        assert "Duplicate node IDs" in str(exc_info.value)


class TestYAMLJSONEquivalence:
    """Test that configs work with both YAML and JSON."""

    def test_from_dict(self):
        """Test creating config from dict (as would come from YAML/JSON)."""
        config_dict = {
            "schema_version": "1.0",
            "flow": {"name": "test_flow"},
            "state": {"fields": {"topic": {"type": "str"}}},
            "nodes": [
                {
                    "id": "node1",
                    "prompt": "Test",
                    "output_schema": {"type": "str"},
                    "outputs": ["topic"],
                }
            ],
            "edges": [{"from": "START", "to": "node1"}],
        }
        config = WorkflowConfig(**config_dict)
        assert config.schema_version == "1.0"

    def test_to_dict(self):
        """Test converting config to dict (for YAML/JSON export)."""
        config = WorkflowConfig(
            schema_version="1.0",
            flow=FlowMetadata(name="test_flow"),
            state=StateSchema(fields={"topic": StateFieldConfig(type="str")}),
            nodes=[
                NodeConfig(
                    id="node1",
                    prompt="Test",
                    output_schema=OutputSchema(type="str"),
                    outputs=["topic"],
                )
            ],
            edges=[EdgeConfig(**{"from": "START", "to": "node1"})],
        )
        config_dict = config.model_dump(by_alias=True, exclude_none=True)
        assert config_dict["schema_version"] == "1.0"
        assert config_dict["flow"]["name"] == "test_flow"
        assert "from" in config_dict["edges"][0]  # Uses alias
