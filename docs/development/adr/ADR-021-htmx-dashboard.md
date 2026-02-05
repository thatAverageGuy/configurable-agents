# ADR-021: HTMX Dashboard Framework

**Status**: Accepted
**Date**: 2026-02-04
**Deciders**: thatAverageGuy, Claude Code

---

## Context

The system needs a web-based orchestration dashboard for:
- Managing running workflows (start, stop, restart)
- Discovering and viewing registered agents
- Monitoring workflow execution with real-time updates
- Accessing MLFlow UI (iframe integration)
- Viewing metrics, logs, and traces

### Requirements

- **UI-03**: User can manage running workflows through orchestration dashboard
- **UI-04**: User can discover and register agents through orchestration interface
- **UI-05**: MLFlow UI is accessible within the orchestration dashboard
- **UI-06**: User can monitor agent status, logs, and metrics in real-time

### Constraints

- Must be lightweight (no heavy JS frameworks like React/Vue)
- Must support real-time updates without page refreshes
- Must integrate with existing FastAPI infrastructure
- Must work in local development environment

---

## Decision

**Use FastAPI + HTMX + Server-Sent Events (SSE) for dashboard. No JavaScript frameworks.**

---

## Rationale

### Why HTMX?

1. **No JavaScript Required**: All dynamic behavior via HTML attributes
2. **Progressive Enhancement**: Works without JS, enhances with HTMX
3. **Small**: ~14KB minified vs 200KB+ for React
4. **Fast Development**: Write HTML, not component code
5. **Backend-Driven**: All logic in Python (FastAPI), not frontend

### Why Server-Sent Events (SSE)?

1. **Real-Time Updates**: One-way streaming from server to client
2. **Simpler than WebSockets**: No bidirectional protocol overhead
3. **Browser Native**: Built-in `EventSource` API
4. **Auto-Reconnect**: Browser handles connection drops
5. **Low Latency**: Server pushes updates immediately

### Why Not React/Vue?

1. **Overkill**: Dashboard is mostly CRUD, no complex state management
2. **Build Complexity**: Need bundlers, dev servers, hot reload
3. **Learning Curve**: Team knows Python/HTML, not React
4. **Deployment**: Static asset serving, build pipelines
5. **Maintenance**: Two codebases (Python backend + JS frontend)

### Why FastAPI?

1. **Async**: Native async/await for concurrent requests
2. **Type Safety**: Pydantic models for request/response
3. **Templating**: Built-in Jinja2 support (or use custom templates)
4. **SSE Support**: Easy to stream responses with `StreamingResponse`

---

## Implementation

### Architecture

```
FastAPI Backend (Python)
    ↓
Jinja2 Templates (HTML + HTMX attributes)
    ↓
Browser (HTMX + SSE)
    ↓
Dynamic Updates Without Page Refresh
```

### HTMX Pattern Examples

**Button Triggers Backend Update**:
```html
<button hx-post="/api/workflows/start/{workflow_id}"
        hx-target="#workflow-status"
        hx-swap="outerHTML">
    Start Workflow
</button>

<div id="workflow-status">
    Status: Stopped
</div>
```

**Click → POST Request → Replace Target HTML**

**Real-Time Updates via SSE**:
```html
<div hx-ext="sse"
     hx-sse="/api/workflows/stream/{workflow_id}"
     hx-swap="innerHTML">
    Loading...
</div>
```

**Auto-Connect → Stream Updates → Replace HTML**

### Server-Sent Events (SSE)

```python
from fastapi.responses import StreamingResponse

@app.get("/api/workflows/stream/{workflow_id}")
async def stream_workflow_updates(workflow_id: str):
    """Stream workflow execution updates"""

    async def event_stream():
        while True:
            # Get workflow status from storage
            status = get_workflow_status(workflow_id)

            # Send SSE event
            yield f"event: status\ndata: {status.json()}\n\n"

            if status.is_complete:
                break

            await asyncio.sleep(1)  # Poll every second

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )
```

### HTMX SSE Integration

```html
<div hx-ext="sse" sse-connect="/api/workflows/stream/{workflow_id}">
    <div sse-swap="message">
        <!-- Auto-updated with server messages -->
    </div>
</div>
```

### Repository Injection

```python
@app.get("/dashboard")
async def dashboard(request: Request):
    """Render main dashboard"""
    # Inject repositories via app.state
    workflow_repo = request.app.state.workflow_repo
    agent_repo = request.app.state.agent_repo

    workflows = workflow_repo.list_active()
    agents = agent_repo.list_active()

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "workflows": workflows, "agents": agents}
    )
```

### Partial Template Swaps

**Backend Returns HTML Fragment**:
```python
@app.get("/api/workflows/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Return HTML fragment for workflow"""
    status = workflow_repo.get_workflow(workflow_id)

    return templates.TemplateResponse(
        "partials/workflow_status.html",
        {"request": request, "status": status}
    )
```

**HTMX Swaps Specific Element**:
```html
<div id="workflow-detail"
     hx-get="/api/workflows/{workflow_id}"
     hx-trigger="load, every 1s"
     hx-swap="outerHTML">
    <!-- Auto-refreshed every second -->
</div>
```

---

## Configuration

### Dashboard Server

```yaml
config:
  dashboard:
    host: "0.0.0.0"
    port: 8000
    reload: true  # Development mode
```

### MLFlow Integration

```html
<iframe src="http://localhost:5000"
        width="100%"
        height="800px"
        frameborder="0">
</iframe>
```

---

## Features

### Workflow Management

- **Start**: POST /api/workflows/start/{workflow_id}
- **Stop**: POST /api/workflows/stop/{workflow_id}
- **Restart**: POST /api/workflows/restart/{workflow_id}
- **Status**: GET /api/workflows/{workflow_id}

### Agent Discovery

- **List Agents**: GET /api/agents
- **Agent Details**: GET /api/agents/{agent_id}
- **Agent Health**: Heartbeat status in real-time

### Real-Time Monitoring

- **Workflow Logs**: SSE stream of workflow execution logs
- **Metrics Dashboard**: Cost, duration, token usage
- **Performance**: Bottleneck detection display

---

## Alternatives Considered

### Alternative 1: React + FastAPI

**Pros**:
- Rich component ecosystem
- Developer-friendly (if team knows React)
- Complex state management (Redux, etc.)

**Cons**:
- Build complexity (bundlers, dev servers)
- Two codebases (Python + JavaScript)
- Heavy page load (200KB+ JS bundle)
- Overkill for mostly CRUD dashboard

**Why rejected**: Violates "boring technology" principle. Adds unnecessary complexity.

### Alternative 2: Streamlit

**Pros**:
- Python-only (no HTML/CSS/JS)
- Fast development
- Built-in components

**Cons**:
- Limited customization (hard to brand)
- Heavy dependency (entire UI framework)
- Not suitable for granular control
- Used for chat UI (separate concern)

**Why rejected**: Already using Streamlit for chat UI. Need more control for dashboard.

### Alternative 3: Pure JavaScript (Vanilla)

**Pros**:
- No framework overhead
- Full control

**Cons**:
- Manual DOM manipulation
- No component system
- More code than HTMX
- Harder to maintain

**Why rejected**: HTMX provides better abstraction with less code.

---

## Consequences

### Positive Consequences

1. **Fast Development**: Write HTML, not React components
2. **Small Bundle**: ~14KB HTMX vs 200KB+ React
3. **Python-Only**: Team doesn't need to learn React
4. **Real-Time**: SSE enables live updates without WebSockets complexity
5. **Testable**: Easy to test backend logic without JS tests

### Negative Consequences

1. **Learning Curve**: Team must learn HTMX attributes
2. **Less Structured**: No component system, just HTML fragments
3. **Limited Ecosystem**: Fewer third-party components than React
4. **SEO**: Not suitable for public-facing pages (fine for dashboard)

### Risks

#### Risk 1: HTMX Doesn't Scale

**Likelihood**: Low (HTMX proven in production)
**Impact**: Low
**Mitigation**: Can migrate to React later if needed. HTMX is just HTML attributes, easy to replace.

#### Risk 2: SSE Connection Limits

**Likelihood**: Low (single-user dashboard)
**Impact**: Low
**Mitigation**: Browser limits SSE connections per domain (typically 6). Dashboard uses 1-2 connections.

#### Risk 3: Real-Time Updates Lag

**Likelihood**: Medium
**Impact**: Low
**Mitigation**: Polling interval (1s) is reasonable for dashboard. Can optimize if needed.

---

## Related Decisions

- [ADR-020](ADR-020-agent-registry.md): Agent registry (dashboard displays agents)
- [ADR-024](ADR-024-webhook-integration.md): Webhook server (same FastAPI infrastructure)

---

## Implementation Status

**Status**: ✅ Complete (v1.0)

**Files**:
- `src/configurable_agents/dashboard/server.py` - FastAPI dashboard server
- `src/configurable_agents/dashboard/templates/` - Jinja2 templates with HTMX
- `src/configurable_agents/dashboard/routes/` - Dashboard routes

**Features**:
- Workflow management (start, stop, restart)
- Agent discovery and health monitoring
- MLFlow iframe integration
- Real-time log streaming (SSE)
- Cost and performance metrics display

**Testing**: 18 tests covering dashboard endpoints, SSE streaming, and HTMX responses

---

## Superseded By

None (current)
