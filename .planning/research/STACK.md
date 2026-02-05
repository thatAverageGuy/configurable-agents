# Technology Stack

**Project:** Configurable Agents - v1.1 Core UX Polish
**Researched:** 2026-02-04
**Milestone:** Subsequent - v1.1 Core UX Polish

## Executive Summary

For v1.1 Core UX Polish, **minimal NEW stack additions** are needed. The focus is on **integration patterns** rather than new dependencies:

1. **Single-command startup** via Python `multiprocessing` (built-in, no new dependency)
2. **Auto-initialization** via existing SQLAlchemy 2.0 `Base.metadata.create_all()`
3. **Unified workspace** via Gradio's `mount_gradio_app()` into existing FastAPI
4. **Navigation redesign** via HTMX template reorganization (no new dependencies)

**Recommendation:** Add 0 new production dependencies. All UX improvements can be achieved with existing stack + Python standard library.

---

## Stack Changes for v1.1

### Single-Command Startup

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Python `multiprocessing`** | Built-in (3.10+) | Process manager for parallel services | No external dependency, cross-platform, integrates with existing CLI |
| **Python `threading`** | Built-in | Background service management | Simpler than subprocess for same-process logging |

**Alternatives Considered:**

| Alternative | Why NOT |
|-------------|---------|
| Honcho | Adds dependency, Procfile-based (not native Python) |
| Supervisor | Overkill for dev-friendly single command, requires separate install |
| Gunicorn | Production server, not ideal for dev experience |
| `uvicorn` workers | Multi-worker for scaling, not multi-service management |

**Pattern:**
```python
# Use multiprocessing.Process to run Gradio + FastAPI in parallel
# Single command: configurable-agents start
# Launches both: Dashboard (7861) + Chat UI (7860) + optional MLFlow (5000)
```

**Sources:**
- [Using Honcho to Create a Multi-Process Docker Container](https://www.cloudbees.com/blog/using-honcho-create-multi-process-docker-container) (for comparison)
- [Uvicorn Deployment Guide](https://uvicorn.dev/deployment/) (process manager context)

---

### Auto-Initialization

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **SQLAlchemy 2.0** | Already installed (`>=2.0.46`) | Auto-create tables on first run | Already in stack, `create_all()` is idempotent |
| **Python `pathlib`** | Built-in | Database file creation check | Cross-platform path handling |

**Implementation Pattern:**
```python
# In create_storage_backend():
# 1. Check if database file exists
# 2. If not, create directory and run Base.metadata.create_all(engine)
# 3. Log initialization message (not error)
```

**Graceful Degradation for MLFlow:**
- Check if MLFlow UI is accessible before mounting
- If not available, show banner instead of raw error
- Use try/except around `mlflow.server.app.create_app()`

**Sources:**
- [SQLAlchemy Metadata.create_all()](http://docs.sqlalchemy.org/en/latest/core/metadata.html) (official docs)
- [SQLAlchemy Error Handling](http://docs.sqlalchemy.org/en/latest/errors.html) (graceful patterns)
- [Best Practices for Alembic and SQLAlchemy](https://medium.com/@pavel.loginov.dev/best-practices-for-alembic-and-sqlalchemy-73e4c8a6c205)

---

### Unified Workspace (Gradio + FastAPI Integration)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Gradio `mount_gradio_app`** | Already installed (`>=4.0.0`) | Mount Gradio into FastAPI | Official integration, single port |
| **FastAPI `ASGIMiddleware`** | Already installed | MLFlow WSGI mounting (existing pattern) | Already used for MLFlow |

**Implementation Pattern:**
```python
from fastapi import FastAPI
import gradio as gr

# Create main FastAPI app
app = FastAPI()

# Create Gradio Blocks
chat_ui = create_gradio_chat_ui(...).create_interface()

# Mount Gradio at /chat path
app = gr.mount_gradio_app(app, chat_ui, path="/chat")

# MLFlow already mounted at /mlflow via WSGIMiddleware
```

**Benefits:**
- Single port (e.g., 7861) serves both dashboard and chat UI
- Shared authentication/middleware
- Unified navigation in templates
- Reduced cognitive load (one URL to remember)

**Known Issues:**
- Root path bugs in Gradio 4.21.0+ ([GitHub Issue #10590](https://github.com/gradio-app/gradio/issues/10590))
- Workaround: Set `root_path` explicitly or pin Gradio version

**Sources:**
- [Gradio mount_gradio_app Documentation](https://www.gradio.app/docs/gradio/mount_gradio_app) (official)
- [Gradio + FastAPI Integration (Chinese, Mar 2024)](https://blog.csdn.net/x1131230123/article/details/137050578) (implementation examples)
- [FastAPI+Gradio Golden Combination (Jan 2026)](https://cloud.tencent.com/developer/article/2617624) (architecture patterns)

---

### Navigation Redesign (HTMX Templates)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **HTMX 1.9+** | Already installed (CDN in base.html) | Dynamic nav without JS framework | Already in stack, fits "boring technology" philosophy |
| **Jinja2 templates** | Already installed (FastAPI) | Server-side rendering | Existing infrastructure |

**Current Nav Structure:**
```
/ (Dashboard)
/workflows
/agents
/orchestrator
/mlflow (iframe)
/optimization/experiments
```

**Proposed Nav Structure (Mental Model):**
```
/ (Home - guided entry point)
  ├── /workflows (create, manage, run)
  ├── /chat (config generator)
  ├── /monitor (agents, metrics, MLFlow)
  └── /settings (config, registry)
```

**No new dependencies needed** - template reorganization only.

---

## Existing Stack (v1.0) - No Changes

### Core Framework

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | >=3.10 | Runtime |
| Pydantic | >=2.0 | Config validation |
| LangGraph | >=0.0.20 | Workflow execution |
| LangChain | >=0.1.0 | LLM/tools integration |
| LiteLLM | >=1.80.0 | Multi-provider LLM |

### Storage & Observability

| Technology | Version | Purpose |
|------------|---------|---------|
| SQLAlchemy | >=2.0.46 | Database ORM |
| MLFlow | >=3.9.0 | Experiment tracking |
| Rich | >=13.0.0 | CLI formatting |

### UI/Web

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | Latest | Dashboard API |
| Gradio | >=4.0.0 | Chat UI |
| HTMX | 1.9.10 (CDN) | Dynamic dashboard |
| Jinja2 | Latest | Templates |
| Uvicorn | Latest | ASGI server |

---

## Installation (No New Dependencies)

```bash
# All dependencies already in v1.0
pip install configurable-agents

# Or for development
pip install -e ".[ui,chat]"

# Single-command startup (NEW in v1.1)
configurable-agents start
```

---

## What NOT to Add

| Anti-Feature | Why Avoid |
|--------------|-----------|
| React/Vue/etc. | Python-only constraint, adds build complexity |
| Honcho/Foreman | Unnecessary dependency, `multiprocessing` sufficient |
| Gunicorn | Production optimization, not needed for dev UX |
| Alembic | Overkill for v1.1, `create_all()` is sufficient for now |
| nginx/reverse proxy | Adds deployment complexity, FastAPI handles this |
| Celery/Redis | Background jobs overkill, use `asyncio` or threading |

---

## Integration with Existing Stack

### Process Flow for `configurable-agents start`

```python
# cli.py - NEW command

def cmd_start(args: argparse.Namespace) -> int:
    """Start all services with single command."""
    from multiprocessing import Process
    import time

    processes = []

    # 1. Initialize database (auto-create if needed)
    init_database_first_run(args.db_url)

    # 2. Start Dashboard (FastAPI + HTMX)
    dashboard_proc = Process(
        target=run_dashboard,
        kwargs={"host": args.host, "port": args.port}
    )
    processes.append(dashboard_proc)

    # 3. Start Chat UI (Gradio) - OR mount into FastAPI
    if args.separate_chat:
        chat_proc = Process(
            target=run_chat,
            kwargs={"host": args.host, "port": args.chat_port}
        )
        processes.append(chat_proc)

    # 4. Start MLFlow (optional)
    if args.mlflow:
        mlflow_proc = Process(
            target=run_mlflow,
            kwargs={"host": args.host, "port": args.mlflow_port}
        )
        processes.append(mlflow_proc)

    # Start all processes
    for p in processes:
        p.start()

    # Wait for interrupt
    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print_info("Shutting down...")
        for p in processes:
            p.terminate()
            p.join()

    return 0
```

### Database Initialization Pattern

```python
# storage/factory.py - ENHANCED

def create_storage_backend(config: Optional[StorageConfig] = None):
    if config is None:
        config = StorageConfig()

    backend = config.backend
    db_path = config.path

    # Auto-create database directory
    from pathlib import Path
    db_file = Path(db_path)
    if not db_file.exists():
        db_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created database directory: {db_file.parent}")

    # Create engine
    engine = create_engine(f"sqlite:///{db_path}")

    # Auto-create tables (idempotent)
    try:
        Base.metadata.create_all(engine)
        logger.info(f"Database initialized: {db_path}")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # ... rest of function
```

### Gradio Mount Pattern

```python
# ui/dashboard/app.py - ENHANCED

def create_dashboard_app(...):
    app = FastAPI(...)

    # Mount Gradio Chat UI at /chat
    from configurable_agents.ui import create_gradio_chat_ui
    chat_ui = create_gradio_chat_ui(...)
    app = gr.mount_gradio_app(
        app,
        chat_ui.create_interface(),
        path="/chat",
        auth_message="Configurable Agents Chat UI"
    )

    # Mount MLFlow (existing pattern)
    if mlflow_tracking_uri:
        _mount_mlflow(mlflow_tracking_uri)

    return app
```

---

## Sources

### Process Management
- [CloudBees: Using Honcho for Multi-Process Docker](https://www.cloudbees.com/blog/using-honcho-create-multi-process-docker-container) (comparison)
- [Reddit: Multiple Processes in Single Docker Container](https://www.reddit.com/r/Python/comments/1f432fi/multiple_processes_in_a_single_docker_container/) (community patterns)
- [LibHunt: Supervisor vs Honcho](https://www.libhunt.com/compare/supervisor-vs-honcho) (tool comparison)
- [Uvicorn Deployment Guide](https://uvicorn.dev/deployment/) (official docs)
- [FastAPI Server Workers](https://fastapi.tiangolo.com/deployment/server-workers/) (worker patterns)

### Database Initialization
- [SQLAlchemy Metadata.create_all()](http://docs.sqlalchemy.org/en/latest/core/metadata.html) (official)
- [SQLAlchemy Error Messages](http://docs.sqlalchemy.org/en/latest/errors.html) (error handling)
- [Best Practices for Alembic and SQLAlchemy](https://medium.com/@pavel.loginov.dev/best-practices-for-alembic-and-sqlalchemy-73e4c8a6c205) (migration patterns)
- [Alembic Auto-Generating Migrations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html) (for future v1.2+)

### Gradio + FastAPI Integration
- [Gradio mount_gradio_app Documentation](https://www.gradio.app/docs/gradio/mount_gradio_app) (official - HIGH confidence)
- [FastAPI+Gradio Golden Combination Architecture](https://cloud.tencent.com/developer/article/2617624) (Jan 2026 - MEDIUM confidence)
- [Gradio + FastAPI Production Deployment](https://blog.csdn.net/gitblog_00136/article/details/151110049) (Sep 2025 - MEDIUM confidence)
- [Gradio RootPath Bug Report](https://github.com/gradio-app/gradio/issues/10590) (Feb 2025 - known issue)
- [Hugging Face: FastAPI + Gradio Understanding](https://discuss.huggingface.co/t/help-understanding-link-between-fastapi-and-gradio/47914) (community discussion)
- [Gradio Production: Secure & Scalable](https://medium.com/@marek.gmyrek/gradio-from-prototype-to-production-secure-scalable-gradio-apps-for-data-scientists-739cebaf669b) (production patterns)
- [Chinese Tutorial: Embedding Gradio in FastAPI](https://blog.csdn.net/x1131230123/article/details/137050578) (Mar 2024 - implementation examples)

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Process Management (multiprocessing) | HIGH | Python built-in, well-documented |
| Auto-initialization (SQLAlchemy) | HIGH | Existing stack, `create_all()` is standard pattern |
| Gradio FastAPI Mount | HIGH | Official `mount_gradio_app()` API, verified in docs |
| Navigation Redesign (HTMX) | HIGH | Template reorganization only, no new tech |
| MLFlow Graceful Degradation | MEDIUM | Pattern exists, needs implementation verification |

### Gaps & Phase-Specific Research Flags

| Topic | Status | Notes |
|-------|--------|-------|
| Gradio root_path behind proxy | Phase-specific research | Known issue in 4.21.0+, verify if affecting us |
| MLFlow auto-start from Python | Phase-specific research | May need subprocess pattern if embedding fails |
| Windows multiprocessing quirks | Phase-specific research | Spawn vs fork on Windows may affect logging |

---

## Version Compatibility Matrix

| Dependency | Current (v1.0) | v1.1 Target | Notes |
|------------|----------------|-------------|-------|
| Python | >=3.10 | >=3.10 | No change |
| Gradio | >=4.0.0 | >=4.0.0 | Watch 4.21.0+ root_path bug |
| FastAPI | Latest | Latest | No change |
| SQLAlchemy | >=2.0.46 | >=2.0.46 | No change |
| MLFlow | >=3.9.0 | >=3.9.0 | No change |

---

## Summary for Roadmap

**New Dependencies:** 0

**Key Integration Points:**
1. `configurable-agents start` command using `multiprocessing`
2. Database auto-creation via `Base.metadata.create_all()`
3. Gradio mounted into FastAPI at `/chat` path
4. MLFlow graceful degradation with try/except banner

**Implementation Complexity:** Low to Medium
- Low: Database init, navigation redesign
- Medium: Process management, Gradio mounting

**Risk Areas:**
- Gradio version compatibility (root_path bug)
- Windows multiprocessing behavior (spawn vs fork)
- MLFlow embedding stability
