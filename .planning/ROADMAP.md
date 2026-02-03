# Roadmap: Configurable Agent Orchestration Platform

## Overview

Transform the existing v0.1 linear workflow runner into a full-featured local-first agent orchestration platform. The roadmap progresses through four phases: first upgrading the core execution engine with multi-LLM support and advanced control flow, then making the system multi-agent aware with container optimization and observability, then building the user-facing interfaces and external integrations, and finally delivering advanced capabilities like code sandboxing, long-term memory, and MLFlow optimization. Each phase delivers independently testable, incremental value on top of the working v0.1 foundation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Engine** - Multi-LLM support, advanced control flow, storage abstraction, and execution traces
- [x] **Phase 2: Agent Infrastructure** - Minimal containers, agent lifecycle, and production observability
- [ ] **Phase 3: Interfaces and Triggers** - Chat UI, orchestration dashboard, and external webhook integrations
- [ ] **Phase 4: Advanced Capabilities** - Code sandboxes, long-term memory, tool ecosystem, and MLFlow optimization

## Phase Details

### Phase 1: Core Engine
**Goal**: Users can define and execute complex multi-provider workflows with branching, loops, and parallelism on a pluggable storage backend with full execution traces
**Depends on**: Nothing (builds on v0.1 foundation)
**Requirements**: RT-01, RT-02, RT-03, RT-05, RT-06, ARCH-04, OBS-04
**Success Criteria** (what must be TRUE):
  1. User can write a YAML config that routes to different nodes based on a previous node's output, and the workflow follows the correct branch
  2. User can write a YAML config with retry loops and data iteration, and the workflow repeats nodes until a termination condition is met
  3. User can write a YAML config where multiple nodes execute concurrently, and all results are collected before continuing
  4. User can switch a workflow's LLM provider from Gemini to OpenAI/Anthropic/Ollama by changing one line in the YAML config, and execution succeeds with the new provider
  5. User can run a complete workflow using only Ollama local models with no internet connection
  6. After running a workflow, user can retrieve full execution traces with per-node metrics (latency, tokens, cost) from storage
**Plans**: 4 plans (3 waves)

Plans:
- [x] 01-01-PLAN.md -- Storage abstraction layer (pluggable backend interface with SQLite implementation) [Wave 1]
- [x] 01-02-PLAN.md -- Multi-LLM provider integration (LiteLLM abstraction with OpenAI, Anthropic, Gemini, Ollama support) [Wave 1]
- [x] 01-03-PLAN.md -- Advanced control flow (conditional branching, loop execution, parallel node execution via LangGraph) [Wave 2, depends on 01-02]
- [x] 01-04-PLAN.md -- Storage-executor integration and execution traces (workflow run persistence, per-node metrics, OBS-04) [Wave 3, depends on 01-01, 01-03]

### Phase 2: Agent Infrastructure
**Goal**: Users can deploy minimal agent containers that self-register, maintain health, and produce detailed observable metrics across all providers
**Depends on**: Phase 1 (storage abstraction, multi-LLM providers)
**Requirements**: ARCH-01, ARCH-02, ARCH-03, OBS-02, OBS-03
**Success Criteria** (what must be TRUE):
  1. Agent Docker image is under 100MB and contains no UI dependencies (MLFlow UI runs as separate sidecar)
  2. A new agent container registers itself with the orchestrator on startup and appears in the registry within seconds
  3. When an agent container crashes or is stopped, the registry removes it automatically after its TTL expires
  4. After running a multi-provider workflow, user can see unified cost breakdown across all LLM providers used
  5. User can identify the slowest node in a workflow through performance profiling output
**Plans**: 6 plans (3 waves)

**Note:** Orchestrator-initiated registration (ARCH-02) is deferred to Phase 3. This phase implements agent-initiated registration only.

Plans:
**Wave 1 (parallel execution):**
- [x] 02-01A-PLAN.md -- Storage layer and registry server (AgentRecord ORM, AgentRegistryRepository, AgentRegistryServer with FastAPI endpoints) [Wave 1]
- [x] 02-02A-PLAN.md -- Multi-provider cost tracking (MultiProviderCostTracker, MLFlowTracker integration, provider detection) [Wave 1]
- [x] 02-02B-PLAN.md -- Performance profiling (profile_node decorator, BottleneckAnalyzer, node_executor integration) [Wave 1]

**Wave 2 (depends on Wave 1):**
- [x] 02-01B-PLAN.md -- Registry client and generator integration (AgentRegistryClient with heartbeat, deployment generator updates) [Wave 2, depends on 02-01A]
- [x] 02-02C-PLAN.md -- CLI integration (cost-report, profile-report, observability commands) [Wave 2, depends on 02-02A, 02-02B]

**Wave 3 (depends on Wave 2):**
- [x] 02-01C-PLAN.md -- CLI and tests (agent-registry CLI commands, registry test suite) [Wave 3, depends on 02-01B]

### Phase 3: Interfaces and Triggers
**Goal**: Users can generate configs through conversation, manage running workflows through a dashboard, and trigger workflows from external messaging platforms
**Depends on**: Phase 2 (agent registry for discovery UI, observability for dashboard metrics)
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, ARCH-05, INT-01, INT-02, INT-03
**Success Criteria** (what must be TRUE):
  1. User can describe a desired workflow in natural language through the Gradio chat interface and receive a valid, runnable YAML config
  2. User can close the browser, reopen the chat UI, and continue a previous config generation conversation where they left off
  3. User can view all running workflows, their status, logs, and metrics on the orchestration dashboard and stop or restart a workflow from the UI
  4. User can see registered agents, their capabilities, and health status in the orchestration dashboard
  5. User can send a WhatsApp or Telegram message that triggers a workflow execution, and receive the result back in the same chat
**Plans**: 6 plans (4 waves)

Plans:
**Wave 1 (parallel execution):**
- [x] 03-01-PLAN.md -- Chat UI for config generation (Gradio ChatInterface with session persistence, SQLite-backed chat history, config validation) [Wave 1]
- [x] 03-02-PLAN.md -- Orchestration dashboard (FastAPI + HTMX + SSE, agent discovery UI, MLFlow iframe embed, real-time metrics) [Wave 1]

**Wave 2 (depends on Wave 1):**
- [x] 03-03-PLAN.md -- Generic webhook infrastructure (HMAC validation, idempotency tracking, async workflow execution, generic webhook endpoint) [Wave 2, depends on 03-01, 03-02]

**Wave 3 (depends on Wave 2):**
- [x] 03-03B-PLAN.md -- Platform webhook integrations (WhatsApp Business API handler, Telegram Bot API handler via aiogram 3.x) [Wave 3, depends on 03-03]

**Wave 4 (gap closure):**
- [ ] 03-04-PLAN.md -- Workflow restart implementation (integrate run_workflow_async into dashboard restart endpoint)
- [ ] 03-05-PLAN.md -- Test fixture unpacking fix (update tests to unpack 6 values from create_storage_backend)

### Phase 4: Advanced Capabilities
**Goal**: Users can run agent-generated code safely, leverage persistent memory across executions, use pre-built tools, and optimize prompts through MLFlow experimentation
**Depends on**: Phase 3 (UI for sandbox management, observability for MLFlow optimization)
**Requirements**: RT-04, RT-07, RT-08, OBS-01, ARCH-06
**Success Criteria** (what must be TRUE):
  1. User can configure a workflow node that executes agent-generated Python code in a sandboxed Docker container with network isolation and resource limits
  2. User can run a workflow twice and observe that the second execution uses context from the first (persistent memory across runs)
  3. User can add pre-built tools (web search, API calls, data processing) to workflow nodes via YAML config without writing code
  4. User can run A/B prompt experiments through MLFlow and see which prompt variant produces better results at lower cost
**Plans**: 3 plans

Plans:
- [ ] 04-01: Code execution sandbox (Docker-based isolation with resource limits, network controls, and disposable environments)
- [ ] 04-02: Long-term memory and tool ecosystem (persistent per-agent memory storage, LangChain tools subset integration)
- [ ] 04-03: MLFlow optimization (prompt experimentation, evaluations, A/B testing, quality gates)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Engine | 4/4 | Complete | 2026-02-03 |
| 2. Agent Infrastructure | 6/6 | Complete | 2026-02-03 |
| 3. Interfaces and Triggers | 3/6 (gap closure pending) | In Progress | - |
| 4. Advanced Capabilities | 0/3 | Not started | - |
