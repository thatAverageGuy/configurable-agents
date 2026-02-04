# Configurable Agents - Enterprise Agent Orchestration Platform

## What This Is

A local-first, config-driven agent orchestration platform that enables building production-grade multi-agent systems from laptop to enterprise scale. Users describe agent workflows through conversational UI or YAML configs, which generate self-optimizing, fully observable agent systems that run anywhere - from a solo developer's laptop to Kubernetes clusters - without cloud lock-in.

## Core Value

The **combination** of four pillars makes this unique - remove any one and it becomes generic:

1. **Self-optimizing runtime**: Agents can spawn, organize, and optimize themselves based on workflow needs
2. **Local-first orchestration**: Complete control and privacy - no cloud dependencies, works offline
3. **Config-driven everything**: Complex multi-agent systems defined through YAML or conversational interface, no code required
4. **Observable by design**: MLFlow integration making every agent action trackable, debuggable, and improvable

This is the only platform that delivers enterprise-grade agent orchestration with zero cloud lock-in, config-first simplicity, and production observability from day one.

## Current Milestone: v1.2 Integration Testing & Critical Bug Fixes

**Goal:** Make the system actually work through comprehensive testing and fixing all critical bugs.

**Problem:** System claims 98% test pass rate but basic functionality is completely broken (CLI, UI, workflow execution all fail).

**Target outcomes:**
- All CLI commands work without errors
- All Dashboard pages load and function correctly
- Chat UI works end-to-end (config generation, multi-turn, download, validate)
- Workflows run successfully from CLI
- Workflows run successfully from UI
- Integration tests prevent regression (real tests, not mocks)

---

## Current State

**Shipped:** v1.0 Foundation (2026-02-04)

A production-ready local-first agent orchestration platform with multi-LLM support, advanced control flow, complete observability, and zero cloud lock-in.

**Capabilities Delivered:**
- Multi-LLM support across 4 providers (OpenAI, Anthropic, Google, Ollama) with unified cost tracking
- Advanced control flow (conditional branching, loops, parallel execution) via LangGraph
- Complete observability stack (MLFlow integration, cost tracking, performance profiling, execution traces)
- User interfaces (Gradio Chat UI for config generation, FastAPI + HTMX orchestration dashboard)
- External integrations (WhatsApp, Telegram, and generic webhook triggers)
- Advanced capabilities (code sandboxes with RestrictedPython + Docker, persistent memory, 15 pre-built tools, A/B optimization)

**Codebase:**
- ~30,888 lines of Python code
- 1,018+ tests with 98%+ pass rate
- 4 phases, 19 plans, ~100+ tasks

## Next Milestone Goals

TBD — Run `/gsd:new-milestone` to define v1.1 objectives

---

### Validated

**v0.1 Foundation (Pre-v1.0):**
- ✓ Linear workflow execution
- ✓ YAML config parsing and validation
- ✓ Google Gemini LLM integration
- ✓ MLFlow tracking (basic)
- ✓ Docker deployment (single workflow)
- ✓ CLI interface (run, validate, deploy)
- ✓ Serper web search tool
- ✓ Pydantic schema validation
- ✓ LangGraph execution engine

**v1.0 Foundation (Shipped 2026-02-04):**

**Runtime Capabilities:**
- ✓ Advanced control flow (branching based on conditions) — v1.0
- ✓ Loop support (retry logic, iteration over data) — v1.0
- ✓ Parallel node execution (concurrent agent operations) — v1.0
- ✓ Code execution sandboxes (RestrictedPython with Docker extensibility) — v1.0
- ✓ Multi-LLM provider support (OpenAI, Anthropic, Google, Ollama) — v1.0
- ✓ Local model support (Ollama integration for privacy-first deployments) — v1.0
- ✓ Long-term memory per node/agent/workflow (persistent context across executions) — v1.0
- ✓ Common LangChain tools subset (search, APIs, data processing - 15 tools) — v1.0

**Observability:**
- ✓ Full MLFlow production features (prompt optimization, evaluations, A/B testing) — v1.0
- ✓ Enhanced cost tracking with multi-provider support — v1.0
- ✓ Performance profiling and bottleneck detection — v1.0
- ✓ Workflow execution traces with detailed metrics — v1.0

**User Interfaces:**
- ✓ Chat UI for config generation (Gradio-based conversational interface) — v1.0
- ✓ Session persistence in Chat UI (conversation history, config iterations) — v1.0
- ✓ Orchestration UI for runtime management (FastAPI + HTMX dashboard) — v1.0
- ✓ Agent discovery and registration interface (agent-initiated) — v1.0
- ✓ MLFlow UI embedded in orchestration dashboard (iframe integration) — v1.0
- ✓ Real-time agent monitoring and control (status, logs, metrics streaming) — v1.0

**Architecture:**
- ✓ Minimal agent container design (decouple MLFlow UI from agents) — v1.0
- ⚠ Bidirectional agent registration (agent-initiated complete, orchestrator-initiated deferred) — v1.0 partial
- ✓ Agent registry with heartbeat/TTL (track active agents) — v1.0
- ✓ Storage abstraction layer (SQLite default, pluggable for Postgres/Redis) — v1.0
- ✓ Session storage for Chat UI (conversation history persistence) — v1.0
- ✓ Long-term memory storage backend (per-agent context storage) — v1.0

**Integrations:**
- ✓ WhatsApp webhook integration (trigger workflows from WhatsApp messages) — v1.0
- ✓ Telegram bot integration (trigger workflows from Telegram) — v1.0
- ✓ External trigger API (generic webhook endpoint for third-party integrations) — v1.0

### Active

<!-- Current milestone scope: v1.2 Integration Testing & Critical Bug Fixes -->

- [ ] **TEST-01**: CLI commands work (run, validate, deploy, ui, etc.)
- [ ] **TEST-02**: Dashboard UI pages load and function (workflows, agents, experiments, optimization, MLFlow)
- [ ] **TEST-03**: Chat UI works end-to-end (config generation, multi-turn conversations, download, validate)
- [ ] **TEST-04**: Workflows execute from CLI without errors
- [ ] **TEST-05**: Workflows execute from UI without errors
- [ ] **TEST-06**: Integration tests cover critical user workflows (not mocked)
- [ ] **TEST-07**: All tests pass and system actually works

### Out of Scope

**Deferred to v2+:**
- Self-optimizing agents (runtime auto-spawn and optimization) — v1 focuses on explicit configuration; auto-optimization adds significant complexity
- Kubernetes optimization and enterprise refactor — current Docker deployment sufficient for v1; K8s optimizations needed only at scale
- Full LangChain tool registry (500+ tools) — start with common subset (10-20 tools); full registry in v2 based on demand
- Visual workflow builder — config-first philosophy maintained; no drag-drop node editors

**Explicitly excluded:**
- Cloud-hosted service — violates local-first principle; users can deploy to their own cloud but no managed service
- React/JS-based UI frameworks — heavyweight, complex, violates lightweight principle; using Gradio + HTMX instead
- Agent marketplace — premature for v1; focus on core platform capabilities first
- Multi-tenancy — v1 targets single user/team; enterprise multi-tenancy in later versions

## Context

**Current State (v1.2 - Testing Required):**
System is essentially broken despite claimed 98% test pass rate.

**Critical Bugs Discovered (2026-02-05):**
- CLI `run` command: UnboundLocalError (FIXED)
- Chat UI: Multi-turn conversations crash (history format wrong)
- Chat UI: Download/Validate buttons crash (same history issue)
- Dashboard: Workflows page crashes (missing macros.html)
- Dashboard: Agents page crashes (Jinja2 underscore import)
- Dashboard: MLFlow page returns 404
- Dashboard: Optimization page shows MLFlow filesystem errors

**Root Cause:**
Tests are heavily mocked and don't verify actual functionality. No integration tests exist for real user workflows.

**Technical Stack:**
- Python 3.10+ runtime
- LangGraph for execution engine
- Pydantic 2.0+ for validation
- MLFlow 3.9+ for observability
- FastAPI for API servers
- Gradio for Chat UI
- HTMX for dashboard
- LiteLLM for multi-provider support
- SQLAlchemy 2.0 for storage
- Docker for containerization
- RestrictedPython for code sandboxing

**Target Users:**
1. **Solo developers/researchers** - Need powerful local tools for agent experimentation without cloud costs or complexity
2. **Small teams (2-10 people)** - Need shared infrastructure for collaborative agent development with local-first control
3. **Enterprises** - Need production-grade scale, security, compliance, and deployment flexibility

**Evolution Goal:**
Transform from a simple linear workflow runner (v0.1) into a full-featured local-first agent orchestration platform that competes with LangGraph Platform and LangChain Studio while maintaining zero cloud lock-in.

**User Workflow Vision:**
1. User opens Chat UI, describes desired agent workflow in natural language
2. System generates optimized YAML config through conversational iteration
3. User approves config and triggers execution
4. Orchestration UI shows running agents, real-time status, logs, metrics
5. MLFlow dashboard embedded for deep observability and cost tracking
6. Agents can be spawned locally or deployed to Docker/K8s with bidirectional registration

## Constraints

- **Local-first**: Must run completely offline; no mandatory cloud dependencies; users control their data
- **Tech stack**: Python ecosystem only; no React/JS frameworks; lightweight deployments
- **Docker overhead**: Agent containers must be minimal (~50-100MB); no bundled UIs with each agent
- **Storage**: SQLite default for zero-config experience; pluggable backends for scale
- **Security**: Code execution must be sandboxed; start with RestrictedPython, extensible to Docker/Firecracker
- **Observability**: MLFlow integration non-negotiable; all agent actions must be trackable
- **Config-first**: YAML/config remains source of truth; UIs generate configs, not visual node graphs
- **Cross-platform**: Must work on Linux, macOS, Windows (Docker Desktop)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Gradio for Chat UI | Python-native, built for ML/AI interfaces, good session handling, lightweight (~30MB) | ✓ Good — 604-line GradioChatUI with session persistence |
| FastAPI + HTMX for Orchestration UI | Maximum control, minimal footprint (~10-15MB), real-time updates without JS frameworks | ✓ Good — Dashboard with SSE streaming, agent discovery, workflow management |
| Bidirectional agent registration | Supports all deployment modes (local, Docker, cloud, VPS); no hardcoded URLs; user has control | ⚠ Partial — Agent-initiated complete, orchestrator-initiated deferred |
| SQLite default storage with pluggable backends | Zero-config for local/dev; can scale to Postgres/Redis for enterprise without code changes | ✓ Good — 8 repositories, factory pattern, all phases use storage abstraction |
| RestrictedPython for code sandboxing (v1) | Fastest (<10ms), works everywhere, good for trusted code; extensible to Docker/Firecracker for untrusted code | ✓ Good — PythonSandboxExecutor + DockerSandboxExecutor, 62 tests |
| MLFlow UI iframe embed | Simplest integration path; can evolve to custom UI with MLFlow API in v2 | ✓ Good — iframe integration in dashboard base template |
| Decouple agent containers from MLFlow UI | Agent containers stay minimal (~50MB); single UI sidecar serves all agents; reduces duplication | ✓ Good — python:3.10-slim base, MLFlow sidecar pattern |
| Defer self-optimizing agents to v2 | v1 focuses on explicit configuration and solid foundations; auto-optimization adds significant complexity | ✓ Good — v1.0 shipped with explicit config-only approach |
| Start with LangChain tool subset (10-20 tools) | Full registry (500+ tools) is overwhelming; start with common tools based on usage patterns | ✓ Good — 15 tools delivered (web: 3, file: 4, data: 4, system: 3), extensible design |

---
*Last updated: 2026-02-05 after discovering critical bugs and starting v1.2 test & fix milestone*
