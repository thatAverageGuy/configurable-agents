# Architecture Overview

**Status**: Living document (updated as system evolves)
**Version**: v0.1 design
**Last Updated**: 2026-01-24

---

## System Overview

The system transforms YAML configuration into executable agent workflows.

```
┌──────────────┐
│ YAML Config  │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Config Parser    │ ← Parse YAML, validate schema
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Config Validator │ ← Validate dependencies, types, references
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Graph Builder    │ ← Construct LangGraph execution graph
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Runtime Executor │ ← Execute graph with inputs
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Outputs (JSON)   │
└──────────────────┘
```

---

## Component Architecture (v0.1)

### 1. Config Parser
**Responsibility**: Load and parse YAML/JSON into Python dict

**Implementation**:
- Use `pyyaml` for YAML parsing (.yaml, .yml files)
- Use built-in `json` for JSON parsing (.json files)
- Auto-detect format from file extension
- No validation at this layer (just syntax checking)
- Return raw dict structure
- Class-based with convenience function wrappers

**Architecture**:
```python
class ConfigLoader:
    def load_file(self, path: str) -> dict:
        """Load from YAML or JSON file (auto-detect)"""

    def _parse_file(self, path: str) -> dict:
        """Parse file to dict based on extension"""

# User-facing convenience function
def parse_config_file(path: str) -> dict:
    return ConfigLoader().load_file(path)
```

**Supported Formats**:
- YAML: `.yaml`, `.yml` (primary format)
- JSON: `.json` (alternative format, same schema)

**Path Handling**:
- Absolute paths: `/full/path/to/config.yaml`
- Relative paths: `./config.yaml` (resolved from cwd)

**Files**:
- `config/parser.py`

---

### 2. Config Validator
**Responsibility**: Validate config structure, types, and dependencies

**Validation Rules**:
- Required top-level keys: `flow`, `state`, `nodes`, `edges`
- Node IDs are unique
- Edge references point to valid nodes
- State fields have valid types
- Tool references exist in registry
- No circular dependencies in edges
- Inputs/outputs reference valid state fields
- Pydantic schemas are valid

**Implementation**:
- Pure Python validation functions
- Return typed errors with helpful messages
- Fail fast on first error OR collect all errors (TBD)

**Files**:
- `config/validator.py`
- `config/schema.py` (Pydantic models for config structure)

---

### 3. State Schema Builder
**Responsibility**: Generate Pydantic models from state config

**Input** (from config):
```yaml
state:
  fields:
    topic:
      type: str
      required: true
    research:
      type: str
      default: ""
```

**Output**: Dynamically created Pydantic `BaseModel` subclass

**Implementation**:
- Use `type()` to create classes at runtime
- Support basic types: `str`, `int`, `float`, `bool`, `list`, `dict`
- Support nested types: `list[str]`, `dict[str, int]`
- Validate at instantiation time

**Files**:
- `core/state_builder.py`

---

### 4. Output Schema Builder
**Responsibility**: Generate Pydantic models for node outputs

**Input** (from config):
```yaml
nodes:
  - id: research
    output_schema:
      fields:
        - name: summary
          type: str
        - name: sources
          type: list[str]
```

**Output**: Pydantic model that LLM must conform to

**Implementation**:
- Similar to State Schema Builder
- Used for structured LLM outputs (JSON mode)
- Validation ensures LLM output matches schema

**Files**:
- `core/output_builder.py`

---

### 5. Tool Registry
**Responsibility**: Provide tools to nodes by name

**Interface**:
```python
def get_tool(tool_name: str) -> BaseTool:
    """Load a tool by name from registry"""
```

**v0.1 Tools**:
- `serper_search` (Google search via Serper API)

**Implementation**:
- Use LangChain tools
- Load API keys from environment variables
- Fail loudly if tool not found or API key missing

**Files**:
- `tools/registry.py`
- `tools/serper.py`

---

### 6. LLM Provider
**Responsibility**: Execute LLM calls with structured outputs

**v0.1 Support**:
- Google Gemini only (`gemini-2.0-flash-exp` as default)

**Configuration** (global defaults):
```yaml
config:
  llm:
    provider: google
    model: gemini-2.0-flash-exp
    temperature: 0.7
    max_tokens: 1024
```

**Node-level overrides**:
```yaml
nodes:
  - id: research
    llm:
      temperature: 0.5
      max_tokens: 512
```

**Implementation**:
- Use LangChain's `ChatGoogleGenerativeAI`
- Force structured outputs using Pydantic schemas
- Read `GOOGLE_API_KEY` from environment

**Files**:
- `llm/provider.py`
- `llm/google.py`

---

### 7. Node Executor
**Responsibility**: Execute a single node (LLM call + optional tools)

**Node Structure**:
```yaml
nodes:
  - id: research
    description: "Research the topic"
    prompt: |
      Research the topic: {state.topic}
      Return a summary and list of sources.
    inputs:
      - topic  # References state.topic
    output_schema:
      fields:
        - name: summary
          type: str
        - name: sources
          type: list[str]
    tools:
      - serper_search
    llm:
      temperature: 0.5
```

**Execution Flow**:
1. Resolve prompt template from current state
2. Load tools from registry
3. Configure LLM with node settings
4. Call LLM with structured output schema
5. Validate output against schema
6. Update state with output fields

**Implementation**:
- Each node execution is a pure function: `(state, node_config) -> updated_state`
- No side effects except LLM API calls
- Log inputs/outputs at debug level

**Files**:
- `core/node_executor.py`

---

### 8. Graph Builder
**Responsibility**: Construct LangGraph execution graph from config

**Input** (from config):
```yaml
edges:
  - from: START
    to: research
  - from: research
    to: write
  - from: write
    to: END
```

**Output**: LangGraph `StateGraph` instance

**Implementation**:
- Use LangGraph's `StateGraph` API
- Add nodes as functions
- Add edges for control flow
- v0.1: Linear flows only (no conditionals)

**Files**:
- `core/graph_builder.py`

---

### 9. Runtime Executor
**Responsibility**: Execute the graph with initial inputs

**Interface**:
```python
def run_workflow(config: dict, inputs: dict) -> dict:
    """
    Execute a workflow from config.

    Args:
        config: Validated config dict
        inputs: Initial state values

    Returns:
        Final state as dict
    """
```

**Execution Flow**:
1. Validate config
2. Build state schema
3. Initialize state with inputs
4. Build graph
5. Execute graph
6. Return final state

**Error Handling**:
- Config validation errors → return immediately with error details
- Node execution errors → crash loudly with full context
- LLM timeout/rate limit → retry with exponential backoff (configurable)

**Files**:
- `core/runtime.py`

---

## Data Flow (v0.1)

### Example Workflow: Article Writer

**Config**:
```yaml
flow:
  name: article_writer

state:
  fields:
    topic: {type: str, required: true}
    research: {type: str, default: ""}
    article: {type: str, default: ""}

nodes:
  - id: research
    prompt: "Research {state.topic} and return a summary."
    output_schema:
      fields:
        - name: summary
          type: str
    tools: [serper_search]

  - id: write
    prompt: "Write an article about {state.topic} using: {state.research}"
    output_schema:
      fields:
        - name: article
          type: str

edges:
  - {from: START, to: research}
  - {from: research, to: write}
  - {from: write, to: END}
```

**Execution**:
```python
result = run_workflow(
    config=load_config("article_writer.yaml"),
    inputs={"topic": "AI Safety"}
)

# result = {
#     "topic": "AI Safety",
#     "research": "AI safety focuses on...",
#     "article": "In recent years, AI safety has..."
# }
```

---

## Deferred to Later Versions

### Not in v0.1:
- **Conditional edges** (if/else routing)
- **Loops** (retry logic, iterations)
- **Parallel execution** (multiple branches)
- **Persistent mode** (Docker container deployment)
- **Multiple LLM providers** (OpenAI, Anthropic, local)
- **MLFlow integration** (observability beyond console logs)
- **DSPy optimization**
- **Custom code nodes** (Python function execution)
- **Long-term memory** (vector DBs, SQLite)

These will be added incrementally in future versions based on `docs/TASKS.md`.

---

## Technology Stack (v0.1)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Config Format | YAML | Human-readable, git-friendly |
| Validation | Pydantic | Industry standard, excellent errors |
| Execution Engine | LangGraph | Explicit state machines, no hidden magic |
| LLM Provider | LangChain + Google Gemini | Simple integration, good free tier |
| Tools | LangChain Tools | Large ecosystem, standard interface |
| Testing | pytest | Standard Python testing |
| Logging | stdlib logging | Simple, no dependencies |

---

## Design Principles

### 1. Explicit Over Implicit
- State changes are visible in config
- Control flow is explicit in edges
- No hidden behavior

### 2. Fail Fast
- Validate at parse time, not runtime
- Catch errors before expensive LLM calls
- Clear error messages with suggested fixes

### 3. Testability
- Pure functions wherever possible
- No global state
- Mockable LLM calls for testing

### 4. Incremental Complexity
- v0.1 is intentionally limited (linear flows only)
- Add features incrementally with clear boundaries
- Avoid premature abstraction

---

## Security Considerations

### v0.1 Scope:
- **No arbitrary code execution** (deferred custom code nodes)
- **Environment variable isolation** (API keys from .env only)
- **Input validation** (Pydantic schemas prevent injection)
- **Tool sandboxing** (tools can only do what LangChain allows)

### Future Considerations:
- Secrets management (vault integration)
- Resource limits (token budgets, timeouts)
- Network sandboxing (for container mode)
- Audit logging (who ran what, when)

---

## Observability Layer (MLFlow) - v0.1

### Responsibility
Track workflow execution metrics, costs, and performance for debugging and optimization.

### Architecture

```
Runtime Executor
      ↓
┌─────────────────────────────────────┐
│  MLFlow Tracking                    │
│                                     │
│  Workflow Run:                      │
│  - params (name, model, temp)       │
│  - metrics (duration, tokens, cost) │
│  - artifacts (inputs, outputs)      │
│                                     │
│  Node Runs (nested):                │
│  - params (node_id, tools)          │
│  - metrics (duration, retries)      │
│  - artifacts (prompt, response)     │
└─────────────────────────────────────┘
      ↓
file://./mlruns (local)
or postgresql:// (remote)
or s3:// (cloud)
```

### Components

**MLFlow Tracker** (`observability/mlflow_tracker.py`):
- Initialize tracking (set URI, experiment)
- Start/end workflow runs
- Log parameters, metrics, artifacts
- Handle disabled state gracefully (no-op)

**Cost Tracker** (`llm/cost_tracker.py`):
- Token-to-cost conversion (pricing tables)
- Per-model pricing (Gemini, OpenAI, Anthropic)
- Cumulative cost calculation

### Integration Points

1. **Runtime Executor** (`runtime/executor.py`):
   - Start MLFlow run on workflow start
   - Log workflow-level params/metrics
   - Log inputs/outputs as artifacts
   - End run on completion/failure

2. **Node Executor** (`core/node_executor.py`):
   - Start nested run per node
   - Log node-level params/metrics
   - Log prompt/response as artifacts
   - Extract token counts from LLM responses

3. **LLM Provider** (`llm/provider.py`):
   - Return token counts with responses
   - Enable cost calculation

### Configuration

```yaml
config:
  observability:
    mlflow:
      enabled: true
      tracking_uri: "file://./mlruns"  # Local file storage
      experiment_name: "production_workflows"
      log_artifacts: true
```

### Data Flow

```
Workflow Execution
      ↓
[MLFlow enabled?] → No → Execute normally
      ↓ Yes
Start MLFlow run
      ↓
Execute nodes (with nested runs)
      ↓
Log metrics (tokens, cost, duration)
      ↓
Save artifacts (inputs, outputs, prompts)
      ↓
End MLFlow run
```

### Storage Backends

- **v0.1**: File-based (`file://./mlruns`) - zero setup
- **v0.2**: Remote (PostgreSQL, S3, Databricks)
- **Enterprise**: Multi-tenancy, retention policies, PII redaction

### Related ADRs
- ADR-011: MLFlow for Observability
- ADR-014: Three-Tier Observability Strategy

---

## Deployment Architecture (Docker) - v0.1

### Responsibility
Package workflows as standalone Docker containers with FastAPI servers.

### Architecture

```
configurable-agents deploy workflow.yaml
      ↓
┌─────────────────────────────────────┐
│  Artifact Generator                 │
│                                     │
│  Templates:                         │
│  - Dockerfile (multi-stage)         │
│  - server.py (FastAPI)              │
│  - requirements.txt                 │
│  - docker-compose.yml               │
│  - README.md                        │
└─────────────────────────────────────┘
      ↓
docker build -t workflow:latest .
      ↓
docker run -d -p 8000:8000 -p 5000:5000 workflow
      ↓
┌─────────────────────────────────────┐
│  Running Container                  │
│                                     │
│  Port 8000: FastAPI Server          │
│  - POST /run (sync/async)           │
│  - GET /status/{job_id}             │
│  - GET /health                      │
│  - GET /schema                      │
│                                     │
│  Port 5000: MLFlow UI               │
│  - View execution traces            │
│  - Track costs, prompts             │
└─────────────────────────────────────┘
```

### Components

**Artifact Generator** (`deploy/generator.py`):
- Load templates from `deploy/templates/`
- Substitute variables (workflow_name, ports, timeout)
- Generate Dockerfile, server.py, etc.
- Write to output directory

**FastAPI Server** (generated `server.py`):
- Load workflow config at startup
- POST /run endpoint (sync/async execution)
- Job store (in-memory dict for v0.1)
- Background task execution
- Input validation against workflow schema
- OpenAPI docs auto-generated

**Docker Image** (generated `Dockerfile`):
- Multi-stage build (builder + runtime)
- Base: `python:3.10-slim` (~120MB)
- Optimizations: no cache, minimal deps
- Health check for orchestration
- MLFlow UI startup (if enabled)

### Deployment Flow

```
1. Validate workflow (fail-fast)
2. Check Docker installed
3. Generate artifacts
   ├─ Dockerfile
   ├─ server.py
   ├─ requirements.txt
   ├─ docker-compose.yml
   └─ README.md
4. Build Docker image
5. Run container (detached)
6. Print success message
```

### Sync/Async Hybrid

```python
# FastAPI endpoint logic
async def run_workflow_endpoint(inputs):
    try:
        # Attempt sync (with timeout)
        result = await asyncio.wait_for(
            asyncio.to_thread(run_workflow, config, inputs),
            timeout=SYNC_TIMEOUT  # Default: 30s
        )
        return {"status": "success", "outputs": result}

    except asyncio.TimeoutError:
        # Fall back to async
        job_id = str(uuid.uuid4())
        jobs[job_id] = {"status": "pending", ...}
        background_tasks.add_task(run_workflow_async, job_id, inputs)
        return {"status": "async", "job_id": job_id}
```

### Environment Variables

**CLI** (`--env-file`):
```bash
configurable-agents deploy workflow.yaml --env-file .env
# Auto-detects .env if exists
```

**Streamlit UI**:
- Upload .env file (drag & drop)
- Paste variables (textarea)
- Skip (configure later via docker run -e)

**Security**:
- Never baked into image layers
- Injected at runtime (docker run --env-file)
- Values masked in UI preview

### Image Optimization

**Multi-stage build**:
```dockerfile
# Stage 1: Builder
FROM python:3.10-slim AS builder
RUN pip install --user -r requirements.txt

# Stage 2: Runtime (no build tools)
FROM python:3.10-slim
COPY --from=builder /root/.local /root/.local
COPY workflow.yaml server.py ./
CMD mlflow ui & python server.py
```

**Target size**: ~180-200MB (acceptable for v0.1)

### Related ADRs
- ADR-012: Docker Deployment Architecture
- ADR-013: Environment Variable Handling

---

## Open Questions (To be resolved in ADRs)

1. Should validation fail fast (first error) or collect all errors?
2. How should we handle LLM timeouts and retries?
3. Should tools be configurable per-invocation or global only?
4. How do we version config schemas as features evolve?
5. Should we support YAML anchors/aliases for DRY configs?

These will be documented in `docs/adr/` as decisions are made.
