"""Dashboard routes for orchestrator management.

Provides web interface for viewing orchestrator status, discovering agents,
and managing agent connections.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from configurable_agents.orchestrator.models import AgentConnection
from configurable_agents.orchestrator.service import OrchestratorService
from configurable_agents.storage.base import OrchestratorRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


def get_orchestrator_service() -> OrchestratorService:
    """Get or create the orchestrator service.

    This is a placeholder - in production, the service would be
    initialized at startup and injected via dependency injection.

    Returns:
        OrchestratorService instance

    Raises:
        HTTPException 500: If service cannot be created
    """
    # TODO: In production, this would be injected via app.state
    from configurable_agents.orchestrator import create_orchestrator_service

    try:
        # Get registry URL from environment or use default
        import os

        registry_url = os.getenv("REGISTRY_URL", "http://localhost:9000")
        return create_orchestrator_service(registry_url)
    except Exception as e:
        logger.error(f"Failed to create orchestrator service: {e}")
        raise HTTPException(status_code=500, detail="Orchestrator service unavailable")


def get_orchestrator_repo() -> OrchestratorRepository:
    """Get or create the orchestrator repository.

    Returns:
        OrchestratorRepository instance

    Raises:
        HTTPException 500: If repository cannot be created
    """
    # TODO: In production, this would be injected via app.state
    from configurable_agents.storage import create_storage_backend

    try:
        _, _, _, _, _, _, _, orchestrator_repo = create_storage_backend()
        return orchestrator_repo
    except Exception as e:
        logger.error(f"Failed to get orchestrator repository: {e}")
        raise HTTPException(status_code=500, detail="Storage unavailable")


@router.get("", response_class=HTMLResponse)
async def orchestrator_page(request: Request) -> HTMLResponse:
    """Render the orchestrator management page."""
    # Get templates from app state
    templates = request.app.state.templates

    return templates.TemplateResponse("orchestrator.html", {"request": request})


@router.get("/status")
async def get_orchestrator_status(
    service: OrchestratorService = Depends(get_orchestrator_service),
) -> Dict:
    """Get orchestrator and agent connection status.

    Returns:
        Status dictionary with connection counts and health info
    """
    try:
        return service.get_status()
    except Exception as e:
        logger.error(f"Failed to get orchestrator status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def discover_agents(
    include_dead: bool = False,
    service: OrchestratorService = Depends(get_orchestrator_service),
) -> Dict[str, List[Dict]]:
    """Discover agents from the registry.

    Args:
        include_dead: If False, only return alive agents

    Returns:
        Dictionary with discovered agents list
    """
    try:
        agents = service.discover_agents(include_dead=include_dead)
        return {"agents": agents}
    except Exception as e:
        logger.error(f"Failed to discover agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect/{agent_id}")
async def connect_to_agent(
    agent_id: str,
    connection_params: Optional[Dict] = None,
    service: OrchestratorService = Depends(get_orchestrator_service),
) -> Dict:
    """Manually connect to an agent.

    Args:
        agent_id: Unique identifier for the agent
        connection_params: Optional connection parameters

    Returns:
        Connection details

    Raises:
        HTTPException 404: If agent not found
        HTTPException 500: If connection fails
    """
    try:
        connection = service.register_agent(agent_id, connection_params)
        return {"status": "connected", "connection": connection.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to connect to agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/disconnect/{agent_id}")
async def disconnect_from_agent(
    agent_id: str,
    service: OrchestratorService = Depends(get_orchestrator_service),
) -> Dict:
    """Disconnect from an agent.

    Args:
        agent_id: Unique identifier for the agent

    Returns:
        Disconnection confirmation

    Raises:
        HTTPException 404: If agent not connected
        HTTPException 500: If disconnection fails
    """
    try:
        success = service.deregister_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Not connected to agent {agent_id}")

        return {"status": "disconnected", "agent_id": agent_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect from agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections")
async def list_connections(
    service: OrchestratorService = Depends(get_orchestrator_service),
) -> Dict[str, List[Dict]]:
    """List all active agent connections.

    Returns:
        Dictionary with connections list
    """
    try:
        connections = service.list_connections()
        return {"connections": [c.to_dict() for c in connections]}
    except Exception as e:
        logger.error(f"Failed to list connections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orchestrators")
async def list_orchestrators(
    repo: OrchestratorRepository = Depends(get_orchestrator_repo),
) -> Dict[str, List]:
    """List all registered orchestrators.

    Returns:
        Dictionary with orchestrators list
    """
    try:
        orchestrators = repo.list_all(include_dead=False)
        return {
            "orchestrators": [
                {
                    "orchestrator_id": o.orchestrator_id,
                    "orchestrator_name": o.orchestrator_name,
                    "orchestrator_type": o.orchestrator_type,
                    "api_endpoint": o.api_endpoint,
                    "is_alive": o.is_alive(),
                    "last_heartbeat": o.last_heartbeat.isoformat() if o.last_heartbeat else None,
                    "ttl_seconds": o.ttl_seconds,
                }
                for o in orchestrators
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list orchestrators: {e}")
        raise HTTPException(status_code=500, detail=str(e))
