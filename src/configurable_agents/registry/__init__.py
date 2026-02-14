"""Deployment registry module for distributed workflow coordination.

Provides the central registry server that deployed workflows register with,
and client functionality for workflows to maintain their registration.

The registry tracks:
- Deployment network locations (host:port)
- Deployment metadata (capabilities, configuration, workflow_name)
- Deployment health via TTL-based heartbeats
- Active vs expired deployment status

Renamed in UI Redesign (2026-02-13):
- AgentRegistryServer → DeploymentRegistryServer
- AgentRegistryClient → DeploymentClient
- AgentRecord → Deployment (imported from storage)
- Removed orchestrator-related exports

Public API:
    - DeploymentRegistryServer: FastAPI-based registry server
    - DeploymentClient: Client for deployment self-registration
    - Deployment: ORM model for registry records (imported from storage)

Example:
    >>> from configurable_agents.registry import DeploymentRegistryServer
    >>> server = DeploymentRegistryServer("sqlite:///configurable_agents.db")
    >>> app = server.create_app()
    >>> # Run with uvicorn: uvicorn app:app --port 9000
"""

# Re-export storage models for convenience
from configurable_agents.storage.models import Deployment

# Server and client components
from configurable_agents.registry.server import DeploymentRegistryServer
from configurable_agents.registry.client import DeploymentClient

# Backward-compatible aliases (deprecated)
AgentRegistryServer = DeploymentRegistryServer
AgentRegistryClient = DeploymentClient
WorkflowRegistryServer = DeploymentRegistryServer
WorkflowRegistryClient = DeploymentClient

__all__ = [
    # Preferred names
    "DeploymentRegistryServer",
    "DeploymentClient",
    "Deployment",
    # Backward-compatible aliases
    "AgentRegistryServer",
    "AgentRegistryClient",
    "WorkflowRegistryServer",
    "WorkflowRegistryClient",
]
