# Roadmap: Configurable Agent Orchestration Platform

## Overview

A journey from broken system to working platform through systematic testing and fixing of each component. v1.2 focuses on making the system actually work - CLI commands execute without errors, all Dashboard pages load and function, Chat UI works end-to-end, workflows execute successfully from both CLI and UI, and integration tests prevent regression.

## Milestones

- ✅ **v1.0 Foundation** — Phases 1-4 (shipped 2026-02-04) — [View details](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Core UX Polish** — Phases 5-6 (shipped 2026-02-05)
- 🚧 **v1.2 Integration Testing & Critical Bug Fixes** — Phases 7-11 (in progress)

## Phases

<details>
<summary>✅ v1.0 Foundation (Phases 1-4) — SHIPPED 2026-02-04</summary>

See [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) for full details.

**Summary:**
- Phase 1: Core Engine (4 plans) - Multi-LLM support, advanced control flow, storage abstraction
- Phase 2: Agent Infrastructure (6 plans) - Minimal containers, agent lifecycle, observability
- Phase 3: Interfaces and Triggers (6 plans) - Chat UI, orchestration dashboard, webhooks
- Phase 4: Advanced Capabilities (3 plans) - Code sandboxes, memory, tools, MLFlow optimization

**Status:** All 4 phases complete, 19 plans shipped, 27/27 requirements satisfied

</details>

<details>
<summary>✅ v1.1 Core UX Polish (Phases 5-6) — SHIPPED 2026-02-05</summary>

**Milestone Goal:** Streamline developer experience with single-command startup, unified workspace, auto-initialization, and intuitive navigation.

#### Phase 5: Foundation & Reliability
**Goal**: Users can start the platform with one command and it just works, with clear feedback and graceful error handling.
**Depends on**: Phase 4
**Requirements**: STARTUP-01, STARTUP-02, STARTUP-03, STARTUP-04, STARTUP-05, STARTUP-06, OBS-01, ERR-01
**Success Criteria** (what must be TRUE):
  1. User can start entire UI with single command `configurable-agents ui` and see all services launch
  2. First run creates databases automatically without errors (from CLI, Python API, or UI)
  3. Startup shows progress feedback (spinners or "X/Y steps complete")
  4. Dashboard shows status at a glance (active workflows, agent health, recent errors)
  5. All error messages include error code, description, and resolution steps
  6. Platform shuts down gracefully and restores sessions after crashes

**Plans**: 3 plans

Plans:
- [x] 05-01: Single-command startup with ProcessManager
- [x] 05-02: Auto-initialization with graceful degradation
- [x] 05-03: Status dashboard and error handling

#### Phase 6: Navigation & Onboarding
**Goal**: Users can discover features quickly and navigate intuitively, with clear guidance on what to do next.
**Depends on**: Phase 5
**Requirements**: ONBOARD-01, NAV-01, NAV-02
**Success Criteria** (what must be TRUE):
  1. User can open command palette via Cmd/Ctrl+K and fuzzy search workflows, agents, templates
  2. User can filter navigation lists by typing in sideboards
  3. Empty states guide users to clear next actions ("Create workflow" or "Browse templates")

**Plans**: Deferred to v1.3

Plans:
- [ ] 06-01: Command palette (Cmd/Ctrl+K) with fuzzy search
- [ ] 06-02: Quick search in navigation sideboards
- [ ] 06-03: Empty state guidance and onboarding

**Status:** Phase 5 complete (3/3 plans), Phase 6 deferred to v1.3

</details>

### 🚧 v1.2 Integration Testing & Critical Bug Fixes (In Progress)

**Milestone Goal:** Make the system actually work through comprehensive testing and fixing all critical bugs.

#### Phase 7: CLI Testing & Fixes
**Goal**: All CLI commands work without errors
**Depends on**: Phase 5
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06
**Success Criteria** (what must be TRUE):
  1. User can run `configurable-agents run` and workflows execute without crashes
  2. User can run `configurable-agents validate` and configs are validated correctly
  3. User can run `configurable-agents deploy` and deployment artifacts are generated
  4. User can run `configurable-agents ui` and all services start successfully
  5. All CLI errors show clear messages with actionable resolution steps
**Plans**: 5 plans in 3 waves

Plans:
- [x] 07-01-PLAN.md — Test and fix CLI run command (subprocess tests, UnboundLocalError regression)
- [x] 07-02-PLAN.md — Test and fix CLI validate command (subprocess tests, error message quality)
- [x] 07-03-PLAN.md — Test and fix CLI deploy command (subprocess tests, Docker checks, generate-only mode)
- [x] 07-04-PLAN.md — Test and fix CLI ui command (subprocess tests, Windows multiprocessing compatibility)
- [x] 07-05-PLAN.md — Add CLI integration tests (comprehensive cross-platform tests, error message verification)

**Status:** Complete (2026-02-05) - 83 CLI integration tests created, all subprocess-based, verified on Windows

#### Phase 8: Dashboard UI Testing & Fixes
**Goal**: All Dashboard pages load and function correctly
**Depends on**: Phase 7
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07, DASH-08
**Success Criteria** (what must be TRUE):
  1. User can open Workflows page and see list of workflows
  2. User can open Agents page and see list of agents
  3. User can open Experiments page and see list of experiments
  4. User can open Optimization page and use optimization features
  5. User can access MLFlow page or see clear "not running" message
  6. All Dashboard interactive elements work without errors
**Plans**: TBD

Plans:
- [ ] 08-01: Fix Workflows page template errors
- [ ] 08-02: Fix Agents page Jinja2 import errors
- [ ] 08-03: Fix MLFlow page 404
- [ ] 08-04: Fix Optimization page filesystem errors
- [ ] 08-05: Test all Dashboard pages and interactive elements
- [ ] 08-06: Add Dashboard integration tests

#### Phase 9: Chat UI Testing & Fixes
**Goal**: Chat UI works end-to-end
**Depends on**: Phase 7
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06
**Success Criteria** (what must be TRUE):
  1. User can generate configs through conversational interface
  2. User can have multi-turn conversations without crashes
  3. User can download generated config files
  4. User can validate generated configs from Chat UI
  5. Chat history persists correctly across sessions
  6. No history format errors in any Chat UI feature
**Plans**: TBD

Plans:
- [ ] 09-01: Fix Chat UI history format handling
- [ ] 09-02: Fix multi-turn conversation crashes
- [ ] 09-03: Fix download and validate button crashes
- [ ] 09-04: Test Chat UI end-to-end workflow
- [ ] 09-05: Add Chat UI integration tests

#### Phase 10: Workflow Execution Testing & Fixes
**Goal**: Workflows run successfully from CLI and UI
**Depends on**: Phase 7, Phase 8
**Requirements**: EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05
**Success Criteria** (what must be TRUE):
  1. User can execute workflows from CLI without crashes
  2. User can execute workflows from Dashboard UI without crashes
  3. Workflow errors are caught and displayed with clear messages
  4. MLFlow tracking records all workflow runs
  5. Workflow state persists across executions
**Plans**: TBD

Plans:
- [ ] 10-01: Test workflow execution from CLI
- [ ] 10-02: Test workflow execution from UI
- [ ] 10-03: Fix any workflow execution errors
- [ ] 10-04: Verify MLFlow tracking works
- [ ] 10-05: Add workflow execution integration tests

#### Phase 11: Integration Tests & Verification
**Goal**: End-to-end user workflows tested and system actually works
**Depends on**: Phase 7, Phase 8, Phase 9, Phase 10
**Requirements**: INT-01, INT-02, INT-03, INT-04, INT-05
**Success Criteria** (what must be TRUE):
  1. User can generate config through Chat UI, execute it, and monitor results
  2. Integration tests use real functionality (not mocked)
  3. Integration tests cover all critical user paths
  4. Tests prevent regression of fixed bugs
  5. All tests pass and system actually works end-to-end
**Plans**: TBD

Plans:
- [ ] 11-01: Create end-to-end integration test for config generation workflow
- [ ] 11-02: Create integration tests for CLI execution workflows
- [ ] 11-03: Create integration tests for Dashboard workflows
- [ ] 11-04: Add regression tests for all fixed bugs
- [ ] 11-05: Run full test suite and verify system actually works

## Progress

**Execution Order:**
Phases execute in numeric order: 7 → 8 → 9 → 10 → 11

| Phase             | Milestone | Plans Complete | Status      | Completed  |
| ----------------- | --------- | -------------- | ----------- | ---------- |
| 1. Core Engine    | v1.0      | 4/4            | Complete    | 2026-02-03 |
| 2. Agent Infrastructure | v1.0      | 6/6            | Complete    | 2026-02-03 |
| 3. Interfaces & Triggers | v1.0      | 6/6            | Complete    | 2026-02-03 |
| 4. Advanced Capabilities | v1.0      | 3/3            | Complete    | 2026-02-04 |
| 5. Foundation & Reliability | v1.1      | 3/3            | Complete    | 2026-02-04 |
| 6. Navigation & Onboarding | v1.1      | 0/3            | Deferred    | - |
| 7. CLI Testing & Fixes | v1.2      | 5/5            | Complete    | 2026-02-05 |
| 8. Dashboard UI Testing & Fixes | v1.2      | 0/6            | Not started | - |
| 9. Chat UI Testing & Fixes | v1.2      | 0/5            | Not started | - |
| 10. Workflow Execution Testing & Fixes | v1.2      | 0/5            | Not started | - |
| 11. Integration Tests & Verification | v1.2      | 0/5            | Not started | - |
