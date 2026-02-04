"""Status dashboard routes for HTMX polling.

Provides periodic status updates for the dashboard showing
active workflows, agent health, recent errors, and system resources.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from configurable_agents.storage.base import (
    AbstractWorkflowRunRepository,
    AgentRegistryRepository,
)
from configurable_agents.storage.models import WorkflowRunRecord

router = APIRouter()

logger = logging.getLogger(__name__)

# Optional psutil for system resources
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - system resources will show 0%")


class StatusMetrics:
    """Container for status dashboard metrics."""

    active_workflows: int
    total_workflows: int
    agent_healthy: int
    agent_total: int
    recent_errors: List[Dict[str, str]]
    cpu_percent: float
    memory_percent: float

    def __init__(
        self,
        active_workflows: int = 0,
        total_workflows: int = 0,
        agent_healthy: int = 0,
        agent_total: int = 0,
        recent_errors: Optional[List[Dict[str, str]]] = None,
        cpu_percent: float = 0.0,
        memory_percent: float = 0.0,
    ):
        self.active_workflows = active_workflows
        self.total_workflows = total_workflows
        self.agent_healthy = agent_healthy
        self.agent_total = agent_total
        self.recent_errors = recent_errors or []
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent


async def get_active_workflow_count(repo: AbstractWorkflowRunRepository) -> Tuple[int, int]:
    """Get count of active and total workflows.

    Args:
        repo: Workflow run repository

    Returns:
        Tuple of (active_count, total_count)
    """
    try:
        # Try to get all runs
        if hasattr(repo, 'engine'):
            with Session(repo.engine) as session:
                total_stmt = select(WorkflowRunRecord)
                active_stmt = select(WorkflowRunRecord).where(
                    WorkflowRunRecord.status == "running"
                )

                total_count = len(list(session.scalars(total_stmt).all()))
                active_count = len(list(session.scalars(active_stmt).all()))

                return active_count, total_count
        else:
            # Fallback: try list_all method
            runs = repo.list_all(limit=1000)
            active_count = sum(1 for r in runs if r.status == "running")
            return active_count, len(runs)
    except Exception as e:
        logger.warning(f"Failed to get workflow count: {e}")
        return 0, 0


async def get_agent_health_status(repo: AgentRegistryRepository) -> Tuple[int, int]:
    """Get agent health status.

    Args:
        repo: Agent registry repository

    Returns:
        Tuple of (healthy_count, total_count)
    """
    try:
        agents = repo.list_all(include_dead=False)
        healthy_count = sum(1 for a in agents if a.is_alive())
        return healthy_count, len(agents)
    except Exception as e:
        logger.warning(f"Failed to get agent health: {e}")
        return 0, 0


async def get_recent_errors(
    repo: AbstractWorkflowRunRepository,
    count: int = 5,
) -> List[Dict[str, str]]:
    """Get recent workflow errors.

    Args:
        repo: Workflow run repository
        count: Maximum number of errors to return

    Returns:
        List of error dictionaries with message and timestamp
    """
    try:
        if hasattr(repo, 'engine'):
            with Session(repo.engine) as session:
                cutoff = datetime.utcnow() - timedelta(hours=24)
                stmt = (
                    select(WorkflowRunRecord)
                    .where(
                        WorkflowRunRecord.status == "failed",
                        WorkflowRunRecord.started_at >= cutoff
                    )
                    .order_by(desc(WorkflowRunRecord.started_at))
                    .limit(count)
                )

                failed_runs = list(session.scalars(stmt).all())

                return [
                    {
                        "message": run.error_message or "Unknown error",
                        "workflow": run.workflow_name,
                        "timestamp": run.started_at.strftime("%H:%M") if run.started_at else "??:??",
                    }
                    for run in failed_runs
                ]
        return []
    except Exception as e:
        logger.warning(f"Failed to get recent errors: {e}")
        return []


async def get_system_resources() -> Tuple[float, float]:
    """Get current system resource usage.

    Returns:
        Tuple of (cpu_percent, memory_percent)
    """
    if not PSUTIL_AVAILABLE:
        return 0.0, 0.0
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory().percent
        return cpu, memory
    except Exception as e:
        logger.warning(f"Failed to get system resources: {e}")
        return 0.0, 0.0


@router.get("/api/status", response_class=HTMLResponse)
async def status_dashboard(request: Request):
    """Return status dashboard HTML fragment for HTMX polling.

    This endpoint returns an HTML fragment that replaces the status
    panel on the dashboard via HTMX's hx-swap="outerHTML".

    The fragment auto-refreshes every 10 seconds via hx-trigger.
    """
    # Get repositories from app state
    workflow_repo: AbstractWorkflowRunRepository = request.app.state.workflow_repo
    agent_repo: AgentRegistryRepository = request.app.state.agent_registry_repo
    templates = request.app.state.templates

    # Gather metrics
    active_workflows, total_workflows = await get_active_workflow_count(workflow_repo)
    agent_healthy, agent_total = await get_agent_health_status(agent_repo)
    recent_errors = await get_recent_errors(workflow_repo, count=5)
    cpu_percent, memory_percent = await get_system_resources()

    # Render status panel fragment
    return templates.TemplateResponse(
        "partials/status_panel.html",
        {
            "request": request,
            "active_workflows": active_workflows,
            "total_workflows": total_workflows,
            "agent_healthy": agent_healthy,
            "agent_total": agent_total,
            "recent_errors": recent_errors,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
        },
    )


@router.get("/api/status/health")
async def health_check(request: Request):
    """Simple health check endpoint.

    Returns JSON with overall system health status.
    """
    workflow_repo: AbstractWorkflowRunRepository = request.app.state.workflow_repo
    agent_repo: AgentRegistryRepository = request.app.state.agent_registry_repo

    active_workflows, _ = await get_active_workflow_count(workflow_repo)
    agent_healthy, _ = await get_agent_health_status(agent_repo)

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_workflows": active_workflows,
        "healthy_agents": agent_healthy,
    }
