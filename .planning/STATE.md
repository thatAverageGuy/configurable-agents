# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** Local-first, config-driven agent orchestration with full observability and zero cloud lock-in
**Current focus:** Phase 2 - Agent Infrastructure

## Current Position

Phase: 2 of 4 (Agent Infrastructure)
Plan: 02B of 6 in current phase
Status: Plan complete
Last activity: 2026-02-03 -- Completed 02-02B-PLAN.md (Performance Profiling and Bottleneck Detection)

Progress: [###       ]  3/12 plans complete (25%)

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 17 min
- Total execution time: 1.99 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1     | 4     | 65    | 16 min   |
| 2     | 3     | 52    | 17 min   |

**Recent Trend:**
- Last 5 plans: 01-04 (11 min), 02-02A (16 min), 02-01A (18 min), 02-01B (20 min), 02-02B (19 min)
- Trend: Phase 2 agent infrastructure progressing steadily

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 4-phase structure compressing research 8-phase suggestion per quick depth setting
- [Roadmap]: LiteLLM chosen as multi-LLM abstraction layer (research validated)
- [Roadmap]: Storage abstraction in Phase 1 as foundational dependency for all later phases
- [Roadmap]: Code execution sandbox deferred to Phase 4 (needs UI from Phase 3 for management)
- [01-01]: SQLAlchemy 2.0 with DeclarativeBase and Mapped/mapped_column for type-safe ORM
- [01-01]: Repository Pattern for storage abstraction enables SQLite to PostgreSQL migration
- [01-01]: Context manager pattern (with Session) prevents transaction leaks in SQLAlchemy 2.0
- [01-02]: Google provider uses direct implementation (not LiteLLM) for optimal LangChain compatibility
- [01-02]: LiteLLM reserved for OpenAI, Anthropic, and Ollama providers
- [01-02]: Ollama uses ollama_chat/ prefix per LiteLLM best practices
- [01-02]: Ollama local models tracked as zero-cost in cost estimator
- [01-03]: Safe condition evaluator using AST-like parsing instead of eval() for security
- [01-03]: Loop iteration tracking via hidden _loop_iteration_{node} state fields with auto-increment
- [01-03]: Parallel execution via LangGraph Send objects with state dict augmentation
- [01-03]: Feature gate version bumped to 0.2.0-dev to reflect flow control capabilities
- [01-04]: Storage repos attached to tracker object to avoid changing build_graph signature
- [01-04]: All storage operations wrapped in try/except for graceful degradation
- [01-04]: Per-node state includes truncated output values (500 chars max) for storage efficiency
- [02-02A]: MultiProviderCostTracker aggregates costs by provider/model combination
- [02-22A]: Provider detection supports openai, anthropic, google, ollama from model names
- [02-02A]: Ollama models return $0.00 cost (local models have no API fees)
- [02-02A]: Per-provider metrics logged to MLFlow as provider_{name}_cost_usd for UI filtering
- [02-01A]: Agent registry uses agent_metadata field name to avoid SQLAlchemy reserved attribute
- [02-01A]: AgentRecord has custom __init__ for default TTL (60s) and heartbeat timestamps
- [02-01A]: Agent registration is idempotent - re-registering updates existing record
- [02-01A]: Background cleanup runs every 60 seconds via asyncio.create_task()
- [02-01A]: TTL heartbeat pattern - agents refresh TTL via /heartbeat endpoint
- [02-01A]: Session management pattern for SQLAlchemy in FastAPI endpoints
- [02-02B]: Thread-local storage for BottleneckAnalyzer enables parallel execution safety
- [02-02B]: Bottleneck threshold uses > (strictly greater than) for detection
- [02-02B]: Per-node timing captured via time.perf_counter() in decorator with try/finally
- [02-02B]: MLFlow metrics: node_{node_id}_duration_ms and node_{node_id}_cost_usd
- [02-02B]: bottleneck_info JSON field in WorkflowRunRecord for historical analysis

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-03
Stopped at: Completed 02-02B-PLAN.md (Performance Profiling and Bottleneck Detection)
Resume file: None
