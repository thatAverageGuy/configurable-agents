"""FastAPI dashboard application for execution and deployment monitoring.

Provides a unified web interface with HTMX-powered real-time updates,
MLFlow UI embedding, and comprehensive system observability.

Updated in UI Redesign (2026-02-13):
- WorkflowRunRecord → Execution
- AgentRecord → Deployment
- workflow_repo → execution_repo
- agent_registry_repo → deployment_repo
- Routes: /workflows/* → /executions/*, /agents/* → /deployments/*
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Engine, Select, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from configurable_agents.storage.base import (
    AbstractExecutionRepository,
    AbstractExecutionStateRepository,
    DeploymentRepository,
)
from configurable_agents.storage.models import Execution, Deployment


class DashboardApp:
    """FastAPI dashboard application for orchestration monitoring.

    Provides real-time views of executions, deployments, and metrics with
    HTMX-powered dynamic updates and embedded MLFlow UI.

    Attributes:
        app: The FastAPI application instance
        execution_repo: Repository for execution data
        state_repo: Repository for execution state data
        deployment_repo: Repository for deployment registry data
        templates: Jinja2 templates instance
    """

    def __init__(
        self,
        execution_repo: AbstractExecutionRepository,
        state_repo: Optional[AbstractExecutionStateRepository],
        deployment_repo: DeploymentRepository,
        mlflow_tracking_uri: Optional[str] = None,
        template_dir: Optional[Path] = None,
        static_dir: Optional[Path] = None,
    ):
        """Initialize the dashboard application.

        Args:
            execution_repo: Repository for execution persistence
            state_repo: Repository for execution state persistence (optional)
            deployment_repo: Repository for deployment registry persistence
            mlflow_tracking_uri: Optional MLFlow tracking URI for UI embedding
            template_dir: Custom templates directory (default: built-in templates)
            static_dir: Custom static files directory (default: built-in static)
        """
        self.execution_repo = execution_repo
        self.state_repo = state_repo
        self.deployment_repo = deployment_repo
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.mlflow_mounted = False

        # Create FastAPI app
        self.app = FastAPI(
            title="Configurable Agents Dashboard",
            description="Real-time execution and deployment monitoring",
            version="0.2.0",
        )

        # Setup templates and static files
        self._setup_templates(template_dir)
        self._setup_static_files(static_dir)

        # Mount MLFlow only if URI is a file path (embedded mode)
        # For HTTP URIs (external servers), don't mount - just link to them
        if mlflow_tracking_uri and not mlflow_tracking_uri.startswith("http"):
            self._mount_mlflow(mlflow_tracking_uri)
            self.mlflow_mounted = True

        # Store repositories in app state for route access
        self.app.state.execution_repo = execution_repo
        self.app.state.workflow_repo = execution_repo  # Backward-compatible alias
        self.app.state.workflow_run_repo = execution_repo  # Backward-compatible alias
        self.app.state.state_repo = state_repo
        self.app.state.deployment_repo = deployment_repo
        self.app.state.agent_registry_repo = deployment_repo  # Backward-compatible alias
        self.app.state.templates = self.templates
        self.app.state.mlflow_tracking_uri = mlflow_tracking_uri

        # Register startup event for deployment health checks
        @self.app.on_event("startup")
        async def startup_event():
            """Run tasks on dashboard startup."""
            logger = logging.getLogger(__name__)
            logger.info("Dashboard startup: Checking registered deployments")
            try:
                deployments = deployment_repo.list_all(include_dead=True)
                logger.info(f"Found {len(deployments)} deployments in registry")
            except Exception as e:
                logger.warning(f"Failed to list deployments on startup: {e}")

        # Include routers
        self._include_routers()

        # Register actual helper implementations after routers are loaded
        self._register_template_helpers()

        # Create main routes
        self._create_main_dashboard_routes()

        # Add middleware for request context
        @self.app.middleware("http")
        async def add_request_context(request: Request, call_next):
            """Add common context to all requests."""
            response = await call_next(request)
            return response

    def _include_routers(self) -> None:
        """Include dashboard routers."""
        from configurable_agents.ui.dashboard.routes import (
            executions_router,
            deployments_router,
            metrics_router,
        )
        from configurable_agents.ui.dashboard.routes import status as status_routes

        self.app.include_router(executions_router)
        self.app.include_router(deployments_router)
        self.app.include_router(metrics_router)
        self.app.include_router(status_routes.router)

    def _register_template_helpers(self) -> None:
        """Register actual helper function implementations for templates.

        This is called after router loading so we can import the helper
        functions from the route modules.
        """
        from configurable_agents.ui.dashboard.routes.executions import (
            _format_duration as fmt_dur_impl,
            _format_cost as fmt_cost_impl,
        )
        from configurable_agents.ui.dashboard.routes.deployments import (
            time_ago as time_ago_impl,
            parse_capabilities as parse_caps_impl,
        )

        self.templates.env.globals.update({
            "format_duration": fmt_dur_impl,
            "format_cost": fmt_cost_impl,
            "time_ago": time_ago_impl,
            "parse_capabilities": parse_caps_impl,
        })

    def _setup_templates(self, template_dir: Optional[Path] = None) -> None:
        """Configure Jinja2 templates.

        Args:
            template_dir: Custom templates directory path
        """
        if template_dir is None:
            # Use built-in templates directory
            template_dir = Path(__file__).parent / "templates"

        self.template_dir = Path(template_dir)
        self.templates = Jinja2Templates(directory=str(self.template_dir))

        # Add custom filters for templates
        self.templates.env.filters["to_json"] = json.dumps
        self.templates.env.filters["from_json"] = json.loads

        # Add stub helper functions to template globals
        # These will be replaced with actual implementations after router loading
        self.templates.env.globals.update({
            "format_duration": lambda s: "-",
            "format_cost": lambda c: "$0.00",
            "time_ago": lambda dt: "-",
            "parse_capabilities": lambda m: [],
        })

    def _setup_static_files(self, static_dir: Optional[Path] = None) -> None:
        """Configure static file serving.

        Args:
            static_dir: Custom static files directory path
        """
        if static_dir is None:
            # Use built-in static directory
            static_dir = Path(__file__).parent / "static"

        self.static_dir = Path(static_dir)

        # Create static directory if it doesn't exist
        self.static_dir.mkdir(parents=True, exist_ok=True)

        # Mount static files
        self.app.mount("/static", StaticFiles(directory=str(self.static_dir)), name="static")

    def _mount_mlflow(self, mlflow_tracking_uri: str) -> None:
        """Mount MLFlow WSGI application at /mlflow.

        Args:
            mlflow_tracking_uri: MLFlow tracking URI
        """
        try:
            from mlflow.server.app import create_app
            from fastapi.middleware.wsgi import WSGIMiddleware

            # Create MLFlow app
            mlflow_app = create_app(
                backend_store_uri=mlflow_tracking_uri,
                default_artifact_root=mlflow_tracking_uri.replace("file://", "") + "/artifacts",
            )

            # Mount at /mlflow
            self.app.mount("/mlflow", WSGIMiddleware(mlflow_app))
            self.mlflow_mounted = True
        except ImportError:
            # MLFlow not available - skip mounting
            self.mlflow_mounted = False
        except Exception as e:
            # Log error but don't fail dashboard startup
            logging.getLogger(__name__).warning(f"Failed to mount MLFlow: {e}")
            self.mlflow_mounted = False

    def _create_main_dashboard_routes(self) -> None:
        """Create main dashboard routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """Render main dashboard page."""
            # Get summary statistics for status panel
            try:
                all_executions = self._get_all_executions()
                total_executions = len(all_executions)
                active_executions = sum(1 for e in all_executions if e.status == "running")
            except Exception:
                total_executions = 0
                active_executions = 0

            try:
                all_deployments = self.deployment_repo.list_all(include_dead=False)
                deployment_total = len(all_deployments)
                deployment_healthy = sum(1 for d in all_deployments if d.is_alive())
            except Exception:
                deployment_total = 0
                deployment_healthy = 0

            return self.templates.TemplateResponse(
                "dashboard.html",
                {
                    "request": request,
                    # For initial status panel render
                    "active_executions": active_executions,
                    "total_executions": total_executions,
                    "deployment_healthy": deployment_healthy,
                    "deployment_total": deployment_total,
                    # Backward-compatible aliases
                    "active_workflows": active_executions,
                    "total_workflows": total_executions,
                    "agent_healthy": deployment_healthy,
                    "agent_total": deployment_total,
                    "recent_errors": [],
                    "cpu_percent": 0,
                    "memory_percent": 0,
                    "now": datetime.utcnow(),
                },
            )

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

        @self.app.get("/mlflow", response_class=HTMLResponse)
        async def mlflow_handler(request: Request):
            """Handle MLFlow route - redirect to external or show unavailable page."""
            # If MLFlow is an external HTTP server, redirect to it
            if self.mlflow_tracking_uri and self.mlflow_tracking_uri.startswith("http"):
                return RedirectResponse(url=self.mlflow_tracking_uri)

            # Otherwise show unavailable page
            return self.templates.TemplateResponse(
                "mlflow_unavailable.html",
                {"request": request}
            )

    def _get_all_executions(self, limit: int = 100) -> List[Execution]:
        """Get all executions from repository.

        Args:
            limit: Maximum number of executions to return

        Returns:
            List of Execution instances
        """
        # Try different methods based on repository implementation
        try:
            # For SQLite repository with engine access
            if hasattr(self.execution_repo, 'engine'):
                engine = self.execution_repo.engine
                with Session(engine) as session:
                    stmt: Select[Execution] = (
                        select(Execution)
                        .order_by(Execution.started_at.desc())
                        .limit(limit)
                    )
                    return list(session.scalars(stmt).all())
        except Exception:
            pass

        # Fall back to trying list_all if it exists
        if hasattr(self.execution_repo, 'list_all'):
            try:
                return self.execution_repo.list_all(limit=limit)
            except Exception:
                pass

        return []

    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance.

        Returns:
            FastAPI application instance for mounting
        """
        return self.app


def create_dashboard_app(
    db_url: str = "sqlite:///configurable_agents.db",
    mlflow_tracking_uri: Optional[str] = None,
) -> DashboardApp:
    """Create and configure a dashboard application.

    Factory function for creating a pre-configured DashboardApp instance
    with storage backends initialized from the database URL.

    Args:
        db_url: Database URL for storage backend (default: SQLite)
        mlflow_tracking_uri: Optional MLFlow tracking URI for UI embedding

    Returns:
        Configured DashboardApp instance

    Example:
        >>> app = create_dashboard_app(
        ...     db_url="sqlite:///configurable_agents.db",
        ...     mlflow_tracking_uri="sqlite:///mlflow.db"
        ... )
        >>> import uvicorn
        >>> uvicorn.run(app.get_app(), host="0.0.0.0", port=7861)
    """
    from configurable_agents.storage import ensure_initialized
    from configurable_agents.storage.sqlite import (
        SQLiteExecutionRepository,
        SQLiteExecutionStateRepository,
        SqliteDeploymentRepository,
    )

    # Auto-initialize database
    try:
        ensure_initialized(db_url, show_progress=False)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Database auto-init failed: {e}")

    # Create database engine
    engine = create_engine(db_url, connect_args={"check_same_thread": False})

    # Create repositories
    execution_repo = SQLiteExecutionRepository(engine)
    state_repo = SQLiteExecutionStateRepository(engine)
    deployment_repo = SqliteDeploymentRepository(engine)

    return DashboardApp(
        execution_repo=execution_repo,
        state_repo=state_repo,
        deployment_repo=deployment_repo,
        mlflow_tracking_uri=mlflow_tracking_uri,
    )
