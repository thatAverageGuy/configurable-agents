"""Deployment management routes with HTMX-powered real-time updates.

Provides endpoints for viewing registered deployments, health status,
capabilities, and execution management with dynamic updates.

Renamed in UI Redesign (2026-02-13):
- agents.py → deployments.py
- orchestrator.py MERGED into this file
- AgentRecord → Deployment
- AgentRegistryRepository → DeploymentRepository
- Routes: /agents/* → /deployments/*
- Orchestrator routes merged into /deployments/*
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from configurable_agents.storage.base import DeploymentRepository, AbstractExecutionRepository
from configurable_agents.storage.models import Deployment, Execution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deployments")


# ========================================
# Request/Response Models (from orchestrator)
# ========================================

class DeploymentRegistrationRequest(BaseModel):
    """Request model for manual deployment registration."""
    deployment_id: str = Field(..., description="Unique identifier for the deployment")
    deployment_name: str = Field(..., description="Human-readable name for the deployment")
    deployment_url: str = Field(..., description="Full URL of the deployment (e.g., http://localhost:8001)")
    workflow_name: Optional[str] = Field(default=None, description="Name of the workflow this deployment runs")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class ExecuteWorkflowRequest(BaseModel):
    """Request model for executing workflow on deployment."""
    inputs: Dict[str, Any] = Field(..., description="Workflow inputs")


# ========================================
# Helper Functions
# ========================================

def time_ago(dt: Optional[datetime]) -> str:
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


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime as string.

    Args:
        dt: DateTime object

    Returns:
        Formatted datetime string (e.g., "2024-01-15 14:30:00")
    """
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_capabilities(deployment_metadata: Optional[str]) -> List[str]:
    """Extract capabilities from deployment metadata JSON.

    Args:
        deployment_metadata: JSON string containing deployment metadata

    Returns:
        List of capability strings
    """
    if not deployment_metadata:
        return []

    try:
        metadata = json.loads(deployment_metadata)
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


# ========================================
# Dependencies
# ========================================

async def _get_deployment_repo(request: Request) -> DeploymentRepository:
    """Get deployment repository from app state."""
    return request.app.state.deployment_repo


def get_execution_repo(request: Request) -> AbstractExecutionRepository:
    """Get execution repository from app.state.

    Args:
        request: FastAPI request object

    Returns:
        AbstractExecutionRepository instance

    Raises:
        HTTPException 500: If repository not available
    """
    repo = getattr(request.app.state, "execution_repo", None)
    if repo is None:
        logger.error("Execution repository not initialized in app.state")
        raise HTTPException(
            status_code=500,
            detail="Execution repository not initialized."
        )
    return repo


# ========================================
# List and View Routes
# ========================================

@router.get("/", response_class=HTMLResponse)
async def deployments_list(
    request: Request,
    deployment_repo: DeploymentRepository = Depends(_get_deployment_repo),
):
    """Render deployments list page."""
    templates = request.app.state.templates

    # Get all deployments (alive only by default)
    deployments = deployment_repo.list_all(include_dead=False)

    return templates.TemplateResponse(
        "deployments.html",
        {
            "request": request,
            "deployments": deployments,
        },
    )


@router.get("/table", response_class=HTMLResponse)
async def deployments_table(
    request: Request,
    deployment_repo: DeploymentRepository = Depends(_get_deployment_repo),
):
    """Render deployments table partial for HTMX refresh."""
    templates = request.app.state.templates

    # Get all deployments (alive only by default)
    deployments = deployment_repo.list_all(include_dead=False)

    return templates.TemplateResponse(
        "deployments_table.html",
        {
            "request": request,
            "deployments": deployments,
        },
    )


@router.get("/all", response_class=HTMLResponse)
async def deployments_list_all(
    request: Request,
    deployment_repo: DeploymentRepository = Depends(_get_deployment_repo),
):
    """Render deployments list page including dead deployments."""
    templates = request.app.state.templates

    # Get all deployments including dead ones
    deployments = deployment_repo.list_all(include_dead=True)

    return templates.TemplateResponse(
        "deployments.html",
        {
            "request": request,
            "deployments": deployments,
            "show_all": True,
        },
    )


@router.post("/refresh")
async def deployments_refresh(
    request: Request,
    deployment_repo: DeploymentRepository = Depends(_get_deployment_repo),
):
    """Trigger refresh of deployments table (for manual refresh button)."""
    templates = request.app.state.templates

    # Get all deployments (alive only by default)
    deployments = deployment_repo.list_all(include_dead=False)

    return templates.TemplateResponse(
        "deployments_table.html",
        {
            "request": request,
            "deployments": deployments,
        },
    )


# ========================================
# Registration and Management Routes (from orchestrator)
# ========================================

@router.post("/register")
async def register_deployment(
    registration: DeploymentRegistrationRequest,
    repo: DeploymentRepository = Depends(_get_deployment_repo),
) -> Dict[str, Any]:
    """Manually register a deployment with health check.

    Args:
        registration: Deployment registration details
        repo: Deployment repository

    Returns:
        Registration response with deployment info

    Raises:
        HTTPException 400: If deployment URL is invalid
        HTTPException 503: If deployment health check fails
    """
    try:
        # Parse deployment URL to extract host and port
        from urllib.parse import urlparse

        parsed = urlparse(registration.deployment_url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid deployment URL: {registration.deployment_url}. Must include scheme (http:// or https://)"
            )

        host = parsed.hostname or parsed.netloc.split(":")[0]
        port = parsed.port or (80 if parsed.scheme == "http" else 443)

        # Health check: GET {deployment_url}/health
        logger.info(f"Checking health of deployment at {registration.deployment_url}/health")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{registration.deployment_url}/health")
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Deployment health check failed: HTTP {response.status_code}"
                    )
                health_data = response.json()
                if health_data.get("status") != "alive":
                    raise HTTPException(
                        status_code=503,
                        detail=f"Deployment is not alive: {health_data.get('status')}"
                    )
        except httpx.ConnectError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to deployment at {registration.deployment_url}: {str(e)}"
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=503,
                detail=f"Deployment health check timed out: {registration.deployment_url}/health"
            )

        # Serialize metadata to JSON string for database storage
        metadata_json = json.dumps(registration.metadata) if registration.metadata else "{}"

        deployment_record = Deployment(
            deployment_id=registration.deployment_id,
            deployment_name=registration.deployment_name,
            workflow_name=registration.workflow_name,
            host=host,
            port=port,
            deployment_metadata=metadata_json,
            registered_at=datetime.utcnow(),
            last_heartbeat=datetime.utcnow(),
        )

        # Add or update in repository
        existing = repo.get(registration.deployment_id)
        if existing:
            # Update existing deployment
            existing.deployment_name = registration.deployment_name
            existing.workflow_name = registration.workflow_name
            existing.host = host
            existing.port = port
            existing.deployment_metadata = metadata_json
            existing.last_heartbeat = datetime.utcnow()
        else:
            # Add new deployment
            repo.add(deployment_record)

        logger.info(f"Registered deployment: {registration.deployment_id} at {registration.deployment_url}")

        return {
            "status": "registered",
            "deployment_id": registration.deployment_id,
            "deployment_name": registration.deployment_name,
            "deployment_url": registration.deployment_url,
            "message": f"Deployment '{registration.deployment_name}' registered successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register deployment {registration.deployment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-check", response_class=HTMLResponse)
async def health_check_all(
    repo: DeploymentRepository = Depends(_get_deployment_repo),
) -> HTMLResponse:
    """Health check all registered deployments.

    Queries the /health endpoint of each deployment and returns HTML partial.
    Called via HTMX polling every 10s from deployments page.

    Args:
        repo: Deployment repository

    Returns:
        HTML partial for deployments list
    """
    try:
        deployments = repo.list_all(include_dead=True)

        if not deployments:
            return HTMLResponse(
                content='<div class="no-deployments">No deployments registered yet. Use the form above to register your first deployment.</div>'
            )

        result_deployments = []

        async with httpx.AsyncClient(timeout=3.0) as client:
            for deployment in deployments:
                # Build deployment URL
                deployment_url = f"http://{deployment.host}:{deployment.port}"

                # Check health
                is_healthy = False
                error_message = None

                try:
                    response = await client.get(f"{deployment_url}/health")
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

                # Calculate time ago
                if deployment.last_heartbeat:
                    delta = datetime.utcnow() - deployment.last_heartbeat
                    seconds = delta.total_seconds()
                    if seconds < 60:
                        time_ago_str = f"{int(seconds)}s ago"
                    else:
                        minutes = int(seconds / 60)
                        time_ago_str = f"{minutes}m ago"
                else:
                    time_ago_str = "Never"

                result_deployments.append({
                    "deployment_id": deployment.deployment_id,
                    "deployment_name": deployment.deployment_name,
                    "workflow_name": deployment.workflow_name,
                    "host": deployment.host,
                    "port": deployment.port,
                    "deployment_url": deployment_url,
                    "is_healthy": is_healthy,
                    "error_message": error_message,
                    "last_seen": time_ago_str,
                    "is_alive": deployment.is_alive(),
                })

        # Build HTML table
        html = '''
        <div id="deployments-list-container"
             hx-get="/deployments/health-check"
             hx-trigger="every 10s"
             hx-swap="outerHTML">
            <h3>Registered Deployments</h3>
            <table class="deployments-table">
                <thead>
                    <tr>
                        <th>Status</th>
                        <th>Name</th>
                        <th>ID</th>
                        <th>Workflow</th>
                        <th>URL</th>
                        <th>Last Seen</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        '''

        for dep_data in result_deployments:
            status_class = "status-healthy" if dep_data["is_healthy"] else "status-unhealthy"
            status_text = "✓ Healthy" if dep_data["is_healthy"] else f"✗ {dep_data['error_message'] or 'Unavailable'}"

            html += f'''
                    <tr>
                        <td class="{status_class}">{status_text}</td>
                        <td><strong>{dep_data['deployment_name']}</strong></td>
                        <td><code>{dep_data['deployment_id']}</code></td>
                        <td>{dep_data['workflow_name'] or '-'}</td>
                        <td><code>{dep_data['deployment_url']}</code></td>
                        <td>{dep_data['last_seen']}</td>
                        <td>
                            <button class="btn-execute" onclick="openExecuteModal('{dep_data['deployment_id']}', '{dep_data['deployment_name']}')">Execute</button>
                            <button class="btn-remove" onclick="removeDeployment('{dep_data['deployment_id']}', '{dep_data['deployment_name']}')">Remove</button>
                        </td>
                    </tr>
            '''

        html += '''
                </tbody>
            </table>
        </div>
        '''

        return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"Failed to health check deployments: {e}")
        return HTMLResponse(
            content=f'<div class="error-message">Failed to load deployments: {str(e)}</div>'
        )


@router.delete("/{deployment_id}")
async def deregister_deployment(
    deployment_id: str,
    repo: DeploymentRepository = Depends(_get_deployment_repo),
) -> Dict[str, str]:
    """Remove deployment from registry.

    Args:
        deployment_id: Deployment identifier
        repo: Deployment repository

    Returns:
        Deregistration confirmation

    Raises:
        HTTPException 404: If deployment not found
    """
    try:
        deployment = repo.get(deployment_id)
        if deployment is None:
            raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")

        repo.delete(deployment_id)
        logger.info(f"Deregistered deployment: {deployment_id}")

        return {"status": "deregistered", "deployment_id": deployment_id}

    except HTTPException:
        raise
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Failed to deregister deployment {deployment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deployment_id}/docs")
async def deployment_docs(
    deployment_id: str,
    repo: DeploymentRepository = Depends(_get_deployment_repo),
):
    """Redirect to deployment's API documentation."""
    deployment = repo.get(deployment_id)

    if deployment is None:
        return HTMLResponse(
            content=f"Deployment not found: {deployment_id}",
            status_code=404,
        )

    # Redirect to deployment's docs endpoint
    docs_url = f"http://{deployment.host}:{deployment.port}/docs"
    return RedirectResponse(url=docs_url, status_code=302)


# ========================================
# Execution Routes (from orchestrator)
# ========================================

@router.get("/{deployment_id}/schema")
async def get_deployment_schema(
    deployment_id: str,
    repo: DeploymentRepository = Depends(_get_deployment_repo),
) -> Dict[str, Any]:
    """Get workflow schema from deployment.

    Args:
        deployment_id: Deployment identifier
        repo: Deployment repository

    Returns:
        Workflow schema JSON

    Raises:
        HTTPException 404: If deployment not found
        HTTPException 503: If deployment unreachable
    """
    try:
        # Get deployment from database
        deployment = repo.get(deployment_id)
        if deployment is None:
            raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")

        # Build deployment URL
        deployment_url = f"http://{deployment.host}:{deployment.port}"

        # Fetch schema
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{deployment_url}/schema")
            if response.status_code != 200:
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to fetch schema: HTTP {response.status_code}"
                )

            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema for deployment {deployment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{deployment_id}/execute")
async def execute_on_deployment(
    deployment_id: str,
    request_data: ExecuteWorkflowRequest,
    repo: DeploymentRepository = Depends(_get_deployment_repo),
    execution_repo: AbstractExecutionRepository = Depends(get_execution_repo),
) -> Dict[str, str]:
    """Execute workflow on deployment.

    Calls POST /run on the deployment with inputs, creates an Execution
    record with deployment_id set, and redirects to the execution details page.

    Args:
        deployment_id: Deployment identifier
        request_data: Execution request with inputs
        repo: Deployment repository
        execution_repo: Execution repository

    Returns:
        Redirect response to /executions/{execution_id}

    Raises:
        HTTPException 404: If deployment not found
        HTTPException 503: If deployment unreachable or execution fails
    """
    try:
        # Get deployment from database
        deployment = repo.get(deployment_id)
        if deployment is None:
            raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")

        # Build deployment URL
        deployment_url = f"http://{deployment.host}:{deployment.port}"

        # Create execution ID and record
        execution_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        # Create execution record (will update after execution)
        execution_record = Execution(
            id=execution_id,
            workflow_name=deployment.workflow_name or deployment_id,
            deployment_id=deployment_id,  # Link to deployment
            status="running",
            inputs=json.dumps(request_data.inputs),
            started_at=started_at,
        )
        execution_repo.add(execution_record)

        # Execute on deployment
        logger.info(f"Executing on deployment {deployment_id} with inputs: {request_data.inputs}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{deployment_url}/run",
                json=request_data.inputs,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                # Execution failed
                completed_at = datetime.utcnow()
                duration_seconds = (completed_at - started_at).total_seconds()

                # Mark as failed
                execution_repo.update_status(execution_id, "failed")

                # Update error message directly via SQL
                with execution_repo.engine.begin() as conn:
                    conn.execute(
                        text("UPDATE executions SET error_message = :error, completed_at = :completed_at, duration_seconds = :duration WHERE id = :id"),
                        {"error": f"HTTP {response.status_code}: {response.text[:200]}", "completed_at": completed_at, "duration": duration_seconds, "id": execution_id}
                    )

                raise HTTPException(
                    status_code=503,
                    detail=f"Deployment execution failed: HTTP {response.status_code} - {response.text[:200]}"
                )

            result = response.json()

        # Update execution record with results
        completed_at = datetime.utcnow()
        duration_seconds = (completed_at - started_at).total_seconds()

        # Use update_execution_completion method
        execution_repo.update_execution_completion(
            execution_id,
            "completed",
            duration_seconds,
            result.get("total_tokens") or 0,
            result.get("cost_usd") or 0.0
        )

        # Update outputs directly via SQL
        with execution_repo.engine.begin() as conn:
            conn.execute(
                text("UPDATE executions SET outputs = :outputs WHERE id = :id"),
                {"outputs": json.dumps(result.get("outputs")) if result.get("outputs") else None, "id": execution_id}
            )

        logger.info(f"Execution completed: execution_id={execution_id}, deployment={deployment_id}, duration={duration_seconds:.2f}s")

        # Return redirect URL
        return {"redirect_url": f"/executions/{execution_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute on deployment {deployment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export helper functions for use in templates
__all__ = [
    "router",
    "time_ago",
    "format_datetime",
    "parse_capabilities",
]
