# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

For detailed task-by-task implementation notes, see [implementation logs](docs/development/implementation_logs/) and [planning archives](.planning/milestones/).

---

## [Unreleased]

### Added
- **CL-001: Documentation Reorganization** (2026-02-06)
  - Created `docs/user/` for user-facing documentation
  - Moved internal docs to `docs/development/` (PROJECT_VISION.md, ARCHITECTURE.md, SPEC.md)
  - Created `docs/development/session_context/` for archived session contexts
  - Updated CLAUDE.md with permanent project instructions (workflow, task naming, completion criteria)
  - Rewrote CONTEXT.md with new streamlined structure

- **ARCH-02 Complete: Orchestrator-Initiated Agent Registration** (2026-02-06)
- **ARCH-02 Complete: Orchestrator-Initiated Agent Registration** (2026-02-06)
  - Manual agent registration via dashboard UI
  - Live health monitoring with HTMX polling (every 10s)
  - Execute workflows on remote agents
  - Agent execution history with filterable views
  - Orchestrator embedded in dashboard (not separate service)
  - 14/14 integration tests passing

### Changed
- Updated ADR-020 to mark ARCH-02 as complete (was deferred)
- Updated docs/TASKS.md to reflect ARCH-02 completion
- Enhanced workflows table with Agent ID column
- Added agent filter to execution history page

### Fixed
- ImportError: WorkflowRunRepository → AbstractWorkflowRunRepository
- SQLite type error: metadata dict requires JSON serialization
- Repository method errors: use update_status() and update_run_completion()
- Wrong redirect URL: /runs/ → /workflows/

---

## [1.0.0] - 2026-02-04

### 🎉 Major Release: Production-Ready Multi-Agent Orchestration Platform

**v1.0 Foundation** - 4 phases, 19 plans, 27 requirements, 1,000+ tests (98%+ pass rate)

Transformed from a simple linear workflow runner (v0.1) into a full-featured local-first agent orchestration platform with multi-LLM support, advanced control flow, complete observability, and zero cloud lock-in.

---

### Phase 1: Core Engine (4 plans)

#### Multi-LLM Support via LiteLLM
- **4 LLM providers**: OpenAI, Anthropic, Google Gemini, Ollama
- **Unified cost tracking**: Track costs across all providers in one place
- **Zero-cloud option**: Run entirely on Ollama local models (no API keys needed)
- **Per-node configuration**: Mix providers in a single workflow
- **Provider switching**: Change one line in config to switch providers
- **Local model support**: Ollama integration with zero API costs

#### Advanced Control Flow
- **Conditional routing**: Branch based on agent outputs (if/else logic)
- **Loops and retry**: Iterate until termination conditions met
- **Parallel execution**: Fan-out/fan-in patterns for concurrent operations
- **Safe condition evaluation**: AST-based parsing (no eval() security risks)
- **Loop iteration tracking**: Hidden state fields with auto-increment
- **LangGraph Send API**: Parallel state augmentation

#### Storage Abstraction
- **Pluggable backends**: SQLite, PostgreSQL, Redis (swap without code changes)
- **SQLite default**: Zero-config experience for local development
- **Factory pattern**: Backend selection via configuration
- **Session management**: Context managers for transaction safety
- **WAL mode**: Concurrent reads during writes
- **Graceful degradation**: Storage failures don't crash workflows

#### Execution Traces
- **Workflow run persistence**: All executions stored to database
- **Per-node metrics**: Latency, tokens, cost per node
- **Detailed traces**: Complete execution history
- **State snapshots**: Truncated output values for storage efficiency
- **Query interface**: Retrieve historical runs

---

### Phase 2: Agent Infrastructure (6 plans)

#### Agent Registry with Heartbeat/TTL
- **Service discovery**: Agents register on startup
- **Health monitoring**: Heartbeat mechanism (20s interval, 60s TTL)
- **Automatic expiration**: Dead agents removed after TTL expires
- **Bidirectional registration**: Agent-initiated (complete), orchestrator-initiated (completed 2026-02-06 via dashboard UI)
- **FastAPI endpoints**: `/register`, `/heartbeat`, `/agents`, `/health`
- **Registry repository**: AgentRecord ORM with SQLAlchemy
- **Background cleanup**: Automatic stale agent removal every 60s

#### Minimal Agent Containers
- **Container size**: ~50-100MB (no UI dependencies)
- **MLFlow decoupling**: UI runs as separate sidecar
- **python:3.10-slim base**: Minimal footprint
- **Multi-stage builds**: Optimized layer structure
- **Health checks**: `/health` endpoint for liveness probes

#### Multi-Provider Cost Tracking
- **MultiProviderCostTracker**: Aggregates costs by provider/model
- **Provider detection**: Automatic detection from model names
- **Zero-cost Ollama**: Local models tracked as $0.00
- **MLFlow metrics**: `provider_{name}_cost_usd` for UI filtering
- **Cost reporting CLI**: Query and export costs with filters

#### Performance Profiling
- **Bottleneck detection**: Nodes >50% execution time flagged
- **Per-node timing**: `time.perf_counter()` decorator with try/finally
- **MLFlow metrics**: `node_{node_id}_duration_ms` and `node_{node_id}_cost_usd`
- **Bottleneck info**: JSON field in WorkflowRunRecord for historical analysis
- **Thread-local storage**: Parallel execution safety

#### CLI Integration
- **`cost-report`**: Query costs by date range, workflow, experiment
- **`profile-report`**: Performance analysis with bottleneck highlighting
- **`observability`**: Unified observability command group
- **Rich output**: Formatted tables with bold highlights
- **Export formats**: Table, JSON, CSV

---

### Phase 3: Interfaces & Triggers (6 plans)

#### Gradio Chat UI for Config Generation
- **Conversational interface**: Generate configs through natural language
- **Session persistence**: Conversation history stored in SQLite
- **Session IDs**: Derived from client IP:port for continuity
- **Streaming responses**: Async generator pattern for non-blocking LLM calls
- **Gradio 6.x**: Latest version with theme/css parameters in launch()
- **Config validation**: Invalid configs caught before saving

#### FastAPI + HTMX Orchestration Dashboard
- **Server-Side Rendering**: Jinja2 templates with HTMX for dynamic updates
- **Partial template swaps**: `hx-swap="outerHTML"` for efficient updates
- **SSE streaming**: Async generators for real-time data pushing
- **Repository injection**: `app.state` for route dependency access
- **No JavaScript**: Python-only stack (14KB HTMX vs 200KB+ React)
- **Production pattern**: Used by Netflix, Uber, Microsoft

#### Agent Discovery Interface
- **View registered agents**: List all active agents
- **Health status**: Real-time health monitoring
- **Capabilities display**: Agent capabilities and metadata
- **Dynamic updates**: SSE streaming for live updates

#### MLFlow UI Integration
- **iframe embed**: MLFlow UI within dashboard
- **Single sign-on**: Shared authentication context
- **Context switching**: Workflow execution ↔ MLFlow analysis

#### Generic Webhook Infrastructure
- **HMAC signature verification**: Timing-attack safe comparison
- **Idempotency tracking**: `INSERT OR IGNORE` for webhook_id
- **Async execution**: `asyncio.run_in_executor()` for non-blocking
- **Optional validation**: Only when WEBHOOK_SECRET configured
- **Generic endpoint**: Accepts workflow_name and inputs

#### Platform Webhook Integrations
- **WhatsApp Business API**: Message chunking (4096 char limit)
- **Telegram Bot API**: aiogram 3.x with modern async/await
- **Factory functions**: Testability without singletons
- **Lazy initialization**: Handlers only load when env vars configured
- **CLI webhooks command**: Follows existing dashboard pattern
- **Challenge response**: GET /webhooks/whatsapp for Meta verification

#### Workflow Restart
- **Temp file pattern**: Config snapshot for async compatibility
- **BackgroundTasks**: Non-blocking restart with finally cleanup
- **JSONResponse**: Consistent error handling

---

### Phase 4: Advanced Capabilities (3 plans)

#### Code Execution Sandboxes
- **RestrictedPython**: Fast (<10ms) safe code execution
- **Docker extensible**: Full isolation for untrusted code
- **Resource presets**: low/medium/high/max CPU, memory, timeout limits
- **Security whitelisting**: ALLOWED_PATHS for files, ALLOWED_COMMANDS for shell
- **SQL restrictions**: SELECT only (rejects DROP, DELETE, UPDATE, INSERT, ALTER, CREATE)
- **Error continuation**: `on_error: 'continue'` catches and returns errors
- **Custom _print_**: Safe print class (not instance) for RestrictedPython
- **Safe getattr**: `_call_print` allowed, private attributes blocked
- **Actual values**: Real state values for sandbox inputs (not stringified templates)

#### Persistent Memory Backend
- **Namespaced storage**: `{agent_id}:{workflow_id or "*"}:{node_id or "*"}:{key}`
- **Dict-like read**: `agent.memory['key']` for convenience
- **Explicit write**: `agent.memory.write('key', value)` for clarity
- **Pluggable backends**: SQLite (default), PostgreSQL, Redis
- **Per-agent context**: Long-term memory survives container restarts

#### Pre-Built Tool Registry (15 Tools)
- **Web tools (3)**: Serper search, Tavily search, Brave search
- **File tools (4)**: Read, write, list, delete
- **Data tools (4)**: CSV read/write, JSON read/write
- **System tools (3)**: Shell, Python exec, datetime
- **Tool factory pattern**: Lazy loading and validation
- **LangChain BaseTool**: Integration with existing ecosystem

#### MLFlow Optimization
- **A/B testing**: Prompt variant comparison
- **Quality gates**: WARN (logs), FAIL (raises), BLOCK_DEPLOY (sets flag)
- **Percentile calculation**: Nearest-rank method (p50, p95, p99)
- **Automatic backup**: YAML backup before applying optimized prompts
- **CLI optimization group**: `evaluate`, `apply-optimized`, `ab-test`
- **MLFlow experiment aggregation**: Metrics across runs

---

### Technical Details

- **Total lines of code**: ~30,888 Python
- **Test coverage**: 1,018+ tests (98%+ pass rate)
- **Development time**: 20 days (2026-01-15 → 2026-02-04)
- **Average plan duration**: 20 minutes (6.0 hours total)
- **Phase breakdown**:
  - Phase 1: 4 plans, 65 minutes (16 min/plan)
  - Phase 2: 6 plans, 106 minutes (18 min/plan)
  - Phase 3: 6 plans, 106 minutes (18 min/plan)
  - Phase 4: 3 plans, 151 minutes (50 min/plan)

---

### Dependencies Updated

**New major dependencies:**
- `litellm` (latest) - Multi-LLM abstraction
- `ollama` (latest) - Local model runtime
- `gradio>=6.5.1` - Chat UI framework
- `fastapi>=0.100.0` - API servers
- `htmx>=1.9.0` - Dashboard interactivity
- `aiogram>=3.0.0` - Telegram bot framework
- `RestrictedPython` - Code sandboxing

**Updated:**
- `mlflow>=3.9.0` - Enhanced observability (from 2.9)
- `sqlalchemy>=2.0.0` - Storage backend (from 1.x)

---

### Architecture Decision Records (ADRs)

**New ADRs created during v1.0:**
- ADR-019: LiteLLM Multi-Provider Integration
- ADR-020: Agent Registry Architecture
- ADR-021: HTMX Dashboard Framework
- ADR-022: RestrictedPython Sandbox
- ADR-023: Memory Backend Design
- ADR-024: Webhook Integration Pattern
- ADR-025: Optimization Architecture

**Previous ADRs (v0.1):** ADR-001 through ADR-018 (18 records)

---

### Known Limitations (Deferred to v1.1+)

- **ARCH-02**: Orchestrator-initiated agent registration (agent-initiated complete)
- **Self-optimizing agents**: Runtime auto-spawn and optimization
- **Full LangChain tool registry**: Currently 15 tools, full registry (500+) deferred
- **Visual workflow builder**: Config-first philosophy maintained
- **Kubernetes deployment**: Enterprise-scale patterns

---

### Documentation

**Updated:**
- README.md - Complete v1.0 feature overview
- All ADRs - 25 total architectural decisions
- Implementation logs - 19 plan completions documented

**New:**
- `.planning/milestones/v1.0-ROADMAP.md` - 4-phase roadmap
- `.planning/milestones/v1.0-REQUIREMENTS.md` - 27 requirements
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` - Comprehensive audit

---

### Breaking Changes from v0.1

**Configuration:**
- `config.llm.provider` now accepts `openai`, `anthropic`, `google`, `ollama` (was only `google`)
- `edges[].routes[]` added for conditional routing
- `edges[].parallel` added for parallel execution
- `config.memory` added for persistent memory
- `config.webhooks` added for external triggers

**CLI:**
- New commands: `chat`, `dashboard`, `agents`, `webhooks`, `report`
- Observability commands: `cost-report`, `profile-report`

**Python API:**
- Storage backends now require factory pattern: `create_storage_backend()`
- LLM provider returns tuple `(result, usage_metadata)`

**Migration:** See `.planning/milestones/v1.0-ROADMAP.md` for detailed migration guide

---

## [0.1.0-dev] - Archived (See .planning/milestones/v0.1-archive)

### Overview
Initial working alpha with linear workflows, Google Gemini integration, MLFlow 2.9 observability, and Docker deployment.

**Key Features (v0.1):**
- Linear workflow execution (no control flow)
- Single LLM provider (Google Gemini)
- 645 tests passing
- MLFlow 2.9 manual tracking
- Basic Docker deployment

**Archived:** 2026-02-04 (superseded by v1.0)

---

## Version Planning

### [1.1.0] - TBD (Planning)

**Focus:** Next milestone goals TBD

**Potential areas:**
- Complete orchestrator-initiated agent registration (ARCH-02)
- Kubernetes deployment patterns
- Enhanced collaborative features
- Self-optimizing agents
- Full LangChain tool registry

---

## Notes

### About This Changelog

This changelog follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format:
- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

### Implementation Details

For comprehensive v1.0 implementation details, see:
- **[.planning/phases/](.planning/phases/)** - Phase-by-phase summaries
- **[.planning/milestones/v1.0-ROADMAP.md](.planning/milestones/v1.0-ROADMAP.md)** - Complete roadmap
- **[.planning/milestones/v1.0-MILESTONE-AUDIT.md](.planning/milestones/v1.0-MILESTONE-AUDIT.md)** - Delivery verification

For legacy v0.1 details:
- **[docs/implementation_logs/](docs/implementation_logs/)** - Task-by-task records (v0.1)

### Versioning

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for added functionality (backwards-compatible)
- **PATCH** version for backwards-compatible bug fixes

Current version: **1.0.0** (production release)

---

*For the latest updates, see [.planning/STATE.md](.planning/STATE.md)*
*For development progress, see [.planning/ROADMAP.md](.planning/ROADMAP.md)*
