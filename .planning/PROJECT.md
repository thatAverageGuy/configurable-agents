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

## Requirements

### Validated

- ✓ Linear workflow execution - existing
- ✓ YAML config parsing and validation - existing
- ✓ Google Gemini LLM integration - existing
- ✓ MLFlow tracking (basic) - existing
- ✓ Docker deployment (single workflow) - existing
- ✓ CLI interface (run, validate, deploy) - existing
- ✓ Serper web search tool - existing
- ✓ Pydantic schema validation - existing
- ✓ LangGraph execution engine - existing

### Active

**Runtime Capabilities:**
- [ ] Advanced control flow (branching based on conditions)
- [ ] Loop support (retry logic, iteration over data)
- [ ] Parallel node execution (concurrent agent operations)
- [ ] Code execution sandboxes (RestrictedPython with Docker/Firecracker extensibility)
- [ ] Multi-LLM provider support (OpenAI, Anthropic, Gemini, Ollama)
- [ ] Local model support (Ollama integration for privacy-first deployments)
- [ ] Long-term memory per node/agent/workflow (persistent context across executions)
- [ ] Common LangChain tools subset (search, APIs, data processing)

**Observability:**
- [ ] Full MLFlow production features (prompt optimization, evaluations, A/B testing)
- [ ] Enhanced cost tracking with multi-provider support
- [ ] Performance profiling and bottleneck detection
- [ ] Workflow execution traces with detailed metrics

**User Interfaces:**
- [ ] Chat UI for config generation (Gradio-based conversational interface)
- [ ] Session persistence in Chat UI (conversation history, config iterations)
- [ ] Orchestration UI for runtime management (FastAPI + HTMX dashboard)
- [ ] Agent discovery and registration interface (bidirectional registration)
- [ ] MLFlow UI embedded in orchestration dashboard (iframe integration)
- [ ] Real-time agent monitoring and control (status, logs, metrics streaming)

**Architecture:**
- [ ] Minimal agent container design (decouple MLFlow UI from agents)
- [ ] Bidirectional agent registration (agent-initiated and orchestrator-initiated)
- [ ] Agent registry with heartbeat/TTL (track active agents)
- [ ] Storage abstraction layer (SQLite default, pluggable for Postgres/Redis)
- [ ] Session storage for Chat UI (conversation history persistence)
- [ ] Long-term memory storage backend (per-agent context storage)

**Integrations:**
- [ ] WhatsApp webhook integration (trigger workflows from WhatsApp messages)
- [ ] Telegram bot integration (trigger workflows from Telegram)
- [ ] External trigger API (generic webhook endpoint for third-party integrations)

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

**Existing Foundation (v0.1 - 93% complete):**
The project has a working v0.1 alpha with 25/27 tasks complete (645 passing tests). Core capabilities include:
- Config-driven workflow definition (YAML/JSON)
- Linear node execution with LangGraph
- Structured LLM outputs (Pydantic validation)
- Parse-time validation (fail-fast before LLM calls)
- Google Gemini provider integration
- Basic MLFlow tracking and cost estimation
- Docker deployment with FastAPI server
- CLI interface for run/validate/deploy/report

**Technical Stack:**
- Python 3.10+ runtime
- LangGraph 0.0.20+ for execution
- Pydantic 2.0+ for validation
- MLFlow 3.9+ for observability
- FastAPI for API servers
- Docker for containerization

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
| Gradio for Chat UI | Python-native, built for ML/AI interfaces, good session handling, lightweight (~30MB) | — Pending |
| FastAPI + HTMX for Orchestration UI | Maximum control, minimal footprint (~10-15MB), real-time updates without JS frameworks | — Pending |
| Bidirectional agent registration | Supports all deployment modes (local, Docker, cloud, VPS); no hardcoded URLs; user has control | — Pending |
| SQLite default storage with pluggable backends | Zero-config for local/dev; can scale to Postgres/Redis for enterprise without code changes | — Pending |
| RestrictedPython for code sandboxing (v1) | Fastest (<10ms), works everywhere, good for trusted code; extensible to Docker/Firecracker for untrusted code | — Pending |
| MLFlow UI iframe embed | Simplest integration path; can evolve to custom UI with MLFlow API in v2 | — Pending |
| Decouple agent containers from MLFlow UI | Agent containers stay minimal (~50MB); single UI sidecar serves all agents; reduces duplication | — Pending |
| Defer self-optimizing agents to v2 | v1 focuses on explicit configuration and solid foundations; auto-optimization adds significant complexity | — Pending |
| Start with LangChain tool subset (10-20 tools) | Full registry (500+ tools) is overwhelming; start with common tools based on usage patterns | — Pending |

---
*Last updated: 2026-02-02 after initialization*
