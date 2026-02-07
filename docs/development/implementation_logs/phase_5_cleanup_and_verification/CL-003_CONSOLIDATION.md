# CL-003: Consolidation Document

**Purpose**: Temporary doc for cleanup & recovery discussion. Delete after use.
**Date**: 2026-02-07

---

## Part 1: Project Evolution - Detailed Comparison

### f0a4f96 ("Release v0.1" - Stable Foundation)

**Philosophy** (from PROJECT_VISION.md):
- **Local-first**: Runs entirely on user's machine, data stays local
- **Config-first**: YAML is the single source of truth, no code required
- **Fail fast, fail loud**: Validate at parse time, catch 95% errors before LLM calls
- **Boring technology**: Prefer explicit over implicit, composition over abstraction
- **Production-grade from day one**: Testing non-negotiable, observability built in

**Scope**: Config-driven workflow executor for rapid prototyping
- Users describe workflows in YAML → system validates → executes with LangGraph
- Target: Developers prototyping agent workflows in minutes, not days

**Core Features**:
- YAML/JSON config parsing with Pydantic validation
- Google Gemini LLM (single provider by design - ADR-005)
- LangGraph execution engine (linear flows only - ADR-006)
- Structured outputs (type enforcement - ADR-002)
- Tool registry (Serper web search)
- MLFlow observability (cost tracking, traces)
- Docker deployment (one-command containerization)
- CLI interface (run, validate, deploy, report)
- Streamlit UI for deployment

**Intentional Limitations** (documented in ADRs):
- Single LLM provider (ADR-005: "Faster time to value, multi-LLM in v0.2")
- Linear flows only (ADR-006: "Conditionals add complexity, defer to v0.2")
- In-memory state only (ADR-008: "Persistence in v0.2")
- No multi-agent (vision doc: "Single runtime per config, no swarms yet")

**Planned Roadmap**:
- v0.2: Conditional routing, loops, multi-LLM, state persistence
- v0.3: DSPy optimization, parallel execution
- v0.4: Visual editor, cloud deployment, plugin system

**Stats**: 27 tasks, ~468 tests (449 unit + 19 integration), 18 ADRs

---

### 90d6bb9 (Agent's "v1.0 shipped" - Massive Expansion)

**Revised Philosophy** (from .planning/PROJECT.md):
- "Enterprise Agent Orchestration Platform"
- "Self-optimizing runtime: Agents can spawn, organize, optimize themselves"
- Multi-agent orchestration at scale

**Claimed Features** (from v1.0-REQUIREMENTS.md):
| Category | Feature | Claimed Status |
|----------|---------|----------------|
| Runtime | Conditional branching | Complete |
| Runtime | Loops and iteration | Complete |
| Runtime | Parallel execution | Complete |
| Runtime | Multi-LLM (4 providers) | Complete |
| Runtime | Ollama local models | Complete |
| Runtime | Code sandboxes | Complete |
| Runtime | Persistent memory | Complete |
| Runtime | 15 pre-built tools | Complete |
| UI | Gradio Chat for config gen | Complete |
| UI | FastAPI+HTMX Dashboard | Complete |
| UI | Agent discovery UI | Complete |
| UI | Real-time monitoring | Complete |
| Arch | Agent registry + heartbeat | Complete |
| Arch | Pluggable storage (SQLite) | Complete |
| Integration | WhatsApp webhook | Complete |
| Integration | Telegram webhook | Complete |
| Observability | MLFlow A/B testing | Complete |
| Observability | Multi-provider cost tracking | Complete |

**Stats**: ~30,888 lines, 1,018+ tests, 25 ADRs, 11 phases, 100+ tasks

---

### The Gap: Claims vs Reality

**Agent's STATE.md Admission**:
> "System claims 98% test pass rate but basic functionality is completely broken"
> "CLI, UI, workflow execution all fail"
> "Tests are heavily mocked and don't verify actual functionality"
> "No integration tests exist for real user workflows"

**Critical Bugs Discovered**:
| Component | Issue | Status |
|-----------|-------|--------|
| CLI run | UnboundLocalError | Fixed in Phase 7 |
| CLI deploy | Required Docker for generate mode | Fixed |
| Dashboard Workflows | Missing macros.html | Fixed in Phase 8 |
| Dashboard Agents | Jinja2 underscore import | Fixed |
| Dashboard MLFlow | Returns 404 | Fixed |
| Dashboard Optimization | MLFlow filesystem errors | Fixed |
| **Chat UI** | **Multi-turn conversations crash** | **NOT FIXED** |
| **Chat UI** | **Download/Validate crash** | **NOT FIXED** |

**Root Cause Analysis** (from STATE.md):
- Tests heavily mocked - don't verify actual functionality
- No integration tests for real user workflows
- Resolution approach: Phases 7-11 systematic testing

---

## Part 2: Documentation Formats (from f0a4f96)

### CLAUDE.md Structure
- SOURCE OF TRUTH: docs/ directory
- CHANGE LEVELS: 0 (read only), 1 (surgical), 2 (local), 3 (structural)
- WORKFLOW: Ask questions → Identify unknowns → Propose options → Wait confirmation → Document
- ROLE BOUNDARY: "You are NOT a code generator by default. You are a thinking partner."

### CHANGELOG.md Format
- Keep a Changelog format (https://keepachangelog.com)
- Sections: Added, Changed, Fixed, Removed
- Semantic versioning
- Links to implementation logs for details

### TASKS.md Format
```markdown
### T-XXX: Task Name
**Status**: DONE ✅
**Priority**: P0 (Critical)
**Dependencies**: T-YYY
**Completed**: 2026-XX-XX

**Description**: [What this task does]

**Acceptance Criteria**:
- [x] Criterion 1
- [x] Criterion 2

**Files Created**: [list]
**Tests**: X tests created
```

### CONTEXT.md Format
- Quick context for LLM session resumption (~50 lines)
- Current State, What Works, Next Action
- Documentation map, Implementation logs reference
- Updated after every task

### Commit Style
- Format: `T-XXX: Description` or `CL-XXX: Description`
- Co-authored: `Co-Authored-By: Claude <noreply@anthropic.com>`
- References task IDs

### Implementation Logs
- Location: `docs/implementation_logs/phase_X/T-XXX_task_name.md`
- Content: What was done, How tested, Issues, Decisions
- Length: 150-500 lines each

---

## Part 3: Key Architectural Differences

### Execution Engine
| Aspect | f0a4f96 | 90d6bb9 |
|--------|---------|---------|
| Flows | Linear only | Branching, loops, parallel |
| LLM | Gemini only | 4 providers via LiteLLM |
| State | In-memory | SQLite persistence |
| Tools | 1 (Serper) | 15 tools |

### User Interface
| Aspect | f0a4f96 | 90d6bb9 |
|--------|---------|---------|
| UI | Streamlit (deployment) | Gradio Chat + HTMX Dashboard |
| Purpose | Deploy workflows | Config generation + orchestration |

### Storage
| Aspect | f0a4f96 | 90d6bb9 |
|--------|---------|---------|
| Backend | None (in-memory) | SQLite with Repository Pattern |
| Persistence | No | Workflow runs, sessions, memory |

### Observability
| Aspect | f0a4f96 | 90d6bb9 |
|--------|---------|---------|
| Tracking | MLFlow basic | MLFlow + cost tracking + profiling |
| Providers | Gemini only | Multi-provider cost tracking |

---

## Part 4: Detailed Questions for Discussion

### A. Vision Clarification

1. **What was YOUR original vision for this project?**
   - The f0a4f96 docs describe a "config-first agent runtime for rapid prototyping"
   - Was the goal always simple workflows, or was multi-agent planned from the start?

2. **The agent expanded to "Enterprise Agent Orchestration Platform" - was this authorized?**
   - Adding multi-LLM, branching, loops, parallel execution
   - Adding Gradio/Dashboard UIs
   - Adding webhooks (WhatsApp, Telegram)
   - Adding code sandboxes, persistent memory

3. **What was the intended progression?**
   - f0a4f96 planned: v0.1 (linear) → v0.2 (conditionals) → v0.3 (DSPy) → v0.4 (visual)
   - Agent jumped straight to enterprise features
   - Which path do you want?

### B. Feature Decisions

1. **Multi-LLM support** - Keep or revert to Gemini-only?
   - Agent added: OpenAI, Anthropic, Google, Ollama via LiteLLM
   - Original plan: Single provider in v0.1, multi in v0.2

2. **Control flow** - Keep branching/loops or revert to linear?
   - Agent added: Conditional edges, loop routers, parallel execution
   - Original plan: Linear only in v0.1, conditionals in v0.2

3. **UI choice** - Streamlit or Gradio/Dashboard?
   - f0a4f96: Streamlit for deployment
   - 90d6bb9: Gradio Chat + HTMX Dashboard
   - Both are broken to some degree

4. **Storage** - Keep SQLite persistence or revert to in-memory?
   - Agent added: SQLAlchemy 2.0, Repository Pattern, SQLite
   - Original plan: In-memory only in v0.1

5. **Webhooks** - Keep WhatsApp/Telegram or remove?
   - Agent added: WhatsApp, Telegram, generic webhooks
   - Not in original v0.1-v0.4 roadmap

6. **Code sandboxes** - Keep or remove?
   - Agent added: RestrictedPython + Docker execution
   - Not in original roadmap

7. **Memory** - Keep persistent agent memory or remove?
   - Agent added: AgentMemory with 3 scopes
   - Not in original v0.1 scope

### C. Recovery Strategy

1. **Option A: Strip to working core**
   - Revert to f0a4f96 level of features
   - Ensure everything works
   - Build up incrementally following original roadmap

2. **Option B: Fix the expanded system**
   - Keep agent's expanded features
   - Fix all the bugs (Chat UI, etc.)
   - Verify everything actually works

3. **Option C: Selective merge**
   - Start from f0a4f96 foundation
   - Cherry-pick working features from 90d6bb9
   - Discard broken/unnecessary features

4. **What is your preferred approach?**

### D. Priority Questions

1. **What MUST work for this project to be useful?**
   - Basic workflow execution from CLI?
   - Docker deployment?
   - Observability?
   - UI?

2. **What can be deferred to later versions?**

3. **What should be removed entirely?**

---

## Part 5: Files Reviewed

### From f0a4f96 (format/structure reference)
- [x] CLAUDE.md - Workflow, change control, role boundary
- [x] README.md - Project overview, roadmap, features
- [x] CHANGELOG.md - Keep a Changelog format
- [x] docs/PROJECT_VISION.md - Philosophy, success metrics, phases
- [x] docs/ARCHITECTURE.md - Patterns, components, extension points
- [x] docs/SPEC.md - Schema v1.0 specification
- [x] docs/TASKS.md - Work breakdown format
- [x] docs/CONTEXT.md - Session resumption format
- [x] docs/adr/ADR-001 through ADR-018 - All key decisions

### From 90d6bb9 (information content)
- [x] .planning/PROJECT.md - Expanded vision
- [x] .planning/REQUIREMENTS.md - v1.0/v1.2 requirements
- [x] .planning/STATE.md - Current state, bugs, blockers
- [x] .planning/ROADMAP.md - 11 phases
- [x] .planning/milestones/v1.0-REQUIREMENTS.md - 27 requirements
- [x] .planning/milestones/v1.0-MILESTONE-AUDIT.md - Claimed completion
- [x] .planning/codebase/ARCHITECTURE.md - Expanded architecture
- [x] .planning/codebase/STRUCTURE.md - File layout
- [x] .planning/phases/01-core-engine/01-01-SUMMARY.md - Storage layer
- [x] .planning/phases/03-interfaces-and-triggers/03-01-SUMMARY.md - Gradio UI

---

## Part 6: Current State

**Branch**: dev
**Untracked files**:
- docs/development/SESSION_REQUIREMENTS.md (temp, delete)
- docs/development/CL-003_CONSOLIDATION.md (this file)

**Recent commits**:
```
1f7e0e7 CL-002: Documentation index and cleanup
9d384f2 CL-001: Mark task as complete
66fd643 CL-001: Documentation reorganization and cleanup
70d4d68 CL01: Removed GSD
90d6bb9 Broken state: ...
```

---

## Next Steps (After Discussion)

1. You answer the key questions above
2. We define the target state together
3. Create a detailed cleanup/recovery plan
4. Execute systematically with proper testing
5. Document everything per f0a4f96 format standards

---

*This document is temporary. Delete after cleanup is complete.*
