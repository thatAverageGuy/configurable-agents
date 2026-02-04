"""FastAPI dashboard application for workflow and agent monitoring.

Provides a unified web interface with HTMX-powered real-time updates,
MLFlow UI embedding, and comprehensive system observability.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Engine, Select, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from configurable_agents.storage.base import (
    AbstractWorkflowRunRepository,
    AgentRegistryRepository,
)
from configurable_agents.storage.models import WorkflowRunRecord, AgentRecord


class DashboardApp:
    """FastAPI dashboard application for orchestration monitoring.

    Provides real-time views of workflows, agents, and metrics with
    HTMX-powered dynamic updates and embedded MLFlow UI.

    Attributes:
        app: The FastAPI application instance
        workflow_repo: Repository for workflow run data
        agent_registry_repo: Repository for agent registry data
        templates: Jinja2 templates instance
    """

    def __init__(
        self,
        workflow_repo: AbstractWorkflowRunRepository,
        agent_registry_repo: AgentRegistryRepository,
        mlflow_tracking_uri: Optional[str] = None,
        template_dir: Optional[Path] = None,
        static_dir: Optional[Path] = None,
    ):
        """Initialize the dashboard application.

        Args:
            workflow_repo: Repository for workflow run persistence
            agent_registry_repo: Repository for agent registry persistence
            mlflow_tracking_uri: Optional MLFlow tracking URI for UI embedding
            template_dir: Custom templates directory (default: built-in templates)
            static_dir: Custom static files directory (default: built-in static)
        """
        self.workflow_repo = workflow_repo
        self.agent_registry_repo = agent_registry_repo
        self.mlflow_tracking_uri = mlflow_tracking_uri

        # Create FastAPI app
        self.app = FastAPI(
            title="Configurable Agents Dashboard",
            description="Real-time workflow and agent monitoring",
            version="0.1.0",
        )

        # Setup templates and static files
        self._setup_templates(template_dir)
        self._setup_static_files(static_dir)

        # Mount MLFlow if URI provided
        if mlflow_tracking_uri:
            self._mount_mlflow(mlflow_tracking_uri)

        # Store repositories in app state for route access
        self.app.state.workflow_repo = workflow_repo
        self.app.state.agent_registry_repo = agent_registry_repo
        self.app.state.templates = self.templates

        # Include routers
        self._include_routers()

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
            workflows_router,
            agents_router,
            metrics_router,
            optimization_router,
            orchestrator_router,
        )

        self.app.include_router(workflows_router)
        self.app.include_router(agents_router)
        self.app.include_router(metrics_router)
        self.app.include_router(optimization_router)
        self.app.include_router(orchestrator_router)

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
        except ImportError:
            # MLFlow not available - skip mounting
            pass
        except Exception as e:
            # Log error but don't fail dashboard startup
            import logging
            logging.getLogger(__name__).warning(f"Failed to mount MLFlow: {e}")

    def _create_main_dashboard_routes(self) -> None:
        """Create main dashboard routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """Render main dashboard page."""
            # Get summary statistics
            try:
                all_runs = self._get_all_runs()
                total_workflows = len(all_runs)
                running_workflows = sum(1 for r in all_runs if r.status == "running")
                total_cost = sum(r.total_cost_usd or 0 for r in all_runs)
            except Exception:
                total_workflows = 0
                running_workflows = 0
                total_cost = 0.0

            try:
                all_agents = self.agent_registry_repo.list_all(include_dead=False)
                registered_agents = len(all_agents)
            except Exception:
                registered_agents = 0

            return self.templates.TemplateResponse(
                "dashboard.html",
                {
                    "request": request,
                    "total_workflows": total_workflows,
                    "running_workflows": running_workflows,
                    "registered_agents": registered_agents,
                    "total_cost": total_cost,
                },
            )

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    def _get_all_runs(self, limit: int = 100) -> List[WorkflowRunRecord]:
        """Get all workflow runs from repository.

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of WorkflowRunRecord instances
        """
        # Try different methods based on repository implementation
        try:
            # For SQLite repository with engine access
            if hasattr(self.workflow_repo, 'engine'):
                engine = self.workflow_repo.engine
                with Session(engine) as session:
                    stmt: Select[WorkflowRunRecord] = (
                        select(WorkflowRunRecord)
                        .order_by(WorkflowRunRecord.started_at.desc())
                        .limit(limit)
                    )
                    return list(session.scalars(stmt).all())
        except Exception:
            pass

        # Fall back to trying list_all if it exists
        if hasattr(self.workflow_repo, 'list_all'):
            try:
                return self.workflow_repo.list_all(limit=limit)
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
        ...     db_url="sqlite:///agents.db",
        ...     mlflow_tracking_uri="file://./mlruns"
        ... )
        >>> import uvicorn
        >>> uvicorn.run(app.get_app(), host="0.0.0.0", port=7861)
    """
    from configurable_agents.storage.sqlite import (
        SQLiteWorkflowRunRepository,
        SqliteAgentRegistryRepository,
    )

    # Create database engine
    engine = create_engine(db_url, connect_args={"check_same_thread": False})

    # Create repositories
    workflow_repo = SQLiteWorkflowRunRepository(engine)
    agent_repo = SqliteAgentRegistryRepository(engine)

    return DashboardApp(
        workflow_repo=workflow_repo,
        agent_registry_repo=agent_repo,
        mlflow_tracking_uri=mlflow_tracking_uri,
    )
