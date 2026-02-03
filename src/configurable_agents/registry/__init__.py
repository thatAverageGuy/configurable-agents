"""Agent registry module for distributed agent coordination.

Provides the central registry server that agents register with, and
client functionality for agents to maintain their registration.

The registry tracks:
- Agent network locations (host:port)
- Agent metadata (capabilities, configuration)
- Agent health via TTL-based heartbeats
- Active vs expired agent status

Public API:
    - AgentRegistryServer: FastAPI-based registry server
    - AgentRegistryClient: Client for agent self-registration (stub for Phase 2)
    - AgentRecord: ORM model for agent records

Example:
    >>> from configurable_agents.registry import AgentRegistryServer
    >>> server = AgentRegistryServer("sqlite:///agents.db")
    >>> app = server.create_app()
    >>> # Run with uvicorn: uvicorn app:app --port 8000
"""

# Re-export storage models for convenience
from configurable_agents.storage.models import AgentRecord

# Server and client components (will be implemented in this module)
from configurable_agents.registry.server import AgentRegistryServer

__all__ = [
    "AgentRegistryServer",
    "AgentRecord",
]
