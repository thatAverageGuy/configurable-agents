"""Pydantic models for deployment registry API.

Defines request and response schemas for the deployment registry HTTP endpoints.
Uses Pydantic for validation and serialization.

These models map between HTTP JSON and the Deployment ORM model.

Renamed in UI Redesign (2026-02-13):
- AgentRegistrationRequest → DeploymentRegistrationRequest
- AgentInfo → DeploymentInfo
- Removed OrchestratorRegistrationRequest and OrchestratorInfo
- Field names: agent_id → deployment_id, agent_name → deployment_name
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DeploymentRegistrationRequest(BaseModel):
    """Request model for deployment registration.

    Deployments submit this data when registering with the registry.
    Registration is idempotent - re-registering with the same deployment_id
    updates the existing record.

    Attributes:
        deployment_id: Unique identifier for this deployment
        deployment_name: Human-readable name for the deployment
        host: Host address where the deployment is running
        port: Port number where the deployment is listening
        ttl_seconds: Time-to-live in seconds for heartbeat (default: 60)
        workflow_name: Name of the workflow this deployment runs (optional)
        metadata: Optional JSON string with additional deployment info
    """

    deployment_id: str = Field(..., description="Unique deployment identifier")
    deployment_name: str = Field(..., description="Human-readable deployment name")
    host: str = Field(..., description="Deployment host address")
    port: int = Field(..., ge=1, le=65535, description="Deployment port number")
    ttl_seconds: int = Field(
        default=60, ge=1, le=3600, description="TTL in seconds for heartbeat"
    )
    workflow_name: Optional[str] = Field(
        default=None, description="Name of the workflow this deployment runs"
    )
    metadata: Optional[str] = Field(
        default=None, description="JSON blob with additional deployment info"
    )


class DeploymentInfo(BaseModel):
    """Response model for deployment information.

    Returned by list and get operations to show deployment status.

    Attributes:
        deployment_id: Unique identifier for the deployment
        deployment_name: Human-readable name for the deployment
        host: Host address where the deployment is running
        port: Port number where the deployment is listening
        workflow_name: Name of the workflow this deployment runs
        is_alive: Whether the deployment's TTL has not expired
        last_heartbeat: Timestamp of the last heartbeat from this deployment
        registered_at: When the deployment first registered with the registry
        ttl_seconds: Configured TTL for this deployment
        metadata: JSON blob with additional deployment info
    """

    deployment_id: str
    deployment_name: str
    host: str
    port: int
    workflow_name: Optional[str] = None
    is_alive: bool
    last_heartbeat: datetime
    registered_at: datetime
    ttl_seconds: int
    metadata: Optional[str] = None


class HeartbeatResponse(BaseModel):
    """Response model for heartbeat endpoint.

    Confirms that the heartbeat was received and the deployment's TTL refreshed.

    Attributes:
        status: Confirmation message
        last_heartbeat: Timestamp of the heartbeat that was recorded
        message: Optional message
    """

    status: str
    last_heartbeat: Optional[datetime] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check endpoint.

    Indicates the registry server is operational.

    Attributes:
        status: Health status (should be "healthy")
        registered_deployments: Number of deployments currently registered
        active_deployments: Number of deployments with valid TTL
    """

    status: str
    registered_deployments: int
    active_deployments: int


# Backward-compatible aliases (deprecated, will be removed in future)
AgentRegistrationRequest = DeploymentRegistrationRequest
AgentInfo = DeploymentInfo
