# Project Vision

> **Note**: This document describes the long-term vision and core philosophy (relatively stable).
> For current implementation status and progress, see [README.md](../README.md#roadmap--status).
> For detailed task breakdown, see [TASKS.md](TASKS.md).

**Last Updated**: 2026-02-02 (phases aligned with current roadmap)

---

## Purpose

Enable anyone to go from **idea to production-grade agent system in minutes** through configuration, not code.

## The Problem

Building agent workflows today requires:
- Manual integration of LLM providers, tools, and orchestration frameworks
- Writing boilerplate for state management, error handling, observability
- Understanding framework-specific abstractions (LangGraph, CrewAI, etc.)
- Deploying and operationalizing custom code

This creates friction for:
- **Developers** prototyping agent ideas
- **Enterprises** needing quick PoCs
- **Researchers** experimenting with agent architectures
- **Practitioners** who want production-grade systems without infrastructure work

## The Solution

A **config-first agent runtime** that:

1. **Takes YAML config as input** describing workflow structure, state, and behavior
2. **Validates everything upfront** (schema, dependencies, tool availability)
3. **Generates and executes** the agent system dynamically
4. **Supports two modes**:
   - **One-shot**: Run once with inputs, return outputs, destroy
   - **Persistent**: Deploy as containerized API service

## Core Philosophy

### Local-First
- Runs entirely on user's machine by default
- No external dependencies beyond LLM API keys
- Data stays local unless user explicitly deploys elsewhere

### Strict Typing
- All inputs and outputs conform to Pydantic schemas defined in config
- No runtime surprises from unstructured LLM outputs
- Validation happens at parse time, not after expensive LLM calls

### Fail Fast, Fail Loud
- Invalid config? Reject immediately with helpful error messages
- Missing dependencies? Catch before execution starts
- LLM timeout? Crash with clear context, don't silently continue

### Boring Technology
- Prefer explicit over implicit
- Prefer composition over abstraction
- Prefer standard tools (Pydantic, LangGraph, MLFlow) over custom frameworks
- Avoid magic; make control flow inspectable

### Production-Grade from Day One
- Testing is non-negotiable
- Observability built in (logging, tracing, metrics)
- Security by default (no accidental file access, command injection)
- Cost control (timeouts, retry limits, token budgets)

## Success Metrics

**v1.0 Achievement (2026-02-04):**
- ✅ A developer can describe a workflow idea in natural language, get a valid config, and have a running agent system in < 5 minutes (UI-01, UI-02)
- ✅ Users can optimize prompts using MLFlow A/B testing without writing code (OBS-01)
- ✅ Enterprise teams can deploy agents as minimal Docker containers with full observability (ARCH-01, OBS-02, OBS-03)
- ✅ System supports 4 LLM providers, 15+ tools, and advanced control flow (RT-01 through RT-08)

**12 months from now (v1.1+):**
- Active community contributing tool integrations and example workflows
- Multi-agent orchestration patterns in production use
- Vector database integration for semantic memory
- Kubernetes deployment patterns for enterprise scale

**3 years from now (v2.0+):**
- Standard tool for agent development, like Docker is for containers
- Supports multi-modal workflows (text, image, video, code execution)
- Cloud deployment abstraction (one config → AWS/GCP/Azure deployment)
- Self-optimizing agents with automatic performance tuning
- Active ecosystem of shared configs and optimized workflows

## Non-Goals

### What We're NOT Building

- **A no-code UI first** — We start with config-as-code. UI comes later (v0.4).
- **A framework lock-in** — Users can export to pure LangGraph/Python if needed.
- **A SaaS-first product** — Self-hosted infrastructure is core. Optional managed SaaS in v0.4 for users who prefer it.
- **General-purpose compute** — This is for LLM agent workflows, not arbitrary scripts.
- **A replacement for LangGraph/CrewAI** — We build on top of them, not compete.

### Explicit Constraints

- **Single runtime per config** — No distributed agent swarms (yet)
- **Structured outputs only** — No raw LLM streaming (parse to Pydantic first)
- **Declarative configs** — No Turing-complete logic in YAML
- **Local execution first** — Cloud deployment is an extension, not the core

## Roadmap Progress

### v1.0 - Foundation (SHIPPED 2026-02-04)
- **Status**: Complete ✅
- **Requirements**: 27/27 (100%)
- **Phases**: 4 phases, 19 plans

**Core Capabilities**:
- Config-driven architecture (YAML/JSON)
- Advanced control flow (conditional routing, loops, parallel execution)
- Structured outputs (Pydantic validation)
- Multi-LLM support (Google, OpenAI, Anthropic, Ollama)
- Tool integration (15+ pre-built tools, extensible registry)
- Parse-time validation (fail fast, save costs)
- MLFlow observability (cost tracking, tracing, prompt inspection, optimization)
- Agent registry (heartbeat/TTL, minimal containers)
- Orchestration dashboard (FastAPI + HTMX + SSE)
- Chat UI for config generation (Gradio with session persistence)
- Webhook integrations (generic, WhatsApp, Telegram)
- Sandbox code execution (RestrictedPython + Docker opt-in)
- Long-term memory backend (namespaced key-value storage)
- Comprehensive testing (645 tests: 626 unit + 19 integration)

**Documentation**: See [TASKS.md](TASKS.md) for complete requirements mapping.

### v1.1 - Enhancement (PLANNING)
- **Status**: Not started
- **Estimated**: Q2 2026, +8-12 weeks

**Potential Features** (under consideration):
- Orchestrator-initiated agent registration (complete ARCH-02)
- Enhanced tool ecosystem (expand beyond 15 tools)
- Vector database integration for semantic memory
- DSPy module integration and optimization
- OpenTelemetry integration
- Kubernetes deployment manifests
- Enhanced dashboard features

**Planning Process**: TBD based on user feedback and v1.0 usage patterns.

### v2.0 - Scale (DEFERRED)
- Self-optimizing agents (auto-scaling runtime)
- Enterprise features (multi-tenancy, RBAC)
- Full LangChain tool registry (500+ tools)
- Visual workflow builder (drag-and-drop)
- Advanced memory (contextual/agentic, Agent Protocol)
- Cloud-managed service (optional SaaS offering)

## Guiding Questions

When making decisions, ask:

1. **Does this add complexity or remove it?** (Prefer removal)
2. **Can a user understand this by reading the config?** (Prefer transparency)
3. **Will this break existing configs?** (Avoid breaking changes)
4. **Is this testable?** (If not, rethink the design)
5. **Does this fail fast?** (Catch errors early, not late)

## Inspiration

- **Docker**: Config → container (we do config → agent)
- **Terraform**: Declarative infrastructure (we do declarative workflows)
- **FastAPI**: Developer experience and validation (Pydantic everywhere)
- **LangGraph**: Explicit state machines (we build on this)
- **DSPy**: Optimization as first-class (we integrate this)
