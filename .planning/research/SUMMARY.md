# Project Research Summary

**Project:** Configurable Agent Orchestration Platform
**Domain:** Local-first, config-driven agent orchestration with multi-LLM support
**Researched:** 2026-02-02
**Confidence:** HIGH

## Executive Summary

This is a **local-first, config-driven agent orchestration platform** evolving from v0.1 (linear workflows with Google Gemini) to v1.0 (full-featured multi-agent orchestration). The research validates the current technical foundation (LangGraph, MLflow 3.9+, Pydantic, FastAPI, Docker) and identifies clear evolution paths through four architectural layers: control plane, execution plane, observability, and storage.

The recommended approach prioritizes **incremental complexity**: start with storage abstraction and API decoupling (v0.2), evolve to multi-container orchestration with service discovery (v0.3), then scale to Kubernetes with cloud backends (v0.4). The stack is Python-only, lightweight, and avoids framework lock-in. Key differentiators include MLflow-native optimization (no competitor offers this), conversational config generation via Gradio, and true local-first architecture (SQLite → PostgreSQL → Cloud without code changes).

**Critical risks identified:** (1) Multi-LLM rate limit cascades causing cost explosions - **40% of agentic AI projects will be canceled by 2027 due to cost overruns** (Gartner), (2) Framework over-abstraction (LangChain trap) creating maintenance nightmares, and (3) SQLite write concurrency bottlenecks as agent count scales. Mitigation strategies are clear: token-aware rate limiting with circuit breakers, thin abstraction layers with LangGraph primitives, and WAL mode + async write queues for SQLite before migrating to PostgreSQL.

## Key Findings

### Recommended Stack

The existing v0.1 foundation is **production-ready for 2026** and requires only strategic additions, not replacements. Research confirms the core stack (LangGraph >=0.0.20, Pydantic >=2.0, MLflow >=3.9.0, FastAPI, Docker) represents current best practices.

**Core technologies (Already deployed in v0.1):**
- **LangGraph** (>=0.0.20): Stateful graph execution engine - Correct choice for agent orchestration. LangGraph superseded LangChain for agent workflows and supports advanced control flow natively (conditionals, loops, parallel execution, checkpoints).
- **MLflow** (>=3.9.0): LLM observability and experiment tracking - Version 3.9.0 (released Jan 30, 2026) adds AI Assistant, performance dashboards, judge optimization, and OpenTelemetry native support. No competitor integrates experiment tracking at this level.
- **Pydantic** (>=2.0): Config validation and structured outputs - Industry standard for LLM structured outputs and schema validation.
- **FastAPI**: Async API server - Enables API decoupling and UI sidecar pattern.
- **Docker**: Container deployment - Already supports multi-stage builds and production patterns.

**Strategic additions for v0.2+:**

**Multi-LLM abstraction:**
- **LiteLLM** (Latest): Unified interface for 100+ providers (OpenAI, Anthropic, Google, Ollama, Azure, AWS Bedrock). 8ms P95 latency, built-in cost tracking, retry/fallback logic, and load balancing. Industry standard for multi-provider abstraction.
- **Ollama** (Latest): Local LLM runtime for zero-cloud deployments. Supports Llama 3, Gemma, DeepSeek, Mistral, 50+ models. JSON mode for structured outputs, "thinking" mode for reasoning.

**Conversational UI:**
- **Gradio** (6.5.1, Jan 29 2026): Purpose-built for chat interfaces. Minimal code, streaming support, free Hugging Face hosting. Perfect for config generation chatbot.

**Orchestration management UI:**
- **FastAPI + HTMX + DaisyUI**: Python-only stack (no React/Vue). HTMX is 14KB with no build step. Server-side rendering via Jinja2 templates. Used by Netflix, Uber, Microsoft for production UIs.

**Enhanced observability:**
- **OpenTelemetry** (Latest Python SDK): MLflow 3.6+ has native support. Distributed tracing across containers, cross-platform metrics export, industry standard for enterprise observability.

**Storage:**
- **SQLite** (Built-in): Zero-config local storage with WAL mode for concurrent reads during writes.
- **DuckDB** (Latest): Embedded analytics engine. 10-100x faster than SQLite for OLAP queries. Ideal for dashboard aggregations.
- **PostgreSQL** (16+): Team collaboration and multi-writer workloads. Migration path from SQLite via storage abstraction layer.

**What NOT to use:**
- **LangChain (base)**: Deprecated for agent orchestration. LangGraph supersedes it.
- **CrewAI/AutoGen**: Framework lock-in, less control. Use LangGraph for flexibility.
- **React/Vue/Angular**: JavaScript frameworks violate Python-only constraint. Use HTMX.
- **RestrictedPython alone**: "Glass sandbox" with known CVEs. Use Docker containers or gVisor for code execution.

### Expected Features

Research reveals a clear feature hierarchy validated across LangGraph Platform, CrewAI, Prefect, and Temporal.

**Must have (table stakes for v1.0):**
- Multi-Agent Orchestration (sequential, hierarchical, parallel patterns)
- Advanced Control Flow (branching, loops, conditionals via graph-based execution)
- Multi-LLM Provider Support (OpenAI, Anthropic, Google, Ollama - no vendor lock-in)
- State Management & Persistence (checkpointing, resume capability)
- Observability (real-time tracing, token/cost tracking via MLflow)
- YAML Configuration (declarative configs as source of truth, Git-friendly)
- Code Execution Sandbox (Docker-based isolation for agent-generated code)
- Error Handling & Retries (automatic retries, fallback strategies, graceful degradation)
- Basic Memory (short-term session memory; long-term can wait for v1.2)
- Self-Hosted Deployment (Docker Compose for local/VPC, preserves local-first promise)

**Should have (competitive advantage for v1.1-1.3):**
- Conversational Config UI (Gradio) - Chat interface for YAML generation. Lowers barrier to entry vs code-first competitors.
- Visual Workflow Builder - Drag-and-drop orchestration designer with code export (OpenAI AgentKit pattern).
- Runtime Management UI (FastAPI + HTMX) - Live workflow control, intervention, real-time monitoring.
- Human-in-the-Loop - Approval workflows, feedback incorporation, resume logic.
- Long-Term Memory (RAG) - Vector database integration, semantic retrieval across sessions.
- MLflow Prompt Optimization - Automated experimentation, A/B testing. **No competitor offers this.**
- MLflow Evaluation Pipelines - Regression testing, quality gates, cost/latency tracking per prompt version.

**Defer to v2.0+ (future consideration):**
- Contextual/Agentic Memory (beyond RAG: adaptive memory that learns and evolves)
- Agent Protocol Support (A2A, MCP for cross-platform interoperability)
- OpenTelemetry Integration (enterprise observability platform compatibility)
- Cloud Deployment Options (AWS/Azure/GCP managed offerings)
- Multi-Tenancy (SaaS mode with tenant isolation)

**Anti-features (commonly requested but problematic):**
- **Real-time everything via WebSockets**: Battery drain, complexity overhead for features that don't need it. Use polling + selective WebSockets (live tracing, chat only).
- **Proprietary agent framework**: Reinventing LangGraph creates maintenance burden. Orchestrate existing frameworks instead.
- **Cloud-only architecture**: Kills local-first value prop, creates vendor lock-in. Hybrid by design.
- **No-code only**: Complex agents need code. Visual builder with code escape hatches is the right balance.
- **Single model lock-in**: Model landscape changes fast. Multi-provider from day 1.

### Architecture Approach

Modern agent orchestration platforms converge on a **four-layer separation pattern**: control plane (orchestrator, service registry, task queue, API gateway), execution plane (agent containers), observability layer (tracing, metrics, logging), and storage layer (workflow, state, results, metadata). This pattern is validated across LangGraph Platform, Prefect, and Temporal.

**Major components and responsibilities:**

1. **Orchestrator Engine** - Workflow execution, task scheduling, state management. Implementation: LangGraph for graph execution, supports conditionals, loops, parallel execution via Send API.

2. **Service Registry** - Agent discovery, health checks, capability catalog. Implementation: Bidirectional registration (agents register on startup, orchestrator queries for healthy agents). Start with in-memory registry (v0.2), evolve to Consul/etcd (v0.4).

3. **Task Queue** - Work distribution, backpressure, priority queues. Implementation: Redis for production (v0.3), in-memory for local dev (v0.2).

4. **API Gateway** - Request routing, authentication, rate limiting. Implementation: FastAPI with REST endpoints (/run, /health, /status/{job_id}, /workflows).

5. **Agent Container** - Execute tasks, report results, maintain heartbeat. Implementation: Minimal Docker image (~50-100MB), single-purpose, no UI dependencies.

6. **Storage Backend** - Pluggable abstraction for SQLite → PostgreSQL → Cloud. Implementation: Abstract interface with factory pattern, enables local-first → team → enterprise migration without code changes.

7. **UI Sidecar** - Optional user interfaces, deployed separately. Implementation: Separate containers for Gradio (chat), HTMX dashboard (orchestration), MLflow UI (observability). Communicate via API Gateway.

**Key architectural patterns:**

**Storage abstraction (Phase 1):** Define `StorageBackend` interface with implementations for SQLite (v0.1), PostgreSQL (v0.2), and Cloud (S3 + DynamoDB, v0.4). Factory pattern selects backend from config. This is foundational - all other components depend on storage.

**UI decoupling via sidecar pattern (Phase 2):** UI components run in separate containers, communicate via REST API. Agent containers remain minimal (~50-100MB, no Flask/Gradio). Deploy UI optionally (headless for production, UI for dev/monitoring). Technology flexibility: swap UI frameworks without rebuilding agents.

**Service discovery with bidirectional registration (Phase 3):** Agents register on startup with metadata (capabilities, version, max_concurrent_tasks). Orchestrator queries registry with filters (e.g., "agents with text-generation capability"). Heartbeat mechanism expires stale entries (prevents zombie agents). Health checks deregister dead agents automatically.

**Deployment topology evolution:**
- **v0.1**: Single Python process, SQLite file, file logs (current - fast iteration)
- **v0.2**: Docker Compose with orchestrator + agent containers, shared PostgreSQL, MLflow server (team collaboration)
- **v0.3**: Multi-container with service registry, task queue, UI sidecar (realistic production testing)
- **v0.4**: Kubernetes with auto-scaling, cloud storage, OpenTelemetry → Prometheus (enterprise scale)

**Anti-patterns to avoid:**
- **Premature microservices**: Don't split into 5+ containers in v0.1. Start monolithic, evolve gradually.
- **Tight coupling to storage implementation**: Abstract behind interface. Never use PostgreSQL JSONB queries directly in business logic.
- **Monolithic UI container**: Separate Gradio, HTMX, MLflow into individual images. Users compose what they need.
- **Synchronous service discovery**: Cache registry results, subscribe to updates. Don't query on every request.
- **No health checks**: Implement /health endpoint, configure registry TTL-based expiration. Dead agents must deregister automatically.

### Critical Pitfalls

Research analyzed agent orchestration failures in 2025-2026 to identify production-breaking patterns. **40% of agentic AI projects are projected to be canceled by end-of-2027 due to escalating costs and misaligned value** (Gartner 2025).

**Top 5 pitfalls with prevention strategies:**

1. **Multi-LLM Rate Limit Cascade Failures** - Traditional request-per-second rate limiting is insufficient for LLM APIs. Multi-agent workflows create exponential token growth (Agent A's verbose output → Agent B's massive input). Monthly API bills can be 5-10x higher than expected.
   - **Prevention**: Token-aware rate limiting (limit tokens processed, not just requests), intelligent routing (cheap models for simple tasks), circuit breakers (automated token budgets), per-tenant quotas.
   - **Phase**: Phase 2 (Multi-LLM Support) - Critical. Must implement before supporting multiple providers.

2. **Framework Over-Abstraction (The "LangChain Trap")** - Over-abstraction adds 200-500ms latency, debugging requires reading framework source code, framework updates break workflows. AI frameworks fail in production due to unpredictable costs and scalability limitations.
   - **Prevention**: Build on LangGraph primitives (already done via ADR-001), vendor-agnostic design, escape hatches to pure Python, minimal middleware, avoid framework-specific patterns.
   - **Phase**: Phase 1 (Foundation) - Already addressed. Continue discipline in Phase 2.

3. **Zombie Agents and Orphaned Registrations** - Non-human identities outnumber human identities by 45:1, with significant portions inactive or orphaned. Agents self-register but fail to deregister on crash, creating "zombie identities" waiting for exploitation.
   - **Prevention**: Heartbeat mechanisms with registry expiration, graceful shutdown handlers, TTL-based expiration, automated cleanup audits, registration-deployment coupling.
   - **Phase**: Phase 2 (State Persistence) - Must implement agent registry with TTL. Phase 4 (Cloud) becomes critical for agent fleets.

4. **Context Window Overflow (Lost-in-the-Middle)** - Multi-step workflows accumulate context linearly. Simple truncation removes important information. Even when content fits, LLMs weigh beginning/end more heavily (primacy/recency bias), causing quality degradation.
   - **Prevention**: Intelligent truncation (summarize older messages), semantic chunking (split by meaning), RAG pipelines (retrieve relevant chunks), compression (summarize intermediate outputs), context-aware routing.
   - **Phase**: Phase 1 (Foundation) - Partially addressed via output schema validation. Phase 2 (Loops & State) becomes critical for long-running workflows.

5. **SQLite Write Concurrency Bottleneck** - SQLite has single-writer model. Multiple agents writing simultaneously create SQLITE_BUSY errors. The problem compounds: retries create exponential backoff, slowing the entire system.
   - **Prevention**: WAL mode (Write-Ahead Logging for non-blocking reads), connection pooling (single writer, multiple readers), async write queue (buffer writes, flush with single thread), migration path to PostgreSQL.
   - **Phase**: Phase 2 (State Persistence) - Critical. Current v0.1 uses in-memory state (ADR-008), avoiding this. Phase 2 must implement WAL mode + async queue or migrate to PostgreSQL.

**Additional pitfalls:**

6. **Observability Death by a Thousand Logs** - Over-instrumentation creates 15-20% latency overhead. Synchronous logging blocks execution. Log storage costs exceed compute costs.
   - **Prevention**: Async logging (MLflow async, ADR-011), tiered instrumentation (errors always, success sampled), sampling (1% success, 100% errors), structured JSON logs.
   - **Phase**: Phase 1 (Observability) - Already addressed via ADR-014 (three-tier strategy) and ADR-011 (async logging).

7. **Docker Image Bloat (The 8GB Container)** - Simple agent deployments ballooning to 2.54GB or 8GB. Slow builds (56s for BERT classifier), slow deployments, increased storage costs.
   - **Prevention**: Multi-stage builds, minimal base images (python:3.11-slim), layer optimization, dependency auditing, .dockerignore, separate UI from agent containers.
   - **Phase**: Phase 1 (Docker Deployment) - Critical now. Verify T-022 (docker artifact generator) uses multi-stage builds and slim images.

8. **RestrictedPython Security Theater** - RestrictedPython provides false sense of security. Attackers can escape via Python's dynamic nature (inspect, __builtins__, inheritance chains). Sandbox escapes expose host kernel.
   - **Prevention**: Full virtualization (gVisor, Kata containers), no code execution in v0.1 (already done via ADR), tool sandboxing (LangChain BaseTool constraints), secret isolation.
   - **Phase**: Phase 1 (Foundation) - Already addressed via ADR (no arbitrary code execution). Phase 2 (Custom Code Nodes) must use full virtualization, never RestrictedPython alone.

9. **"Dumb RAG" Memory Thrashing** - Dumping all documentation into vector databases without addressing data quality causes context-flooding. Poor retrieval strategies retrieve irrelevant context or too much context (overflow).
   - **Prevention**: Semantic chunking (split by meaning), metadata filtering (tag + filter before semantic search), hybrid search (embeddings + BM25), reranking (score retrieved chunks), data quality processes.
   - **Phase**: Phase 3 (Quality Metrics) - RAG not in current roadmap, but likely user demand. If adding RAG: v0.3+ with evaluation framework, never "quick integration" in Phase 2.

## Implications for Roadmap

Based on combined research, recommended phase structure prioritizes **incremental architectural complexity** while delivering user value at each stage.

### Phase 1: Foundation + Multi-LLM Support (v0.2)
**Rationale:** Storage abstraction is foundational (all components depend on it), and multi-LLM support is the primary v1.0 differentiator. These can be built in parallel with minimal dependencies.

**Delivers:**
- Pluggable storage backend (SQLite → PostgreSQL → Cloud migration path without code changes)
- Multi-LLM abstraction via LiteLLM (OpenAI, Anthropic, Google, Ollama)
- Token-aware rate limiting with circuit breakers (prevents cost explosions)
- Local LLM support via Ollama (true local-first with zero cloud costs)

**Addresses features:**
- Multi-LLM Provider Support (table stakes)
- Deployment Flexibility (SQLite for local, PostgreSQL for teams)
- Configuration Management (YAML with multi-provider configs)

**Avoids pitfalls:**
- Rate limit cascade failures (token-aware limiting, circuit breakers)
- SQLite concurrency (storage abstraction enables PostgreSQL migration)
- Framework lock-in (LiteLLM as thin abstraction, not full framework)

**Effort:** 3-4 weeks
**Blockers:** None (builds on v0.1 foundation)

---

### Phase 2: State Persistence + Agent Lifecycle (v0.2)
**Rationale:** Long-running workflows require persistent state and checkpoint/resume capability. Agent lifecycle management (registration, heartbeat, deregistration) prevents zombie agents and enables service discovery for Phase 3.

**Delivers:**
- Persistent state with checkpointing (workflows survive crashes, resume from last checkpoint)
- Agent registry with TTL-based expiration (bidirectional registration, health checks)
- Graceful shutdown handlers (deregister on termination)
- SQLite WAL mode + async write queue (concurrent reads during writes)

**Addresses features:**
- State Management & Persistence (table stakes)
- Error Handling & Retries (checkpoint on failure, resume from last good state)
- Basic Memory (session state persists across executions)

**Avoids pitfalls:**
- Zombie agents (heartbeat + TTL expiration + graceful shutdown)
- SQLite write concurrency (WAL mode + async queue before migration to PostgreSQL)
- Context overflow (implement summarization for multi-turn workflows)

**Effort:** 3-4 weeks
**Blockers:** Storage abstraction complete (Phase 1)

---

### Phase 3: Advanced Control Flow + Observability (v0.2-0.3)
**Rationale:** Graph-based execution with conditionals, loops, and parallel execution is table stakes for v1.0. Enhanced observability (OpenTelemetry, distributed tracing) enables debugging complex multi-agent workflows.

**Delivers:**
- Conditional routing (branch based on agent outputs)
- Loop execution (retry logic, while loops with termination conditions)
- Parallel execution (fan-out/fan-in patterns via LangGraph Send API)
- OpenTelemetry integration (distributed tracing across containers, Prometheus metrics)
- Enhanced MLflow dashboards (performance charts, latency tracking, cost per workflow)

**Addresses features:**
- Control Flow (Branching/Loops) (table stakes)
- Observability & Tracing (real-time visibility, token/cost tracking)

**Avoids pitfalls:**
- Context overflow (intelligent truncation in loop executions)
- Observability overhead (async logging, sampling, tiered instrumentation)
- Framework lock-in (LangGraph native control flow, no custom abstractions)

**Effort:** 3-4 weeks
**Blockers:** State persistence complete (Phase 2) for checkpoint/resume in loops

---

### Phase 4: Conversational UI + Runtime Management (v0.3)
**Rationale:** Conversational config generation (Gradio) and runtime management dashboard (HTMX) are key differentiators. These are independent UIs consuming the API Gateway, enabling parallel development.

**Delivers:**
- Gradio chat interface for YAML config generation (non-technical users build agents through conversation)
- HTMX orchestration dashboard (view workflows, trigger runs, inspect state, real-time logs)
- MLflow UI integration (prompt optimization, evaluation pipelines)
- UI sidecar pattern (separate containers, optional deployment)

**Addresses features:**
- Conversational Config UI (differentiator - lowers barrier to entry)
- Runtime Management UI (differentiator - live workflow control)
- Visual Workflow Builder (if time permits - drag-and-drop with code export)

**Avoids pitfalls:**
- Docker image bloat (UI in separate containers, agents remain minimal ~50-100MB)
- UX failures (progress indicators, cost visibility, user-friendly errors)

**Effort:** 4-5 weeks
**Blockers:** API Gateway layer complete (Phase 2) for UI-agent communication

---

### Phase 5: Code Execution Sandbox + HITL (v0.3)
**Rationale:** Code execution sandbox enables agent-generated code (critical for data analysis, automation workflows). Human-in-the-loop approval workflows are enterprise requirement for compliance and governance.

**Delivers:**
- Docker-based code execution sandbox (network isolation, resource limits)
- Human-in-the-loop approval steps (pause workflow, request approval, resume with feedback)
- Tool sandboxing (LangChain BaseTool constraints, secret isolation)

**Addresses features:**
- Code Execution Sandbox (table stakes)
- Human-in-the-Loop (table stakes for enterprise)
- Tool Integration (pre-built connectors + safe API integration framework)

**Avoids pitfalls:**
- RestrictedPython security theater (use Docker containers, not language-level restrictions)
- Security vulnerabilities (no secrets in prompts, network isolation, disposable environments)

**Effort:** 3-4 weeks
**Blockers:** Runtime management UI (Phase 4) for approval interface

---

### Phase 6: Multi-Container Orchestration (v0.3)
**Rationale:** Combines all previous components into production-ready multi-container deployment. Orchestrator container, agent pool, service registry, PostgreSQL, MLflow server, UI sidecar.

**Delivers:**
- Docker Compose templates for multi-container deployment
- Orchestrator container (separate from agents for scalability)
- Agent pool (multiple agent containers, auto-registered)
- Service discovery (agents query registry for orchestrator location)
- Networking configuration (container-to-container communication)
- Volume management (persistent storage for PostgreSQL + MLflow)

**Addresses features:**
- Deployment Flexibility (self-hosted multi-container, realistic production testing)
- Multi-Agent Orchestration (distributed agent execution)

**Avoids pitfalls:**
- Premature microservices (waited until Phase 6 to separate orchestrator from agents)
- Synchronous service discovery (cached registry results, health checks)
- No health checks (implemented /health endpoint, TTL-based expiration)

**Effort:** 2-3 weeks
**Blockers:** Service registry (Phase 2), UI sidecar (Phase 4) complete

---

### Phase 7: Long-Term Memory (RAG) + Evaluations (v0.4)
**Rationale:** RAG-based long-term memory enables cross-session context retrieval. MLflow evaluation pipelines enable prompt optimization and regression testing. These are competitive features, not table stakes.

**Delivers:**
- Vector database integration (Chroma, Pinecone, Weaviate for semantic search)
- Semantic chunking + metadata filtering (intelligent context retrieval)
- Reranking (score retrieved chunks by relevance)
- MLflow prompt optimization (automated A/B testing, cost/latency tracking)
- MLflow evaluation pipelines (quality gates, regression testing)

**Addresses features:**
- Long-Term Memory (RAG) (competitive advantage)
- MLflow Optimization (differentiator - no competitor offers this)
- MLflow Evaluations (differentiator - production-grade quality assurance)

**Avoids pitfalls:**
- "Dumb RAG" memory thrashing (semantic chunking, metadata filtering, reranking, retrieval quality metrics)
- Context overflow (RAG retrieves relevant chunks dynamically, not all context)

**Effort:** 4-5 weeks
**Blockers:** Observability (Phase 3) complete for retrieval quality metrics

---

### Phase 8: Kubernetes Deployment (v0.4)
**Rationale:** Enterprise deployment with auto-scaling, high availability, cloud storage backends. Most complex phase, requires all previous components.

**Delivers:**
- Kubernetes manifests (Deployments for orchestrator, StatefulSets for agents)
- Helm charts (parameterized deployments)
- Ingress configuration (external access with TLS)
- Auto-scaling policies (HPA for agents based on queue depth)
- Cloud storage integration (S3 for artifacts, RDS for state, DynamoDB for metadata)

**Addresses features:**
- Deployment Flexibility (cloud deployment, auto-scaling)
- RBAC & Governance (Kubernetes RBAC, audit logs)

**Avoids pitfalls:**
- Premature microservices (Kubernetes is final phase, not first)
- Docker image bloat (minimal images from Phase 1 critical for K8s pod startup time)

**Effort:** 4-6 weeks
**Blockers:** All previous phases complete

---

### Phase Ordering Rationale

- **Storage first (Phase 1)**: All components depend on storage. Abstract early to enable SQLite → PostgreSQL → Cloud migration without refactoring business logic.
- **Multi-LLM parallel to storage (Phase 1)**: Primary v1.0 differentiator, no dependencies, can be built concurrently.
- **State persistence before control flow (Phase 2 → 3)**: Loops and conditionals require checkpointing. Can't implement resume logic without persistent state.
- **Lifecycle management with state (Phase 2)**: Agent registry needed for service discovery in Phase 6, but also prevents zombie agents in Phase 2 when introducing persistent state.
- **Observability before UIs (Phase 3 → 4)**: UIs need tracing data to display. OpenTelemetry instrumentation must exist before building dashboards.
- **UIs before sandboxing (Phase 4 → 5)**: Approval workflows (HITL) need runtime management UI for human interaction.
- **Multi-container after components built (Phase 6)**: Orchestrator separation, service discovery, and UI sidecar can't be tested until components exist.
- **RAG after observability (Phase 7)**: Retrieval quality metrics (precision/recall) require evaluation framework from Phase 3.
- **Kubernetes last (Phase 8)**: Requires all components production-tested in multi-container (Phase 6) before scaling to K8s.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 5 (Code Execution Sandbox)**: Complex security domain. Research gVisor vs Kata containers vs Firecracker for sandboxing. Docker sandboxes pattern needs detailed security audit.
- **Phase 7 (RAG Integration)**: Sparse documentation on production RAG patterns. Research vector database tradeoffs (Chroma vs Pinecone vs Weaviate), reranking strategies, hybrid search implementations.
- **Phase 8 (Kubernetes)**: Niche deployment patterns for stateful agent workloads. Research Kubernetes StatefulSet vs Deployment for agents, HPA autoscaling triggers, cloud storage backends (RDS vs DynamoDB vs S3).

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Storage Abstraction)**: Well-documented pattern (factory pattern, interface design). SQLite/PostgreSQL integration is standard.
- **Phase 2 (Agent Lifecycle)**: Service discovery with Consul/etcd has mature patterns. Heartbeat + TTL expiration is common pattern.
- **Phase 3 (Control Flow)**: LangGraph documentation covers conditionals, loops, parallel execution. No novel patterns needed.
- **Phase 4 (UIs)**: Gradio and HTMX documentation is comprehensive. Chat interface and CRUD dashboard are standard patterns.
- **Phase 6 (Multi-Container)**: Docker Compose networking and service discovery are well-documented. Orchestrator-agent separation is standard pattern.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | All recommendations verified with official docs dated Jan-Feb 2026. LiteLLM, Gradio, MLflow 3.9.0, Ollama are actively maintained with recent releases. Stack aligns with industry trends (multi-LLM, local-first, Python-only). |
| Features | **HIGH** | Feature research cross-referenced against LangGraph Platform, CrewAI, Prefect, Temporal, and Microsoft Agent Framework. Table stakes vs differentiators validated with 2025-2026 market analysis. MVP definition matches production patterns from leading platforms. |
| Architecture | **HIGH** | Architectural patterns validated across LangGraph Platform (graph-based orchestration), Prefect (work pools + workers), and Temporal (durable execution). Deployment topology evolution (single process → multi-container → Kubernetes) matches industry standard progression. Service discovery patterns confirmed via Consul, etcd, and microservices architecture sources. |
| Pitfalls | **HIGH** | Pitfall research based on production post-mortems, 2025-2026 failure analysis, and authoritative sources. Critical statistics verified (40% project cancellation rate by 2027, 45:1 NHI:human ratio, 15-20% observability overhead). Prevention strategies validated against LangGraph, Prefect, and enterprise deployment guides. |

**Overall confidence:** **HIGH**

### Gaps to Address

**Gap 1: Agent Protocol Support (A2A, MCP)** - Research identified emerging interoperability standards (Agent2Agent protocol, Model Context Protocol) for cross-platform tool sharing, but implementation details are sparse. Current roadmap defers this to v2.0+, which is appropriate given early-stage ecosystem.
- **How to handle**: Monitor protocol adoption during v1.0 development. If community momentum builds, add to v1.x as optional integration. Not blocking for launch.

**Gap 2: Advanced Memory Systems (Contextual/Agentic)** - Research indicates 2026 trend toward contextual/agentic memory surpassing traditional RAG for adaptive workflows, but production patterns are still emerging. Not well-defined for implementation.
- **How to handle**: Start with RAG (Phase 7, well-documented pattern). Monitor research on contextual memory. Add experimental flag for advanced memory in v1.3 if patterns stabilize.

**Gap 3: Kubernetes StatefulSet vs Deployment for Agents** - Research shows conflicting recommendations for stateful agent workloads in Kubernetes. Some sources suggest StatefulSet (stable network identity), others suggest Deployment (easier scaling).
- **How to handle**: Requires Phase 8 research. Test both approaches in multi-container (Phase 6) before committing to Kubernetes pattern. Document tradeoffs in ADR.

**Gap 4: Cost Optimization Strategies** - Research emphasizes cost explosions as primary failure mode (40% project cancellation), but specific cost optimization strategies beyond token-aware rate limiting are under-documented.
- **How to handle**: Phase 2 must implement token-aware rate limiting, circuit breakers, and per-tenant quotas. Phase 7 (MLflow Optimization) adds cost/latency tracking per prompt version. Add cost estimation to UI (Phase 4) for visibility.

**Gap 5: Evaluation Metrics for Agent Quality** - Research identifies evaluation as critical (Phase 7), but specific metrics for multi-agent orchestration quality are not standardized. LLM judges, prompt optimization, and regression testing are tools, not complete frameworks.
- **How to handle**: Phase 7 research must define agent quality metrics (precision, recall, task completion rate, cost per task). Use MLflow evaluation framework as foundation. Validate metrics with early users before full rollout.

## Sources

### Primary (HIGH confidence)

**Stack Research:**
- [LiteLLM GitHub](https://github.com/BerriAI/litellm) - Official repository, Jan 26 2026 update
- [LiteLLM Docs](https://docs.litellm.ai/docs/) - Official documentation
- [MLFlow 3.9.0 Release](https://mlflow.github.io/mlflow-website/releases/) - Jan 30 2026 release notes
- [MLFlow OpenTelemetry Support](https://mlflow.org/blog/opentelemetry-tracing-support) - Official integration guide
- [Gradio GitHub](https://github.com/gradio-app/gradio) - Version 6.5.1, Jan 29 2026
- [Ollama GitHub](https://github.com/ollama/ollama) - Official repository, 2026 active
- [FastAPI + HTMX + DaisyUI Guide](https://sunscrapers.com/blog/modern-web-dev-fastapi-htmx-daisyui/) - Production pattern guide

**Feature Research:**
- [LangGraph Platform Overview](https://www.langchain.com/langgraph) - Official LangChain documentation
- [LangGraph Platform Documentation](https://docs.langchain.com/langgraph-platform) - Deployment patterns
- [CrewAI Introduction](https://docs.crewai.com/en/introduction) - Official documentation
- [CrewAI Official Site](https://www.crewai.com/) - Feature comparison
- [Microsoft Agent Framework Overview](https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview) - Microsoft official docs
- [Agent Orchestration Frameworks Comparison 2026](https://iterathon.tech/blog/ai-agent-orchestration-frameworks-2026) - Market analysis

**Architecture Research:**
- [LangGraph Multi-Agent Orchestration Guide (2025)](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025) - Comprehensive architecture guide
- [Prefect Deployments Documentation](https://docs.prefect.io/v3/concepts/deployments) - Official Prefect patterns
- [Temporal Workflow Orchestration (Jan 2026)](https://medium.com/@milinangalia/the-rise-of-temporal-how-netflix-and-leading-tech-companies-are-revolutionizing-workflow-822fbcc736e6) - Production case studies
- [AI Agent Orchestration Patterns - Azure](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) - Microsoft official patterns
- [Google's Eight Essential Multi-Agent Design Patterns (Jan 2026)](https://www.infoq.com/news/2026/01/multi-agent-design-patterns/) - Google research
- [Microservices Pattern: Service Registry](https://microservices.io/patterns/service-registry.html) - Standard pattern documentation

**Pitfalls Research:**
- [Why Multi-Agent LLM Systems Fail - Orq.ai](https://orq.ai/blog/why-do-multi-agent-llm-systems-fail) - Production failure analysis
- [Rate Limiting in AI Gateway - TrueFoundry](https://www.truefoundry.com/blog/rate-limiting-in-llm-gateway) - Token-aware rate limiting
- [The 2025 AI Agent Report - Composio](https://composio.dev/blog/why-ai-agent-pilots-fail-2026-integration-roadmap) - 40% project cancellation statistic
- [Beyond SQLite Single-Writer Limitation - Turso](https://turso.tech/blog/beyond-the-single-writer-limitation-with-tursos-concurrent-writes) - Concurrency patterns
- [Docker Container Bloat Solutions - Eureka](https://eureka.patsnap.com/article/docker-container-bloat-how-to-reduce-image-size-and-improve-speed) - Image optimization

### Secondary (MEDIUM confidence)

- [Complete Ollama Tutorial 2026](https://dev.to/proflead/complete-ollama-tutorial-2026-llms-via-cli-cloud-python-3m97) - Community tutorial
- [Streamlit vs Gradio 2025](https://www.squadbase.dev/en/blog/streamlit-vs-gradio-in-2025-a-framework-comparison-for-ai-apps) - UI framework comparison
- [LangChain Alternatives 2026](https://www.lindy.ai/blog/langchain-alternatives) - Framework comparison
- [Agent Lifecycle Management 2026](https://onereach.ai/blog/agent-lifecycle-management-stages-governance-roi/) - Governance patterns
- [Context Window Management Strategies](https://www.getmaxim.ai/articles/context-window-management-strategies-for-long-context-ai-agents-and-chatbots/) - Truncation strategies

### Tertiary (LOW confidence, needs validation)

- [Agent Protocol Support (A2A, MCP)](https://arxiv.org/html/2510.04173v1) - Open Agent Specification Technical Report (early-stage)
- [Contextual Memory vs RAG 2026](https://venturebeat.com/data/six-data-shifts-that-will-shape-enterprise-ai-in-2026) - Emerging trend, not production-validated
- [Agentic AI 2026: From Hype to Trusted Reality](https://knubisoft.medium.com/agentic-ai-2026-from-hype-to-trusted-reality-c4e735f9db0a) - Opinion piece

---

*Research completed: 2026-02-02*
*Ready for roadmap: yes*
