"""
Pydantic models for config schema v1.0.

Full Schema Day One (ADR-009): Complete schema supporting all features through v0.3.
Runtime implements features incrementally across versions.
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================
# 2. Flow Metadata
# ============================================


class FlowMetadata(BaseModel):
    """Workflow metadata."""

    name: str = Field(..., description="Unique workflow identifier")
    description: Optional[str] = Field(None, description="Human-readable description")
    version: Optional[str] = Field(
        None, description="Workflow version (semantic versioning recommended)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is non-empty."""
        if not v or not v.strip():
            raise ValueError("Flow name cannot be empty")
        return v.strip()


# ============================================
# 3. State Schema
# ============================================


class StateFieldConfig(BaseModel):
    """Configuration for a single state field."""

    type: str = Field(..., description="Type string (e.g., 'str', 'list[int]', 'object')")
    required: bool = Field(False, description="If true, field must be provided in inputs")
    default: Optional[Any] = Field(None, description="Default value if not provided")
    description: Optional[str] = Field(None, description="Field description")
    schema_: Optional[Dict[str, Any]] = Field(
        None, alias="schema", description="Nested object schema (for type='object')"
    )

    class Config:
        populate_by_name = True  # Allow both 'schema' and 'schema_'

    @model_validator(mode="after")
    def validate_required_and_default(self) -> "StateFieldConfig":
        """Validate that required fields don't have defaults."""
        if self.required and self.default is not None:
            raise ValueError("Cannot have both required=true and a default value")
        return self


class StateSchema(BaseModel):
    """State schema definition."""

    fields: Dict[str, StateFieldConfig] = Field(
        ..., description="State field definitions"
    )

    @field_validator("fields")
    @classmethod
    def validate_fields_not_empty(cls, v: Dict[str, StateFieldConfig]) -> Dict[str, StateFieldConfig]:
        """Validate that at least one field is defined."""
        if not v:
            raise ValueError("State must have at least one field")
        return v


# ============================================
# 4. Nodes
# ============================================


class OutputSchemaField(BaseModel):
    """Field definition in output schema."""

    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Type string")
    description: Optional[str] = Field(
        None, description="Field description (helps LLM understand what to return)"
    )


class OutputSchema(BaseModel):
    """
    Output schema definition for node outputs.

    Can be either:
    - Object type with multiple fields
    - Simple type (str, int, etc.)
    """

    type: str = Field(..., description="Output type ('object' or basic type)")
    fields: Optional[List[OutputSchemaField]] = Field(
        None, description="Fields for object type"
    )
    description: Optional[str] = Field(None, description="Output description")

    @model_validator(mode="after")
    def validate_object_has_fields(self) -> "OutputSchema":
        """Validate that object type has fields."""
        if self.type == "object" and not self.fields:
            raise ValueError("Output schema with type='object' must have fields")
        return self


class OptimizeConfig(BaseModel):
    """Node-level DSPy optimization config (v0.3+)."""

    enabled: bool = Field(False, description="Enable optimization for this node")
    metric: Optional[str] = Field(None, description="Metric name (must be in registry)")
    strategy: Optional[str] = Field(None, description="DSPy strategy")
    max_demos: Optional[int] = Field(None, description="Max few-shot examples")


class LLMConfig(BaseModel):
    """LLM configuration (global or node-level)."""

    provider: Optional[str] = Field(
        None, description="LLM provider: 'openai', 'anthropic', 'google', 'ollama'"
    )
    model: Optional[str] = Field(None, description="Model name")
    temperature: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Temperature (0.0-1.0)"
    )
    max_tokens: Optional[int] = Field(None, gt=0, description="Max tokens")
    api_base: Optional[str] = Field(
        None,
        description="Custom API base URL (e.g., for Ollama: http://localhost:11434)",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: Optional[str]) -> Optional[str]:
        """Validate provider is supported."""
        if v is not None:
            supported = ["openai", "anthropic", "google", "ollama"]
            if v not in supported:
                raise ValueError(
                    f"Provider '{v}' not supported. Supported providers: {supported}"
                )
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: Optional[float]) -> Optional[float]:
        """Validate temperature is in range."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Temperature must be between 0.0 and 1.0")
        return v


# ============================================
# 4.4. Sandbox Configuration (v0.4+)
# ============================================


class SandboxConfig(BaseModel):
    """
    Sandbox configuration for safe code execution (v0.4+).

    Controls how code execution nodes are isolated and limited.
    """

    mode: Literal["python", "docker"] = Field(
        "python",
        description="Execution mode: 'python' (RestrictedPython) or 'docker' (container isolation)"
    )
    enabled: bool = Field(
        True,
        description="Enable sandbox for code execution nodes"
    )
    network: Union[bool, Dict[str, Any]] = Field(
        True,
        description="Network access: True (enabled), False (disabled), or detailed config"
    )
    preset: Literal["low", "medium", "high", "max"] = Field(
        "medium",
        description="Resource preset for execution limits"
    )
    resources: Optional[Dict[str, Any]] = Field(
        None,
        description="Custom resource overrides (cpu, memory, timeout)"
    )
    timeout: Optional[int] = Field(
        None,
        ge=1,
        le=3600,
        description="Execution timeout in seconds (overrides preset)"
    )

    @field_validator("preset")
    @classmethod
    def validate_preset(cls, v: str) -> str:
        """Validate preset is one of the supported values."""
        valid_presets = {"low", "medium", "high", "max"}
        if v not in valid_presets:
            raise ValueError(
                f"preset must be one of {valid_presets}, got '{v}'"
            )
        return v


# ============================================
# 4.5. Optimization (v0.4+)
# ============================================


class MLFlowConfig(BaseModel):
    """MLFlow experiment configuration for optimization (v0.4+)."""

    experiment: Optional[str] = Field(
        None, description="MLFlow experiment name for grouping runs"
    )
    run_name: Optional[str] = Field(
        None, description="Optional run identifier template"
    )


class VariantConfig(BaseModel):
    """Prompt variant configuration for A/B testing (v0.4+)."""

    name: str = Field(..., description="Variant name for identification")
    prompt: str = Field(..., description="Prompt template to test")
    config_overrides: Optional[Dict[str, Any]] = Field(
        None, description="Optional config overrides for this variant"
    )
    node_id: Optional[str] = Field(
        None, description="Specific node ID to apply prompt (default: first node)"
    )


class ABTestConfig(BaseModel):
    """A/B testing configuration (v0.4+)."""

    enabled: bool = Field(False, description="Enable A/B testing for this workflow")
    experiment: str = Field(..., description="MLFlow experiment name for results")
    variants: List[VariantConfig] = Field(
        ..., description="List of prompt variants to test"
    )
    run_count: int = Field(3, ge=1, le=10, description="Runs per variant (default: 3)")
    parallel: bool = Field(True, description="Run variants concurrently")


class QualityGateModel(BaseModel):
    """Quality gate threshold definition (v0.4+)."""

    metric: str = Field(..., description="Metric name to check (e.g., 'cost_usd', 'duration_ms')")
    max: Optional[float] = Field(None, description="Maximum allowed value (exclusive)")
    min: Optional[float] = Field(None, description="Minimum allowed value (exclusive)")


class GatesModel(BaseModel):
    """Quality gates configuration (v0.4+)."""

    gates: List[QualityGateModel] = Field(
        default_factory=list, description="List of quality gate thresholds"
    )
    on_fail: str = Field(
        "warn",
        description="Action when gates fail: 'warn', 'fail', or 'block_deploy'"
    )

    @field_validator("on_fail")
    @classmethod
    def validate_on_fail(cls, v: str) -> str:
        """Validate on_fail value."""
        valid_actions = {"warn", "fail", "block_deploy"}
        if v not in valid_actions:
            raise ValueError(
                f"on_fail must be one of {valid_actions}, got '{v}'"
            )
        return v


class MemoryConfig(BaseModel):
    """Memory configuration for agent persistent storage (v0.4+)."""

    enabled: bool = Field(False, description="Enable persistent memory for this scope")
    default_scope: Literal["agent", "workflow", "node"] = Field(
        "agent",
        description="Default memory scope: 'agent', 'workflow', or 'node'",
    )


class ToolConfig(BaseModel):
    """Tool configuration for binding tools to LLMs (v0.4+)."""

    name: str = Field(..., description="Tool name from registry")
    on_error: Literal["fail", "continue"] = Field(
        "fail",
        description="Error handling: 'fail' raises error, 'continue' returns error result",
    )
    config: Optional[Dict[str, Any]] = Field(
        None,
        description="Tool-specific configuration",
    )


class NodeConfig(BaseModel):
    """Node configuration."""

    id: str = Field(..., description="Unique node identifier")
    description: Optional[str] = Field(None, description="Human description")
    inputs: Optional[Dict[str, str]] = Field(
        None, description="Input mapping: {local_var: state_reference}"
    )
    prompt: str = Field(..., description="Prompt template with {placeholders}")
    output_schema: OutputSchema = Field(..., description="Output type enforcement")
    outputs: List[str] = Field(..., description="State fields to update")
    tools: Optional[List[Union[str, ToolConfig]]] = Field(
        None, description="Tool names from registry or tool configs"
    )
    memory: Optional[MemoryConfig] = Field(
        None, description="Memory configuration for this node (v0.4+)"
    )
    optimize: Optional[OptimizeConfig] = Field(
        None, description="Node-level optimization (v0.3+)"
    )
    llm: Optional[LLMConfig] = Field(None, description="Node-level LLM override")
    sandbox: Optional[SandboxConfig] = Field(
        None, description="Sandbox configuration for code execution (v0.4+)"
    )
    code: Optional[str] = Field(
        None,
        description="Python code to execute (for code_execution node type, v0.4+)"
    )

    # Observability overrides (optional, overrides workflow-level defaults)
    log_prompts: Optional[bool] = Field(
        None, description="Override workflow-level log_prompts for this node"
    )
    log_artifacts: Optional[bool] = Field(
        None, description="Override workflow-level log_artifacts for this node"
    )

    # MLFlow override (v0.4+)
    mlflow: Optional[MLFlowConfig] = Field(
        None, description="MLFlow experiment configuration (overrides workflow-level)"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate that ID is a valid Python identifier."""
        if not v.isidentifier():
            raise ValueError(f"Node ID '{v}' must be a valid Python identifier")
        return v

    @field_validator("outputs")
    @classmethod
    def validate_outputs_not_empty(cls, v: List[str]) -> List[str]:
        """Validate that outputs list is not empty."""
        if not v:
            raise ValueError("Node must have at least one output")
        return v


# ============================================
# 5. Edges
# ============================================


class RouteCondition(BaseModel):
    """Condition for conditional routing (v0.2+)."""

    logic: str = Field(
        ...,
        description="Condition logic or 'default'. Use 'state.field' references with operators (>, <, ==, !=, >=, <=, and, or, not). Example: 'state.score > 0.8' or 'state.approved and state.amount < 1000'",
    )


class Route(BaseModel):
    """Conditional route (v0.2+)."""

    condition: RouteCondition = Field(..., description="Route condition")
    to: str = Field(..., description="Target node")


class LoopConfig(BaseModel):
    """Loop configuration for retry/iteration edges."""

    max_iterations: int = Field(
        10,
        gt=0,
        le=100,
        description="Maximum loop iterations before forced exit",
    )
    condition_field: str = Field(
        ...,
        description="State field to evaluate for loop termination (must be bool type)",
    )
    exit_to: str = Field(
        "END", description="Node to route to when loop condition is met or max iterations reached"
    )


class ParallelConfig(BaseModel):
    """Parallel execution configuration for fan-out edges."""

    items_field: str = Field(
        ..., description="State field containing list of items to fan out over"
    )
    target_node: str = Field(..., description="Node to execute for each item")
    collect_field: str = Field(
        ..., description="State field to collect results into (must be list type)"
    )


class EdgeConfig(BaseModel):
    """Edge configuration."""

    from_: str = Field(..., alias="from", description="Source node (or START)")
    to: Optional[str] = Field(None, description="Target node (or END) - for linear edges")
    routes: Optional[List[Route]] = Field(
        None, description="Conditional routes (v0.2+)"
    )
    loop: Optional[LoopConfig] = Field(
        None, description="Loop configuration (retry/iteration)"
    )
    parallel: Optional[ParallelConfig] = Field(
        None, description="Parallel fan-out configuration"
    )

    class Config:
        populate_by_name = True  # Allow both 'from' and 'from_'

    @model_validator(mode="after")
    def validate_to_or_routes(self) -> "EdgeConfig":
        """Validate that exactly one of 'to', 'routes', 'loop', or 'parallel' is specified."""
        has_to = self.to is not None
        has_routes = self.routes is not None and len(self.routes) > 0
        has_loop = self.loop is not None
        has_parallel = self.parallel is not None

        edge_types = sum([has_to, has_routes, has_loop, has_parallel])

        if edge_types == 0:
            raise ValueError(
                "Edge must have exactly one of: 'to' (linear), 'routes' (conditional), 'loop' (iteration), or 'parallel' (fan-out)"
            )

        if edge_types > 1:
            raise ValueError(
                "Edge cannot have multiple edge types. Choose exactly one of: 'to', 'routes', 'loop', or 'parallel'"
            )

        return self


# ============================================
# 6. Optimization (v0.3+)
# ============================================


class OptimizationConfig(BaseModel):
    """Global DSPy optimization config (v0.3+)."""

    enabled: bool = Field(False, description="Enable DSPy optimization")
    strategy: str = Field("BootstrapFewShot", description="DSPy optimizer strategy")
    metric: str = Field("semantic_match", description="Metric name (must be in registry)")
    max_demos: int = Field(4, gt=0, description="Max few-shot examples")


# ============================================
# 7. Global Config
# ============================================


class ExecutionConfig(BaseModel):
    """Execution configuration."""

    timeout: int = Field(120, gt=0, description="Timeout in seconds")
    max_retries: int = Field(3, ge=0, description="Max retries")


class ObservabilityMLFlowConfig(BaseModel):
    """MLFlow observability config (v0.1+, updated for MLflow 3.9)."""

    enabled: bool = Field(False, description="Enable MLFlow tracking")
    tracking_uri: str = Field(
        "file://./mlruns",
        description="MLFlow backend URI (file://, sqlite://, postgresql://, s3://, etc.). "
        "Note: file:// is deprecated in MLflow 3.9, consider sqlite:///mlflow.db"
    )
    experiment_name: str = Field(
        "configurable_agents",
        description="Experiment name for grouping runs"
    )
    run_name: Optional[str] = Field(
        None,
        description="Template for run names (default: timestamp-based)"
    )

    # Observability controls (workflow-level defaults, can be overridden per-node)
    log_prompts: bool = Field(
        True,
        description="Show prompts/responses in MLFlow UI (auto-captured by autolog in 3.9)"
    )
    log_artifacts: bool = Field(
        True,
        description="Save artifacts as downloadable files (default for all nodes)"
    )
    artifact_level: str = Field(
        "standard",
        description="Artifact detail level: 'minimal', 'standard', or 'full'"
    )

    # MLflow 3.9 features
    async_logging: bool = Field(
        True,
        description="Enable async trace logging for zero-latency production (MLflow 3.5+)"
    )

    # Enterprise hooks (reserved for v0.2+, not enforced)
    retention_days: Optional[int] = Field(
        None,
        description="Auto-cleanup old runs after N days (v0.2+)"
    )
    redact_pii: bool = Field(
        False,
        description="Sanitize PII before logging (v0.2+)"
    )

    @field_validator("artifact_level")
    @classmethod
    def validate_artifact_level(cls, v: str) -> str:
        """Validate artifact level is one of the supported values."""
        valid_levels = {"minimal", "standard", "full"}
        if v not in valid_levels:
            raise ValueError(
                f"artifact_level must be one of {valid_levels}, got '{v}'"
            )
        return v


class ObservabilityLoggingConfig(BaseModel):
    """Logging config."""

    level: str = Field("INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper


class ObservabilityConfig(BaseModel):
    """Observability configuration (v0.2+)."""

    mlflow: Optional[ObservabilityMLFlowConfig] = Field(None, description="MLFlow config")
    logging: Optional[ObservabilityLoggingConfig] = Field(
        None, description="Logging config"
    )


class StorageConfig(BaseModel):
    """Storage backend configuration."""

    backend: str = Field("sqlite", description="Storage backend type: 'sqlite' or connection URI")
    path: str = Field("./workflows.db", description="SQLite database path (only for sqlite backend)")


class GlobalConfig(BaseModel):
    """Global infrastructure configuration."""

    llm: Optional[LLMConfig] = Field(None, description="Global LLM config")
    execution: Optional[ExecutionConfig] = Field(None, description="Execution config")
    observability: Optional[ObservabilityConfig] = Field(
        None, description="Observability config (v0.2+)"
    )
    storage: Optional[StorageConfig] = Field(None, description="Storage backend config")

    # Optimization configuration (v0.4+)
    mlflow: Optional[MLFlowConfig] = Field(
        None, description="MLFlow experiment configuration"
    )
    ab_test: Optional[ABTestConfig] = Field(
        None, description="A/B testing configuration"
    )
    gates: Optional[GatesModel] = Field(
        None, description="Quality gates configuration"
    )

    # Optimization configuration (v0.4+)
    mlflow: Optional[MLFlowConfig] = Field(
        None, description="MLFlow experiment configuration"
    )
    ab_test: Optional[ABTestConfig] = Field(
        None, description="A/B testing configuration"
    )
    gates: Optional[GatesModel] = Field(
        None, description="Quality gates configuration"
    )


# ============================================
# 1. Top-Level Config
# ============================================


class WorkflowConfig(BaseModel):
    """
    Top-level workflow configuration.

    Schema v1.0 - supports all features through v0.3.
    Runtime implements features incrementally.
    """

    schema_version: str = Field(
        ..., description="Config schema version (currently '1.0')"
    )
    flow: FlowMetadata = Field(..., description="Workflow metadata")
    state: StateSchema = Field(..., description="State definition")
    nodes: List[NodeConfig] = Field(..., description="Execution nodes")
    edges: List[EdgeConfig] = Field(..., description="Control flow edges")
    optimization: Optional[OptimizationConfig] = Field(
        None, description="DSPy optimization settings (v0.3+)"
    )
    memory: Optional[MemoryConfig] = Field(
        None, description="Workflow-level memory configuration (v0.4+)"
    )
    config: Optional[GlobalConfig] = Field(None, description="Infrastructure settings")

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        """Validate schema version."""
        if v != "1.0":
            raise ValueError(f"Unsupported schema version '{v}'. Expected '1.0'")
        return v

    @field_validator("nodes")
    @classmethod
    def validate_nodes_not_empty(cls, v: List[NodeConfig]) -> List[NodeConfig]:
        """Validate that at least one node is defined."""
        if not v:
            raise ValueError("Workflow must have at least one node")
        return v

    @field_validator("edges")
    @classmethod
    def validate_edges_not_empty(cls, v: List[EdgeConfig]) -> List[EdgeConfig]:
        """Validate that at least one edge is defined."""
        if not v:
            raise ValueError("Workflow must have at least one edge")
        return v

    @model_validator(mode="after")
    def validate_node_ids_unique(self) -> "WorkflowConfig":
        """Validate that node IDs are unique."""
        node_ids = [node.id for node in self.nodes]
        duplicates = [id for id in node_ids if node_ids.count(id) > 1]
        if duplicates:
            raise ValueError(f"Duplicate node IDs: {set(duplicates)}")
        return self
