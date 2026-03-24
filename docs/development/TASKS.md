# Requirements: Configurable Agent Orchestration Platform

**Version**: v1.1 In Progress | v1.0 Shipped (2026-02-04)
**Last Updated**: 2026-03-23

---

## v1.1 Active Tasks — Hardening & Usability

> **Context**: A detailed code audit (2026-03-23) surfaced bugs and design gaps in the v1.0 implementation. This section tracks all v1.1 work. Phase 2 (autonomous vision) is fully deferred — see [VISION_AUTONOMOUS.md](VISION_AUTONOMOUS.md) and the Phase 2 section below.

---

### BF-010: Fix Loop `max_iterations` — Loop Counter State Injection

**Status**: DONE (2026-03-24)
**Priority**: HIGH
**ADR**: [ADR-028](adr/ADR-028-loop-counter-state-injection.md)

**Problem**: Loop counter `_loop_iteration_{node_id}` returned in node output dict but dropped by Pydantic (extra field, not in state schema). Counter is always 0. `max_iterations` guard is dead code. Loops can only exit via `condition_field`.

**Fix**: Auto-inject `__loop_counter_{node_id}: int = 0` fields into state schema at graph build time by scanning loop edges.

**Details**: [BF-010 Implementation Log](implementation_logs/phase_6_v1_1_hardening/BF-010_loop_max_iterations.md)

---

### BF-011: Fix List Field Reducer — Replace Semantics for Loops

**Status**: DONE (2026-03-24)
**Priority**: HIGH
**ADR**: [ADR-029](adr/ADR-029-list-field-reducer-config.md)

**Problem**: All list-type state fields use append reducer. Retry loops accumulate results from every iteration instead of replacing. After N retries, a list field contains N× the expected data.

**Fix**: Add optional `reducer: replace | append` to `StateFieldConfig` schema. Default stays `append` (backward compatible). Users declare `replace` on any list field used as a "current results" buffer in a loop.

**Details**: [BF-011 Implementation Log](implementation_logs/phase_6_v1_1_hardening/BF-011_list_reducer.md)

---

### BF-012: Fix Double CostEstimator Call Per Node

**Status**: DONE (2026-03-24)
**Priority**: MEDIUM

**Problem**: `execute_node()` creates and calls `CostEstimator` twice — once at ~line 598 (result unused), once at ~line 685 for storage. Wasted compute, inconsistency risk.

**Fix**: Remove first dead call. Single calculation, reused.

**Details**: [BF-012 Implementation Log](implementation_logs/phase_6_v1_1_hardening/BF-012_cost_estimator_double_call.md)

---

### BF-013: Fix Silent Route Condition Failure

**Status**: DONE (2026-03-24)
**Priority**: MEDIUM

**Problem**: Failed condition evaluations silently fall to default route with no log. Broken condition expressions are invisible — workflow appears to work but ignores the intended routing.

**Fix**: Log WARNING with condition text and error reason when a condition evaluation fails.

**Details**: [BF-013 Implementation Log](implementation_logs/phase_6_v1_1_hardening/BF-013_silent_route_condition_logging.md)

---

### T-014: Runtime Memory Override — Per-Invocation Control

**Status**: DONE (2026-03-24)
**Priority**: HIGH
**ADR**: [ADR-027](adr/ADR-027-runtime-overrides-layer.md)

**Problem**: Memory scope is fixed in YAML per node. Changing it requires config edits, defeating the goal of a single reusable config invokable in different modes (e.g., production with no memory vs. development with full memory).

**Fix**: Introduce `runtime_overrides` dict layer applied after config parse, before execution. Initial scope: memory overrides. CLI: `--memory-scope none|workflow|agent`. Webhook: `runtime: {memory: {scope: none}}` in POST body.

**Details**: [T-014 Implementation Log](implementation_logs/phase_6_v1_1_hardening/T-014_runtime_memory_override.md)

---

### T-015: Memory Fact Extraction — Make Opt-In

**Status**: TODO
**Priority**: HIGH

**Problem**: Every memory-enabled node makes an extra full LLM API call for fact extraction. Always-on, undocumented, doubles cost and latency. No user visibility into these extra calls.

**Fix**: Add `extract_facts: bool = False` to `MemoryConfig`. Extraction is opt-in. Add `extraction_model` for specifying a cheaper model when extraction IS enabled.

**Details**: [T-015 Implementation Log](implementation_logs/phase_6_v1_1_hardening/T-015_memory_extraction_opt_in.md)

---

### T-016: Web Search Enterprise Hardening

**Status**: TODO
**Priority**: MEDIUM

**Problem**: Single attempt, no retry, no fallback, no caching, no result validation. Transient API failures abort workflows. Same query costs money on every run even if recently fetched.

**Fix**: Add retry with backoff, provider fallback, SQLite-backed query cache (TTL=1h, on by default), minimum result validation.

**Details**: [T-016 Implementation Log](implementation_logs/phase_6_v1_1_hardening/T-016_web_search_hardening.md)

---

## v1.0 Completed Tasks

### UI-REDESIGN: Unified UI Architecture Implementation ✅ COMPLETE

**Status**: COMPLETE
**Started**: 2026-02-13
**Completed**: 2026-02-13 (template fix: 2026-02-17)
**Priority**: HIGH

**Summary**: Implemented unified 4-page UI architecture (Chat UI, Executions, Deployments, MLflow). All terminology renamed for consistency.

**Design Documents**:
- [UI_DESIGN_SPEC.md](UI_DESIGN_SPEC.md) — Complete specification (approved)
- [UI_PAGES_DESIGN.md](UI_PAGES_DESIGN.md) — ASCII mockups, user flows
- [UI_REDESIGN_ANALYSIS.md](UI_REDESIGN_ANALYSIS.md) — Impact analysis (~45 files)

**Implementation Phases**:

| Phase | Focus | Files | Status |
|-------|-------|-------|--------|
| 1 | Storage Layer | 5 | ✅ COMPLETE |
| 2 | CLI Updates | 2 | ✅ COMPLETE |
| 3 | Registry Module | 4 | ✅ COMPLETE |
| 4 | Dashboard/UI | 10 | ✅ COMPLETE |
| 5 | Tests | 10 | ✅ COMPLETE |
| 6 | Documentation | 6 | ✅ COMPLETE |

**Key Changes Summary**:
- `WorkflowRunRecord` → `Execution` (table: `executions`)
- `AgentRecord` → `Deployment` (table: `deployments`)
- `OrchestratorRecord` → REMOVED (absorbed into deployments)
- CLI command: `workflow-registry` → `deployments`
- Routes: `/workflows/*` → `/executions/*`, `/agents/*` → `/deployments/*`
- Storage factory: 8 → 7 return values

**Template Alignment** (2026-02-17):
- Fixed all Jinja2 HTML templates missed during Phase 4 (variable names, model fields, file renames)
- Removed dead `orchestrator.html` template and Optimization nav link
- Removed 6 stale optimization tests from UI test suites
- Test results: 85 passed, 0 failed

**Breaking Changes**:
- Requires fresh database (tables renamed)
- API routes changed
- CLI commands changed

**Details**:
- [Implementation Plan](implementation_logs/UI_REDESIGN_IMPLEMENTATION_PLAN.md)
- [ADR-026](adr/ADR-026-ui-redesign-terminology.md) — Architecture decision

---

### CL-006: Full Documentation Audit and Sync ✅ COMPLETE

**Status**: COMPLETE
**Started**: 2026-02-28
**Completed**: 2026-02-28
**Priority**: MEDIUM

**Summary**: Comprehensive audit of all docs vs actual code. Found and fixed 22 discrepancies across 9 files.

**Issues Fixed**:
- Port numbers: dashboard default 8000 → 7861 (README, QUICKSTART, PRODUCTION_DEPLOYMENT, ARCHITECTURE)
- CLI commands: `registry` → `deployments start`, `deploy generate --config` → `deploy <file> --generate --output-dir`
- Terminology: "Workflow Registry" → "Deployment Registry", "workflows" → "executions" (README)
- ARCHITECTURE.md: `Click` → `argparse`, removed A/B testing from observability, fixed ports, fixed user guide links
- Dead references: Removed all `.planning/milestones/` dead links (README, ARCHITECTURE)
- TASKS.md: ARCH-02 Partial → Complete, CL-002 IN PROGRESS → COMPLETE, added plan file note
- CHANGELOG.md: Updated "PROJECT STATE IS BROKEN" → "COMPLETE"
- docs/README.md: Added CL-005 log + 4 missing UI design docs to index

**Details**: All 22 findings from the post-CL-005 documentation audit

---

### CL-005: UI Commands Verification and Fixes ✅ COMPLETE

**Status**: COMPLETE
**Started**: 2026-02-24
**Completed**: 2026-02-24
**Priority**: MEDIUM

**Summary**: Deep-tested the 3 remaining UI commands (`dashboard`, `chat`, `ui`) — Round 3 of CLI verification. Found 7 issues (VF-007–VF-013), fixed 6.

**Issues Found and Fixed**:

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| VF-007 | Low | Dashboard startup prints stale `/workflows`, `/agents` URLs | Updated to `/executions`, `/deployments` |
| VF-008 | Medium | Template `Agent ID` header, `Cancel this workflow?` dialog | Renamed to `Deployment ID`, `Cancel this execution?` |
| VF-009 | Low | Nonexistent execution returns HTTP 200 | Added `status_code=404` |
| VF-010 | **Critical** | `chat` crashes — storage factory tuple unpack (8 vs 7) | Fixed to 7-value unpack |
| VF-011 | Low | `check_restore_session()` SQLAlchemy detached instance | Added `session.expunge()` |
| VF-012 | Medium | `win32job` API misuse — job objects non-functional | Rewrote with correct pywin32 API |
| VF-013 | Low | cli.py imports ~17s on Windows (observation) | No fix — future lazy import opportunity |

**Also completed**:
- Synced UI_ARCHITECTURE.md with actual code (4 doc discrepancies corrected pre-runtime)

**Test results**: 671 passed, 1 pre-existing failure, 3 skipped

**Details**: [CL-005 UI Commands Verification](implementation_logs/phase_5_cleanup_and_verification/CL-005_UI_COMMANDS_VERIFICATION.md)

---

### CL-004: Documentation Truth Audit and Dead Code Removal ✅ COMPLETE

**Status**: COMPLETE
**Started**: 2026-02-17
**Completed**: 2026-02-17
**Priority**: HIGH

**Summary**: Systematic audit of all documentation after heavy churn from CL-003, UI-REDESIGN, BF-007/008/009, and template alignment fixes. Removed dead orchestrator module, fixed 38+ stale documentation references across 13 files.

**Actions Completed**:
- ✅ Removed orchestrator module entirely (src, deploy, tests, examples — 12 files)
- ✅ Fixed optimization/A/B testing references in 7 user-facing docs
- ✅ Fixed UI-REDESIGN terminology in 4 internal dev docs
- ✅ Fixed multi-agent collaboration example config
- ✅ Fixed test_schema_integration.py referencing removed config.optimization
- ✅ Verified: 348 passed, 4 skipped, 0 failed

**Details**: [CL-004 Documentation Truth Audit](implementation_logs/phase_5_cleanup_and_verification/CL-004_documentation_truth_audit.md)

---

### CL-003: Codebase Cleanup, Testing, and Verification — SUPERSEDED

**Status**: SUPERSEDED by UI-REDESIGN
**Started**: 2026-02-07
**Completed**: 2026-02-13 (superseded)

**Note**: The "workflow-registry" → "deployments" rename from CL-003 has been superseded by the comprehensive UI-REDESIGN task which renamed all terminology consistently across the codebase.

**Priority**: HIGH

**Summary**: Systematic testing of all 12 test configs, fixing bugs discovered during testing.

**Completed**:
- All 12 test configs validated and executing successfully
- Fixed INVALID_CONCURRENT_GRAPH_UPDATE (Annotated reducers in state_builder.py)
- Fixed test config YAML syntax (routes, loop blocks)
- Replaced broken MAP/Send parallel with fork-join parallel (10-phase implementation)
- Config 07 and 12 fully rewritten and verified

**Bug Fixes** (discovered during CL-003):

| ID | Issue | Priority | Status |
|----|-------|----------|--------|
| BF-001 | Storage backend tuple unpacking (`too many values to unpack`) | HIGH | ✅ DONE |
| BF-002 | Tool execution — no agent loop in provider.py | CRITICAL | ✅ DONE |
| BF-003 | Memory persistence — not persisting between runs | MEDIUM | ✅ DONE |
| BF-004 | MLFlow cost summary — parsing, model attribution, GenAI view | MEDIUM | ✅ DONE |
| BF-005 | Pre-existing test failures (dict-vs-Pydantic, deploy artifacts) | MEDIUM | ✅ DONE |
| BF-006 | ChatLiteLLM deprecation migration (`langchain-litellm`) | LOW | ✅ DONE |
| BF-007 | Webhooks CLI — wrong router import | MEDIUM | ✅ DONE |
| BF-008 | Docker deploy — build failure + port mismatch | HIGH | ✅ DONE |
| BF-009 | Vestigial `--enable-profiling` CLI flag | LOW | ✅ DONE |

**CLI Verification** (2026-02-09):
- All 20 CLI commands discovered and documented in `docs/user/cli_guide.md`
- All commands manually tested — basic functionality verified for all
- Full Docker deploy verified end-to-end (build → run → API calls)

**Deep Flag Verification — Round 1** (2026-02-09):
- All 10 flag/command items tested in depth — 5 issues found (VF-001–VF-005)
- Created `OBSERVABILITY_REFERENCE.md` — MLflow 3.9 GenAI reference doc

**Extended CLI Verification — Round 2** (2026-02-09):
- 4 commands tested — 1 new issue found (VF-006)
- Created `UI_ARCHITECTURE.md`

**VF Fixing Session** (2026-02-10) — ALL 6 ISSUES FIXED:

| ID | Summary | Fix Applied | Status |
|----|---------|-------------|--------|
| VF-001 | `--verbose` no DEBUG output | Added `setup_logging()` in `main()` | ✅ FIXED |
| VF-002 | `--enable-profiling` no-op | Removed dead env var + `mlflow.active_run()` code | ✅ FIXED |
| VF-003 | `--no-mlflow` cosmetic artifacts | Conditional template variables in generator.py | ✅ FIXED |
| VF-004 | Reporting uses legacy `search_runs()` | Rewrote cost-report, profile-report, obs status to `search_traces()` | ✅ FIXED |
| VF-005 | `report costs` wrong tracking URI | Added `mlflow.set_tracking_uri()` + trace-based rewrite | ✅ FIXED |
| VF-006 | Parent commands crash without subcommand | Added `hasattr(args, 'func')` check in `main()` | ✅ FIXED |

**Additional actions completed** (2026-02-10):
- **Removed optimization module** — Entire `optimization/` package, CLI commands, dashboard routes, templates, tests deleted. Quality gates moved to `runtime/gates.py`. See [OPTIMIZATION_INVESTIGATION.md](OPTIMIZATION_INVESTIGATION.md)
- **Renamed Agent Registry → Workflow Registry** — CLI command `agent-registry` → `workflow-registry`, added `WorkflowRegistryServer`/`WorkflowRegistryClient` aliases. Internal class names preserved for DB compatibility.

**Test results after fixes**: 656 passed, 0 failed, 3 skipped

**Round 3 completed in CL-005**: `dashboard`, `chat`, `ui` — all verified and fixed (VF-007–VF-013)

**Details**:
- [CL-003 VF Fixing Session](implementation_logs/phase_5_cleanup_and_verification/CL-003_VF_FIXING_SESSION.md)
- [CL-003 Deep Flag Verification](implementation_logs/phase_5_cleanup_and_verification/CL-003_DEEP_FLAG_VERIFICATION.md)
- [CL-003 Test Findings](implementation_logs/phase_5_cleanup_and_verification/CL-003_TEST_FINDINGS.md)
- [UI Architecture](UI_ARCHITECTURE.md) — Read before UI testing or fixing
- [Observability Reference](OBSERVABILITY_REFERENCE.md)
- [Optimization Investigation](OPTIMIZATION_INVESTIGATION.md)

---

### CL-002: Documentation Index and Dead Link Cleanup

**Status**: ✅ COMPLETE (Further cleanup completed in CL-003 through CL-005)
**Started**: 2026-02-06
**Completed**: 2026-02-06 (final verification via CL-003/CL-004/CL-005)

**Summary**: Created docs/README.md index and updated references to non-existent documentation.

**Actions Completed**:
- ✅ Created docs/README.md as comprehensive documentation index
- ✅ Updated CHANGELOG.md to remove .planning/ references and add broken state warning
- ✅ Updated README.md with documentation index link
- ✅ Updated CLAUDE.md with documentation structure information
- ✅ Updated docs/development/TASKS.md to remove .planning/ references
- ✅ Updated CONTEXT.md with broken state declaration

**Note**: All cleanup actions completed in CL-003/CL-004/CL-005. Project state is verified clean.

**Details**: [CL-002 Doc Index Cleanup](implementation_logs/phase_5_cleanup_and_verification/CL-002_doc_index_cleanup.md)

---

### CL-001: Cleanup and Documentation Reorganization

**Status**: ✅ COMPLETE
**Started**: 2026-02-06
**Completed**: 2026-02-06

**Summary**: Cleanup after autonomous agent caused documentation and codebase discrepancies.

**Actions Completed**:
- ✅ Reorganized documentation structure (docs/user/ vs docs/development/)
- ✅ Updated CLAUDE.md with permanent instructions
- ✅ Updated CONTEXT.md with new structure
- ✅ Updated README.md with new doc paths
- ✅ Updated CHANGELOG.md with CL-001 entry
- ✅ Created implementation log for CL-001
- ✅ Committed and pushed to dev (commit: 66fd643)

**Details**: [CL-001 Cleanup Restoration](implementation_logs/phase_5_cleanup_and_verification/CL-001_cleanup_restoration.md)

---

**Philosophy**: This document tracks v1.0 milestone requirements.

---

## v1.0 Requirements Status

**Total**: 27 requirements
**Complete**: 27/27 (100%)
**Shipped**: 2026-02-04

### Requirement Categories

**Runtime (8/8 complete)**:
- [x] **RT-01**: Conditional routing in workflow configs (if/else based on agent outputs)
- [x] **RT-02**: Loops in workflow configs (retry logic, iteration with termination conditions)
- [x] **RT-03**: Parallel node execution (concurrent agent operations via fan-out/fan-in)
- [x] **RT-04**: Agent-generated code in sandboxed environment (Docker-based isolation with resource limits)
- [x] **RT-05**: Any supported LLM provider per node (OpenAI, Anthropic, Gemini, Ollama via LiteLLM)
- [x] **RT-06**: Workflows entirely on local models via Ollama (zero cloud cost, full privacy)
- [x] **RT-07**: Persistent memory per node, agent, or workflow (context survives across executions)
- [x] **RT-08**: Pre-built LangChain tools in workflow nodes (search, APIs, data processing - 15 common tools)

**Observability (4/4 complete)**:
- [x] **OBS-01**: Full MLFlow production features (prompt optimization, evaluations, A/B testing)
- [x] **OBS-02**: Token costs across all configured LLM providers with unified reporting
- [x] **OBS-03**: Performance profiling and bottleneck detection for workflow executions
- [x] **OBS-04**: Detailed workflow execution traces with per-node metrics (latency, tokens, cost)

**User Interface (6/6 complete)**:
- [x] **UI-01**: Generate YAML configs through conversational chat interface (Gradio-based)
- [x] **UI-02**: Chat UI persists conversation history and config iterations across sessions
- [x] **UI-03**: Manage running workflows through orchestration dashboard (FastAPI + HTMX)
- [x] **UI-04**: Discover and register agents through the orchestration interface
- [x] **UI-05**: MLFlow UI accessible within the orchestration dashboard (iframe integration)
- [x] **UI-06**: Monitor agent status, logs, and metrics in real-time (streaming updates)

**Architecture (6/6 complete)**:
- [x] **ARCH-01**: Agent containers are minimal (~50-100MB) with MLFlow UI decoupled as separate sidecar
- [x] **ARCH-02**: Agents support bidirectional registration (agent-initiated and orchestrator-initiated) ✅ COMPLETE (2026-02-06)
- [x] **ARCH-03**: Agent registry tracks active agents with heartbeat and TTL-based expiration
- [x] **ARCH-04**: Storage backend is pluggable (SQLite default, swappable to PostgreSQL/Redis without code changes)
- [x] **ARCH-05**: Chat UI sessions persist conversation history in storage backend
- [x] **ARCH-06**: Long-term memory has dedicated storage backend (per-agent context storage)

**Integration (3/3 complete)**:
- [x] **INT-01**: Trigger workflows from WhatsApp messages (webhook integration)
- [x] **INT-02**: Trigger workflows from Telegram messages (bot integration)
- [x] **INT-03**: Trigger workflows from any external system via generic webhook API

---

## Requirements Mapping to Phases

> **Note**: Plan file references (e.g., `01-03-PLAN.md`) are internal planning documents not checked into the repository. See [implementation_logs/](implementation_logs/) for actual implementation details.

| Requirement | Phase | Status | Plan (internal reference) |
|-------------|-------|--------|--------------------------|
| RT-01 | Phase 1 | Complete | 01-03-PLAN.md |
| RT-02 | Phase 1 | Complete | 01-03-PLAN.md |
| RT-03 | Phase 1 | Complete | 01-03-PLAN.md |
| RT-05 | Phase 1 | Complete | 01-02-PLAN.md |
| RT-06 | Phase 1 | Complete | 01-02-PLAN.md |
| ARCH-04 | Phase 1 | Complete | 01-01-PLAN.md |
| OBS-04 | Phase 1 | Complete | 01-04-PLAN.md |
| ARCH-01 | Phase 2 | Complete | 02-01-PLAN.md series |
| ARCH-02 | Phase 2 | Complete | 02-01-PLAN.md series (orchestrator-initiated completed 2026-02-06) |
| ARCH-03 | Phase 2 | Complete | 02-01-PLAN.md series |
| OBS-02 | Phase 2 | Complete | 02-02-PLAN.md |
| OBS-03 | Phase 2 | Complete | 02-02-PLAN.md |
| UI-01 | Phase 3 | Complete | 03-01-PLAN.md |
| UI-02 | Phase 3 | Complete | 03-01-PLAN.md |
| UI-03 | Phase 3 | Complete | 03-02-PLAN.md |
| UI-04 | Phase 3 | Complete | 03-02-PLAN.md |
| UI-05 | Phase 3 | Complete | 03-02-PLAN.md |
| UI-06 | Phase 3 | Complete | 03-02-PLAN.md |
| ARCH-05 | Phase 3 | Complete | 03-01-PLAN.md |
| INT-01 | Phase 3 | Complete | 03-03B-PLAN.md |
| INT-02 | Phase 3 | Complete | 03-03B-PLAN.md |
| INT-03 | Phase 3 | Complete | 03-03-PLAN.md |
| RT-04 | Phase 4 | Complete | 04-01-PLAN.md |
| RT-07 | Phase 4 | Complete | 04-02-PLAN.md |
| RT-08 | Phase 4 | Complete | 04-02-PLAN.md |
| OBS-01 | Phase 4 | Complete | 04-03-PLAN.md |
| ARCH-06 | Phase 4 | Complete | 04-02-PLAN.md |

**Coverage**:
- v1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0

---

## v1.0 Milestone Summary

**Shipped**: 27 of 27 v1 requirements (100%)
**Previously Adjusted**: ARCH-02 was marked as partial (orchestrator-initiated deferred post-v1, agent-initiated is sufficient)
**Update (2026-02-06)**: ARCH-02 is now complete - orchestrator-initiated registration implemented via dashboard UI
**Dropped**: None

All v1.0 requirements were successfully implemented and verified through integration testing.

---

## Phase Breakdown

### Phase 1: Core Engine (4 plans complete)

**Goal**: Users can define and execute complex multi-provider workflows with branching, loops, and parallelism on a pluggable storage backend with full execution traces.

**Requirements Delivered**:
- RT-01: Conditional routing ✓
- RT-02: Loop execution ✓
- RT-03: Parallel execution ✓
- RT-05: Multi-LLM providers (LiteLLM + direct Google) ✓
- RT-06: Local models via Ollama ✓
- ARCH-04: Pluggable storage backend ✓
- OBS-04: Execution traces ✓

**Plans**:
- [x] 01-01-PLAN.md - Storage abstraction layer
- [x] 01-02-PLAN.md - Multi-LLM provider integration
- [x] 01-03-PLAN.md - Advanced control flow
- [x] 01-04-PLAN.md - Storage-executor integration

**Status**: Complete 2026-02-03

---

### Phase 2: Agent Infrastructure (6 plans complete)

**Goal**: Users can deploy minimal agent containers that self-register, maintain health, and produce detailed observable metrics across all providers.

**Requirements Delivered**:
- ARCH-01: Minimal agent containers ✓
- ARCH-02: Bidirectional registration (partial - agent-initiated only) ✓
- ARCH-03: Agent registry with heartbeat/TTL ✓
- OBS-02: Multi-provider cost tracking ✓
- OBS-03: Performance profiling ✓

**Plans**:
- [x] 02-01A-PLAN.md - Storage layer and registry server
- [x] 02-02A-PLAN.md - Multi-provider cost tracking
- [x] 02-02B-PLAN.md - Performance profiling
- [x] 02-01B-PLAN.md - Registry client and generator integration
- [x] 02-02C-PLAN.md - CLI integration
- [x] 02-01C-PLAN.md - CLI and tests

**Status**: Complete 2026-02-03

---

### Phase 3: Interfaces and Triggers (6 plans complete)

**Goal**: Users can generate configs through conversation, manage running workflows through a dashboard, and trigger workflows from external messaging platforms.

**Requirements Delivered**:
- UI-01: Chat UI for config generation ✓
- UI-02: Chat UI session persistence ✓
- UI-03: Orchestration dashboard ✓
- UI-04: Agent discovery UI ✓
- UI-05: MLFlow UI integration ✓
- UI-06: Real-time monitoring ✓
- ARCH-05: Chat UI session storage ✓
- INT-01: WhatsApp webhooks ✓
- INT-02: Telegram webhooks ✓
- INT-03: Generic webhooks ✓

**Plans**:
- [x] 03-01-PLAN.md - Chat UI for config generation
- [x] 03-02-PLAN.md - Orchestration dashboard
- [x] 03-03-PLAN.md - Generic webhook infrastructure
- [x] 03-03B-PLAN.md - Platform webhook integrations
- [x] 03-04-PLAN.md - Workflow restart implementation
- [x] 03-05-PLAN.md - Test fixture unpacking fix

**Status**: Complete 2026-02-03

---

### Phase 4: Advanced Capabilities (3 plans complete)

**Goal**: Users can run agent-generated code safely, leverage persistent memory across executions, use pre-built tools, and optimize prompts through MLFlow experimentation.

**Requirements Delivered**:
- RT-04: Sandbox code execution ✓
- RT-07: Long-term memory ✓
- RT-08: Pre-built tools ✓
- OBS-01: MLFlow optimization ✓
- ARCH-06: Memory backend ✓

**Plans**:
- [x] 04-01-PLAN.md - Code execution sandbox
- [x] 04-02-PLAN.md - Long-term memory and tool ecosystem
- [x] 04-03-PLAN.md - MLFlow optimization

**Status**: Complete 2026-02-04

---

## Deferrals

### ARCH-02: Orchestrator-Initiated Registration

**Status**: Partially complete (agent-initiated only)

**Reason**: Agent-initiated registration is sufficient for v1.0 use cases. Orchestrator-initiated registration (active discovery) can be added post-v1 without breaking changes.

**Impact**: Low - agents can self-register on startup, heartbeat maintains health, no manual discovery needed.

**Future**: Consider adding in v1.1 if multi-agent orchestration requires centralized agent discovery.

---

## Phase 2 Deferred Requirements — Autonomous Expansion

> **These are fully deferred. No implementation until Phase 2 is explicitly started.**
> **Vision details**: [VISION_AUTONOMOUS.md](VISION_AUTONOMOUS.md) | **Roadmap**: [ROADMAP.md](ROADMAP.md)

---

### Autonomy Framework

- **AUT-01**: Autonomy level configuration model (0=fixed, 1=selective, 2=composable, 3=generative) — per-workflow setting
- **AUT-02**: Expansion engine — meta-agent that generates new NodeSpec/EdgeSpec at runtime given task context and structural memory
- **AUT-03**: Ephemeral expansion — dynamic nodes exist for one run only, fully logged in MLFlow trace
- **AUT-04**: Persistent expansion — approved ephemeral expansions written back to config as derived child config with parent reference
- **AUT-05**: Expansion validation — autonomy level constraints enforced on generated structure; expansion engine cannot exceed declared level
- **AUT-06**: Rule-based expansion triggers (Level 1) — deterministic expansion decisions without LLM (e.g., "if node returns > N items, fan out")

### Structural Memory (distinct from content memory)

- **SMEM-01**: Structural memory schema — stores workflow patterns, expansion paths, routing decisions, and outcome metrics as structured records
- **SMEM-02**: Structural memory backend — dedicated storage table, separate from content memory KV store
- **SMEM-03**: Expansion engine reads structural memory to bias toward historically successful patterns
- **SMEM-04**: Confidence updates — structural memory records updated via Bayesian update based on run outcomes
- **SMEM-05**: Memory pruning — API to remove stale or invalid structural memory patterns

### Path-Based Traceability

- **TRACE-01**: Canonical execution path format — `{workflow}@{version}/{node}[{context}]/...` stored as MLFlow trace attribute
- **TRACE-02**: Path replay — given (workflow_version + input + expansion_path), reproduce the exact execution structure
- **TRACE-03**: Path diff — compare two execution paths from the same workflow to identify divergence points
- **TRACE-04**: Expansion history — every generated node logged with expansion engine rationale and structural memory citations

### Self-Optimization

- **SELF-01**: MLFlow evaluation framework integration — define quality metrics, run evaluation sweeps, identify underperforming nodes
- **SELF-02**: Workflow evolution lifecycle — review/approve/reject expansion history; promote ephemeral → persistent
- **SELF-03** (conditional): DSPy prompt optimization — if MLFlow evaluation proves insufficient for cross-LLM consistency, add DSPy compilation per model. Decision deferred until MLFlow evaluation is tested.

### Advanced Memory (Content Tier)

- **MEM-01**: Vector/semantic memory — evaluate Mem0 or LightRAG for semantic search over memory vs. current KV lookup
- **MEM-02**: Agent Protocol support (A2A, MCP) — cross-platform memory interoperability
- **MEM-03**: Memory re-use patterns across workflow types (share relevant memories across related workflows)

### Enterprise Scale (Phase 3+)

- **ENT-01**: Kubernetes deployment with auto-scaling, Helm charts, and cloud storage backends
- **ENT-02**: Multi-tenancy with tenant isolation and RBAC
- **ENT-03**: OpenTelemetry integration for enterprise observability platforms

### Extended Tools (Phase 3+)

- **TOOL-01**: Full LangChain tool registry (500+ tools) with dynamic discovery
- **TOOL-02**: Visual workflow builder (drag-and-drop node editor with config export)

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud-hosted managed service | Violates local-first principle; users deploy to own infrastructure |
| React/JS-based UI frameworks | Heavyweight, complex; using Gradio + HTMX instead |
| Agent marketplace | Premature for v1; focus on core platform first |
| Multi-tenancy | v1 targets single user/team; enterprise later |
| Visual workflow builder | Config-first philosophy; no drag-drop node editors in v1 |
| Full LangChain tool registry | Start with common subset (15 tools); expand based on demand |

---

## Requirements Traceability Matrix

| ID | Requirement | Phase | Status | ADR |
|----|-------------|-------|--------|-----|
| RT-01 | Conditional routing | 1 | Complete | ADR-001 |
| RT-02 | Loops | 1 | Complete | ADR-001 |
| RT-03 | Parallel execution | 1 | Complete | ADR-001 |
| RT-04 | Sandbox code execution | 4 | Complete | ADR-022 |
| RT-05 | Multi-LLM providers | 1 | Complete | ADR-005, ADR-019 |
| RT-06 | Local models (Ollama) | 1 | Complete | ADR-019 |
| RT-07 | Persistent memory | 4 | Complete | ADR-023 |
| RT-08 | Pre-built tools | 4 | Complete | ADR-007 |
| OBS-01 | MLFlow optimization | 4 | Complete | ADR-011, ADR-025 |
| OBS-02 | Multi-provider costs | 2 | Complete | ADR-011 |
| OBS-03 | Performance profiling | 2 | Complete | ADR-011 |
| OBS-04 | Execution traces | 1 | Complete | ADR-011 |
| UI-01 | Chat UI config generation | 3 | Complete | ADR-021 |
| UI-02 | Chat UI persistence | 3 | Complete | ADR-021 |
| UI-03 | Orchestration dashboard | 3 | Complete | ADR-021 |
| UI-04 | Agent discovery UI | 3 | Complete | ADR-021 |
| UI-05 | MLFlow UI integration | 3 | Complete | ADR-021 |
| UI-06 | Real-time monitoring | 3 | Complete | ADR-021 |
| ARCH-01 | Minimal agent containers | 2 | Complete | ADR-020 |
| ARCH-02 | Bidirectional registration | 2 | Complete | ADR-020 |
| ARCH-03 | Agent registry | 2 | Complete | ADR-020 |
| ARCH-04 | Pluggable storage | 1 | Complete | Phase 1 (01-01) |
| ARCH-05 | Chat UI storage | 3 | Complete | ADR-021 |
| ARCH-06 | Memory backend | 4 | Complete | ADR-023 |
| INT-01 | WhatsApp webhooks | 3 | Complete | ADR-024 |
| INT-02 | Telegram webhooks | 3 | Complete | ADR-024 |
| INT-03 | Generic webhooks | 3 | Complete | ADR-024 |

---

## References

- **Architecture Decision Records**: [docs/development/adr/](adr/)
- **Technical Specification**: [docs/development/SPEC.md](SPEC.md)
- **Architecture Overview**: [docs/development/ARCHITECTURE.md](ARCHITECTURE.md)
- **Documentation Index**: [docs/README.md](../README.md)

---

*Archived: 2026-02-04 as part of v1.0 milestone completion*
