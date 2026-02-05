"""Dashboard routes for orchestrator management.

Provides web interface for manually registering agents, executing workflows
on remote agents, and managing agent connections. Orchestrator is embedded
in the dashboard (not a separate service).
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from configurable_agents.storage.base import AgentRegistryRepository, WorkflowRunRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


# ========================================
# Request/Response Models
# ========================================

class AgentRegistrationRequest(BaseModel):
    """Request model for manual agent registration."""
    agent_id: str = Field(..., description="Unique identifier for the agent")
    agent_name: str = Field(..., description="Human-readable name for the agent")
    agent_url: str = Field(..., description="Full URL of the agent (e.g., http://localhost:8001)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class ExecuteWorkflowRequest(BaseModel):
    """Request model for executing workflow on agent."""
    inputs: Dict[str, Any] = Field(..., description="Workflow inputs")


# ========================================
# Dependencies
# ========================================

def get_agent_registry_repo(request: Request) -> AgentRegistryRepository:
    """Get agent registry repository from app.state.

    Args:
        request: FastAPI request object

    Returns:
        AgentRegistryRepository instance

    Raises:
        HTTPException 500: If repository not available
    """
    repo = getattr(request.app.state, "agent_registry_repo", None)
    if repo is None:
        logger.error("Agent registry repository not initialized in app.state")
        raise HTTPException(
            status_code=500,
            detail="Agent registry repository not initialized."
        )
    return repo


def get_workflow_run_repo(request: Request) -> WorkflowRunRepository:
    """Get workflow run repository from app.state.

    Args:
        request: FastAPI request object

    Returns:
        WorkflowRunRepository instance

    Raises:
        HTTPException 500: If repository not available
    """
    repo = getattr(request.app.state, "workflow_run_repo", None)
    if repo is None:
        logger.error("Workflow run repository not initialized in app.state")
        raise HTTPException(
            status_code=500,
            detail="Workflow run repository not initialized."
        )
    return repo


# ========================================
# Routes
# ========================================

@router.get("", response_class=HTMLResponse)
async def orchestrator_page(request: Request) -> HTMLResponse:
    """Render the orchestrator management page."""
    templates = request.app.state.templates
    return templates.TemplateResponse("orchestrator.html", {"request": request})


@router.post("/register")
async def register_agent(
    registration: AgentRegistrationRequest,
    repo: AgentRegistryRepository = Depends(get_agent_registry_repo),
) -> Dict[str, Any]:
    """Manually register an agent with health check.

    Args:
        registration: Agent registration details
        repo: Agent registry repository

    Returns:
        Registration response with agent info

    Raises:
        HTTPException 400: If agent URL is invalid
        HTTPException 503: If agent health check fails
    """
    try:
        # Parse agent URL to extract host and port
        from urllib.parse import urlparse

        parsed = urlparse(registration.agent_url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent URL: {registration.agent_url}. Must include scheme (http:// or https://)"
            )

        host = parsed.hostname or parsed.netloc.split(":")[0]
        port = parsed.port or (80 if parsed.scheme == "http" else 443)

        # Health check: GET {agent_url}/health
        logger.info(f"Checking health of agent at {registration.agent_url}/health")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{registration.agent_url}/health")
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Agent health check failed: HTTP {response.status_code}"
                    )
                health_data = response.json()
                if health_data.get("status") != "alive":
                    raise HTTPException(
                        status_code=503,
                        detail=f"Agent is not alive: {health_data.get('status')}"
                    )
        except httpx.ConnectError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to agent at {registration.agent_url}: {str(e)}"
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=503,
                detail=f"Agent health check timed out: {registration.agent_url}/health"
            )

        # Register in database
        from configurable_agents.storage.models import AgentRecord

        agent_record = AgentRecord(
            agent_id=registration.agent_id,
            agent_name=registration.agent_name,
            host=host,
            port=port,
            agent_metadata=registration.metadata or {},
            registered_at=datetime.utcnow(),
            last_heartbeat=datetime.utcnow(),
        )

        # Add or update in repository
        existing = repo.get(registration.agent_id)
        if existing:
            # Update existing agent
            existing.agent_name = registration.agent_name
            existing.host = host
            existing.port = port
            existing.agent_metadata = registration.metadata or {}
            existing.last_heartbeat = datetime.utcnow()
            repo.update(existing)
        else:
            # Add new agent
            repo.add(agent_record)

        logger.info(f"Registered agent: {registration.agent_id} at {registration.agent_url}")

        return {
            "status": "registered",
            "agent_id": registration.agent_id,
            "agent_name": registration.agent_name,
            "agent_url": registration.agent_url,
            "message": f"Agent '{registration.agent_name}' registered successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register agent {registration.agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-check")
async def health_check_all(
    repo: AgentRegistryRepository = Depends(get_agent_registry_repo),
) -> Dict[str, Any]:
    """Health check all registered agents.

    Queries the /health endpoint of each agent and returns status.
    Called via HTMX polling every 10s from orchestrator page.

    Args:
        repo: Agent registry repository

    Returns:
        Dictionary with agents list and health status
    """
    try:
        agents = repo.list_all(include_dead=True)

        result_agents = []

        async with httpx.AsyncClient(timeout=3.0) as client:
            for agent in agents:
                # Build agent URL
                agent_url = f"http://{agent.host}:{agent.port}"

                # Check health
                is_healthy = False
                error_message = None

                try:
                    response = await client.get(f"{agent_url}/health")
                    if response.status_code == 200:
                        health_data = response.json()
                        is_healthy = health_data.get("status") == "alive"
                    else:
                        error_message = f"HTTP {response.status_code}"
                except httpx.ConnectError:
                    error_message = "Connection refused"
                except httpx.TimeoutException:
                    error_message = "Timeout"
                except Exception as e:
                    error_message = str(e)[:50]  # Truncate long errors

                result_agents.append({
                    "agent_id": agent.agent_id,
                    "agent_name": agent.agent_name,
                    "host": agent.host,
                    "port": agent.port,
                    "agent_url": agent_url,
                    "is_healthy": is_healthy,
                    "error_message": error_message,
                    "last_seen": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
                    "is_alive": agent.is_alive(),
                })

        return {"agents": result_agents}

    except Exception as e:
        logger.error(f"Failed to health check agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/schema")
async def get_agent_schema(
    agent_id: str,
    repo: AgentRegistryRepository = Depends(get_agent_registry_repo),
) -> Dict[str, Any]:
    """Get workflow schema from agent.

    Args:
        agent_id: Agent identifier
        repo: Agent registry repository

    Returns:
        Workflow schema JSON

    Raises:
        HTTPException 404: If agent not found
        HTTPException 503: If agent unreachable
    """
    try:
        # Get agent from database
        agent = repo.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        # Build agent URL
        agent_url = f"http://{agent.host}:{agent.port}"

        # Fetch schema
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{agent_url}/schema")
            if response.status_code != 200:
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to fetch schema: HTTP {response.status_code}"
                )

            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/execute")
async def execute_on_agent(
    agent_id: str,
    request_data: ExecuteWorkflowRequest,
    repo: AgentRegistryRepository = Depends(get_agent_registry_repo),
    workflow_repo: WorkflowRunRepository = Depends(get_workflow_run_repo),
) -> Dict[str, str]:
    """Execute workflow on agent.

    Calls POST /run on the agent with inputs, creates a WorkflowRunRecord
    with workflow_name=agent_id, and redirects to the run details page.

    Args:
        agent_id: Agent identifier
        request_data: Execution request with inputs
        repo: Agent registry repository
        workflow_repo: Workflow run repository

    Returns:
        Redirect response to /runs/{run_id}

    Raises:
        HTTPException 404: If agent not found
        HTTPException 503: If agent unreachable or execution fails
    """
    try:
        # Get agent from database
        agent = repo.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        # Build agent URL
        agent_url = f"http://{agent.host}:{agent.port}"

        # Create run ID and record
        run_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        # Create run record (will update after execution)
        from configurable_agents.storage.models import WorkflowRunRecord

        run_record = WorkflowRunRecord(
            id=run_id,
            workflow_name=agent_id,  # Use agent_id as workflow_name
            status="running",
            inputs=str(request_data.inputs),  # JSON string
            started_at=started_at,
        )
        workflow_repo.add(run_record)

        # Execute on agent
        logger.info(f"Executing on agent {agent_id} with inputs: {request_data.inputs}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{agent_url}/run",
                json=request_data.inputs,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                # Execution failed
                completed_at = datetime.utcnow()
                run_record.status = "failed"
                run_record.completed_at = completed_at
                run_record.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                workflow_repo.update(run_record)

                raise HTTPException(
                    status_code=503,
                    detail=f"Agent execution failed: HTTP {response.status_code} - {response.text[:200]}"
                )

            result = response.json()

        # Update run record with results
        completed_at = datetime.utcnow()
        duration_seconds = (completed_at - started_at).total_seconds()

        run_record.status = "completed"
        run_record.completed_at = completed_at
        run_record.duration_seconds = duration_seconds
        run_record.outputs = str(result.get("outputs")) if result.get("outputs") else None
        run_record.total_cost_usd = result.get("cost_usd")
        run_record.total_tokens = result.get("total_tokens")

        workflow_repo.update(run_record)

        logger.info(f"Execution completed: run_id={run_id}, agent={agent_id}, duration={duration_seconds:.2f}s")

        # Return redirect URL
        return {"redirect_url": f"/runs/{run_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute on agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}")
async def deregister_agent(
    agent_id: str,
    repo: AgentRegistryRepository = Depends(get_agent_registry_repo),
) -> Dict[str, str]:
    """Remove agent from registry.

    Args:
        agent_id: Agent identifier
        repo: Agent registry repository

    Returns:
        Deregistration confirmation

    Raises:
        HTTPException 404: If agent not found
    """
    try:
        agent = repo.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        repo.delete(agent_id)
        logger.info(f"Deregistered agent: {agent_id}")

        return {"status": "deregistered", "agent_id": agent_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deregister agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
