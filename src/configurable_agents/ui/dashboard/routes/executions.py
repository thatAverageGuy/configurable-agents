"""Execution monitoring routes with HTMX-powered real-time updates.

Provides endpoints for viewing workflow executions, status, and metrics
with dynamic updates via Server-Sent Events (SSE).

Renamed in UI Redesign (2026-02-13):
- workflows.py → executions.py
- WorkflowRunRecord → Execution
- AbstractWorkflowRunRepository → AbstractExecutionRepository
- Routes: /workflows/* → /executions/*
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
from configurable_agents.storage.base import AbstractExecutionRepository
from configurable_agents.storage.models import Execution


router = APIRouter(prefix="/executions")


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
        status: Execution status string

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


# Dependency to get execution repo from app state
async def _get_execution_repo(request: Request) -> AbstractExecutionRepository:
    """Get execution repository from app state."""
    return request.app.state.execution_repo


@router.get("/", response_class=HTMLResponse)
async def executions_list(
    request: Request,
    status_filter: Optional[str] = None,
    execution_repo: AbstractExecutionRepository = Depends(_get_execution_repo),
):
    """Render executions list page."""
    templates: Jinja2Templates = request.app.state.templates

    # Get all executions
    executions = _get_all_executions(execution_repo, limit=100)

    # Filter by status if specified
    if status_filter:
        executions = [e for e in executions if e.status == status_filter]

    return templates.TemplateResponse(
        "executions.html",
        {
            "request": request,
            "executions": executions,
            "status_filter": status_filter or "all",
        },
    )


@router.get("/table", response_class=HTMLResponse)
async def executions_table(
    request: Request,
    status_filter: Optional[str] = None,
    deployment: Optional[str] = None,
    execution_repo: AbstractExecutionRepository = Depends(_get_execution_repo),
):
    """Render executions table partial for HTMX refresh."""
    templates: Jinja2Templates = request.app.state.templates

    # Get all executions
    executions = _get_all_executions(execution_repo, limit=100)

    # Filter by status if specified
    if status_filter:
        executions = [e for e in executions if e.status == status_filter]

    # Filter by deployment if specified
    if deployment:
        # Filter by deployment_id
        executions = [e for e in executions if e.deployment_id == deployment]

    return templates.TemplateResponse(
        "executions_table.html",
        {
            "request": request,
            "executions": executions,
            "status_filter": status_filter or "all",
            "deployment_filter": deployment or "",
        },
    )


@router.get("/{execution_id}", response_class=HTMLResponse)
async def execution_detail(
    execution_id: str,
    request: Request,
    execution_repo: AbstractExecutionRepository = Depends(_get_execution_repo),
):
    """Render execution detail page."""
    templates: Jinja2Templates = request.app.state.templates

    # Get the execution
    execution = execution_repo.get(execution_id)

    if execution is None:
        return templates.TemplateResponse(
            "executions.html",
            {
                "request": request,
                "error": f"Execution not found: {execution_id}",
            },
        )

    # Parse outputs if available
    outputs = None
    if execution.outputs:
        try:
            outputs = json.loads(execution.outputs)
        except (json.JSONDecodeError, TypeError):
            outputs = {"raw": execution.outputs}

    # Parse bottleneck info if available
    bottleneck_info = None
    if execution.bottleneck_info:
        try:
            bottleneck_info = json.loads(execution.bottleneck_info)
        except (json.JSONDecodeError, TypeError):
            pass

    # Get state history if available
    state_repo = getattr(request.app.state, "state_repo", None)
    state_history = []
    if state_repo:
        try:
            state_history = state_repo.get_state_history(execution_id)
        except Exception:
            pass

    return templates.TemplateResponse(
        "execution_detail.html",
        {
            "request": request,
            "execution": execution,
            "outputs": outputs,
            "bottleneck_info": bottleneck_info,
            "state_history": state_history,
            "format_duration": _format_duration,
            "format_cost": _format_cost,
            "format_datetime": _format_datetime,
        },
    )


@router.post("/{execution_id}/cancel")
async def execution_cancel(
    execution_id: str,
    execution_repo: AbstractExecutionRepository = Depends(_get_execution_repo),
):
    """Cancel a running execution (best-effort)."""
    # Get the execution
    execution = execution_repo.get(execution_id)

    if execution is None:
        return Response(content="Execution not found", status_code=404)

    if execution.status != "running":
        return Response(
            content=f"Cannot cancel execution with status: {execution.status}",
            status_code=400,
        )

    # Update status to cancelled
    try:
        execution_repo.update_status(execution_id, "cancelled")
        return Response(content="Execution cancelled", status_code=200)
    except Exception as e:
        return Response(
            content=f"Failed to cancel execution: {e}",
            status_code=500,
        )


@router.post("/{execution_id}/restart")
async def execution_restart(
    execution_id: str,
    background_tasks: BackgroundTasks,
    execution_repo: AbstractExecutionRepository = Depends(_get_execution_repo),
):
    """Restart an execution with the same inputs.

    Extracts the original config from the execution record,
    creates a temporary config file, and re-executes the workflow
    using the original inputs.
    """
    # Get the original execution
    execution = execution_repo.get(execution_id)

    if execution is None:
        return JSONResponse(
            content={"error": "Execution not found"},
            status_code=404
        )

    # Cannot restart running executions
    if execution.status == "running":
        return JSONResponse(
            content={"error": "Cannot restart a running execution"},
            status_code=400
        )

    # Parse original inputs
    inputs: Dict[str, Any] = {}
    if execution.inputs:
        try:
            inputs = json.loads(execution.inputs)
        except (json.JSONDecodeError, TypeError):
            return JSONResponse(
                content={"error": "Failed to parse original inputs"},
                status_code=500
            )

    # Parse config snapshot
    if not execution.config_snapshot:
        return JSONResponse(
            content={"error": "No config snapshot available for this execution"},
            status_code=500
        )

    try:
        config_dict = json.loads(execution.config_snapshot)
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
                # Error is logged by run_workflow_async, execution record will show failed status
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
                "message": "Execution restart initiated",
                "original_execution_id": execution_id
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
            content={"error": f"Failed to restart execution: {e}"},
            status_code=500
        )


def _get_all_executions(repo: AbstractExecutionRepository, limit: int = 100) -> List[Execution]:
    """Get all executions from repository.

    Args:
        repo: Execution repository
        limit: Maximum number of executions to return

    Returns:
        List of Execution instances
    """
    # Try different methods based on repository implementation
    try:
        # For SQLite repository with engine access
        if hasattr(repo, 'engine'):
            engine = repo.engine
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
    if hasattr(repo, 'list_all'):
        try:
            return repo.list_all(limit=limit)
        except Exception:
            pass

    return []


# Backward-compatible function alias
_get_all_runs = _get_all_executions


# Export helper functions for use in templates
__all__ = [
    "router",
    "_format_duration",
    "_format_cost",
    "_format_datetime",
    "_format_datetime_relative",
    "_get_status_badge_class",
]
