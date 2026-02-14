"""Status dashboard routes for HTMX polling.

Provides periodic status updates for the dashboard showing
active executions, deployment health, recent errors, and system resources.

Updated in UI Redesign (2026-02-13):
- WorkflowRunRecord → Execution
- AbstractWorkflowRunRepository → AbstractExecutionRepository
- AgentRegistryRepository → DeploymentRepository
- Variable names: workflow → execution, agent → deployment
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from configurable_agents.storage.base import (
    AbstractExecutionRepository,
    DeploymentRepository,
)
from configurable_agents.storage.models import Execution

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

    active_executions: int
    total_executions: int
    deployment_healthy: int
    deployment_total: int
    recent_errors: List[Dict[str, str]]
    cpu_percent: float
    memory_percent: float

    def __init__(
        self,
        active_executions: int = 0,
        total_executions: int = 0,
        deployment_healthy: int = 0,
        deployment_total: int = 0,
        recent_errors: Optional[List[Dict[str, str]]] = None,
        cpu_percent: float = 0.0,
        memory_percent: float = 0.0,
    ):
        self.active_executions = active_executions
        self.total_executions = total_executions
        self.deployment_healthy = deployment_healthy
        self.deployment_total = deployment_total
        self.recent_errors = recent_errors or []
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent


async def get_active_execution_count(repo: AbstractExecutionRepository) -> Tuple[int, int]:
    """Get count of active and total executions.

    Args:
        repo: Execution repository

    Returns:
        Tuple of (active_count, total_count)
    """
    try:
        # Try to get all executions
        if hasattr(repo, 'engine'):
            with Session(repo.engine) as session:
                total_stmt = select(Execution)
                active_stmt = select(Execution).where(
                    Execution.status == "running"
                )

                total_count = len(list(session.scalars(total_stmt).all()))
                active_count = len(list(session.scalars(active_stmt).all()))

                return active_count, total_count
        else:
            # Fallback: try list_all method
            executions = repo.list_all(limit=1000)
            active_count = sum(1 for e in executions if e.status == "running")
            return active_count, len(executions)
    except Exception as e:
        logger.warning(f"Failed to get execution count: {e}")
        return 0, 0


async def get_deployment_health_status(repo: DeploymentRepository) -> Tuple[int, int]:
    """Get deployment health status.

    Args:
        repo: Deployment repository

    Returns:
        Tuple of (healthy_count, total_count)
    """
    try:
        deployments = repo.list_all(include_dead=False)
        healthy_count = sum(1 for d in deployments if d.is_alive())
        return healthy_count, len(deployments)
    except Exception as e:
        logger.warning(f"Failed to get deployment health: {e}")
        return 0, 0


async def get_recent_errors(
    repo: AbstractExecutionRepository,
    count: int = 5,
) -> List[Dict[str, str]]:
    """Get recent execution errors.

    Args:
        repo: Execution repository
        count: Maximum number of errors to return

    Returns:
        List of error dictionaries with message and timestamp
    """
    try:
        if hasattr(repo, 'engine'):
            with Session(repo.engine) as session:
                cutoff = datetime.utcnow() - timedelta(hours=24)
                stmt = (
                    select(Execution)
                    .where(
                        Execution.status == "failed",
                        Execution.started_at >= cutoff
                    )
                    .order_by(desc(Execution.started_at))
                    .limit(count)
                )

                failed_executions = list(session.scalars(stmt).all())

                return [
                    {
                        "message": execution.error_message or "Unknown error",
                        "workflow": execution.workflow_name,
                        "timestamp": execution.started_at.strftime("%H:%M") if execution.started_at else "??:??",
                    }
                    for execution in failed_executions
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
    execution_repo: AbstractExecutionRepository = request.app.state.execution_repo
    deployment_repo: DeploymentRepository = request.app.state.deployment_repo
    templates = request.app.state.templates

    # Gather metrics
    active_executions, total_executions = await get_active_execution_count(execution_repo)
    deployment_healthy, deployment_total = await get_deployment_health_status(deployment_repo)
    recent_errors = await get_recent_errors(execution_repo, count=5)
    cpu_percent, memory_percent = await get_system_resources()

    # Render status panel fragment
    return templates.TemplateResponse(
        "partials/status_panel.html",
        {
            "request": request,
            "active_executions": active_executions,
            "total_executions": total_executions,
            "deployment_healthy": deployment_healthy,
            "deployment_total": deployment_total,
            "recent_errors": recent_errors,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "now": datetime.utcnow(),
        },
    )


@router.get("/api/status/health")
async def health_check(request: Request):
    """Simple health check endpoint.

    Returns JSON with overall system health status.
    """
    execution_repo: AbstractExecutionRepository = request.app.state.execution_repo
    deployment_repo: DeploymentRepository = request.app.state.deployment_repo

    active_executions, _ = await get_active_execution_count(execution_repo)
    deployment_healthy, _ = await get_deployment_health_status(deployment_repo)

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_executions": active_executions,
        "healthy_deployments": deployment_healthy,
    }
