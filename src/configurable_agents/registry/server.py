"""Deployment registry FastAPI server.

Provides HTTP endpoints for deployment registration, heartbeat, listing,
and health checks. Runs a background cleanup task to remove expired deployments.

Renamed in UI Redesign (2026-02-13):
- AgentRegistryServer → DeploymentRegistryServer
- Routes: /agents/* → /deployments/*
- Removed orchestrator endpoints (absorbed into deployments)
- Updated to use new storage classes

Example:
    >>> from configurable_agents.registry import DeploymentRegistryServer
    >>> server = DeploymentRegistryServer("sqlite:///configurable_agents.db")
    >>> app = server.create_app()
    >>> # Run with: uvicorn app:app --port 9000
"""

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from configurable_agents.config.schema import StorageConfig
from configurable_agents.storage.base import DeploymentRepository
from configurable_agents.storage.factory import create_storage_backend
from configurable_agents.storage.models import Deployment

from configurable_agents.registry.models import (
    DeploymentInfo,
    DeploymentRegistrationRequest,
    HealthResponse,
    HeartbeatResponse,
)


class DeploymentRegistryServer:
    """Deployment registry server using FastAPI.

    Provides HTTP endpoints for deployment registration, heartbeat refresh,
    deployment listing, and health checks. Runs a background task to clean
    up expired deployments.

    Attributes:
        registry_url: Database URL for storage backend
        repo: Deployment repository instance
        app: FastAPI application instance
        _cleanup_task: Background task for expired deployment cleanup
    """

    def __init__(self, registry_url: str, repo: Optional[DeploymentRepository] = None):
        """Initialize the deployment registry server.

        Args:
            registry_url: Database URL (e.g., "sqlite:///configurable_agents.db")
            repo: Optional pre-configured repository (for testing)
        """
        self.registry_url = registry_url
        self.app: Optional[FastAPI] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Parse URL to create storage config
        if registry_url.startswith("sqlite:///"):
            db_path = registry_url.replace("sqlite:///", "")
            config = StorageConfig(backend="sqlite", path=db_path)
            _, _, self.repo, _, _, _, _ = create_storage_backend(config)
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
            title="Deployment Registry",
            description="Central registry for distributed deployment coordination",
            version="0.2.0",
        )

        # Store reference
        self.app = app

        # Register deployment endpoints
        app.add_api_route("/deployments/register", self.register_deployment, methods=["POST"])
        app.add_api_route(
            "/deployments/{deployment_id}/heartbeat", self.heartbeat, methods=["POST"]
        )
        app.add_api_route("/deployments", self.list_deployments, methods=["GET"])
        app.add_api_route("/deployments/{deployment_id}", self.get_deployment, methods=["GET"])
        app.add_api_route("/deployments/{deployment_id}", self.delete_deployment, methods=["DELETE"])

        # Health check
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
        """Background task to periodically delete expired deployments.

        Runs every 60 seconds, removing deployments whose TTL has expired.
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

    async def register_deployment(self, request: DeploymentRegistrationRequest) -> DeploymentInfo:
        """Register or update a deployment.

        Idempotent operation - if the deployment_id already exists, updates
        the existing record with new heartbeat and metadata.

        Args:
            request: Deployment registration data

        Returns:
            DeploymentInfo with current deployment status
        """
        from configurable_agents.storage.sqlite import SqliteDeploymentRepository

        # For SQLite repo, use session directly for proper merge
        if isinstance(self.repo, SqliteDeploymentRepository):
            from sqlalchemy.orm import Session
            engine = self.repo.engine

            with Session(engine) as session:
                existing = session.get(Deployment, request.deployment_id)

                if existing:
                    # Update existing deployment
                    existing.last_heartbeat = datetime.utcnow()
                    existing.deployment_name = request.deployment_name
                    existing.host = request.host
                    existing.port = request.port
                    existing.ttl_seconds = request.ttl_seconds
                    existing.workflow_name = request.workflow_name
                    existing.deployment_metadata = request.metadata
                else:
                    # Create new deployment
                    existing = Deployment(
                        deployment_id=request.deployment_id,
                        deployment_name=request.deployment_name,
                        host=request.host,
                        port=request.port,
                        ttl_seconds=request.ttl_seconds,
                        workflow_name=request.workflow_name,
                        deployment_metadata=request.metadata,
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
            existing = self.repo.get(request.deployment_id)

            if existing:
                # Update existing deployment
                existing.last_heartbeat = datetime.utcnow()
                existing.deployment_name = request.deployment_name
                existing.host = request.host
                existing.port = request.port
                existing.ttl_seconds = request.ttl_seconds
                existing.workflow_name = request.workflow_name
                existing.deployment_metadata = request.metadata
            else:
                # Create new deployment
                existing = Deployment(
                    deployment_id=request.deployment_id,
                    deployment_name=request.deployment_name,
                    host=request.host,
                    port=request.port,
                    ttl_seconds=request.ttl_seconds,
                    workflow_name=request.workflow_name,
                    deployment_metadata=request.metadata,
                    registered_at=datetime.utcnow(),
                    last_heartbeat=datetime.utcnow(),
                )
                self.repo.add(existing)

            # Re-fetch to get an attached instance
            record = self.repo.get(request.deployment_id)
            return self._record_to_info(record)  # type: ignore

    async def heartbeat(self, deployment_id: str) -> HeartbeatResponse:
        """Refresh a deployment's heartbeat timestamp.

        Updates the deployment's last_heartbeat to now, extending its TTL.

        Args:
            deployment_id: Unique identifier for the deployment

        Returns:
            HeartbeatResponse with updated timestamp

        Raises:
            HTTPException: 404 if deployment not found
        """
        try:
            self.repo.update_heartbeat(deployment_id)
            deployment = self.repo.get(deployment_id)
            return HeartbeatResponse(
                status="ok", last_heartbeat=deployment.last_heartbeat  # type: ignore
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def list_deployments(
        self,
        include_dead: bool = Query(
            False, description="Include expired deployments in response"
        ),
    ) -> list[DeploymentInfo]:
        """List all registered deployments.

        Args:
            include_dead: If False, only return deployments with valid TTL

        Returns:
            List of DeploymentInfo objects
        """
        deployments = self.repo.list_all(include_dead=include_dead)
        return [self._record_to_info(d) for d in deployments]

    async def get_deployment(self, deployment_id: str) -> DeploymentInfo:
        """Get information about a specific deployment.

        Args:
            deployment_id: Unique identifier for the deployment

        Returns:
            DeploymentInfo with deployment details

        Raises:
            HTTPException: 404 if deployment not found
        """
        deployment = self.repo.get(deployment_id)
        if deployment is None:
            raise HTTPException(status_code=404, detail=f"Deployment not found: {deployment_id}")
        return self._record_to_info(deployment)

    async def delete_deployment(self, deployment_id: str) -> JSONResponse:
        """Delete a deployment from the registry.

        Args:
            deployment_id: Unique identifier for the deployment

        Returns:
            JSON response confirming deletion

        Raises:
            HTTPException: 404 if deployment not found
        """
        try:
            self.repo.delete(deployment_id)
            return JSONResponse(
                status_code=200, content={"status": "deleted", "deployment_id": deployment_id}
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def health(self) -> HealthResponse:
        """Health check endpoint.

        Returns registry status and deployment counts.

        Returns:
            HealthResponse with status and metrics
        """
        all_deployments = self.repo.list_all(include_dead=False)
        active_count = len(all_deployments)
        total_deployments = len(self.repo.list_all(include_dead=True))

        return HealthResponse(
            status="healthy",
            registered_deployments=total_deployments,
            active_deployments=active_count,
        )

    def _record_to_info(self, record: Deployment) -> DeploymentInfo:
        """Convert Deployment ORM model to DeploymentInfo Pydantic model.

        Args:
            record: Deployment instance

        Returns:
            DeploymentInfo instance
        """
        return DeploymentInfo(
            deployment_id=record.deployment_id,
            deployment_name=record.deployment_name,
            host=record.host,
            port=record.port,
            workflow_name=record.workflow_name,
            is_alive=record.is_alive(),
            last_heartbeat=record.last_heartbeat,
            registered_at=record.registered_at,
            ttl_seconds=record.ttl_seconds,  # type: ignore
            metadata=record.deployment_metadata,
        )


# Convenience function to create app directly
def create_app(registry_url: str = "sqlite:///configurable_agents.db") -> FastAPI:
    """Create a FastAPI app for the deployment registry.

    Convenience function for quick server startup.

    Args:
        registry_url: Database URL for storage backend

    Returns:
        FastAPI application
    """
    server = DeploymentRegistryServer(registry_url)
    return server.create_app()


# Backward-compatible alias
AgentRegistryServer = DeploymentRegistryServer
