# Architecture

**Analysis Date:** 2026-02-02

## Pattern Overview

**Overall:** Config-driven pipeline with declarative YAML → runtime schema generation → LangGraph execution

**Key Characteristics:**
- Fail-fast validation at parse time (catch 95% of errors before LLM execution)
- Immutable, layered architecture: Config → Schema → Builder → Executor
- Dynamic Pydantic schema generation from YAML type strings (no code generation)
- LangGraph as execution substrate with closure-based node functions
- Observability-first design with MLFlow tracking from day one

## Layers

**Configuration Layer:**
- Purpose: Parse and validate YAML/JSON workflow definitions
- Location: `src/configurable_agents/config/`
- Contains: Parser (`parser.py`), Schema models (`schema.py`), Type resolver (`types.py`), Business logic validator (`validator.py`)
- Depends on: `pydantic`, `pyyaml`
- Used by: Runtime executor, all downstream components

**Core Execution Layer:**
- Purpose: Transform validated config into executable LangGraph, manage state and node execution
- Location: `src/configurable_agents/core/`
- Contains:
  - `state_builder.py`: Generate Pydantic models from state schema (WorkflowState class)
  - `graph_builder.py`: Build compiled LangGraph from config and state model
  - `node_executor.py`: Execute individual nodes with template resolution, LLM calls, tool binding
  - `output_builder.py`: Enforce output schema validation
  - `template.py`: Resolve {field} syntax in prompts
- Depends on: `langgraph`, `langchain-core`, `pydantic`
- Used by: Runtime executor

**Runtime Layer:**
- Purpose: Orchestrate the full workflow lifecycle: load → validate → build → execute → track
- Location: `src/configurable_agents/runtime/`
- Contains:
  - `executor.py`: Main entry point (`run_workflow`, `validate_workflow`) with comprehensive error handling
  - `feature_gate.py`: Runtime feature support validation for versioning
- Depends on: Config, Core, Observability, LLM, Tools layers
- Used by: CLI, Deployment, UI

**LLM Integration Layer:**
- Purpose: Abstract LLM provider calls with structured output support
- Location: `src/configurable_agents/llm/`
- Contains:
  - `provider.py`: Factory and call interface (`create_llm`, `call_llm_structured`)
  - `google.py`: Google Gemini implementation (v0.1 only)
- Depends on: `langchain-google-genai`, `langchain-core`
- Used by: Node executor

**Tools Layer:**
- Purpose: Centralized registry for tools available to nodes
- Location: `src/configurable_agents/tools/`
- Contains:
  - `registry.py`: Tool registration and lookup by name
  - `serper.py`: Web search implementation (v0.1)
- Depends on: `langchain-community`
- Used by: Node executor

**Observability Layer:**
- Purpose: Cost tracking, metrics, and workflow profiling via MLFlow
- Location: `src/configurable_agents/observability/`
- Contains:
  - `mlflow_tracker.py`: MLFlow integration (run creation, metric/param logging)
  - `cost_estimator.py`: Token count → USD conversion by model/provider
  - `cost_reporter.py`: Query, aggregate, export cost data (CSV/JSON)
- Depends on: `mlflow>=3.9.0`
- Used by: Runtime executor, CLI reporting

**Deployment Layer:**
- Purpose: Generate production Docker containers and FastAPI servers
- Location: `src/configurable_agents/deploy/`
- Contains:
  - `generator.py`: Artifact generation (Dockerfile, main.py, docker-compose, .env.example)
- Depends on: config module, templates
- Used by: CLI deploy command

**CLI & UI Layer:**
- Purpose: User-facing interfaces for execution, validation, deployment, reporting
- Location: `src/configurable_agents/cli.py`, `streamlit_app.py`
- Contains: Argument parsing, command dispatch, error display
- Depends on: All lower layers
- Used by: End users

## Data Flow

**Workflow Execution Flow (Happy Path):**

1. **Load**: `parse_config_file(path)` → dict
2. **Validate (Pydantic)**: `WorkflowConfig(**dict)` → raises if schema violated
3. **Validate (Business)**: `validate_config(config)` → checks dependencies, node references, edges
4. **Build State**: `build_state_model(config.state)` → generates `WorkflowState` Pydantic class dynamically
5. **Build Graph**: `build_graph(config, state_model)` → creates LangGraph with nodes, edges, START/END
6. **Initialize State**: `state_model(**inputs)` → validate inputs match state schema
7. **Execute**: `graph.invoke(initial_state)` → LangGraph executes nodes sequentially
8. **Return**: Final state dict as output

**Node Execution (inside graph):**

1. **Resolve inputs**: Map node input fields to state fields
2. **Resolve prompt**: Replace `{field}` placeholders with state values
3. **Create LLM**: `create_llm(merged_config)` with node+global LLM settings
4. **Call LLM**: `call_llm_structured(llm, prompt, output_schema)` with tool binding
5. **Validate output**: `build_output_model(schema).parse_obj(llm_response)`
6. **Update state**: Copy-on-write pattern, return updated state dict

**Error Handling:**

- **Parse phase**: `ConfigLoadError` - file not found, YAML syntax
- **Validation phase**: `ConfigValidationError` - semantic errors (missing node references, type mismatches)
- **State init**: `StateInitializationError` - required fields missing, wrong types
- **Graph build**: `GraphBuildError` - LangGraph construction failure (shouldn't happen after validation)
- **Execution**: `WorkflowExecutionError` - node failure, LLM error, tool error
- All wrapped with context (phase, node_id, original error) for debugging

**State Management:**

- Immutable Pydantic model instance passed through graph
- Nodes return updated state dict (copy-on-write)
- LangGraph automatically merges returned state into graph state
- No side effects outside the state model

## Key Abstractions

**WorkflowConfig:**
- Purpose: Type-safe representation of entire workflow config
- Examples: `src/configurable_agents/config/schema.py` (lines 1-300+)
- Pattern: Nested Pydantic models (FlowMetadata, StateSchema, NodeConfig, EdgeConfig, GlobalConfig)
- Constraints: Validated at parse time; business logic validators ensure node references exist, types are valid

**NodeConfig:**
- Purpose: Single node definition (LLM call + tools + output)
- Pattern: Prompt template, LLM settings override, output schema, input/output mappings
- Key fields: `id`, `prompt`, `llm` (optional), `output_schema`, `inputs` (mapping), `outputs` (list)

**StateSchema:**
- Purpose: Define workflow state structure and types
- Pattern: Dict of field name → StateFieldConfig (type string, required, default, description)
- Type strings: `str`, `int`, `bool`, `float`, `list[T]`, `dict`, `object` (with nested schema)
- Converted to: Pydantic BaseModel subclass at runtime

**CompiledStateGraph (from LangGraph):**
- Purpose: Executable workflow graph ready for invocation
- Pattern: Nodes (START, user nodes, END), edges, state schema
- Execution: Deterministic, linear in v0.1 (no branches/loops until v0.2)

**MLFlowTracker:**
- Purpose: Track workflow runs with metrics, costs, artifacts
- Pattern: Log to MLFlow experiment/runs; store workflow name, model, tokens, cost per node
- Used by: Runtime executor (logs metrics after node execution, at end of run)

## Entry Points

**CLI Entry Point:**
- Location: `src/configurable_agents/cli.py:main()`
- Triggers: `configurable-agents` command (defined in pyproject.toml)
- Responsibilities:
  - Parse CLI args (run, validate, deploy, report)
  - Load config, invoke appropriate handler
  - Pretty-print results and errors
  - Handle Docker, port management for deploy command

**Runtime Entry Point:**
- Location: `src/configurable_agents/runtime/executor.py:run_workflow(config_path, inputs, verbose)`
- Triggers: Called by CLI `run` command, deploy server, Streamlit UI
- Responsibilities:
  - Full orchestration: parse → validate → build → execute
  - Observability: Initialize MLFlow tracker
  - Error handling: Wrap exceptions with context
  - Returns: Final state dict

**Validation Entry Point:**
- Location: `src/configurable_agents/runtime/executor.py:validate_workflow(config_path)`
- Triggers: Called by CLI `validate` command
- Responsibilities:
  - Config load + Pydantic validation + business logic validation
  - Returns: None (raises on error)

**Deployment Entry Point:**
- Location: `src/configurable_agents/deploy/generator.py:generate_deployment_artifacts()`
- Triggers: Called by CLI `deploy` command
- Responsibilities:
  - Generate Dockerfile, FastAPI server template, docker-compose
  - Return dict of artifact_name → file path

**Streamlit UI Entry Point:**
- Location: `streamlit_app.py`
- Triggers: `streamlit run streamlit_app.py`
- Responsibilities:
  - Interactive YAML editor
  - Config validation feedback
  - Workflow execution with input collection
  - Deployment artifact generation

## Error Handling

**Strategy:** Fail-fast, context-rich exceptions with phase information

**Hierarchy:**
```
ExecutionError (base)
├── ConfigLoadError (parse/file issues)
├── ConfigValidationError (semantic errors)
├── StateInitializationError (input validation)
├── GraphBuildError (LangGraph construction - shouldn't happen)
└── WorkflowExecutionError (runtime node/LLM failure)
```

**Patterns:**

- **Config validation**: Pydantic model raises `ValidationError` → caught and re-raised as `ConfigValidationError` with message
- **Business logic**: `validate_config()` raises `ValidationError` → caught and re-raised as `ConfigValidationError`
- **Node execution**: `execute_node()` catches `LLMAPIError`, `ToolConfigError`, `ValidationError` → raises `NodeExecutionError` with node_id
- **Graph build**: Exceptions bubble up as `GraphBuildError` (defensive check - shouldn't happen)
- **CLI display**: Each error type has dedicated handler that prints with color/symbol, full traceback with --verbose

## Cross-Cutting Concerns

**Logging:**
- Approach: Standard Python `logging` module with module-level loggers
- Config: `logging_config.py` sets up format and levels (DEBUG/INFO/WARNING/ERROR)
- Usage: Debug logs at config parse, validation, graph build, node execution; info logs for workflow start/end
- Verbose flag: CLI sets root logger to DEBUG when --verbose

**Validation:**
- **Pydantic validation**: Automatic on `WorkflowConfig(**dict)` instantiation
- **Business logic validation**: `validate_config()` checks:
  - All node IDs referenced in edges exist
  - START/END edges present
  - No circular edges (in v0.1, linear flows only)
  - Tool names are registered
  - LLM config valid (model, provider supported)
- **State validation**: `build_state_model()` creates Pydantic model; `state_model(**inputs)` validates input types/required
- **Output validation**: `build_output_model()` creates schema validator; `execute_node()` validates LLM response

**Authentication:**
- Approach: Environment variables (no secrets in config files)
- Managed by: Each provider/tool reads from `os.environ` (e.g., `GOOGLE_API_KEY`, `SERPER_API_KEY`)
- Deployment: Docker entrypoint loads from .env file or sets via `docker run -e`
- No API key validation at config time (deferred to execution)

**Observability (MLFlow):**
- Auto-enabled in v0.1 (not optional in runtime, but disable-able in deploy)
- Tracks: Experiment = workflow name, Run per execution, metrics per node (input_tokens, output_tokens, cost_usd)
- Query: `CostReporter` queries MLFlow runs via API; exports to CSV/JSON
- Params logged: model, provider, node_id, status
- Artifacts: None logged in v0.1 (future: store prompt templates, configs)

