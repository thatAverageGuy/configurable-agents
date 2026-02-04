# Architecture Overview

**Purpose**: High-level system design, patterns, and architecture
**Audience**: Developers wanting to understand how the system works
**Last Updated**: 2026-02-02

**For detailed decisions**: See [Architecture Decision Records](adr/)
**For implementation tasks**: See [TASKS.md](TASKS.md)
**For version features**: See [README.md](../README.md#roadmap--status)

---

## System Overview

The system transforms YAML configuration into executable agent workflows through a config-driven pipeline.

```
┌──────────────┐
│ YAML Config  │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Config Parser    │ ← Parse YAML/JSON
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Config Validator │ ← Validate dependencies, types
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Graph Builder    │ ← Construct LangGraph
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Runtime Executor │ ← Execute workflow
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Outputs (dict)   │
└──────────────────┘
```

---

## Core Architecture Patterns

### 1. Config-Driven Pipeline Pattern

**Pattern**: Config → Validate → Build → Execute

**Why**: Fail-fast validation prevents wasted LLM costs. Catch 95% of errors before execution.

**Implementation**: See [ADR-003](adr/ADR-003-config-driven-architecture.md), [ADR-004](adr/ADR-004-parse-time-validation.md)

**Flow**:
```python
# Config → Pydantic model → Validate → Build → Execute
config_dict = load_config("workflow.yaml")       # Parse YAML
config = WorkflowConfig(**config_dict)           # Pydantic validation
validate_config(config)                          # Business logic validation
graph = build_graph(config, ...)                 # Construct execution graph
result = graph.invoke(initial_state)             # Execute
```

**Code**: [`runtime/executor.py:25-45`](../src/configurable_agents/runtime/executor.py)

---

### 2. Dynamic Schema Generation Pattern

**Pattern**: YAML type strings → Runtime Pydantic models

**Why**: Type safety without code generation. Users define types in config, system generates validation models dynamically.

**Implementation**: See [ADR-002](adr/ADR-002-strict-typing-pydantic-schemas.md)

**Example**:
```yaml
# User writes this in config
state:
  fields:
    - name: topic
      type: str
      required: true
    - name: article
      type: str
      default: ""
```

```python
# System generates this at runtime (equivalent to):
class WorkflowState(BaseModel):
    topic: str  # Required
    article: str = ""  # Optional with default

# Created dynamically:
StateModel = build_state_model(config.state)
state = StateModel(topic="AI Safety")  # Validated!
```

**Code**: [`core/state_builder.py:15-60`](../src/configurable_agents/core/state_builder.py)

---

### 3. Closure-Based Node Pattern

**Pattern**: Config → Closure function → LangGraph node

**Why**: Clean separation of graph structure (edges, flow) from node logic (LLM calls, tools). Each node is a self-contained closure capturing its configuration.

**Implementation**: See [ADR-001](adr/ADR-001-langgraph-execution-engine.md)

**Code**:
```python
def make_node_function(node_config: NodeConfig, global_config: GlobalConfig):
    """Create a closure that executes a node"""
    def node_function(state: BaseModel) -> dict:
        # Closure captures node_config
        return execute_node(state, node_config, global_config)
    return node_function

# Add to graph
graph.add_node(node_id, make_node_function(node_cfg, global_cfg))
```

**Why closures**: No global state, no class instances, just pure functions. LangGraph sees simple `state -> dict` functions.

**Code**: [`core/graph_builder.py:80-95`](../src/configurable_agents/core/graph_builder.py)

---

### 4. Two-Phase Validation Pattern

**Pattern**: Pydantic (structure) → Custom validator (business logic)

**Why**: Pydantic catches ~70% of errors (types, required fields). Custom validator catches ~25% (cross-references, graph structure). Total: ~95% of errors before execution.

**Implementation**: See [ADR-004](adr/ADR-004-parse-time-validation.md)

**Phase 1 - Pydantic**:
```python
config = WorkflowConfig(**config_dict)
# Validates: structure, types, required fields
# Example error: "field 'state' required"
```

**Phase 2 - Custom**:
```python
validate_config(config)
# Validates: node refs, state fields, output types, graph structure
# Example error: "Node 'write' references unknown state field 'artcile'. Did you mean 'article'?"
```

**Code**: [`config/validator.py:20-250`](../src/configurable_agents/config/validator.py)

---

### 5. Structured Output Enforcement Pattern

**Pattern**: Schema → JSON mode LLM → Pydantic validation → State update

**Why**: No unstructured LLM outputs in production. Every response is type-validated before updating state.

**Implementation**: See [ADR-002](adr/ADR-002-strict-typing-pydantic-schemas.md)

**Flow**:
```python
# 1. Build output model from config
OutputModel = build_output_model(node.output_schema, node.id)

# 2. Force LLM to return JSON matching schema
llm_with_schema = llm.with_structured_output(
    OutputModel.model_json_schema()
)

# 3. Call LLM (guaranteed JSON response)
response = llm_with_schema.invoke(prompt)

# 4. Validate with Pydantic
validated = OutputModel(**response)  # Raises error if invalid

# 5. Update state (type-safe)
state_dict[field] = validated.field_value
```

**Code**: [`core/node_executor.py:120-180`](../src/configurable_agents/core/node_executor.py)

---

### 6. Factory Pattern (Tool Registry)

**Pattern**: Lazy factory-based tool instantiation

**Why**: Tools only created when needed. Supports custom tool registration. Fail-fast if tool not found.

**Implementation**: See [ADR-007](adr/ADR-007-tools-as-named-registry.md)

**Code**:
```python
class ToolRegistry:
    def __init__(self):
        self._factories = {
            "serper_search": self._create_serper_tool,
            # Add more tools here
        }
        self._instances = {}  # Cache

    def get_tool(self, name: str) -> BaseTool:
        if name not in self._factories:
            raise ToolNotFoundError(f"Tool '{name}' not found")

        if name not in self._instances:
            self._instances[name] = self._factories[name]()

        return self._instances[name]
```

**Code**: [`tools/registry.py:15-80`](../src/configurable_agents/tools/registry.py)

---

### 7. Builder Pattern (State & Output Builders)

**Pattern**: Config → Builder → Pydantic model

**Why**: Centralize complex model creation logic. Reusable for state and output schemas.

**Implementation**: See [ADR-002](adr/ADR-002-strict-typing-pydantic-schemas.md)

**State Builder**:
```python
def build_state_model(state_schema: StateSchema) -> Type[BaseModel]:
    """Build Pydantic model from state config"""
    field_defs = {}
    for field in state_schema.fields:
        python_type = get_python_type(field.type)
        default = ... if field.required else field.default
        field_defs[field.name] = (python_type, default)

    return create_model("WorkflowState", **field_defs)
```

**Output Builder**:
```python
def build_output_model(output_schema: OutputSchema, node_id: str):
    """Build Pydantic model for node output"""
    # Similar logic, different source
    return create_model(f"Output_{node_id}", **field_defs)
```

**Code**: [`core/state_builder.py`](../src/configurable_agents/core/state_builder.py), [`core/output_builder.py`](../src/configurable_agents/core/output_builder.py)

---

### 8. Strategy Pattern (LLM Providers)

**Pattern**: Provider interface with multiple implementations

**Why**: Support multiple LLM providers (future) without changing core logic.

**Implementation**: See [ADR-005](adr/ADR-005-single-llm-provider-v01.md)

**Interface** (v0.1 - Google Gemini only):
```python
def create_llm(config: LLMConfig) -> BaseChatModel:
    """Create LLM instance based on provider"""
    if config.provider == "google":  # v0.1
        return create_google_llm(config)
    # v0.2+: elif config.provider == "openai": ...
    # v0.2+: elif config.provider == "anthropic": ...
```

**Future expansion**: Add provider in `llm/openai.py`, register in `create_llm()`.

**Code**: [`llm/provider.py:20-50`](../src/configurable_agents/llm/provider.py)

---

### 9. Decorator Pattern (Feature Gating)

**Pattern**: Wrap validation logic with version checks

**Why**: Allow future features in config schema (v0.2, v0.3) while blocking execution in v0.1. Progressive disclosure of features.

**Implementation**: See [ADR-009](adr/ADR-009-full-schema-day-one.md)

**Code**:
```python
def gate_features(config: WorkflowConfig) -> None:
    """Block unsupported features, warn on future features"""

    # Hard block (v0.2+ not implemented)
    if _has_conditional_routing(config):
        raise FeatureNotAvailableError(
            "Conditional routing requires v0.2+. "
            "Use simple edges in v0.1."
        )

    # Soft warning (v0.3+ planned)
    if config.optimization and config.optimization.enabled:
        warnings.warn(
            "DSPy optimization planned for v0.3. "
            "Config accepted but optimization ignored.",
            FutureWarning
        )
```

**Code**: [`runtime/feature_gate.py:15-120`](../src/configurable_agents/runtime/feature_gate.py)

---

## Component Architecture

### Config Layer

**Components**: Parser, Validator, Schema Models, Feature Gate

**Responsibility**: Load, validate, and gate workflow configs

**Key Pattern**: Two-phase validation (Pydantic + Custom)

**Files**:
- `config/parser.py` - YAML/JSON parsing
- `config/schema.py` - 13 Pydantic models (complete schema v1.0)
- `config/validator.py` - 8-stage validation pipeline
- `runtime/feature_gate.py` - Version-based feature gating

**Related ADRs**: [ADR-003](adr/ADR-003-config-driven-architecture.md), [ADR-004](adr/ADR-004-parse-time-validation.md), [ADR-009](adr/ADR-009-full-schema-day-one.md)

---

### Execution Layer

**Components**: State Builder, Output Builder, Template Resolver, Node Executor

**Responsibility**: Execute nodes with type safety and prompt resolution

**Key Pattern**: Dynamic schema generation + Structured output enforcement

**Files**:
- `core/state_builder.py` - Generate state models from config
- `core/output_builder.py` - Generate output models from config
- `core/template.py` - Resolve {variable} placeholders in prompts
- `core/node_executor.py` - Execute single node (LLM + tools + validation)

**Related ADRs**: [ADR-002](adr/ADR-002-strict-typing-pydantic-schemas.md), [ADR-003](adr/ADR-003-config-driven-architecture.md)

---

### Orchestration Layer

**Components**: Graph Builder, Runtime Executor

**Responsibility**: Construct and execute LangGraph workflows

**Key Pattern**: Closure-based nodes + Config-driven pipeline

**Files**:
- `core/graph_builder.py` - Construct LangGraph from config
- `runtime/executor.py` - End-to-end workflow execution

**Related ADRs**: [ADR-001](adr/ADR-001-langgraph-execution-engine.md)

---

### Integration Layer

**Components**: LLM Provider, Tool Registry

**Responsibility**: External API integration (LLMs, tools)

**Key Pattern**: Factory (tools) + Strategy (LLM providers)

**Files**:
- `llm/provider.py` - LLM provider interface
- `llm/google.py` - Google Gemini implementation
- `tools/registry.py` - Tool registry with lazy loading
- `tools/serper.py` - Serper web search tool

**Related ADRs**: [ADR-005](adr/ADR-005-single-llm-provider-v01.md), [ADR-007](adr/ADR-007-tools-as-named-registry.md)

---

## Technology Stack

| Layer | Technology | Why | ADR |
|-------|-----------|-----|-----|
| **Execution** | LangGraph | No prompt wrapping, DSPy compatible | [ADR-001](adr/ADR-001-langgraph-execution-engine.md) |
| **Validation** | Pydantic | Industry standard, excellent errors | [ADR-002](adr/ADR-002-strict-typing-pydantic-schemas.md) |
| **Config** | YAML + Pydantic | Human-readable + type-safe | [ADR-003](adr/ADR-003-config-driven-architecture.md) |
| **LLM (v0.1)** | Google Gemini | Simple integration, good free tier | [ADR-005](adr/ADR-005-single-llm-provider-v01.md) |
| **Tools** | LangChain Tools | Standard interface, large ecosystem | [ADR-007](adr/ADR-007-tools-as-named-registry.md) |
| **Testing** | pytest | Standard Python testing | [ADR-017](adr/ADR-017-testing-strategy-cost-management.md) |
| **CLI** | Click | Industry standard | [ADR-015](adr/ADR-015-cli-interface-design.md) |
| **Observability** | MLFlow (v0.1) | LLM-specific tracking | [ADR-011](adr/ADR-011-mlflow-observability.md) |
| **Deployment** | Docker + FastAPI | Containerized microservices | [ADR-012](adr/ADR-012-docker-deployment-architecture.md) |

---

## Design Principles in Practice

### Principle: Explicit Over Implicit

**Philosophy**: No hidden behavior. Everything visible in config.

**Implementation**:
- Explicit state fields (ADR-002) - No auto-generated fields
- Explicit edges (ADR-006) - No automatic routing
- Explicit output schemas (ADR-002) - No unstructured outputs
- Explicit tool references (ADR-007) - No auto-discovery

**Example**: Node must declare outputs
```yaml
nodes:
  - id: research
    outputs: [summary, sources]  # Explicit
    output_schema:  # Explicit types
      type: object
      fields:
        - {name: summary, type: str}
        - {name: sources, type: list[str]}
```

---

### Principle: Fail Fast, Save Money

**Philosophy**: Catch errors before expensive LLM calls.

**Implementation**: Parse-time validation (ADR-004)

**Cost Comparison**:
```
❌ Without validation:
Step 1 (research): ✓ $0.01
Step 2 (outline): ✓ $0.02
Step 3 (write): ✓ $0.10
Step 4 (review): ✗ TypeError: expected dict, got str
Total: $0.13 (wasted)

✅ With validation:
Config validation: ✗ Error: node 'review' expects dict but 'write' outputs str
Total: $0.00 (caught at parse time)
```

**Code**: [`config/validator.py`](../src/configurable_agents/config/validator.py)

---

### Principle: Local-First, Enterprise-Ready

**Philosophy**: Works out-of-the-box locally. Optional enterprise features.

**Implementation**:
- **MLFlow** (ADR-011): File-based backend (v0.1) → PostgreSQL/S3 (v0.2+)
- **State**: In-memory (v0.1) → Redis/PostgreSQL (v0.2+)
- **Deployment**: Local Docker (v0.1) → Cloud (v0.2+)

**Design Strategy**: Implement simple version first, leave hooks for enterprise upgrades.

---

### Principle: Testability

**Philosophy**: Pure functions, no global state, easy mocking.

**Implementation** (ADR-017):
- **Unit tests** (449): Mock LLM/API calls, fast, free
- **Integration tests** (19): Real APIs, cost-tracked (<$0.50 per PR)
- **CI strategy**: Unit tests always, integration tests on PR

**Code**: [`tests/`](../tests/)

---

## Observability Architecture (v0.1)

**Status**: In progress (T-018 to T-021)

**Pattern**: MLFlow for LLM-specific tracking

**Architecture**:
```
Runtime Executor
      ↓
Workflow Run (MLFlow)
  - Params: workflow name, model, temp
  - Metrics: duration, total_tokens, total_cost
  - Artifacts: inputs.json, outputs.json
      ↓
Node Runs (nested)
  - Params: node_id, tools
  - Metrics: duration, input_tokens, output_tokens, cost
  - Artifacts: prompt.txt, response.txt
```

**Implementation**: See [ADR-011](adr/ADR-011-mlflow-observability.md), [ADR-014](adr/ADR-014-three-tier-observability-strategy.md)

**Detailed Guide**: See [OBSERVABILITY.md](OBSERVABILITY.md)

---

## Deployment Architecture (v0.1)

**Status**: Planned (T-022 to T-024)

**Pattern**: FastAPI + MLFlow UI in Docker container

**Architecture**:
```
configurable-agents deploy workflow.yaml
      ↓
Generate artifacts (Dockerfile, server.py, docker-compose.yml)
      ↓
Build multi-stage Docker image
      ↓
Run container (detached)
  - Port 8000: FastAPI server (POST /run, GET /status, GET /health)
  - Port 5000: MLFlow UI
```

**Sync/Async Hybrid**:
- Fast workflows (<30s): Return result immediately
- Slow workflows (>30s): Background job, return job_id

**Implementation**: See [ADR-012](adr/ADR-012-docker-deployment-architecture.md), [ADR-013](adr/ADR-013-environment-variable-handling.md)

**Detailed Guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)

---

## Extension Points

> **Note**: Detailed extension guides will be moved to [CONTRIBUTING.md](CONTRIBUTING.md) in a future update. Current step-by-step instructions below are temporary.

### Adding a New Tool

1. **Create tool file**: `src/configurable_agents/tools/my_tool.py`
   ```python
   from langchain.tools import BaseTool

   class MyCustomTool(BaseTool):
       name = "my_custom_tool"
       description = "What this tool does"

       def _run(self, query: str) -> str:
           # Your tool logic
           return result
   ```

2. **Register in registry**: `src/configurable_agents/tools/registry.py`
   ```python
   class ToolRegistry:
       def __init__(self):
           self._factories = {
               "serper_search": self._create_serper_tool,
               "my_custom_tool": self._create_my_tool,  # Add here
           }

       def _create_my_tool(self) -> BaseTool:
           return MyCustomTool()
   ```

3. **Add tests**: `tests/tools/test_my_tool.py`

4. **Use in config**:
   ```yaml
   nodes:
     - id: process
       tools: [my_custom_tool]
   ```

**Reference**: See [`tools/serper.py`](../src/configurable_agents/tools/serper.py) for example.

---

### Adding a New LLM Provider (v0.2+)

1. **Create provider file**: `src/configurable_agents/llm/openai.py`
   ```python
   from langchain_openai import ChatOpenAI

   def create_openai_llm(config: LLMConfig) -> BaseChatModel:
       return ChatOpenAI(
           model=config.model,
           temperature=config.temperature,
           # ...
       )
   ```

2. **Register in provider**: `src/configurable_agents/llm/provider.py`
   ```python
   def create_llm(config: LLMConfig) -> BaseChatModel:
       if config.provider == "google":
           return create_google_llm(config)
       elif config.provider == "openai":  # Add here
           return create_openai_llm(config)
   ```

3. **Update schema**: `src/configurable_agents/config/schema.py`
   ```python
   class LLMConfig(BaseModel):
       provider: Literal["google", "openai", "anthropic"] = "google"
   ```

4. **Add tests**: `tests/llm/test_openai.py`

**Reference**: See [`llm/google.py`](../src/configurable_agents/llm/google.py) for example.

---

### Adding a New Validation Rule

1. **Add validation function**: `src/configurable_agents/config/validator.py`
   ```python
   def _validate_my_rule(config: WorkflowConfig) -> None:
       """Validate my custom rule"""
       # Your validation logic
       if some_condition:
           raise ValidationError("Error message", suggestion="...")
   ```

2. **Call in pipeline**: `src/configurable_agents/config/validator.py`
   ```python
   def validate_config(config: WorkflowConfig) -> None:
       _validate_edge_references(config)
       _validate_node_outputs(config)
       _validate_my_rule(config)  # Add here
       # ...
   ```

3. **Add tests**: `tests/config/test_validator.py`

**Reference**: See [`config/validator.py:20-250`](../src/configurable_agents/config/validator.py) for examples.

---

## Security Considerations

### v0.1 Scope

- ✅ No arbitrary code execution (custom code nodes deferred to v0.2+)
- ✅ Environment variable isolation (API keys from .env only)
- ✅ Input validation (Pydantic prevents injection)
- ✅ Tool sandboxing (LangChain BaseTool constraints)

### Future (v0.2+)

- Secrets management (vault integration)
- Resource limits (token budgets, timeouts)
- Network sandboxing (for container mode)
- Audit logging (who ran what, when)

---

## Deep Dive References

**Detailed Decisions**: [Architecture Decision Records](adr/) (16 ADRs)

**Implementation Tasks**: [TASKS.md](TASKS.md) (27 tasks, 18 complete)

**Version Features**: [README.md](../README.md#roadmap--status) (v0.1-v0.4 overview)

**Technical Specs**: [SPEC.md](SPEC.md) (Complete config schema reference)

**User Guides**:
- [QUICKSTART.md](QUICKSTART.md) - Get started in 5 minutes
- [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) - Config schema guide
- [OBSERVABILITY.md](OBSERVABILITY.md) - MLFlow tracking guide
- [DEPLOYMENT.md](DEPLOYMENT.md) - Docker deployment guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
