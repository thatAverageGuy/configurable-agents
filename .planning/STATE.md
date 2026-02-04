# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** Local-first, config-driven agent orchestration with full observability and zero cloud lock-in
**Current focus:** All phases complete

## Current Position

Phase: 4 of 4 (Advanced Capabilities)
Plan: 3 of 3 in current phase
Status: Phase complete, verified
Last activity: 2026-02-04 -- Completed Phase 4 (Advanced Capabilities)

Progress: [##########]  18/18 plans complete (100% of all phases)

## Performance Metrics

**Velocity:**
- Total plans completed: 18
- Average duration: 20 min
- Total execution time: 6.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1     | 4     | 65    | 16 min   |
| 2     | 6     | 106   | 18 min   |
| 3     | 6     | 106   | 18 min   |
| 4     | 3     | 151   | 50 min   |

**Recent Trend:**
- Last 3 plans: 04-03 (45 min), 04-02 (45 min), 04-01 (61 min)
- Trend: All 4 phases complete and verified

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
- [02-01A]: Agent registry uses agent_metadata field name to avoid SQLAlchemy reserved attribute
- [02-01A]: AgentRecord has custom __init__ for default TTL (60s) and heartbeat timestamps
- [02-01A]: Agent registration is idempotent - re-registering updates existing record
- [02-01A]: Background cleanup runs every 60 seconds via asyncio.create_task()
- [02-01A]: TTL heartbeat pattern - agents refresh TTL via /heartbeat endpoint
- [02-01A]: Session management pattern for SQLAlchemy in FastAPI endpoints
- [02-02A]: MultiProviderCostTracker aggregates costs by provider/model combination
- [02-02A]: Provider detection supports openai, anthropic, google, ollama from model names
- [02-02A]: Ollama models return $0.00 cost (local models have no API fees)
- [02-02A]: Per-provider metrics logged to MLFlow as provider_{name}_cost_usd for UI filtering
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
- [02-02C]: Rich library (>=13.0.0) for formatted CLI table output
- [02-02C]: Lazy MLFlow import in CLI functions allows help without MLFlow installed
- [02-02C]: CLI observability group with status/cost-report/profile-report subcommands
- [02-02C]: --enable-profiling flag sets CONFIGURABLE_AGENTS_PROFILING env var for runtime control
- [02-02C]: Cost report highlights most expensive provider in bold/yellow
- [02-02C]: Profile report highlights slowest node in bold/red, bottlenecks (>50%) in yellow
- [02-01C]: CLI uses argparse for consistency with existing commands
- [02-01C]: Rich library for formatted table output in list command
- [02-01C]: httpx.AsyncClient with ASGITransport for server testing (avoids httpx 0.28 compatibility)
- [02-01C]: Heartbeat loop CancelledError handling exits immediately instead of retrying
- [02-02C]: Orchestrator-initiated registration (ARCH-02) deferred to Phase 3 for dashboard integration
- [03-02]: HTMX chosen for dynamic updates without JavaScript frameworks
- [03-02]: Server-Sent Events (SSE) for one-way real-time data pushing to clients
- [03-02]: Repository injection via app.state for route dependency access
- [03-02]: Partial template swaps (hx-swap="outerHTML") for efficient HTMX updates
- [03-02]: SSE streaming pattern: async generator yielding formatted event strings
- [03-01]: Gradio 6.x requires theme/css parameters in launch() method, not Blocks constructor
- [03-01]: ChatMessage uses message_metadata column name to avoid SQLAlchemy reserved word
- [03-01]: stream_chat() async generator pattern for non-blocking LLM responses
- [03-01]: Session ID derived from request.client.host:port for browser-based continuity
- [03-03]: HMAC signature verification uses hmac.compare_digest() for timing-attack safety
- [03-03]: INSERT OR IGNORE pattern for idempotent webhook_id marking
- [03-03]: Async wrapper run_workflow_async() using asyncio.run_in_executor()
- [03-03]: Optional signature validation - only when WEBHOOK_SECRET configured
- [03-03]: Generic webhook endpoint accepts workflow_name and inputs for universal triggering
- [03-03B]: Used aiogram 3.x with modern async/await patterns (not legacy aiogram 2.x callbacks)
- [03-03B]: Lazy initialization of platform handlers only when env vars configured
- [03-03B]: Message chunking for Telegram's 4096 char limit and WhatsApp's 4096 char limit
- [03-03B]: Factory functions for Bot and Dispatcher instead of singletons for testability
- [03-03B]: CLI webhooks command follows existing patterns from dashboard command
- [03-03B]: GET /webhooks/whatsapp returns challenge for Meta webhook verification
- [03-04]: Temp file pattern: config_snapshot saved to temp YAML for run_workflow_async() compatibility
- [03-04]: BackgroundTasks for non-blocking restart execution with finally block cleanup
- [03-04]: JSONResponse instead of Response for consistent error handling in restart endpoint
- [04-01]: Use 'result' variable instead of '__result' for sandbox code (RestrictedPython blocks underscore-prefixed names)
- [04-01]: Pass _SafePrint class (not instance) as _print_ global for RestrictedPython compatibility
- [04-01]: Custom _safe_getattr allows _call_print while blocking other private attributes
- [04-01]: Extract actual values from state for sandbox inputs instead of stringified template results
- [04-01]: Resource presets (low/medium/high/max) for configurable CPU, memory, and timeout limits
- [04-02]: Memory namespace pattern: "{agent_id}:{workflow_id or \"*\"}:{node_id or \"*\"}:{key}"
- [04-02]: Dict-like read with explicit write: agent.memory['key'] vs agent.memory.write('key', value)
- [04-02]: Tool factory pattern: def create_tool() -> Tool for lazy loading and validation
- [04-02]: Security whitelisting: ALLOWED_PATHS for file ops, ALLOWED_COMMANDS for shell
- [04-02]: Error handling continuation: on_error: 'continue' catches errors and returns error dict
- [04-02]: SQL queries limited to SELECT only for safety (rejects DROP, DELETE, UPDATE, INSERT, ALTER, CREATE)
- [04-03]: Percentile calculation uses nearest-rank method (index = ceil(p/100 * n) - 1)
- [04-03]: Quality gates support three actions: WARN (logs), FAIL (raises), BLOCK_DEPLOY (sets flag)
- [04-03]: A/B test variants applied via config override to preserve workflow integrity
- [04-03]: Automatic YAML backup created when applying optimized prompts
- [04-03]: CLI optimization group follows existing pattern (evaluate, apply-optimized, ab-test)
- [04-03]: MLFlow experiment aggregation with p50/p95/p99 percentiles for metrics

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-04
Stopped at: Phase 4 complete, all phases verified
Resume file: None
