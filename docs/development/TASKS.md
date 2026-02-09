# Requirements: Configurable Agent Orchestration Platform

**Version**: v1.0 Shipped (2026-02-04)
**Last Updated**: 2026-02-06

---

## Active Tasks

### CL-003: Codebase Cleanup, Testing, and Verification

**Status**: IN PROGRESS
**Started**: 2026-02-07
**Priority**: HIGH

**Summary**: Systematic testing of all 12 test configs, fixing bugs discovered during testing.

**Completed**:
- All 12 test configs validated and executing successfully
- Fixed INVALID_CONCURRENT_GRAPH_UPDATE (Annotated reducers in state_builder.py)
- Fixed test config YAML syntax (routes, loop blocks)
- Replaced broken MAP/Send parallel with fork-join parallel (10-phase implementation)
- Config 07 and 12 fully rewritten and verified

**Remaining Bug Fixes** (discovered during CL-003):

| ID | Issue | Priority | Status |
|----|-------|----------|--------|
| BF-001 | Storage backend tuple unpacking (`too many values to unpack`) | HIGH | ✅ DONE |
| BF-002 | Tool execution — no agent loop in provider.py | CRITICAL | ✅ DONE |
| BF-003 | Memory persistence — not persisting between runs | MEDIUM | ✅ DONE |
| BF-004 | MLFlow cost summary — parsing, model attribution, GenAI view | MEDIUM | ✅ DONE |
| BF-005 | Pre-existing test failures (dict-vs-Pydantic, deploy artifacts) | MEDIUM | ✅ DONE |
| BF-006 | ChatLiteLLM deprecation migration (`langchain-litellm`) | LOW | ✅ DONE |

**Details**: [CL-003 Test Findings](implementation_logs/phase_5_cleanup_and_verification/CL-003_TEST_FINDINGS.md)

---

### CL-002: Documentation Index and Dead Link Cleanup

**Status**: IN PROGRESS (Project state still broken, further cleanup needed)
**Started**: 2026-02-06

**Summary**: Created docs/README.md index and updated references to non-existent documentation.

**Actions Completed**:
- ✅ Created docs/README.md as comprehensive documentation index
- ✅ Updated CHANGELOG.md to remove .planning/ references and add broken state warning
- ✅ Updated README.md with documentation index link
- ✅ Updated CLAUDE.md with documentation structure information
- ✅ Updated docs/development/TASKS.md to remove .planning/ references
- ✅ Updated CONTEXT.md with broken state declaration

**IMPORTANT**: Project state remains BROKEN. Further cleanup and verification phase
needed before this can be marked complete.

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

| Requirement | Phase | Status | Plan |
|-------------|-------|--------|------|
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

## v2 Requirements (Deferred)

The following requirements are tracked but not in v1.0 scope:

### Self-Optimization

- **SELF-01**: Agents can spawn and organize themselves based on workflow needs (auto-scaling runtime)
- **SELF-02**: System automatically optimizes agent configurations based on performance history

### Enterprise Scale

- **ENT-01**: Kubernetes deployment with auto-scaling, Helm charts, and cloud storage backends
- **ENT-02**: Multi-tenancy with tenant isolation and RBAC
- **ENT-03**: OpenTelemetry integration for enterprise observability platforms

### Extended Tools

- **TOOL-01**: Full LangChain tool registry (500+ tools) with dynamic discovery
- **TOOL-02**: Visual workflow builder (drag-and-drop node editor with code export)

### Advanced Memory

- **MEM-01**: Contextual/agentic memory that learns and evolves beyond RAG patterns
- **MEM-02**: Agent Protocol support (A2A, MCP) for cross-platform interoperability
- **MEM-03**: Memory persistence revisit — optimize KV store, evaluate vector/semantic memory, add memory re-use patterns across agents, consider Mem0/LightRAG integration, optimize extraction cost (batch, async, selective extraction)

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
| ARCH-02 | Bidirectional registration | 2 | Partial | ADR-020 |
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
