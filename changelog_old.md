# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**This is the historical v0.1 changelog archive. For current changelog, see [CHANGELOG.md](CHANGELOG.md)**

---

## [0.1.0-dev] - 2026-01-24 to 2026-02-02

### 🎉 Initial Alpha Release: Linear Workflow Foundation

**v0.1 Foundation** - 4 phases, 25 tasks, 645 tests (100% pass rate)

Initial working alpha with linear workflows, Google Gemini integration, MLFlow 3.9 observability, and Docker deployment.

---

### Phase 1: Foundation (2026-01-24 to 2026-01-26)

#### Project Setup and Configuration

- **Package structure**: `src/configurable_agents/` layout with proper module organization
- **Core dependencies**: pydantic>=2.0, pyyaml, langgraph, langchain, google-genai, pytest
- **Logging infrastructure**: Application-wide formatters with structured output
- **3 setup tests**: package_version, imports, logging_config
- **Commit**: `4c4ab10`

#### YAML/JSON Config Parser

- **Automatic format detection**: Handles both YAML and JSON configs seamlessly
- **Class-based ConfigLoader**: Reusable loader with convenience functions
- **18 parser tests**: Comprehensive coverage for valid and invalid configs
- **Error handling**: File context with helpful error messages and suggestions
- **Config validation**: Early detection of malformed configuration files

#### Complete Config Schema (Pydantic Models)

- **Full Schema v1.0**: All v0.3 features from day one (Full Schema Day One - ADR-009)
- **13 Pydantic models**: WorkflowConfig, FlowMetadata, StateSchema, NodeConfig, EdgeConfig, etc.
- **103 comprehensive tests**: 31 type tests + 67 schema tests + 5 integration tests
- **Nested object support**: Full support for complex data structures
- **Collection types**: Lists, dicts, optional fields, and future-proof extensions

#### Config Validator

- **Comprehensive validation logic**: Beyond Pydantic schema validation
- **Multi-level validation**: Schema version, flow, state, node, edge, and optimization checks
- **Rich error messages**: File name, line number, context, and "Did you mean?" suggestions
- **265 lines of validation logic**: Thorough coverage of edge cases
- **User-friendly errors**: Clear guidance on how to fix validation failures

#### Runtime Feature Gating

- **Version-aware feature detection**: Rejects configs with v0.2+ features
- **Clear messaging**: Warns users about feature availability timeline
- **UnsupportedFeatureError**: Helpful error messages explaining what's not available
- **Future-proof**: Easy to extend for new feature sets

#### Type System

- **Type parsing and validation**: Full support for config type strings
- **Three type categories**: Basic types (str, int, float, bool), collections (list, dict), nested objects
- **31 comprehensive tests**: Complete coverage of type system
- **Type enforcement**: Ensures data integrity throughout execution

#### State Schema Builder

- **Dynamic Pydantic BaseModel generation**: Creates models from state config at runtime
- **Recursive nested object support**: Handles arbitrarily deep nesting
- **30 tests**: Simple, nested, deeply nested, and "kitchen sink" scenarios
- **207 lines of state builder code**: Robust implementation
- **Type safety**: Full Pydantic validation on all state data

#### Output Schema Builder

- **Dynamic Pydantic output models**: Generated from node output config
- **Simple output wrapping**: Single values wrapped in 'result' field
- **Object output support**: Multiple fields with proper typing
- **29 comprehensive tests**: All output patterns covered
- **Validation enforcement**: Ensures outputs match expected schema

---

### Phase 2: Core Execution (2026-01-25 to 2026-01-27)

#### Tool Registry with Lazy Loading

- **ToolRegistry class**: Lazy loading for efficient resource usage
- **Serper search integration**: Web search tool with API key configuration
- **Environment-based configuration**: Secure API key management
- **37 tests**: 22 registry tests + 15 Serper integration tests
- **Tool binding**: Automatic tool loading for LLM function calling

#### Google Gemini LLM Provider

- **Structured outputs**: Native support for Pydantic models
- **Automatic retry logic**: Clarified prompts on validation errors
- **Exponential backoff**: Graceful handling of rate limits
- **Configuration merging**: Node-level config overrides global settings
- **32 tests**: 19 provider tests + 13 Google-specific tests
- **Tool binding**: Full function calling support

#### Prompt Template Resolver

- **Variable placeholder resolution**: {variable} syntax from input mappings or state
- **Nested state access**: Support for {metadata.author} patterns
- **Automatic type conversion**: str() conversion for all value types
- **"Did you mean?" suggestions**: Edit distance ≤ 2 for typos
- **44 comprehensive tests**: All template patterns covered
- **Safe resolution**: Handles missing variables gracefully

#### Node Executor

- **Single node execution**: LLM calls with tools and type-enforced output
- **Input mapping resolution**: Automatic state-to-input transformation
- **Copy-on-write state updates**: Immutable pattern for safety
- **Tool loading and binding**: Automatic tool management
- **23 comprehensive tests**: All execution scenarios covered
- **Known issue documented**: Template resolver {state.field} syntax deferred to v0.2

#### LangGraph Builder

- **StateGraph construction**: Build from config with proper state management
- **Linear flow support**: v0.1 constraint (no control flow yet)
- **Direct Pydantic integration**: No TypedDict conversion needed
- **Closure-based node functions**: Proper scoping and state access
- **START/END handling**: LangGraph entry/exit points
- **18 tests**: 16 unit tests + 2 integration tests

#### Runtime Executor

- **Main entry point**: config → execution pipeline
- **6-phase pipeline**: load, validate, feature gate, build state, build graph, execute
- **Final state return**: Clean dict output
- **Comprehensive error handling**: Graceful failure modes
- **Execution timing and metrics**: Built-in observability
- **Validation-only mode**: `--validate` flag for config checking
- **27 tests**: 23 unit tests + 4 integration tests

---

### Phase 3: Polish & UX (2026-01-27 to 2026-01-28)

#### CLI Interface

- **`run` command**: Execute workflow from file with one command
- **`validate` command**: Validate config without running
- **Smart input parsing**: Type detection for str, int, bool, JSON
- **Color-coded terminal output**: Visual feedback on execution
- **Unicode fallback**: Windows console compatibility
- **39 tests**: 37 unit tests + 2 integration tests
- **Exit codes**: 0 (success), 1 (error) for scripting

#### Example Configurations

- **echo.yaml**: Minimal working example
- **article_writer.yaml**: Multi-step workflow with tools
- **nested_state.yaml**: Nested object demonstration
- **type_enforcement.yaml**: Complete type system showcase
- **README files**: Explanations for each example

#### User Documentation

- **QUICKSTART.md**: 5-minute tutorial for new users
- **CONFIG_REFERENCE.md**: User-friendly schema guide
- **Version availability table**: Clear feature timeline in README.md
- **TROUBLESHOOTING.md**: Common issues and solutions

#### Integration Tests

- **Real API testing**: Google Gemini and Serper integration
- **Error scenarios**: Invalid config, missing API key, LLM timeout, tool failure
- **19 integration tests**: 17 passed + 2 documented skips
- **Execution time**: 21.64s for full suite
- **~17 real API calls**: Gemini and Serper calls during tests
- **Cost tracking**: All API costs tracked and reported

**Bugs Fixed**:
1. Tool binding order - Tools must be bound BEFORE structured output
2. Model name - Updated gemini-1.5-flash → gemini-2.5-flash-lite

---

### Phase 4: Observability & Docker Deployment (2026-01-31 to 2026-02-02)

#### MLFlow Integration Foundation

- **mlflow>=2.9.0 dependency**: Observability infrastructure
- **ObservabilityConfig schema**: Configuration for tracking
- **MLFlowConfig schema**: MLFlow-specific settings
- **CostEstimator**: Pricing for 9 Gemini models
- **MLFlowTracker**: Workflow and node-level tracking
- **Graceful degradation**: Zero overhead when disabled
- **46 tests**: 37 unit tests + 9 integration tests
- **514 total tests**: All observability covered

#### MLFlow Instrumentation

- **Node-level tracking**: Nested runs for each node
- **Token tracking**: Extracted from LLM responses
- **Updated test mocks**: Tuple return (result, usage) support
- **492 unit tests**: All updated for new return format

#### Cost Tracking & Reporting

- **CLI cost reporting**: Multiple output formats (table, JSON, CSV)
- **Date range filters**: Query by time period
- **MLFlow experiment queries**: Extract metrics from runs
- **39 tests**: 29 unit tests + 5 CLI tests + 5 integration tests
- **577 total tests**: Full cost tracking coverage

#### Observability Documentation

- **OBSERVABILITY.md**: Comprehensive tracking guide
- **article_writer_mlflow.yaml**: Example with MLFlow enabled
- **Updated user docs**: CONFIG_REFERENCE.md, QUICKSTART.md, README.md
- **Bug fix**: Removed incorrect MLFlow warning from feature_gate.py

#### MLFlow 3.9 Comprehensive Migration

- **60% code reduction**: 484 → 396 lines
- **Automatic tracing**: mlflow.langchain.autolog() replaces manual tracking
- **Span/trace model**: Modern trace-based structure (vs nested runs)
- **Automatic token usage**: Built-in tracking with LangChain autolog
- **SQLite backend**: Default backend (replacing deprecated file://)
- **Async trace logging**: Production-ready async support
- **80 observability tests**: Complete migration coverage
- **645 total tests**: Final v0.1 test count

**Files Modified**:
- pyproject.toml - mlflow version update
- mlflow_tracker.py - Complete rewrite for 3.9
- schema.py - New MLFlowConfig fields
- executor.py - Async trace logging
- node_executor.py - Updated for autolog
- OBSERVABILITY.md - User migration guide
- CONFIG_REFERENCE.md - Updated examples
- README.md - Version updates
- +MLFLOW_39_USER_MIGRATION_GUIDE.md - Detailed migration docs

#### Docker Artifact Generator

- **Deployment package**: src/configurable_agents/deploy/
- **8 artifacts per workflow**: Complete deployment package
- **Multi-stage Dockerfile**: ~180-200MB target image
- **FastAPI server template**: 6.4KB production-ready server
- **24 tests**: 21 unit tests + 3 integration tests
- **601 total tests**: Docker deployment covered

#### FastAPI Server

- **Sync/async hybrid**: Proper async handling for LLM calls
- **Input validation**: Against workflow schema
- **35 tests**: 30 unit tests + 5 integration tests
- **636 total tests**: Server fully tested

#### CLI Deploy Command

- **One-command deployment**: `configurable-agents deploy workflow.yaml`
- **Port checking**: Socket-based availability check
- **Environment file handling**: Automatic .env management
- **23 tests**: 22 unit tests + 1 integration test
- **659 tests → 645 final**: Test suite optimization

---

### Technical Details

- **Total lines of code**: ~30,000 Python
- **Test coverage**: 645 tests (100% pass rate)
- **Development time**: 10 days (2026-01-24 → 2026-02-02)
- **Average task duration**: ~8 hours per task
- **Phase breakdown**:
  - Phase 1: 7 tasks (Foundation)
  - Phase 2: 6 tasks (Core Execution)
  - Phase 3: 4 tasks (Polish & UX)
  - Phase 4: 8 tasks (Observability & Docker)

---

### Dependencies Added

**Core dependencies:**
- `pydantic>=2.0` - Data validation and settings
- `pyyaml` - YAML config parsing
- `langgraph` - Workflow execution engine
- `langchain` - LLM abstraction layer
- `google-genai` - Google Gemini provider
- `pytest` - Testing framework

**Observability:**
- `mlflow>=3.9.0` - Experiment tracking and observability

**Deployment:**
- `fastapi` - API server framework
- `uvicorn` - ASGI server
- `docker` - Container deployment

**Utilities:**
- `python-dotenv` - Environment variable management

---

### Architecture Decision Records (ADRs)

**ADRs created during v0.1:**
- ADR-001 through ADR-018 (18 records)

**Key decisions:**
- Full Schema Day One (ADR-009) - Schema v1.0 from start
- LangGraph execution engine (ADR-002)
- Google Gemini provider (ADR-003)
- MLFlow 3.9 automatic tracing (ADR-018)

---

### Known Limitations

**Deferred to v1.0+**:
- **Conditional routing**: if/else logic based on state
- **Loops and retry**: Iteration with termination conditions
- **Parallel execution**: Concurrent node operations
- **Multi-LLM providers**: Only Google Gemini in v0.1
- **Agent registry**: Service discovery and lifecycle management
- **UI dashboard**: Web-based orchestration interface
- **Webhook integrations**: External triggers
- **Code execution sandbox**: Safe code execution
- **Long-term memory**: Persistent agent memory

**Known bugs** (documented, non-blocking):
- Nested objects in output schema not yet supported (2 tests skipped, documented)
- Template resolver {state.field} syntax deferred to v0.2

---

### Documentation

**Created during v0.1:**
- README.md - Project overview and quickstart
- QUICKSTART.md - 5-minute tutorial
- CONFIG_REFERENCE.md - User-friendly schema guide
- TROUBLESHOOTING.md - Common issues
- OBSERVABILITY.md - MLFlow setup and usage
- DEPLOYMENT.md - Docker deployment guide
- docs/implementation_logs/v0.1/ - 26 detailed implementation logs
- ADR-001 through ADR-018 - 18 architecture decision records

---

### Breaking Changes from v0.1

When migrating to v1.0+, note:

**Configuration:**
- `config.llm.provider` now accepts openai, anthropic, google, ollama (was only google)
- `edges[].routes[]` added for conditional routing
- `edges[].parallel` added for parallel execution
- `config.memory` added for persistent memory
- `config.webhooks` added for external triggers

**CLI:**
- New commands: chat, dashboard, agents, webhooks, report
- Observability commands: cost-report, profile-report

**Python API:**
- Storage backends now require factory pattern: create_storage_backend()
- LLM provider returns tuple (result, usage_metadata)

**Migration**: See [.planning/milestones/v1.0-ROADMAP.md](.planning/milestones/v1.0-ROADMAP.md) for detailed migration guide

---

## Version Planning

### [1.0.0] - Shipped 2026-02-04

**Focus**: Multi-agent orchestration platform

**Major additions:**
- Multi-LLM support (OpenAI, Anthropic, Google, Ollama)
- Advanced control flow (conditional routing, loops, parallel execution)
- Agent registry with heartbeat/TTL
- Gradio Chat UI and HTMX Dashboard
- Webhook integrations (WhatsApp, Telegram)
- Code execution sandbox
- Long-term memory backend
- 15 pre-built tools

---

## Notes

### About This Changelog

This historical changelog follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format:
- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

### Implementation Details

For comprehensive v0.1 implementation details, see:
- **[docs/implementation_logs/v0.1/](docs/implementation_logs/v0.1/)** - 26 detailed implementation logs
- **[tasks_old.md](tasks_old.md)** - Complete task history (T-001 through T-025)

### Versioning

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for added functionality (backwards-compatible)
- **PATCH** version for backwards-compatible bug fixes

**Note**: v0.1 was a development release. v1.0 is the first stable production release.

---

*Historical archive: 2026-02-06*
*This changelog preserves the complete v0.1 development record (2026-01-24 to 2026-02-02)*
*See [CHANGELOG.md](CHANGELOG.md) for current version changelog*
