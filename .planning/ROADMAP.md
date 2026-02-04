# Roadmap: Configurable Agent Orchestration Platform

## Overview

Local-first, config-driven agent orchestration platform with multi-LLM support, advanced control flow, complete observability, and zero cloud lock-in.

## Milestones

- ✅ **v1.0 Foundation** — Phases 1-4 (shipped 2026-02-04) — [View details](milestones/v1.0-ROADMAP.md)
- 🚧 **v1.1 Core UX Polish** — Phases 5-6 (in progress)

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

### 🚧 v1.1 Core UX Polish (In Progress)

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
**Plans**: TBD

Plans:
- [ ] 05-01: Single-command startup with ProcessManager
- [ ] 05-02: Auto-initialization with graceful degradation
- [ ] 05-03: Status dashboard and error handling

#### Phase 6: Navigation & Onboarding
**Goal**: Users can discover features quickly and navigate intuitively, with clear guidance on what to do next.
**Depends on**: Phase 5
**Requirements**: ONBOARD-01, NAV-01, NAV-02
**Success Criteria** (what must be TRUE):
  1. User can open command palette via Cmd/Ctrl+K and fuzzy search workflows, agents, templates
  2. User can filter navigation lists by typing in sideboards
  3. Empty states guide users to clear next actions ("Create workflow" or "Browse templates")
**Plans**: TBD

Plans:
- [ ] 06-01: Command palette (Cmd/Ctrl+K) with fuzzy search
- [ ] 06-02: Quick search in navigation sideboards
- [ ] 06-03: Empty state guidance and onboarding

## Progress

**Execution Order:**
Phases execute in numeric order: 5 → 6

| Phase             | Milestone | Plans Complete | Status      | Completed  |
| ----------------- | --------- | -------------- | ----------- | ---------- |
| 1. Core Engine    | v1.0      | 4/4            | Complete    | 2026-02-03 |
| 2. Agent Infrastructure | v1.0      | 6/6            | Complete    | 2026-02-03 |
| 3. Interfaces & Triggers | v1.0      | 6/6            | Complete    | 2026-02-03 |
| 4. Advanced Capabilities | v1.0      | 3/3            | Complete    | 2026-02-04 |
| 5. Foundation & Reliability | v1.1      | 0/3            | Not started | - |
| 6. Navigation & Onboarding | v1.1      | 0/3            | Not started | - |
