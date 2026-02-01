# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For detailed task-by-task implementation notes, see [implementation logs](docs/implementation_logs/).

---

## [Unreleased]

### Added

**CLI Deploy Command** (T-024):
- One-command Docker deployment: `configurable-agents deploy workflow.yaml`
- Validates config → checks Docker → generates artifacts → builds image → runs container
- Rich terminal output with color-coded messages and Unicode symbols
- Port availability checking (API and MLFlow ports)
- Environment file handling (auto-detect .env, custom paths, skip option)
- Container name sanitization (lowercase, alphanumeric + dash/underscore)
- Generate-only mode (--generate flag) for artifact generation without Docker
- Comprehensive error handling with actionable suggestions
- 22 unit tests + 1 integration test - all passing
- Total: 66 CLI tests passing (44 existing + 22 new deploy tests)

**FastAPI Server with Input Validation & MLFlow** (T-023):
- Enhanced server.py.template with dynamic input validation using Pydantic
- Automatic Pydantic model generation from workflow state schema (`_build_input_model()`)
- Type-safe API with 422 validation errors for invalid inputs
- Conditional MLFlow integration (enabled via `MLFLOW_TRACKING_URI` environment variable)
- MLFlow tracking for both sync and async executions (params, metrics, execution time, errors)
- Graceful MLFlow error handling (failures don't crash server)
- WorkflowConfig object creation for schema access (while using dict for run_workflow)
- 35 new tests (30 unit + 5 integration) - all passing
- Total: 616 unit tests (100% pass rate)
- Template validation tests (no live server execution needed)

**Docker Artifact Generator** (T-022):
- Deployment artifact generation for Docker containers in `src/configurable_agents/deploy/`
- 7 template files for complete Docker deployment (Dockerfile, FastAPI server, docker-compose, etc.)
- Multi-stage Dockerfile with health check and MLFlow UI integration
- FastAPI server template with sync/async hybrid execution (timeout-based)
- Automatic example input generation from workflow state schema
- Template engine using Python's `string.Template` (zero dependencies)
- Configurable ports (API: 8000, MLFlow: 5000), sync timeout (30s default), container names
- Generated artifacts: Dockerfile (1.4KB), server.py (6.4KB), requirements.txt, docker-compose.yml, .env.example, README.md (5.9KB), .dockerignore, workflow.yaml
- Comprehensive README template with API reference, management commands, troubleshooting
- 24 new tests (21 unit + 3 integration) - all passing
- Total: 568 unit tests (100% pass rate)
- Implementation: `DeploymentArtifactGenerator` class with `generate_deployment_artifacts()` function

**Observability Documentation** (T-021):
- Comprehensive MLFlow documentation in `docs/OBSERVABILITY.md`
- Configuration reference added to `docs/CONFIG_REFERENCE.md` (~60 lines)
- Observability section added to `docs/QUICKSTART.md`
- Working example: `examples/article_writer_mlflow.yaml` demonstrating MLFlow tracking
- CLI cost reporting guide with practical examples
- Updated Gemini pricing table (9 models, January 2025 pricing)
- Fixed incorrect feature gate warning (MLFlow fully supported in v0.1)
- 6 files modified (4 docs, 1 source, 1 test)

**Cost Tracking & Reporting** (T-020):
- CLI cost reporting: `configurable-agents report costs` with multiple filters
- MLFlow cost query and aggregation utilities in `observability/cost_reporter.py`
- Date range filters: `--range today|last_7_days|last_30_days|custom`
- Custom date filtering with `--start-date` and `--end-date`
- Output formats: table (default), JSON, CSV with `--format` flag
- Export to file with `--output report.json` or `report.csv`
- Summary statistics: total cost, run count, average cost, model breakdown
- Detailed per-run breakdowns with node-level metrics and token counts
- Workflow and experiment filtering
- Fail-fast validation for missing MLFlow or corrupted data
- 39 new tests (29 unit + 5 CLI + 5 integration) - all passing

**MLFlow Node Instrumentation** (T-019):
- Automatic node-level tracking with token extraction from LangChain responses
- LLM provider now returns tuple `(result, usage_metadata)` with token counts
- Node executor wraps execution in `tracker.track_node()` for MLFlow logging
- Logs resolved prompts and LLM responses as artifacts per node
- Token usage tracked across retries for accurate cost calculation
- Zero overhead when MLFlow disabled (graceful degradation maintained)
- All 492 unit tests passing (fixed 15 observability test mocking errors)
- Updated to 544 tests after T-020 (+39 new tests, +13 integration tests)

**MLFlow Observability Foundation** (T-018):
- MLFlow integration for workflow execution tracking and cost monitoring
- CostEstimator with pricing for 9 Gemini models (latest January 2025 pricing)
- MLFlowTracker for workflow-level and node-level metrics
- Automatic token counting and cost calculation ($USD with 6-decimal precision)
- Graceful degradation when MLFlow unavailable (zero performance overhead)
- 46 new tests (37 unit + 9 integration) - all passing
- Support for local file storage and remote backends (PostgreSQL, S3, Databricks)
- Artifact logging for inputs, outputs, prompts, and responses
- Windows-compatible file:// URI handling

**Other Improvements**:
- Documentation structure optimization with implementation logs
- CONTEXT.md for quick LLM session resumption
- Organized implementation logs by phase (19 comprehensive task records)

### Changed
- Updated ObservabilityMLFlowConfig schema to match SPEC.md (added tracking_uri, experiment_name, run_name, log_artifacts)
- Simplified CHANGELOG.md to standard format (detailed notes moved to implementation logs)
- Archived project status tracking (now in CONTEXT.md and TASKS.md)

### Removed
- DISCUSSION.md (superseded by CONTEXT.md and implementation logs)

---

## [0.1.0-dev] - 2026-01-28

### Added

**Integration Testing & Quality** (T-017):
- 19 integration tests with real API calls (6 workflow + 13 error scenarios)
- Cost tracking for LLM API usage ($0.47 for full suite)
- Fixed 2 critical bugs: tool binding order and default Gemini model
- Total: 468 tests passing (449 unit + 19 integration)

**Complete User Documentation** (T-016):
- QUICKSTART.md - 5-minute beginner tutorial
- CONFIG_REFERENCE.md - User-friendly config reference
- TROUBLESHOOTING.md - Common issues and solutions
- 16 Architecture Decision Records with complete rationale

**Working Example Workflows** (T-015):
- 4 comprehensive examples: echo, article_writer, nested_state, type_enforcement
- Progressive complexity learning path (beginner → advanced)
- Individual README files for each example
- All examples validated and working

**Command-Line Interface** (T-014):
- `run` command for executing workflows from terminal
- `validate` command for config validation
- Smart input parsing with type detection (str, int, bool, JSON)
- Pretty color-coded output with Unicode fallback for Windows
- Comprehensive error handling with helpful messages
- Two entry points: `configurable-agents` script and `python -m configurable_agents`

**End-to-End Workflow Execution** (T-013):
- Complete workflow execution pipeline (load → parse → validate → gate → build → execute)
- Execute workflows from YAML/JSON files
- 6 exception types for granular error handling
- Verbose logging option for debugging
- Validation-only mode for pre-flight checks

**LangGraph Execution Engine** (T-012):
- Build compiled LangGraph StateGraph from validated configs
- Closure-based node function wrapping
- Direct Pydantic BaseModel integration (no TypedDict conversion)
- START/END entry/exit point handling

**Node Execution** (T-011):
- Integrates LLM, tools, prompts, and output schemas
- Copy-on-write state updates (immutable pattern)
- Input mapping resolution from state
- Comprehensive error handling with node_id context

**Prompt Template Resolution** (T-010):
- Variable resolution from inputs and state
- Nested state access ({metadata.author}, 3+ levels deep)
- Type conversion (int, bool → string)
- "Did you mean?" suggestions for typos (edit distance ≤ 2)

**Google Gemini LLM Integration** (T-009):
- LLM provider factory pattern
- Structured output calling with Pydantic schema binding
- Automatic retry on validation failures and rate limits
- Configuration merging (node overrides global)
- Multiple Gemini models supported

**Tool Registry & Web Search** (T-008):
- Factory-based lazy loading tool registry
- Serper web search tool integration
- LangChain BaseTool integration
- API key validation from environment

**Dynamic Schema Builders** (T-006, T-007):
- State models: Dynamic Pydantic BaseModel from StateSchema configs
- Output models: Type-enforced LLM responses with Pydantic validation
- Support for all type system types (basic, collections, nested objects)
- Required/optional fields with default values

**Runtime Feature Gating** (T-004.5):
- Hard blocks for v0.2+ features (conditional routing)
- Soft blocks for v0.3+ features (optimization, MLFlow)
- Helpful error messages with version timelines and workarounds
- Feature support query API

**Comprehensive Config Validation** (T-004):
- Cross-reference validation (node IDs, state fields, output types)
- Graph structure validation (connectivity, reachability)
- Linear flow enforcement (no cycles, no conditional routing)
- "Did you mean?" suggestions for typos
- 8 validation stages with fail-fast error handling

**Type System & Schema** (T-003, T-005):
- Complete type system: str, int, float, bool, list, dict, nested objects
- 13 Pydantic models for Schema v1.0
- Full Schema Day One (supports features through v0.3)
- Type validation, field validation, cross-field validation

**Config Parser** (T-002):
- YAML parsing (.yaml, .yml)
- JSON parsing (.json)
- Auto-format detection from extension
- Comprehensive error handling

**Project Foundation** (T-001):
- Complete package structure (`src/configurable_agents/`)
- Development environment setup
- pytest configuration and test infrastructure
- Logging configuration

### Fixed

- Tool binding order bug in LLM provider (tools now bound before structured output)
- Incorrect default Gemini model (updated to `gemini-2.0-flash-lite`)

### Technical Details

- **Tests**: 468 total (449 unit + 19 integration)
- **Test Cost**: ~$0.50 per integration run
- **Architecture Decision Records**: 16 ADRs
- **Schema Version**: 1.0 (stable, future-proof)
- **Python Version**: 3.10+
- **LLM Provider**: Google Gemini
- **Execution Engine**: LangGraph
- **Tools**: Serper web search

For detailed implementation notes, see:
- [Phase 1 Implementation Logs](docs/implementation_logs/phase_1_foundation/) - Foundation (8 tasks)
- [Phase 2 Implementation Logs](docs/implementation_logs/phase_2_core_execution/) - Core Execution (6 tasks)
- [Phase 3 Implementation Logs](docs/implementation_logs/phase_3_polish_ux/) - Polish & UX (4 tasks)

---

## [0.1.0-initial] - 2026-01-24

### Added

- Project setup with complete package structure (T-001)
- YAML/JSON config parser with error handling (T-002)
- Complete Pydantic schema for Schema v1.0 (T-003)

### Technical Details

- **Tests**: 124 passing
- Full Schema Day One design (ADR-009)

---

## Version Planning

### [0.2.0] - Q2 2026 (Planned)

**Theme**: Intelligence

- Conditional routing (if/else based on state)
- Loops and retry logic
- Multi-LLM support (OpenAI, Anthropic, Ollama)
- State persistence and workflow resume
- Config composition (import/extend)

### [0.3.0] - Q3 2026 (Planned)

**Theme**: Optimization

- DSPy prompt optimization (automatic)
- Quality metrics and evaluation
- Parallel node execution
- OpenTelemetry integration

### [0.4.0] - Q4 2026 (Planned)

**Theme**: Ecosystem

- Visual workflow editor
- One-click cloud deployments
- Prometheus + Grafana monitoring
- Plugin system
- Config marketplace

---

## Notes

### About This Changelog

This changelog follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format:
- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

### Implementation Details

For comprehensive task-by-task implementation details, see:
- **[Implementation Logs](docs/implementation_logs/)** - Detailed task records (150-500 lines each)
- **[TASKS.md](docs/TASKS.md)** - Work breakdown and current status
- **[CONTEXT.md](docs/CONTEXT.md)** - Current state and next action
- **[Architecture Decision Records](docs/adr/)** - Design rationale

### Versioning

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for added functionality (backwards-compatible)
- **PATCH** version for backwards-compatible bug fixes

Current version: **0.1.0-dev** (development, pre-release)

---

*For the latest updates, see [docs/CONTEXT.md](docs/CONTEXT.md)*
*For development progress, see [docs/TASKS.md](docs/TASKS.md)*
