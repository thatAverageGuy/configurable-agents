# Phase 5: Foundation & Reliability - Research

**Researched:** 2026-02-04
**Domain:** Process Management, Auto-Initialization, Status Dashboards, Error Handling
**Confidence:** HIGH

## Summary

Phase 5 focuses on making the platform "just work" with a single command. The core technical challenges are:
1. **Single-command startup** using Python `multiprocessing` to orchestrate Dashboard (FastAPI) + Chat UI (Gradio) + optional MLFlow
2. **Auto-initialization** of databases using SQLAlchemy's `create_all()` with graceful degradation
3. **Status dashboard** with periodic refresh via HTMX `hx-trigger="every Ns"`
4. **Error message formatting** with actionable resolution steps and collapsible technical details
5. **Graceful shutdown** handling signals and cleanup across all child processes
6. **Windows compatibility** for multiprocessing (spawn vs fork)

The existing stack already has all necessary dependencies. The primary patterns use Python's built-in `multiprocessing` module, SQLAlchemy's `Base.metadata.create_all()` for database initialization, Rich library for startup spinners, and HTMX's polling for dashboard updates.

**Primary recommendation:** Use `multiprocessing.Process` with explicit signal handling, `create_all()` with existence checking, HTMX polling at 5-10 second intervals, and platform-aware start method detection.

## Standard Stack

The following libraries are **already installed** and will be used:

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Python `multiprocessing`** | Built-in (3.10+) | Process manager for parallel services | No external dependency, cross-platform, integrates with existing CLI |
| **Python `asyncio` + `signal`** | Built-in | Graceful shutdown handling | Standard library signal handling |
| **SQLAlchemy 2.0** | >=2.0.46 (installed) | Auto-create tables on first run | `create_all()` is idempotent and standard pattern |
| **Rich** | >=13.0.0 (installed) | CLI spinners and startup progress | Already in stack for formatted output |

### Supporting (Already Installed)

| Library | Purpose | When to Use |
|---------|---------|-------------|
| **FastAPI** | Dashboard API with lifespan events | Database init on startup, graceful degradation |
| **HTMX** | Status dashboard periodic refresh | `hx-trigger="every Ns"` for auto-updates |
| **Gradio** | Chat UI | May be mounted or run as separate process |

### Alternatives Considered (Rejected)

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `multiprocessing` | Honcho, Supervisor | Adds dependency, unnecessary for dev experience |
| SQLAlchemy `create_all()` | Alembic migrations | Overkill for single-user SQLite, adds complexity |
| HTMX polling | SSE (Server-Sent Events) | SSE is more complex, polling sufficient for status updates |
| Separate processes | Docker Compose | Already used for production, multiprocessing better for dev |

**No new dependencies required.**

## Architecture Patterns

### Recommended Project Structure

```
src/configurable_agents/
├── process/
│   ├── __init__.py
│   ├── manager.py          # NEW: ProcessManager for startup/shutdown
│   └── health.py           # NEW: Health checks for services
├── storage/
│   ├── __init__.py
│   ├── factory.py          # ENHANCED: Auto-initialization logic
│   └── health.py           # NEW: Database health checks
├── ui/
│   ├── dashboard/
│   │   ├── app.py          # ENHANCED: Lifespan events for auto-init
│   │   └── routes/
│   │       └── status.py   # NEW: Status dashboard endpoints
│   └── templates/
│       └── status.html     # NEW: Status dashboard template
└── cli.py                  # ENHANCED: New `start` command
```

### Pattern 1: ProcessManager for Single-Command Startup

**What:** A wrapper around Python's `multiprocessing.Process` that manages multiple services (Dashboard, Chat UI, MLFlow) with unified logging and graceful shutdown.

**When to use:** Implementing `configurable-agents start` command to launch all services together.

**Example:**
```python
# src/configurable_agents/process/manager.py

import signal
import sys
from multiprocessing import Process
from typing import List, Optional, Callable

class ServiceSpec:
    """Specification for a service to run."""
    def __init__(
        self,
        name: str,
        target: Callable,
        args: tuple = (),
        kwargs: dict = None,
    ):
        self.name = name
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}

class ProcessManager:
    """Manage multiple processes with graceful shutdown."""

    def __init__(self, verbose: bool = False):
        self.services: List[ServiceSpec] = []
        self.processes: dict = {}
        self.verbose = verbose
        self._shutdown_requested = False

    def add_service(self, service: ServiceSpec):
        """Add a service to be managed."""
        self.services.append(service)

    def start_all(self):
        """Start all registered services."""
        for service in self.services:
            process = Process(
                target=self._run_service,
                args=(service,),
                name=service.name,
            )
            process.start()
            self.processes[service.name] = process

    def _run_service(self, service: ServiceSpec):
        """Run a service with error handling."""
        try:
            service.target(*service.args, **service.kwargs)
        except Exception as e:
            if self.verbose:
                print(f"Service {service.name} failed: {e}", file=sys.stderr)

    def wait(self):
        """Wait for all processes, handling shutdown signals."""
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            # Wait for all processes
            for process in self.processes.values():
                process.join()
        except KeyboardInterrupt:
            self._shutdown()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self._shutdown_requested = True
        self._shutdown()

    def _shutdown(self):
        """Gracefully shutdown all processes."""
        for name, process in self.processes.items():
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
```

**Source:** Based on established patterns from [Graceful exit with Python multiprocessing](https://the-fonz.gitlab.io/posts/python-multiprocessing/) and [Robust Process Management in Python](https://medium.com/@RampantLions/robust-process-management-in-python-named-workers-messaging-queues-and-graceful-shutdown-cacfe2b8e7ca).

### Pattern 2: Auto-Initialization with Graceful Degradation

**What:** Database initialization that runs on first startup, is idempotent, and handles failures gracefully without blocking the entire application.

**When to use:** Any database-backed service starting up (Dashboard, CLI commands).

**Example:**
```python
# src/configurable_agents/storage/factory.py - ENHANCED

from pathlib import Path
from sqlalchemy import create_engine, inspect
from configurable_agents.storage.models import Base
import logging

logger = logging.getLogger(__name__)

def ensure_database_initialized(db_url: str) -> bool:
    """
    Ensure database tables exist, creating them if needed.

    Args:
        db_url: SQLAlchemy database URL

    Returns:
        True if database is ready, False if degraded mode
    """
    # Extract path from SQLite URL
    if db_url.startswith("sqlite:///"):
        db_path = Path(db_url.replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(db_url)

    try:
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if not existing_tables:
            # First run - create all tables
            logger.info("Initializing database...")
            Base.metadata.create_all(engine)
            logger.info("Database initialized successfully")
        else:
            logger.debug(f"Using existing database with {len(existing_tables)} tables")

        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

# Modified create_storage_backend
def create_storage_backend(config=None, auto_init=True):
    if config is None:
        from configurable_agents.config.schema import StorageConfig
        config = StorageConfig()

    if auto_init:
        ensure_database_initialized(f"sqlite:///{config.path}")

    # ... rest of existing function
```

**Source:** SQLAlchemy standard pattern from [Metadata.create_all()](http://docs.sqlalchemy.org/en/latest/core/metadata.html) documentation.

### Pattern 3: FastAPI Lifespan Events for Startup

**What:** Use FastAPI's `lifespan` context manager for database initialization on startup and cleanup on shutdown.

**When to use:** Dashboard application startup.

**Example:**
```python
# src/configurable_agents/ui/dashboard/app.py - ENHANCED

from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup/shutdown with graceful degradation."""
    # Startup
    from configurable_agents.storage import ensure_database_initialized

    db_url = getattr(app.state, "db_url", "sqlite:///configurable_agents.db")

    try:
        db_ready = ensure_database_initialized(db_url)
        app.state.db_ready = db_ready

        if not db_ready:
            logger.warning("Running in degraded mode - database unavailable")

    except Exception as e:
        logger.error(f"Startup error: {e}")
        app.state.db_ready = False

    yield

    # Shutdown
    logger.info("Dashboard shutting down...")

# Create app with lifespan
app = FastAPI(
    title="Configurable Agents Dashboard",
    lifespan=lifespan,
)
```

**Source:** FastAPI official [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) documentation.

### Pattern 4: Status Dashboard with HTMX Polling

**What:** Use HTMX's `hx-trigger="every Ns"` attribute for periodic status updates without JavaScript.

**When to use:** Dashboard status widgets showing active workflows, agent health, errors.

**Example:**
```html
<!-- templates/status.html -->
<div class="status-grid">
  <!-- Active Workflows -->
  <div class="status-card"
       hx-get="/api/status/workflows"
       hx-trigger="load, every 5s"
       hx-swap="innerHTML">
    Loading workflow status...
  </div>

  <!-- Agent Health -->
  <div class="status-card"
       hx-get="/api/status/agents"
       hx-trigger="load, every 10s"
       hx-swap="innerHTML">
    Loading agent status...
  </div>

  <!-- Recent Errors -->
  <div class="status-card"
       hx-get="/api/status/errors"
       hx-trigger="load, every 5s"
       hx-swap="innerHTML">
    Loading recent errors...
  </div>

  <!-- System Resources -->
  <div class="status-card"
       hx-get="/api/status/resources"
       hx-trigger="load, every 10s"
       hx-swap="innerHTML">
    Loading system status...
  </div>
</div>
```

**Backend endpoint:**
```python
# src/configurable_agents/ui/dashboard/routes/status.py

@router.get("/workflows")
async def workflow_status(request: Request):
    """Return HTML fragment with workflow counts."""
    from configurable_agents.storage import get_workflow_counts

    try:
        active_count, total_count = get_workflow_counts()
        return f"""
        <div class="status-item">
            <span class="label">Workflows:</span>
            <span class="value">{active_count} / {total_count} active</span>
        </div>
        """
    except Exception as e:
        return f"<div class='status-error'>Status unavailable</div>"
```

**Source:** HTMX [load polling](https://htmx.org/docs/) documentation and [How to Build Web Polling with HTMX](https://hamy.xyz/blog/2024-07_htmx-polling-example).

### Pattern 5: Rich Spinners for Startup Feedback

**What:** Use Rich library's `Progress` and `Status` classes for visual startup feedback.

**When to use:** `configurable-agents start` command to show service startup progress.

**Example:**
```python
# src/configurable_agents/cli.py - ENHANCED for `start` command

from rich.console import Console
from rich.status import Status

def cmd_start(args: argparse.Namespace) -> int:
    """Start all services with single command."""
    console = Console()

    services_to_start = [
        ("Database", ensure_database_initialized, (args.db_url,)),
        ("Dashboard", run_dashboard, (args.host, args.port)),
    ]

    if args.chat:
        services_to_start.append(("Chat UI", run_chat, (args.host, args.chat_port)))

    if args.mlflow:
        services_to_start.append(("MLFlow", run_mlflow, (args.mlflow_port,)))

    with Status("Starting services...", console=console) as status:
        for name, func, fn_args in services_to_start:
            status.update(f"Starting {name}...")
            try:
                func(*fn_args)
                console.print(f"[green]✓[/green] {name} started")
            except Exception as e:
                console.print(f"[red]✗[/red] {name} failed: {e}")
                return 1

    console.print(f"\n[bold green]All {len(services_to_start)} services started successfully![/bold green]")
    return 0
```

**Source:** Rich [Progress Display](https://rich.readthedocs.io/en/latest/progress.html) documentation.

### Anti-Patterns to Avoid

- **Blocking on MLFlow startup:** Don't make the entire dashboard wait for MLFlow. Use graceful degradation instead.
- **Silent auto-init failures:** Always log initialization status and provide clear error messages with action items.
- **Fork on Windows:** Windows only supports `spawn` start method. Always use `get_context()` or explicitly set start method.
- **Polling too frequently:** Don't use `< 2s` polling intervals. Most dashboards work fine with 5-10s intervals.
- **Hiding errors behind "simplified" UI:** Always provide verbose/debug modes that show full error details.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Process orchestration | Custom signal handlers, process tracking | `multiprocessing.Process` with signal handlers | Built-in, cross-platform, well-tested |
| Database initialization | Custom table creation logic | SQLAlchemy `Base.metadata.create_all()` | Idempotent, handles schema, standard pattern |
| Startup spinners | ANSI codes, manual cursor control | Rich `Status`/`Progress` | Handles edge cases, cross-platform, already installed |
| Status updates | WebSocket servers, long-polling endpoints | HTMX `hx-trigger="every Ns"` | Zero JS needed, simple, sufficient for dashboards |
| Graceful shutdown | Custom atexit handlers | FastAPI `lifespan` + signal handlers | Standard pattern, async-safe |

## Common Pitfalls

### Pitfall 1: Windows Multiprocessing Spawn vs Fork

**What goes wrong:** Code that works on Linux/macOS fails on Windows because `fork` is not available. Global state, open file handles, and database connections don't propagate to child processes.

**Why it happens:** Windows only supports `spawn` start method which creates a fresh Python interpreter and re-imports all modules. Code in `if __name__ == "__main__":` blocks won't run in child processes.

**How to avoid:**
- Use `multiprocessing.get_context("spawn")` explicitly on all platforms for consistency
- Ensure all entry points are top-level functions (not lambdas or local functions)
- Don't rely on global state in child processes
- Use picklable arguments only

**Warning signs:**
- Pickle errors when starting processes
- Child processes hanging or not starting
- Database connection errors in subprocesses

**Source:** [Python Multiprocessing, Revisited: Fork vs Spawn](https://medium.com/@Nexumo_/python-multiprocessing-revisited-fork-vs-spawn-5b9216fd5710) and [StackOverflow: multiprocessing fork() vs spawn()](https://stackoverflow.com/questions/64095876/multiprocessing-fork-vs-spawn).

### Pitfall 2: MLFlow Blocking Dashboard Startup

**What goes wrong:** If MLFlow server fails to start (port conflict, dependency issue), the entire dashboard becomes unusable.

**Why it happens:** Startup sequence waits for MLFlow before serving. MLFlow is treated as hard dependency.

**How to avoid:**
- Use graceful degradation: Dashboard works without MLFlow, shows banner
- Start MLFlow asynchronously with timeout
- Provide clear status indicator: "MLFlow: not running"
- Make MLFlow optional via flag

**Warning signs:**
- Dashboard returns 503 when MLFlow is down
- Users asking "why can't I access dashboard?"
- Port conflicts preventing all services

### Pitfall 3: Silent Database Initialization Failures

**What goes wrong:** Database creation fails silently (permissions, disk full) leaving system in undefined state.

**Why it happens:** Errors are logged but not surfaced to users, or initialization happens asynchronously without health checks.

**How to avoid:**
- Block on critical failures with actionable error messages
- Use `Base.metadata.create_all()` which is idempotent
- Check table existence before attempting operations
- Provide health check endpoint

**Warning signs:**
- "Table not found" errors mid-execution
- Empty databases despite workflow runs
- Support tickets about "data not saving"

### Pitfall 4: Alert Fatigue from Status Dashboard

**What goes wrong:** Dashboard shows too many status indicators, users ignore everything.

**Why it happens:** Every metric is shown with equal priority. No tiering or smart aggregation.

**How to avoid:**
- Show max 5 key metrics by default
- Tier indicators: Critical (always visible), Warning (collapsible), Info (on-demand)
- Only alert on state changes, not continuous status
- Use longer polling intervals (5-10s) for less critical data

**Warning signs:**
- Users disabling status dashboard
- All indicators showing "critical" (alert fatigue)
- Requests to "simplify" status display

**Source:** [Alert Fatigue and Dashboard Overload: Why Cybersecurity Needs Better UX](https://medium.com/design-bootcamp/alert-fatigue-and-dashboard-overload-why-cybersecurity-needs-better-ux-1f3bd32ad81c).

### Pitfall 5: Gradio root_path Behind Reverse Proxy

**What goes wrong:** Gradio assets (theme.css) return 404 when accessing through reverse proxy or mounted at subpath.

**Why it happens:** Known bug in Gradio 4.21.0+ where `root_path` configuration is not properly handled. Static asset paths don't include the base path.

**How to avoid:**
- Consider running Gradio as separate process on its own port
- If mounting, test thoroughly with reverse proxy setup
- Pin Gradio version below 4.21.0 if mounting is required
- Alternatively, use iframe embedding instead of `mount_gradio_app()`

**Warning signs:**
- Theme not loading when accessing dashboard
- Console errors for missing .css files
- Layout broken in embedded Gradio UI

**Source:** [Gradio Issue #10590: RootPath not properly working from 4.21.0](https://github.com/gradio-app/gradio/issues/10590) and [mount_gradio_app subpath issues](https://github.com/gradio-app/gradio/issues/4291).

## Code Examples

### Single-Command Startup with ProcessManager

```python
# cli.py - new cmd_start function

def cmd_start(args: argparse.Namespace) -> int:
    """Start all services with single command."""
    from configurable_agents.process.manager import ProcessManager, ServiceSpec
    from configurable_agents.storage import ensure_database_initialized

    console = Console()

    # Step 1: Initialize database
    with console.status("[bold cyan]Initializing database...", spinner="dots"):
        try:
            ensure_database_initialized(args.db_url)
            console.print("[green]✓[/green] Database ready")
        except Exception as e:
            console.print(f"[red]✗[/red] Database failed: {e}")
            console.print(f"  [yellow]Fix:[/yellow] Check permissions and disk space")
            return 1

    # Step 2: Start services via ProcessManager
    manager = ProcessManager(verbose=args.verbose)

    # Dashboard (always)
    manager.add_service(ServiceSpec(
        name="dashboard",
        target=run_dashboard,
        kwargs={"host": args.host, "port": args.port, "db_url": args.db_url},
    ))

    # Chat UI (optional)
    if not args.no_chat:
        manager.add_service(ServiceSpec(
            name="chat",
            target=run_chat,
            kwargs={"host": args.host, "port": args.chat_port},
        ))

    # MLFlow (optional)
    if args.mlflow:
        manager.add_service(ServiceSpec(
            name="mlflow",
            target=run_mlflow,
            kwargs={"port": args.mlflow_port},
        ))

    # Start all
    manager.start_all()

    # Print access URLs
    console.print(f"\n[bold]Services started:[/bold]")
    console.print(f"  Dashboard: http://localhost:{args.port}")
    if not args.no_chat:
        console.print(f"  Chat UI:   http://localhost:{args.chat_port}")
    if args.mlflow:
        console.print(f"  MLFlow:    http://localhost:{args.mlflow_port}")
    console.print(f"\n[yellow]Press Ctrl+C to stop all services[/yellow]")

    # Wait for shutdown
    manager.wait()
    return 0
```

### Rich Startup Progress with Multiple Services

```python
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console

def show_startup_progress(services: List[Tuple[str, Callable]]) -> dict:
    """
    Show startup progress for multiple services.

    Returns:
        Dict mapping service names to (success: bool, error: str)
    """
    console = Console()
    results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        tasks = {
            name: progress.add_task(f"Starting {name}...", total=None)
            for name, _ in services
        }

        for name, func in services:
            try:
                func()
                progress.update(tasks[name], completed=True)
                console.print(f"[green]✓[/green] {name} started")
                results[name] = (True, None)
            except Exception as e:
                console.print(f"[red]✗[/red] {name} failed: {e}")
                results[name] = (False, str(e))

    return results
```

### Error Message with Actionable Resolution

```python
# Format errors with description + resolution + details

class FormattedError:
    """Structured error with actionable resolution."""

    def __init__(
        self,
        description: str,
        resolution: str,
        technical_details: str = None,
    ):
        self.description = description
        self.resolution = resolution
        self.technical_details = technical_details

    def print(self, verbose: bool = False):
        """Print formatted error to console."""
        console.print(f"[red]✗[/red] {self.description}")
        console.print(f"  [yellow]Fix:[/yellow] {self.resolution}")

        if verbose and self.technical_details:
            console.print(f"\n[dim]Technical details:[/dim]")
            console.print(f"[dim]{self.technical_details}[/dim]")

# Common error patterns
COMMON_ERRORS = {
    "port_in_use": FormattedError(
        description="Port {port} is already in use",
        resolution="Stop the conflicting service or use --port to specify a different port",
        technical_details="Try: lsof -i :{port} (Linux/macOS) or netstat -ano | findstr :{port} (Windows)",
    ),
    "permission_denied": FormattedError(
        description="Permission denied writing to {path}",
        resolution="Check file permissions or set AGENTS_DB_PATH to a writable location",
        technical_details="Current user lacks write access to: {path}",
    ),
    "disk_full": FormattedError(
        description="Disk full, cannot write to database",
        resolution="Free up disk space and try again",
        technical_details="Available space: {bytes_free} bytes",
    ),
}
```

### Database Health Check Endpoint

```python
# routes/health.py

@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint with database status."""
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
    }

    # Check database
    try:
        # Simple query to test connection
        with Session(request.app.state.engine) as session:
            session.execute(text("SELECT 1"))
        health["services"]["database"] = "ok"
    except Exception as e:
        health["status"] = "degraded"
        health["services"]["database"] = f"error: {e}"

    # Check MLFlow if configured
    mlflow_uri = getattr(request.app.state, "mlflow_tracking_uri", None)
    if mlflow_uri:
        try:
            client = MlflowClient(mlflow_uri)
            client.search_experiments(max_results=1)
            health["services"]["mlflow"] = "ok"
        except Exception:
            health["services"]["mlflow"] = "unavailable"

    return health
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` decorator | `lifespan` context manager | FastAPI 0.93.0+ | Unified startup/shutdown, async-safe |
| Fork-based multiprocessing | Spawn-based (cross-platform) | Python 3.8+ | Better Windows support, safer process isolation |
| Manual polling with setInterval | HTMX `hx-trigger="every Ns"` | HTMX 1.8+ | Zero-JS solution, cleaner markup |
| Separate CLI for each service | Single `start` command | Modern CLI best practice | Better DX, simpler onboarding |

**Deprecated/outdated:**
- **`@app.on_event` decorators:** Replaced by `lifespan` parameter in FastAPI
- **Fork on macOS:** Changed to spawn default in Python 3.8 due to security issues
- **Gradio < 4.0:** Many breaking changes, ensure compatibility when mounting

## Open Questions

Things that couldn't be fully resolved:

1. **MLFlow embedded mode reliability**
   - What we know: MLFlow can be embedded via WSGIMiddleware, but some users report issues
   - What's unclear: Long-term stability of embedding vs subprocess approach
   - Recommendation: Implement graceful degradation, consider subprocess fallback

2. **Optimal refresh interval for status dashboard**
   - What we know: 5-10s is typical, depends on use case
   - What's unclear: User preference for this specific application
   - Recommendation: Start with 10s, make configurable via environment variable

3. **Session persistence across restarts**
   - What we know: In-memory state is lost on restart
   - What's unclear: Whether users expect workflow state to persist
   - Recommendation: Out of scope for Phase 5, defer to future phases

## Sources

### Primary (HIGH confidence)
- [FastAPI Lifespan Events - Official Documentation](https://fastapi.tiangolo.com/advanced/events/) - Startup/shutdown patterns
- [SQLAlchemy Metadata.create_all() - Official Docs](http://docs.sqlalchemy.org/en/latest/core/metadata.html) - Database initialization
- [Rich Progress Display - Official Docs](https://rich.readthedocs.io/en/latest/progress.html) - CLI spinners
- [HTMX Documentation - Polling](https://htmx.org/docs/) - Periodic refresh patterns

### Secondary (MEDIUM confidence)
- [Graceful exit with Python multiprocessing](https://the-fonz.gitlab.io/posts/python-multiprocessing/) - Process shutdown patterns
- [Robust Process Management in Python](https://medium.com/@RampantLions/robust-process-management-in-python-named-workers-messaging-queues-and-graceful-shutdown-cacfe2b8e7ca) - ProcessManager patterns
- [FastAPI Lifespan Explained (2025)](https://medium.com/algomart/fastapi-lifespan-explained-the-right-way-to-handle-startup-and-shutdown-logic-f825f38dd304) - Modern lifespan patterns
- [Building Web Polling with HTMX (2024)](https://hamy.xyz/blog/2024-07_htmx-polling-example) - HTMX polling examples
- [How to Build Simple Web Polling with HTMX](https://www.youtube.com/watch?v=-Yxv8uAUVho) - Video tutorial

### Tertiary (LOW confidence - verified issues, not implementation)
- [Gradio Issue #10590: RootPath bug from 4.21.0](https://github.com/gradio-app/gradio/issues/10590) - Known Gradio bug
- [Gradio Issue #4291: mount_gradio_app subpath issues](https://github.com/gradio-app/gradio/issues/4291) - Mounting Gradio challenges
- [Python Multiprocessing, Revisited: Fork vs Spawn](https://medium.com/@Nexumo_/python-multiprocessing-revisited-fork-vs-spawn-5b9216fd5710) - Windows compatibility

### Codebase References
- `C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents\src\configurable_agents\cli.py` - Existing CLI structure
- `C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents\src\configurable_agents\ui\dashboard\app.py` - Dashboard app
- `C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents\src\configurable_agents\storage\factory.py` - Storage factory (already has `create_all()`)
- `C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents\src\configurable_agents\storage\models.py` - SQLAlchemy models

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components are Python built-in or already installed
- Architecture: HIGH - Established patterns with official documentation
- Pitfalls: HIGH - Based on documented issues and verified bug reports

**Research date:** 2026-02-04
**Valid until:** 2026-03-06 (30 days - stack is stable, no major changes expected)

## Implementation Complexity Assessment

| Component | Complexity | Est. Lines | Risk |
|-----------|------------|------------|------|
| ProcessManager | Medium | ~150 | Medium - signal handling cross-platform |
| Auto-initialization | Low | ~50 | Low - using existing `create_all()` |
| CLI `start` command | Low | ~80 | Low - wraps existing commands |
| Status dashboard routes | Low | ~100 | Low - simple HTMX endpoints |
| Error formatting | Low | ~50 | Low - template-based |
| Graceful shutdown | Medium | ~100 | Medium - process cleanup |

**Total estimated:** ~530 lines of new code across ~6 files.

**Dependencies to add:** 0

**Key risks:**
1. Windows multiprocessing quirks (spawn vs fork) - mitigated by explicit start method
2. Gradio mounting issues if attempting unification - mitigated by separate process approach
3. Signal handling on Windows - mitigated by using `signal` module with fallbacks
