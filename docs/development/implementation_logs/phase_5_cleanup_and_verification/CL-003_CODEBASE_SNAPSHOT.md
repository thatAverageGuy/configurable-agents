# CL-003: Codebase Snapshot

**Purpose**: Detailed inventory of current codebase state for review and fixing
**Date**: 2026-02-07
**Status**: Active reference document

---

## Module Overview

Total: **82 Python files** across **17 modules**

| Module | Files | Purpose | Status |
|--------|-------|---------|--------|
| config/ | 5 | Config parsing, schema, validation | Core - needs verification |
| core/ | 8 | Graph building, node execution | Core - needs verification |
| runtime/ | 4 | Workflow execution orchestration | Core - needs verification |
| llm/ | 4 | LLM provider abstraction | Core - needs verification |
| tools/ | 7 | Tool registry and implementations | Extended - 15 tools |
| observability/ | 5 | MLFlow tracking, cost estimation | Core - needs verification |
| deploy/ | 2 | Docker artifact generation | Core - needs verification |
| storage/ | 5 | SQLite persistence | Extended |
| ui/ | 8 | Dashboard + Gradio Chat | Extended - known issues |
| memory/ | 2 | Persistent agent memory | Extended |
| sandbox/ | 4 | Code execution sandboxes | Extended |
| optimization/ | 4 | A/B testing, quality gates | Extended |
| orchestrator/ | 4 | Orchestration service | Extended |
| registry/ | 4 | Agent registry | Extended |
| webhooks/ | 5 | Telegram, WhatsApp | Extended |
| process/ | 2 | Process management | Extended |
| utils/ | 2 | Error formatting | Extended |

---

## Detailed Module Analysis

### 1. config/ - Configuration Layer

| File | Lines | Purpose | Notes |
|------|-------|---------|-------|
| `schema.py` | 672 | Pydantic models for WorkflowConfig | Full Schema v1.0 with extended features |
| `parser.py` | ~100 | YAML/JSON parsing | |
| `types.py` | ~150 | Type string resolution | |
| `validator.py` | ~300 | Business logic validation | |
| `__init__.py` | ~30 | Public exports | |

**Key Classes in schema.py**:
- `WorkflowConfig` - Top-level config
- `FlowMetadata` - Name, description, version
- `StateSchema` / `StateFieldConfig` - State definition
- `NodeConfig` - Node with prompt, outputs, tools
- `EdgeConfig` - Linear, conditional, loop, parallel edges
- `LLMConfig` - Provider, model, temperature
- `OutputSchema` - Structured output definition
- `ObservabilityMLFlowConfig` - MLFlow settings
- `SandboxConfig` - Code execution settings
- `MemoryConfig` - Agent memory settings

**Supported Providers**: openai, anthropic, google, ollama

**TODO**:
- [ ] Verify schema matches actual runtime implementation
- [ ] Check all field defaults are correct
- [ ] Verify validation error messages are helpful

---

### 2. core/ - Execution Engine

| File | Lines | Purpose | Notes |
|------|-------|---------|-------|
| `graph_builder.py` | ~300 | Build LangGraph from config | Core logic |
| `node_executor.py` | ~250 | Execute single node | LLM calls, tool binding |
| `state_builder.py` | ~150 | Generate Pydantic state model | Dynamic model creation |
| `output_builder.py` | ~100 | Validate node outputs | Type enforcement |
| `template.py` | ~100 | Resolve {placeholders} in prompts | |
| `control_flow.py` | ~200 | Conditional routing, loops | Extended feature |
| `parallel.py` | ~150 | Parallel execution | Extended feature |
| `__init__.py` | ~20 | Exports | |

**TODO**:
- [ ] Test linear flow execution
- [ ] Test conditional routing
- [ ] Test loop execution
- [ ] Test parallel execution
- [ ] Verify error handling

---

### 3. runtime/ - Execution Orchestration

| File | Lines | Purpose | Notes |
|------|-------|---------|-------|
| `executor.py` | 634 | Main run_workflow() function | Core orchestration |
| `feature_gate.py` | ~100 | Runtime feature validation | |
| `profiler.py` | ~150 | Bottleneck analysis | Extended |
| `__init__.py` | ~30 | Exports | |

**Key Functions**:
- `run_workflow(config_path, inputs, verbose)` - Main entry point
- `run_workflow_from_config(config, inputs)` - From pre-loaded config
- `validate_workflow(config_path)` - Validation only
- `run_workflow_async()` - Async wrapper

**Execution Phases**:
1. Load and parse config
2. Pydantic validation
3. Business logic validation
4. Feature gate check
5. Initialize storage (optional)
6. Build state model
7. Initialize state with inputs
8. Create workflow run record
9. Initialize MLFlow tracker
10. Build graph
11. Initialize profiler
12. Execute graph
13. Check quality gates
14. Update run record

**TODO**:
- [ ] Test basic execution
- [ ] Test error handling
- [ ] Test MLFlow integration
- [ ] Test storage persistence

---

### 4. llm/ - LLM Provider

| File | Lines | Purpose | Notes |
|------|-------|---------|-------|
| `provider.py` | 373 | Factory function, call_llm_structured | |
| `google.py` | ~150 | Google Gemini implementation | Direct LangChain |
| `litellm_provider.py` | ~200 | LiteLLM multi-provider | Extended |
| `__init__.py` | ~20 | Exports | |

**Supported Providers**:
- `google` - Direct implementation (default)
- `openai` - Via LiteLLM
- `anthropic` - Via LiteLLM
- `ollama` - Via LiteLLM

**Key Functions**:
- `create_llm(llm_config, global_config)` - Factory
- `call_llm_structured(llm, prompt, output_model, tools)` - Structured output

**TODO**:
- [ ] Test Google provider
- [ ] Test LiteLLM providers (if installed)
- [ ] Test tool binding
- [ ] Test structured output

---

### 5. tools/ - Tool Registry

| File | Purpose |
|------|---------|
| `registry.py` | Tool registration and lookup |
| `serper.py` | Serper web search |
| `web_tools.py` | web_search, web_scrape, http_client |
| `file_tools.py` | file_read, file_write, file_glob, file_move |
| `data_tools.py` | json_parse, yaml_parse, dataframe_to_csv, sql_query |
| `system_tools.py` | env_vars, process, shell |
| `__init__.py` | Exports |

**Available Tools (15)**:
```
dataframe_to_csv, env_vars, file_glob, file_move, file_read, file_write,
http_client, json_parse, process, serper_search, shell, sql_query,
web_scrape, web_search, yaml_parse
```

**TODO**:
- [ ] Test each tool individually
- [ ] Verify API key handling
- [ ] Check error handling

---

### 6. observability/ - MLFlow Integration

| File | Purpose |
|------|---------|
| `mlflow_tracker.py` | MLFlow 3.9 auto-tracing |
| `cost_estimator.py` | Token → USD conversion |
| `cost_reporter.py` | Query and export costs |
| `multi_provider_tracker.py` | Multi-provider cost tracking |
| `__init__.py` | Exports |

**TODO**:
- [ ] Test MLFlow tracking
- [ ] Test cost estimation
- [ ] Test cost reporting CLI

---

### 7. deploy/ - Docker Deployment

| File | Purpose |
|------|---------|
| `generator.py` | Generate Dockerfile, server.py, etc. |
| `__init__.py` | Exports |

**Generated Artifacts**:
- Dockerfile
- server.py (FastAPI)
- docker-compose.yml
- requirements.txt
- .env.example
- README.md
- .dockerignore

**TODO**:
- [ ] Test artifact generation
- [ ] Test Docker build
- [ ] Test deployed container

---

### 8. storage/ - Persistence Layer

| File | Purpose |
|------|---------|
| `base.py` | Abstract repository interfaces |
| `models.py` | SQLAlchemy ORM models |
| `sqlite.py` | SQLite implementation |
| `factory.py` | create_storage_backend() |
| `__init__.py` | Exports |

**Models**:
- WorkflowRunRecord
- ExecutionStateRecord
- ChatSession / ChatMessage
- AgentRecord
- MemoryRecord

**TODO**:
- [ ] Test storage initialization
- [ ] Test CRUD operations
- [ ] Test graceful degradation when storage fails

---

### 9. ui/ - User Interfaces

**Dashboard** (ui/dashboard/):
| File | Purpose | Status |
|------|---------|--------|
| `app.py` | FastAPI app creation | |
| `routes/workflows.py` | Workflow list/detail | Fixed |
| `routes/agents.py` | Agent list/detail | Fixed |
| `routes/orchestrator.py` | Orchestration | |
| `routes/optimization.py` | A/B testing UI | Fixed |
| `routes/metrics.py` | Metrics display | |
| `routes/status.py` | Status endpoint | |

**Gradio Chat** (ui/gradio_chat.py):
- Status: **KNOWN BROKEN** - Multi-turn crashes

**TODO**:
- [ ] Test Dashboard loads
- [ ] Test each route
- [ ] Test Chat UI (known broken)

---

### 10. Extended Modules (Less Critical)

| Module | Purpose | Priority |
|--------|---------|----------|
| memory/ | Agent persistent memory | P2 |
| sandbox/ | Code execution | P3 |
| optimization/ | A/B testing, gates | P3 |
| orchestrator/ | Service orchestration | P2 |
| registry/ | Agent registry | P2 |
| webhooks/ | External triggers | P3 |
| process/ | Process management | P2 |
| utils/ | Error formatting | P3 |

---

## CLI Commands

```bash
# Core commands
configurable-agents run <config.yaml> --input key=value
configurable-agents validate <config.yaml>
configurable-agents deploy <config.yaml>

# UI commands
configurable-agents ui                    # Start dashboard + chat
configurable-agents ui --dashboard-only   # Dashboard only
configurable-agents ui --chat-only        # Chat only

# Observability commands
configurable-agents report costs --range last_7_days
configurable-agents report costs --format csv --output report.csv
configurable-agents profile-report
```

---

## Environment Variables

**Required**:
- `GOOGLE_API_KEY` - For Google Gemini LLM

**Optional** (for extended features):
- `SERPER_API_KEY` - For web search
- `OPENAI_API_KEY` - For OpenAI LLM
- `ANTHROPIC_API_KEY` - For Anthropic LLM
- `TAVILY_API_KEY` - For Tavily search

---

## Known Issues

| Component | Issue | Status |
|-----------|-------|--------|
| Chat UI | Multi-turn conversations crash | NOT FIXED |
| Chat UI | Download/Validate buttons crash | NOT FIXED |
| Tests | Heavily mocked, don't verify real functionality | Known |

---

## Testing Checklist

### P0 - Core Functionality
- [ ] `configurable-agents validate sample_config.yaml`
- [ ] `configurable-agents run sample_config.yaml --input message="test"`
- [ ] `configurable-agents deploy sample_config.yaml --generate`

### P1 - Extended Core
- [ ] Dashboard loads at http://localhost:8001
- [ ] MLFlow tracking works
- [ ] Docker deployment produces working container

### P2 - Extended Features
- [ ] Multi-LLM support
- [ ] Conditional routing
- [ ] Loops
- [ ] Memory persistence

### P3 - Optional Features
- [ ] Webhooks
- [ ] Sandboxes
- [ ] A/B testing

---

*This document is updated as we verify each component.*
