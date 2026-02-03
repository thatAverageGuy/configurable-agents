# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** Local-first, config-driven agent orchestration with full observability and zero cloud lock-in
**Current focus:** Phase 2 - Agent Infrastructure

## Current Position

Phase: 2 of 4 (Agent Infrastructure)
Plan: 01C of 6 in current phase
Status: In progress
Last activity: 2026-02-03 -- Completed 02-01C-PLAN.md (Agent Registry CLI & Tests)

Progress: [#######   ]  7/12 plans complete (58%)

## Performance Metrics

**Velocity:**
- Total plans completed: 13
- Average duration: 18 min
- Total execution time: 3.98 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1     | 4     | 65    | 16 min   |
| 2     | 7     | 144   | 21 min   |

**Recent Trend:**
- Last 5 plans: 02-01B (20 min), 02-02A (16 min), 02-02B (19 min), 02-01C (41 min), 02-02C (18 min)
- Trend: Phase 2 agent infrastructure progressing, observability complete

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
- [02-01B]: Heartbeat interval default (20s) is ~1/3 of TTL (60s) for reliable refresh
- [02-01B]: Retry delay (5s) on heartbeat HTTP errors balances responsiveness with load
- [02-01B]: Host/port auto-detected from AGENT_HOST/AGENT_PORT env vars with socket.gethostname() fallback
- [02-01B]: Deregistration is best-effort - errors logged but not raised (agent shutting down)
- [02-01B]: Conditional code generation via template variables populated or empty based on enable_registry flag
- [02-01B]: httpx>=0.26.0 used for async HTTP in registry client
- [02-01C]: Heartbeat background task runs on separate async task with while True loop
- [02-01C]: Shutdown Event set by signal handler for graceful cleanup
- [02-01C]: Cleanup interval (60s) matches default TTL for efficient stale agent removal
- [02-01C]: SQLAlchemy Session injected into cleanup endpoint for storage access
- [02-02C]: Rich library (>=13.0.0) for formatted CLI table output
- [02-02C]: Lazy MLFlow import in CLI functions allows help without MLFlow installed
- [02-02C]: CLI observability group with status/cost-report/profile-report subcommands
- [02-02C]: --enable-profiling flag sets CONFIGURABLE_AGENTS_PROFILING env var for runtime control
- [02-02C]: Cost report highlights most expensive provider in bold/yellow
- [02-02C]: Profile report highlights slowest node in bold/red, bottlenecks (>50%) in yellow
- [02-01C]: CLI uses argparse instead of Typer for consistency with existing commands
- [02-01C]: Rich library for formatted table output in list command
- [02-01C]: httpx.AsyncClient with ASGITransport for server testing (avoids httpx 0.28 compatibility)
- [02-01C]: Heartbeat loop CancelledError handling exits immediately instead of retrying

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-03
Stopped at: Completed 02-01C-PLAN.md (Agent Registry CLI & Tests)
Resume file: None
