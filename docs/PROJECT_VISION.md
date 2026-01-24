# Project Vision

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

**12 months from now:**
- A developer can describe a workflow idea in natural language, get a config, and have a running agent system in < 5 minutes
- Users can optimize prompts using DSPy without writing code
- Enterprise teams use this for PoCs and production deployments
- Community contributes tool integrations and example workflows

**3 years from now:**
- Standard tool for agent development, like Docker is for containers
- Supports multi-modal workflows (text, image, video, code execution)
- Cloud deployment abstraction (one config → AWS/GCP/Azure deployment)
- Active ecosystem of shared configs and optimized workflows

## Non-Goals

### What We're NOT Building

- **A no-code UI first** — We start with config-as-code. UI comes later.
- **A framework lock-in** — Users can export to pure LangGraph/Python if needed.
- **A hosted service** — This is infrastructure you run, not SaaS.
- **General-purpose compute** — This is for LLM agent workflows, not arbitrary scripts.
- **A replacement for LangGraph/CrewAI** — We build on top of them, not compete.

### Explicit Constraints

- **Single runtime per config** — No distributed agent swarms (yet)
- **Structured outputs only** — No raw LLM streaming (parse to Pydantic first)
- **Declarative configs** — No Turing-complete logic in YAML
- **Local execution first** — Cloud deployment is an extension, not the core

## Phases

### Phase 1: Core Engine (v0.1-v0.3)
- Config schema and validator
- Linear execution (sequential steps)
- Google Gemini + basic tools
- One-shot mode
- Comprehensive testing

### Phase 2: Enhanced Runtime (v0.4-v0.6)
- Conditional branching and loops
- Persistent/container mode
- Multiple LLM providers (OpenAI, Anthropic, local models)
- MLFlow observability integration
- Tool registry expansion

### Phase 3: Optimization & Deployment (v0.7-v0.9)
- DSPy prompt optimization
- Feedback collection UI
- LLM-as-judge evaluation
- Cloud deployment templates (ECS, Lambda, Fargate)
- Cost tracking and budgets

### Phase 4: Advanced Features (v1.0+)
- Multi-agent delegation and hierarchical workflows
- Long-term memory (vector DBs, SQLite)
- Config generator chatbot
- Web UI for config editing and monitoring
- Multi-modal support (vision, audio, code execution)

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
