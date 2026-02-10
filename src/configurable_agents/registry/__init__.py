"""Workflow registry module for distributed workflow coordination.

Provides the central registry server that deployed workflows register with,
and client functionality for workflows to maintain their registration.

The registry tracks:
- Workflow network locations (host:port)
- Workflow metadata (capabilities, configuration)
- Workflow health via TTL-based heartbeats
- Active vs expired workflow status

Note: Internal class names use "Agent" prefix for backward compatibility
with existing storage schema. The public concept is "Workflow Registry".

Public API:
    - WorkflowRegistryServer (alias: AgentRegistryServer): FastAPI-based registry server
    - WorkflowRegistryClient (alias: AgentRegistryClient): Client for workflow self-registration
    - AgentRecord: ORM model for registry records

Example:
    >>> from configurable_agents.registry import WorkflowRegistryServer
    >>> server = WorkflowRegistryServer("sqlite:///registry.db")
    >>> app = server.create_app()
    >>> # Run with uvicorn: uvicorn app:app --port 8000
"""

# Re-export storage models for convenience
from configurable_agents.storage.models import AgentRecord

# Server and client components
from configurable_agents.registry.server import AgentRegistryServer
from configurable_agents.registry.client import AgentRegistryClient

# Public aliases (preferred names)
WorkflowRegistryServer = AgentRegistryServer
WorkflowRegistryClient = AgentRegistryClient

__all__ = [
    # Preferred names
    "WorkflowRegistryServer",
    "WorkflowRegistryClient",
    # Backward-compatible names
    "AgentRegistryServer",
    "AgentRegistryClient",
    "AgentRecord",
]
