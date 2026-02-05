# Architecture Research: v1.1 Core UX Polish

**Domain:** FastAPI/HTMX/Gradio Agent Orchestration Platform
**Researched:** 2026-02-04
**Overall Confidence:** MEDIUM-HIGH
**Research Mode:** Ecosystem + Integration

---

## Executive Summary

The v1.1 Core UX Polish milestone requires integrating UX improvements into an existing FastAPI/HTMX/Gradio stack. Key architectural challenges include:

1. **Single-command startup** - Need process manager to orchestrate Dashboard (FastAPI) + Chat UI (Gradio) + MLFlow servers
2. **Auto-initialization** - Database setup, graceful degradation patterns
3. **Unified workspace** - Either consolidate UIs or improve handoff between Dashboard and Chat UI
4. **Navigation redesign** - Reorganize routes for better discoverability
5. **Status visibility** - Real-time updates via SSE (already integrated but needs expansion)

The current architecture is well-positioned for these improvements. FastAPI's lifespan events, existing SSE infrastructure with HTMX, and SQLAlchemy 2.0's create_all() provide clear paths forward.

---

## Current Architecture Analysis

### Existing Stack

| Component | Technology | Location | Purpose |
|-----------|-----------|----------|---------|
| Dashboard | FastAPI + HTMX + Jinja2 | `ui/dashboard/app.py` | Main orchestration UI |
| Chat UI | Gradio | `ui/gradio_chat.py` | Config generation interface |
| Storage | SQLAlchemy 2.0 + SQLite | `storage/sqlite.py` | 8 repositories |
| Observability | MLFlow 3.9+ | `observability/` | Cost tracking, traces |
| Deployment | Docker | `deploy/` | Multi-container setup |

### Current UI Split

```
┌─────────────────────────────────────────────────────────────┐
│                    Current v1.0 Architecture                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Port 7861 (FastAPI)         Port 7860 (Gradio)             │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  Dashboard       │      │  Chat UI         │            │
│  │  (HTMX + Jinja2) │      │  (Gradio Blocks) │            │
│  │                  │      │                  │            │
│  │  - Workflows     │      │  - Config        │            │
│  │  - Agents        │◄─────┤  - Generator     │            │
│  │  - Metrics       │  link│  - Chat          │            │
│  │  - MLFlow iframe │      │                  │            │
│  └──────────────────┘      └──────────────────┘            │
│         │                                                  │
│         ▼                                                  │
│  ┌──────────────────┐                                    │
│  │  SQLite DB       │                                    │
│  │  (8 repos)       │                                    │
│  └──────────────────┘                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Observations:**
- Dashboard runs on port 7861 (configurable via `--port`)
- Gradio Chat UI runs on port 7860 (configurable via `--port`)
- Both use same SQLite database (via repository pattern)
- Navigation handoff is via static link in Chat UI
- MLFlow is iframe-embedded at `/mlflow` in Dashboard

---

## 1. Single-Command Startup Architecture

### Problem Statement

Currently, users must start services separately:
```bash
# Terminal 1
configurable-agents dashboard --port 7861

# Terminal 2
configurable-agents chat --port 7860
```

For MLFlow, a third service may be needed. This is a poor developer experience.

### Options

| Option | Description | Pros | Cons | Confidence |
|--------|-------------|------|------|------------|
| **Custom Process Manager** | Python multiprocessing module to spawn processes | No new dependencies, full control | More code to maintain, signal handling complexity | HIGH |
| **Honcho/Procfile** | Python port of Foreman, uses Procfile format | Declarative config, battle-tested | Additional dependency, Windows support issues | MEDIUM |
| **Supervisord** | Process control system | Production-grade, auto-restart | Heavy for dev use, complex config | MEDIUM |
| **Docker Compose** | Multi-container orchestration | Already used for deployment, isolates dependencies | Requires Docker, heavier than native | HIGH |
| **FastAPI Lifespan Mount** | Mount Gradio as sub-app in FastAPI | Single process, shared context | Gradio's event loop may conflict | LOW |

### Recommendation: Dual-Track Approach

**Development:** Custom Process Manager
- Use Python's `multiprocessing` module
- Spawn Gradio and MLFlow as child processes
- Clean shutdown on SIGINT/SIGTERM
- Status output to console with colored prefixes

**Production:** Docker Compose (already implemented)
- Current `deploy/docker-compose.yml` works
- Single container with internal process management
- Or separate containers with orchestration

### Proposed Implementation

```python
# cli.py - new command
def cmd_start(args: argparse.Namespace) -> int:
    """Start all services with single command."""
    from configurable_agents.process.manager import ProcessManager

    manager = ProcessManager()

    # Dashboard (FastAPI)
    manager.add_service(
        name="dashboard",
        target=run_dashboard,
        kwargs={"host": args.host, "port": args.dashboard_port}
    )

    # Chat UI (Gradio)
    manager.add_service(
        name="chat",
        target=run_gradio_chat,
        kwargs={"host": args.host, "port": args.chat_port}
    )

    # MLFlow (optional)
    if args.mlflow:
        manager.add_service(
            name="mlflow",
            target=run_mlflow,
            kwargs={"port": args.mlflow_port}
        )

    # Start all and wait
    manager.start_all()
    manager.wait()  # Blocks until interrupted

    return 0
```

**Integration Points:**
- New `process/manager.py` module
- CLI command: `configurable-agents start`
- Reuses existing `cmd_dashboard()` and `cmd_chat()` entry points
- Graceful shutdown handler

---

## 2. Auto-Initialization Architecture

### Problem Statement

Fresh installations require manual database setup. Users may encounter errors on first run if tables don't exist.

### Current State

Looking at `storage/sqlite.py`:
- Repositories use SQLAlchemy 2.0 with context managers
- No auto-create on initialization
- Models defined in `storage/models.py`

### Options

| Option | Description | Pros | Cons | Confidence |
|--------|-------------|------|------|------------|
| **Alembic Migrations** | Industry-standard migration tool | Production-grade, rollback support | Complex for single-user SQLite | MEDIUM |
| **SQLAlchemy create_all()** | Simple metadata.create_all() | Zero config, works immediately | No version tracking, can't downgrade | HIGH |
| **Factory with Init Flag** | Check/create tables in factory function | Explicit, fail-fast on errors | Manual version management | HIGH |
| **FastAPI Lifespan Hook** | Initialize on app startup | Automatic for web users | Doesn't help CLI usage | MEDIUM |

### Recommendation: Hybrid Approach

**For Development:**
```python
# storage/factory.py - enhanced
def create_storage_backend(config: StorageConfig, auto_init: bool = True):
    """Create storage backend with optional auto-initialization."""
    engine = create_engine(config.url)

    if auto_init:
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if not existing_tables:
            # Create all tables
            models.Base.metadata.create_all(engine)
            logger.info(f"Initialized database: {config.url}")
        else:
            logger.debug(f"Using existing database: {config.url}")

    # Create repositories...
```

**For Production:**
- Use Alembic for versioned migrations
- Migration check in FastAPI lifespan events
- Graceful degradation if migration fails (log warning, continue)

### Graceful Degradation Pattern

```python
# ui/dashboard/app.py - lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup/shutdown with graceful degradation."""
    # Startup
    try:
        # Check migrations
        await check_and_migrate(app.state.db_engine)
        app.state.db_ready = True
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        app.state.db_ready = False
        # Don't fail startup - serve in degraded mode

    yield

    # Shutdown
    await cleanup_resources()

# Create app with lifespan
app = FastAPI(lifespan=lifespan)
```

**Degraded Mode UI:**
- Show banner: "Database unavailable - running in read-only mode"
- Hide write operations (start workflow, register agents)
- Keep read operations visible (static docs, status)

---

## 3. Unified Workspace Architecture

### Problem Statement

Users must navigate between two UIs on different ports. The context switch is jarring.

### Current Integration Points

From `ui/gradio_chat.py:522`:
```python
gr.Markdown(
    f"**[Open Dashboard]({self.dashboard_url})** - Monitor workflows and agents"
)
```

From `ui/dashboard/templates/base.html:31`:
```html
<li><a href="/mlflow">MLFlow</a></li>
```

### Options

| Option | Description | Pros | Cons | Confidence |
|--------|-------------|------|------|------------|
| **Full Integration** | Port Chat UI to HTMX/Jinja2 | Consistent UX, single codebase | Loss of Gradio features (chat streaming, file upload) | MEDIUM |
| **Gradio Mount** | Mount Gradio app at `/chat` | Preserves Gradio features, single URL | Event loop conflicts, styling mismatch | LOW |
| **Tabbed Interface** | Add Chat tab as iframe | Minimal change, clear separation | Iframe limitations, cross-frame issues | HIGH |
|**Keep Separate + Better Nav** | Improve handoff with shared auth | Respects domain boundaries | Requires session sharing mechanism | HIGH |
| **Reverse Proxy** | Single domain with path routing | Production-ready, clean URLs | Requires nginx/caddy config | MEDIUM |

### Recommendation: Phased Approach

**Phase 1 (v1.1):** Tabbed Interface with iframe
- Add "Chat" tab to Dashboard navigation
- Embed Gradio UI at `http://localhost:7860` in iframe
- Handle CORS and size negotiation
- Clear visual indication of context

**Phase 2 (v1.2):** Shared Session + Better Handoff
- Shared authentication/session state
- Deep linking to Chat UI with pre-filled context
- Return-to-Dashboard after config generation
- Consistent styling between UIs

**Future Consideration:** Full HTMX Port
- Evaluate after HTMX gains streaming support
- Chat interface is UI-heavy, HTMX may not be ideal fit
- Keep as separate consideration after v1.2

### Proposed Phase 1 Implementation

```python
# ui/dashboard/routes/chat.py
@router.get("/chat")
async def chat_page(request: Request):
    """Render Gradio Chat UI in iframe."""
    chat_url = os.getenv("GRADIO_URL", "http://localhost:7860")

    return templates.TemplateResponse(
        "chat_embed.html",
        {
            "request": request,
            "chat_url": chat_url,
            "nav_chat": 'class="active"'  # Highlight nav
        }
    )
```

```html
<!-- templates/chat_embed.html -->
{% extends "base.html" %}

{% block content %}
<div class="chat-container">
    <iframe src="{{ chat_url }}"
            class="chat-iframe"
            allow="clipboard-write; microphone">
    </iframe>
</div>
{% endblock %}
```

---

## 4. Navigation Redesign Architecture

### Current Structure

From `templates/base.html:26-32`:
```html
<ul class="nav-links">
    <li><a href="/">Dashboard</a></li>
    <li><a href="/workflows">Workflows</a></li>
    <li><a href="/agents">Agents</a></li>
    <li><a href="/orchestrator">Orchestrator</a></li>
    <li><a href="/mlflow">MLFlow</a></li>
    <li><a href="/optimization/experiments">Optimization</a></li>
</ul>
```

### Issues

1. Flat structure - no grouping of related features
2. No visual hierarchy
3. "Orchestrator" and "Agents" are related but separate
4. "Optimization" buried in sub-path

### Proposed Navigation Structure

```html
<!-- Redesigned navigation with grouping -->
<nav class="navbar">
    <div class="nav-container">
        <div class="nav-brand">
            <a href="/">Configurable Agents</a>
        </div>

        <ul class="nav-section">
            <li class="nav-section-title">Monitor</li>
            <li><a href="/">Dashboard</a></li>
            <li><a href="/workflows">Workflows</a></li>
            <li><a href="/agents">Agents</a></li>
        </ul>

        <ul class="nav-section">
            <li class="nav-section-title">Create</li>
            <li><a href="/chat">Config Builder</a></li>
            <li><a href="/workflows/new">New Workflow</a></li>
        </ul>

        <ul class="nav-section">
            <li class="nav-section-title">Analyze</li>
            <li><a href="/metrics">Metrics</a></li>
            <li><a href="/optimization">Optimization</a></li>
            <li><a href="/mlflow">MLFlow</a></li>
        </ul>

        <ul class="nav-section">
            <li class="nav-section-title">System</li>
            <li><a href="/orchestrator">Orchestrator</a></li>
            <li><a href="/settings">Settings</a></li>
        </ul>
    </div>
</nav>
```

### Route Organization

```
/                           → Dashboard home
/workflows                   → Workflow list
/workflows/{id}             → Workflow detail
/workflows/new              → Create workflow (form)
/chat                       → Config builder (Gradio iframe)
/agents                     → Agent registry
/metrics                    → Cost/performance metrics
/optimization               → A/B testing, experiments
/mlflow                     → MLFlow UI (iframe)
/orchestrator               → Orchestrator management
/settings                   → System configuration
```

---

## 5. Status Visibility Architecture

### Current State

From `templates/base.html:43-53`:
```javascript
document.body.addEventListener('htmx:sseError', function(evt) {
    console.log('SSE connection error, will attempt reconnect...');
});
```

SSE infrastructure is already in place but not actively used for status updates.

### Requirements

1. Real-time workflow status updates
2. Agent health indicators
3. System resource usage
4. Background job progress

### Implementation Pattern

**FastAPI SSE Endpoint:**
```python
# ui/dashboard/routes/status.py
from fastapi.responses import StreamingResponse

@router.get("/status/stream")
async def status_stream():
    """Server-Sent Events for real-time status updates."""
    async def event_generator():
        while True:
            # Gather status from all components
            status = {
                "workflows": await get_workflow_status(),
                "agents": await get_agent_status(),
                "system": get_system_status()
            }

            yield f"event: status\ndata: {json.dumps(status)}\n\n"
            await asyncio.sleep(2)  # 2s refresh

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**HTMX Consumption:**
```html
<!-- templates/dashboard.html -->
<div hx-ext="sse" sse-connect="/status/stream" sse-swap="status">
    <div id="workflow-status" hx-sse="status">
        <!-- Auto-updated content -->
    </div>
    <div id="agent-health" hx-sse="status">
        <!-- Auto-updated content -->
    </div>
</div>
```

### Status Components

| Component | Update Frequency | Data Source |
|-----------|------------------|-------------|
| Workflow Status | 2s | `workflow_runs` table |
| Agent Heartbeat | 5s | `agent_registry` table |
| System Resources | 5s | `psutil` (optional) |
| Queue Depth | 1s | In-memory state |

---

## Integration Points with Existing Code

### New Components Required

| Component | File | Purpose |
|-----------|------|---------|
| ProcessManager | `process/manager.py` | Multi-process orchestration |
| InitCheck | `storage/init.py` | Auto-initialization utilities |
| ChatRoute | `ui/dashboard/routes/chat.py` | Chat UI integration |
| StatusStream | `ui/dashboard/routes/status.py` | SSE status updates |
| Migrations | `alembic/versions/` | Database versioning (future) |

### Modified Components

| Component | Changes | Impact |
|-----------|---------|--------|
| `cli.py` | Add `cmd_start()` | New entry point |
| `ui/dashboard/app.py` | Add lifespan handler | Auto-init on startup |
| `templates/base.html` | Redesign nav structure | Better UX |
| `storage/factory.py` | Add auto-init flag | Graceful DB setup |

---

## Build Order Recommendation

### Phase 1: Foundation (Start Here)
1. **Auto-initialization** - Prerequisite for everything
   - Add `create_all()` to storage factory
   - Implement degraded mode detection
   - Update tests

2. **Single-command startup** - Core UX improvement
   - Implement ProcessManager class
   - Add `start` CLI command
   - Handle signals and cleanup

### Phase 2: Integration
3. **Navigation redesign** - Better organization
   - Restructure base.html navigation
   - Add section grouping
   - Update route handlers

4. **Status visibility** - Real-time updates
   - Implement SSE status endpoint
   - Add HTMX SSE consumers
   - Create status widgets

### Phase 3: Polish
5. **Unified workspace** - Chat integration
   - Add Chat tab/iframe
   - Configure CORS
   - Test handoff flows

---

## Architectural Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Process manager complexity** | Medium | Start simple (multiprocessing), add features incrementally |
| **Gradio event loop conflicts** | High | Keep separate process, use iframe for integration |
| **Database migration conflicts** | Medium | Auto-create for dev, Alembic for production (phase 2) |
| **SSE reconnection storms** | Low | Implement exponential backoff, already in HTMX extension |
| **iframe CORS issues** | Medium | Configure FastAPI CORS middleware carefully |

---

## Open Questions for Phase-Specific Research

1. **Gradio 5.x streaming behavior** - Does Gradio 5.x support custom event loops for FastAPI mounting?
2. **Windows process management** - Does multiprocessing work reliably on Windows for this use case?
3. **MLFlow embedded mode** - Can MLFlow run purely embedded or must it be separate process?
4. **Session sharing** - Best approach for sharing auth between Dashboard and Gradio?

---

## Sources

### Process Management
- [FastAPI Deployment Guide for 2026](https://www.zestminds.com/blog/fastapi-deployment-guide/) - Production deployment patterns
- [How to Deploy FastAPI with Nginx and Supervisor](https://www.travisluong.com/how-to-deploy-fastapi-with-nginx-and-supervisor/) - Supervisord integration
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/testing-events/) - Official lifespan documentation
- [Docker, procfiles, and health checks](https://blog.thea.codes/docker-procfiles/) - Honcho/Procfile discussion

### Database Initialization
- [Stack Overflow: Auto-initialize SQLAlchemy with Alembic](https://stackoverflow.com/questions/56161826/how-can-i-initialize-the-database-automatically-with-sqlalchemy-and-alembic) - Alembic initialization patterns
- [Alembic Autogenerate Documentation](https://alembic.sqlalchemy.org/en/latest/autogenerate.html) - Official Alembic docs

### Real-time Updates (SSE)
- [Building Real-Time Dashboards with FastAPI and HTMX](https://medium.com/codex/building-real-time-dashboards-with-fastapi-and-htmx-01ea458673cb) - HTMX SSE patterns
- [Implementing SSE with FastAPI](https://mahdijafaridev.medium.com/implementing-server-sent-events-sse-with-fastapi-real-time-updates-made-simple-6492f8bfc154) - FastAPI SSE implementation
- [FastAPI HTMX SSE Streaming (YouTube)](https://www.youtube.com/watch?v=D5l_A_kqUhI) - Video tutorial

### Gradio Integration
- [Mount Gradio App Documentation](https://www.gradio.app/docs/gradio/mount_gradio_app) - Official mounting guide
- [FastAPI App with Gradio Client](https://www.gradio.app/guides/fastapi-app-with-the-gradio-client) - Client integration
- [Gradio Embed GitHub Issue](https://github.com/gradio-app/gradio/issues/1608) - Embedding discussion

---

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| Process Management | HIGH | Python multiprocessing well-understood; existing codebase structure clear |
| Auto-initialization | HIGH | SQLAlchemy create_all() is standard; degraded mode is straightforward |
| UI Consolidation | MEDIUM | Gradio/FastAPI integration has tradeoffs; iframe approach safe but limited |
| Navigation Redesign | HIGH | Straightforward HTML/template reorganization |
| Real-time Status | HIGH | SSE already in codebase; HTMX extension handles complexity |
| Overall Integration | MEDIUM-HIGH | Existing architecture is sound; most changes additive |

---

## Summary Recommendation

For v1.1 Core UX Polish, the architecture should:

1. **Use custom ProcessManager** for single-command startup (development) with Docker Compose for production
2. **Implement auto-initialization** via SQLAlchemy create_all() with graceful degradation
3. **Add Chat tab as iframe** in Phase 1, defer full integration until Gradio 5.x event loop behavior is verified
4. **Restructure navigation** into logical sections (Monitor, Create, Analyze, System)
5. **Expand SSE usage** for real-time status updates across dashboard widgets

The existing FastAPI/HTMX/Gradio architecture is well-suited for these improvements. Most changes are additive rather than architectural rewrites, which reduces risk.
