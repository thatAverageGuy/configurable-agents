"""Server-Sent Events (SSE) endpoints for real-time metrics streaming.

Provides SSE endpoints for workflow and agent updates that
push data to connected clients for dynamic dashboard updates.
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
    AbstractWorkflowRunRepository,
    AgentRegistryRepository,
)
from configurable_agents.storage.models import WorkflowRunRecord, AgentRecord


router = APIRouter(prefix="/metrics")


async def _workflow_event_stream(
    workflow_repo: AbstractWorkflowRunRepository,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for workflow updates.

    Args:
        workflow_repo: Workflow repository for querying runs

    Yields:
        SSE-formatted event strings
    """
    try:
        while True:
            # Get active runs
            active_runs = _get_active_runs(workflow_repo)

            # Format as JSON
            data = [
                {
                    "id": run.id,
                    "name": run.workflow_name,
                    "status": run.status,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "duration_seconds": run.duration_seconds,
                    "total_tokens": run.total_tokens,
                    "total_cost_usd": run.total_cost_usd,
                }
                for run in active_runs
            ]

            # Send SSE event
            event = f"event: workflow_update\n"
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


async def _agent_event_stream(
    agent_repo: AgentRegistryRepository,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for agent updates.

    Args:
        agent_repo: Agent repository for querying agents

    Yields:
        SSE-formatted event strings
    """
    try:
        while True:
            # Get all alive agents
            agents = agent_repo.list_all(include_dead=False)

            # Format as JSON
            data = [
                {
                    "id": agent.agent_id,
                    "name": agent.agent_name,
                    "host": agent.host,
                    "port": agent.port,
                    "is_alive": agent.is_alive(),
                    "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
                }
                for agent in agents
            ]

            # Send SSE event
            event = f"event: agent_update\n"
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


def _get_active_runs(repo: AbstractWorkflowRunRepository, limit: int = 100) -> list:
    """Get active workflow runs from repository.

    Args:
        repo: Workflow repository
        limit: Maximum number of runs to return

    Returns:
        List of active WorkflowRunRecord instances
    """
    # Try different methods based on repository implementation
    try:
        # For SQLite repository with engine access
        if hasattr(repo, 'engine'):
            engine = repo.engine
            with Session(engine) as session:
                stmt: Select[WorkflowRunRecord] = (
                    select(WorkflowRunRecord)
                    .where(
                        WorkflowRunRecord.status.in_(["running", "pending"])
                    )
                    .order_by(WorkflowRunRecord.started_at.desc())
                    .limit(limit)
                )
                return list(session.scalars(stmt).all())
    except Exception:
        pass

    # Fall back to trying list_all if it exists
    if hasattr(repo, 'list_all'):
        try:
            all_runs = repo.list_all(limit=limit)
            return [r for r in all_runs if r.status in ("running", "pending")]
        except Exception:
            pass

    return []


@router.get("/workflows/stream")
async def workflows_stream(request: Request):
    """SSE endpoint for workflow updates.

    Returns a streaming response with workflow update events every 5 seconds.
    Clients can listen for 'workflow_update' events to receive real-time data.

    Headers:
        Cache-Control: no-cache
        Connection: keep-alive
        X-Accel-Buffering: no (disable nginx buffering)

    Example client-side usage (with HTMX SSE extension):
        <div hx-ext="sse" sse-connect="/metrics/workflows/stream"
             sse-swap="workflow_update">
        </div>
    """
    workflow_repo = request.app.state.workflow_repo

    return StreamingResponse(
        _workflow_event_stream(workflow_repo),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agents/stream")
async def agents_stream(request: Request):
    """SSE endpoint for agent updates.

    Returns a streaming response with agent update events every 10 seconds.
    Clients can listen for 'agent_update' events to receive real-time data.

    Headers:
        Cache-Control: no-cache
        Connection: keep-alive
        X-Accel-Buffering: no (disable nginx buffering)

    Example client-side usage (with HTMX SSE extension):
        <div hx-ext="sse" sse-connect="/metrics/agents/stream"
             sse-swap="agent_update">
        </div>
    """
    agent_repo = request.app.state.agent_registry_repo

    return StreamingResponse(
        _agent_event_stream(agent_repo),
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
    workflow counts, agent counts, and cost totals.
    """
    workflow_repo = request.app.state.workflow_repo
    agent_repo = request.app.state.agent_registry_repo

    # Get workflow stats
    all_runs = _get_all_runs_limit(workflow_repo, limit=1000)
    total_workflows = len(all_runs)
    running_workflows = sum(1 for r in all_runs if r.status == "running")
    total_cost = sum(r.total_cost_usd or 0 for r in all_runs)

    # Get agent stats
    agents = agent_repo.list_all(include_dead=False)
    registered_agents = len(agents)

    return {
        "total_workflows": total_workflows,
        "running_workflows": running_workflows,
        "registered_agents": registered_agents,
        "total_cost_usd": total_cost,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _get_all_runs_limit(repo: AbstractWorkflowRunRepository, limit: int = 1000) -> list:
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


# Export for templates
__all__ = ["router"]
