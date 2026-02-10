# UI Architecture — Dashboard, Chat, and Unified Launcher

**Status**: REFERENCE — Read before testing or modifying any UI code
**Created**: 2026-02-09
**Related**: [ARCHITECTURE.md](ARCHITECTURE.md), [ADR-021: HTMX Dashboard](adr/ADR-021-htmx-dashboard.md)

---

## Overview

The UI system consists of three independently-runnable services and one unified launcher:

| Service | Tech Stack | Default Port | CLI Command | Purpose |
|---------|-----------|-------------|-------------|---------|
| **Dashboard** | FastAPI + HTMX + Jinja2 | 7861 | `dashboard` | Monitoring: workflows, agents, metrics, orchestrator |
| **Chat UI** | Gradio | 7860 | `chat` | Conversational config generation |
| **MLflow UI** | MLflow built-in | 5000 | _(managed by `ui`)_ | Experiment tracking and traces |
| **Unified Launcher** | ProcessManager | all above | `ui` | Spawns all services as child processes |

### System Context

```
                    +-----------------------+
                    |    User (Browser)     |
                    +-----------+-----------+
                                |
          +---------------------+---------------------+
          |                     |                     |
          v                     v                     v
  +-------+-------+   +--------+--------+   +--------+--------+
  |   Dashboard    |   |    Chat UI      |   |   MLflow UI     |
  |  :7861 (HTMX)  |   |  :7860 (Gradio) |   |  :5000 (Flask)  |
  +-------+-------+   +--------+--------+   +-----------------+
          |                     |
          v                     v
  +-------+-------+   +--------+--------+
  |  SQLite DB     |   |   LLM Provider  |
  | (shared state) |   | (config gen)    |
  +---------------+   +-----------------+
```

---

## 1. Dashboard (`cmd_dashboard`)

### Purpose

Web-based monitoring UI for the entire Configurable Agents system. Shows workflow runs, registered agents (deployed containers), metrics, and allows manual orchestration of remote agents.

### Architecture

```
DashboardApp (FastAPI)
├── Routes
│   ├── / ........................ Main dashboard (summary stats + status panel)
│   ├── /health ................. Health check endpoint
│   ├── /mlflow ................. Redirect to MLflow or show "unavailable" page
│   ├── /workflows/ ............. Workflow runs list (filterable by status)
│   │   ├── /workflows/table .... HTMX partial — workflows table refresh
│   │   ├── /workflows/{id} ..... Workflow detail (outputs, bottleneck, state history)
│   │   ├── /workflows/{id}/cancel ... Cancel running workflow
│   │   └── /workflows/{id}/restart .. Restart with same inputs (background)
│   ├── /agents/ ................ Registered agents (alive only)
│   │   ├── /agents/table ....... HTMX partial — agents table refresh
│   │   ├── /agents/all ......... Include dead agents
│   │   ├── /agents/{id}/docs ... Redirect to agent's /docs endpoint
│   │   ├── /agents/{id} DELETE . Deregister agent
│   │   └── /agents/refresh ..... Manual refresh trigger
│   ├── /metrics/
│   │   ├── /metrics/workflows/stream .. SSE: workflow updates every 5s
│   │   ├── /metrics/agents/stream ..... SSE: agent updates every 10s
│   │   └── /metrics/summary ........... JSON: summary stats
│   ├── /optimization/
│   │   ├── /optimization/experiments ... MLflow experiment list (HTML)
│   │   ├── /optimization/experiments.json .. Same as JSON
│   │   ├── /optimization/compare ........ Variant comparison (HTML)
│   │   ├── /optimization/compare.json ... Same as JSON
│   │   └── /optimization/apply POST ..... Apply optimized prompt to YAML
│   ├── /orchestrator
│   │   ├── /orchestrator ............... Management page (HTML)
│   │   ├── /orchestrator/register POST . Register agent with health check
│   │   ├── /orchestrator/health-check .. HTMX partial: health check all agents
│   │   ├── /orchestrator/{id}/schema ... Get workflow schema from agent
│   │   ├── /orchestrator/{id}/execute .. Execute workflow on remote agent
│   │   └── /orchestrator/{id} DELETE ... Deregister agent
│   └── /api/status
│       ├── /api/status .............. HTMX partial: status panel (10s poll)
│       └── /api/status/health ....... JSON health check
├── Templates (Jinja2 + HTMX)
│   ├── base.html .................. Base layout with nav + HTMX script
│   ├── dashboard.html ............. Main dashboard page
│   ├── workflows.html ............. Workflows list page
│   ├── workflows_table.html ....... HTMX partial for workflow table
│   ├── workflow_detail.html ....... Single workflow detail
│   ├── agents.html ................ Agents list page
│   ├── agents_table.html .......... HTMX partial for agents table
│   ├── experiments.html ........... MLflow experiments list
│   ├── optimization.html .......... Variant comparison page
│   ├── orchestrator.html .......... Orchestrator management page
│   ├── mlflow_unavailable.html .... Shown when MLflow not configured
│   ├── macros.html ................ Reusable Jinja2 macros
│   ├── errors/error.html .......... Error page
│   └── partials/status_panel.html . HTMX partial for status panel
├── Static Files
│   └── /static/ (auto-created)
├── Template Helpers (globals)
│   ├── format_duration(seconds) → "2m 30s"
│   ├── format_cost(usd) → "$0.0123"
│   ├── time_ago(datetime) → "2 hours ago"
│   └── parse_capabilities(metadata_json) → ["cap1", "cap2"]
└── MLflow Mount
    └── /mlflow (WSGI middleware, only for file:// URIs)
```

### Dashboard State Machine

```
                    ┌──────────────┐
                    │   cmd_dashboard│
                    │   invoked     │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ Import uvicorn│
                    └──────┬───────┘
                           │ fail → exit(1) "uvicorn required"
                    ┌──────▼───────────────┐
                    │ create_dashboard_app()│
                    │  - ensure_initialized │
                    │  - create engine      │
                    │  - create repos       │
                    │  - DashboardApp()     │
                    └──────┬───────────────┘
                           │ fail → exit(1) "Failed to create"
                    ┌──────▼───────┐
                    │ Print URLs   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ uvicorn.run()│
                    │ (blocking)   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
      ┌───────▼──┐  ┌─────▼────┐  ┌───▼───────┐
      │ Ctrl+C   │  │ Error    │  │ Normal    │
      │ → exit(0)│  │ → exit(1)│  │ → exit(0) │
      └──────────┘  └──────────┘  └───────────┘
```

### DashboardApp Initialization Flow

```
DashboardApp.__init__()
│
├── 1. Create FastAPI app
├── 2. _setup_templates()
│       └── Jinja2Templates + stub helpers + filters (to_json, from_json)
├── 3. _setup_static_files()
│       └── Mount /static directory
├── 4. _mount_mlflow() [only if URI is file://, not http://]
│       └── Create MLflow WSGI app → mount at /mlflow
├── 5. Store repos in app.state
│       ├── app.state.workflow_repo
│       ├── app.state.workflow_run_repo (alias)
│       ├── app.state.agent_registry_repo
│       ├── app.state.templates
│       └── app.state.mlflow_tracking_uri
├── 6. Register startup event (log agent count)
├── 7. _include_routers() — all 6 route modules
├── 8. _register_template_helpers() — replace stubs with real implementations
├── 9. _create_main_dashboard_routes() — /, /health, /mlflow
└── 10. Add HTTP middleware (request context — currently no-op)
```

### HTMX Real-Time Update Pattern

The dashboard uses three mechanisms for real-time updates:

1. **HTMX Polling** (`hx-trigger="every 10s"`): Status panel polls `/api/status` every 10s
2. **HTMX SSE** (`sse-connect`): Metrics streams for workflow (5s) and agent (10s) updates
3. **HTMX Partial Swap**: Table partials (`/workflows/table`, `/agents/table`) for filtered refreshes

```
Browser                           Dashboard Server
  │                                      │
  │─── GET / ──────────────────────────►│  (full page load)
  │◄── dashboard.html ─────────────────│  (includes status_panel.html)
  │                                      │
  │─── GET /api/status ────────────────►│  (HTMX poll every 10s)
  │◄── status_panel.html (partial) ────│  (hx-swap="outerHTML")
  │                                      │
  │─── GET /metrics/workflows/stream ──►│  (SSE connection)
  │◄── event: workflow_update ─────────│  (every 5s)
  │◄── : heartbeat ────────────────────│
  │◄── event: workflow_update ─────────│
  │                                      │
  │─── GET /workflows/table?status=... ►│  (HTMX on filter change)
  │◄── workflows_table.html (partial) ─│
```

---

## 2. Chat UI (`cmd_chat`)

### Purpose

Conversational interface for generating valid workflow YAML configs through natural language. User describes a workflow, the LLM generates YAML, the system validates it against `WorkflowConfig` schema, and the user can download the result.

### Architecture

```
GradioChatUI
├── LLM Client (from create_llm)
├── ChatSessionRepository (SQLite persistence)
├── WorkflowConfig schema (validation)
│
├── Interface Layout (Gradio Blocks)
│   ├── ChatInterface (left, scale=3)
│   │   ├── Message input
│   │   ├── Example prompts (4 pre-defined)
│   │   └── Conversation history
│   ├── Actions Panel (right, scale=1)
│   │   ├── Download YAML button
│   │   ├── Validate Config button
│   │   └── Status textbox
│   └── Footer
│       ├── Session persistence note
│       └── Dashboard link
│
├── Core Methods
│   ├── generate_config(message, history, request)
│   │   ├── Get/create session from request
│   │   ├── Save user message to DB
│   │   ├── Build conversation context (last 5 messages)
│   │   ├── Call stream_chat() with CONFIG_GENERATION_PROMPT
│   │   ├── Extract YAML from response
│   │   ├── Validate against WorkflowConfig
│   │   └── Save config to session if valid
│   ├── download_config(history) → temp .yaml file path
│   ├── validate_config(history) → status message
│   └── create_interface() → gr.Blocks
│
└── Factory: create_gradio_chat_ui()
    ├── create_llm(llm_config, global_config)
    ├── create_storage_backend() → ChatSessionRepository
    └── GradioChatUI(llm_client, session_repo, dashboard_url)
```

### Chat UI State Machine

```
                   ┌───────────────┐
                   │  cmd_chat     │
                   │  invoked      │
                   └───────┬───────┘
                           │
                   ┌───────▼───────┐
                   │ create_gradio │
                   │ _chat_ui()    │
                   └───────┬───────┘
                           │ fail → exit(1) "Gradio required"
                   ┌───────▼───────┐
                   │ ui.launch()   │
                   │ (blocking)    │
                   └───────┬───────┘
                           │
                   ┌───────▼───────────────────────────┐
                   │     Gradio Server Running          │
                   │                                     │
                   │  User Message Flow:                 │
                   │  ┌──────────────────────────────┐  │
                   │  │ 1. User types message        │  │
                   │  │ 2. generate_config() called   │  │
                   │  │ 3. Get/create session (DB)    │  │
                   │  │ 4. Save user msg to session   │  │
                   │  │ 5. Build context (last 5)     │  │
                   │  │ 6. stream_chat() → LLM        │  │
                   │  │ 7. Yield response chunks      │  │
                   │  │ 8. Extract YAML block          │  │
                   │  │ 9. Validate vs WorkflowConfig  │  │
                   │  │    ├─ Valid → "Config valid!"  │  │
                   │  │    ├─ Invalid → show error     │  │
                   │  │    └─ No YAML → "No YAML found"│  │
                   │  │ 10. Save to session if valid   │  │
                   │  └──────────────────────────────┘  │
                   │                                     │
                   │  Download Flow:                     │
                   │  ┌──────────────────────────────┐  │
                   │  │ 1. Click "Download YAML"     │  │
                   │  │ 2. Extract YAML from last msg │  │
                   │  │ 3. Write to temp .yaml file   │  │
                   │  │ 4. Return file path to Gradio │  │
                   │  └──────────────────────────────┘  │
                   │                                     │
                   │  Validate Flow:                     │
                   │  ┌──────────────────────────────┐  │
                   │  │ 1. Click "Validate Config"   │  │
                   │  │ 2. Extract YAML from last msg │  │
                   │  │ 3. Parse + validate schema    │  │
                   │  │ 4. Display result in status   │  │
                   │  └──────────────────────────────┘  │
                   └───────────────────────────────────┘
```

### Session Persistence Model

```
Browser Session
  │
  ├── Session ID derived from: client.host:client.port
  │   └── Looks up recent sessions for this client
  │       ├── Found → reuse session_id
  │       └── Not found → create_session(client_id)
  │
  ├── Each message saved:
  │   ├── session_repo.add_message(session_id, "user", message)
  │   └── session_repo.add_message(session_id, "assistant", response, metadata)
  │
  └── Config saved on valid generation:
      └── session_repo.update_config(session_id, yaml_content)
```

---

## 3. Unified Launcher (`cmd_ui`)

### Purpose

Single command to launch the complete UI stack (Dashboard + Chat + MLflow) as managed child processes with unified shutdown.

### Architecture

```
cmd_ui
├── ProcessManager (multiprocessing orchestration)
│   ├── ServiceSpec("mlflow", _run_mlflow_with_config, config)
│   │   └── Runs: mlflow ui --host ... --port ...
│   │       └── Windows: job objects for reliable cleanup
│   ├── ServiceSpec("dashboard", _run_dashboard_with_config, config)
│   │   └── Runs: create_dashboard_app() + uvicorn.run()
│   └── ServiceSpec("chat", _run_chat_with_config, config)
│       └── Runs: create_gradio_chat_ui() + ui.launch()
│
├── Crash Detection
│   ├── check_restore_session() → detect dirty shutdown
│   ├── mark_session_dirty() → set flag before starting
│   └── save_session() → clear flag on clean shutdown
│
└── Signal Handling
    ├── SIGINT (Ctrl+C) → shutdown()
    └── SIGTERM (Unix) → shutdown()
```

### Unified Launcher State Machine

```
                    ┌──────────────┐
                    │   cmd_ui     │
                    │   invoked    │
                    └──────┬───────┘
                           │
                    ┌──────▼──────────────┐
                    │ Import uvicorn       │
                    └──────┬──────────────┘
                           │ fail → exit(1)
                    ┌──────▼──────────────┐
                    │ Create ProcessManager│
                    └──────┬──────────────┘
                           │
                    ┌──────▼──────────────┐
                    │ check_restore_session│
                    │ (crash detection)    │
                    └──────┬──────────────┘
                           │ dirty → warn user
                    ┌──────▼──────────────┐
                    │ mark_session_dirty() │
                    └──────┬──────────────┘
                           │
                    ┌──────▼──────────────────────────────────┐
                    │ Configure Services                       │
                    │                                          │
                    │  1. MLflow (if installed, no --mlflow-uri)│
                    │     └── ServiceSpec("mlflow")            │
                    │  2. Dashboard (always)                    │
                    │     └── ServiceSpec("dashboard")          │
                    │  3. Chat (unless --no-chat)               │
                    │     └── ServiceSpec("chat")               │
                    └──────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────────────┐
                    │ manager.start_all()  │
                    │ (spawn processes)    │
                    └──────┬──────────────┘
                           │
                    ┌──────▼──────────────┐
                    │ Print service URLs   │
                    └──────┬──────────────┘
                           │
                    ┌──────▼──────────────┐
                    │ manager.wait()       │
                    │ (blocks until done)  │
                    └──────┬──────────────┘
                           │
              ┌────────────┼──────────────┐
              │            │              │
      ┌───────▼──────┐  ┌─▼───────┐  ┌──▼──────────┐
      │ Ctrl+C       │  │ Process │  │ All exited  │
      │              │  │ crashed │  │ cleanly     │
      └──────┬───────┘  └────┬────┘  └──────┬──────┘
             │               │               │
      ┌──────▼───────────────▼───────────────▼──────┐
      │ manager.shutdown()                            │
      │  1. save_session(clean)                       │
      │  2. terminate() all alive processes            │
      │  3. join(timeout=5)                            │
      │  4. kill() stragglers                          │
      │  5. clear process list                         │
      └──────────────────────────────────────────────┘
```

### ProcessManager Lifecycle

```
ProcessManager States:
━━━━━━━━━━━━━━━━━━━━

  ┌─────────┐    add_service()    ┌──────────┐
  │  IDLE   │ ──────────────────► │ SERVICES │
  │         │                     │ QUEUED   │
  └─────────┘                     └────┬─────┘
                                       │ start_all()
                                ┌──────▼──────┐
                                │   RUNNING   │
                                │             │
                                │ Processes:  │
                                │ - spawned   │
                                │ - monitored │
                                │ - signals   │
                                │   registered│
                                └──────┬──────┘
                                       │ signal / process crash / wait() returns
                                ┌──────▼──────┐
                                │  SHUTTING   │
                                │   DOWN      │
                                │             │
                                │ 1. save sess│
                                │ 2. terminate│
                                │ 3. join(5s) │
                                │ 4. kill     │
                                └──────┬──────┘
                                       │
                                ┌──────▼──────┐
                                │  SHUTDOWN   │
                                │  COMPLETE   │
                                └─────────────┘

Per-Process States:
━━━━━━━━━━━━━━━━━━

  ┌─────────┐  Process.start()  ┌──────────┐
  │ CREATED │ ────────────────► │ RUNNING  │
  └─────────┘                   └────┬─────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
             ┌──────▼─────┐  ┌──────▼─────┐  ┌──────▼─────┐
             │ EXIT(0)    │  │ EXIT(!=0)  │  │ terminate()│
             │ (clean)    │  │ (crash)    │  │ (shutdown) │
             └────────────┘  └────────────┘  └──────┬─────┘
                                                     │
                                              ┌──────▼─────┐
                                              │ join(5s)   │
                                              └──────┬─────┘
                                                     │ timeout?
                                              ┌──────▼─────┐
                                              │ kill()     │
                                              └────────────┘
```

### Windows Compatibility

The ProcessManager has specific Windows handling:

1. **Pickle-safe targets**: All `Process(target=...)` callables must be module-level functions (not lambdas, closures, or bound methods). This is why `_run_dashboard_with_config`, `_run_chat_with_config`, `_run_mlflow_with_config` exist as module-level wrappers in `cli.py`.

2. **Config dict pattern**: Instead of `functools.partial` (not pickleable on Windows), each wrapper takes a single `config: dict` parameter that it unpacks.

3. **MLflow subprocess cleanup**: Uses Windows Job Objects (`pywin32`) to ensure MLflow child processes are terminated when the parent exits. Falls back to `atexit` + `subprocess.terminate()` if `pywin32` is not available.

4. **Signal handling**: Only `SIGINT` on Windows (no `SIGTERM`).

---

## 4. CLI Flags Reference

### `configurable-agents dashboard`

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind to |
| `--port` | `7861` | Port to listen on |
| `--db-url` | `sqlite:///configurable_agents.db` | Database URL for storage |
| `--mlflow-uri` | `None` | MLflow tracking URI for embedded UI |
| `-v, --verbose` | `false` | Enable verbose output |

### `configurable-agents chat`

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind to |
| `--port` | `7860` | Port to listen on |
| `--dashboard-url` | `DASHBOARD_URL` env or `http://localhost:7861` | URL for dashboard link |
| `--share` | `false` | Create a public Gradio link |
| `-v, --verbose` | `false` | Enable verbose output |

### `configurable-agents ui`

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind to (all services) |
| `--dashboard-port` | `7861` | Dashboard port |
| `--chat-port` | `7860` | Chat UI port |
| `--db-url` | `sqlite:///configurable_agents.db` | Database URL |
| `--mlflow-uri` | `None` | MLflow tracking URI (overrides auto-detect) |
| `--mlflow-port` | `5000` | MLflow UI port (ignored if `--mlflow-uri` set) |
| `--no-chat` | `false` | Skip Chat UI, start Dashboard only |
| `-v, --verbose` | `false` | Enable verbose output |

---

## 5. Data Flow Between Services

### Shared Database

All services share the same SQLite database (default: `configurable_agents.db`):

```
configurable_agents.db
├── workflow_runs ──────── Dashboard reads, Orchestrator writes
├── execution_states ───── Dashboard reads (state history)
├── agents ─────────────── Dashboard reads, Registry writes
├── orchestrators ──────── Dashboard reads, Registry writes
├── chat_sessions ──────── Chat UI reads/writes
├── chat_messages ──────── Chat UI reads/writes
└── session_states ─────── ProcessManager reads/writes (crash detection)
```

### Cross-Service Communication

```
Dashboard ◄──reads──► SQLite DB ◄──writes──► Workflow Executor
                │                                    ▲
                │                                    │
                ├──HTTP──► Remote Agent (/run) ──────┘
                │           (via orchestrator routes)
                │
Chat UI ──writes──► SQLite DB (chat_sessions)
                │
                └──HTTP──► LLM Provider (config generation)
```

### Orchestrator Flow (Dashboard → Remote Agent)

The orchestrator routes in the dashboard allow manual execution on remote deployed agents:

```
  User (Dashboard UI)
    │
    │ 1. POST /orchestrator/register
    │    {agent_id, agent_name, agent_url}
    │
    ▼
  Dashboard: orchestrator route
    │
    │ 2. Health check: GET {agent_url}/health
    │    └── Must return {"status": "alive"}
    │
    │ 3. Save to agents table (DB)
    │
    │ 4. HTMX polling: GET /orchestrator/health-check (every 10s)
    │    └── Checks all agents, returns HTML table partial
    │
    │ 5. POST /orchestrator/{agent_id}/execute
    │    {inputs: {...}}
    │
    ▼
  Dashboard creates WorkflowRunRecord(status="running")
    │
    │ 6. POST {agent_url}/run (inputs)
    │
    ▼
  Remote Agent executes workflow
    │
    │ 7. Returns {outputs, total_tokens, cost_usd}
    │
    ▼
  Dashboard updates WorkflowRunRecord(status="completed")
    └── Returns redirect to /workflows/{run_id}
```

---

## 6. Template Structure

### Inheritance

```
base.html (layout + nav + HTMX + CSS)
├── dashboard.html (main page, includes status_panel.html)
├── workflows.html (includes workflows_table.html)
├── workflow_detail.html
├── agents.html (includes agents_table.html)
├── experiments.html
├── optimization.html
├── orchestrator.html
└── mlflow_unavailable.html
```

### HTMX Partials (no base.html inheritance)

```
partials/status_panel.html ← /api/status (every 10s)
workflows_table.html ← /workflows/table
agents_table.html ← /agents/table
```

---

## 7. Optimization Routes (To Be Removed)

The `/optimization/*` routes in the dashboard depend on the `optimization/` module which is scheduled for removal (see [OPTIMIZATION_INVESTIGATION.md](OPTIMIZATION_INVESTIGATION.md)). These routes will be removed along with the module:

- `/optimization/experiments` — Lists MLflow experiments
- `/optimization/compare` — Compares variants
- `/optimization/apply` — Applies optimized prompt to YAML
- Template: `experiments.html`, `optimization.html`

**Note**: The `optimization_router` is imported and mounted in `DashboardApp._include_routers()`. Removing the optimization module will require removing this import and the associated templates.

---

## 8. Known Issues and Observations

### Dashboard/Agent Routes Overlap

Both `/agents/*` (agents_router) and `/orchestrator/*` (orchestrator_router) deal with agent management:
- **agents_router**: Read-only view of registered agents (list, table, deregister)
- **orchestrator_router**: CRUD operations + execution (register with health check, execute on agent, schema fetch)

The agent deregistration exists in both routers:
- `DELETE /agents/{id}` (agents_router)
- `DELETE /orchestrator/{id}` (orchestrator_router)

### Chat UI Streaming Issue

The `generate_config()` method collects the full response synchronously via `loop.run_until_complete()` before yielding chunks, which means the "streaming" is simulated (chunked output of already-complete text). True streaming would require async generator integration with Gradio.

### MLflow Mounting Logic

MLflow is mounted as WSGI middleware at `/mlflow` **only** when `mlflow_tracking_uri` is a file path (not HTTP). For HTTP URIs, the `/mlflow` route redirects to the external MLflow server. If MLflow is not installed, the route shows `mlflow_unavailable.html`.

---

## 9. Dependencies

### Dashboard

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `jinja2` | HTML templating |
| `sqlalchemy` | Database ORM |
| `mlflow` (optional) | Experiment tracking mount |
| `httpx` | HTTP client for agent health checks (orchestrator) |
| `psutil` (optional) | System resource monitoring in status panel |

### Chat UI

| Package | Purpose |
|---------|---------|
| `gradio>=4.0.0` | Chat interface framework |
| `pyyaml` | YAML parsing/validation |
| LLM provider SDK | Config generation |

### ProcessManager

| Package | Purpose |
|---------|---------|
| `multiprocessing` (stdlib) | Process spawning |
| `pywin32` (optional, Windows) | Job objects for MLflow cleanup |

---

## References

- [ADR-021: HTMX Dashboard](adr/ADR-021-htmx-dashboard.md)
- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture
- [OPTIMIZATION_INVESTIGATION.md](OPTIMIZATION_INVESTIGATION.md) — Optimization module removal plan
- [CL-003 Deep Flag Verification](implementation_logs/phase_5_cleanup_and_verification/CL-003_DEEP_FLAG_VERIFICATION.md) — CLI verification findings

---

*This document captures the complete UI architecture. Read before testing or modifying any UI-related code.*
