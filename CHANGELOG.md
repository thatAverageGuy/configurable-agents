# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For detailed task-by-task implementation notes, see [implementation logs](docs/development/implementation_logs/).

---

## [Unreleased] — v1.1 Hardening & Usability

### Added (2026-03-26)

**T-015: Memory fact extraction — opt-in via `extract_facts` flag**
- Added `extract_facts: bool = False` to `MemoryConfig` — extraction is now opt-in (was always-on, doubling LLM cost per memory-enabled node).
- Added `extraction_model: Optional[str] = None` — allows specifying a cheaper model (e.g. `gpt-4o-mini`) for extraction when enabled, independent of the node's main LLM.
- Added `_build_extraction_llm()` helper in `node_executor.py` — infers provider from model name prefix (`gpt`→openai, `claude`→anthropic, `gemini`→google).
- When `extract_facts=False`: logs DEBUG, skips extraction entirely. When `extract_facts=True`: logs INFO with model used and fact count.
- 13 unit tests in `tests/core/test_memory_extraction_opt_in.py` — all pass.
- **Migration**: existing `memory.enabled: true` configs default to `extract_facts: false` — add `extract_facts: true` explicitly to restore previous behaviour.

### Fixed (2026-03-26)

**BF-010 (Pydantic 2.12 field name rejection)**
- Pydantic 2.12 rejects field names with leading double underscores. `__loop_counter_{node_id}` renamed to `lc_{node_id}` throughout (`control_flow.py`, `test_state_builder.py`, `test_control_flow.py`, `test_graph_builder.py`).

**T-014 runtime override — scope guard bug**
- `_apply_runtime_overrides()` incorrectly created `MemoryConfig()` for nodes with `memory=None` when `scope=workflow` or `scope=agent`. Fixed to only inject `MemoryConfig(enabled=False)` for `scope=none`; workflow/agent scope skips nodes with no existing memory config.

**BF-012 mock path in `test_node_executor_metrics.py`**
- `@patch("configurable_agents.observability.cost_estimator.CostEstimator")` → `@patch("configurable_agents.core.node_executor.CostEstimator")` — patches the symbol at import site, not definition site.

**MLflow API drift — `test_cost_reporter.py` and `test_multi_provider_tracker.py`**
- `cost_reporter.py` was migrated from MLflow runs API to traces API (3.9→3.10 change). Tests still used old API (`_run_to_cost_entry`, `client.search_runs`, `mlflow.get_experiment_by_name`, SQL filter strings).
- Rewrote 11 test methods in `TestCostReporter`: replaced `make_mock_run()` with `make_mock_trace()` (GenAI trace structure), updated mocks to `client.get_experiment_by_name` + `mlflow.search_traces`, updated filter string key (`attributes.start_time` → `trace.timestamp_ms`), rewrote status filter tests (now Python-level, not SQL), removed invalid-status ValueError test (no such validation in current impl).
- Fixed `test_generate_cost_report_success` in `test_multi_provider_tracker.py`: mock `client.get_experiment_by_name` (not `mlflow.get_experiment_by_name`), use `mlflow.search_traces` returning trace objects with `span.attributes["mlflow.chat.tokenUsage"]`.

**Dependency pinning — supply chain hardening**
- All `>=` version constraints in `pyproject.toml` replaced with exact `==` pins matching installed versions from `uv.lock`.
- `litellm` pinned to `==1.80.0` (last safe version before the quarantined releases).
- `requires-python` narrowed from `>=3.10` to `>=3.12,<3.13`.
- Removed invalid `docs:build`, `docs:serve`, `docs:clean` script entries (`:` not valid in script names).

### Added (2026-03-24)

**T-014: Runtime memory override — per-invocation `--memory-scope` CLI flag**
- Added `RuntimeOverrides` and `MemoryRuntimeOverride` Pydantic models to `config/schema.py`.
- Added `_apply_runtime_overrides(config, overrides)` in `runtime/executor.py` — mutates node-level and workflow-level `MemoryConfig` in-place, leaving the YAML file untouched.
- `scope: none` disables memory on all nodes (and injects `MemoryConfig(enabled=False)` on nodes that had none). `scope: workflow` / `scope: agent` sets `default_scope` without touching `enabled`.
- `run_workflow()` and `run_workflow_async()` now accept `runtime_overrides: Optional[Dict[str, Any]]` — validated and applied after config parse, before execution.
- Overrides are persisted to the `executions.runtime_overrides` (TEXT, nullable) column for auditability.
- `cli.py`: added `--memory-scope {none,workflow,agent}` flag to the `run` command — shown in `--help` with usage guidance.
- `webhooks/router.py`: generic webhook payload `"runtime": {...}` is extracted and passed through to `run_workflow_async()`.
- `storage/factory.py`: added `_apply_column_migrations()` — runs `ALTER TABLE executions ADD COLUMN runtime_overrides TEXT` on startup for existing databases (safe no-op if column already exists).
- Unit tests: 13 tests covering `_apply_runtime_overrides` and `RuntimeOverrides` validation in `tests/runtime/test_runtime_overrides.py`.
- Integration and live tests blocked pending `litellm` quarantine resolution.

### Fixed (2026-03-24)

**BF-013: Route condition failure logging**
- Root cause: `ControlFlowError` raised during condition evaluation was silently caught with `continue` — no indication that a condition was skipped. Broken conditions appeared to "work" by silently taking the default route.
- Fix: Added `logger.warning(...)` on `ControlFlowError` — logs condition text, error message, and available state field names. Added `logger.debug(...)` when the default route is taken — logs target and number of conditions evaluated.
- No behavior change. Fallback-to-default is preserved exactly.

**BF-012: Remove double CostEstimator call per node**
- Root cause: `execute_node()` instantiated `CostEstimator` and called `estimate_cost()` twice — once after the LLM call (result assigned to `cost_usd` but never used), and again inside the storage persistence block to populate `state_snapshot["cost_usd"]`.
- Fix: Removed the second instantiation. The `cost_usd` value computed in the first block is now reused directly in the storage snapshot.
- No observable behavior change — cost values and storage records are identical.

**BF-011: List field reducer — `replace` semantics for retry loops**
- Root cause: all list-type state fields unconditionally used `_list_concat_reducer` (append). In a retry loop, each iteration appended to the previous result — after N loops the field contained N× the data.
- Fix: Added `reducer: Literal["append", "replace"]` field to `StateFieldConfig` (default: `"append"`, fully backward-compatible). Users declare `reducer: replace` on any list field that represents "current result" rather than "accumulated history".
- Added `_replace_reducer` to `state_builder.py` — returns new value, discards current.
- Replaced `_get_reducer_for_type(python_type)` with `_get_reducer_for_field(python_type, field_config)` — selects reducer based on type AND explicit config.
- Config validator rejects `reducer: replace` on non-list types (e.g. `str`, `int`, `dict`).
- Tests: 4 unit tests for reducer functions, 4 end-to-end model tests, 7 schema validator tests.
- Docs: updated `CONFIG_REFERENCE.md` — added `reducer` to Field Properties table with usage guidance.

**BF-010: Loop `max_iterations` guard now works correctly**
- Root cause: `_wrap_with_loop_counter()` wrote loop counter into node output dict, but Pydantic dropped it as an unknown field (extra="ignore"). Counter was always 0. `max_iterations` was dead code.
- Fix: Auto-inject `__loop_counter_{node_id}: int = 0` fields into state model at build time by scanning loop edges (`get_loop_counter_fields()`). Fields are registered in the Pydantic model so updates are accepted.
- Updated `get_loop_iteration_key()` prefix from `_loop_iteration_` → `__loop_counter_` to match injected field names.
- Made `create_loop_router()` use `get_loop_iteration_key()` instead of its own hardcoded string.
- Added `extra_fields` param to `build_state_model()` for injecting framework-managed fields.
- Executor now calls `build_state_model(config.state, extra_fields=get_loop_counter_fields(config))`.
- Tests: updated existing loop tests to new key prefix; added unit tests for `extra_fields`, `get_loop_iteration_key`, and `get_loop_counter_fields`.

### Planning (2026-03-23)

**Code audit + v1.1 planning + documentation:**
- Full codebase audit: identified 4 bugs, 3 design gaps, and long-term architectural gaps
- Documented Phase 2 autonomous vision: hierarchical deterministic workflow platform
- Created [ROADMAP.md](docs/development/ROADMAP.md) — phase roadmap (v1.0 → v1.1 → Phase 2 → Phase 3)
- Created [VISION_AUTONOMOUS.md](docs/development/VISION_AUTONOMOUS.md) — Phase 2 autonomous system design
- Created ADR-027 (runtime overrides layer), ADR-028 (loop counter), ADR-029 (list reducer)
- Created 7 implementation logs for v1.1 tasks (BF-010 through T-016)
- Updated TASKS.md: v1.1 active tasks + expanded Phase 2 deferred requirements
- Updated ARCHITECTURE.md: known gaps table + Phase 2 insertion point notes
- Updated CONTEXT.md: current state, next steps

**Bugs identified (to be fixed in v1.1)**:
- BF-010: Loop `max_iterations` guard silently broken — counter always 0
- BF-011: List field reducer always appends — retry loops accumulate stale data
- BF-012: CostEstimator called twice per node — first result unused
- BF-013: Route condition failures silently swallowed — no log on broken conditions

**Features planned for v1.1**:
- T-014: Runtime memory override (`--memory-scope` CLI flag, webhook `runtime` block)
- T-015: Memory fact extraction opt-in (`extract_facts: false` default, `extraction_model` config)
- T-016: Web search hardening (retry, fallback, SQLite cache, result validation)

---

## [Unreleased] — v1.0 Post-Ship

### Fixed

**CL-006: Documentation sync — all docs aligned with actual code** (2026-02-28)
- Fixed dashboard port in README, QUICKSTART, PRODUCTION_DEPLOYMENT (8000 → 7861)
- Fixed "Workflow Registry" → "Deployment Registry" terminology in README
- Fixed broken `docs/ARCHITECTURE.md` link → `docs/development/ARCHITECTURE.md` in README
- Fixed `configurable-agents registry` → `configurable-agents deployments start` in SECURITY_GUIDE
- Fixed `configurable-agents deploy generate --config / --output` → `deploy <file> --generate --output-dir` in PRODUCTION_DEPLOYMENT
- Fixed "View running workflows" → "View running executions" in README
- Fixed "Monitor agent registry" → "Monitor deployment registry" in README
- Fixed "A/B testing and quality gates" PERFORMANCE_OPTIMIZATION.md description in README
- Fixed "Click + Rich" → "argparse + Rich" in ARCHITECTURE.md tech stack
- Removed "A/B testing support" from Observability Architecture section (optimization module was removed in CL-003)
- Fixed dashboard/webhooks port in Deployment Architecture section of ARCHITECTURE.md (8000 → 7861/7862)
- Fixed broken user guide relative links in ARCHITECTURE.md deep-dive section
- Removed dead `.planning/milestones/` references from README and ARCHITECTURE.md
- Fixed CL-002 status: IN PROGRESS → COMPLETE (cleanup finished in CL-003/004/005)
- Fixed ARCH-02 status: Partial → Complete in traceability matrix (completed 2026-02-06)
- Fixed CL-003 "Remaining" note to reference CL-005 which handled Round 3
- Added note to TASKS.md requirements mapping that plan files are internal-only
- Added CL-005 log and 4 missing UI design docs to docs/README.md index
- Updated CHANGELOG.md cleanup warning from "BROKEN" to "COMPLETE"

### Cleanup Status: COMPLETE (as of CL-005, 2026-02-24)

After introducing an autonomous agent system post-v1.0, the codebase and documentation
became inconsistent and out of sync. All cleanup tasks (CL-001 through CL-005) are now
complete. The project has been restored to a verified, testable state (671 tests passing).

### Fixed

**CL-005: UI commands verification and fixes** (2026-02-24)
- Fixed `chat` command crash — `create_storage_backend()` tuple unpack mismatch (7 vs 8) after UI-REDESIGN removed orchestrator repo (VF-010)
- Fixed `cmd_dashboard` startup banner printing stale `/workflows` and `/agents` URLs instead of `/executions` and `/deployments` (VF-007)
- Fixed executions table header `Agent ID` → `Deployment ID` and confirm dialog `Cancel this workflow?` → `Cancel this execution?` (VF-008)
- Fixed nonexistent execution detail returning HTTP 200 instead of 404 (VF-009)
- Fixed `ProcessManager.check_restore_session()` SQLAlchemy detached instance warning via `session.expunge()` (VF-011)
- Fixed `win32job` API misuse in MLflow cleanup — corrected `QueryInformationJobObject`/`SetInformationJobObject` usage and `AssignProcessToJobObject` signature (VF-012)

### Changed

**CL-005: Documentation sync with code** (2026-02-24)
- Updated UI_ARCHITECTURE.md route tree: `POST /deployments/{id}/deregister` → `DELETE /deployments/{id}`
- Added undocumented legacy metric routes and backward-compat aliases to UI_ARCHITECTURE.md
- Fixed `app.state` listing and router count in UI_ARCHITECTURE.md init flow diagram

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
