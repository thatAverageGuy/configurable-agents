"""Server-Sent Events (SSE) endpoints for real-time metrics streaming.

Provides SSE endpoints for execution and deployment updates that
push data to connected clients for dynamic dashboard updates.

Updated in UI Redesign (2026-02-13):
- WorkflowRunRecord → Execution
- AgentRecord → Deployment
- AbstractWorkflowRunRepository → AbstractExecutionRepository
- AgentRegistryRepository → DeploymentRepository
- Routes: /workflows/* → /executions/*, /agents/* → /deployments/*
"""

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from configurable_agents.storage.base import (
    AbstractExecutionRepository,
    DeploymentRepository,
)
from configurable_agents.storage.models import Execution, Deployment


router = APIRouter(prefix="/metrics")


async def _execution_event_stream(
    execution_repo: AbstractExecutionRepository,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for execution updates.

    Args:
        execution_repo: Execution repository for querying executions

    Yields:
        SSE-formatted event strings
    """
    try:
        while True:
            # Get active executions
            active_executions = _get_active_executions(execution_repo)

            # Format as JSON
            data = [
                {
                    "id": execution.id,
                    "name": execution.workflow_name,
                    "deployment_id": execution.deployment_id,
                    "status": execution.status,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "duration_seconds": execution.duration_seconds,
                    "total_tokens": execution.total_tokens,
                    "total_cost_usd": execution.total_cost_usd,
                }
                for execution in active_executions
            ]

            # Send SSE event
            event = f"event: execution_update\n"
            event += f"data: {json.dumps(data)}\n\n"
            yield event

            # Wait before next update
            await asyncio.sleep(5)

            # Send heartbeat to keep connection alive
            yield ": heartbeat\n\n"

    except asyncio.CancelledError:
        # Client disconnected
        raise
    except Exception:
        # Log error and send heartbeat
        yield ": error\n\n"
        await asyncio.sleep(5)


async def _deployment_event_stream(
    deployment_repo: DeploymentRepository,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for deployment updates.

    Args:
        deployment_repo: Deployment repository for querying deployments

    Yields:
        SSE-formatted event strings
    """
    try:
        while True:
            # Get all alive deployments
            deployments = deployment_repo.list_all(include_dead=False)

            # Format as JSON
            data = [
                {
                    "id": deployment.deployment_id,
                    "name": deployment.deployment_name,
                    "workflow_name": deployment.workflow_name,
                    "host": deployment.host,
                    "port": deployment.port,
                    "is_alive": deployment.is_alive(),
                    "last_heartbeat": deployment.last_heartbeat.isoformat() if deployment.last_heartbeat else None,
                }
                for deployment in deployments
            ]

            # Send SSE event
            event = f"event: deployment_update\n"
            event += f"data: {json.dumps(data)}\n\n"
            yield event

            # Wait before next update
            await asyncio.sleep(10)

            # Send heartbeat to keep connection alive
            yield ": heartbeat\n\n"

    except asyncio.CancelledError:
        # Client disconnected
        raise
    except Exception:
        # Log error and send heartbeat
        yield ": error\n\n"
        await asyncio.sleep(10)


def _get_active_executions(repo: AbstractExecutionRepository, limit: int = 100) -> list:
    """Get active executions from repository.

    Args:
        repo: Execution repository
        limit: Maximum number of executions to return

    Returns:
        List of active Execution instances
    """
    # Try different methods based on repository implementation
    try:
        # For SQLite repository with engine access
        if hasattr(repo, 'engine'):
            engine = repo.engine
            with Session(engine) as session:
                stmt: Select[Execution] = (
                    select(Execution)
                    .where(
                        Execution.status.in_(["running", "pending"])
                    )
                    .order_by(Execution.started_at.desc())
                    .limit(limit)
                )
                return list(session.scalars(stmt).all())
    except Exception:
        pass

    # Fall back to trying list_all if it exists
    if hasattr(repo, 'list_all'):
        try:
            all_executions = repo.list_all(limit=limit)
            return [e for e in all_executions if e.status in ("running", "pending")]
        except Exception:
            pass

    return []


@router.get("/executions/stream")
async def executions_stream(request: Request):
    """SSE endpoint for execution updates.

    Returns a streaming response with execution update events every 5 seconds.
    Clients can listen for 'execution_update' events to receive real-time data.

    Headers:
        Cache-Control: no-cache
        Connection: keep-alive
        X-Accel-Buffering: no (disable nginx buffering)

    Example client-side usage (with HTMX SSE extension):
        <div hx-ext="sse" sse-connect="/metrics/executions/stream"
             sse-swap="execution_update">
        </div>
    """
    execution_repo = request.app.state.execution_repo

    return StreamingResponse(
        _execution_event_stream(execution_repo),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/deployments/stream")
async def deployments_stream(request: Request):
    """SSE endpoint for deployment updates.

    Returns a streaming response with deployment update events every 10 seconds.
    Clients can listen for 'deployment_update' events to receive real-time data.

    Headers:
        Cache-Control: no-cache
        Connection: keep-alive
        X-Accel-Buffering: no (disable nginx buffering)

    Example client-side usage (with HTMX SSE extension):
        <div hx-ext="sse" sse-connect="/metrics/deployments/stream"
             sse-swap="deployment_update">
        </div>
    """
    deployment_repo = request.app.state.deployment_repo

    return StreamingResponse(
        _deployment_event_stream(deployment_repo),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/summary")
async def metrics_summary(request: Request):
    """Get summary metrics for the dashboard.

    Returns a JSON summary of current system metrics including
    execution counts, deployment counts, and cost totals.
    """
    execution_repo = request.app.state.execution_repo
    deployment_repo = request.app.state.deployment_repo

    # Get execution stats
    all_executions = _get_all_executions_limit(execution_repo, limit=1000)
    total_executions = len(all_executions)
    running_executions = sum(1 for e in all_executions if e.status == "running")
    total_cost = sum(e.total_cost_usd or 0 for e in all_executions)

    # Get deployment stats
    deployments = deployment_repo.list_all(include_dead=False)
    registered_deployments = len(deployments)

    return {
        "total_executions": total_executions,
        "running_executions": running_executions,
        "registered_deployments": registered_deployments,
        "total_cost_usd": total_cost,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _get_all_executions_limit(repo: AbstractExecutionRepository, limit: int = 1000) -> list:
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


# Backward-compatible route aliases (deprecated)
@router.get("/workflows/stream")
async def workflows_stream_legacy(request: Request):
    """Legacy SSE endpoint - redirects to executions/stream."""
    return await executions_stream(request)


@router.get("/agents/stream")
async def agents_stream_legacy(request: Request):
    """Legacy SSE endpoint - redirects to deployments/stream."""
    return await deployments_stream(request)


# Export for templates
__all__ = ["router"]
