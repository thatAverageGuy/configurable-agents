# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For detailed task-by-task implementation notes, see [implementation logs](docs/implementation_logs/).

---

## [Unreleased]

### Added

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
