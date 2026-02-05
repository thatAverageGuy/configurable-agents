# Development Context

> **Purpose**: Quick context for resuming development. Updated after each task completion.
>
> **For LLMs**: Read this first to understand current state, next action, and project standards.
> Fetch details from linked docs as needed during implementation.

---

**Last Updated**: 2026-02-04
**Current Phase**: v1.0 MILESTONE SHIPPED
**Latest Completion**: v1.0 Foundation (2026-02-04)
**Next Action**: Plan v1.1 features
**Status**: v1.0 complete with all 27 requirements satisfied, ready for production use

---

## v1.0 Milestone Summary

**Shipped**: 2026-02-04

v1.0 transforms the system from a v0.1 linear workflow runner into a full-featured local-first agent orchestration platform with:

### Core Capabilities Delivered

**Advanced Control Flow**:
- Conditional routing (if/else based on state)
- Loop execution (retry logic, iteration with termination conditions)
- Parallel node execution (concurrent agent operations via fan-out/fan-in)

**Multi-LLM Support**:
- Google Gemini (direct LangChain implementation for optimal compatibility)
- OpenAI (via LiteLLM wrapper)
- Anthropic Claude (via LiteLLM wrapper)
- Ollama local models (zero-cost, full privacy)

**Agent Infrastructure**:
- Agent registry with heartbeat/TTL pattern
- Minimal container images (~50-100MB)
- Agent-initiated registration (orchestrator-initiated deferred to post-v1)
- Multi-provider cost tracking
- Performance profiling with bottleneck detection

**User Interfaces**:
- Gradio-based chat UI for config generation with session persistence
- FastAPI + HTMX orchestration dashboard (no JS frameworks)
- Server-Sent Events (SSE) for real-time updates
- MLFlow UI integration (iframe embed)

**External Integrations**:
- Generic webhook infrastructure (HMAC signature verification)
- WhatsApp Business API integration
- Telegram Bot API integration (aiogram 3.x)

**Advanced Capabilities**:
- RestrictedPython sandbox for code execution (Docker opt-in)
- Long-term memory backend with namespace patterns
- 15+ pre-built LangChain tools
- MLFlow optimization system (A/B testing, quality gates)

**Observability**:
- MLFlow 3.9+ automatic tracing
- Per-node metrics (latency, tokens, cost)
- Multi-provider cost aggregation
- Execution traces with detailed logging

### Requirements Satisfied

**Total**: 27/27 requirements (100%)
- Runtime: 8/8 (RT-01 through RT-08)
- Observability: 4/4 (OBS-01 through OBS-04)
- User Interface: 6/6 (UI-01 through UI-06)
- Architecture: 6/6 (ARCH-01 through ARCH-06)
- Integration: 3/3 (INT-01 through INT-03)

See [docs/TASKS.md](TASKS.md) for complete requirements mapping.

### Phase Execution

**Phase 1: Core Engine** (4 plans, complete 2026-02-03)
- Storage abstraction layer
- Multi-LLM provider integration
- Advanced control flow
- Storage-executor integration

**Phase 2: Agent Infrastructure** (6 plans, complete 2026-02-03)
- Agent registry server and client
- Multi-provider cost tracking
- Performance profiling
- CLI observability commands

**Phase 3: Interfaces and Triggers** (6 plans, complete 2026-02-03)
- Gradio chat UI for config generation
- FastAPI + HTMX orchestration dashboard
- Generic webhook infrastructure
- Platform webhook integrations (WhatsApp, Telegram)
- Workflow restart implementation
- Test fixture fixes

**Phase 4: Advanced Capabilities** (3 plans, complete 2026-02-04)
- Code execution sandbox (RestrictedPython + Docker)
- Long-term memory and tool ecosystem
- MLFlow optimization system

---

## What Works Right Now

```bash
# Complete end-to-end workflow execution with control flow
configurable-agents run workflow.yaml --input topic="AI"

# Multi-LLM provider execution
configurable-agents run workflow.yaml --input topic="AI" --provider openai

# Local model execution (zero cost)
configurable-agents run workflow.yaml --input topic="AI" --provider ollama

# Config validation
configurable-agents validate workflow.yaml

# Orchestration dashboard
configurable-agents dashboard

# Webhook server
configurable-agents webhooks

# Chat UI for config generation
configurable-agents chat

# Observability commands
configurable-agents report costs
configurable-agents report profile
configurable-agents optimization evaluate workflow.yaml

# Python API
from configurable_agents.runtime import run_workflow
result = run_workflow("workflow.yaml", {"topic": "AI"})
```

**Key Capabilities**:
- ✅ YAML/JSON config parsing and validation (Schema v1.0 + extensions)
- ✅ Dynamic Pydantic state and output models
- ✅ Multi-LLM support (Google, OpenAI, Anthropic, Ollama)
- ✅ Conditional routing, loops, and parallel execution
- ✅ Tool registry (15+ pre-built tools)
- ✅ LangGraph execution engine with advanced control flow
- ✅ CLI interface with smart input parsing
- ✅ MLFlow observability (cost tracking, workflow metrics, automatic tracing)
- ✅ Agent registry with heartbeat/TTL lifecycle
- ✅ FastAPI + HTMX dashboard (orchestration, monitoring)
- ✅ Gradio chat UI (config generation with session persistence)
- ✅ Webhook infrastructure (generic, WhatsApp, Telegram)
- ✅ Sandbox code execution (RestrictedPython + Docker opt-in)
- ✅ Long-term memory backend (namespaced key-value storage)
- ✅ MLFlow optimization (A/B testing, quality gates)
- ✅ Comprehensive documentation

---

## Next Action: Plan v1.1 Features

With v1.0 complete, the next milestone should focus on:

### Potential v1.1 Features

**Enhanced Multi-Agent Orchestration**:
- Orchestrator-initiated agent registration (ARCH-02 completion)
- Multi-agent workflow patterns (agent swarms, hierarchical agents)
- Agent communication protocols

**Enhanced Tool Ecosystem**:
- Expand LangChain tool registry (beyond 15 tools)
- Custom tool registration via CLI
- Tool composition and chaining

**Enhanced Memory**:
- Vector database integration for semantic memory
- RAG pattern support
- Context window optimization

**Enhanced Optimization**:
- DSPy module integration and optimization
- Prompt engineering automation
- Multi-arm bandit experiments

**Enhanced Observability**:
- OpenTelemetry integration
- Distributed tracing across agents
- Real-time dashboard enhancements

**Enhanced Deployment**:
- Kubernetes deployment manifests
- Helm charts for cloud deployment
- Auto-scaling policies

**Planning Process**:
1. Review v2 deferred requirements
2. Prioritize based on user feedback and usage patterns
3. Create roadmap document in `.planning/milestones/v1.1-ROADMAP.md`
4. Break down into phases and plans
5. Begin implementation

---

## Documentation Map

### Core Technical Docs (Stable, Reference)

| Document | Purpose | When to Read |
|----------|---------|--------------|
| **PROJECT_VISION.md** | Long-term vision, philosophy, non-goals | Understanding "why" and project direction |
| **ARCHITECTURE.md** | System design, patterns, components (v1.0) | Understanding "how" the system works |
| **SPEC.md** | Schema v1.0 specification + v1.0 extensions | Implementing config-related features |
| **TASKS.md** | v1.0 requirements status (27/27 complete) | Understanding what was delivered |

### Milestone Archives (Historical, v1.0)

| Document | Purpose | When to Read |
|----------|---------|--------------|
| **.planning/milestones/v1.0-ROADMAP.md** | v1.0 roadmap with 4 phases | Understanding v1.0 execution |
| **.planning/milestones/v1.0-REQUIREMENTS.md** | v1.0 requirements archive | Understanding v1.0 scope |
| **.planning/milestones/v1.0-MILESTONE-AUDIT.md** | v1.0 completion audit | Understanding v1.0 delivery |

### Implementation Records (Historical, Detailed)

| Document | Purpose | When to Read |
|----------|---------|--------------|
| **CHANGELOG.md** | Release notes (standard format, user-facing) | Understanding what changed per release |
| **adr/** | Architecture Decision Records (25+ ADRs) | Understanding why a design choice was made |

### User-Facing Docs (External)

| Document | Purpose | Audience |
|----------|---------|----------|
| **QUICKSTART.md** | 5-minute tutorial | New users |
| **CONFIG_REFERENCE.md** | Config schema guide | Config authors |
| **TROUBLESHOOTING.md** | Common errors and fixes | Users debugging issues |
| **OBSERVABILITY.md** | MLFlow setup and usage | Users tracking costs |
| **DEPLOYMENT.md** | Docker deployment | Users deploying workflows |

### Living Documents (Updated Frequently)

| Document | Purpose | Update Frequency |
|----------|---------|------------------|
| **CONTEXT.md** (this file) | Current state, next action, dev context | After each milestone |
| **README.md** | Project overview, progress, quickstart | Per release |

---

## Implementation Standards

### Code Principles

**Philosophy**:
- **Local-First**: Runs on user's machine, data stays local
- **Strict Typing**: All inputs/outputs are Pydantic models
- **Fail Fast, Fail Loud**: Validate at parse time, clear errors, no silent failures
- **Boring Technology**: Explicit > implicit, composition > abstraction
- **Production-Grade**: Testing non-negotiable, observability built in

### Testing Requirements

**Test Strategy**:
- **Unit tests** (645+): Mock LLM/APIs, fast, free
- **Integration tests** (19+): Real APIs, cost-tracked (<$0.50 per PR)
- **Cost tracking**: Integration tests must track and report API costs

**Running Tests**:
```bash
# Unit tests (fast, free)
pytest tests/ --ignore=tests/integration/

# Integration tests (slow, costs $0.50)
pytest tests/integration/ -v

# All tests
pytest -v
```

### Change Control

**CRITICAL**: All changes must declare a CHANGE LEVEL.

| Level | Scope | Requirements |
|-------|-------|--------------|
| **LEVEL 0** | Read only (questions, analysis) | Default mode, no file modifications |
| **LEVEL 1** | Surgical edits (~20 lines, existing files only) | No new files, no refactoring |
| **LEVEL 2** | Local changes (single logical area) | Public interfaces stable, typical for tasks |
| **LEVEL 3** | Structural changes (multi-file, architectural) | **Requires ADR** or updating ARCHITECTURE.md |

---

## Quick Commands

```bash
# Run tests
pytest tests/ --ignore=tests/integration/  # Unit only (fast)
pytest tests/integration/ -v                # Integration only (slow, $$)
pytest -v                                   # All tests

# Run workflow
configurable-agents run workflow.yaml --input topic="AI"
configurable-agents validate workflow.yaml

# Dashboard and webhooks
configurable-agents dashboard  # FastAPI + HTMX dashboard
configurable-agents webhooks   # Webhook server

# Observability
configurable-agents report costs
configurable-agents report profile
configurable-agents optimization evaluate workflow.yaml

# Check code
ruff check src/      # Linting
mypy src/            # Type checking

# Git
git log --oneline -10  # Recent commits
git diff main          # Changes since main
```

---

## Key Files Reference

### Most Frequently Modified

- `src/configurable_agents/core/graph_builder.py` - LangGraph construction with control flow
- `src/configurable_agents/config/schema.py` - Pydantic models (v1.0 base + extensions)
- `src/configurable_agents/runtime/executor.py` - Workflow execution orchestration
- `docs/TASKS.md` - v1.0 requirements tracking
- `docs/CONTEXT.md` - This file (update after each milestone)

### Key Entry Points

- `src/configurable_agents/runtime/executor.py:run_workflow()` - Main execution function
- `src/configurable_agents/cli.py:main()` - CLI entry point
- `src/configurable_agents/dashboard/server.py` - Dashboard server
- `src/configurable_agents/webhooks/server.py` - Webhook server

### Configuration

- `pyproject.toml` - Dependencies, project metadata
- `.env.example` - Required environment variables
- `pytest.ini` - Test configuration

---

## Architecture References

**Detailed Decisions**: [Architecture Decision Records](adr/) (25+ ADRs)

**Key v1.0 ADRs**:
- [ADR-019](adr/ADR-019-litellm-integration.md) - LiteLLM Multi-Provider Integration
- [ADR-020](adr/ADR-020-agent-registry.md) - Agent Registry Architecture
- [ADR-021](adr/ADR-021-htmx-dashboard.md) - HTMX Dashboard Framework
- [ADR-022](adr/ADR-022-restrictedpython-sandbox.md) - RestrictedPython Sandbox
- [ADR-023](adr/ADR-023-memory-backend.md) - Memory Backend Design
- [ADR-024](adr/ADR-024-webhook-integration.md) - Webhook Integration Pattern
- [ADR-025](adr/ADR-025-optimization-architecture.md) - Optimization Architecture

**Version Features**: [README.md](../README.md#roadmap--status) (v1.0 complete)

**Technical Specs**: [SPEC.md](SPEC.md) (Complete config schema reference + v1.0 extensions)

---

## v1.0 Capabilities Reference

### Conditional Routing

Users can define conditional branches in workflows:

```yaml
edges:
  - from: validate_node
    routes:
      - condition:
          logic: "{state.score} >= 8"
        to: END
      - condition:
          logic: "default"
        to: rewrite_node
```

### Loop Execution

Users can define retry logic and iteration:

```yaml
nodes:
  - id: retry_node
    loop:
      max_iterations: 3
      until: "{state.success} == true"
```

### Parallel Execution

Users can execute nodes concurrently:

```yaml
edges:
  - from: START
    parallel:
      - node_1
      - node_2
      - node_3
    join: merge_node
```

### Multi-LLM Providers

Users can configure any supported LLM per node:

```yaml
config:
  llm:
    provider: "openai"
    model: "gpt-4-turbo"

nodes:
  - id: creative_node
    llm:
      provider: "anthropic"
      model: "claude-3-opus"
```

### Sandbox Code Execution

Users can run agent-generated code safely:

```yaml
nodes:
  - id: data_processor
    code: |
      result = process_data(data)
      return {"output": result}
```

### Long-Term Memory

Users can configure persistent memory:

```yaml
nodes:
  - id: learning_node
    memory:
      write:
        - key: "user_preference"
          value: "{state.preference}"
      read:
        - key: "user_preference"
          as: "saved_preference"
```

### Webhook Configuration

Users can configure webhook integrations:

```yaml
config:
  webhooks:
    enabled: true
    secret: "webhook_secret_key"
    platforms:
      whatsapp:
        phone_id: "123456789"
        access_token: "token"
```

### Optimization

Users can enable MLFlow optimization:

```yaml
optimization:
  enabled: true
  strategy: "BootstrapFewShot"
  metric: "semantic_match"
  max_demos: 8
```

---

*Last Updated: 2026-02-04 | v1.0 Complete - Ready for v1.1 Planning*
