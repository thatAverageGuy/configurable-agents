"""Agent registry FastAPI server.

Provides HTTP endpoints for agent registration, heartbeat, listing,
and health checks. Runs a background cleanup task to remove expired agents.

Example:
    >>> from configurable_agents.registry import AgentRegistryServer
    >>> server = AgentRegistryServer("sqlite:///agents.db")
    >>> app = server.create_app()
    >>> # Run with: uvicorn app:app --port 8000
"""

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from configurable_agents.config.schema import StorageConfig
from configurable_agents.storage.base import AgentRegistryRepository
from configurable_agents.storage.factory import create_storage_backend
from configurable_agents.storage.models import AgentRecord

from configurable_agents.registry.models import (
    AgentInfo,
    AgentRegistrationRequest,
    HealthResponse,
    HeartbeatResponse,
)


class AgentRegistryServer:
    """Agent registry server using FastAPI.

    Provides HTTP endpoints for agent registration, heartbeat refresh,
    agent listing, and health checks. Runs a background task to clean
    up expired agents.

    Attributes:
        registry_url: Database URL for storage backend
        repo: Agent registry repository instance
        app: FastAPI application instance
        _cleanup_task: Background task for expired agent cleanup
    """

    def __init__(self, registry_url: str, repo: Optional[AgentRegistryRepository] = None):
        """Initialize the agent registry server.

        Args:
            registry_url: Database URL (e.g., "sqlite:///agents.db")
            repo: Optional pre-configured repository (for testing)
        """
        self.registry_url = registry_url
        self.app: Optional[FastAPI] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Parse URL to create storage config
        if registry_url.startswith("sqlite:///"):
            db_path = registry_url.replace("sqlite:///", "")
            config = StorageConfig(backend="sqlite", path=db_path)
            _, _, self.repo = create_storage_backend(config)
        else:
            raise ValueError(f"Unsupported registry URL: {registry_url}")

        # Use provided repo if given (for testing)
        if repo is not None:
            self.repo = repo

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI application.

        Returns:
            FastAPI application with all registry endpoints
        """
        app = FastAPI(
            title="Agent Registry",
            description="Central registry for distributed agent coordination",
            version="0.1.0",
        )

        # Store reference
        self.app = app

        # Register endpoints
        app.add_api_route("/agents/register", self.register_agent, methods=["POST"])
        app.add_api_route(
            "/agents/{agent_id}/heartbeat", self.heartbeat, methods=["POST"]
        )
        app.add_api_route("/agents", self.list_agents, methods=["GET"])
        app.add_api_route("/agents/{agent_id}", self.get_agent, methods=["GET"])
        app.add_api_route("/agents/{agent_id}", self.delete_agent, methods=["DELETE"])
        app.add_api_route("/health", self.health, methods=["GET"])

        # Register lifecycle events
        app.add_event_handler("startup", self.on_startup)
        app.add_event_handler("shutdown", self.on_shutdown)

        return app

    async def on_startup(self) -> None:
        """Start background cleanup task when server starts."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def on_shutdown(self) -> None:
        """Cancel background cleanup task when server stops."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self) -> None:
        """Background task to periodically delete expired agents.

        Runs every 60 seconds, removing agents whose TTL has expired.
        """
        while True:
            try:
                await asyncio.sleep(60)
                deleted = self.repo.delete_expired()
                if deleted > 0:
                    # Log cleanup (in production, use proper logging)
                    pass
            except asyncio.CancelledError:
                break
            except Exception:
                # Continue loop even if cleanup fails
                pass

    async def register_agent(self, request: AgentRegistrationRequest) -> AgentInfo:
        """Register or update an agent.

        Idempotent operation - if the agent_id already exists, updates
        the existing record with new heartbeat and metadata.

        Args:
            request: Agent registration data

        Returns:
            AgentInfo with current agent status
        """
        from configurable_agents.storage.sqlite import SqliteAgentRegistryRepository

        # For SQLite repo, use session directly for proper merge
        if isinstance(self.repo, SqliteAgentRegistryRepository):
            from sqlalchemy.orm import Session
            engine = self.repo.engine

            with Session(engine) as session:
                existing = session.get(AgentRecord, request.agent_id)

                if existing:
                    # Update existing agent
                    existing.last_heartbeat = datetime.utcnow()
                    existing.agent_name = request.agent_name
                    existing.host = request.host
                    existing.port = request.port
                    existing.ttl_seconds = request.ttl_seconds
                    existing.agent_metadata = request.metadata
                else:
                    # Create new agent
                    existing = AgentRecord(
                        agent_id=request.agent_id,
                        agent_name=request.agent_name,
                        host=request.host,
                        port=request.port,
                        ttl_seconds=request.ttl_seconds,
                        agent_metadata=request.metadata,
                        registered_at=datetime.utcnow(),
                        last_heartbeat=datetime.utcnow(),
                    )
                    session.add(existing)

                session.commit()
                # Refresh to get database defaults and ensure record is attached
                session.refresh(existing)
                return self._record_to_info(existing)
        else:
            # Generic implementation for other repo types
            existing = self.repo.get(request.agent_id)

            if existing:
                # Update existing agent
                existing.last_heartbeat = datetime.utcnow()
                existing.agent_name = request.agent_name
                existing.host = request.host
                existing.port = request.port
                existing.ttl_seconds = request.ttl_seconds
                existing.agent_metadata = request.metadata
            else:
                # Create new agent
                existing = AgentRecord(
                    agent_id=request.agent_id,
                    agent_name=request.agent_name,
                    host=request.host,
                    port=request.port,
                    ttl_seconds=request.ttl_seconds,
                    agent_metadata=request.metadata,
                    registered_at=datetime.utcnow(),
                    last_heartbeat=datetime.utcnow(),
                )
                self.repo.add(existing)

            # Re-fetch to get an attached instance
            agent_record = self.repo.get(request.agent_id)
            return self._record_to_info(agent_record)  # type: ignore

    async def heartbeat(self, agent_id: str) -> HeartbeatResponse:
        """Refresh an agent's heartbeat timestamp.

        Updates the agent's last_heartbeat to now, extending its TTL.

        Args:
            agent_id: Unique identifier for the agent

        Returns:
            HeartbeatResponse with updated timestamp

        Raises:
            HTTPException: 404 if agent not found
        """
        try:
            self.repo.update_heartbeat(agent_id)
            agent = self.repo.get(agent_id)
            return HeartbeatResponse(
                status="ok", last_heartbeat=agent.last_heartbeat  # type: ignore
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def list_agents(
        self,
        include_dead: bool = Query(
            False, description="Include expired agents in response"
        ),
    ) -> list[AgentInfo]:
        """List all registered agents.

        Args:
            include_dead: If False, only return agents with valid TTL

        Returns:
            List of AgentInfo objects
        """
        agents = self.repo.list_all(include_dead=include_dead)
        return [self._record_to_info(a) for a in agents]

    # Fix: make this a proper method with self parameter
    async def get_agent(self, agent_id: str) -> AgentInfo:
        """Get information about a specific agent.

        Args:
            agent_id: Unique identifier for the agent

        Returns:
            AgentInfo with agent details

        Raises:
            HTTPException: 404 if agent not found
        """
        agent = self.repo.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        return self._record_to_info(agent)

    async def delete_agent(self, agent_id: str) -> JSONResponse:
        """Delete an agent from the registry.

        Args:
            agent_id: Unique identifier for the agent

        Returns:
            JSON response confirming deletion

        Raises:
            HTTPException: 404 if agent not found
        """
        try:
            self.repo.delete(agent_id)
            return JSONResponse(
                status_code=200, content={"status": "deleted", "agent_id": agent_id}
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def health(self) -> HealthResponse:
        """Health check endpoint.

        Returns registry status and agent counts.

        Returns:
            HealthResponse with status and metrics
        """
        all_agents = self.repo.list_all(include_dead=False)
        active_count = len(all_agents)
        total_agents = len(self.repo.list_all(include_dead=True))

        return HealthResponse(
            status="healthy", registered_agents=total_agents, active_agents=active_count
        )

    def _record_to_info(self, record: AgentRecord) -> AgentInfo:
        """Convert AgentRecord ORM model to AgentInfo Pydantic model.

        Args:
            record: AgentRecord instance

        Returns:
            AgentInfo instance
        """
        return AgentInfo(
            agent_id=record.agent_id,
            agent_name=record.agent_name,
            host=record.host,
            port=record.port,
            is_alive=record.is_alive(),
            last_heartbeat=record.last_heartbeat,
            registered_at=record.registered_at,
            ttl_seconds=record.ttl_seconds,  # type: ignore
            metadata=record.agent_metadata,
        )


# Convenience function to create app directly
def create_app(registry_url: str = "sqlite:///agents.db") -> FastAPI:
    """Create a FastAPI app for the agent registry.

    Convenience function for quick server startup.

    Args:
        registry_url: Database URL for storage backend

    Returns:
        FastAPI application
    """
    server = AgentRegistryServer(registry_url)
    return server.create_app()
