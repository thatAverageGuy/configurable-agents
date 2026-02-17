# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For detailed task-by-task implementation notes, see [implementation logs](docs/development/implementation_logs/).

---

## [Unreleased]

### WARNING: PROJECT STATE IS BROKEN

After introducing an autonomous agent system post-v1.0, the codebase and documentation
became inconsistent and out of sync. Cleanup tasks are in progress to restore
the project to a verifiable state.

### Removed

**CL-004: Documentation truth audit and dead code removal** (2026-02-17)
- Removed `orchestrator/` module entirely (src, deploy, tests, examples) — functionality was migrated to deployments routes during UI-REDESIGN
- Removed `examples/multi_agent_collaboration/orchestrator_config.py` and orchestrator references from multi-agent examples
- Removed stale optimization/A/B testing references from 7 user-facing docs (QUICKSTART, TROUBLESHOOTING, PERFORMANCE_OPTIMIZATION, PRODUCTION_DEPLOYMENT, OBSERVABILITY, ADVANCED_TOPICS, README)
- Removed "MLFlow Optimization Issues" section from TROUBLESHOOTING.md
- Removed A/B Testing and Quality Gates sections from PERFORMANCE_OPTIMIZATION.md
- Removed optimization schema sections from SPEC.md
- Removed orchestrator and optimization route sections from UI_ARCHITECTURE.md
- Replaced "Optimization System" section in ARCHITECTURE.md with REMOVED notice

### Fixed

**CL-004: Documentation alignment fixes** (2026-02-17)
- Fixed `workflow-registry list` → `deployments list` in root README.md
- Fixed `agent-registry list` → `deployments list` in QUICKSTART.md
- Fixed CLI commands in PERFORMANCE_OPTIMIZATION.md (`observability profile-report` → `profile-report`)
- Fixed agent registry → dashboard references in PRODUCTION_DEPLOYMENT.md
- Fixed `configurable-agents registry` → `configurable-agents dashboard` in PRODUCTION_DEPLOYMENT.md
- Fixed orchestration references in ARCHITECTURE.md to use deployment terminology
- Updated route paths, model names, and table names in UI_ARCHITECTURE.md to match post-UI-REDESIGN state
- Fixed `test_load_complete_yaml_config` integration test that was asserting on removed `config.optimization`
- Fixed invalid `orchestration:` config block in multi_agent_collaboration.yaml (replaced with valid `execution:` block)

### Fixed

**BF-009: Documentation, CLI verification report, and cleanup** (2026-02-14)
- Removed `--enable-profiling` flag from `run` command — flag was defined but never passed to `run_workflow()`, making it non-functional
- Removed backwards-compatibility comment that referenced the vestigial flag
- Removed `TestEnableProfilingFlag` test class from test suite
- Updated CLI guide to remove `--enable-profiling` references
- Created bug report documenting redundant `node_*_duration_ms` metrics (fix deferred to ADR-018)
- Profiling is always enabled via MLflow 3.9 `autolog()` — no flag needed

**Template alignment with UI-REDESIGN** (2026-02-17)
- Fixed all Jinja2 HTML templates that were missed during UI-REDESIGN Phase 4
- `deployments_table.html`: Rewrote to use `deployments` variable and `Deployment` model fields (`deployment_id`, `deployment_name`, `deployment_metadata`)
- `executions_table.html`: Fixed `{% if workflows %}` → `{% if executions %}` variable mismatch
- `execution_detail.html`: Renamed from `workflow_detail.html`, all `workflow.*` → `execution.*`
- `dashboard.html`: Updated quick links from old `/workflows`/`/agents` routes to `/executions`/`/deployments`
- `status_panel.html`: Fixed variable names (`active_workflows` → `active_executions`, `agent_healthy` → `deployment_healthy`)
- Removed dead `orchestrator.html` template (no route references it)
- Removed dead Optimization nav link from `base.html`
- Removed 6 stale optimization tests from E2E and integration test suites (module was removed in CL-003)
- Updated all test assertions to match new terminology (`agent_metadata` → `deployment_metadata`, workflow→execution, agent→deployment)

### Changed

**UI Redesign - Complete Implementation** (2026-02-13)

A comprehensive rename and restructuring to align terminology with the new 4-page UI design (Chat UI, Executions, Deployments, MLflow). All 6 phases implemented.

**Phase 1: Storage Layer**
- `WorkflowRunRecord` → `Execution` (table: `workflow_runs` → `executions`)
- `AgentRecord` → `Deployment` (table: `agents` → `deployments`)
- `ExecutionStateRecord` → `ExecutionState` (field: `run_id` → `execution_id`)
- `OrchestratorRecord` → REMOVED (absorbed into deployments)
- Added `Execution.deployment_id` FK to link executions to deployments
- Added `Deployment.workflow_name` to track which workflow a deployment runs
- `AbstractWorkflowRunRepository` → `AbstractExecutionRepository`
- `AgentRegistryRepository` → `DeploymentRepository`
- `OrchestratorRepository` → REMOVED
- Storage factory return tuple: 8 values → 7 values (removed orchestrator)

**Phase 2: CLI Updates**
- Command renamed: `workflow-registry` → `deployments`
- Functions renamed: `cmd_workflow_registry_*` → `cmd_deployments_*`
- Import renamed: `WorkflowRegistryServer` → `DeploymentRegistryServer`
- Default DB path: `workflows.db` → `configurable_agents.db`

**Phase 3: Registry Module**
- `AgentRegistryServer` → `DeploymentRegistryServer`
- `AgentRegistryClient` → `DeploymentClient`
- Pydantic models renamed: `AgentRegistrationRequest` → `DeploymentRegistrationRequest`
- Routes: `/agents/*` → `/deployments/*`
- Backward-compatible aliases provided for all renamed classes

**Phase 4: Dashboard/UI**
- Routes: `/workflows/*` → `/executions/*`
- Routes: `/agents/*` → `/deployments/*`
- Orchestrator routes (`/orchestrator/*`) merged into `/deployments/*`
- Files renamed: `workflows.py` → `executions.py`, `agents.py` → `deployments.py`
- Files deleted: `orchestrator.py` (functionality merged)
- App state: `workflow_repo` → `execution_repo`, `agent_registry_repo` → `deployment_repo`

**Phase 5: Tests**
- Updated 10 test files with new model/class names
- Renamed `test_agent_registry_repository.py` → `test_deployment_repository.py`
- All storage tuple unpacking updated (8 → 7 values)

**Phase 6: Documentation**
- Created ADR for terminology changes
- Updated architecture documentation
- Updated implementation plan with completion status

**Files Modified**: ~45 files across all phases

**BREAKING CHANGES**:
- Requires fresh database (tables renamed: `workflow_runs` → `executions`, `agents` → `deployments`)
- API routes changed: `/workflows` → `/executions`, `/agents` → `/deployments`, `/orchestrator/*` removed
- CLI command changed: `workflow-registry` → `deployments`
- Storage factory returns 7 values instead of 8 (removed orchestrator repository)
- All class imports changed (backward-compatible aliases provided in `__init__.py` files)

### Fixed

**CL-003: Fix VF-001–VF-006, remove optimization module, rename workflow registry** (2026-02-10)

- **VF-001**: Fixed `--verbose` producing no DEBUG output — added `setup_logging()` call in `main()` so all commands get proper logging handlers
- **VF-002**: Removed dead `--enable-profiling` code — env var `CONFIGURABLE_AGENTS_PROFILING` was set but never read; removed `mlflow.active_run()` metric logging in `node_executor.py` (always None under trace paradigm)
- **VF-003**: Fixed `--no-mlflow` deploy artifacts — Dockerfile now exposes only port 8000 (not 8000+5000), docker-compose.yml omits MLflow port mapping and volume mount when MLflow disabled
- **VF-004**: Rewrote all observability reporting commands (`cost-report`, `profile-report`, `observability status`, `report costs`) from legacy `search_runs()` to `search_traces()` + span extraction, matching MLflow 3.9 GenAI paradigm
- **VF-005**: Fixed `CostReporter` experiment lookup — added `mlflow.set_tracking_uri()` in `__init__` and rewrote `get_cost_entries()` to use trace-based queries
- **VF-006**: Fixed parent commands (`optimization`, `workflow-registry`) crashing without subcommand — added `hasattr(args, 'func')` check in `main()`

### Removed

**Optimization module removed** (2026-02-10)
- Removed entire `optimization/` package (`evaluator.py`, `ab_test.py`, `gates.py`, `__init__.py`)
- Removed CLI commands: `optimization evaluate`, `optimization apply-optimized`, `optimization ab-test`
- Removed dashboard route (`routes/optimization.py`) and templates (`optimization.html`, `experiments.html`)
- Removed all optimization tests (`tests/optimization/`, `tests/cli/test_optimization_commands.py`)
- Moved `QualityGate` system from `optimization/gates.py` to `runtime/gates.py` (used by executor, not an optimization concern)
- Optimization to be redesigned later with MLflow 3.9 GenAI evaluation + DSPy

### Changed

**Agent Registry renamed to Workflow Registry** (2026-02-10)
- CLI command renamed from `agent-registry` to `workflow-registry`
- Added `WorkflowRegistryServer` and `WorkflowRegistryClient` aliases in `registry/__init__.py`
- CLI help text updated from "agent" to "workflow" terminology
- Internal class names (`AgentRegistryServer`, `AgentRecord`, etc.) preserved for backward compatibility

**BF-007: Fix webhooks command — wrong router import** (2026-02-09)
- Fixed `from configurable_agents.webhooks import router` importing the module instead of the `APIRouter` instance
- Changed to `from configurable_agents.webhooks.router import router as webhook_router` in `cli.py`
- Webhooks server now starts correctly, `/` and `/webhooks/health` respond

**BF-008: Fix Docker deploy — build failure and port mismatch** (2026-02-09)
- **BF-008a**: Fixed Docker build failure caused by invalid `pyproject.toml` script entries (`docs:build`, `docs:serve`, `docs:clean` are shell commands, not Python entry points) — rewrote `_copy_pyproject_toml()` in `deploy/generator.py` to filter invalid entries
- **BF-008b**: Fixed container port mismatch — `server.py.template` used `port=${api_port}` but Dockerfile exposes 8000 internally — hardcoded to `port=8000`, updated `docker-compose.yml.template` port mappings to `${api_port}:8000` and `${mlflow_port}:5000`
- Updated test assertions in `test_generator_integration.py` and `test_server_template.py` to match new fixed-port behavior
- Full Docker deploy verified: container builds, starts, `/health`, `/docs`, `/schema`, `/run` all work

### Added

**CLI Reference Guide** (2026-02-09)
- Created `docs/user/cli_guide.md` — comprehensive reference for all 20 CLI commands
- Covers all flags, defaults, examples, port map, and verification status
- Systematic manual testing of all CLI commands documented

### Changed

**BF-006: Migrate ChatLiteLLM to langchain-litellm** (2026-02-09)
- Migrated `ChatLiteLLM` import from deprecated `langchain-community` to standalone `langchain-litellm` package (v0.4.0)
- Updated import paths in `litellm_provider.py` and `provider.py`
- Added `langchain-litellm>=0.2.0` to project dependencies
- Updated 11 `@patch()` mock paths in test files
- Fixed 4 pre-existing test failures: updated mlflow config default assertion and `log_workflow_summary` test expectations to match `log_feedback` rewrite

### Fixed

**BF-005: Fix pre-existing test failures** (2026-02-08)
- Fixed 22 test failures across 5 test files — all 69 tests in affected modules now pass
- Fixed dict-vs-Pydantic assertions in `test_node_executor.py`, `test_node_executor_metrics.py`, `test_integration.py` (sandbox) — `execute_node()` returns partial dict, not full Pydantic model
- Fixed deploy artifact count assertions in `test_generator.py`, `test_generator_integration.py` — generator now produces 10 artifacts (added `src/` and `pyproject.toml`)
- Fixed Dockerfile port assertions — template uses fixed internal ports (8000/5000), not user-configured ports
- Fixed `st_size > 0` check for directory artifacts on Windows

### Changed

**MLflow storage defaults: mlruns → sqlite** (2026-02-08)
- Changed default `tracking_uri` from `file://./mlruns` to `sqlite:///mlflow.db` across all code and templates (12 files)
- Updated deploy templates: Dockerfile, docker-compose, .dockerignore, README
- Updated user-facing docs: OBSERVABILITY.md, DEPLOYMENT.md
- MLflow 3.9 uses SQLite by default; `file://./mlruns` still works for backward compatibility
- Updated `mlflow>=2.9.0` requirement to `mlflow>=3.9.0` in deploy generator

### Fixed

**BF-004: Fix MLFlow cost summary and GenAI view integration** (2026-02-08)
- Fixed `search_traces()` call using wrong location format (`"mlflow-experiment:{id}"` → raw experiment ID) and missing `return_type="list"` (was returning DataFrame, causing `KeyError: 0`)
- Fixed model name attribution for Gemini/Google spans — added fallback chain to extract model from `invocation_params.model` and `metadata.ls_model_name` when `ai.model.name` is absent
- Fixed token key mismatch — Gemini uses `input_tokens`/`output_tokens` while code expected `prompt_tokens`/`completion_tokens`, now handles both
- Added per-span `try/except ValueError` on `estimate_cost()` so unknown models default to cost 0 instead of aborting entire summary
- Rewrote `log_workflow_summary()` to use `mlflow.log_feedback()` (trace-level assessments) instead of `mlflow.log_metrics()`/`mlflow.log_dict()` (run-level), making cost data visible in MLflow GenAI experiment view
- Added `mlflow.flush_trace_async_logging()` in executor before cost query to prevent race condition
- Verified: Config 02 and 12 run clean, assessments stored on traces (`cost_usd`, `total_tokens`, `cost_breakdown`)

**BF-001: Fix storage backend tuple unpacking** (2026-02-08)
- Fixed `create_storage_backend()` callers that unpacked wrong number of values (function returns 8, callers expected 3-6)
- Fixed 8 call sites across 5 files: `runtime/executor.py`, `cli.py` (×2), `tests/registry/test_ttl_expiry.py`, `tests/registry/test_server.py`, `tests/runtime/test_executor_storage.py` (×3)
- Resolves `too many values to unpack (expected 6)` crash on every workflow run with storage enabled
- Verified with test configs 09 and 12 (end-to-end execution) and 47 previously-failing unit tests now pass

**BF-002: Implement tool execution agent loop** (2026-02-08)
- Added `_execute_tool_loop()` in `provider.py` — manual agent loop: invoke LLM → detect tool calls → execute tools → feed results back → repeat
- Changed `call_llm_structured()` to two-phase approach: Phase 1 runs tool loop (enriches prompt with tool results), Phase 2 extracts structured output
- Previously tools were bound via `bind_tools()` but `with_structured_output()` was applied immediately, causing the LLM to skip tool calls entirely
- Updated `test_call_with_tools` mock setup to match new two-phase flow
- Verified: config 12 `web_search` tool now returns real search results instead of echoing the query
- Confirmed BF-003 (memory persistence) is a separate issue — storage initializes but memory load/save not wired into prompts

**BF-003: Fix memory persistence across runs** (2026-02-08)
- Fixed scope-aware namespace construction: agent scope now uses wildcard `*:*` for workflow/node instead of per-run UUIDs, enabling cross-run memory persistence
- Fixed `AgentMemory` truthiness bug: `if agent_memory:` evaluated to False due to `__len__` returning 0 on empty memory, skipping all memory read/write code — changed to `if agent_memory is not None:`
- Added `memory` field to `GlobalConfig` schema so `config.memory:` in YAML is actually parsed
- Added auto-extraction of facts from LLM responses via lightweight extraction call
- Added `max_entries` limit on memory injection into prompts to prevent context bloat
- Fixed config 09 field names to match schema (`default_scope` instead of `scope`)
- Verified end-to-end: Run 1 stores "name=Alice", Run 2 recalls "Your name is Alice"

### Added

**CL-002: Documentation Index and Dead Link Cleanup** (In Progress - 2026-02-06)
- Created `docs/README.md` as comprehensive documentation index
- Updated all references to non-existent `.planning/` directory
- Updated doc paths to correct locations (docs/development/adr/, etc.)
- Updated CHANGELOG.md to remove dead references
- Updated README.md with documentation index link
- Updated CLAUDE.md with documentation structure information
- Updated docs/development/TASKS.md to remove dead references

**CL-001: Documentation Reorganization** ✅ (2026-02-06)
- Created `docs/user/` for user-facing documentation
- Moved internal docs to `docs/development/` (PROJECT_VISION, ARCHITECTURE, SPEC)
- Created `docs/development/session_context/` for archived contexts
- Updated CLAUDE.md with permanent project instructions
- Rewrote CONTEXT.md with streamlined structure
- Updated README.md with new doc paths
- Created implementation log for CL-001

### Changed
- Documentation reorganized into `docs/user/` and `docs/development/`
- All doc paths updated to reflect new structure

### Removed
- `.planning/` directory references (directory no longer exists)
- Various documentation files from autonomous agent cleanup

---

## [1.0.0] - 2026-02-04

### 🎉 Major Release: Production-Ready Multi-Agent Orchestration Platform

**v1.0 Foundation** - 4 phases, 19 plans, 27 requirements, 1,000+ tests (98%+ pass rate)

Transformed from a simple linear workflow runner (v0.1) into a full-featured local-first agent orchestration platform with multi-LLM support, advanced control flow, complete observability, and zero cloud lock-in.

---

**NOTE**: Full v1.0 details exist but project state is currently broken due to post-v1.0
autonomous agent issues. Cleanup is in progress to restore verifiable state.

---

## Version Planning

### [1.1.0] - TBD (Planning Deferred)

**Focus**: Cleanup and verification of current state before planning new features.

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

### Versioning

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for added functionality (backwards-compatible)
- **PATCH** version for backwards-compatible bug fixes

Current version: **1.0.0** (production release, but state verification needed)

---

*For the latest project state, see [CONTEXT.md](CONTEXT.md)*
*For development progress, see [docs/development/TASKS.md](docs/development/TASKS.md)*
*For documentation index, see [docs/README.md](docs/README.md)*
