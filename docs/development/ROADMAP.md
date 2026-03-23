# Roadmap

**Last Updated**: 2026-03-23
**Author**: thatAverageGuy

This document is the authoritative source for what has been built, what is being built now, and what is planned but deferred. Each phase has a clear prerequisite dependency on the previous phase.

---

## Phase 1 — v1.0: Core Platform (SHIPPED 2026-02-04)

**Theme**: Make it work correctly and completely.

**Delivered**:
- Config-driven multi-agent workflows via YAML
- 4 LLM providers (OpenAI, Anthropic, Google, Ollama) via LiteLLM
- Advanced control flow: conditional routing, loops, parallel execution
- Persistent memory (SQLite-backed, agent/workflow/node scope)
- Code execution sandbox (RestrictedPython + Docker)
- 15 pre-built tools (web, file, data, system)
- Gradio Chat UI for config generation
- FastAPI + HTMX Orchestration Dashboard
- MLFlow 3.9 tracing, cost tracking, performance profiling
- Webhook triggers: WhatsApp, Telegram, generic HTTP
- Docker Compose deployment artifact generation

**Status**: 27/27 requirements complete. All verified.

**Details**: [TASKS.md — Phase 1-4](TASKS.md)

---

## Phase 1.1 — v1.1: Hardening & Usability (IN PROGRESS — 2026-03-23)

**Theme**: Fix what's broken, make it trustworthy for production use.

**Context**: A detailed code audit (2026-03-23) surfaced bugs and design gaps in the v1.0 implementation that affect correctness, cost predictability, and usability. This phase addresses those before any new capabilities are added.

**Active Tasks**:

| ID | Type | Summary | Status |
|----|------|---------|--------|
| BF-010 | Bug Fix | Loop `max_iterations` guard broken — counter never persists | TODO |
| BF-011 | Bug Fix | List field reducer always appends — loops accumulate stale data | TODO |
| BF-012 | Bug Fix | CostEstimator called twice per node — wasted compute, inconsistent | TODO |
| BF-013 | Bug Fix | Route condition failures silently skipped — no log, falls to default | TODO |
| T-014 | Feature | Runtime memory override — per-invocation scope control, no config change | TODO |
| T-015 | Feature | Memory fact extraction opt-in — currently always-on, doubles LLM cost | TODO |
| T-016 | Feature | Web search hardening — retry, fallback, caching, result validation | TODO |

**Details**: [TASKS.md — v1.1 Section](TASKS.md) | [Implementation Logs](implementation_logs/phase_6_v1_1_hardening/)

**Exit criteria**: All 7 tasks complete, tests passing, no regressions on existing configs.

---

## Phase 2 — Autonomous Expansion (DEFERRED — start date TBD)

**Theme**: Make it capable of reasoning about and expanding its own structure.

**Context**: The long-term vision for this system is a hierarchical, path-traceable autonomous workflow platform — not just a DAG runner. Phase 1 and 1.1 build the deterministic foundation. Phase 2 adds the autonomous layer on top.

**Key Capabilities**:

- **Autonomy levels (0–3)**: Configurable dial from fully deterministic to self-generative
- **Dynamic workflow expansion**: Workflows that can add nodes/branches at runtime based on task scope
- **Expansion modality**: Ephemeral (this run only) or persistent (written back to config)
- **Structural memory**: A second memory tier that stores workflow patterns, routing decisions, and "what worked" — distinct from content memory (facts/context)
- **Path-based traceability**: Every execution decision is a graph transition with a logged path, not a free-form string — fully auditable and replayable
- **Self-evolution**: Workflows that improve their own structure over time via structural memory

**Prerequisite**: Phase 1.1 complete. Specifically: runtime overrides layer (T-014), stable loop behavior (BF-010/011), and reliable observability.

**Details**: [VISION_AUTONOMOUS.md](VISION_AUTONOMOUS.md) | [TASKS.md — Phase 2 Deferred](TASKS.md)

---

## Phase 3 — Enterprise Scale (FURTHER DEFERRED)

**Theme**: Make it run at scale with multi-tenant isolation and enterprise integrations.

**Key Capabilities**:
- Kubernetes deployment with Helm charts and auto-scaling
- Multi-tenancy with RBAC
- OpenTelemetry integration for enterprise observability
- Full LangChain tool registry (500+ tools)
- Visual workflow builder (drag-and-drop)
- DSPy prompt optimization (if MLFlow optimization proves insufficient)

**Prerequisite**: Phase 2 complete.

---

## Decision Log — Key Deferred Decisions

| Decision | Deferred To | Reason |
|---|---|---|
| DSPy prompt optimization | Phase 3 (conditional) | MLFlow 3.9 has evaluation features; test those first. DSPy if cross-LLM consistency needed. |
| Vector/semantic memory (Mem0, LightRAG) | Phase 2 | Current KV memory sufficient for Phase 1 use cases |
| Visual workflow builder | Phase 3 | Config-first philosophy; YAML + Chat UI covers Phase 1-2 use cases |
| Kubernetes / Helm | Phase 3 | Docker Compose covers Phase 1-2 deployment needs |
| A2A / MCP protocol support | Phase 2 | Cross-platform interoperability not needed until autonomous expansion |

---

*This roadmap is a living document. Phase start dates are determined by the owner when prerequisites are met.*
