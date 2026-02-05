# Task Numbering Map: T-XXX ↔ Phase-Plan Bidirectional Mapping

**Created**: 2026-02-06
**Purpose**: Unified task numbering system spanning v0.1 through present

---

## Numbering Philosophy

**v0.1 Tasks (T-001 to T-024)**: Original standalone git commits
**Cancelled Tasks (T-025 to T-027)**: Skipped in renumbering
**MLFlow Migration (original T-028)**: Renumbered to T-025
**v1.0+ Work (T-026 onwards)**: Phase-Plan mapped to sequential T-numbers

---

## Renumbering Summary

| Old Number | New Number | Title | Reason |
|------------|------------|-------|--------|
| T-001 to T-024 | T-001 to T-024 | v0.1 Foundation & Core | Unchanged |
| T-025 | ~~cancelled~~ | ~~DSPy Integration~~ | Deferred, skip |
| T-026 | ~~cancelled~~ | ~~Structured Output + DSPy~~ | Deferred, skip |
| T-027 | ~~cancelled~~ | ~~Error Message Improvements~~ | Deferred, skip |
| T-028 | **T-025** | MLFlow 3.9 Migration | Renumbered to fill gap |
| — | **T-026 onwards** | v1.0 Phase-Plans | New sequential numbering |

---

## Complete Task Mapping

### v0.1 Tasks (T-001 to T-025)

| T-Number | Phase/Plan | Title | Completed | Status |
|----------|------------|-------|-----------|--------|
| T-001 | v0.1 Phase 1 | Project Setup | 2026-01-24 | ✅ DONE |
| T-002 | v0.1 Phase 1 | Config Parser | 2026-01-24 | ✅ DONE |
| T-003 | v0.1 Phase 1 | Config Schema | 2026-01-24 | ✅ DONE |
| T-004 | v0.1 Phase 1 | Config Validator | 2026-01-26 | ✅ DONE |
| T-004.5 | v0.1 Phase 1 | Runtime Feature Gating | 2026-01-26 | ✅ DONE |
| T-005 | v0.1 Phase 1 | Type System | 2026-01-26 | ✅ DONE |
| T-006 | v0.1 Phase 1 | State Schema Builder | 2026-01-26 | ✅ DONE |
| T-007 | v0.1 Phase 1 | Output Schema Builder | 2026-01-26 | ✅ DONE |
| T-008 | v0.1 Phase 2 | Tool Registry | 2026-01-25 | ✅ DONE |
| T-009 | v0.1 Phase 2 | LLM Provider | 2026-01-26 | ✅ DONE |
| T-010 | v0.1 Phase 2 | Prompt Template Resolver | 2026-01-26 | ✅ DONE |
| T-011 | v0.1 Phase 2 | Node Executor | 2026-01-27 | ✅ DONE |
| T-012 | v0.1 Phase 2 | Graph Builder | 2026-01-27 | ✅ DONE |
| T-013 | v0.1 Phase 2 | Runtime Executor | 2026-01-27 | ✅ DONE |
| T-014 | v0.1 Phase 3 | CLI Interface | 2026-01-27 | ✅ DONE |
| T-015 | v0.1 Phase 3 | Example Configs | 2026-01-28 | ✅ DONE |
| T-016 | v0.1 Phase 3 | Documentation | 2026-01-28 | ✅ DONE |
| T-017 | v0.1 Phase 3 | Integration Tests | 2026-01-28 | ✅ DONE |
| T-018 | v0.1 Phase 4 | MLFlow Integration Foundation | 2026-01-31 | ✅ DONE |
| T-019 | v0.1 Phase 4 | MLFlow Instrumentation | 2026-01-31 | ✅ DONE |
| T-020 | v0.1 Phase 4 | Cost Tracking & Reporting | 2026-01-31 | ✅ DONE |
| T-021 | v0.1 Phase 4 | Observability Documentation | 2026-01-31 | ✅ DONE |
| T-022 | v0.1 Phase 4 | Docker Artifact Generator | 2026-01-31 | ✅ DONE |
| T-023 | v0.1 Phase 4 | FastAPI Server with Sync/Async | 2026-02-01 | ✅ DONE |
| T-024 | v0.1 Phase 4 | CLI Deploy Command | 2026-02-01 | ✅ DONE |
| ~~T-025~~ | ~~Cancelled~~ | ~~DSPy Integration Test~~ | — | ❌ Cancelled |
| ~~T-026~~ | ~~Cancelled~~ | ~~Structured Output + DSPy~~ | — | ❌ Cancelled |
| ~~T-027~~ | ~~Cancelled~~ | ~~Error Message Improvements~~ | — | ❌ Cancelled |
| **T-025** | **v0.1 (was T-028)** | **MLFlow 3.9 Migration** | **2026-02-02** | **✅ DONE** |

---

### v1.0 Phase 1: Core Engine (T-026 to T-029)

| T-Number | Phase-Plan | Title | Requirements | Completed | Status |
|----------|------------|-------|-------------|-----------|--------|
| T-026 | 01-01 | Storage Abstraction Layer | ARCH-04 | 2026-02-03 | ✅ DONE |
| T-027 | 01-02 | Multi-Provider LLM Support | RT-05, RT-06 | 2026-02-03 | ✅ DONE |
| T-028 | 01-03 | Advanced Control Flow | RT-01, RT-02, RT-03 | 2026-02-03 | ✅ DONE |
| T-029 | 01-04 | Storage-Executor Integration | ARCH-04, OBS-04 | 2026-02-03 | ✅ DONE |

**Phase 1 Requirements Delivered**:
- RT-01: Conditional routing ✓
- RT-02: Loop execution ✓
- RT-03: Parallel execution ✓
- RT-05: Multi-LLM providers ✓
- RT-06: Local models via Ollama ✓
- ARCH-04: Pluggable storage backend ✓
- OBS-04: Execution traces ✓

---

### v1.0 Phase 2: Agent Infrastructure (T-030 to T-035)

| T-Number | Phase-Plan | Title | Requirements | Completed | Status |
|----------|------------|-------|-------------|-----------|--------|
| T-030 | 02-01A | Agent Registry Storage & Server | ARCH-01, ARCH-02, ARCH-03 | 2026-02-03 | ✅ DONE |
| T-031 | 02-01B | Registry Client + Generator Integration | ARCH-01, ARCH-02 | 2026-02-03 | ✅ DONE |
| T-032 | 02-01C | CLI Integration | ARCH-01 | 2026-02-03 | ✅ DONE |
| T-033 | 02-02A | Multi-Provider Cost Tracking | OBS-02 | 2026-02-03 | ✅ DONE |
| T-034 | 02-02B | Performance Profiling | OBS-03 | 2026-02-03 | ✅ DONE |
| T-035 | 02-02C | CLI Observability Commands | OBS-02, OBS-03 | 2026-02-03 | ✅ DONE |

**Phase 2 Requirements Delivered**:
- ARCH-01: Minimal agent containers ✓
- ARCH-02: Bidirectional registration (partial) ✓
- ARCH-03: Agent registry with heartbeat/TTL ✓
- OBS-02: Multi-provider cost tracking ✓
- OBS-03: Performance profiling ✓

---

### v1.0 Phase 3: Interfaces & Triggers (T-036 to T-041)

| T-Number | Phase-Plan | Title | Requirements | Completed | Status |
|----------|------------|-------|-------------|-----------|--------|
| T-036 | 03-01 | Chat UI for Config Generation | UI-01, UI-02, ARCH-05 | 2026-02-03 | ✅ DONE |
| T-037 | 03-02 | Orchestration Dashboard | UI-03, UI-04, UI-05, UI-06 | 2026-02-03 | ✅ DONE |
| T-038 | 03-03 | Generic Webhook Infrastructure | INT-03 | 2026-02-03 | ✅ DONE |
| T-039 | 03-03B | Platform Webhook Integrations | INT-01, INT-02 | 2026-02-03 | ✅ DONE |
| T-040 | 03-04 | Workflow Restart Implementation | - | 2026-02-03 | ✅ DONE |
| T-041 | 03-05 | Test Fixture Unpacking Fix | - | 2026-02-03 | ✅ DONE |

**Phase 3 Requirements Delivered**:
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

---

### v1.0 Phase 4: Advanced Capabilities (T-042 to T-044)

| T-Number | Phase-Plan | Title | Requirements | Completed | Status |
|----------|------------|-------|-------------|-----------|--------|
| T-042 | 04-01 | Code Execution Sandboxes | RT-04 | 2026-02-04 | ✅ DONE |
| T-043 | 04-02 | Long-Term Memory and Tool Ecosystem | RT-07, RT-08, ARCH-06 | 2026-02-04 | ✅ DONE |
| T-044 | 04-03 | MLFlow Optimization | OBS-01 | 2026-02-04 | ✅ DONE |

**Phase 4 Requirements Delivered**:
- RT-04: Sandbox code execution ✓
- RT-07: Long-term memory ✓
- RT-08: Pre-built tools ✓
- OBS-01: MLFlow optimization ✓
- ARCH-06: Memory backend ✓

---

### v1.1 Phase 5: Foundation & Reliability (T-045 to T-047)

| T-Number | Phase-Plan | Title | Completed | Status |
|----------|------------|-------|-----------|--------|
| T-045 | 05-01 | Single-Command Startup | 2026-02-04 | ✅ DONE |
| T-046 | 05-02 | Database Auto-Initialization | 2026-02-04 | ✅ DONE |
| T-047 | 05-03 | Status Dashboard | 2026-02-04 | ✅ DONE |

**Quick Tasks (sub-tasks of Phase 5)**:
- quick-001: Fix Windows multiprocessing UI (part of T-045)
- quick-002: Fix lambda pickle issue (part of T-045)
- quick-003: Use ServiceSpec args (part of T-045)
- quick-004: Fix bound method pickle (part of T-045)
- quick-005: Add process debug logging (part of T-045)
- quick-006: Add uvicorn import (part of T-046)
- quick-007: Add uvicorn dependency (part of T-046)
- quick-008: Add dotenv loading (part of T-046)

---

### v1.1 Phase 6: Deferred to v1.3

**Plans**: 06-01, 06-02, 06-03
**Status**: Deferred, not executed in v1.1

---

### v1.2 Phase 7: CLI Testing & Fixes (T-048 to T-052)

| T-Number | Phase-Plan | Title | Completed | Status |
|----------|------------|-------|-----------|--------|
| T-048 | 07-01 | CLI Run Command Testing | 2026-02-05 | ✅ DONE |
| T-049 | 07-02 | CLI Validate Command Testing | 2026-02-05 | ✅ DONE |
| T-050 | 07-03 | CLI Deploy Command Testing | 2026-02-05 | ✅ DONE |
| T-051 | 07-04 | CLI UI Command Integration Testing | 2026-02-05 | ✅ DONE |
| T-052 | 07-05 | CLI Comprehensive Integration Testing | 2026-02-05 | ✅ DONE |

---

### v1.2 Phase 8: Dashboard UI Testing & Fixes (T-053 to T-058)

| T-Number | Phase-Plan | Title | Completed | Status |
|----------|------------|-------|-----------|--------|
| T-053 | 08-01 | Template Macros and Global Helpers | 2026-02-05 | ✅ DONE |
| T-054 | 08-02 | Agents Page Helper Function Renaming | 2026-02-05 | ✅ DONE |
| T-055 | 08-03 | MLFlow 404 Fix | 2026-02-05 | ✅ DONE |
| T-056 | 08-04 | Optimization Page MLFlow Error Handling | 2026-02-05 | ✅ DONE |
| T-057 | 08-05 | Dashboard E2E Testing | 2026-02-05 | ✅ DONE |
| T-058 | 08-06 | Dashboard Integration Testing | 2026-02-05 | ✅ DONE |

---

### v1.2 Phase 9-11: In Progress (T-059 onwards)

**Status**: In progress, not yet complete

---

## Reverse Lookup: Phase-Plan → T-Number

### Phase 1: Core Engine
- 01-01 → T-026
- 01-02 → T-027
- 01-03 → T-028
- 01-04 → T-029

### Phase 2: Agent Infrastructure
- 02-01A → T-030
- 02-01B → T-031
- 02-01C → T-032
- 02-02A → T-033
- 02-02B → T-034
- 02-02C → T-035

### Phase 3: Interfaces & Triggers
- 03-01 → T-036
- 03-02 → T-037
- 03-03 → T-038
- 03-03B → T-039
- 03-04 → T-040
- 03-05 → T-041

### Phase 4: Advanced Capabilities
- 04-01 → T-042
- 04-02 → T-043
- 04-03 → T-044

### Phase 5: Foundation & Reliability
- 05-01 → T-045
- 05-02 → T-046
- 05-03 → T-047

### Phase 6: Deferred
- 06-01 → (deferred to v1.3)
- 06-02 → (deferred to v1.3)
- 06-03 → (deferred to v1.3)

### Phase 7: CLI Testing
- 07-01 → T-048
- 07-02 → T-049
- 07-03 → T-050
- 07-04 → T-051
- 07-05 → T-052

### Phase 8: Dashboard UI Testing
- 08-01 → T-053
- 08-02 → T-054
- 08-03 → T-055
- 08-04 → T-056
- 08-05 → T-057
- 08-06 → T-058

---

## Requirement ID → Task Mapping

### Runtime Requirements (RT-XX)
- RT-01 → T-028 (01-03)
- RT-02 → T-028 (01-03)
- RT-03 → T-028 (01-03)
- RT-04 → T-042 (04-01)
- RT-05 → T-027 (01-02)
- RT-06 → T-027 (01-02)
- RT-07 → T-043 (04-02)
- RT-08 → T-043 (04-02)

### Observability Requirements (OBS-XX)
- OBS-01 → T-044 (04-03)
- OBS-02 → T-033 (02-02A)
- OBS-03 → T-034 (02-02B)
- OBS-04 → T-029 (01-04)

### UI Requirements (UI-XX)
- UI-01 → T-036 (03-01)
- UI-02 → T-036 (03-01)
- UI-03 → T-037 (03-02)
- UI-04 → T-037 (03-02)
- UI-05 → T-037 (03-02)
- UI-06 → T-037 (03-02)

### Architecture Requirements (ARCH-XX)
- ARCH-01 → T-030 (02-01A)
- ARCH-02 → T-030 (02-01A)
- ARCH-03 → T-030 (02-01A)
- ARCH-04 → T-026 (01-01)
- ARCH-05 → T-036 (03-01)
- ARCH-06 → T-043 (04-02)

### Integration Requirements (INT-XX)
- INT-01 → T-039 (03-03B)
- INT-02 → T-039 (03-03B)
- INT-03 → T-038 (03-03)

---

## Usage Guide

### To find task by Phase-Plan:
1. Look up phase in "Reverse Lookup" section
2. Find plan number (e.g., 02-01A)
3. Get corresponding T-number (e.g., T-030)

### To find Phase-Plan by T-Number:
1. Look up T-number in appropriate phase section
2. Find corresponding Phase-Plan identifier

### To find tasks delivering a requirement:
1. Look up requirement ID in "Requirement ID → Task Mapping"
2. Get all T-numbers that deliver that requirement

---

## Statistics

**Total Tasks (v0.1 to present)**: 58 (T-001 to T-058)
- v0.1: 25 tasks (T-001 to T-025, includes MLFlow migration)
- v1.0: 19 tasks (T-026 to T-044)
- v1.1: 3 tasks (T-045 to T-047)
- v1.2: 11 tasks (T-048 to T-058)

**Cancelled**: 3 tasks (original T-025 to T-027)
**Deferred**: 3 plans (Phase 6: 06-01 to 06-03)
**In Progress**: T-059 onwards (Phase 9+)
