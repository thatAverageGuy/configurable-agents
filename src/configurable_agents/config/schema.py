"""
Pydantic models for config schema v1.0.

Full Schema Day One (ADR-009): Complete schema supporting all features through v0.3.
Runtime implements features incrementally across versions.
"""

from typing import Any, Dict, List, Optional, Union

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

    provider: Optional[str] = Field(None, description="LLM provider (v0.1: only 'google')")
    model: Optional[str] = Field(None, description="Model name")
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0, description="Temperature (0.0-1.0)")
    max_tokens: Optional[int] = Field(None, gt=0, description="Max tokens")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: Optional[float]) -> Optional[float]:
        """Validate temperature is in range."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Temperature must be between 0.0 and 1.0")
        return v


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
    tools: Optional[List[str]] = Field(None, description="Tool names from registry")
    optimize: Optional[OptimizeConfig] = Field(
        None, description="Node-level optimization (v0.3+)"
    )
    llm: Optional[LLMConfig] = Field(None, description="Node-level LLM override")

    # Observability overrides (optional, overrides workflow-level defaults)
    log_prompts: Optional[bool] = Field(
        None, description="Override workflow-level log_prompts for this node"
    )
    log_artifacts: Optional[bool] = Field(
        None, description="Override workflow-level log_artifacts for this node"
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

    logic: str = Field(..., description="Condition logic or 'default'")


class Route(BaseModel):
    """Conditional route (v0.2+)."""

    condition: RouteCondition = Field(..., description="Route condition")
    to: str = Field(..., description="Target node")


class EdgeConfig(BaseModel):
    """Edge configuration."""

    from_: str = Field(..., alias="from", description="Source node (or START)")
    to: Optional[str] = Field(None, description="Target node (or END) - for linear edges")
    routes: Optional[List[Route]] = Field(
        None, description="Conditional routes (v0.2+)"
    )

    class Config:
        populate_by_name = True  # Allow both 'from' and 'from_'

    @model_validator(mode="after")
    def validate_to_or_routes(self) -> "EdgeConfig":
        """Validate that either 'to' or 'routes' is specified, but not both."""
        has_to = self.to is not None
        has_routes = self.routes is not None and len(self.routes) > 0

        if not has_to and not has_routes:
            raise ValueError("Edge must have either 'to' or 'routes'")

        if has_to and has_routes:
            raise ValueError("Edge cannot have both 'to' and 'routes'")

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
    """MLFlow observability config (v0.1+)."""

    enabled: bool = Field(False, description="Enable MLFlow tracking")
    tracking_uri: str = Field(
        "file://./mlruns",
        description="MLFlow backend URI (file://, postgresql://, s3://, etc.)"
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
        description="Show prompts/responses in MLFlow UI (not as files, default for all nodes)"
    )
    log_artifacts: bool = Field(
        True,
        description="Save artifacts as downloadable files (default for all nodes)"
    )
    artifact_level: str = Field(
        "standard",
        description="Artifact detail level: 'minimal', 'standard', or 'full'"
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


class GlobalConfig(BaseModel):
    """Global infrastructure configuration."""

    llm: Optional[LLMConfig] = Field(None, description="Global LLM config")
    execution: Optional[ExecutionConfig] = Field(None, description="Execution config")
    observability: Optional[ObservabilityConfig] = Field(
        None, description="Observability config (v0.2+)"
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
