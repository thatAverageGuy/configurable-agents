# Architecture Overview

**Purpose**: High-level system design, patterns, and architecture
**Audience**: Developers wanting to understand how the system works
**Last Updated**: 2026-02-13 (UI Redesign)

> **Note**: This document reflects the UI Redesign terminology changes (2026-02-13).
> Models renamed: `WorkflowRunRecord` → `Execution`, `AgentRecord` → `Deployment`.
> Routes changed: `/workflows/*` → `/executions/*`, `/agents/*` → `/deployments/*`.

**For detailed decisions**: See [Architecture Decision Records](adr/)
**For implementation tasks**: See [TASKS.md](TASKS.md)
**For version features**: See [README.md](../README.md#roadmap--status)

---

## System Overview

The system transforms YAML configuration into executable agent workflows through a config-driven pipeline with advanced control flow, multi-LLM support, and comprehensive observability.

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
│ Config Validator │ ← Validate dependencies, types, features
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Storage Backend  │ ← Abstract storage (SQLite/PostgreSQL)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Graph Builder    │ ← Construct LangGraph with control flow
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Runtime Executor │ ← Execute workflow with tracking
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Outputs + Trace  │ ← Return results + MLFlow tracking
└──────────────────┘
```

---

## v1.0 Subsystems

### 1. LiteLLM Integration Layer

**Location**: `src/configurable_agents/llm/`

**Purpose**: Unified multi-provider LLM support with transparent cost tracking

**Components**:
- `provider.py` - LLM factory and provider interface
- `google.py` - Direct Google Gemini implementation (optimal LangChain compatibility)
- `litellm.py` - LiteLLM wrapper for OpenAI, Anthropic, Ollama
- `cost_estimator.py` - Multi-provider cost calculation

**Key Features**:
- **Google Provider**: Direct LangChain implementation (not LiteLLM) for best compatibility
- **OpenAI/Anthropic**: LiteLLM abstraction with unified API
- **Ollama**: Local model support with `ollama_chat/` prefix, zero-cost tracking
- **Structured Output**: Pydantic schema binding for all providers
- **Automatic Retries**: Validation error recovery with clarified prompts
- **Tool Binding**: Tool integration before structured output (correct order)

**Providers Supported**:
- Google: gemini-2.5-flash-lite, gemini-2.5-pro, gemini-2.5-flash, gemini-1.5-pro, gemini-1.5-flash
- OpenAI: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- Anthropic: claude-3-opus, claude-3-sonnet, claude-3-haiku
- Ollama: llama2, mistral, codellama (local models, zero cost)

**Related ADRs**: [ADR-005](adr/ADR-005-multi-llm-provider-v10.md), [ADR-019](adr/ADR-019-litellm-integration.md)

---

### 2. Deployment Registry Architecture

**Location**: `src/configurable_agents/registry/`

**Purpose**: Dynamic deployment discovery, registration, and health monitoring

**Components**:
- `models.py` - Deployment ORM model (SQLAlchemy 2.0), DeploymentRegistrationRequest
- `repository.py` - DeploymentRepository for storage operations
- `server.py` - DeploymentRegistryServer (FastAPI, heartbeat endpoint)
- `client.py` - DeploymentClient (auto-registration, heartbeat loop)

**Key Features**:
- **Deployment-Initiated Registration**: Deployments self-register on startup
- **Heartbeat/TTL Pattern**: 60s TTL, 20s heartbeat interval (~1/3 for reliability)
- **Graceful Expiration**: Background cleanup removes stale deployments
- **Idempotent Registration**: Re-registering updates existing records
- **FastAPI Integration**: Session management, async endpoints
- **Docker Integration**: Auto-detect host/port from env vars
- **Workflow Tracking**: Each deployment tracks which workflow it runs via `workflow_name`

**Storage Backend**:
- Pluggable via Repository Pattern
- SQLite default (development), PostgreSQL (production)
- Context manager pattern prevents transaction leaks

**Related ADRs**: [ADR-020](adr/ADR-020-agent-registry.md) (historical)

---

### 3. Dashboard (FastAPI + HTMX + SSE)

**Location**: `src/configurable_agents/ui/dashboard/`

**Purpose**: Orchestration dashboard for execution management, deployment discovery, and real-time monitoring

**Components**:
- `app.py` - FastAPI application with HTMX endpoints
- `templates/` - Jinja2 templates with HTMX attributes
- `routes/` - Dashboard routes (executions, deployments, metrics, status)

**Key Features**:
- **HTMX for Dynamic Updates**: No JavaScript framework needed
- **Server-Sent Events (SSE)**: Real-time streaming to clients
- **Deployment Discovery UI**: View registered deployments, capabilities, health status
- **Execution Management**: Start, stop, restart executions with progress tracking
- **MLFlow Integration**: iframe embed for observability UI
- **Repository Injection**: Dependency injection via app.state

**Technology Stack**:
- FastAPI: Async web framework
- HTMX: Dynamic HTML without JS
- SSE: One-way real-time data pushing
- Jinja2: Server-side templating

**Routes**:
- `/executions/*` - Execution management (formerly `/workflows/*`)
- `/deployments/*` - Deployment management (formerly `/agents/*`)
- `/metrics/*` - Real-time metrics via SSE

**Related ADRs**: [ADR-021](adr/ADR-021-htmx-dashboard.md)

---

### 4. Sandbox Execution (RestrictedPython + Docker)

**Location**: `src/configurable_agents/sandbox/`

**Purpose**: Safe execution of agent-generated code with resource limits

**Components**:
- `restricted_python.py` - RestrictedPython executor with safe globals
- `docker_executor.py` - Docker sandbox with network isolation (optional)
- `presets.py` - Resource limit presets (low/medium/high/max)

**Key Features**:
- **RestrictedPython Default**: Fast, works everywhere, no Docker required
- **Docker Opt-In**: Network isolation, strict resource limits
- **Safe Globals**: Custom `_print_`, `_getattr_`, `_import_` guards
- **Resource Presets**: Configurable CPU, memory, timeout limits
- **Security Whitelisting**: ALLOWED_PATHS, ALLOWED_COMMANDS for file/shell ops
- **Error Handling Continuation**: `on_error: continue` catches errors and returns dict

**Security Measures**:
- AST-like parsing instead of eval() for condition evaluation
- No access to private attributes (underscore-prefixed names blocked)
- File operations restricted to whitelisted paths
- Shell commands restricted to whitelist
- SQL queries limited to SELECT only

**Related ADRs**: [ADR-022](adr/ADR-022-restrictedpython-sandbox.md)

---

### 5. Memory Backend

**Location**: `src/configurable_agents/memory/`

**Purpose**: Persistent, namespaced key-value storage for agent context

**Components**:
- `memory.py` - AgentMemory with dict-like read and explicit write API
- `models.py` - MemoryEntry ORM model
- `repository.py` - MemoryRepository for storage operations

**Key Features**:
- **Namespace Pattern**: `{agent_id}:{workflow_id or "*"}:{node_id or "*"}:{key}`
- **Dict-Like Read**: `memory['key']` for convenient access
- **Explicit Write**: `memory.write('key', value)` for clarity
- **Wildcard Support**: `*` for workflow/node in namespace for broader scope
- **Storage Abstraction**: SQLite default, PostgreSQL swappable

**Use Cases**:
- Cross-execution context retention
- Agent learning and state persistence
- Workflow resume capabilities
- Long-term memory for agents

**Related ADRs**: [ADR-023](adr/ADR-023-memory-backend.md)

---

### 6. Webhook Router

**Location**: `src/configurable_agents/webhooks/`

**Purpose**: Generic webhook infrastructure with platform-specific integrations

**Components**:
- `server.py` - Generic webhook endpoints (FastAPI)
- `platforms/whatsapp.py` - WhatsApp Business API handler
- `platforms/telegram.py` - Telegram Bot API handler (aiogram 3.x)
- `models.py` - WebhookExecution ORM model

**Key Features**:
- **Generic Webhook**: Universal `/webhooks/generic` endpoint
- **HMAC Verification**: Optional signature validation for security
- **Idempotency Tracking**: `INSERT OR IGNORE` for webhook_id deduplication
- **Async Execution**: Background workflow execution via run_workflow_async
- **Platform Handlers**: Lazy initialization only when env vars configured
- **Message Chunking**: Automatic splitting for 4096 char limits (WhatsApp/Telegram)

**Integrations**:
- WhatsApp Business API (Meta webhook verification, HMAC signing)
- Telegram Bot API (aiogram 3.x async patterns)
- Generic webhook (workflow_name + inputs for universal triggering)

**Related ADRs**: [ADR-024](adr/ADR-024-webhook-integration.md)

---

### 7. Optimization System

**Location**: `src/configurable_agents/optimization/`

**Purpose**: MLFlow-based prompt optimization and A/B testing

**Components**:
- `evaluator.py` - ExperimentEvaluator for MLFlow metric aggregation
- `ab_testing.py` - ABTestRunner for variant comparison
- `quality_gates.py` - QualityGateChecker for automated validation
- `optimizer.py` - PromptOptimizer for applying optimized prompts

**Key Features**:
- **Percentile Calculation**: p50, p95, p99 using nearest-rank method
- **Quality Gates**: WARN (logs), FAIL (raises), BLOCK_DEPLOY (sets flag)
- **A/B Testing**: Config override workflow for variant comparison
- **Automatic Backup**: YAML backup created before applying optimizations
- **CLI Integration**: `optimization` command group (evaluate, apply-optimized, ab-test)

**Quality Metrics**:
- Cost per run
- Duration
- Token usage
- Custom metrics

**Related ADRs**: [ADR-025](adr/ADR-025-optimization-architecture.md)

---

## Core Architecture Patterns

### 1. Config-Driven Pipeline Pattern

**Pattern**: Config → Validate → Build → Execute → Track

**Why**: Fail-fast validation prevents wasted LLM costs. Catch 95% of errors before execution.

**Implementation**: See [ADR-003](adr/ADR-003-config-driven-architecture.md), [ADR-004](adr/ADR-004-parse-time-validation.md)

**Flow**:
```python
# Config → Pydantic model → Validate → Build → Execute → Track
config_dict = load_config("workflow.yaml")       # Parse YAML
config = WorkflowConfig(**config_dict)           # Pydantic validation
validate_config(config)                          # Business logic validation
graph = build_graph(config, ...)                 # Construct execution graph
result = run_workflow(graph, initial_state)      # Execute with tracking
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

### 8. Strategy Pattern (Multi-LLM Providers)

**Pattern**: Provider interface with multiple implementations

**Why**: Support multiple LLM providers without changing core logic.

**Implementation**: See [ADR-005](adr/ADR-005-multi-llm-provider-v10.md), [ADR-019](adr/ADR-019-litellm-integration.md)

**Interface** (v1.0 - Multi-provider):
```python
def create_llm(config: LLMConfig) -> BaseChatModel:
    """Create LLM instance based on provider"""
    if config.provider == "google":
        return create_google_llm(config)  # Direct implementation
    elif config.provider in ["openai", "anthropic"]:
        return create_litellm_llm(config)  # LiteLLM wrapper
    elif config.provider == "ollama":
        return create_ollama_llm(config)   # LiteLLM with local models
    else:
        raise LLMProviderError(f"Unsupported provider: {config.provider}")
```

**Future expansion**: Add provider in `llm/` directory, register in `create_llm()`.

**Code**: [`llm/provider.py:20-50`](../src/configurable_agents/llm/provider.py)

---

### 9. Repository Pattern (Storage Abstraction)

**Pattern**: Abstract repository with concrete implementations

**Why**: Pluggable storage backends (SQLite default, PostgreSQL swappable)

**Implementation**: Phase 1 (01-01-PLAN.md)

**Code**:
```python
class AbstractExecutionRepository(ABC):
    @abstractmethod
    def add(self, execution: Execution) -> None: ...

    @abstractmethod
    def get(self, execution_id: str) -> Optional[Execution]: ...

    @abstractmethod
    def list_by_workflow(self, workflow_name: str, limit: int = 100) -> List[Execution]: ...

class SQLiteExecutionRepository(AbstractExecutionRepository):
    def __init__(self, engine):
        self.engine = engine

    def add(self, execution: Execution) -> None:
        with Session(self.engine) as session:
            session.add(execution)
            session.commit()
```

**Repositories**:
- `AbstractExecutionRepository` → `SQLiteExecutionRepository` (table: `executions`)
- `DeploymentRepository` → `SqliteDeploymentRepository` (table: `deployments`)
- `ExecutionStateRepository` → `SQLiteExecutionStateRepository` (table: `execution_states`)

**Code**: [`storage/base.py`](../src/configurable_agents/storage/base.py), [`storage/sqlite.py`](../src/configurable_agents/storage/sqlite.py)

---

## Component Architecture

### Config Layer

**Components**: Parser, Validator, Schema Models, Feature Gate

**Responsibility**: Load, validate, and gate workflow configs

**Key Pattern**: Two-phase validation (Pydantic + Custom)

**Files**:
- `config/parser.py` - YAML/JSON parsing
- `config/schema.py` - 13+ Pydantic models (complete schema v1.0 + v1.0 extensions)
- `config/validator.py` - 8-stage validation pipeline
- `runtime/feature_gate.py` - Version-based feature gating (v0.2.0-dev for control flow)

**Related ADRs**: [ADR-003](adr/ADR-003-config-driven-architecture.md), [ADR-004](adr/ADR-004-parse-time-validation.md), [ADR-009](adr/ADR-009-full-schema-day-one.md)

---

### Execution Layer

**Components**: State Builder, Output Builder, Template Resolver, Node Executor, Graph Builder

**Responsibility**: Execute nodes with type safety and prompt resolution

**Key Pattern**: Dynamic schema generation + Structured output enforcement

**Files**:
- `core/state_builder.py` - Generate state models from config
- `core/output_builder.py` - Generate output models from config
- `core/template.py` - Resolve {variable} placeholders in prompts
- `core/node_executor.py` - Execute single node (LLM + tools + validation)
- `core/graph_builder.py` - Build compiled LangGraph from config and state model

**Related ADRs**: [ADR-002](adr/ADR-002-strict-typing-pydantic-schemas.md), [ADR-003](adr/ADR-003-config-driven-architecture.md), [ADR-001](adr/ADR-001-langgraph-execution-engine.md)

---

### Runtime Layer

**Components**: Runtime Executor, Feature Gate

**Responsibility**: Orchestrate the full workflow lifecycle: load → validate → build → execute → track

**Key Pattern**: Config-driven pipeline with comprehensive error handling

**Files**:
- `runtime/executor.py` - Main entry point (run_workflow, validate_workflow)
- `runtime/feature_gate.py` - Runtime feature support validation

**Related ADRs**: [ADR-001](adr/ADR-001-langgraph-execution-engine.md)

---

### Integration Layer

**Components**: LLM Provider, Tool Registry, Storage Backend

**Responsibility**: External API integration (LLMs, tools, databases)

**Key Pattern**: Factory (tools, storage) + Strategy (LLM providers) + Repository (storage)

**Files**:
- `llm/provider.py` - LLM factory interface
- `llm/google.py` - Google Gemini direct implementation
- `llm/litellm.py` - LiteLLM wrapper for OpenAI/Anthropic/Ollama
- `tools/registry.py` - Tool registry with lazy loading
- `storage/sqlite.py` - Storage repositories (executions, deployments, memory, webhooks)

**Related ADRs**: [ADR-005](adr/ADR-005-multi-llm-provider-v10.md), [ADR-007](adr/ADR-007-tools-as-named-registry.md), [ADR-019](adr/ADR-019-litellm-integration.md)

---

### Observability Layer

**Components**: MLFlow Tracker, Cost Reporter, Performance Profiler, Multi-Provider Cost Tracker

**Responsibility**: Cost tracking, metrics, workflow profiling, optimization

**Key Pattern**: MLFlow automatic tracing + manual metrics + cost aggregation

**Files**:
- `observability/mlflow_tracker.py` - MLFlow integration (workflow/node tracking)
- `observability/cost_reporter.py` - Cost query and export (CSV/JSON)
- `observability/performance_profiler.py` - Bottleneck detection and timing
- `observability/multi_provider_cost_tracker.py` - Per-provider cost aggregation

**Related ADRs**: [ADR-011](adr/ADR-011-mlflow-observability.md), [ADR-014](adr/ADR-014-three-tier-observability-strategy.md)

---

### Deployment Layer

**Components**: Dashboard Server, Webhook Server, Deployment Generator

**Responsibility**: Generate production deployments, serve dashboard, handle webhooks

**Key Pattern**: FastAPI + HTMX + SSE for dashboard, async webhook handling

**Files**:
- `ui/dashboard/app.py` - Orchestration dashboard (FastAPI + HTMX)
- `webhooks/server.py` - Generic webhook infrastructure
- `deploy/generator.py` - Artifact generation (Dockerfile, docker-compose, server.py)

**Related ADRs**: [ADR-012](adr/ADR-012-docker-deployment-architecture.md), [ADR-021](adr/ADR-021-htmx-dashboard.md), [ADR-024](adr/ADR-024-webhook-integration.md)

---

## Technology Stack

| Layer | Technology | Why | ADR |
|-------|-----------|-----|-----|
| **Execution** | LangGraph | No prompt wrapping, DSPy compatible, control flow | [ADR-001](adr/ADR-001-langgraph-execution-engine.md) |
| **Validation** | Pydantic | Industry standard, excellent errors, dynamic models | [ADR-002](adr/ADR-002-strict-typing-pydantic-schemas.md) |
| **Config** | YAML + Pydantic | Human-readable + type-safe | [ADR-003](adr/ADR-003-config-driven-architecture.md) |
| **LLM (v1.0)** | Multi-Provider | Google (direct) + LiteLLM (OpenAI/Anthropic/Ollama) | [ADR-005](adr/ADR-005-multi-llm-provider-v10.md), [ADR-019](adr/ADR-019-litellm-integration.md) |
| **Tools** | LangChain Tools | Standard interface, 15+ pre-built tools, extensible | [ADR-007](adr/ADR-007-tools-as-named-registry.md) |
| **Storage** | SQLAlchemy 2.0 | Type-safe ORM, Repository Pattern, pluggable backends | Phase 1 (01-01-PLAN.md) |
| **Dashboard** | FastAPI + HTMX | Async, lightweight, no JS frameworks needed | [ADR-021](adr/ADR-021-htmx-dashboard.md) |
| **Observability** | MLFlow 3.9+ | Automatic tracing, GenAI features, cost tracking | [ADR-011](adr/ADR-011-mlflow-observability.md) |
| **Testing** | pytest | Standard Python testing | [ADR-017](adr/ADR-017-testing-strategy-cost-management.md) |
| **CLI** | Click + Rich | Industry standard, formatted tables | [ADR-015](adr/ADR-015-cli-interface-design.md) |
| **Deployment** | Docker + FastAPI | Containerized microservices, one-command deploy | [ADR-012](adr/ADR-012-docker-deployment-architecture.md) |

---

## Design Principles in Practice

### Principle: Explicit Over Implicit

**Philosophy**: No hidden behavior. Everything visible in config.

**Implementation**:
- Explicit state fields (ADR-002) - No auto-generated fields
- Explicit edges (ADR-006) - Linear flows in v0.1, conditional in v1.0
- Explicit output schemas (ADR-002) - No unstructured outputs
- Explicit tool references (ADR-007) - No auto-discovery
- Explicit routing (v1.0) - Conditional logic visible in config

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
- **Storage** (v1.0): SQLite (default) → PostgreSQL/Redis (swappable)
- **Deployment** (v1.0): Local Docker → Cloud (manual export)
- **Observability** (v1.0): File-based MLFlow → PostgreSQL/S3 (configurable)
- **Multi-LLM** (v1.0): Local Ollama (zero cost) → Cloud providers (optional)

**Design Strategy**: Implement simple version first, leave hooks for enterprise upgrades.

---

### Principle: Testability

**Philosophy**: Pure functions, no global state, easy mocking.

**Implementation** (ADR-017):
- **Unit tests** (645+): Mock LLM/API calls, fast, free
- **Integration tests** (19+): Real APIs, cost-tracked (<$0.50 per PR)
- **CI strategy**: Unit tests always, integration tests on PR

**Code**: [`tests/`](../tests/)

---

## Advanced v1.0 Features

### Conditional Routing

**Schema**:
```yaml
edges:
  - from: validate_node
    routes:
      - condition:
          logic: "{state.score} >= 8"
        to: END
      - condition:
          logic: "default"
        to: rewrite_node
```

**Implementation**:
- Safe condition evaluator (AST-like parsing, not eval())
- Route resolution at graph execution time
- Support for complex boolean expressions
- Fallback to "default" route for unmatched conditions

**Code**: [`core/graph_builder.py:conditional_edges`](../src/configurable_agents/core/graph_builder.py)

---

### Loop Execution

**Schema**:
```yaml
nodes:
  - id: retry_node
    loop:
      max_iterations: 3
      until: "{state.success} == true"
      break_on_error: false
```

**Implementation**:
- Hidden state fields for iteration tracking (`_loop_iteration_{node}`)
- Auto-increment on each iteration
- `until` condition evaluation per iteration
- Graceful handling of max_iterations exceeded

**Code**: [`core/graph_builder.py:loop_execution`](../src/configurable_agents/core/graph_builder.py)

---

### Fork-Join Parallel Execution

**Schema**:
```yaml
edges:
  - from: START
    to: [analyze_pros, analyze_cons]  # Fork: both nodes run in parallel
  - from: analyze_pros
    to: combine
  - from: analyze_cons
    to: combine                        # Join: both converge at combine
```

**Implementation**:
- `EdgeConfig.to` accepts `Union[str, List[str]]` — list means fork-join
- Each target in the list gets its own `graph.add_edge()` call
- LangGraph natively runs nodes in parallel when they share the same source
- Each branch writes to its own state fields (no shared state between branches)
- Join node receives merged state from all branches

**Design Decision**: Fork-join (different nodes concurrently) over MAP (same node on different data).
MAP pattern using LangGraph `Send` objects was removed because Send passes raw dicts, causing
Pydantic model compatibility issues. Fork-join uses native LangGraph edges with zero overhead.

**Code**: [`core/graph_builder.py:_add_edge`](../src/configurable_agents/core/graph_builder.py)

---

## Observability Architecture (v1.0)

**Status**: Complete (Phase 1, 2, 3, 4)

**Pattern**: MLFlow 3.9+ automatic tracing + manual cost/performance tracking

**Architecture**:
```
Runtime Executor
      ↓
MLFlow Automatic Tracing
  - Spans for workflow and nodes
  - Automatic token usage tracking
  - LLM call instrumentation
      ↓
Manual Metrics
  - Multi-provider cost tracking
  - Performance profiling (bottleneck detection)
  - Custom metrics (duration, retries)
      ↓
MLFlow Backend (SQLite/PostgreSQL)
  - Experiment aggregation
  - Cost reporting (CSV/JSON export)
  - A/B testing support
```

**Implementation**: See [ADR-011](adr/ADR-011-mlflow-observability.md), [ADR-014](adr/ADR-014-three-tier-observability-strategy.md)

**Detailed Guide**: See [OBSERVABILITY.md](OBSERVABILITY.md)

---

## Deployment Architecture (v1.0)

**Status**: Complete (Phase 3, 4)

**Pattern**: FastAPI + HTMX Dashboard + Webhook Server + Docker

**Architecture**:
```
configurable-agents dashboard
      ↓
FastAPI Server (port 8000)
  - Dashboard UI (HTMX + SSE)
  - Deployment registry endpoints (/deployments/*)
  - Execution management (/executions/*)
  - MLFlow iframe embed (port 5000)
      ↓
Webhook Server (port 8000/webhooks)
  - Generic webhook endpoint
  - Platform handlers (WhatsApp, Telegram)
  - HMAC signature verification
      ↓
Storage Backend (SQLite/PostgreSQL)
  - Executions (execution records with metrics)
  - Deployments (deployment registry with heartbeats)
  - Memory entries
  - Webhook executions
```

**Sync/Async Hybrid**:
- Fast workflows (<30s): Return result immediately
- Slow workflows (>30s): Background job, return job_id

**Implementation**: See [ADR-012](adr/ADR-012-docker-deployment-architecture.md), [ADR-013](adr/ADR-013-environment-variable-handling.md), [ADR-021](adr/ADR-021-htmx-dashboard.md)

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

### Adding a New LLM Provider

1. **Create provider file**: `src/configurable_agents/llm/openai.py` (if using LiteLLM)
   ```python
   from litellm import completion as litellm_completion
   from langchain_openai import ChatOpenAI

   def create_openai_llm(config: LLMConfig) -> BaseChatModel:
       # LiteLLM wrapper
       if config.model.startswith("gpt-"):
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
           return create_litellm_llm(config)
   ```

3. **Update schema**: `src/configurable_agents/config/schema.py`
   ```python
   class LLMConfig(BaseModel):
       provider: Literal["google", "openai", "anthropic", "ollama"] = "google"
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

### v1.0 Scope

- ✅ Safe code execution (RestrictedPython sandbox)
- ✅ Environment variable isolation (API keys from .env only)
- ✅ Input validation (Pydantic prevents injection)
- ✅ Tool sandboxing (LangChain BaseTool constraints, whitelisted paths/commands)
- ✅ Webhook security (HMAC signature verification, idempotency tracking)
- ✅ SQL injection protection (SELECT-only queries for sandbox)

### Future (v1.1+)

- Secrets management (vault integration)
- Resource limits (token budgets, timeouts) - partially implemented via presets
- Network sandboxing (Docker isolation - opt-in)
- Audit logging (who ran what, when) - partially implemented via MLFlow
- Rate limiting (webhook endpoint protection)

---

## Deep Dive References

**Detailed Decisions**: [Architecture Decision Records](adr/) (25+ ADRs)

**Implementation Tasks**: [TASKS.md](TASKS.md) (27 requirements, 100% complete)

**Version Features**: [README.md](../README.md#roadmap--status) (v0.1-v0.4 overview, v1.0 complete)

**Technical Specs**: [SPEC.md](SPEC.md) (Complete config schema reference + v1.0 extensions)

**User Guides**:
- [QUICKSTART.md](QUICKSTART.md) - Get started in 5 minutes
- [CONFIG_REFERENCE.md](CONFIG_REFERENCE.md) - Config schema guide
- [OBSERVABILITY.md](OBSERVABILITY.md) - MLFlow tracking guide
- [DEPLOYMENT.md](DEPLOYMENT.md) - Docker deployment guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues

**Milestone Archives**:
- [.planning/milestones/v1.0-ROADMAP.md](../.planning/milestones/v1.0-ROADMAP.md) - v1.0 roadmap
- [.planning/milestones/v1.0-REQUIREMENTS.md](../.planning/milestones/v1.0-REQUIREMENTS.md) - v1.0 requirements
- [.planning/milestones/v1.0-MILESTONE-AUDIT.md](../.planning/milestones/v1.0-MILESTONE-AUDIT.md) - v1.0 audit
