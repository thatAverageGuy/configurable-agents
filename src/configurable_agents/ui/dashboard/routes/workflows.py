"""Workflow monitoring routes with HTMX-powered real-time updates.

Provides endpoints for viewing workflow runs, status, and metrics
with dynamic updates via Server-Sent Events (SSE).
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, BackgroundTasks, Request, Response, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Select, create_engine, select
from sqlalchemy.orm import Session

from configurable_agents.runtime.executor import run_workflow_async
from configurable_agents.storage.base import AbstractWorkflowRunRepository
from configurable_agents.storage.models import WorkflowRunRecord


router = APIRouter(prefix="/workflows")


def _format_duration(seconds: Optional[float]) -> str:
    """Format duration in seconds as human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "2m 30s", "45s", "< 1s")
    """
    if seconds is None or seconds < 0:
        return "-"

    if seconds < 1:
        return "< 1s"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _format_cost(usd: Optional[float]) -> str:
    """Format cost in USD as string.

    Args:
        usd: Cost in USD

    Returns:
        Formatted cost string (e.g., "$0.0123")
    """
    if usd is None:
        return "$0.00"
    return f"${usd:.4f}"


def _format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime as string.

    Args:
        dt: DateTime object

    Returns:
        Formatted datetime string (e.g., "2024-01-15 14:30:00")
    """
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _format_datetime_relative(dt: Optional[datetime]) -> str:
    """Format datetime as relative time string.

    Args:
        dt: DateTime object

    Returns:
        Relative time string (e.g., "2 hours ago", "just now")
    """
    if dt is None:
        return "-"

    now = datetime.utcnow()
    delta = now - dt

    seconds = delta.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"


def _get_status_badge_class(status: str) -> str:
    """Get CSS class for status badge.

    Args:
        status: Workflow status string

    Returns:
        CSS class name for the badge
    """
    status_lower = status.lower() if status else ""
    status_map = {
        "running": "badge-running",
        "completed": "badge-completed",
        "failed": "badge-failed",
        "pending": "badge-pending",
        "cancelled": "badge-cancelled",
    }
    return status_map.get(status_lower, "badge-pending")


# Dependency to get workflow repo from app state
async def _get_workflow_repo(request: Request) -> AbstractWorkflowRunRepository:
    """Get workflow repository from app state."""
    return request.app.state.workflow_repo


@router.get("/", response_class=HTMLResponse)
async def workflows_list(
    request: Request,
    status_filter: Optional[str] = None,
    workflow_repo: AbstractWorkflowRunRepository = Depends(_get_workflow_repo),
):
    """Render workflows list page."""
    templates: Jinja2Templates = request.app.state.templates

    # Get all runs
    runs = _get_all_runs(workflow_repo, limit=100)

    # Filter by status if specified
    if status_filter:
        runs = [r for r in runs if r.status == status_filter]

    return templates.TemplateResponse(
        "workflows.html",
        {
            "request": request,
            "workflows": runs,
            "status_filter": status_filter or "all",
        },
    )


@router.get("/table", response_class=HTMLResponse)
async def workflows_table(
    request: Request,
    status_filter: Optional[str] = None,
    workflow_repo: AbstractWorkflowRunRepository = Depends(_get_workflow_repo),
):
    """Render workflows table partial for HTMX refresh."""
    templates: Jinja2Templates = request.app.state.templates

    # Get all runs
    runs = _get_all_runs(workflow_repo, limit=100)

    # Filter by status if specified
    if status_filter:
        runs = [r for r in runs if r.status == status_filter]

    return templates.TemplateResponse(
        "workflows_table.html",
        {
            "request": request,
            "workflows": runs,
            "status_filter": status_filter or "all",
        },
    )


@router.get("/{run_id}", response_class=HTMLResponse)
async def workflow_detail(
    run_id: str,
    request: Request,
    workflow_repo: AbstractWorkflowRunRepository = Depends(_get_workflow_repo),
):
    """Render workflow detail page."""
    templates: Jinja2Templates = request.app.state.templates

    # Get the run
    run = workflow_repo.get(run_id)

    if run is None:
        return templates.TemplateResponse(
            "workflows.html",
            {
                "request": request,
                "error": f"Workflow run not found: {run_id}",
            },
        )

    # Parse outputs if available
    outputs = None
    if run.outputs:
        try:
            outputs = json.loads(run.outputs)
        except (json.JSONDecodeError, TypeError):
            outputs = {"raw": run.outputs}

    # Parse bottleneck info if available
    bottleneck_info = None
    if run.bottleneck_info:
        try:
            bottleneck_info = json.loads(run.bottleneck_info)
        except (json.JSONDecodeError, TypeError):
            pass

    # Get state history if available
    state_repo = getattr(request.app.state, "state_repo", None)
    state_history = []
    if state_repo:
        try:
            state_history = state_repo.get_state_history(run_id)
        except Exception:
            pass

    return templates.TemplateResponse(
        "workflow_detail.html",
        {
            "request": request,
            "workflow": run,
            "outputs": outputs,
            "bottleneck_info": bottleneck_info,
            "state_history": state_history,
            "format_duration": _format_duration,
            "format_cost": _format_cost,
            "format_datetime": _format_datetime,
        },
    )


@router.post("/{run_id}/cancel")
async def workflow_cancel(
    run_id: str,
    workflow_repo: AbstractWorkflowRunRepository = Depends(_get_workflow_repo),
):
    """Cancel a running workflow (best-effort)."""
    # Get the run
    run = workflow_repo.get(run_id)

    if run is None:
        return Response(content="Workflow run not found", status_code=404)

    if run.status != "running":
        return Response(
            content=f"Cannot cancel workflow with status: {run.status}",
            status_code=400,
        )

    # Update status to cancelled
    try:
        workflow_repo.update_status(run_id, "cancelled")
        return Response(content="Workflow cancelled", status_code=200)
    except Exception as e:
        return Response(
            content=f"Failed to cancel workflow: {e}",
            status_code=500,
        )


@router.post("/{run_id}/restart")
async def workflow_restart(
    run_id: str,
    background_tasks: BackgroundTasks,
    workflow_repo: AbstractWorkflowRunRepository = Depends(_get_workflow_repo),
):
    """Restart a workflow with the same inputs.

    Extracts the original config from the workflow run record,
    creates a temporary config file, and re-executes the workflow
    using the original inputs.
    """
    # Get the original run
    run = workflow_repo.get(run_id)

    if run is None:
        return JSONResponse(
            content={"error": "Workflow run not found"},
            status_code=404
        )

    # Cannot restart running workflows
    if run.status == "running":
        return JSONResponse(
            content={"error": "Cannot restart a running workflow"},
            status_code=400
        )

    # Parse original inputs
    inputs: Dict[str, Any] = {}
    if run.inputs:
        try:
            inputs = json.loads(run.inputs)
        except (json.JSONDecodeError, TypeError):
            return JSONResponse(
                content={"error": "Failed to parse original inputs"},
                status_code=500
            )

    # Parse config snapshot
    if not run.config_snapshot:
        return JSONResponse(
            content={"error": "No config snapshot available for this run"},
            status_code=500
        )

    try:
        config_dict = json.loads(run.config_snapshot)
    except (json.JSONDecodeError, TypeError) as e:
        return JSONResponse(
            content={"error": f"Failed to parse config snapshot: {e}"},
            status_code=500
        )

    # Create temporary config file
    temp_config_path = None
    try:
        # Create a temporary YAML file with the config
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        ) as temp_file:
            temp_config_path = temp_file.name
            yaml.dump(config_dict, temp_file)

        # Execute workflow in background
        async def _run_restart_workflow() -> None:
            """Execute workflow and clean up temp file."""
            try:
                await run_workflow_async(temp_config_path, inputs)
            except Exception as e:
                # Error is logged by run_workflow_async, workflow record will show failed status
                pass
            finally:
                # Clean up temporary config file
                try:
                    os.unlink(temp_config_path)
                except Exception:
                    pass

        # Schedule background execution
        background_tasks.add_task(_run_restart_workflow)

        return JSONResponse(
            content={
                "status": "restarted",
                "message": "Workflow restart initiated",
                "original_run_id": run_id
            },
            status_code=200
        )

    except Exception as e:
        # Clean up temp file if something went wrong
        if temp_config_path and os.path.exists(temp_config_path):
            try:
                os.unlink(temp_config_path)
            except Exception:
                pass

        return JSONResponse(
            content={"error": f"Failed to restart workflow: {e}"},
            status_code=500
        )


def _get_all_runs(repo: AbstractWorkflowRunRepository, limit: int = 100) -> List[WorkflowRunRecord]:
    """Get all workflow runs from repository.

    Args:
        repo: Workflow repository
        limit: Maximum number of runs to return

    Returns:
        List of WorkflowRunRecord instances
    """
    # Try different methods based on repository implementation
    try:
        # For SQLite repository with engine access
        if hasattr(repo, 'engine'):
            engine = repo.engine
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
    if hasattr(repo, 'list_all'):
        try:
            return repo.list_all(limit=limit)
        except Exception:
            pass

    return []


# Export helper functions for use in templates
__all__ = [
    "router",
    "_format_duration",
    "_format_cost",
    "_format_datetime",
    "_format_datetime_relative",
    "_get_status_badge_class",
]
