"""Pydantic models for agent registry API.

Defines request and response schemas for the agent registry HTTP endpoints.
Uses Pydantic for validation and serialization.

These models map between HTTP JSON and the AgentRecord ORM model.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentRegistrationRequest(BaseModel):
    """Request model for agent registration.

    Agents submit this data when registering with the registry.
    Registration is idempotent - re-registering with the same agent_id
    updates the existing record.

    Attributes:
        agent_id: Unique identifier for this agent
        agent_name: Human-readable name for the agent
        host: Host address where the agent is running
        port: Port number where the agent is listening
        ttl_seconds: Time-to-live in seconds for heartbeat (default: 60)
        metadata: Optional JSON string with additional agent info
    """

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: str = Field(..., description="Human-readable agent name")
    host: str = Field(..., description="Agent host address")
    port: int = Field(..., ge=1, le=65535, description="Agent port number")
    ttl_seconds: int = Field(
        default=60, ge=1, le=3600, description="TTL in seconds for heartbeat"
    )
    metadata: Optional[str] = Field(
        default=None, description="JSON blob with additional agent info"
    )


class AgentInfo(BaseModel):
    """Response model for agent information.

    Returned by list and get operations to show agent status.

    Attributes:
        agent_id: Unique identifier for the agent
        agent_name: Human-readable name for the agent
        host: Host address where the agent is running
        port: Port number where the agent is listening
        is_alive: Whether the agent's TTL has not expired
        last_heartbeat: Timestamp of the last heartbeat from this agent
        registered_at: When the agent first registered with the registry
        ttl_seconds: Configured TTL for this agent
        metadata: JSON blob with additional agent info
    """

    agent_id: str
    agent_name: str
    host: str
    port: int
    is_alive: bool
    last_heartbeat: datetime
    registered_at: datetime
    ttl_seconds: int
    metadata: Optional[str] = None


class HeartbeatResponse(BaseModel):
    """Response model for heartbeat endpoint.

    Confirms that the heartbeat was received and the agent's TTL refreshed.

    Attributes:
        status: Confirmation message
        last_heartbeat: Timestamp of the heartbeat that was recorded
    """

    status: str
    last_heartbeat: datetime


class HealthResponse(BaseModel):
    """Response model for health check endpoint.

    Indicates the registry server is operational.

    Attributes:
        status: Health status (should be "healthy")
        registered_agents: Number of agents currently registered
        active_agents: Number of agents with valid TTL
    """

    status: str
    registered_agents: int
    active_agents: int


class OrchestratorRegistrationRequest(BaseModel):
    """Request model for orchestrator registration.

    Orchestrators submit this data when registering with the registry.
    Registration is idempotent - re-registering with the same orchestrator_id
    updates the existing record.

    Attributes:
        orchestrator_id: Unique identifier for this orchestrator
        orchestrator_name: Human-readable name for the orchestrator
        orchestrator_type: Type of orchestrator (e.g., "central", "distributed")
        api_endpoint: URL where the orchestrator exposes its API
        ttl_seconds: Time-to-live in seconds for heartbeat (default: 300)
    """

    orchestrator_id: str = Field(..., description="Unique orchestrator identifier")
    orchestrator_name: str = Field(..., description="Human-readable orchestrator name")
    orchestrator_type: str = Field(
        ..., description="Type of orchestrator (e.g., 'central', 'distributed')"
    )
    api_endpoint: str = Field(..., description="Orchestrator API endpoint URL")
    ttl_seconds: int = Field(
        default=300, ge=1, le=3600, description="TTL in seconds for heartbeat"
    )


class OrchestratorInfo(BaseModel):
    """Response model for orchestrator information.

    Returned by list and get operations to show orchestrator status.

    Attributes:
        orchestrator_id: Unique identifier for the orchestrator
        orchestrator_name: Human-readable name for the orchestrator
        orchestrator_type: Type of orchestrator
        api_endpoint: URL where the orchestrator exposes its API
        is_alive: Whether the orchestrator's TTL has not expired
        last_heartbeat: Timestamp of the last heartbeat from this orchestrator
        registered_at: When the orchestrator first registered with the registry
        ttl_seconds: Configured TTL for this orchestrator
    """

    orchestrator_id: str
    orchestrator_name: str
    orchestrator_type: str
    api_endpoint: str
    is_alive: bool
    last_heartbeat: datetime
    registered_at: datetime
    ttl_seconds: int
