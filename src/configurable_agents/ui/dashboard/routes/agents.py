"""Agent discovery routes with HTMX-powered real-time updates.

Provides endpoints for viewing registered agents, health status,
and capabilities with dynamic updates via Server-Sent Events (SSE).
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from configurable_agents.storage.base import AgentRegistryRepository
from configurable_agents.storage.models import AgentRecord


router = APIRouter(prefix="/agents")


def _time_ago(dt: Optional[datetime]) -> str:
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
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours}h ago"
    else:
        days = int(seconds // 86400)
        return f"{days}d ago"


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


def _parse_capabilities(agent_metadata: Optional[str]) -> List[str]:
    """Extract capabilities from agent metadata JSON.

    Args:
        agent_metadata: JSON string containing agent metadata

    Returns:
        List of capability strings
    """
    if not agent_metadata:
        return []

    try:
        metadata = json.loads(agent_metadata)
        if isinstance(metadata, dict):
            # Try common capability keys
            if "capabilities" in metadata:
                capabilities = metadata.get("capabilities")
                if isinstance(capabilities, list) and capabilities:
                    return capabilities
            # Try nodes as capabilities
            if "nodes" in metadata:
                nodes = metadata.get("nodes")
                if isinstance(nodes, list):
                    return [str(n) for n in nodes]
        elif isinstance(metadata, list):
            return [str(item) for item in metadata]
    except (json.JSONDecodeError, TypeError):
        pass

    return []


# Dependency to get agent repo from app state
async def _get_agent_repo(request: Request) -> AgentRegistryRepository:
    """Get agent repository from app state."""
    return request.app.state.agent_registry_repo


@router.get("/", response_class=HTMLResponse)
async def agents_list(
    request: Request,
    agent_repo: AgentRegistryRepository = Depends(_get_agent_repo),
):
    """Render agents list page."""
    templates: Jinja2Templates = request.app.state.templates

    # Get all agents (alive only by default)
    agents = agent_repo.list_all(include_dead=False)

    return templates.TemplateResponse(
        "agents.html",
        {
            "request": request,
            "agents": agents,
        },
    )


@router.get("/table", response_class=HTMLResponse)
async def agents_table(
    request: Request,
    agent_repo: AgentRegistryRepository = Depends(_get_agent_repo),
):
    """Render agents table partial for HTMX refresh."""
    templates: Jinja2Templates = request.app.state.templates

    # Get all agents (alive only by default)
    agents = agent_repo.list_all(include_dead=False)

    return templates.TemplateResponse(
        "agents_table.html",
        {
            "request": request,
            "agents": agents,
        },
    )


@router.get("/all", response_class=HTMLResponse)
async def agents_list_all(
    request: Request,
    agent_repo: AgentRegistryRepository = Depends(_get_agent_repo),
):
    """Render agents list page including dead agents."""
    templates: Jinja2Templates = request.app.state.templates

    # Get all agents including dead ones
    agents = agent_repo.list_all(include_dead=True)

    return templates.TemplateResponse(
        "agents.html",
        {
            "request": request,
            "agents": agents,
            "show_all": True,
        },
    )


@router.delete("/{agent_id}")
async def agent_deregister(
    agent_id: str,
    agent_repo: AgentRegistryRepository = Depends(_get_agent_repo),
):
    """Deregister an agent from the registry."""
    try:
        agent_repo.delete(agent_id)
        return Response(
            content=f"Agent {agent_id} deregistered",
            status_code=200,
        )
    except ValueError as e:
        return Response(
            content=str(e),
            status_code=404,
        )
    except Exception as e:
        return Response(
            content=f"Failed to deregister agent: {e}",
            status_code=500,
        )


@router.get("/{agent_id}/docs")
async def agent_docs(
    agent_id: str,
    agent_repo: AgentRegistryRepository = Depends(_get_agent_repo),
):
    """Redirect to agent's API documentation."""
    agent = agent_repo.get(agent_id)

    if agent is None:
        return Response(
            content=f"Agent not found: {agent_id}",
            status_code=404,
        )

    # Redirect to agent's docs endpoint
    docs_url = f"http://{agent.host}:{agent.port}/docs"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=docs_url, status_code=302)


@router.post("/refresh")
async def agents_refresh(
    request: Request,
    agent_repo: AgentRegistryRepository = Depends(_get_agent_repo),
):
    """Trigger refresh of agents table (for manual refresh button)."""
    templates: Jinja2Templates = request.app.state.templates

    # Get all agents (alive only by default)
    agents = agent_repo.list_all(include_dead=False)

    return templates.TemplateResponse(
        "agents_table.html",
        {
            "request": request,
            "agents": agents,
        },
    )


# Export helper functions for use in templates
__all__ = [
    "router",
    "_time_ago",
    "_format_datetime",
    "_parse_capabilities",
]
