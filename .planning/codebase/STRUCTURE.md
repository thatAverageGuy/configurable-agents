# Codebase Structure

**Analysis Date:** 2026-02-02

## Directory Layout

```
configurable-agents/
├── src/configurable_agents/          # Main package
│   ├── __init__.py                    # Package metadata (__version__)
│   ├── __main__.py                    # Entry point for python -m
│   ├── cli.py                         # Command-line interface (900+ lines)
│   ├── logging_config.py              # Logging setup (format, levels)
│   │
│   ├── config/                        # Configuration parsing & validation
│   │   ├── __init__.py                # Public API (parser, schema, types, validator)
│   │   ├── parser.py                  # YAML/JSON loading, ConfigLoader class
│   │   ├── schema.py                  # Pydantic models (WorkflowConfig, NodeConfig, etc.)
│   │   ├── types.py                   # Type string resolution (str → Python type)
│   │   └── validator.py               # Business logic validation (node refs, edges, etc.)
│   │
│   ├── core/                          # Workflow execution engine
│   │   ├── __init__.py                # Public API exports
│   │   ├── state_builder.py           # Generate Pydantic WorkflowState model
│   │   ├── graph_builder.py           # Build LangGraph from config
│   │   ├── node_executor.py           # Execute single node (LLM, tools, output)
│   │   ├── output_builder.py          # Validate node output against schema
│   │   └── template.py                # Resolve {field} in prompts
│   │
│   ├── runtime/                       # Execution orchestration
│   │   ├── __init__.py                # Public API (run_workflow, validate_workflow, exceptions)
│   │   ├── executor.py                # Main run/validate logic (orchestration)
│   │   └── feature_gate.py            # Runtime feature support validation
│   │
│   ├── llm/                           # LLM provider integration
│   │   ├── __init__.py                # Public API (create_llm, call_llm_structured)
│   │   ├── provider.py                # Factory, LLM call interface
│   │   └── google.py                  # Google Gemini provider (v0.1)
│   │
│   ├── tools/                         # Tool registry
│   │   ├── __init__.py                # Public API (get_tool, list_tools, register_tool)
│   │   ├── registry.py                # ToolRegistry class, lookup by name
│   │   └── serper.py                  # Web search via Serper API
│   │
│   ├── observability/                 # MLFlow tracking & cost reporting
│   │   ├── __init__.py                # Public API (MLFlowTracker, CostReporter, etc.)
│   │   ├── mlflow_tracker.py          # MLFlow integration (run logging)
│   │   ├── cost_estimator.py          # Token count → USD conversion
│   │   └── cost_reporter.py           # Query and export cost data
│   │
│   └── deploy/                        # Docker deployment
│       ├── __init__.py                # Public API (generate_deployment_artifacts)
│       ├── generator.py               # Artifact generation
│       └── templates/                 # Jinja2 templates for Dockerfile, server, etc.
│
├── tests/                             # Test suite (mirrors src structure)
│   ├── conftest.py                    # Pytest fixtures (mock config, etc.)
│   ├── config/                        # Config parsing & validation tests
│   │   ├── test_parser.py
│   │   ├── test_schema.py
│   │   ├── test_schema_integration.py
│   │   ├── test_types.py
│   │   └── test_validator.py
│   ├── core/                          # Core execution tests
│   │   ├── test_graph_builder.py
│   │   ├── test_node_executor.py
│   │   ├── test_output_builder.py
│   │   ├── test_state_builder.py
│   │   └── test_template.py
│   ├── deploy/                        # Deployment tests
│   │   ├── test_generator.py
│   │   ├── test_generator_integration.py
│   │   ├── test_server_integration.py
│   │   └── test_server_template.py
│   ├── integration/                   # Integration & end-to-end tests
│   │   ├── conftest.py                # Integration-specific fixtures
│   │   └── test_error_scenarios.py
│   └── __init__.py
│
├── examples/                          # Example workflows
│   ├── README.md                      # Example documentation
│   ├── article_writer.yaml            # Multi-node article generation
│   ├── article_writer_mlflow.yaml     # Same with MLFlow observability
│   ├── article_writer_README.md       # Article writer walkthrough
│   ├── echo.yaml                      # Simple echo node (testing)
│   ├── echo_README.md
│   ├── nested_state.yaml              # Nested object state
│   ├── nested_state_README.md
│   ├── simple_workflow.yaml           # Minimal single-node workflow
│   ├── type_enforcement.yaml          # Type validation examples
│   └── type_enforcement_README.md
│
├── docs/                              # Project documentation
│   ├── ARCHITECTURE.md                # System design (living document)
│   ├── SPEC.md                        # Technical specification
│   ├── TASKS.md                       # Work breakdown & status
│   ├── PROJECT_VISION.md              # Long-term vision
│   ├── adr/                           # Architecture Decision Records
│   │   ├── ADR-001-langgraph-execution-engine.md
│   │   ├── ADR-002-strict-typing-pydantic-schemas.md
│   │   ├── ADR-003-config-driven-architecture.md
│   │   ├── ADR-004-parse-time-validation.md
│   │   ├── ADR-005-single-llm-provider-v01.md
│   │   ├── ADR-006-linear-flows-only-v01.md
│   │   ├── ADR-007-tools-as-named-registry.md
│   │   ├── ADR-008-in-memory-state-only-v01.md
│   │   ├── ADR-009-full-schema-day-one.md
│   │   ├── ADR-010-python-free-export-target.md
│   │   ├── ADR-011-mlflow-observability.md
│   │   ├── ADR-012-docker-deployment-architecture.md
│   │   ├── ADR-013-environment-variable-handling.md
│   │   ├── ADR-014-three-tier-observability-strategy.md
│   │   ├── ADR-015-cli-interface-design.md
│   │   ├── ADR-017-testing-strategy-cost-management.md
│   │   └── ADR-018-mlflow-39-upgrade-genai-tracing.md
│   └── bugs/                          # Known issues
│       ├── BUG-001-docker-build-pypi-dependency.md
│       └── BUG-002-server-template-wrong-function.md
│
├── deploy/                            # Deployment outputs (generated)
│   ├── Dockerfile                     # Generated by deploy command
│   ├── main.py                        # FastAPI server template
│   ├── docker-compose.yml
│   ├── .env.example
│   └── [other artifacts]
│
├── streamlit_app.py                   # Web UI (interactive YAML editor)
├── pyproject.toml                     # Package config, dependencies, build
├── pytest.ini                         # Pytest configuration
├── setup.sh / setup.bat               # Dev environment setup scripts
├── CLAUDE.md                          # Project instructions
├── README.md                          # Project overview & quickstart
├── CHANGELOG.md                       # Version history
├── SETUP.md                           # Dev environment setup docs
├── SYSTEM_PROMPT.md                   # Prompt for AI-assisted config generation
└── .env                               # Local environment variables (not committed)
```

## Directory Purposes

**src/configurable_agents/config/:**
- Purpose: Load, parse, and validate workflow configurations
- Contains: YAML parsing, Pydantic schema models, type resolution, business logic validation
- Key files:
  - `schema.py`: Complete Pydantic model hierarchy for v0.1 workflows (500+ lines)
  - `parser.py`: ConfigLoader class using PyYAML
  - `types.py`: Type string parsing (e.g., "list[int]" → List[int])
  - `validator.py`: Graph connectivity, node references, edge validation
- Generated files: None (runtime, no code generation)

**src/configurable_agents/core/:**
- Purpose: Transform validated config into executable LangGraph and execute nodes
- Contains: State model generation, graph construction, node execution with LLM/tools
- Key files:
  - `state_builder.py`: Uses Pydantic.create_model() to generate WorkflowState dynamically
  - `graph_builder.py`: Constructs StateGraph, adds nodes/edges, compiles
  - `node_executor.py`: Core node execution (template resolve → LLM call → output validate)
  - `template.py`: {field} placeholder resolution in prompts
  - `output_builder.py`: Validates node output against schema
- Generated files: None (state models generated at runtime)

**src/configurable_agents/runtime/:**
- Purpose: Orchestrate full workflow lifecycle
- Contains: Entry points for execution (run_workflow, validate_workflow), feature gating
- Key files:
  - `executor.py`: Main orchestration logic with comprehensive error handling
  - `feature_gate.py`: Feature support validation by version
- No generated files

**src/configurable_agents/llm/:**
- Purpose: Abstract LLM provider calls with structured output
- Contains: LLM factory, call interface, provider implementations
- Key files:
  - `provider.py`: Factory (create_llm), call interface (call_llm_structured), config merging
  - `google.py`: Google Gemini provider implementation
- Provider pattern: Each provider module has constructor function, imported in provider.py
- Future providers (v0.2+): OpenAI, Anthropic, Ollama (structure ready)

**src/configurable_agents/tools/:**
- Purpose: Centralized registry for tools available to nodes
- Contains: Tool lookup, registration, built-in tools
- Key files:
  - `registry.py`: ToolRegistry singleton, get_tool(), list_tools()
  - `serper.py`: Web search implementation
- Tool pattern: Each tool is LangChain Tool subclass, registered in registry by name
- Future tools: File I/O, database query, API call, external service adapters

**src/configurable_agents/observability/:**
- Purpose: Cost tracking, metrics, and workflow profiling
- Contains: MLFlow integration, cost estimation, reporting
- Key files:
  - `mlflow_tracker.py`: MLFlow run creation, metric/param logging, active run management
  - `cost_estimator.py`: Token count → USD (by model/provider, updated pricing)
  - `cost_reporter.py`: MLFlow query API, filtering, aggregation, CSV/JSON export
- Data: Reads from MLFlow backend (file:// or remote); generates reports

**src/configurable_agents/deploy/:**
- Purpose: Generate production Docker containers
- Contains: Artifact generators (Dockerfile, server script)
- Key files:
  - `generator.py`: Main function generate_deployment_artifacts()
  - `templates/`: Jinja2 templates for Dockerfile, main.py, docker-compose
- Outputs: Generated files written to output_dir (default: ./deploy/)

**tests/:**
- Purpose: Unit, integration, and end-to-end tests
- Structure: Mirrors src/ structure (tests/config/ matches src/config/, etc.)
- Patterns:
  - `conftest.py`: Pytest fixtures (mock configs, temp files, API mocks)
  - `test_*_integration.py`: Tests requiring API keys or external services (marked with @pytest.mark.integration)
  - Individual modules test specific classes/functions
- Coverage: 645+ tests at v0.1 release
- Run: `pytest` (all), `pytest -m "not integration"` (skip API tests), `pytest -v` (verbose)

**docs/:**
- Purpose: Project documentation, decisions, specifications
- Contains: Architecture overview, ADRs, technical spec, work tracking
- Key files:
  - `ARCHITECTURE.md`: Living document, current system design
  - `SPEC.md`: Technical specification (features, constraints, examples)
  - `TASKS.md`: Work breakdown structure and status
  - `adr/`: Immutable decision records (never edited, only superseded)
- Convention: ADRs are append-only; create new ADR to supersede old ones

**examples/:**
- Purpose: Sample workflows demonstrating features
- Contains: YAML configs with README walkthroughs
- Pattern: Each example has .yaml config and corresponding _README.md with explanation
- Key examples:
  - `simple_workflow.yaml`: Minimal single-node workflow
  - `article_writer.yaml`: Multi-node workflow with input mapping
  - `nested_state.yaml`: Object state with nested schemas
  - `type_enforcement.yaml`: Type validation examples

## Key File Locations

**Entry Points:**
- `src/configurable_agents/cli.py:main()`: CLI entry point (installed via pyproject.toml entry point)
- `src/configurable_agents/__main__.py`: Python module entry point (`python -m configurable_agents`)
- `streamlit_app.py`: Web UI entry point (`streamlit run streamlit_app.py`)
- `src/configurable_agents/runtime/executor.py:run_workflow()`: Programmatic entry point

**Configuration:**
- `pyproject.toml`: Package metadata, dependencies, entry points, tool config
- `pytest.ini`: Pytest settings (testpaths, markers)
- `src/configurable_agents/logging_config.py`: Logging format/level setup
- `src/configurable_agents/config/schema.py`: Complete schema definition (Pydantic models)

**Core Logic:**
- `src/configurable_agents/config/parser.py`: YAML parsing (ConfigLoader class)
- `src/configurable_agents/config/validator.py`: Business logic validation
- `src/configurable_agents/core/graph_builder.py`: LangGraph construction
- `src/configurable_agents/core/node_executor.py`: Node execution (LLM + tools + output)
- `src/configurable_agents/runtime/executor.py`: Orchestration & error handling

**Testing:**
- `tests/conftest.py`: Shared fixtures
- `tests/config/test_*.py`: Config layer tests
- `tests/core/test_*.py`: Core execution tests
- `tests/deploy/test_*.py`: Deployment tests
- `tests/integration/`: End-to-end tests

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `graph_builder.py`)
- Test files: `test_<module>.py` (e.g., `test_graph_builder.py`)
- Config files: `<purpose>.py` or `<purpose>.yaml` (e.g., `pytest.ini`, `article_writer.yaml`)
- Templates: `<name>.jinja2` (in deploy/templates/)

**Directories:**
- Packages (with __init__.py): `snake_case/` (e.g., `core/`, `config/`)
- Data directories: Descriptive lowercase (e.g., `examples/`, `docs/`, `tests/`)
- Generated outputs: Specific names (e.g., `deploy/`, `.planning/`)

**Classes:**
- Python classes: `PascalCase` (e.g., `WorkflowConfig`, `GraphBuilderError`)
- Exceptions: Suffix with `Error` (e.g., `ConfigValidationError`, `NodeExecutionError`)
- Pydantic models: Match domain concept (e.g., `StateSchema`, `NodeConfig`, `EdgeConfig`)

**Functions:**
- Public API: `snake_case` (e.g., `run_workflow`, `build_state_model`, `create_llm`)
- Helpers: Prefix with `_` if internal (e.g., `_strip_state_prefix`, `_resolve_inputs`)
- Error handlers: Verb-based (e.g., `handle_error`, `wrap_exception`)

**Variables:**
- State: `state` or `state_dict` (dict representation)
- Models: `<domain>_model` (e.g., `state_model`, `output_model`)
- Configs: `<domain>_config` (e.g., `node_config`, `llm_config`, `global_config`)

## Where to Add New Code

**New Feature (within existing module):**
- Implementation: Add to appropriate `src/configurable_agents/<module>/` file
- Example: Adding prompt caching → add to `src/configurable_agents/core/node_executor.py`
- Tests: Add to corresponding `tests/<module>/test_*.py`

**New Provider (LLM or Tool):**
- LLM Provider:
  - File: `src/configurable_agents/llm/<provider>.py` (new file)
  - Pattern: Implement constructor function + import in `provider.py`
  - Tests: `tests/llm/test_<provider>.py` (new file)
- Tool:
  - File: `src/configurable_agents/tools/<tool>.py` (new file)
  - Pattern: Create LangChain Tool instance + register in `registry.py`
  - Tests: `tests/tools/test_<tool>.py` (new file)

**New Module (new layer):**
- Create: `src/configurable_agents/<module>/` directory with `__init__.py`
- Export public API in `__init__.py`
- Add tests: `tests/<module>/` directory with mirror structure
- Update: `src/configurable_agents/runtime/executor.py` if it's used in main flow
- Document: Add section to `docs/ARCHITECTURE.md`

**Utilities & Helpers:**
- Shared helpers across modules: `src/configurable_agents/utils/` (new module)
- Module-specific helpers: Keep in same file with `_` prefix, or `<module>/helpers.py`

**Configuration & Defaults:**
- Schema changes: Update `src/configurable_agents/config/schema.py` (Pydantic models)
- Validation rules: Add validators to schema models or `src/configurable_agents/config/validator.py`
- Type support: Add case to `src/configurable_agents/config/types.py:parse_type_string()`
- Pricing/cost data: Update `src/configurable_agents/observability/cost_estimator.py`

## Special Directories

**src/configurable_agents/deploy/templates/:**
- Purpose: Jinja2 templates for generated Docker artifacts
- Generated: Templates are static, outputs are dynamic
- Committed: Yes (templates are source)
- Content: Dockerfile, main.py server template, docker-compose.yml, .env.example

**.planning/codebase/:**
- Purpose: GSD codebase analysis (ARCHITECTURE.md, STRUCTURE.md, STACK.md, etc.)
- Generated: Yes (by gsd:map-codebase command)
- Committed: Yes (part of repo)
- Content: Markdown analysis documents

**mlflow runs/ artifacts:**
- Purpose: MLFlow tracking data
- Generated: Yes (created at runtime when workflows execute with observability)
- Committed: No (git-ignored)
- Location: `./mlruns/` (default) or custom path via env var

**tests/.pytest_cache/:**
- Purpose: Pytest test discovery cache
- Generated: Yes (by pytest at test discovery)
- Committed: No (git-ignored)
- Cleared: `pytest --cache-clear`

**docs/bugs/:**
- Purpose: Known issues tracking (like ADRs but for problems, not decisions)
- Generated: No
- Committed: Yes (living record of issues)
- Format: BUG-NNN-title.md with description, workaround, fix status

